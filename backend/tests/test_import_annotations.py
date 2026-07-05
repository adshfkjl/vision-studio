import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image

from vision_studio.main import app
from vision_studio.storage import annotation_path, config_path, read_json


CVAT_XML = """<?xml version="1.0" encoding="utf-8"?>
<annotations>
  <version>1.1</version>
  <meta>
    <task>
      <labels>
        <label>
          <name>stem</name>
          <color>#5e7934</color>
          <type>skeleton</type>
          <svg>&lt;line data-type="edge" data-node-from="1" data-node-to="2"&gt;&lt;/line&gt;&lt;line data-type="edge" data-node-from="2" data-node-to="3"&gt;&lt;/line&gt;</svg>
        </label>
        <label><name>1</name><type>points</type><parent>stem</parent></label>
        <label><name>2</name><type>points</type><parent>stem</parent></label>
        <label><name>3</name><type>points</type><parent>stem</parent></label>
      </labels>
    </task>
  </meta>
  <image id="0" name="plant.jpg" width="100" height="80">
    <skeleton label="stem">
      <points label="1" outside="0" occluded="0" points="10,20"></points>
      <points label="2" outside="0" occluded="0" points="20,30"></points>
      <points label="3" outside="0" occluded="1" points="30,40"></points>
    </skeleton>
  </image>
</annotations>
"""

VOC_XML = """<annotation>
  <filename>plant.jpg</filename>
  <size><width>100</width><height>80</height></size>
  <object><name>leaf</name><bndbox><xmin>10</xmin><ymin>20</ymin><xmax>30</xmax><ymax>50</ymax></bndbox></object>
</annotation>
"""

COCO_JSON = {
    "images": [{"id": 1, "file_name": "plant.jpg", "width": 100, "height": 80}],
    "categories": [{"id": 7, "name": "leaf"}],
    "annotations": [{"id": 1, "image_id": 1, "category_id": 7, "bbox": [10, 20, 20, 30]}],
}

LABELME_JSON = {
    "imagePath": "plant.jpg",
    "imageWidth": 100,
    "imageHeight": 80,
    "shapes": [
        {"label": "leaf", "shape_type": "rectangle", "points": [[10, 20], [30, 50]]},
    ],
}


