import test from "node:test";
import assert from "node:assert/strict";

import { canAdjustExistingAnnotation, instanceDetailLabel, instanceTitleLabel, shouldShowBboxResizeHandles } from "./annotationTools.js";

test("mouse mode can adjust existing annotation instances", () => {
  assert.equal(canAdjustExistingAnnotation("mouse"), true);
});

test("creation modes keep their existing instance adjustment behavior", () => {
  assert.equal(canAdjustExistingAnnotation("bbox"), true);
  assert.equal(canAdjustExistingAnnotation("polygon"), true);
  assert.equal(canAdjustExistingAnnotation("keypoint"), true);
});

test("selected bbox resize handles are visible in mouse mode", () => {
  assert.equal(shouldShowBboxResizeHandles({ selected: true, tool: "mouse" }), true);
});

test("bbox resize handles stay out of keypoint mode so bbox interiors do not block point placement", () => {
  assert.equal(shouldShowBboxResizeHandles({ selected: true, tool: "keypoint" }), false);
});

test("bbox resize handles stay hidden when the bbox is not selected", () => {
  assert.equal(shouldShowBboxResizeHandles({ selected: false, tool: "mouse" }), false);
});

test("pose instance labels describe the annotation instead of exposing raw type words", () => {
  const schema = {
    classes: [{ id: 0, name: "object" }],
    keypoints: ["root", "tip"],
  };
  const instance = {
    type: "pose",
    class_id: 0,
    bbox: { cx: 0.5, cy: 0.5, w: 0.2, h: 0.2 },
    keypoints: [{ name: "root", x: 0.5, y: 0.5, v: 2 }],
  };

  assert.equal(instanceTitleLabel(instance, schema, 0), "#1 姿态 · object");
  assert.equal(instanceDetailLabel(instance, schema), "框 + 1/2 关键点");
});
