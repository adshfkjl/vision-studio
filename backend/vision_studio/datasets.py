from __future__ import annotations

import random
import shutil
from pathlib import Path
from typing import Any

from .storage import (
    MaterializedDataset,
    annotation_path,
    copy_or_link,
    project_dir,
    project_image_path,
    read_json,
    save_project,
    splits_dir,
    write_json,
    yolo_label_path,
)
from .yolo import annotation_for_image, annotation_to_yolo, data_yaml_text
from .yolo import classification_class_name, image_has_label


def labeled_image_names(project: dict[str, Any]) -> list[str]:
    images = []
    for item in project.get("images", []):
        image_name = item["name"]
        ann = read_json(annotation_path(project["id"], image_name))
        label_path = yolo_label_path(project, image_name)
        if (ann and ann.get("instances")) or (label_path and label_path.is_file()) or image_has_label(project, image_name):
            images.append(image_name)
    return images


def split_project(project: dict[str, Any], train: float, val: float, test: float, seed: int) -> dict[str, Any]:
    total = train + val + test
    if total <= 0:
        raise ValueError("Split ratios must be positive")
    train_r, val_r, test_r = train / total, val / total, test / total

    images = labeled_image_names(project)

    rng = random.Random(seed)
    rng.shuffle(images)
    n = len(images)
    n_train = int(round(n * train_r))
    n_val = int(round(n * val_r))
    if n_train + n_val > n:
        n_val = max(0, n - n_train)
    split = {
        "train": images[:n_train],
        "val": images[n_train : n_train + n_val],
        "test": images[n_train + n_val :] if test_r > 0 else [],
        "ratios": {"train": train, "val": val, "test": test},
        "seed": seed,
    }
    write_json(splits_dir(project["id"]) / "current.json", split)
    project["split"] = split
    save_project(project)
    return split


def refresh_split(project: dict[str, Any], split: dict[str, Any]) -> dict[str, Any]:
    labeled = labeled_image_names(project)
    labeled_set = set(labeled)
    refreshed: dict[str, Any] = {}
    assigned: set[str] = set()
    changed = False

    for subset in ("train", "val", "test"):
        refreshed_subset = []
        for image_name in split.get(subset, []):
            if image_name in labeled_set and image_name not in assigned:
                refreshed_subset.append(image_name)
                assigned.add(image_name)
            else:
                changed = True
        refreshed[subset] = refreshed_subset

    missing = [image_name for image_name in labeled if image_name not in assigned]
    if missing:
        refreshed["train"].extend(missing)
        changed = True

    for key in ("ratios", "seed"):
        if key in split:
            refreshed[key] = split[key]

    if changed:
        project["split"] = refreshed
        write_json(splits_dir(project["id"]) / "current.json", refreshed)
        save_project(project)
    return refreshed


def materialize_dataset(project: dict[str, Any], split: dict[str, Any] | None = None) -> MaterializedDataset:
    if split is None:
        split = project.get("split")
    if not split:
        split = split_project(project, 0.8, 0.15, 0.05, 42)
    elif split is project.get("split"):
        split = refresh_split(project, split)

    root = project_dir(project["id"]) / "dataset"
    if root.exists():
        shutil.rmtree(root)
    if project["schema"]["task_type"] == "classify":
        for subset in ("train", "val", "test"):
            for image_name in split.get(subset, []):
                class_name = classification_class_name(image_name)
                if not class_name:
                    continue
                src = project_image_path(project, image_name)
                copy_or_link(src, root / subset / class_name / src.name)
        data_yaml = root / "data.yaml"
        data_yaml.write_text(data_yaml_text(project, root), encoding="utf-8")
        return MaterializedDataset(root=root, data_yaml=data_yaml)
    for subset in ("train", "val", "test"):
        (root / "images" / subset).mkdir(parents=True, exist_ok=True)
        (root / "labels" / subset).mkdir(parents=True, exist_ok=True)
        for image_name in split.get(subset, []):
            src = project_image_path(project, image_name)
            copy_or_link(src, root / "images" / subset / src.name)
            ann = read_json(annotation_path(project["id"], image_name))
            if ann is None:
                ann = annotation_for_image(project, image_name)
            yolo_text = annotation_to_yolo(ann, project["schema"])
            (root / "labels" / subset / f"{Path(image_name).stem}.txt").write_text(yolo_text, encoding="utf-8")

    data_yaml = root / "data.yaml"
    data_yaml.write_text(data_yaml_text(project, root), encoding="utf-8")
    return MaterializedDataset(root=root, data_yaml=data_yaml)


def materialize_preview(root: Path, data_yaml: Path) -> dict[str, Any]:
    splits: dict[str, dict[str, int]] = {}
    missing_labels = 0
    sample_labels: list[dict[str, str]] = []
    if (root / "train").is_dir() and not (root / "images").is_dir():
        for subset in ("train", "val", "test"):
            subset_dir = root / subset
            images = sorted(p for p in subset_dir.rglob("*") if p.is_file()) if subset_dir.is_dir() else []
            splits[subset] = {"images": len(images), "labels": len(images)}
        return {
            "root": str(root),
            "data_yaml_path": str(data_yaml),
            "data_yaml": data_yaml.read_text(encoding="utf-8") if data_yaml.is_file() else "",
            "splits": splits,
            "missing_labels": 0,
            "sample_labels": sample_labels,
        }
    for subset in ("train", "val", "test"):
        image_dir = root / "images" / subset
        label_dir = root / "labels" / subset
        images = sorted(p for p in image_dir.glob("*") if p.is_file()) if image_dir.is_dir() else []
        labels = sorted(p for p in label_dir.glob("*.txt")) if label_dir.is_dir() else []
        label_stems = {p.stem for p in labels}
        missing_labels += sum(1 for image in images if image.stem not in label_stems)
        splits[subset] = {"images": len(images), "labels": len(labels)}
        for label in labels:
            if len(sample_labels) >= 5:
                break
            text = label.read_text(encoding="utf-8").strip()
            sample_labels.append({"subset": subset, "name": label.name, "text": text})
    return {
        "root": str(root),
        "data_yaml_path": str(data_yaml),
        "data_yaml": data_yaml.read_text(encoding="utf-8") if data_yaml.is_file() else "",
        "splits": splits,
        "missing_labels": missing_labels,
        "sample_labels": sample_labels,
    }
