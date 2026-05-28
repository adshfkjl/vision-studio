from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import storage as storage_module
from .annotation_import import import_annotation_source, merge_import_schema, schema_from_annotation_source
from .config import cors_allow_origins
from .datasets import materialize_dataset, materialize_preview, split_project
from .devices import available_devices
from .inference import resolve_image_path, resolve_model_path, run_prediction
from .jobs import control_training_job, export_onnx, list_jobs, load_job, start_training
from .storage import (
    APP_ROOT,
    DATA_ROOT,
    abs_path,
    annotation_path,
    annotations_dir,
    ensure_roots,
    generated_yolo_label_path,
    image_size,
    iter_images,
    list_projects,
    load_project,
    project_dir,
    project_image_path,
    predictions_dir,
    save_project,
    unique_project_id,
    write_json,
)
from .yolo import annotation_for_image, annotation_to_yolo, default_schema, image_has_label, schema_from_data_yaml
from .tasks import available_tasks, default_schema_for_task, get_task
from .validation import validate_project

app = FastAPI(title="Vision Studio", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allow_origins(),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIST = APP_ROOT / "frontend" / "dist"


class ImportProjectRequest(BaseModel):
    name: str
    task_type: str = Field(pattern="^(detect|segment|pose|classify|obb)$")
    image_dir: str
    label_dir: str | None = None
    data_yaml: str | None = None
    annotation_file: str | None = None
    annotation_format: str | None = None


class ImportAnnotationsRequest(BaseModel):
    annotation_path: str
    annotation_format: str | None = None


class CreateProjectRequest(BaseModel):
    name: str
    task_type: str = Field(pattern="^(detect|segment|pose|classify|obb)$")
    project_schema: dict[str, Any] | None = None


class SplitRequest(BaseModel):
    train: float = 0.8
    val: float = 0.15
    test: float = 0.05
    seed: int = 42


class TrainRequest(BaseModel):
    task_type: str | None = None
    model: str | None = None
    epochs: int = 100
    imgsz: int = 960
    batch: int = 4
    device: str = "auto"
    lr0: float = 0.01
    optimizer: str = "AdamW"
    patience: int = 30
    seed: int = 42
    name: str = "studio_train"


class PredictRequest(BaseModel):
    project_id: str | None = None
    image_name: str | None = None
    image_path: str | None = None
    model_path: str | None = None
    job_id: str | None = None
    artifact_name: str | None = None
    conf: float = 0.25
    iou: float = 0.7
    imgsz: int | None = None
    device: str = "auto"


def blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def save_uploaded_annotation(upload: UploadFile, target_dir: Path) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = Path(upload.filename or "annotations").name
    if not filename:
        filename = "annotations"
    target = target_dir / filename
    stem = target.stem or "annotations"
    suffix = target.suffix
    idx = 2
    while target.exists():
        target = target_dir / f"{stem}-{idx}{suffix}"
        idx += 1
    with target.open("wb") as fh:
        shutil.copyfileobj(upload.file, fh)
    return target


@app.on_event("startup")
def startup() -> None:
    ensure_roots()


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "data_root": str(DATA_ROOT)}


@app.get("/")
def frontend_index() -> FileResponse:
    index = FRONTEND_DIST / "index.html"
    if not index.is_file():
        raise HTTPException(404, "Frontend has not been built. Run npm run build in vision_studio/frontend.")
    return FileResponse(index)


@app.get("/api/projects")
def get_projects() -> list[dict[str, Any]]:
    return list_projects()


@app.get("/api/jobs")
def get_jobs(project_id: str | None = None, kind: str | None = None) -> dict[str, Any]:
    return {"items": list_jobs(project_id=project_id, kind=kind)}


@app.get("/api/devices")
def get_devices() -> dict[str, Any]:
    return available_devices()


@app.get("/api/tasks")
def get_tasks() -> list[dict[str, Any]]:
    return available_tasks()


