from __future__ import annotations

import argparse
import os

from .datasets import materialize_dataset
from .jobs import load_job, update_job
from .storage import load_project, runs_dir


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

    task_type = params.get("task_type", project["schema"]["task_type"])
    model_name = params.get("model") or ("yolov8n-seg.pt" if task_type == "segment" else "yolov8n-pose.pt")
    model = YOLO(model_name)
    device = params.get("device", "auto")
    if device == "auto":
        try:
            import torch

            device = 0 if torch.cuda.is_available() else "cpu"
        except Exception:
            device = "cpu"

    model.train(
        data=str(dataset.data_yaml.resolve()),
        epochs=int(params.get("epochs", 100)),
        imgsz=int(params.get("imgsz", 960)),
        batch=int(params.get("batch", 4)),
        device=device,
        project=str((runs_dir(project["id"]) / task_type).resolve()),
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
