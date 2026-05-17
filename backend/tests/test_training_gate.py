import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image
from fastapi.testclient import TestClient

from vision_studio.main import app
from vision_studio.yolo import default_schema


class TrainingGateTests(unittest.TestCase):
    def test_train_endpoint_rejects_project_without_labels(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image = root / "one.jpg"
            Image.new("RGB", (32, 24), color=(255, 255, 255)).save(image)
            project = {
                "id": "empty-project",
                "schema": default_schema("pose"),
                "task_type": "pose",
                "images": [{"name": "one.jpg", "path": str(image), "width": 32, "height": 24}],
                "split": None,
            }
            with patch("vision_studio.main.load_project", return_value=project):
                response = TestClient(app).post("/api/projects/empty-project/train", json={"epochs": 1})

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["detail"]["validation"]["train_ready"])


if __name__ == "__main__":
    unittest.main()
