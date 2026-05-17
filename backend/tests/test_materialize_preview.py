import tempfile
import unittest
from pathlib import Path

from PIL import Image

from vision_studio.datasets import materialize_preview


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


if __name__ == "__main__":
    unittest.main()
