import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from vision_studio.jobs import create_job, load_job, update_job
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


if __name__ == "__main__":
    unittest.main()
