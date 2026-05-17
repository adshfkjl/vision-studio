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


def split_project(project: dict[str, Any], train: float, val: float, test: float, seed: int) -> dict[str, Any]:
    total = train + val + test
    if total <= 0:
        raise ValueError("Split ratios must be positive")
    train_r, val_r, test_r = train / total, val / total, test / total

    images = []
    for item in project.get("images", []):
        ann = read_json(annotation_path(project["id"], item["name"]))
        label_path = yolo_label_path(project, item["name"])
        if (ann and ann.get("instances")) or (label_path and label_path.is_file()):
            images.append(item["name"])

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


def materialize_dataset(project: dict[str, Any], split: dict[str, Any] | None = None) -> MaterializedDataset:
    if split is None:
        split = project.get("split")
    if not split:
        split = split_project(project, 0.8, 0.15, 0.05, 42)

    root = project_dir(project["id"]) / "dataset"
    if root.exists():
        shutil.rmtree(root)
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