@app.post("/api/projects")
def create_project(req: CreateProjectRequest) -> dict[str, Any]:
    ensure_roots()
    task = get_task(req.task_type)
    project_id = unique_project_id(req.name)
    pdir = project_dir(project_id)
    for child in ("annotations", "splits", "runs", "exports", "uploads", "yolo_labels"):
        (pdir / child).mkdir(parents=True, exist_ok=True)

    schema = req.project_schema or default_schema(req.task_type)
    schema.setdefault("task_type", req.task_type)
    schema.setdefault("classes", default_schema_for_task(req.task_type)["classes"])
    schema.setdefault("keypoints", default_schema_for_task(req.task_type)["keypoints"])
    schema.setdefault("skeleton", default_schema_for_task(req.task_type)["skeleton"])
    schema.setdefault("flip_idx", default_schema_for_task(req.task_type)["flip_idx"])

    project = {
        "id": project_id,
        "name": req.name,
        "task_type": task["task_type"],
        "image_dir": str(pdir / "uploads" / "images"),
        "label_dir": None,
        "data_yaml": None,
        "schema": schema,
        "images": [],
        "split": None,
    }
    (pdir / "uploads" / "images").mkdir(parents=True, exist_ok=True)
    save_project(project)
    return project


@app.post("/api/projects/import")
def import_project(req: ImportProjectRequest) -> dict[str, Any]:
    ensure_roots()
    task = get_task(req.task_type)
    image_dir = abs_path(req.image_dir)
    label_dir = abs_path(req.label_dir)
    data_yaml = abs_path(req.data_yaml)
    annotation_file = abs_path(req.annotation_file)
    if image_dir is None or not image_dir.is_dir():
        raise HTTPException(400, f"Image directory not found: {req.image_dir}")
    if label_dir is not None and not label_dir.is_dir():
        raise HTTPException(400, f"Label directory not found: {req.label_dir}")
    if annotation_file is not None and not annotation_file.is_file():
        raise HTTPException(400, f"Annotation file not found: {req.annotation_file}")

    project_id = unique_project_id(req.name)
    pdir = project_dir(project_id)
    for child in ("annotations", "splits", "runs", "exports"):
        (pdir / child).mkdir(parents=True, exist_ok=True)

    images = []
    for image in iter_images(image_dir):
        try:
            w, h = image_size(image)
        except Exception:
            continue
        rel = str(image.relative_to(image_dir)).replace("\\", "/")
        images.append({"name": rel, "path": str(image), "width": w, "height": h, "annotated": False})

    if annotation_file:
        try:
            schema = schema_from_annotation_source(annotation_file, req.task_type, req.annotation_format)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
    else:
        schema = schema_from_data_yaml(data_yaml, req.task_type, image_dir=image_dir)
    project = {
        "id": project_id,
        "name": req.name,
        "task_type": task["task_type"],
        "image_dir": str(image_dir),
        "label_dir": str(label_dir) if label_dir else None,
        "data_yaml": str(data_yaml) if data_yaml else None,
        "schema": schema,
        "images": images,
        "split": None,
    }
    if annotation_file:
        try:
            project["import_summary"] = import_annotation_source(project, annotation_file, req.annotation_format)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
    elif label_dir is not None:
        stems = {Path(item["name"]).stem.lower() for item in images}
        labels = sorted(label_dir.glob("*.txt"))
        matched = {label.stem.lower() for label in labels if label.stem.lower() in stems}
        for item in images:
            if Path(item["name"]).stem.lower() in matched:
                item["annotated"] = True
        project["import_summary"] = {
            "annotation_format": "yolo_labels",
            "annotation_images": len(labels),
            "matched_annotations": len(matched),
            "unmatched_annotations": max(0, len(labels) - len(matched)),
        }
    save_project(project)
    return project


@app.post("/api/projects/import-file")
def import_project_file(
    name: str = Form(...),
    task_type: str = Form(...),
    image_dir: str = Form(...),
    label_dir: str | None = Form(None),
    data_yaml: str | None = Form(None),
    annotation_format: str | None = Form(None),
    annotation_file: UploadFile = File(...),
) -> dict[str, Any]:
    annotation_path = save_uploaded_annotation(annotation_file, storage_module.DATA_ROOT / "import_uploads")
    req = ImportProjectRequest(
        name=name,
        task_type=task_type,
        image_dir=image_dir,
        label_dir=blank_to_none(label_dir),
        data_yaml=blank_to_none(data_yaml),
        annotation_file=str(annotation_path),
        annotation_format=blank_to_none(annotation_format),
    )
    return import_project(req)


@app.get("/api/projects/{project_id}/schema")
def get_schema(project_id: str) -> dict[str, Any]:
    return load_project(project_id)["schema"]


@app.put("/api/projects/{project_id}/schema")
def put_schema(project_id: str, schema: dict[str, Any]) -> dict[str, Any]:
    project = load_project(project_id)
    if "classes" not in schema or not schema["classes"]:
        raise HTTPException(400, "At least one class is required")
    schema.setdefault("task_type", project["schema"]["task_type"])
    schema.setdefault("keypoints", [])
    schema.setdefault("skeleton", [])
    schema.setdefault("flip_idx", list(range(len(schema.get("keypoints", [])))))
    project["schema"] = schema
    project["task_type"] = schema["task_type"]
    save_project(project)
    return schema


