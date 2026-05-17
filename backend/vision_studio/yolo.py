from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .storage import abs_path, annotation_path, image_size, load_project, project_image_path, read_json


DEFAULT_COLORS = [
    "#0f766e",
    "#d97706",
    "#2563eb",
    "#be123c",
    "#7c3aed",
    "#15803d",
    "#c2410c",
]


def default_schema(task_type: str) -> dict[str, Any]:
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


def schema_from_data_yaml(path: Path | None, task_type: str) -> dict[str, Any]:
    schema = default_schema(task_type)
    if path is None or not path.is_file():
        return schema
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    names = data.get("names")
    classes = []
    if isinstance(names, dict):
        for idx, name in sorted((int(k), str(v)) for k, v in names.items()):
            classes.append({"id": idx, "name": name, "color": DEFAULT_COLORS[idx % len(DEFAULT_COLORS)]})
    elif isinstance(names, list):
        for idx, name in enumerate(names):
            classes.append({"id": idx, "name": str(name), "color": DEFAULT_COLORS[idx % len(DEFAULT_COLORS)]})
    if classes:
        schema["classes"] = classes

    if task_type == "pose":
        kpt_names = data.get("kpt_names")
        keypoints: list[str] = []
        if isinstance(kpt_names, dict):
            first = kpt_names.get(0) or kpt_names.get("0")
            if isinstance(first, list):
                keypoints = [str(x) for x in first]
        if keypoints:
            schema["keypoints"] = keypoints
            schema["skeleton"] = [[i, i + 1] for i in range(len(keypoints) - 1)]
        flip_idx = data.get("flip_idx")
        if isinstance(flip_idx, list) and len(flip_idx) == len(schema["keypoints"]):
            schema["flip_idx"] = [int(x) for x in flip_idx]
    return schema


def parse_yolo_label(label_path: Path, task_type: str, schema: dict[str, Any]) -> dict[str, Any]:
    annotation = {"version": 1, "instances": []}
    if not label_path.is_file():
        return annotation

    for line in label_path.read_text(encoding="utf-8").splitlines():
        parts = line.strip().split()
        if not parts:
            continue
        class_id = int(float(parts[0]))
        values = [float(x) for x in parts[1:]]
        if task_type == "pose" and len(values) >= 4:
            bbox = {"cx": values[0], "cy": values[1], "w": values[2], "h": values[3]}
            raw_kpts = values[4:]
            keypoints = []
            for idx, name in enumerate(schema.get("keypoints", [])):
                pos = idx * 3
                if pos + 2 < len(raw_kpts):
                    keypoints.append({"name": name, "x": raw_kpts[pos], "y": raw_kpts[pos + 1], "v": int(raw_kpts[pos + 2])})
                else:
                    keypoints.append({"name": name, "x": 0.0, "y": 0.0, "v": 0})
            annotation["instances"].append({"type": "pose", "class_id": class_id, "bbox": bbox, "keypoints": keypoints})
        elif task_type == "segment" and len(values) >= 6:
            points = [{"x": values[i], "y": values[i + 1]} for i in range(0, len(values) - 1, 2)]
            annotation["instances"].append({"type": "polygon", "class_id": class_id, "points": points})
    return annotation


def annotation_for_image(project: dict[str, Any], image_name: str) -> dict[str, Any]:
    saved = read_json(annotation_path(project["id"], image_name))
    if saved is not None:
        return saved
    label_dir = abs_path(project.get("label_dir"))
    if label_dir is None:
        return {"version": 1, "instances": []}
    return parse_yolo_label(label_dir / f"{Path(image_name).stem}.txt", project["schema"]["task_type"], project["schema"])


def format_float(value: float) -> str:
    return f"{max(0.0, min(1.0, float(value))):.6f}".rstrip("0").rstrip(".")


def annotation_to_yolo(annotation: dict[str, Any], schema: dict[str, Any]) -> str:
    task_type = schema["task_type"]
    lines: list[str] = []
    for inst in annotation.get("instances", []):
        class_id = int(inst.get("class_id", 0))
        if task_type == "pose" and inst.get("type") == "pose":
            bbox = inst.get("bbox") or {}
            vals = [bbox.get("cx", 0), bbox.get("cy", 0), bbox.get("w", 0), bbox.get("h", 0)]
            points_by_name = {p.get("name"): p for p in inst.get("keypoints", [])}
            for name in schema.get("keypoints", []):
                pt = points_by_name.get(name) or {}
                vals.extend([pt.get("x", 0), pt.get("y", 0), int(pt.get("v", 0))])
            lines.append(" ".join([str(class_id), *[format_float(v) if isinstance(v, float) else str(v) for v in vals]]))
        elif task_type == "segment" and inst.get("type") == "polygon":
            pts = inst.get("points", [])
            if len(pts) < 3:
                continue
            vals: list[float] = []
            for pt in pts:
                vals.extend([pt.get("x", 0), pt.get("y", 0)])
            lines.append(" ".join([str(class_id), *[format_float(v) for v in vals]]))
    return "\n".join(lines) + ("\n" if lines else "")


def data_yaml_text(project: dict[str, Any], dataset_root: Path) -> str:
    schema = project["schema"]
    root = str(dataset_root.resolve()).replace("\\", "/")
    lines = [
        f"path: {root}",
        "train: images/train",
        "val: images/val",
    ]
    if (dataset_root / "images" / "test").is_dir():
        lines.append("test: images/test")
    if schema["task_type"] == "pose":
        kpts = schema.get("keypoints", [])
        lines.append(f"kpt_shape: [{len(kpts)}, 3]")
        flip = schema.get("flip_idx") or list(range(len(kpts)))
        lines.append("flip_idx: [" + ", ".join(str(int(x)) for x in flip) + "]")
    lines.append("names:")
    for cls in sorted(schema.get("classes", []), key=lambda c: int(c["id"])):
        lines.append(f"  {int(cls['id'])}: {cls['name']}")
    if schema["task_type"] == "pose":
        lines.append("kpt_names:")
        lines.append("  0:")
        for name in schema.get("keypoints", []):
            lines.append(f"    - {name}")
    return "\n".join(lines) + "\n"


def load_annotation_with_size(project_id: str, image_name: str) -> dict[str, Any]:
    project = load_project(project_id)
    image = project_image_path(project, image_name)
    w, h = image_size(image)
    return {"image": image_name, "width": w, "height": h, "annotation": annotation_for_image(project, image_name)}

