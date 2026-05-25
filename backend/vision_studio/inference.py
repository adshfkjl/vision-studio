from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from PIL import Image

from .jobs import load_job
from .storage import abs_path, image_size, load_project, predictions_dir, project_image_path


MODEL_EXTS = {".pt", ".onnx"}


def resolve_model_path(model_path: str | None = None, job_id: str | None = None, artifact_name: str | None = None) -> Path:
    path: Path | None = None
    if job_id and artifact_name:
        job = load_job(job_id)
        artifact = job.get("artifacts", {}).get(artifact_name)
        if isinstance(artifact, dict):
            path = Path(str(artifact.get("path") or ""))
        elif artifact:
            path = Path(str(artifact))
    elif model_path:
        path = abs_path(model_path)

    if path is None:
        raise FileNotFoundError("No model was selected")
    if path.suffix.lower() not in MODEL_EXTS:
        raise ValueError("Model must be a .pt or .onnx file")
    if not path.is_file():
        raise FileNotFoundError(f"Model file not found: {path}")
    return path


def resolve_image_path(project_id: str | None = None, image_name: str | None = None, image_path: str | None = None) -> Path:
    if project_id and image_name:
        return project_image_path(load_project(project_id), image_name)
    path = abs_path(image_path)
    if path is None:
        raise FileNotFoundError("No image was selected")
    if not path.is_file():
        raise FileNotFoundError(f"Image file not found: {path}")
    return path


def class_name(schema: dict[str, Any] | None, class_id: int, names: dict[int, str] | None = None) -> str:
    if schema:
        for cls in schema.get("classes", []):
            if int(cls.get("id", -1)) == class_id:
                return str(cls.get("name") or class_id)
    if names and class_id in names:
        return str(names[class_id])
    return str(class_id)


def box_instance(box: Any, width: int, height: int, schema: dict[str, Any] | None, names: dict[int, str] | None) -> dict[str, Any]:
    xywhn = box.xywhn[0].tolist()
    class_id = int(box.cls[0].item())
    return {
        "type": "box",
        "class_id": class_id,
        "class_name": class_name(schema, class_id, names),
        "confidence": round(float(box.conf[0].item()), 4),
        "bbox": {
            "cx": float(xywhn[0]),
            "cy": float(xywhn[1]),
            "w": float(xywhn[2]),
            "h": float(xywhn[3]),
        },
        "pixels": {
            "width": width,
            "height": height,
        },
    }


def enrich_instance(instance: dict[str, Any], result: Any, index: int, schema: dict[str, Any] | None) -> dict[str, Any]:
    masks = getattr(result, "masks", None)
    if masks is not None and getattr(masks, "xyn", None) is not None and index < len(masks.xyn):
        points = [{"x": float(x), "y": float(y)} for x, y in masks.xyn[index].tolist()]
        instance = {**instance, "type": "polygon", "points": points}

    keypoints = getattr(result, "keypoints", None)
    if keypoints is not None and getattr(keypoints, "xyn", None) is not None and index < len(keypoints.xyn):
        names = schema.get("keypoints", []) if schema else []
        confidences = []
        if getattr(keypoints, "conf", None) is not None:
            confidences = keypoints.conf[index].tolist()
        points = []
        for point_index, (x, y) in enumerate(keypoints.xyn[index].tolist()):
            confidence = confidences[point_index] if point_index < len(confidences) else 0
            points.append({
                "name": names[point_index] if point_index < len(names) else str(point_index),
                "x": float(x),
                "y": float(y),
                "v": 2 if confidence else 0,
                "confidence": round(float(confidence), 4),
            })
        instance = {**instance, "type": "pose", "keypoints": points}
    return instance


def classification_instances(result: Any, schema: dict[str, Any] | None, names: dict[int, str] | None) -> list[dict[str, Any]]:
    probs = getattr(result, "probs", None)
    if probs is None or getattr(probs, "top5", None) is None:
        return []
    scores = getattr(probs, "data", None)
    instances = []
    for class_id in probs.top5[:5]:
        confidence = float(scores[class_id].item()) if scores is not None else 0
        instances.append({
            "type": "classification",
            "class_id": int(class_id),
            "class_name": class_name(schema, int(class_id), names),
            "confidence": round(confidence, 4),
        })
    return instances


def summarize(instances: list[dict[str, Any]]) -> dict[str, Any]:
    by_class: dict[str, int] = {}
    for inst in instances:
        name = str(inst.get("class_name") or inst.get("class_id"))
        by_class[name] = by_class.get(name, 0) + 1
    return {"total": len(instances), "by_class": by_class}


def run_prediction(
    model_path: Path,
    image_path: Path,
    *,
    conf: float = 0.25,
    iou: float = 0.7,
    imgsz: int | None = None,
    device: str = "auto",
    schema: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from ultralytics import YOLO

    model = YOLO(str(model_path))
    kwargs: dict[str, Any] = {"source": str(image_path), "conf": conf, "iou": iou, "verbose": False}
    if imgsz:
        kwargs["imgsz"] = imgsz
    if device and device != "auto":
        kwargs["device"] = device
    result = model.predict(**kwargs)[0]
    width, height = image_size(image_path)
    names = getattr(result, "names", None)
    boxes = getattr(result, "boxes", None)
    instances = []
    if boxes is not None:
        instances = [enrich_instance(box_instance(box, width, height, schema, names), result, idx, schema) for idx, box in enumerate(boxes)]
    if not instances:
        instances = classification_instances(result, schema, names)

    out_dir = predictions_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    preview_name = f"{uuid.uuid4().hex}.jpg"
    preview_path = out_dir / preview_name
    plotted = result.plot()
    Image.fromarray(plotted).save(preview_path)
    return {
        "preview_path": str(preview_path),
        "preview_name": preview_name,
        "model": str(model_path),
        "image": {"name": image_path.name, "width": width, "height": height},
        "instances": instances,
        "summary": summarize(instances),
    }
