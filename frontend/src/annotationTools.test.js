import test from "node:test";
import assert from "node:assert/strict";

import { canAdjustExistingAnnotation, shouldShowBboxResizeHandles } from "./annotationTools.js";

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
