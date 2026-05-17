import unittest
from pathlib import Path

from vision_studio.yolo import annotation_to_yolo, default_schema, parse_yolo_label


class YoloConversionTests(unittest.TestCase):
    def test_pose_round_trip(self) -> None:
        schema = default_schema("pose")
        label = Path(__file__).with_name("_one_pose.txt")
        try:
            label.write_text(
                "0 0.5 0.4 0.2 0.1 0.4 0.35 2 0.5 0.4 2 0.6 0.45 2\n",
                encoding="utf-8",
            )
            ann = parse_yolo_label(label, "pose", schema)
            self.assertEqual(ann["instances"][0]["keypoints"][0]["name"], "stem_root")
            self.assertTrue(annotation_to_yolo(ann, schema).startswith("0 0.5 0.4 0.2 0.1"))
        finally:
            label.unlink(missing_ok=True)

    def test_segment_export(self) -> None:
        schema = default_schema("segment")
        ann = {
            "instances": [
                {
                    "type": "polygon",
                    "class_id": 0,
                    "points": [{"x": 0.1, "y": 0.2}, {"x": 0.3, "y": 0.2}, {"x": 0.3, "y": 0.4}],
                }
            ]
        }
        self.assertEqual(annotation_to_yolo(ann, schema), "0 0.1 0.2 0.3 0.2 0.3 0.4\n")


if __name__ == "__main__":
    unittest.main()