@app.get("/api/projects/{project_id}/images")
def get_images(project_id: str, offset: int = 0, limit: int = 100) -> dict[str, Any]:
    project = load_project(project_id)
    items = project.get("images", [])
    for item in items:
        item["annotated"] = image_has_label(project, item["name"])
    return {"total": len(items), "items": items[offset : offset + limit]}


@app.post("/api/projects/{project_id}/images/upload")
async def upload_images(project_id: str, files: list[UploadFile] = File(...)) -> dict[str, Any]:
    project = load_project(project_id)
    upload_dir = project_dir(project_id) / "uploads" / "images"
    upload_dir.mkdir(parents=True, exist_ok=True)
    added = []
    existing_names = {item["name"] for item in project.get("images", [])}
    for upload in files:
        suffix = Path(upload.filename or "").suffix.lower()
        if suffix not in {".bmp", ".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}:
            continue
        base_name = Path(upload.filename or "image").name
        target = upload_dir / base_name
        stem = target.stem
        idx = 2
        while target.exists() or f"uploaded/{target.name}" in existing_names:
            target = upload_dir / f"{stem}-{idx}{suffix}"
            idx += 1
        with target.open("wb") as fh:
            shutil.copyfileobj(upload.file, fh)
        w, h = image_size(target)
        item = {"name": f"uploaded/{target.name}", "path": str(target), "width": w, "height": h, "annotated": False}
        project.setdefault("images", []).append(item)
        added.append(item)
        existing_names.add(item["name"])
    save_project(project)
    return {"added": added, "total": len(project.get("images", []))}


@app.delete("/api/projects/{project_id}/images/{image_name:path}")
def delete_image(project_id: str, image_name: str) -> dict[str, Any]:
    project = load_project(project_id)
    before = len(project.get("images", []))
    project["images"] = [item for item in project.get("images", []) if item.get("name") != image_name]
    if len(project["images"]) == before:
        raise HTTPException(404, "Image not found")
    ann_path = annotation_path(project_id, image_name)
    if ann_path.exists():
        ann_path.unlink()
    label_path = generated_yolo_label_path(project_id, image_name)
    if label_path.exists():
        label_path.unlink()
    save_project(project)
    return {"removed": image_name, "total": len(project.get("images", []))}


@app.get("/api/projects/{project_id}/images/{image_name:path}")
def get_image(project_id: str, image_name: str) -> FileResponse:
    project = load_project(project_id)
    path = project_image_path(project, image_name)
    return FileResponse(path)


@app.get("/api/projects/{project_id}/annotations/{image_name:path}")
def get_annotation(project_id: str, image_name: str) -> dict[str, Any]:
    project = load_project(project_id)
    image = project_image_path(project, image_name)
    w, h = image_size(image)
    return {"image": image_name, "width": w, "height": h, "annotation": annotation_for_image(project, image_name)}


@app.put("/api/projects/{project_id}/annotations/{image_name:path}")
def put_annotation(project_id: str, image_name: str, annotation: dict[str, Any]) -> dict[str, Any]:
    project = load_project(project_id)
    path = annotation_path(project_id, image_name)
    write_json(path, annotation)
    label_path = generated_yolo_label_path(project_id, image_name)
    label_path.parent.mkdir(parents=True, exist_ok=True)
    label_path.write_text(
        annotation_to_yolo(annotation, project["schema"]),
        encoding="utf-8",
    )
    for item in project.get("images", []):
        if item["name"] == image_name:
            item["annotated"] = True
            break
    save_project(project)
    return {"ok": True, "annotation_path": str(path)}


@app.post("/api/projects/{project_id}/annotations/import")
def import_project_annotations(project_id: str, req: ImportAnnotationsRequest) -> dict[str, Any]:
    project = load_project(project_id)
    annotation_source = abs_path(req.annotation_path)
    if annotation_source is None or not annotation_source.exists():
        raise HTTPException(400, f"Annotation path not found: {req.annotation_path}")
    try:
        imported_schema = schema_from_annotation_source(annotation_source, project["schema"]["task_type"], req.annotation_format)
        project["schema"] = merge_import_schema(project["schema"], imported_schema)
        project["import_summary"] = import_annotation_source(project, annotation_source, req.annotation_format)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    save_project(project)
    return {"project": project, "import_summary": project["import_summary"]}


@app.post("/api/projects/{project_id}/annotations/import-file")
def import_project_annotation_file(
    project_id: str,
    annotation_format: str | None = Form(None),
    annotation_file: UploadFile = File(...),
) -> dict[str, Any]:
    annotation_source = save_uploaded_annotation(annotation_file, project_dir(project_id) / "imports")
    req = ImportAnnotationsRequest(annotation_path=str(annotation_source), annotation_format=blank_to_none(annotation_format))
    return import_project_annotations(project_id, req)


@app.post("/api/projects/{project_id}/split")
def post_split(project_id: str, req: SplitRequest) -> dict[str, Any]:
    project = load_project(project_id)
    return split_project(project, req.train, req.val, req.test, req.seed)


@app.get("/api/projects/{project_id}/validation")
def get_validation(project_id: str) -> dict[str, Any]:
    return validate_project(load_project(project_id))


@app.post("/api/projects/{project_id}/train")
def post_train(project_id: str, req: TrainRequest) -> dict[str, Any]:
    project = load_project(project_id)
    validation = validate_project(project)
    if not validation["train_ready"]:
        raise HTTPException(400, {"message": "Project validation failed", "validation": validation})
    if not project.get("split"):
        split_project(project, 0.8, 0.15, 0.05, req.seed)
    params = req.model_dump()
    params["task_type"] = params["task_type"] or project["schema"]["task_type"]
    return start_training(project_id, params)


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> dict[str, Any]:
    return load_job(job_id)


@app.post("/api/jobs/{job_id}/pause")
def pause_job(job_id: str) -> dict[str, Any]:
    try:
        return control_training_job(job_id, "pause")
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/jobs/{job_id}/resume")
def resume_job(job_id: str) -> dict[str, Any]:
    try:
        return control_training_job(job_id, "resume")
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/jobs/{job_id}/stop")
def stop_job(job_id: str) -> dict[str, Any]:
    try:
        return control_training_job(job_id, "stop")
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/jobs/{job_id}/export/onnx")
def post_export_onnx(job_id: str) -> dict[str, Any]:
    try:
        return export_onnx(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc


@app.post("/api/predict")
def post_predict(req: PredictRequest) -> dict[str, Any]:
    try:
        model_path = resolve_model_path(req.model_path, req.job_id, req.artifact_name)
        image_path = resolve_image_path(req.project_id, req.image_name, req.image_path)
        schema = load_project(req.project_id)["schema"] if req.project_id else None
        result = run_prediction(
            model_path,
            image_path,
            conf=req.conf,
            iou=req.iou,
            imgsz=req.imgsz,
            device=req.device,
            schema=schema,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    preview_name = Path(result["preview_path"]).name
    return {**result, "preview_url": f"/api/predictions/{preview_name}"}


@app.get("/api/predictions/{preview_name}")
def get_prediction_preview(preview_name: str) -> FileResponse:
    path = predictions_dir() / Path(preview_name).name
    if not path.is_file():
        raise HTTPException(404, "Prediction preview not found")
    return FileResponse(path, filename=path.name)


@app.get("/api/artifacts/{job_id}/{artifact_name}")
def get_artifact(job_id: str, artifact_name: str) -> FileResponse:
    job = load_job(job_id)
    artifact = job.get("artifacts", {}).get(artifact_name)
    if not artifact:
        raise HTTPException(404, "Artifact not found")
    path_text = artifact.get("path") if isinstance(artifact, dict) else artifact
    path = Path(path_text)
    if not path.is_file():
        raise HTTPException(404, "Artifact file missing")
    return FileResponse(path, filename=path.name)


@app.post("/api/projects/{project_id}/materialize")
def post_materialize(project_id: str) -> dict[str, Any]:
    project = load_project(project_id)
    validation = validate_project(project)
    if not validation["train_ready"]:
        raise HTTPException(400, {"message": "Project validation failed", "validation": validation})
    dataset = materialize_dataset(project)
    preview = materialize_preview(dataset.root, dataset.data_yaml)
    preview["validation"] = validation
    return preview


@app.post("/api/demo/import-current")
def import_current_demo() -> dict[str, Any]:
    image_dir = APP_ROOT / "images"
    label_dir = APP_ROOT / "labels"
    req = ImportProjectRequest(
        name="current-pose",
        task_type="pose",
        image_dir=str(image_dir),
        label_dir=str(label_dir),
        data_yaml=str(APP_ROOT / "yolo-pose" / "data.yaml"),
    )
    return import_project(req)


if FRONTEND_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="frontend-assets")
