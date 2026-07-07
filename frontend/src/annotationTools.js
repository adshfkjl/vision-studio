const INSTANCE_EDIT_TOOLS = new Set(["mouse", "bbox", "polygon", "keypoint"]);
const BBOX_RESIZE_TOOLS = new Set(["mouse", "bbox"]);
const TYPE_LABELS = {
  pose: "姿态",
  box: "检测框",
  bbox: "检测框",
  polygon: "多边形",
  classification: "分类",
  obb: "旋转框",
};

export function canAdjustExistingAnnotation(tool) {
  return INSTANCE_EDIT_TOOLS.has(tool);
}

export function canResizeBbox(tool) {
  return BBOX_RESIZE_TOOLS.has(tool);
}

export function shouldShowBboxResizeHandles({ selected, tool }) {
  return Boolean(selected && canResizeBbox(tool));
}

export function instanceClassName(instance, schema) {
  return schema?.classes?.find((item) => Number(item.id) === Number(instance?.class_id))?.name || `class ${instance?.class_id ?? 0}`;
}

export function instanceTypeLabel(instance) {
  return TYPE_LABELS[instance?.type] || "实例";
}

export function instanceTitleLabel(instance, schema, index) {
  return `#${index + 1} ${instanceTypeLabel(instance)} · ${instanceClassName(instance, schema)}`;
}

export function instanceDetailLabel(instance, schema) {
  if (instance?.type === "pose") {
    const total = schema?.keypoints?.length || 0;
    const placed = (instance.keypoints || []).filter((point) => point?.v).length;
    return `框 + ${placed}/${total} 关键点`;
  }
  if (instance?.type === "polygon") {
    return `${instance.points?.length || 0} 点`;
  }
  if (instance?.type === "box" || instance?.type === "bbox") {
    return "框";
  }
  if (instance?.type === "obb") {
    return `${instance.points?.length || 0} 角点`;
  }
  return "实例";
}
