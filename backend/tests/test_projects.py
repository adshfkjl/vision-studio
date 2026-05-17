import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from vision_studio.main import app


class ProjectCreationTests(unittest.TestCase):
    def test_create_empty_project_returns_uploadable_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            projects_root = Path(tmp) / "projects"
            data_root = Path(tmp)
            jobs_root = Path(tmp) / "jobs"
            with patch("vision_studio.storage.DATA_ROOT", data_root), patch("vision_studio.storage.PROJECTS_ROOT", projects_root), patch("vision_studio.storage.JOBS_ROOT", jobs_root):
                response = TestClient(app).post(
                    "/api/projects",
                    json={
                        "name": "new local project",
                        "task_type": "pose",
                        "project_schema": {
                            "task_type": "pose",
                            "classes": [{"id": 0, "name": "stem", "color": "#0f766e"}],
                            "keypoints": ["root", "top"],
                            "skeleton": [[0, 1]],
                            "flip_idx": [0, 1],
                        },
                    },
                )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["name"], "new local project")
        self.assertEqual(data["images"], [])
        self.assertTrue(data["image_dir"].endswith("uploads\\images") or data["image_dir"].endswith("uploads/images"))


if __name__ == "__main__":
    unittest.main()
