const INSTANCE_EDIT_TOOLS = new Set(["mouse", "bbox", "polygon", "keypoint"]);
const BBOX_RESIZE_TOOLS = new Set(["mouse", "bbox"]);

export function canAdjustExistingAnnotation(tool) {
  return INSTANCE_EDIT_TOOLS.has(tool);
}

export function canResizeBbox(tool) {
  return BBOX_RESIZE_TOOLS.has(tool);
}

export function shouldShowBboxResizeHandles({ selected, tool }) {
  return Boolean(selected && canResizeBbox(tool));
}
