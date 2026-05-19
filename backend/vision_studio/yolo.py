from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .storage import abs_path, annotation_path, image_size, iter_images, load_project, project_image_path, read_json, yolo_label_path
from .tasks import DEFAULT_COLORS, default_schema_for_task


SPLIT_NAMES = {"train", "val", "test"}


def default_schema(task_type: str) -> dict[str, Any]:
    return default_schema_for_task(task_type)


def schema_from_data_yaml(path: Path | None, task_type: str, image_dir: Path | None = None) -> dict[str, Any]:
    schema = default_schema(task_type)
    if path is None or not path.is_file():
        if task_type == "classify" and image_dir is not None:
            class_names = set()
            for child in image_dir.iterdir() if image_dir.is_dir() else []:
                if not child.is_dir():
                    continue
                if child.name in SPLIT_NAMES:
                    class_names.update(grandchild.name for grandchild in child.iterdir() if grandchild.is_dir())
                else:
                    class_names.add(child.name)
            for image in iter_images(image_dir):
                class_name = classification_class_name(str(image.relative_to(image_dir)))
                if class_name:
                    class_names.add(class_name)
            class_names = sorted(class_names)
            if class_names:
                schema["classes"] = [
                    {"id": idx, "name": name, "color": DEFAULT_COLORS[idx % len(DEFAULT_COLORS)]}
                    for idx, name in enumerate(class_names)
                ]
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


def classification_class_name(image_name: str) -> str | None:
    parts = [part for part in image_name.replace("\\", "/").split("/") if part]
    if len(parts) < 2:
        return None
    parent = parts[-2]
    if parent in SPLIT_NAMES and len(parts) >= 3:
        return parts[-3] or None
    return parent or None


def classification_class_id(project: dict[str, Any], image_name: str) -> int | None:
    class_name = classification_class_name(image_name)
    if class_name is None:
        return None
    for cls in project.get("schema", {}).get("classes", []):
        if str(cls.get("name")) == class_name:
            return int(cls.get("id", 0))
    return None


def image_has_label(project: dict[str, Any], image_name: str) -> bool:
    task_type = project.get("schema", {}).get("task_type") or project.get("task_type")
    if task_type == "classify":
        return classification_class_id(project, image_name) is not None
    if task_type == "obb":
        label_dir = abs_path(project.get("label_dir"))
        return bool(label_dir and (label_dir / f"{Path(image_name).stem}.txt").is_file())
    return annotation_path(project["id"], image_name).is_file() or bool(yolo_label_path(project, image_name) and yolo_label_path(project, image_name).is_file())


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
        if task_type == "detect" and len(values) >= 4:
            bbox = {"cx": values[0], "cy": values[1], "w": values[2], "h": values[3]}
            annotation["instances"].append({"type": "box", "class_id": class_id, "bbox": bbox})
        elif task_type == "classify":
            annotation["instances"].append({"type": "classification", "class_id": class_id, "class_name": schema.get("classes", [{}])[class_id].get("name") if class_id < len(schema.get("classes", [])) else ""})
        elif task_type == "obb" and len(values) >= 8:
            points = [{"x": values[i], "y": values[i + 1]} for i in range(0, 8, 2)]
            annotation["instances"].append({"type": "obb", "class_id": class_id, "points": points})
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
    if project["schema"]["task_type"] == "classify":
        class_id = classification_class_id(project, image_name)
        if class_id is None:
            return {"version": 1, "instances": []}
        class_name = classification_class_name(image_name) or ""
        return {
            "version": 1,
            "instances": [
                {
                    "type": "classification",
                    "class_id": class_id,
                    "class_name": class_name,
                }
            ],
        }
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
        if task_type == "detect" and inst.get("type") in {"box", "bbox"}:
            bbox = inst.get("bbox") or {}
            vals = [bbox.get("cx", 0), bbox.get("cy", 0), bbox.get("w", 0), bbox.get("h", 0)]
            lines.append(" ".join([str(class_id), *[format_float(v) if isinstance(v, float) else str(v) for v in vals]]))
        elif task_type == "classify" and inst.get("type") == "classification":
            lines.append(str(class_id))
        elif task_type == "obb" and inst.get("type") == "obb":
            points = inst.get("points", [])
            if len(points) != 4:
                continue
            vals: list[float] = []
            for pt in points:
                vals.extend([pt.get("x", 0), pt.get("y", 0)])
            lines.append(" ".join([str(class_id), *[format_float(v) for v in vals]]))
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
    if schema["task_type"] == "classify":
        lines = [
            f"path: {root}",
            "train: train",
            "val: val",
        ]
        if (dataset_root / "test").is_dir():
            lines.append("test: test")
    else:
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
