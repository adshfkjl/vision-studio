import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from vision_studio.datasets import materialize_dataset, materialize_preview
from vision_studio.yolo import default_schema


class MaterializePreviewTests(unittest.TestCase):
    def test_preview_reports_counts_and_yaml(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dataset = root / "dataset"
            for subset in ("train", "val", "test"):
                (dataset / "images" / subset).mkdir(parents=True)
                (dataset / "labels" / subset).mkdir(parents=True)
            Image.new("RGB", (10, 10)).save(dataset / "images" / "train" / "one.jpg")
            (dataset / "labels" / "train" / "one.txt").write_text("0 0.5 0.5 0.2 0.2\n", encoding="utf-8")
            (dataset / "data.yaml").write_text("path: demo\ntrain: images/train\nnames:\n  0: stem\n", encoding="utf-8")

            result = materialize_preview(dataset, dataset / "data.yaml")

        self.assertIn("names:", result["data_yaml"])
        self.assertEqual(result["splits"]["train"]["images"], 1)
        self.assertEqual(result["splits"]["train"]["labels"], 1)
        self.assertEqual(result["missing_labels"], 0)
        self.assertEqual(result["sample_labels"][0]["text"], "0 0.5 0.5 0.2 0.2")

    def test_classify_materialization_uses_class_folders(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image_dir = root / "images"
            (image_dir / "cat").mkdir(parents=True)
            image = image_dir / "cat" / "one.jpg"
            Image.new("RGB", (10, 10)).save(image)
            project = {
                "id": "classify-project",
                "schema": {
                    "task_type": "classify",
                    "classes": [
                        {"id": 0, "name": "cat", "color": "#0f766e"},
                        {"id": 1, "name": "dog", "color": "#d97706"},
                    ],
                },
                "task_type": "classify",
                "image_dir": str(image_dir),
                "images": [{"name": "cat/one.jpg", "path": str(image), "width": 10, "height": 10}],
                "split": {"train": ["cat/one.jpg"], "val": [], "test": []},
            }

            with patch("vision_studio.storage.PROJECTS_ROOT", root / "projects"):
                dataset = materialize_dataset(project)
                preview = materialize_preview(dataset.root, dataset.data_yaml)

            self.assertTrue((dataset.root / "train" / "cat" / "one.jpg").is_file())
            self.assertIn("train: train", preview["data_yaml"])

    def test_obb_materialization_preserves_imported_label_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image_dir = root / "images"
            label_dir = root / "labels"
            image_dir.mkdir()
            label_dir.mkdir()
            image = image_dir / "one.jpg"
            Image.new("RGB", (10, 10)).save(image)
            (label_dir / "one.txt").write_text("0 0.1 0.2 0.4 0.2 0.4 0.5 0.1 0.5\n", encoding="utf-8")
            project = {
                "id": "obb-project",
                "schema": default_schema("obb"),
                "task_type": "obb",
                "image_dir": str(image_dir),
                "label_dir": str(label_dir),
                "images": [{"name": "one.jpg", "path": str(image), "width": 10, "height": 10}],
                "split": {"train": ["one.jpg"], "val": [], "test": []},
            }

            with patch("vision_studio.storage.PROJECTS_ROOT", root / "projects"):
                dataset = materialize_dataset(project)

            self.assertEqual(
                (dataset.root / "labels" / "train" / "one.txt").read_text(encoding="utf-8"),
                "0 0.1 0.2 0.4 0.2 0.4 0.5 0.1 0.5\n",
            )

    def test_materialization_adds_newly_annotated_images_to_existing_split(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image_dir = root / "images"
            image_dir.mkdir()
            for name in ("one.jpg", "two.jpg"):
                Image.new("RGB", (10, 10)).save(image_dir / name)
            project = {
                "id": "refresh-project",
                "schema": default_schema("detect"),
                "task_type": "detect",
                "image_dir": str(image_dir),
                "label_dir": None,
                "images": [
                    {"name": "one.jpg", "path": str(image_dir / "one.jpg"), "width": 10, "height": 10},
                    {"name": "two.jpg", "path": str(image_dir / "two.jpg"), "width": 10, "height": 10},
                ],
                "split": {
                    "train": ["one.jpg"],
                    "val": [],
                    "test": [],
                    "ratios": {"train": 0.8, "val": 0.15, "test": 0.05},
                    "seed": 42,
                },
            }

            annotation = {"version": 1, "instances": [{"type": "box", "class_id": 0, "bbox": {"cx": 0.5, "cy": 0.5, "w": 0.2, "h": 0.2}}]}
            with patch("vision_studio.storage.PROJECTS_ROOT", root / "projects"):
                from vision_studio.storage import annotation_path, write_json

                write_json(annotation_path(project["id"], "one.jpg"), annotation)
                write_json(annotation_path(project["id"], "two.jpg"), annotation)

                dataset = materialize_dataset(project)

            materialized_images = {
                path.name
                for subset in ("train", "val", "test")
                for path in (dataset.root / "images" / subset).glob("*.jpg")
            }
            split_images = set(project["split"]["train"] + project["split"]["val"] + project["split"]["test"])
            self.assertIn("two.jpg", materialized_images)
            self.assertIn("two.jpg", split_images)


if __name__ == "__main__":
    unittest.main()