class AnnotationImportTests(unittest.TestCase):
    def test_import_project_materializes_matching_cvat_xml_annotations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data_root = root / "data"
            projects_root = data_root / "projects"
            jobs_root = data_root / "jobs"
            image_dir = root / "images"
            image_dir.mkdir()
            Image.new("RGB", (100, 80), "white").save(image_dir / "plant.jpg")
            xml_path = root / "annotations.xml"
            xml_path.write_text(CVAT_XML, encoding="utf-8")

            with patch("vision_studio.storage.DATA_ROOT", data_root), patch("vision_studio.storage.PROJECTS_ROOT", projects_root), patch("vision_studio.storage.JOBS_ROOT", jobs_root):
                response = TestClient(app).post(
                    "/api/projects/import",
                    json={
                        "name": "cvat import",
                        "task_type": "pose",
                        "image_dir": str(image_dir),
                        "annotation_file": str(xml_path),
                    },
                )
                project = response.json()
                ann = read_json(annotation_path(project["id"], "plant.jpg"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(project["import_summary"]["annotation_format"], "cvat_xml")
        self.assertEqual(project["import_summary"]["matched_annotations"], 1)
        self.assertEqual(project["schema"]["keypoints"], ["1", "2", "3"])
        self.assertEqual(ann["instances"][0]["type"], "pose")
        self.assertAlmostEqual(ann["instances"][0]["keypoints"][0]["x"], 0.1)
        self.assertAlmostEqual(ann["instances"][0]["keypoints"][2]["y"], 0.5)

    def test_delete_image_removes_project_entry_and_internal_annotations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data_root = root / "data"
            projects_root = data_root / "projects"
            jobs_root = data_root / "jobs"
            image_dir = root / "images"
            image_dir.mkdir()
            Image.new("RGB", (100, 80), "white").save(image_dir / "plant.jpg")
            xml_path = root / "annotations.xml"
            xml_path.write_text(CVAT_XML, encoding="utf-8")

            with patch("vision_studio.storage.DATA_ROOT", data_root), patch("vision_studio.storage.PROJECTS_ROOT", projects_root), patch("vision_studio.storage.JOBS_ROOT", jobs_root):
                client = TestClient(app)
                project = client.post(
                    "/api/projects/import",
                    json={
                        "name": "cvat import",
                        "task_type": "pose",
                        "image_dir": str(image_dir),
                        "annotation_file": str(xml_path),
                    },
                ).json()
                response = client.delete(f"/api/projects/{project['id']}/images/plant.jpg")
                saved = read_json(config_path(project["id"]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["removed"], "plant.jpg")
        self.assertEqual(saved["images"], [])
        self.assertFalse(annotation_path(project["id"], "plant.jpg").exists())

    def test_saved_annotations_for_same_basename_nested_images_do_not_collide(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data_root = root / "data"
            projects_root = data_root / "projects"
            jobs_root = data_root / "jobs"
            image_dir = root / "images"
            (image_dir / "plot-a").mkdir(parents=True)
            (image_dir / "plot-b").mkdir()
            Image.new("RGB", (100, 80), "white").save(image_dir / "plot-a" / "leaf.jpg")
            Image.new("RGB", (100, 80), "white").save(image_dir / "plot-b" / "leaf.jpg")

            with patch("vision_studio.storage.DATA_ROOT", data_root), patch("vision_studio.storage.PROJECTS_ROOT", projects_root), patch("vision_studio.storage.JOBS_ROOT", jobs_root):
                client = TestClient(app)
                project = client.post(
                    "/api/projects/import",
                    json={"name": "nested duplicate names", "task_type": "detect", "image_dir": str(image_dir)},
                ).json()
                first = {"version": 1, "instances": [{"type": "box", "class_id": 0, "bbox": {"cx": 0.25, "cy": 0.4, "w": 0.2, "h": 0.3}}]}
                second = {"version": 1, "instances": [{"type": "box", "class_id": 0, "bbox": {"cx": 0.75, "cy": 0.6, "w": 0.1, "h": 0.2}}]}
                first_response = client.put(f"/api/projects/{project['id']}/annotations/plot-a/leaf.jpg", json=first)
                second_response = client.put(f"/api/projects/{project['id']}/annotations/plot-b/leaf.jpg", json=second)
                loaded_first = client.get(f"/api/projects/{project['id']}/annotations/plot-a/leaf.jpg").json()["annotation"]
                loaded_second = client.get(f"/api/projects/{project['id']}/annotations/plot-b/leaf.jpg").json()["annotation"]

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)
        self.assertNotEqual(first_response.json()["annotation_path"], second_response.json()["annotation_path"])
        self.assertEqual(loaded_first["instances"][0]["bbox"]["cx"], 0.25)
        self.assertEqual(loaded_second["instances"][0]["bbox"]["cx"], 0.75)

    def test_existing_project_can_import_pascal_voc_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data_root = root / "data"
            projects_root = data_root / "projects"
            jobs_root = data_root / "jobs"
            image_dir = root / "images"
            image_dir.mkdir()
            Image.new("RGB", (100, 80), "white").save(image_dir / "plant.jpg")
            voc_dir = root / "voc"
            voc_dir.mkdir()
            (voc_dir / "plant.xml").write_text(VOC_XML, encoding="utf-8")

            with patch("vision_studio.storage.DATA_ROOT", data_root), patch("vision_studio.storage.PROJECTS_ROOT", projects_root), patch("vision_studio.storage.JOBS_ROOT", jobs_root):
                client = TestClient(app)
                project = client.post("/api/projects", json={"name": "voc project", "task_type": "detect"}).json()
                client.post(f"/api/projects/{project['id']}/images/upload", files=[("files", ("plant.jpg", (image_dir / "plant.jpg").read_bytes(), "image/jpeg"))])
                response = client.post(f"/api/projects/{project['id']}/annotations/import", json={"annotation_path": str(voc_dir)})
                ann = read_json(annotation_path(project["id"], "uploaded/plant.jpg"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["import_summary"]["annotation_format"], "pascal_voc")
        self.assertEqual(ann["instances"][0]["type"], "box")
        self.assertAlmostEqual(ann["instances"][0]["bbox"]["cx"], 0.2)

    def test_existing_project_can_import_coco_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data_root = root / "data"
            projects_root = data_root / "projects"
            jobs_root = data_root / "jobs"
            image_dir = root / "images"
            image_dir.mkdir()
            Image.new("RGB", (100, 80), "white").save(image_dir / "plant.jpg")
            coco_path = root / "instances.json"
            import json
            coco_path.write_text(json.dumps(COCO_JSON), encoding="utf-8")

            with patch("vision_studio.storage.DATA_ROOT", data_root), patch("vision_studio.storage.PROJECTS_ROOT", projects_root), patch("vision_studio.storage.JOBS_ROOT", jobs_root):
                client = TestClient(app)
                project = client.post("/api/projects", json={"name": "coco project", "task_type": "detect"}).json()
                client.post(f"/api/projects/{project['id']}/images/upload", files=[("files", ("plant.jpg", (image_dir / "plant.jpg").read_bytes(), "image/jpeg"))])
                response = client.post(f"/api/projects/{project['id']}/annotations/import", json={"annotation_path": str(coco_path)})
                ann = read_json(annotation_path(project["id"], "uploaded/plant.jpg"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["import_summary"]["annotation_format"], "coco_json")
        self.assertEqual(ann["instances"][0]["class_id"], 0)

    def test_existing_project_can_import_labelme_json_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data_root = root / "data"
            projects_root = data_root / "projects"
            jobs_root = data_root / "jobs"
            image_dir = root / "images"
            image_dir.mkdir()
            Image.new("RGB", (100, 80), "white").save(image_dir / "plant.jpg")
            labelme_dir = root / "labelme"
            labelme_dir.mkdir()
            import json
            (labelme_dir / "plant.json").write_text(json.dumps(LABELME_JSON), encoding="utf-8")

            with patch("vision_studio.storage.DATA_ROOT", data_root), patch("vision_studio.storage.PROJECTS_ROOT", projects_root), patch("vision_studio.storage.JOBS_ROOT", jobs_root):
                client = TestClient(app)
                project = client.post("/api/projects", json={"name": "labelme project", "task_type": "detect"}).json()
                client.post(f"/api/projects/{project['id']}/images/upload", files=[("files", ("plant.jpg", (image_dir / "plant.jpg").read_bytes(), "image/jpeg"))])
                response = client.post(f"/api/projects/{project['id']}/annotations/import", json={"annotation_path": str(labelme_dir)})
                ann = read_json(annotation_path(project["id"], "uploaded/plant.jpg"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["import_summary"]["annotation_format"], "labelme_json")
        self.assertEqual(ann["instances"][0]["type"], "box")

    def test_existing_project_can_import_yolo_label_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data_root = root / "data"
            projects_root = data_root / "projects"
            jobs_root = data_root / "jobs"
            image_dir = root / "images"
            image_dir.mkdir()
            Image.new("RGB", (100, 80), "white").save(image_dir / "plant.jpg")
            yolo_dir = root / "labels"
            yolo_dir.mkdir()
            (yolo_dir / "plant.txt").write_text("0 0.2 0.4375 0.2 0.375\n", encoding="utf-8")

            with patch("vision_studio.storage.DATA_ROOT", data_root), patch("vision_studio.storage.PROJECTS_ROOT", projects_root), patch("vision_studio.storage.JOBS_ROOT", jobs_root):
                client = TestClient(app)
                project = client.post("/api/projects", json={"name": "yolo project", "task_type": "detect"}).json()
                client.post(f"/api/projects/{project['id']}/images/upload", files=[("files", ("plant.jpg", (image_dir / "plant.jpg").read_bytes(), "image/jpeg"))])
                response = client.post(f"/api/projects/{project['id']}/annotations/import", json={"annotation_path": str(yolo_dir)})
                ann = read_json(annotation_path(project["id"], "uploaded/plant.jpg"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["import_summary"]["annotation_format"], "yolo_labels")
        self.assertAlmostEqual(ann["instances"][0]["bbox"]["cy"], 0.4375)

    def test_existing_project_can_import_uploaded_annotation_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data_root = root / "data"
            projects_root = data_root / "projects"
            jobs_root = data_root / "jobs"
            image_dir = root / "images"
            image_dir.mkdir()
            Image.new("RGB", (100, 80), "white").save(image_dir / "plant.jpg")

            with patch("vision_studio.storage.DATA_ROOT", data_root), patch("vision_studio.storage.PROJECTS_ROOT", projects_root), patch("vision_studio.storage.JOBS_ROOT", jobs_root):
                client = TestClient(app)
                project = client.post("/api/projects", json={"name": "upload import", "task_type": "pose"}).json()
                client.post(f"/api/projects/{project['id']}/images/upload", files=[("files", ("plant.jpg", (image_dir / "plant.jpg").read_bytes(), "image/jpeg"))])
                response = client.post(
                    f"/api/projects/{project['id']}/annotations/import-file",
                    data={"annotation_format": "auto"},
                    files={"annotation_file": ("annotations.xml", CVAT_XML.encode("utf-8"), "application/xml")},
                )
                ann = read_json(annotation_path(project["id"], "uploaded/plant.jpg"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["import_summary"]["annotation_format"], "cvat_xml")
        self.assertEqual(ann["instances"][0]["type"], "pose")

    def test_existing_project_can_import_multiple_uploaded_yolo_label_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data_root = root / "data"
            projects_root = data_root / "projects"
            jobs_root = data_root / "jobs"
            image_dir = root / "images"
            image_dir.mkdir()
            Image.new("RGB", (100, 80), "white").save(image_dir / "plant.jpg")
            Image.new("RGB", (100, 80), "white").save(image_dir / "root.jpg")

            with patch("vision_studio.storage.DATA_ROOT", data_root), patch("vision_studio.storage.PROJECTS_ROOT", projects_root), patch("vision_studio.storage.JOBS_ROOT", jobs_root):
                client = TestClient(app)
                project = client.post("/api/projects", json={"name": "multi upload import", "task_type": "detect"}).json()
                client.post(
                    f"/api/projects/{project['id']}/images/upload",
                    files=[
                        ("files", ("plant.jpg", (image_dir / "plant.jpg").read_bytes(), "image/jpeg")),
                        ("files", ("root.jpg", (image_dir / "root.jpg").read_bytes(), "image/jpeg")),
                    ],
                )
                response = client.post(
                    f"/api/projects/{project['id']}/annotations/import-file",
                    data={"annotation_format": "auto"},
                    files=[
                        ("annotation_files", ("plant.txt", "0 0.2 0.4375 0.2 0.375\n", "text/plain")),
                        ("annotation_files", ("root.txt", "0 0.6 0.375 0.2 0.25\n", "text/plain")),
                    ],
                )
                plant_ann = read_json(annotation_path(project["id"], "uploaded/plant.jpg"))
                root_ann = read_json(annotation_path(project["id"], "uploaded/root.jpg"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["import_summary"]["annotation_format"], "yolo_labels")
        self.assertEqual(response.json()["import_summary"]["matched_annotations"], 2)
        self.assertEqual(plant_ann["instances"][0]["type"], "box")
        self.assertEqual(root_ann["instances"][0]["type"], "box")

    def test_import_project_can_use_uploaded_annotation_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data_root = root / "data"
            projects_root = data_root / "projects"
            jobs_root = data_root / "jobs"
            image_dir = root / "images"
            image_dir.mkdir()
            Image.new("RGB", (100, 80), "white").save(image_dir / "plant.jpg")

            with patch("vision_studio.storage.DATA_ROOT", data_root), patch("vision_studio.storage.PROJECTS_ROOT", projects_root), patch("vision_studio.storage.JOBS_ROOT", jobs_root):
                response = TestClient(app).post(
                    "/api/projects/import-file",
                    data={"name": "uploaded cvat import", "task_type": "pose", "image_dir": str(image_dir), "annotation_format": "auto"},
                    files={"annotation_file": ("annotations.xml", CVAT_XML.encode("utf-8"), "application/xml")},
                )
                project = response.json()
                ann = read_json(annotation_path(project["id"], "plant.jpg"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(project["import_summary"]["annotation_format"], "cvat_xml")
        self.assertEqual(ann["instances"][0]["type"], "pose")

    def test_import_project_can_use_multiple_uploaded_yolo_label_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data_root = root / "data"
            projects_root = data_root / "projects"
            jobs_root = data_root / "jobs"
            image_dir = root / "images"
            image_dir.mkdir()
            Image.new("RGB", (100, 80), "white").save(image_dir / "plant.jpg")
            Image.new("RGB", (100, 80), "white").save(image_dir / "root.jpg")

            with patch("vision_studio.storage.DATA_ROOT", data_root), patch("vision_studio.storage.PROJECTS_ROOT", projects_root), patch("vision_studio.storage.JOBS_ROOT", jobs_root):
                response = TestClient(app).post(
                    "/api/projects/import-file",
                    data={
                        "name": "multi upload project import",
                        "task_type": "detect",
                        "image_dir": str(image_dir),
                        "annotation_format": "auto",
                    },
                    files=[
                        ("annotation_files", ("plant.txt", "0 0.2 0.4375 0.2 0.375\n", "text/plain")),
                        ("annotation_files", ("root.txt", "0 0.6 0.375 0.2 0.25\n", "text/plain")),
                    ],
                )
                project = response.json()
                plant_ann = read_json(annotation_path(project["id"], "plant.jpg"))
                root_ann = read_json(annotation_path(project["id"], "root.jpg"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(project["import_summary"]["annotation_format"], "yolo_labels")
        self.assertEqual(project["import_summary"]["matched_annotations"], 2)
        self.assertEqual(plant_ann["instances"][0]["type"], "box")
        self.assertEqual(root_ann["instances"][0]["type"], "box")


if __name__ == "__main__":
    unittest.main()
