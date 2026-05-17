from __future__ import annotations

from pathlib import Path
from typing import Any

from .storage import annotation_path, project_image_path, read_json
from .yolo import annotation_for_image


def _issue(severity: str, image: str | None, code: str, message: str) -> dict[str, Any]:
    return {"severity": severity, "image": image, "code": code, "message": message}


def _in_unit(value: Any) -> bool:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return 0.0 <= number <= 1.0


def _load_annotation(project: dict[str, Any], image_name: str) -> dict[str, Any]:
    overrides = project.get("_annotation_overrides") or {}
    if image_name in overrides:
        return overrides[image_name]
    saved = read_json(annotation_path(project["id"], image_name))
    if saved is not None:
        return saved
    return annotation_for_image(project, image_name)


def validate_project(project: dict[str, Any]) -> dict[str, Any]:
    schema = project.get("schema") or {}
    task_type = schema.get("task_type") or project.get("task_type")
    class_ids = {int(cls.get("id", 0)) for cls in schema.get("classes", [])}
    keypoints = [str(name) for name in schema.get("keypoints", [])]
    issues: list[dict[str, Any]] = []
    class_counts = {str(class_id): 0 for class_id in sorted(class_ids)}
    annotated_images = 0
    empty_annotations = 0
    invalid_images: set[str] = set()

    images = project.get("images", [])
    for image in images:
        image_name = image.get("name", "")
        try:
            project_image_path(project, image_name)
        except Exception:
            issues.append(_issue("error", image_name, "image_missing", "Image file cannot be found."))
            invalid_images.add(image_name)
            continue

        try:
            annotation = _load_annotation(project, image_name)
        except Exception as exc:
            issues.append(_issue("error", image_name, "annotation_load", f"Annotation could not be loaded: {exc}"))
            invalid_images.add(image_name)
            continue

        instances = annotation.get("instances", []) if isinstance(annotation, dict) else []
        if not instances:
            empty_annotations += 1
            issues.append(_issue("warning", image_name, "empty_annotation", "Image has no labeled instances."))
            continue

        annotated_images += 1
        image_has_error = False
        for index, instance in enumerate(instances):
            class_id = int(instance.get("class_id", -1))
            if class_id not in class_ids:
                issues.append(_issue("error", image_name, "class_id", f"Instance {index + 1} has unknown class id {class_id}."))
                image_has_error = True
            else:
                key = str(class_id)
                class_counts[key] = class_counts.get(key, 0) + 1

            if task_type == "segment":
                points = instance.get("points", [])
                if instance.get("type") != "polygon" or len(points) < 3:
                    issues.append(_issue("error", image_name, "polygon_points", f"Instance {index + 1} needs at least three polygon points."))
                    image_has_error = True
                for point in points:
                    if not _in_unit(point.get("x")) or not _in_unit(point.get("y")):
                        issues.append(_issue("error", image_name, "coordinate_range", f"Instance {index + 1} has a polygon point outside 0..1."))
                        image_has_error = True
                        break

            if task_type == "pose":
                bbox = instance.get("bbox") or {}
                for field in ("cx", "cy", "w", "h"):
                    if not _in_unit(bbox.get(field)):
                        issues.append(_issue("error", image_name, "coordinate_range", f"Instance {index + 1} bbox {field} is outside 0..1."))
                        image_has_error = True
                        break
                actual = {str(point.get("name")): point for point in instance.get("keypoints", [])}
                if set(actual.keys()) != set(keypoints):
                    issues.append(_issue("error", image_name, "pose_keypoints", f"Instance {index + 1} keypoints do not match schema."))
                    image_has_error = True
                for point in actual.values():
                    if not _in_unit(point.get("x")) or not _in_unit(point.get("y")):
                        issues.append(_issue("error", image_name, "coordinate_range", f"Instance {index + 1} has a keypoint outside 0..1."))
                        image_has_error = True
                        break
                    if int(point.get("v", -1)) not in (0, 1, 2):
                        issues.append(_issue("error", image_name, "visibility", f"Instance {index + 1} has invalid keypoint visibility."))
                        image_has_error = True
                        break

        if image_has_error:
            invalid_images.add(image_name)

    has_errors = any(issue["severity"] == "error" for issue in issues)
    has_warnings = any(issue["severity"] == "warning" for issue in issues)
    train_ready = bool(images) and annotated_images > 0 and not has_errors
    split_ready = annotated_images > 0 and not has_errors
    status = "fail" if has_errors or not train_ready else ("warning" if has_warnings else "pass")
    if not images:
        issues.append(_issue("error", None, "no_images", "Project has no images."))
        status = "fail"
    elif annotated_images == 0:
        issues.append(_issue("error", None, "no_labels", "Project has no labeled images."))
        status = "fail"

    return {
        "status": status,
        "summary": {
            "total_images": len(images),
            "annotated_images": annotated_images,
            "empty_annotations": empty_annotations,
            "invalid_images": len(invalid_images),
        },
        "issues": issues,
        "class_counts": class_counts,
        "split_ready": split_ready,
        "train_ready": train_ready,
    }
