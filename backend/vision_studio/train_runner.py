from __future__ import annotations

import argparse
import os
import sys

from .datasets import materialize_dataset
from .devices import available_devices
from .jobs import append_log, load_job, update_job
from .storage import load_project, runs_dir
from .tasks import default_model_for_task, get_task


def resolve_training_device(params: dict, device_info: dict | None = None) -> str:
    device = str(params.get("device") or "auto").strip()
    if device in {"", "auto", "gpu", "cuda"}:
        info = device_info or available_devices()
        return str(info.get("recommended") or "cpu")
    return device


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-id", required=True)
    args = parser.parse_args()

    job = load_job(args.job_id)
    project = load_project(job["project_id"])
    params = job.get("params", {})
    update_job(args.job_id, status="materializing")
    dataset = materialize_dataset(project)
    update_job(args.job_id, status="running", dataset={"root": str(dataset.root), "data_yaml": str(dataset.data_yaml)})

    from ultralytics import YOLO
    import torch

    append_log(args.job_id, f"[studio] Runner Python: {sys.executable}\n")
    append_log(args.job_id, f"[studio] Torch: {torch.__version__} from {torch.__file__}\n")
    append_log(args.job_id, f"[studio] CUDA available: {torch.cuda.is_available()} count={torch.cuda.device_count()}\n")

    task_type = params.get("task_type", project["schema"]["task_type"])
    task = get_task(task_type)
    model_name = params.get("model") or default_model_for_task(task_type)
    model = YOLO(model_name)
    device = resolve_training_device(params)
    append_log(args.job_id, f"[studio] Using training device: {device}\n")

    model.train(
        data=str(dataset.data_yaml.resolve()),
        epochs=int(params.get("epochs", 100)),
        imgsz=int(params.get("imgsz", 960)),
        batch=int(params.get("batch", 4)),
        device=int(device) if str(device).isdigit() else device,
        project=str((runs_dir(project["id"]) / task["task_type"]).resolve()),
        name=params.get("name", "studio_train"),
        exist_ok=True,
        pretrained=True,
        optimizer=params.get("optimizer", "AdamW"),
        lr0=float(params.get("lr0", 0.01)),
        patience=int(params.get("patience", 30)),
        seed=int(params.get("seed", 42)),
        workers=min(8, os.cpu_count() or 4),
        plots=True,
        save=True,
    )


if __name__ == "__main__":
    main()
