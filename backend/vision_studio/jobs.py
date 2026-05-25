from __future__ import annotations

import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from .storage import JOBS_ROOT, exports_dir, load_project, read_json, runs_dir, write_json


def job_path(job_id: str) -> Path:
    return JOBS_ROOT / job_id / "job.json"


def log_path(job_id: str) -> Path:
    return JOBS_ROOT / job_id / "log.txt"


def create_job(project_id: str, kind: str, params: dict[str, Any]) -> dict[str, Any]:
    job_id = uuid.uuid4().hex[:12]
    job = {
        "id": job_id,
        "project_id": project_id,
        "kind": kind,
        "status": "queued",
        "params": params,
        "created_at": time.time(),
        "updated_at": time.time(),
        "artifacts": {},
        "error": None,
    }
    write_json(job_path(job_id), job)
    log_path(job_id).parent.mkdir(parents=True, exist_ok=True)
    log_path(job_id).write_text("", encoding="utf-8")
    return job


def load_job(job_id: str) -> dict[str, Any]:
    job = read_json(job_path(job_id))
    if job is None:
        raise FileNotFoundError(f"Job not found: {job_id}")
    job["log"] = log_path(job_id).read_text(encoding="utf-8") if log_path(job_id).exists() else ""
    return job


def list_jobs(project_id: str | None = None, kind: str | None = None) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    if not JOBS_ROOT.is_dir():
        return jobs
    for path in JOBS_ROOT.glob("*/job.json"):
        job = read_json(path)
        if not job:
            continue
        if project_id and job.get("project_id") != project_id:
            continue
        if kind and job.get("kind") != kind:
            continue
        jobs.append(job)
    return sorted(jobs, key=lambda item: item.get("updated_at") or item.get("created_at") or 0, reverse=True)


def update_job(job_id: str, **fields: Any) -> None:
    job = read_json(job_path(job_id))
    if not job:
        return
    job.update(fields)
    job["updated_at"] = time.time()
    write_json(job_path(job_id), job)


def append_log(job_id: str, text: str) -> None:
    path = log_path(job_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(text)


def run_training_job(job_id: str) -> None:
    job = load_job(job_id)
    update_job(job_id, status="materializing")
    append_log(job_id, "[studio] Starting training job\n")
    cmd = [
        sys.executable,
        "-m",
        "vision_studio.train_runner",
        "--job-id",
        job_id,
    ]
    proc = subprocess.Popen(
        cmd,
        cwd=str(Path(__file__).resolve().parents[1]),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.stdout is not None
    for line in proc.stdout:
        append_log(job_id, line)
    code = proc.wait()
    if code != 0:
        update_job(job_id, status="failed", error=f"Training exited with code {code}")
        return
    project = load_project(job["project_id"])
    params = job.get("params", {})
    task = params.get("task_type", project["schema"]["task_type"])
    name = params.get("name", "studio_train")
    weight_dir = runs_dir(project["id"]) / task / name / "weights"
    artifacts = {}
    for key in ("best", "last"):
        path = weight_dir / f"{key}.pt"
        if path.is_file():
            artifacts[f"{key}.pt"] = {"path": str(path), "size": path.stat().st_size}
    for pattern in ("results.csv", "results.png", "confusion_matrix.png", "labels.jpg"):
        path = runs_dir(project["id"]) / task / name / pattern
        if path.is_file():
            artifacts[pattern] = {"path": str(path), "size": path.stat().st_size}
    update_job(job_id, status="completed", artifacts=artifacts)
    append_log(job_id, "[studio] Training completed\n")


def start_training(project_id: str, params: dict[str, Any]) -> dict[str, Any]:
    job = create_job(project_id, "train", params)
    thread = threading.Thread(target=run_training_job, args=(job["id"],), daemon=True)
    thread.start()
    return job


def export_onnx(job_id: str) -> dict[str, Any]:
    job = load_job(job_id)
    artifacts = job.get("artifacts", {})
    best_artifact = artifacts.get("best.pt") or artifacts.get("last.pt")
    best = best_artifact.get("path") if isinstance(best_artifact, dict) else best_artifact
    if not best:
        raise FileNotFoundError("No .pt artifact is available for export")
    update_job(job_id, status="exporting")
    append_log(job_id, "[studio] Exporting ONNX\n")
    try:
        from ultralytics import YOLO

        model = YOLO(best)
        exported = Path(model.export(format="onnx"))
        project = load_project(job["project_id"])
        out_dir = exports_dir(project["id"])
        out_dir.mkdir(parents=True, exist_ok=True)
        target = out_dir / exported.name
        if exported.resolve() != target.resolve():
            target.write_bytes(exported.read_bytes())
        artifacts["onnx"] = {"path": str(target), "size": target.stat().st_size}
        update_job(job_id, status="completed", artifacts=artifacts)
        append_log(job_id, f"[studio] ONNX exported: {target}\n")
        return load_job(job_id)
    except Exception as exc:
        update_job(job_id, status="failed", error=str(exc))
        append_log(job_id, f"[studio] ONNX export failed: {exc}\n")
        raise
