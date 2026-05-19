from __future__ import annotations

from typing import Any

DEFAULT_COLORS = [
    "#0f766e",
    "#d97706",
    "#2563eb",
    "#be123c",
    "#7c3aed",
    "#15803d",
    "#c2410c",
]

TASK_DEFINITIONS: dict[str, dict[str, Any]] = {
    "detect": {
        "task_type": "detect",
        "display_name": "Detection",
        "station_annotation": True,
        "supports_import_training": True,
        "ultralytics_task": "detect",
        "default_model": "yolov8n.pt",
        "label_kind": "bbox",
    },
    "segment": {
        "task_type": "segment",
        "display_name": "Segmentation",
        "station_annotation": True,
        "supports_import_training": True,
        "ultralytics_task": "segment",
        "default_model": "yolov8n-seg.pt",
        "label_kind": "polygon",
    },
    "pose": {
        "task_type": "pose",
        "display_name": "Pose",
        "station_annotation": True,
        "supports_import_training": True,
        "ultralytics_task": "pose",
        "default_model": "yolov8n-pose.pt",
        "label_kind": "pose",
    },
    "classify": {
        "task_type": "classify",
        "display_name": "Classification",
        "station_annotation": False,
        "supports_import_training": True,
        "ultralytics_task": "classify",
        "default_model": "yolov8n-cls.pt",
        "label_kind": "folder",
    },
    "obb": {
        "task_type": "obb",
        "display_name": "Oriented Bounding Box",
        "station_annotation": False,
        "supports_import_training": True,
        "ultralytics_task": "obb",
        "default_model": "yolov8n-obb.pt",
        "label_kind": "obb",
    },
}


def task_definitions() -> dict[str, dict[str, Any]]:
    return TASK_DEFINITIONS


def available_tasks() -> list[dict[str, Any]]:
    return [TASK_DEFINITIONS[name] for name in ("detect", "segment", "pose", "classify", "obb")]


def get_task(task_type: str) -> dict[str, Any]:
    if task_type not in TASK_DEFINITIONS:
        raise KeyError(f"Unsupported task type: {task_type}")
    return TASK_DEFINITIONS[task_type]


def default_model_for_task(task_type: str) -> str:
    return get_task(task_type)["default_model"]


def station_annotation_supported(task_type: str) -> bool:
    return bool(get_task(task_type)["station_annotation"])


def default_schema_for_task(task_type: str) -> dict[str, Any]:
    schema: dict[str, Any] = {
        "task_type": task_type,
        "classes": [{"id": 0, "name": "stem", "color": DEFAULT_COLORS[0]}],
        "keypoints": [],
        "skeleton": [],
        "flip_idx": [],
    }
    if task_type == "pose":
        schema.update(
            {
                "keypoints": ["stem_root", "stem_mid", "stem_top"],
                "skeleton": [[0, 1], [1, 2]],
                "flip_idx": [2, 1, 0],
            }
        )
    return schema
