import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image

from vision_studio.main import app
from vision_studio.storage import annotation_path, generated_yolo_label_path, read_json, write_json


def write_project(projects_root: Path, image_path: Path) -> None:
    project_dir = projects_root / "sample-project"
    project_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        project_dir / "project.json",
        {
            "id": "sample-project",
            "name": "Sample Project",
            "task_type": "detect",
            "image_dir": str(image_path.parent),
            "label_dir": None,
            "data_yaml": None,
            "schema": {
                "task_type": "detect",
                "classes": [{"id": 0, "name": "stem", "color": "#0f766e"}],
                "keypoints": [],
                "skeleton": [],
                "flip_idx": [],
            },
            "images": [
                {
                    "name": image_path.name,
                    "path": str(image_path),
                    "width": 64,
                    "height": 48,
                    "annotated": False,
                }
            ],
            "split": None,
        },
    )


def write_multi_image_project(projects_root: Path, image_paths: list[Path]) -> None:
    project_dir = projects_root / "sample-project"
    project_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        project_dir / "project.json",
        {
            "id": "sample-project",
            "name": "Sample Project",
            "task_type": "detect",
            "image_dir": str(image_paths[0].parent),
            "label_dir": None,
            "data_yaml": None,
            "schema": {
                "task_type": "detect",
                "classes": [{"id": 0, "name": "stem", "color": "#0f766e"}],
                "keypoints": [],
                "skeleton": [],
                "flip_idx": [],
            },
            "images": [
                {
                    "name": image_path.name,
                    "path": str(image_path),
                    "width": 64,
                    "height": 48,
                    "annotated": False,
                }
                for image_path in image_paths
            ],
            "split": None,
        },
    )


def write_job(jobs_root: Path, model_path: Path) -> None:
    job_dir = jobs_root / "train-job"
    job_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        job_dir / "job.json",
        {
            "id": "train-job",
            "project_id": "sample-project",
            "kind": "train",
            "status": "completed",
            "params": {"name": "studio_train"},
            "artifacts": {"best.pt": {"path": str(model_path), "size": model_path.stat().st_size}},
            "error": None,
        },
    )
    (job_dir / "log.txt").write_text("[studio] Training completed\n", encoding="utf-8")


