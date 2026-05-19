from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image

IMAGE_EXTS = {".bmp", ".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}

PACKAGE_ROOT = Path(__file__).resolve().parent
BACKEND_ROOT = PACKAGE_ROOT.parent
APP_ROOT = BACKEND_ROOT.parent
DATA_ROOT = APP_ROOT / "vision_studio_data"
PROJECTS_ROOT = DATA_ROOT / "projects"
JOBS_ROOT = DATA_ROOT / "jobs"


def ensure_roots() -> None:
    for path in (DATA_ROOT, PROJECTS_ROOT, JOBS_ROOT):
        path.mkdir(parents=True, exist_ok=True)


def slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_.-]+", "-", value.strip()).strip("-._")
    return cleaned.lower() or "project"


def unique_project_id(name: str) -> str:
    base = slugify(name)
    candidate = base
    idx = 2
    while (PROJECTS_ROOT / candidate).exists():
        candidate = f"{base}-{idx}"
        idx += 1
    return candidate


def project_dir(project_id: str) -> Path:
    return PROJECTS_ROOT / project_id


def config_path(project_id: str) -> Path:
    return project_dir(project_id) / "project.json"


def annotations_dir(project_id: str) -> Path:
    return project_dir(project_id) / "annotations"


def yolo_labels_dir(project_id: str) -> Path:
    return project_dir(project_id) / "yolo_labels"


def splits_dir(project_id: str) -> Path:
    return project_dir(project_id) / "splits"


def runs_dir(project_id: str) -> Path:
    return project_dir(project_id) / "runs"


def exports_dir(project_id: str) -> Path:
    return project_dir(project_id) / "exports"


def abs_path(path_text: str | None, base: Path = APP_ROOT) -> Path | None:
    if not path_text:
        return None
    path = Path(path_text)
    if not path.is_absolute():
        path = base / path
    return path.resolve()


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_project(project_id: str) -> dict[str, Any]:
    data = read_json(config_path(project_id))
    if data is None:
        raise FileNotFoundError(f"Project not found: {project_id}")
    return data


def save_project(project: dict[str, Any]) -> None:
    write_json(config_path(project["id"]), project)


def list_projects() -> list[dict[str, Any]]:
    ensure_roots()
    projects: list[dict[str, Any]] = []
    for path in sorted(PROJECTS_ROOT.glob("*/project.json")):
        try:
            data = read_json(path)
            if data:
                projects.append(data)
        except json.JSONDecodeError:
            continue
    return projects


def iter_images(image_dir: Path) -> list[Path]:
    if not image_dir.is_dir():
        return []
    return sorted(p for p in image_dir.rglob("*") if p.is_file() and p.suffix.lower() in IMAGE_EXTS)


def image_size(path: Path) -> tuple[int, int]:
    with Image.open(path) as img:
        return img.size


def annotation_path(project_id: str, image_name: str) -> Path:
    return annotations_dir(project_id) / f"{Path(image_name).stem}.json"


def yolo_label_path(project: dict[str, Any], image_name: str) -> Path | None:
    label_dir = abs_path(project.get("label_dir"))
    if label_dir is None:
        return None
    return label_dir / f"{Path(image_name).stem}.txt"


def project_image_path(project: dict[str, Any], image_name: str) -> Path:
    for item in project.get("images", []):
        if item.get("name") == image_name and item.get("path"):
            direct = Path(item["path"])
            if direct.is_file():
                return direct
    image_dir = abs_path(project.get("image_dir"))
    if image_dir is None:
        raise FileNotFoundError("Project has no image_dir")
    candidate = image_dir / image_name
    if candidate.is_file():
        return candidate
    matches = [p for p in image_dir.rglob(image_name) if p.is_file()]
    if not matches:
        raise FileNotFoundError(image_name)
    return matches[0]


def copy_or_link(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


@dataclass
class MaterializedDataset:
    root: Path
    data_yaml: Path
