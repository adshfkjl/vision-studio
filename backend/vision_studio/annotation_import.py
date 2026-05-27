from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from .cvat import import_cvat_annotations, schema_from_cvat_xml
from .storage import annotation_path, write_json
from .tasks import DEFAULT_COLORS, default_schema_for_task
from .yolo import parse_yolo_label


SUPPORTED_FORMATS = {
    "auto",
    "cvat_xml",
    "coco_json",
    "labelme_json",
    "pascal_voc",
    "yolo_labels",
}


def detect_annotation_format(path: Path, format_hint: str | None = None) -> str:
    hint = (format_hint or "auto").strip().lower()
    if hint and hint != "auto":
        if hint not in SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported annotation format: {format_hint}")
        return hint
    if path.is_dir():
        json_files = sorted(path.glob("*.json"))
        if json_files:
            return detect_annotation_format(json_files[0])
        xml_files = sorted(path.glob("*.xml"))
        if xml_files:
            root = ET.parse(xml_files[0]).getroot()
            return "cvat_xml" if root.tag == "annotations" else "pascal_voc"
        if list(path.glob("*.txt")):
            return "yolo_labels"
    if path.suffix.lower() == ".xml":
        root = ET.parse(path).getroot()
        return "cvat_xml" if root.tag == "annotations" else "pascal_voc"
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and {"images", "annotations", "categories"}.issubset(data):
            return "coco_json"
        if isinstance(data, dict) and isinstance(data.get("shapes"), list):
            return "labelme_json"
    if path.suffix.lower() == ".txt":
        return "yolo_labels"
    raise ValueError(f"Could not detect annotation format for: {path}")


def schema_from_annotation_source(path: Path, task_type: str, format_hint: str | None = None) -> dict[str, Any]:
    fmt = detect_annotation_format(path, format_hint)
    if fmt == "cvat_xml":
        return schema_from_cvat_xml(_single_file(path, ".xml"), task_type)
    schema = default_schema_for_task(task_type)
    class_names: list[str] = []
    if fmt == "coco_json":
        data = _load_coco_json(path)
        class_names = [str(category.get("name") or category.get("id")) for category in data.get("categories", [])]
        if task_type == "pose":
            keypoints = next((category.get("keypoints") for category in data.get("categories", []) if category.get("keypoints")), None)
            if isinstance(keypoints, list):
                schema["keypoints"] = [str(name) for name in keypoints]
                schema["skeleton"] = _coco_skeleton(data.get("categories", []), len(schema["keypoints"]))
                schema["flip_idx"] = list(range(len(schema["keypoints"])))
    elif fmt == "pascal_voc":
        class_names = _voc_class_names(path)
    elif fmt == "labelme_json":
        class_names = _labelme_class_names(path)
    if class_names:
        schema["classes"] = _classes(class_names)
    return schema


def merge_import_schema(current: dict[str, Any], imported: dict[str, Any]) -> dict[str, Any]:
    merged = {**current}
    if imported.get("classes"):
        merged["classes"] = imported["classes"]
    if imported.get("keypoints"):
        merged["keypoints"] = imported["keypoints"]
        merged["skeleton"] = imported.get("skeleton", [])
        merged["flip_idx"] = imported.get("flip_idx", list(range(len(imported["keypoints"]))))
    merged.setdefault("task_type", current.get("task_type") or imported.get("task_type"))
    return merged


def import_annotation_source(project: dict[str, Any], path: Path, format_hint: str | None = None) -> dict[str, Any]:
    fmt = detect_annotation_format(path, format_hint)
    if fmt == "cvat_xml":
        return import_cvat_annotations(project, _single_file(path, ".xml"))
    if fmt == "pascal_voc":
        records = _voc_records(path, project["schema"])
    elif fmt == "coco_json":
        records = _coco_records(path, project["schema"])
    elif fmt == "labelme_json":
        records = _labelme_records(path, project["schema"])
    elif fmt == "yolo_labels":
        records = _yolo_records(path, project["schema"])
    else:
        raise ValueError(f"Unsupported annotation format: {fmt}")
    return _materialize_records(project, fmt, records)


def _classes(names: list[str]) -> list[dict[str, Any]]:
    seen: list[str] = []
    for name in names:
        cleaned = str(name).strip()
        if cleaned and cleaned not in seen:
            seen.append(cleaned)
    return [
        {"id": idx, "name": name, "color": DEFAULT_COLORS[idx % len(DEFAULT_COLORS)]}
        for idx, name in enumerate(seen)
    ]


