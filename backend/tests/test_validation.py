import tempfile
import unittest
from pathlib import Path

from PIL import Image

from vision_studio.validation import validate_project
from vision_studio.yolo import default_schema


def make_image(path: Path) -> None:
    Image.new("RGB", (32, 24), color=(255, 255, 255)).save(path)


class ValidationTests(unittest.TestCase):
    def make_project(self, annotation):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        image = root / "one.jpg"
        make_image(image)
        project = {
            "id": "validation-test",
            "schema": default_schema("pose"),
            "images": [{"name": "one.jpg", "path": str(image), "width": 32, "height": 24}],
            "_annotation_overrides": {"one.jpg": annotation},
        }
        return temp, project

    def test_valid_pose_project_can_train(self):
        temp, project = self.make_project(
            {
                "version": 1,
                "instances": [
                    {
                        "type": "pose",
                        "class_id": 0,
                        "bbox": {"cx": 0.5, "cy": 0.5, "w": 0.25, "h": 0.25},
                        "keypoints": [
                            {"name": "stem_root", "x": 0.45, "y": 0.6, "v": 2},
                            {"name": "stem_mid", "x": 0.5, "y": 0.5, "v": 2},
                            {"name": "stem_top", "x": 0.55, "y": 0.4, "v": 2},
                        ],
                    }
                ],
            }
        )
        with temp:
            result = validate_project(project)
        self.assertEqual(result["status"], "pass")
        self.assertTrue(result["train_ready"])
        self.assertEqual(result["summary"]["annotated_images"], 1)

    def test_out_of_range_coordinates_fail_validation(self):
        temp, project = self.make_project(
            {
                "version": 1,
                "instances": [
                    {
                        "type": "pose",
                        "class_id": 0,
                        "bbox": {"cx": 1.2, "cy": 0.5, "w": 0.25, "h": 0.25},
                        "keypoints": [
                            {"name": "stem_root", "x": 0.45, "y": 0.6, "v": 2},
                            {"name": "stem_mid", "x": 0.5, "y": 0.5, "v": 2},
                            {"name": "stem_top", "x": 0.55, "y": 0.4, "v": 2},
                        ],
                    }
                ],
            }
        )
        with temp:
            result = validate_project(project)
        self.assertEqual(result["status"], "fail")
        self.assertFalse(result["train_ready"])
        self.assertIn("coordinate_range", {issue["code"] for issue in result["issues"]})

    def test_missing_pose_keypoints_fail_validation(self):
        temp, project = self.make_project(
            {
                "version": 1,
                "instances": [
                    {
                        "type": "pose",
                        "class_id": 0,
                        "bbox": {"cx": 0.5, "cy": 0.5, "w": 0.25, "h": 0.25},
                        "keypoints": [{"name": "stem_root", "x": 0.45, "y": 0.6, "v": 2}],
                    }
                ],
            }
        )
        with temp:
            result = validate_project(project)
        self.assertEqual(result["status"], "fail")
        self.assertIn("pose_keypoints", {issue["code"] for issue in result["issues"]})

    def test_classify_project_without_labels_is_not_train_ready(self):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        image = root / "cat" / "one.jpg"
        image.parent.mkdir(parents=True, exist_ok=True)
        make_image(image)
        project = {
            "id": "validation-classify",
            "schema": {
                "task_type": "classify",
                "classes": [
                    {"id": 0, "name": "cat", "color": "#0f766e"},
                    {"id": 1, "name": "dog", "color": "#d97706"},
                ],
            },
            "task_type": "classify",
            "image_dir": str(root),
            "images": [{"name": "cat/one.jpg", "path": str(image), "width": 32, "height": 24}],
        }
        with temp:
            result = validate_project(project)
        self.assertEqual(result["status"], "pass")
        self.assertTrue(result["train_ready"])

    def test_obb_project_without_labels_is_not_train_ready(self):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        image = root / "one.jpg"
        make_image(image)
        label_dir = root / "labels"
        label_dir.mkdir(parents=True, exist_ok=True)
        (label_dir / "one.txt").write_text("0 0.1 0.2 0.3 0.2 0.3 0.4 0.1 0.4\n", encoding="utf-8")
        project = {
            "id": "validation-obb",
            "schema": default_schema("obb"),
            "task_type": "obb",
            "image_dir": str(root),
            "label_dir": str(label_dir),
            "images": [{"name": "one.jpg", "path": str(image), "width": 32, "height": 24}],
        }
        with temp:
            result = validate_project(project)
        self.assertEqual(result["status"], "pass")
        self.assertTrue(result["train_ready"])

    def test_obb_project_rejects_out_of_range_corner_points(self):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        image = root / "one.jpg"
        make_image(image)
        label_dir = root / "labels"
        label_dir.mkdir(parents=True, exist_ok=True)
        (label_dir / "one.txt").write_text("0 0.1 0.2 1.3 0.2 0.3 0.4 0.1 0.4\n", encoding="utf-8")
        project = {
            "id": "validation-obb-range",
            "schema": default_schema("obb"),
            "task_type": "obb",
            "image_dir": str(root),
            "label_dir": str(label_dir),
            "images": [{"name": "one.jpg", "path": str(image), "width": 32, "height": 24}],
        }
        with temp:
            result = validate_project(project)
        self.assertEqual(result["status"], "fail")
        self.assertFalse(result["train_ready"])
        self.assertIn("coordinate_range", {issue["code"] for issue in result["issues"]})


if __name__ == "__main__":
    unittest.main()