class PredictionApiTests(unittest.TestCase):
    def test_lists_completed_model_artifacts_for_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data_root = root / "data"
            projects_root = data_root / "projects"
            jobs_root = data_root / "jobs"
            image_dir = root / "images"
            image_dir.mkdir()
            image_path = image_dir / "one.jpg"
            Image.new("RGB", (64, 48), "white").save(image_path)
            model_path = root / "best.pt"
            model_path.write_bytes(b"model")
            write_project(projects_root, image_path)
            write_job(jobs_root, model_path)

            with patch("vision_studio.storage.DATA_ROOT", data_root), patch("vision_studio.storage.PROJECTS_ROOT", projects_root), patch("vision_studio.storage.JOBS_ROOT", jobs_root), patch("vision_studio.jobs.JOBS_ROOT", jobs_root):
                response = TestClient(app).get("/api/jobs", params={"project_id": "sample-project", "kind": "train"})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["items"][0]["id"], "train-job")
        self.assertEqual(data["items"][0]["artifacts"]["best.pt"]["path"], str(model_path))

    def test_predicts_project_image_with_trained_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data_root = root / "data"
            projects_root = data_root / "projects"
            jobs_root = data_root / "jobs"
            image_dir = root / "images"
            image_dir.mkdir()
            image_path = image_dir / "one.jpg"
            Image.new("RGB", (64, 48), "white").save(image_path)
            model_path = root / "best.pt"
            model_path.write_bytes(b"model")
            preview_path = data_root / "predictions" / "preview.jpg"
            preview_path.parent.mkdir(parents=True, exist_ok=True)
            Image.new("RGB", (64, 48), "white").save(preview_path)
            write_project(projects_root, image_path)
            write_job(jobs_root, model_path)

            fake_prediction = {
                "preview_path": str(preview_path),
                "image": {"name": "one.jpg", "width": 64, "height": 48},
                "instances": [
                    {
                        "type": "box",
                        "class_id": 0,
                        "class_name": "stem",
                        "confidence": 0.91,
                        "bbox": {"cx": 0.5, "cy": 0.5, "w": 0.25, "h": 0.25},
                    }
                ],
                "summary": {"total": 1, "by_class": {"stem": 1}},
            }

            with patch("vision_studio.storage.DATA_ROOT", data_root), patch("vision_studio.storage.PROJECTS_ROOT", projects_root), patch("vision_studio.storage.JOBS_ROOT", jobs_root), patch("vision_studio.jobs.JOBS_ROOT", jobs_root), patch("vision_studio.main.run_prediction", return_value=fake_prediction, create=True):
                response = TestClient(app).post(
                    "/api/predict",
                    json={
                        "project_id": "sample-project",
                        "image_name": "one.jpg",
                        "job_id": "train-job",
                        "artifact_name": "best.pt",
                        "conf": 0.4,
                        "iou": 0.7,
                    },
                )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["instances"][0]["class_name"], "stem")
        self.assertEqual(data["summary"]["total"], 1)
        self.assertTrue(data["preview_url"].startswith("/api/predictions/"))

    def test_prelabels_only_empty_project_images_from_trained_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data_root = root / "data"
            projects_root = data_root / "projects"
            jobs_root = data_root / "jobs"
            image_dir = root / "images"
            image_dir.mkdir()
            existing_path = image_dir / "existing.jpg"
            empty_path = image_dir / "empty.jpg"
            Image.new("RGB", (64, 48), "white").save(existing_path)
            Image.new("RGB", (64, 48), "white").save(empty_path)
            model_path = root / "best.pt"
            model_path.write_bytes(b"model")
            write_multi_image_project(projects_root, [existing_path, empty_path])
            write_job(jobs_root, model_path)

            existing_annotation = {
                "version": 1,
                "instances": [
                    {
                        "type": "box",
                        "class_id": 0,
                        "bbox": {"cx": 0.1, "cy": 0.2, "w": 0.3, "h": 0.4},
                    }
                ],
            }
            existing_ann_path = projects_root / "sample-project" / "annotations" / "existing.json"
            write_json(existing_ann_path, existing_annotation)

            fake_prediction = {
                "preview_path": str(data_root / "predictions" / "ignored.jpg"),
                "image": {"name": "empty.jpg", "width": 64, "height": 48},
                "instances": [
                    {
                        "type": "box",
                        "class_id": 0,
                        "class_name": "stem",
                        "confidence": 0.91,
                        "bbox": {"cx": 0.5, "cy": 0.5, "w": 0.25, "h": 0.25},
                    }
                ],
                "summary": {"total": 1, "by_class": {"stem": 1}},
            }

            with patch("vision_studio.storage.DATA_ROOT", data_root), patch("vision_studio.storage.PROJECTS_ROOT", projects_root), patch("vision_studio.storage.JOBS_ROOT", jobs_root), patch("vision_studio.jobs.JOBS_ROOT", jobs_root), patch("vision_studio.main.run_prediction", return_value=fake_prediction, create=True) as run_prediction:
                response = TestClient(app).post(
                    "/api/projects/sample-project/prelabel",
                    json={
                        "job_id": "train-job",
                        "artifact_name": "best.pt",
                        "conf": 0.4,
                        "iou": 0.7,
                    },
                )
                saved_existing = read_json(annotation_path("sample-project", "existing.jpg"))
                saved_empty = read_json(annotation_path("sample-project", "empty.jpg"))
                yolo_text = generated_yolo_label_path("sample-project", "empty.jpg").read_text(encoding="utf-8")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["processed"], 1)
        self.assertEqual(data["skipped_existing"], 1)
        self.assertEqual(data["saved_annotations"], ["empty.jpg"])
        self.assertEqual(run_prediction.call_count, 1)
        self.assertEqual(saved_existing, existing_annotation)
        self.assertEqual(saved_empty["instances"][0]["bbox"]["cx"], 0.5)
        self.assertEqual(saved_empty["instances"][0]["confidence"], 0.91)
        self.assertEqual(yolo_text, "0 0.5 0.5 0.25 0.25\n")


if __name__ == "__main__":
    unittest.main()
