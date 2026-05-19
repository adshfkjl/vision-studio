import unittest

from vision_studio.tasks import available_tasks, task_definitions


class TaskRegistryTests(unittest.TestCase):
    def test_task_registry_exposes_all_yolo_tasks(self):
        tasks = available_tasks()
        self.assertEqual([task["task_type"] for task in tasks], ["detect", "segment", "pose", "classify", "obb"])

    def test_task_registry_marks_station_annotation_only_for_supported_tasks(self):
        tasks = task_definitions()
        self.assertTrue(tasks["detect"]["station_annotation"])
        self.assertTrue(tasks["segment"]["station_annotation"])
        self.assertTrue(tasks["pose"]["station_annotation"])
        self.assertFalse(tasks["classify"]["station_annotation"])
        self.assertFalse(tasks["obb"]["station_annotation"])


if __name__ == "__main__":
    unittest.main()
