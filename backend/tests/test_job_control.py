import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from vision_studio.jobs import create_job, finalize_training_job, load_job, training_subprocess_env, update_job
from vision_studio.main import app


class FakeProcess:
    def __init__(self) -> None:
        self.suspended = False
        self.resumed = False
        self.terminated = False

    def suspend(self) -> None:
        self.suspended = True

    def resume(self) -> None:
        self.resumed = True

    def terminate(self) -> None:
        self.terminated = True


class JobControlTests(unittest.TestCase):
    def test_pause_resume_and_stop_training_job_process_tree(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            jobs_root = Path(tmp) / "jobs"
            with patch("vision_studio.jobs.JOBS_ROOT", jobs_root):
                job = create_job("project", "train", {})
                update_job(job["id"], status="running", pid=1234)
                process = FakeProcess()

                with patch("vision_studio.jobs.process_tree", return_value=[process]):
                    pause = TestClient(app).post(f"/api/jobs/{job['id']}/pause")
                    paused = load_job(job["id"])
                    resume = TestClient(app).post(f"/api/jobs/{job['id']}/resume")
                    resumed = load_job(job["id"])
                    stop = TestClient(app).post(f"/api/jobs/{job['id']}/stop")
                    stopped = load_job(job["id"])

        self.assertEqual(pause.status_code, 200)
        self.assertTrue(process.suspended)
        self.assertEqual(paused["status"], "paused")
        self.assertEqual(resume.status_code, 200)
        self.assertTrue(process.resumed)
        self.assertEqual(resumed["status"], "running")
        self.assertEqual(stop.status_code, 200)
        self.assertTrue(process.terminated)
        self.assertEqual(stopped["status"], "stopping")

    def test_gpu_training_subprocess_env_excludes_bundled_deps(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "VISION_STUDIO_USE_BUNDLED_DEPS": "0",
                "PYTHONPATH": r"D:\projects\2\vision_studio\backend\.deps;C:\extra",
            },
            clear=False,
        ):
            env = training_subprocess_env()

        self.assertIn(r"D:\projects\2\vision_studio\backend", env["PYTHONPATH"])
        self.assertNotIn(r"D:\projects\2\vision_studio\backend\.deps", env["PYTHONPATH"])
        self.assertIn(r"C:\extra", env["PYTHONPATH"])

    def test_finalize_training_collects_saved_weights_after_late_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            jobs_root = root / "jobs"
            runs_root = root / "runs"
            weight_dir = runs_root / "pose" / "studio_train" / "weights"
            weight_dir.mkdir(parents=True)
            (weight_dir / "best.pt").write_bytes(b"best")
            (weight_dir / "last.pt").write_bytes(b"last")
            project = {"id": "project", "schema": {"task_type": "pose"}}
            with (
                patch("vision_studio.jobs.JOBS_ROOT", jobs_root),
                patch("vision_studio.jobs.load_project", return_value=project),
                patch("vision_studio.jobs.runs_dir", return_value=runs_root),
            ):
                job = create_job("project", "train", {"task_type": "pose", "name": "studio_train"})
                finalize_training_job(job["id"], 1)
                saved = load_job(job["id"])

        self.assertEqual(saved["status"], "completed")
        self.assertIn("best.pt", saved["artifacts"])
        self.assertIn("last.pt", saved["artifacts"])
        self.assertIn("exited with code 1", saved["error"])


if __name__ == "__main__":
    unittest.main()