def _class_id(schema: dict[str, Any], name: str | None = None, source_id: int | None = None) -> int:
    if name:
        for cls in schema.get("classes", []):
            if str(cls.get("name")) == str(name):
                return int(cls.get("id", 0))
    if source_id is not None:
        for cls in schema.get("classes", []):
            if int(cls.get("id", -1)) == source_id:
                return source_id
    return 0


def _bbox_xywh(x: float, y: float, w: float, h: float, width: float, height: float) -> dict[str, float]:
    return {
        "cx": (x + w / 2) / width,
        "cy": (y + h / 2) / height,
        "w": max(0.004, w / width),
        "h": max(0.004, h / height),
    }


def _bbox_xyxy(xmin: float, ymin: float, xmax: float, ymax: float, width: float, height: float) -> dict[str, float]:
    return _bbox_xywh(xmin, ymin, xmax - xmin, ymax - ymin, width, height)


def _single_file(path: Path, suffix: str) -> Path:
    if path.is_file():
        return path
    files = sorted(path.glob(f"*{suffix}"))
    if not files:
        raise ValueError(f"No {suffix} annotation file found in {path}")
    return files[0]


def _json_files(path: Path) -> list[Path]:
    return sorted(path.glob("*.json")) if path.is_dir() else [path]


def _xml_files(path: Path) -> list[Path]:
    return sorted(path.glob("*.xml")) if path.is_dir() else [path]


def _load_coco_json(path: Path) -> dict[str, Any]:
    target = path
    if path.is_dir():
        json_files = _json_files(path)
        for candidate in json_files:
            data = json.loads(candidate.read_text(encoding="utf-8"))
            if isinstance(data, dict) and {"images", "annotations", "categories"}.issubset(data):
                return data
        raise ValueError(f"No COCO JSON file found in {path}")
    return json.loads(target.read_text(encoding="utf-8"))


def _voc_class_names(path: Path) -> list[str]:
    names: list[str] = []
    for xml_path in _xml_files(path):
        root = ET.parse(xml_path).getroot()
        names.extend((obj.findtext("name") or "").strip() for obj in root.findall("object"))
    return names


def _labelme_class_names(path: Path) -> list[str]:
    names: list[str] = []
    for json_path in _json_files(path):
        data = json.loads(json_path.read_text(encoding="utf-8"))
        names.extend(str(shape.get("label") or "") for shape in data.get("shapes", []))
    return names


def _voc_records(path: Path, schema: dict[str, Any]) -> list[dict[str, Any]]:
    records = []
    for xml_path in _xml_files(path):
        root = ET.parse(xml_path).getroot()
        width = float(root.findtext("./size/width") or 1)
        height = float(root.findtext("./size/height") or 1)
        filename = (root.findtext("filename") or xml_path.with_suffix("").name).replace("\\", "/")
        instances = []
        for obj in root.findall("object"):
            name = (obj.findtext("name") or "").strip()
            box = obj.find("bndbox")
            if box is None:
                continue
            xmin = float(box.findtext("xmin") or 0)
            ymin = float(box.findtext("ymin") or 0)
            xmax = float(box.findtext("xmax") or 0)
            ymax = float(box.findtext("ymax") or 0)
            instances.append({"type": "box", "class_id": _class_id(schema, name), "bbox": _bbox_xyxy(xmin, ymin, xmax, ymax, width, height)})
        records.append({"image": filename, "instances": instances})
    return records


