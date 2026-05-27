from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from .storage import annotation_path, write_json
from .tasks import DEFAULT_COLORS, default_schema_for_task


def _labels(root: ET.Element) -> list[ET.Element]:
    return list(root.findall("./meta/task/labels/label"))


def schema_from_cvat_xml(path: Path, task_type: str) -> dict[str, Any]:
    root = ET.parse(path).getroot()
    schema = default_schema_for_task(task_type)
    labels = _labels(root)
    skeleton_labels = [label for label in labels if (label.findtext("type") or "").strip() == "skeleton"]
    if task_type == "pose" and skeleton_labels:
        parent = (skeleton_labels[0].findtext("name") or "object").strip()
        keypoints = [
            (label.findtext("name") or "").strip()
            for label in labels
            if (label.findtext("parent") or "").strip() == parent
        ]
        if keypoints:
            svg = html.unescape(skeleton_labels[0].findtext("svg") or "")
            skeleton = []
            for start, end in re.findall(r'data-node-from="([^"]+)".*?data-node-to="([^"]+)"', svg):
                if start in keypoints and end in keypoints:
                    skeleton.append([keypoints.index(start), keypoints.index(end)])
            schema.update({
                "classes": [{"id": 0, "name": parent, "color": skeleton_labels[0].findtext("color") or DEFAULT_COLORS[0]}],
                "keypoints": keypoints,
                "skeleton": skeleton or [[idx, idx + 1] for idx in range(len(keypoints) - 1)],
                "flip_idx": list(range(len(keypoints))),
            })
            return schema

    class_names = []
    for label in labels:
        name = (label.findtext("name") or "").strip()
        parent = (label.findtext("parent") or "").strip()
        if name and not parent:
            class_names.append(name)
    if class_names:
        schema["classes"] = [
            {"id": idx, "name": name, "color": DEFAULT_COLORS[idx % len(DEFAULT_COLORS)]}
            for idx, name in enumerate(class_names)
        ]
    return schema


def _class_id(schema: dict[str, Any], name: str) -> int:
    for cls in schema.get("classes", []):
        if str(cls.get("name")) == name:
            return int(cls.get("id", 0))
    return 0


def _bbox_from_points(points: list[dict[str, Any]]) -> dict[str, float]:
    visible = [point for point in points if point.get("v", 0) > 0]
    if not visible:
        return {"cx": 0.5, "cy": 0.5, "w": 0.01, "h": 0.01}
    xs = [float(point["x"]) for point in visible]
    ys = [float(point["y"]) for point in visible]
    left, right = min(xs), max(xs)
    top, bottom = min(ys), max(ys)
    padding = 0.01
    left = max(0.0, left - padding)
    right = min(1.0, right + padding)
    top = max(0.0, top - padding)
    bottom = min(1.0, bottom + padding)
    return {
        "cx": (left + right) / 2,
        "cy": (top + bottom) / 2,
        "w": max(0.004, right - left),
        "h": max(0.004, bottom - top),
    }


def _parse_points(text: str) -> list[tuple[float, float]]:
    pairs = []
    for raw in re.split(r"[;\s]+", text.strip()):
        if not raw:
            continue
        x, y = raw.split(",", 1)
        pairs.append((float(x), float(y)))
    return pairs


def _annotation_from_image(node: ET.Element, schema: dict[str, Any], task_type: str) -> dict[str, Any]:
    width = float(node.attrib.get("width") or 1)
    height = float(node.attrib.get("height") or 1)
    instances: list[dict[str, Any]] = []
    if task_type == "pose":
        keypoints = schema.get("keypoints", [])
        for skeleton in node.findall("skeleton"):
            by_name: dict[str, dict[str, Any]] = {}
            for point_node in skeleton.findall("points"):
                label = point_node.attrib.get("label", "")
                point_pairs = _parse_points(point_node.attrib.get("points", ""))
                if not point_pairs:
                    continue
                x, y = point_pairs[0]
                outside = point_node.attrib.get("outside") == "1"
                occluded = point_node.attrib.get("occluded") == "1"
                by_name[label] = {
                    "name": label,
                    "x": x / width,
                    "y": y / height,
                    "v": 0 if outside else 1 if occluded else 2,
                }
            points = [by_name.get(name, {"name": name, "x": 0, "y": 0, "v": 0}) for name in keypoints]
            instances.append({
                "type": "pose",
                "class_id": _class_id(schema, skeleton.attrib.get("label", "")),
                "bbox": _bbox_from_points(points),
                "keypoints": points,
            })
    elif task_type == "detect":
        for box in node.findall("box"):
            xtl = float(box.attrib.get("xtl", 0)) / width
            ytl = float(box.attrib.get("ytl", 0)) / height
            xbr = float(box.attrib.get("xbr", 0)) / width
            ybr = float(box.attrib.get("ybr", 0)) / height
            instances.append({
                "type": "box",
                "class_id": _class_id(schema, box.attrib.get("label", "")),
                "bbox": {"cx": (xtl + xbr) / 2, "cy": (ytl + ybr) / 2, "w": max(0.004, xbr - xtl), "h": max(0.004, ybr - ytl)},
            })
    elif task_type == "segment":
        for polygon in node.findall("polygon"):
            points = [{"x": x / width, "y": y / height} for x, y in _parse_points(polygon.attrib.get("points", ""))]
            if len(points) >= 3:
                instances.append({"type": "polygon", "class_id": _class_id(schema, polygon.attrib.get("label", "")), "points": points})
    return {"version": 1, "instances": instances}


def import_cvat_annotations(project: dict[str, Any], path: Path) -> dict[str, Any]:
    root = ET.parse(path).getroot()
    by_name = {item["name"].replace("\\", "/").lower(): item for item in project.get("images", [])}
    by_stem = {Path(item["name"]).stem.lower(): item for item in project.get("images", [])}
    matched = 0
    unmatched = 0
    task_type = project["schema"]["task_type"]
    for image_node in root.findall("image"):
        xml_name = image_node.attrib.get("name", "").replace("\\", "/")
        item = by_name.get(xml_name.lower()) or by_stem.get(Path(xml_name).stem.lower())
        if not item:
            unmatched += 1
            continue
        annotation = _annotation_from_image(image_node, project["schema"], task_type)
        if annotation["instances"]:
            write_json(annotation_path(project["id"], item["name"]), annotation)
            item["annotated"] = True
            matched += 1
    return {
        "annotation_format": "cvat_xml",
        "annotation_images": len(root.findall("image")),
        "matched_annotations": matched,
        "unmatched_annotations": unmatched,
    }