def _coco_records(path: Path, schema: dict[str, Any]) -> list[dict[str, Any]]:
    data = _load_coco_json(path)
    images = {image.get("id"): image for image in data.get("images", [])}
    categories = {category.get("id"): str(category.get("name") or category.get("id")) for category in data.get("categories", [])}
    grouped: dict[Any, list[dict[str, Any]]] = {}
    task_type = schema.get("task_type")
    keypoints = schema.get("keypoints", [])
    for ann in data.get("annotations", []):
        image = images.get(ann.get("image_id"))
        if not image:
            continue
        width = float(image.get("width") or 1)
        height = float(image.get("height") or 1)
        class_id = _class_id(schema, categories.get(ann.get("category_id")))
        instances = grouped.setdefault(ann.get("image_id"), [])
        if task_type == "segment" and isinstance(ann.get("segmentation"), list):
            for raw_poly in ann["segmentation"]:
                if not isinstance(raw_poly, list) or len(raw_poly) < 6:
                    continue
                points = [{"x": raw_poly[i] / width, "y": raw_poly[i + 1] / height} for i in range(0, len(raw_poly) - 1, 2)]
                instances.append({"type": "polygon", "class_id": class_id, "points": points})
        elif task_type == "pose" and isinstance(ann.get("keypoints"), list):
            raw = ann["keypoints"]
            points = []
            for idx, name in enumerate(keypoints):
                pos = idx * 3
                points.append({"name": name, "x": raw[pos] / width if pos < len(raw) else 0, "y": raw[pos + 1] / height if pos + 1 < len(raw) else 0, "v": int(raw[pos + 2]) if pos + 2 < len(raw) else 0})
            bbox = ann.get("bbox") or [0, 0, 1, 1]
            instances.append({"type": "pose", "class_id": class_id, "bbox": _bbox_xywh(*[float(v) for v in bbox[:4]], width, height), "keypoints": points})
        elif isinstance(ann.get("bbox"), list) and len(ann["bbox"]) >= 4:
            x, y, w, h = [float(v) for v in ann["bbox"][:4]]
            instances.append({"type": "box", "class_id": class_id, "bbox": _bbox_xywh(x, y, w, h, width, height)})
    return [{"image": str(image.get("file_name", "")), "instances": grouped.get(image_id, [])} for image_id, image in images.items()]


def _coco_skeleton(categories: list[dict[str, Any]], keypoint_count: int) -> list[list[int]]:
    skeleton = next((category.get("skeleton") for category in categories if category.get("skeleton")), None)
    if not isinstance(skeleton, list):
        return [[idx, idx + 1] for idx in range(max(0, keypoint_count - 1))]
    converted = []
    for edge in skeleton:
        if isinstance(edge, list) and len(edge) == 2:
            converted.append([max(0, int(edge[0]) - 1), max(0, int(edge[1]) - 1)])
    return converted


def _labelme_records(path: Path, schema: dict[str, Any]) -> list[dict[str, Any]]:
    records = []
    task_type = schema.get("task_type")
    for json_path in _json_files(path):
        data = json.loads(json_path.read_text(encoding="utf-8"))
        width = float(data.get("imageWidth") or 1)
        height = float(data.get("imageHeight") or 1)
        image_name = str(data.get("imagePath") or json_path.with_suffix("").name)
        instances = []
        for shape in data.get("shapes", []):
            label = str(shape.get("label") or "")
            points = shape.get("points") or []
            if shape.get("shape_type") == "rectangle" and len(points) >= 2:
                xs = [float(point[0]) for point in points[:2]]
                ys = [float(point[1]) for point in points[:2]]
                instances.append({"type": "box", "class_id": _class_id(schema, label), "bbox": _bbox_xyxy(min(xs), min(ys), max(xs), max(ys), width, height)})
            elif task_type == "segment" and len(points) >= 3:
                instances.append({"type": "polygon", "class_id": _class_id(schema, label), "points": [{"x": float(x) / width, "y": float(y) / height} for x, y in points]})
        records.append({"image": image_name.replace("\\", "/"), "instances": instances})
    return records


def _yolo_records(path: Path, schema: dict[str, Any]) -> list[dict[str, Any]]:
    label_files = sorted(path.glob("*.txt")) if path.is_dir() else [path]
    return [
        {"image": f"{label_path.stem}", "instances": parse_yolo_label(label_path, schema["task_type"], schema).get("instances", [])}
        for label_path in label_files
    ]


def _materialize_records(project: dict[str, Any], fmt: str, records: list[dict[str, Any]]) -> dict[str, Any]:
    by_name = {item["name"].replace("\\", "/").lower(): item for item in project.get("images", [])}
    by_base = {Path(item["name"]).name.lower(): item for item in project.get("images", [])}
    by_stem = {Path(item["name"]).stem.lower(): item for item in project.get("images", [])}
    matched = 0
    unmatched = 0
    for record in records:
        image_name = str(record.get("image") or "").replace("\\", "/")
        item = by_name.get(image_name.lower()) or by_base.get(Path(image_name).name.lower()) or by_stem.get(Path(image_name).stem.lower())
        if not item:
            unmatched += 1
            continue
        annotation = {"version": 1, "instances": record.get("instances", [])}
        if annotation["instances"]:
            write_json(annotation_path(project["id"], item["name"]), annotation)
            item["annotated"] = True
            matched += 1
    return {
        "annotation_format": fmt,
        "annotation_images": len(records),
        "matched_annotations": matched,
        "unmatched_annotations": unmatched,
    }
