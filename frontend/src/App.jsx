import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  BoxSelect,
  Brain,
  Download,
  FolderInput,
  GitBranch,
  Image as ImageIcon,
  MousePointer2,
  Plus,
  Save,
  Scissors,
  Settings,
  Trash2,
  Undo2,
  Upload,
  ZoomIn,
  ZoomOut,
} from "lucide-react";
import { api, apiBase, artifactUrl, imageUrl } from "./api.js";

const blankImport = {
  name: "current-pose",
  task_type: "pose",
  image_dir: "images",
  label_dir: "labels",
  data_yaml: "yolo-pose/data.yaml",
};

const blankCreate = {
  name: "new-project",
  task_type: "pose",
  classesText: "stem",
  keypointsText: "stem_root, stem_mid, stem_top",
  skeletonText: "0-1, 1-2",
  flipText: "2, 1, 0",
};

const blankTrain = {
  model: "",
  epochs: 100,
  imgsz: 960,
  batch: 4,
  device: "auto",
  lr0: 0.01,
  optimizer: "AdamW",
  patience: 30,
  seed: 42,
  name: "studio_train",
};

function clsName(schema, id) {
  return schema?.classes?.find((c) => Number(c.id) === Number(id))?.name || `class ${id}`;
}

function clsColor(schema, id) {
  return schema?.classes?.find((c) => Number(c.id) === Number(id))?.color || "#0f766e";
}

function schemaFromForm(form) {
  const classes = form.classesText
    .split(",")
    .map((name) => name.trim())
    .filter(Boolean)
    .map((name, id) => ({ id, name, color: ["#0f766e", "#d97706", "#2563eb", "#be123c", "#7c3aed"][id % 5] }));
  const keypoints = form.keypointsText.split(",").map((x) => x.trim()).filter(Boolean);
  const skeleton = form.skeletonText
    .split(",")
    .map((pair) => pair.trim().split("-").map((x) => Number(x.trim())))
    .filter((pair) => pair.length === 2 && pair.every(Number.isFinite));
  const flip_idx = form.flipText.split(",").map((x) => Number(x.trim())).filter(Number.isFinite);
  return {
    task_type: form.task_type,
    classes: classes.length ? classes : [{ id: 0, name: "object", color: "#0f766e" }],
    keypoints: form.task_type === "pose" ? keypoints : [],
    skeleton: form.task_type === "pose" ? skeleton : [],
    flip_idx: form.task_type === "pose" ? (flip_idx.length === keypoints.length ? flip_idx : keypoints.map((_, idx) => idx)) : [],
  };
}

function pointToSvg(evt, svg) {
  const rect = svg.getBoundingClientRect();
  return {
    x: Math.min(1, Math.max(0, (evt.clientX - rect.left) / rect.width)),
    y: Math.min(1, Math.max(0, (evt.clientY - rect.top) / rect.height)),
  };
}

function annotationSignature(annotation) {
  return JSON.stringify(annotation || { version: 1, instances: [] });
}

function imageStatus(validation, image) {
  if (!image) return "empty";
  const issues = validation?.issues?.filter((issue) => issue.image === image.name) || [];
  if (issues.some((issue) => issue.severity === "error")) return "error";
  if (issues.some((issue) => issue.severity === "warning")) return "warning";
  return image.annotated ? "annotated" : "empty";
}

function statusLabel(status) {
  return { error: "错误", warning: "警告", annotated: "已标", empty: "未标" }[status] || status;
}

const KEYPOINT_COLORS = ["#e11d48", "#2563eb", "#16a34a", "#d97706", "#7c3aed", "#0891b2", "#db2777", "#65a30d", "#ea580c", "#4f46e5"];

function keypointColor(schema, name) {
  const index = Math.max(0, schema?.keypoints?.indexOf(name) ?? 0);
  return KEYPOINT_COLORS[index % KEYPOINT_COLORS.length];
}

function nextKeypoint(schema, current) {
  const keypoints = schema?.keypoints || [];
  if (!keypoints.length) return "";
  const index = keypoints.indexOf(current);
  return keypoints[(index + 1) % keypoints.length] || keypoints[0];
}

function AnnotationCanvas({ project, image, schema, annotation, setAnnotation, activeClass, tool, activeKeypoint, setActiveKeypoint, zoom }) {
  const svgRef = useRef(null);
  const [draft, setDraft] = useState([]);
  const [draftBox, setDraftBox] = useState(null);
  const [selected, setSelected] = useState(null);
  const [drag, setDrag] = useState(null);
  const [liveAnnotation, setLiveAnnotation] = useState(null);
  const [contextMenu, setContextMenu] = useState(null);
  const src = image ? imageUrl(project.id, image.name) : "";
  const displayAnnotation = liveAnnotation || annotation;

  useEffect(() => {
    setSelected(null);
    setDrag(null);
    setDraft([]);
    setDraftBox(null);
    setLiveAnnotation(null);
    setContextMenu(null);
  }, [image?.name]);

  function normalizedBox(start, end) {
    const minX = Math.min(start.x, end.x);
    const maxX = Math.max(start.x, end.x);
    const minY = Math.min(start.y, end.y);
    const maxY = Math.max(start.y, end.y);
    return {
      cx: (minX + maxX) / 2,
      cy: (minY + maxY) / 2,
      w: Math.max(0.002, maxX - minX),
      h: Math.max(0.002, maxY - minY),
    };
  }

  function clampBox(box) {
    const halfW = box.w / 2;
    const halfH = box.h / 2;
    return {
      ...box,
      cx: Math.min(1 - halfW, Math.max(halfW, box.cx)),
      cy: Math.min(1 - halfH, Math.max(halfH, box.cy)),
    };
  }

  function isSelected(type, instanceIndex, key) {
    return selected?.type === type && selected.instanceIndex === instanceIndex && selected.key === key;
  }

  function pointInBox(pt, box) {
    if (!box) return false;
    return pt.x >= box.cx - box.w / 2 && pt.x <= box.cx + box.w / 2 && pt.y >= box.cy - box.h / 2 && pt.y <= box.cy + box.h / 2;
  }

  function selectOnly(next) {
    setSelected(next);
    setDraftBox(null);
    setContextMenu(null);
  }

  function addPolygonPoint(evt) {
    if (tool !== "polygon" || schema.task_type !== "segment") return;
    setDraft((current) => [...current, pointToSvg(evt, svgRef.current)]);
  }

  function finishPolygon() {
    if (draft.length < 3) return;
    setAnnotation({
      ...annotation,
      instances: [...(annotation?.instances || []), { type: "polygon", class_id: Number(activeClass), points: draft }],
    });
    setDraft([]);
  }

  function handlePointerDown(evt) {
    if (!svgRef.current) return;
    if (evt.button === 2) return;
    const pt = pointToSvg(evt, svgRef.current);
    if (schema.task_type === "pose" && tool === "bbox") {
      setSelected(null);
      setDrag({ type: "create-bbox", start: pt, current: pt });
      setDraftBox(normalizedBox(pt, pt));
      return;
    }
    if (schema.task_type === "pose" && tool === "keypoint") {
      const targetIndex =
        (annotation?.instances || []).findIndex((inst) => inst.type === "pose" && pointInBox(pt, inst.bbox));
      if (targetIndex >= 0) {
        const instances = JSON.parse(JSON.stringify(annotation?.instances || []));
        const inst = instances[targetIndex];
        if (inst) {
          inst.keypoints = schema.keypoints.map((name) => {
            const existing = (inst.keypoints || []).find((p) => p.name === name) || { name, x: 0, y: 0, v: 0 };
            return name === activeKeypoint ? { name, x: pt.x, y: pt.y, v: 2 } : existing;
          });
          setAnnotation({ ...annotation, instances });
          setSelected({ type: "keypoint", instanceIndex: targetIndex, key: activeKeypoint });
          setActiveKeypoint(nextKeypoint(schema, activeKeypoint));
        }
      }
      return;
    }
    addPolygonPoint(evt);
  }

  function handlePointerMove(evt) {
    if (!svgRef.current || !drag) return;
    const pt = pointToSvg(evt, svgRef.current);
    if (drag.type === "create-bbox") {
      setDraftBox(normalizedBox(drag.start, pt));
      setDrag({ ...drag, current: pt });
      return;
    }
    const source = liveAnnotation || annotation;
    const instances = JSON.parse(JSON.stringify(source?.instances || []));
    if (drag.type === "keypoint") {
      const inst = instances[drag.instanceIndex];
      inst.keypoints = schema.keypoints.map((name) => {
        const existing = inst.keypoints.find((p) => p.name === name) || { name, x: 0, y: 0, v: 0 };
        return name === drag.key ? { name, x: pt.x, y: pt.y, v: 2 } : existing;
      });
      setLiveAnnotation({ ...source, instances });
      return;
    }
    if (drag.type === "polygon-point") {
      instances[drag.instanceIndex].points[drag.pointIndex] = pt;
      setLiveAnnotation({ ...source, instances });
      return;
    }
    if (drag.type === "bbox") {
      const inst = instances[drag.instanceIndex];
      inst.bbox = clampBox({ ...drag.startBox, cx: drag.startBox.cx + pt.x - drag.start.x, cy: drag.startBox.cy + pt.y - drag.start.y });
      setLiveAnnotation({ ...source, instances });
    }
  }

  function handlePointerUp(evt) {
    if (!drag) return;
    if (drag.type === "create-bbox") {
      const end = pointToSvg(evt, svgRef.current);
      const bbox = normalizedBox(drag.start, end);
      if (bbox.w > 0.004 && bbox.h > 0.004) {
        const inst = {
          type: "pose",
          class_id: Number(activeClass),
          bbox,
          keypoints: schema.keypoints.map((name) => ({ name, x: 0, y: 0, v: 0 })),
        };
        const nextIndex = (annotation?.instances || []).length;
        setAnnotation({ ...annotation, instances: [...(annotation?.instances || []), inst] });
        setSelected({ type: "bbox", instanceIndex: nextIndex, key: "bbox" });
      }
      setDraftBox(null);
    }
    if (liveAnnotation && drag.type !== "create-bbox") {
      setAnnotation(liveAnnotation);
      setLiveAnnotation(null);
    }
    setDrag(null);
  }

  function startKeypointDrag(instanceIndex, name, evt) {
    evt.stopPropagation();
    evt.currentTarget.setPointerCapture?.(evt.pointerId);
    selectOnly({ type: "keypoint", instanceIndex, key: name });
    setDrag({ type: "keypoint", instanceIndex, key: name });
  }

  function startPolygonPointDrag(instanceIndex, pointIndex, evt) {
    evt.stopPropagation();
    evt.currentTarget.setPointerCapture?.(evt.pointerId);
    selectOnly({ type: "polygon-point", instanceIndex, key: pointIndex });
    setDrag({ type: "polygon-point", instanceIndex, pointIndex });
  }

  function startBboxDrag(instanceIndex, box, evt) {
    evt.stopPropagation();
    if (schema.task_type === "pose" && tool === "keypoint") {
      const pt = pointToSvg(evt, svgRef.current);
      const instances = JSON.parse(JSON.stringify(annotation?.instances || []));
      const inst = instances[instanceIndex];
      if (inst) {
        inst.keypoints = schema.keypoints.map((name) => {
          const existing = (inst.keypoints || []).find((p) => p.name === name) || { name, x: 0, y: 0, v: 0 };
          return name === activeKeypoint ? { name, x: pt.x, y: pt.y, v: 2 } : existing;
        });
        setAnnotation({ ...annotation, instances });
        setSelected({ type: "keypoint", instanceIndex, key: activeKeypoint });
        setActiveKeypoint(nextKeypoint(schema, activeKeypoint));
      }
      return;
    }
    evt.currentTarget.setPointerCapture?.(evt.pointerId);
    selectOnly({ type: "bbox", instanceIndex, key: "bbox" });
    setDrag({ type: "bbox", instanceIndex, start: pointToSvg(evt, svgRef.current), startBox: { ...box } });
  }

  function deleteSelection(target) {
    const instances = [...(annotation?.instances || [])];
    if (target.type === "bbox") {
      instances.splice(target.instanceIndex, 1);
    } else if (target.type === "keypoint") {
      const inst = instances[target.instanceIndex];
      inst.keypoints = schema.keypoints.map((name) => {
        const existing = inst.keypoints.find((p) => p.name === name) || { name, x: 0, y: 0, v: 0 };
        return name === target.key ? { name, x: 0, y: 0, v: 0 } : existing;
      });
    } else if (target.type === "polygon-point") {
      const inst = instances[target.instanceIndex];
      if (inst.points.length <= 3) instances.splice(target.instanceIndex, 1);
      else inst.points.splice(target.key, 1);
    }
    setAnnotation({ ...annotation, instances });
    setSelected(null);
    setContextMenu(null);
  }

  function handleContextMenu(target, evt) {
    evt.preventDefault();
    evt.stopPropagation();
    selectOnly(target);
    setContextMenu({ target, x: evt.clientX, y: evt.clientY });
  }

  function movePoint(instanceIndex, pointIndex, evt) {
    startPolygonPointDrag(instanceIndex, pointIndex, evt);
  }

  function moveKeypoint(instanceIndex, name, evt) {
    startKeypointDrag(instanceIndex, name, evt);
  }

  /*
    Keypoint placement is intentionally conservative: an empty click only places
    the active keypoint when a bbox is already selected and that keypoint is not
    visible yet. Existing points and boxes require selection + drag.
  */
  function handleCanvasContextMenu(evt) {
    evt.preventDefault();
  }

  /*
    Keep segment polygon creation unchanged except for selected point dragging,
    because the requested change is about pose keypoints and boxes.
  */

  if (!image) {
    return <div className="empty-state"><ImageIcon size={32} />选择一张图片开始标注</div>;
  }

  const baseWidth = Math.min(image.width || 1200, 1400);
  const stageWidth = Math.round(baseWidth * zoom);

  return (
    <div className="canvas-scroll">
      {contextMenu && (
        <div className="context-menu" style={{ left: contextMenu.x, top: contextMenu.y }}>
          <div className="context-menu-item" onClick={() => deleteSelection(contextMenu.target)}>删除</div>
        </div>
      )}
      <div className="image-stage" style={{ width: stageWidth, aspectRatio: `${image.width} / ${image.height}` }}>
        <img src={src} className="canvas-img" alt={image.name} draggable={false} />
        <svg
          ref={svgRef}
          className="canvas-svg"
          viewBox="0 0 1 1"
          preserveAspectRatio="none"
          onDoubleClick={finishPolygon}
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          onPointerCancel={() => {
            setDrag(null);
            setDraftBox(null);
          }}
          onContextMenu={handleCanvasContextMenu}
        >
          {(displayAnnotation?.instances || []).map((inst, instanceIndex) => {
            const color = clsColor(schema, inst.class_id);
            if (inst.type === "polygon") {
              const points = inst.points.map((p) => `${p.x},${p.y}`).join(" ");
              return (
                <g key={instanceIndex}>
                  <polygon points={points} fill={color} fillOpacity="0.22" stroke={color} strokeWidth="0.001" />
                  {inst.points.map((p, pointIndex) => {
                    const selectedPoint = isSelected("polygon-point", instanceIndex, pointIndex);
                    return (
                      <g key={pointIndex}>
                        {selectedPoint && <circle cx={p.x} cy={p.y} r="0.005" fill="none" stroke="#f59e0b" strokeWidth="0.001" />}
                        <circle
                          cx={p.x}
                          cy={p.y}
                          r="0.004"
                          fill="#ffffff"
                          stroke={selectedPoint ? "#f59e0b" : color}
                          strokeWidth="0.001"
                          onPointerDown={(evt) => movePoint(instanceIndex, pointIndex, evt)}
                          onContextMenu={(evt) => handleContextMenu({ type: "polygon-point", instanceIndex, key: pointIndex }, evt)}
                        />
                      </g>
                    );
                  })}
                </g>
              );
            }
            const box = inst.bbox || { cx: 0.5, cy: 0.5, w: 0.1, h: 0.1 };
            const selectedBox = isSelected("bbox", instanceIndex, "bbox");
            const kptMap = Object.fromEntries((inst.keypoints || []).map((p) => [p.name, p]));
            return (
              <g key={instanceIndex}>
                {selectedBox && (
                  <rect
                    x={box.cx - box.w / 2}
                    y={box.cy - box.h / 2}
                    width={box.w}
                    height={box.h}
                    fill="none"
                    stroke="#f59e0b"
                    strokeWidth="0.002"
                    strokeDasharray="0.01 0.006"
                  />
                )}
                <rect
                  x={box.cx - box.w / 2}
                  y={box.cy - box.h / 2}
                  width={box.w}
                  height={box.h}
                  fill="transparent"
                  stroke={color}
                  strokeWidth="0.001"
                  onPointerDown={(evt) => startBboxDrag(instanceIndex, box, evt)}
                  onContextMenu={(evt) => handleContextMenu({ type: "bbox", instanceIndex, key: "bbox" }, evt)}
                />
                {(schema.skeleton || []).map(([a, b], idx) => {
                  const pa = kptMap[schema.keypoints[a]];
                  const pb = kptMap[schema.keypoints[b]];
                  if (!pa || !pb || pa.v === 0 || pb.v === 0) return null;
                  return <line key={idx} x1={pa.x} y1={pa.y} x2={pb.x} y2={pb.y} stroke={color} strokeOpacity="0.55" strokeWidth="0.001" />;
                })}
                {schema.keypoints.map((name) => {
                  const p = kptMap[name] || { x: 0, y: 0, v: 0 };
                  if (!p.v) return null;
                  const selectedPoint = isSelected("keypoint", instanceIndex, name);
                  const kpColor = keypointColor(schema, name);
                  return (
                    <g key={name}>
                      {selectedPoint && <circle cx={p.x} cy={p.y} r="0.008" fill="none" stroke="#111827" strokeWidth="0.0015" />}
                      <circle
                        cx={p.x}
                        cy={p.y}
                        r="0.005"
                        fill={kpColor}
                        stroke="#ffffff"
                        strokeWidth="0.0015"
                        onPointerDown={(evt) => moveKeypoint(instanceIndex, name, evt)}
                        onContextMenu={(evt) => handleContextMenu({ type: "keypoint", instanceIndex, key: name }, evt)}
                      />
                    </g>
                  );
                })}
              </g>
            );
          })}
          {draft.length > 0 && <polyline points={draft.map((p) => `${p.x},${p.y}`).join(" ")} fill="none" stroke="#f59e0b" strokeWidth="0.001" />}
          {draftBox && (
            <rect
              x={draftBox.cx - draftBox.w / 2}
              y={draftBox.cy - draftBox.h / 2}
              width={draftBox.w}
              height={draftBox.h}
              fill="#f59e0b"
              fillOpacity="0.08"
              stroke="#f59e0b"
              strokeWidth="0.001"
              strokeDasharray="0.01 0.006"
            />
          )}
        </svg>
      </div>
    </div>
  );
}

const SchemaPanel = ({ schema, setSchema, selectedProject }) => {
  const [draft, setDraft] = useState(schema);
  useEffect(() => setDraft(schema), [schema]);
  if (!draft) return null;

  function updateClass(index, patch) {
    const classes = [...draft.classes];
    classes[index] = { ...classes[index], ...patch };
    setDraft({ ...draft, classes });
  }

  function addClass() {
    const next = draft.classes.length ? Math.max(...draft.classes.map((c) => Number(c.id))) + 1 : 0;
    setDraft({ ...draft, classes: [...draft.classes, { id: next, name: `class_${next}`, color: "#2563eb" }] });
  }

  function removeClass(index) {
    if (draft.classes.length <= 1) return;
    setDraft({ ...draft, classes: draft.classes.filter((_, i) => i !== index) });
  }

  function setKeypoints(text) {
    const keypoints = text.split(",").map((x) => x.trim()).filter(Boolean);
    setDraft({
      ...draft,
      keypoints,
      flip_idx: keypoints.map((_, idx) => draft.flip_idx?.[idx] ?? idx),
      skeleton: draft.skeleton?.filter(([a, b]) => a < keypoints.length && b < keypoints.length) || [],
    });
  }

  function setSkeleton(text) {
    const skeleton = text
      .split(",")
      .map((pair) => pair.trim().split("-").map((x) => Number(x.trim())))
      .filter((pair) => pair.length === 2 && pair.every(Number.isFinite));
    setDraft({ ...draft, skeleton });
  }

  async function save() {
    const saved = await api.saveSchema(selectedProject.id, draft);
    setSchema(saved);
  }

  return (
    <section className="panel">
      <h2><Settings size={16} />标签与骨架</h2>
      <div className="class-list">
        {draft.classes.map((item, index) => (
          <div className="class-row" key={item.id}>
            <input type="color" value={item.color} onChange={(evt) => updateClass(index, { color: evt.target.value })} />
            <input value={item.name} onChange={(evt) => updateClass(index, { name: evt.target.value })} />
            <button className="icon-btn" title="删除类别" onClick={() => removeClass(index)}><Trash2 size={15} /></button>
          </div>
        ))}
      </div>
      <button onClick={addClass}><Plus size={15} />添加类别</button>
      {draft.task_type === "pose" && (
        <div className="stack section-gap">
          <label>关键点顺序，逗号分隔</label>
          <textarea value={draft.keypoints.join(", ")} onChange={(evt) => setKeypoints(evt.target.value)} />
          <label>骨架连线，例如 0-1, 1-2</label>
          <input value={(draft.skeleton || []).map(([a, b]) => `${a}-${b}`).join(", ")} onChange={(evt) => setSkeleton(evt.target.value)} />
          <label>翻转映射</label>
          <input value={(draft.flip_idx || []).join(", ")} onChange={(evt) => setDraft({ ...draft, flip_idx: evt.target.value.split(",").map((x) => Number(x.trim())).filter(Number.isFinite) })} />
        </div>
      )}
      <button className="primary" onClick={save}><Save size={15} />保存配置</button>
    </section>
  );
};

function ProjectCenter({ projects, setSelectedProjectId, setPage, importForm, setImportForm, createForm, setCreateForm, refreshProjects, setMessage }) {
  const [actionStatus, setActionStatus] = useState("");

  function enterProject(projectId) {
    setSelectedProjectId(projectId);
    setPage("overview");
  }

  async function doCreate() {
    try {
      setActionStatus("正在创建项目...");
      const project = await api.createProject({
        name: createForm.name,
        task_type: createForm.task_type,
        project_schema: schemaFromForm(createForm),
      });
      await refreshProjects(project.id);
      enterProject(project.id);
      const text = `项目“${project.name}”已创建，已进入项目工作区。`;
      setActionStatus(text);
      setMessage(text);
    } catch (err) {
      const text = `创建项目失败：${err.message}`;
      setActionStatus(text);
      setMessage(text);
    }
  }

  async function doImport() {
    try {
      setActionStatus("正在导入项目...");
      const project = await api.importProject(importForm);
      await refreshProjects(project.id);
      enterProject(project.id);
      const text = `项目“${project.name}”已导入，已进入项目工作区。`;
      setActionStatus(text);
      setMessage(text);
    } catch (err) {
      const text = `导入失败：${err.message}`;
      setActionStatus(text);
      setMessage(text);
    }
  }

  async function doImportCurrent() {
    try {
      setActionStatus("正在导入当前 Pose 数据...");
      const project = await api.importCurrent();
      await refreshProjects(project.id);
      enterProject(project.id);
      const text = `当前 Pose 数据已导入为“${project.name}”。`;
      setActionStatus(text);
      setMessage(text);
    } catch (err) {
      const text = `导入当前数据失败：${err.message}`;
      setActionStatus(text);
      setMessage(text);
    }
  }

  return (
    <div className="project-center">
      <section className="center-hero">
        <div>
          <span className="eyebrow">Project Center</span>
          <h2>选择一个视觉项目开始工作</h2>
          <p>进入项目后再上传图片、编辑标签、标注、划分数据集和训练模型。</p>
        </div>
        <div className="hero-metrics">
          <span><b>{projects.length}</b>项目</span>
          <span><b>{projects.reduce((sum, p) => sum + (p.images?.length || 0), 0)}</b>图片</span>
        </div>
      </section>

      {actionStatus && <p className={`action-status ${actionStatus.includes("失败") ? "error" : ""}`}>{actionStatus}</p>}

      <section className="project-grid">
        {projects.map((project) => {
          const annotated = (project.images || []).filter((img) => img.annotated).length;
          return (
            <button className="project-card" key={project.id} onClick={() => enterProject(project.id)}>
              <div>
                <strong>{project.name}</strong>
                <span>{project.task_type || project.schema?.task_type}</span>
              </div>
              <div className="project-card-stats">
                <span>{project.images?.length || 0} 图</span>
                <span>{annotated} 已标</span>
              </div>
            </button>
          );
        })}
        {projects.length === 0 && <div className="empty-state"><FolderInput size={32} /><strong>还没有项目</strong><span>创建或导入一个项目后再进入工作区。</span></div>}
      </section>

      <div className="page-grid two-col">
        <section className="panel">
          <h2><Plus size={16} />创建项目</h2>
          <div className="stack">
            <input value={createForm.name} onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })} placeholder="项目名" />
            <select value={createForm.task_type} onChange={(e) => setCreateForm({ ...createForm, task_type: e.target.value })}>
              <option value="pose">Pose</option>
              <option value="segment">Segment</option>
            </select>
            <label>标签类别，逗号分隔</label>
            <input value={createForm.classesText} onChange={(e) => setCreateForm({ ...createForm, classesText: e.target.value })} placeholder="stem, root" />
            {createForm.task_type === "pose" && (
              <>
                <label>关键点，按顺序逗号分隔</label>
                <textarea value={createForm.keypointsText} onChange={(e) => setCreateForm({ ...createForm, keypointsText: e.target.value })} />
                <label>骨架连线，例如 0-1, 1-2</label>
                <input value={createForm.skeletonText} onChange={(e) => setCreateForm({ ...createForm, skeletonText: e.target.value })} />
                <label>翻转映射，例如 2, 1, 0</label>
                <input value={createForm.flipText} onChange={(e) => setCreateForm({ ...createForm, flipText: e.target.value })} />
              </>
            )}
          </div>
          <button className="primary" onClick={doCreate}><Plus size={15} />创建并进入</button>
        </section>
        <section className="panel">
          <h2><FolderInput size={16} />项目导入</h2>
          <div className="stack">
            <input value={importForm.name} onChange={(e) => setImportForm({ ...importForm, name: e.target.value })} placeholder="项目名" />
            <select value={importForm.task_type} onChange={(e) => setImportForm({ ...importForm, task_type: e.target.value })}>
              <option value="pose">Pose</option>
              <option value="segment">Segment</option>
            </select>
            <input value={importForm.image_dir} onChange={(e) => setImportForm({ ...importForm, image_dir: e.target.value })} placeholder="图片目录，例如 images" />
            <input value={importForm.label_dir || ""} onChange={(e) => setImportForm({ ...importForm, label_dir: e.target.value })} placeholder="标签目录，例如 labels" />
            <input value={importForm.data_yaml || ""} onChange={(e) => setImportForm({ ...importForm, data_yaml: e.target.value })} placeholder="data.yaml，例如 yolo-pose/data.yaml" />
          </div>
          <div className="button-row">
            <button className="primary" onClick={doImport}><FolderInput size={15} />导入并进入</button>
            <button onClick={doImportCurrent}>导入当前 Pose 数据</button>
          </div>
        </section>
      </div>
    </div>
  );
}

function ProjectOverview({ project, validation, setPage }) {
  const images = project?.images || [];
  const annotated = images.filter((img) => img.annotated).length;
  const summary = validation?.summary || {};
  if (!project) return null;
  return (
    <div className="overview-grid">
      <section className="panel overview-primary">
        <h2>{project.name}</h2>
        <p>当前工作区只作用于这个项目。上传、标注、划分和训练都会写入该项目目录。</p>
        <div className="metric-row">
          <span><b>{images.length}</b>图片</span>
          <span><b>{annotated}</b>已标注</span>
          <span><b>{summary.invalid_images || 0}</b>错误</span>
          <span><b>{validation?.status || "未检查"}</b>预检</span>
        </div>
      </section>
      <section className="panel">
        <h2>下一步</h2>
        <div className="quick-actions">
          <button onClick={() => setPage("data")}><Upload size={15} />上传图片</button>
          <button onClick={() => setPage("labels")}><Settings size={15} />标签与骨架</button>
          <button className="primary" onClick={() => setPage("annotate")}><ImageIcon size={15} />开始标注</button>
          <button onClick={() => setPage("train")}><Brain size={15} />训练与导出</button>
        </div>
      </section>
    </div>
  );
}

function ProjectDataPage({ selectedProject, refreshProjects, setMessage }) {
  const [files, setFiles] = useState([]);
  const [actionStatus, setActionStatus] = useState("");

  async function uploadFiles() {
    if (!selectedProject || files.length === 0) return;
    await api.uploadImages(selectedProject.id, files);
    setFiles([]);
    setActionStatus(`已上传 ${files.length} 张图片到“${selectedProject.name}”。`);
    setMessage("图片已上传");
    await refreshProjects(selectedProject.id);
  }

  return (
    <div className="page-grid two-col">
      <section className="panel">
        <h2><Upload size={16} />上传图片</h2>
        {actionStatus && <p className={`action-status ${actionStatus.includes("失败") ? "error" : ""}`}>{actionStatus}</p>}
        <p>上传的图片会保存到当前项目目录，不会覆盖你的原始数据。</p>
        <input type="file" multiple accept=".bmp,.jpg,.jpeg,.png,.webp,.tif,.tiff,image/*" onChange={(e) => setFiles([...e.target.files])} />
        <div className="upload-list">{files.map((file) => <span key={file.name}>{file.name}</span>)}</div>
        <button className="primary" disabled={!selectedProject || files.length === 0} onClick={uploadFiles}><Upload size={15} />上传到当前项目</button>
      </section>
      <section className="panel">
        <h2><ImageIcon size={16} />项目图片</h2>
        <div className="compact-list">
          {(selectedProject?.images || []).slice(0, 80).map((img) => <span key={img.name}>{img.name}</span>)}
          {(selectedProject?.images || []).length === 0 && <p>这个项目还没有图片。</p>}
        </div>
      </section>
    </div>
  );
}

function AnnotatePage(props) {
  const {
    images,
    selectedImageName,
    setSelectedImageName,
    schema,
    selectedProject,
    selectedImage,
    annotation,
    setAnnotation,
    activeClass,
    setActiveClass,
    activeKeypoint,
    setActiveKeypoint,
    tool,
    setTool,
    saveAnnotation,
    undoAnnotation,
    redoAnnotation,
    canUndo,
    canRedo,
    saveState,
    validation,
    removeSelectedInstance,
    zoom,
    setZoom,
    message,
  } = props;

  return (
    <div className="annotation-page">
      <aside className="panel image-list">
        <h2><ImageIcon size={16} />图片</h2>
        {images.map((img) => (
          <button key={img.name} className={img.name === selectedImageName ? "selected" : ""} onClick={() => setSelectedImageName(img.name)} title={img.name}>
            <span>{img.name}</span>
            <b className={`status-badge ${imageStatus(validation, img)}`}>{statusLabel(imageStatus(validation, img))}</b>
          </button>
        ))}
      </aside>
      <section className="workspace">
        <div className="toolbar">
          <select value={activeClass} onChange={(e) => setActiveClass(Number(e.target.value))}>
            {(schema?.classes || []).map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
          {schema?.task_type === "segment" ? (
            <button className={tool === "polygon" ? "active" : ""} onClick={() => setTool("polygon")}><MousePointer2 size={15} />多边形</button>
          ) : (
            <>
              <button className={tool === "bbox" ? "active" : ""} onClick={() => setTool("bbox")}><BoxSelect size={15} />框</button>
              <button className={tool === "keypoint" ? "active" : ""} onClick={() => setTool("keypoint")}><MousePointer2 size={15} />关键点</button>
              <select value={activeKeypoint} onChange={(e) => setActiveKeypoint(e.target.value)}>
                {(schema?.keypoints || []).map((kp) => <option key={kp} value={kp}>{kp}</option>)}
              </select>
              <span className="keypoint-current"><i style={{ background: keypointColor(schema, activeKeypoint) }} />当前：{activeKeypoint || "未定义"}</span>
            </>
          )}
          <button onClick={undoAnnotation} disabled={!canUndo}><Undo2 size={15} />撤销</button>
          <button onClick={redoAnnotation} disabled={!canRedo}><Undo2 size={15} className="redo-icon" />重做</button>
          <button onClick={saveAnnotation}><Save size={15} />保存</button>
          <button onClick={removeSelectedInstance}><Trash2 size={15} />删除最后实例</button>
          <div className="zoom-controls">
            <button title="缩小" onClick={() => setZoom(Math.max(0.25, Number((zoom - 0.25).toFixed(2))))}><ZoomOut size={15} /></button>
            <input type="range" min="0.25" max="4" step="0.05" value={zoom} onChange={(e) => setZoom(Number(e.target.value))} />
            <button title="放大" onClick={() => setZoom(Math.min(4, Number((zoom + 0.25).toFixed(2))))}><ZoomIn size={15} /></button>
            <span>{Math.round(zoom * 100)}%</span>
          </div>
          <span className={`save-state ${saveState}`}>{saveState === "dirty" ? "未保存" : saveState === "saving" ? "保存中" : "已保存"}</span>
        </div>
        {schema && selectedProject ? (
          <AnnotationCanvas project={selectedProject} image={selectedImage} schema={schema} annotation={annotation} setAnnotation={setAnnotation} activeClass={activeClass} tool={tool} activeKeypoint={activeKeypoint} setActiveKeypoint={setActiveKeypoint} zoom={zoom} />
        ) : (
          <div className="empty-state"><ImageIcon size={32} /><strong>还没有打开项目</strong><span>请先到“数据”页面导入或上传图片。</span></div>
        )}
      </section>
      <aside className="panel">
        <h2>实例</h2>
        <div className="instances">
          {(annotation.instances || []).map((inst, idx) => (
            <div key={idx}><span style={{ background: clsColor(schema, inst.class_id) }} />{idx + 1}. {clsName(schema, inst.class_id)} 路 {inst.type}</div>
          ))}
        </div>
        {message && <p className="message">{message}</p>}
      </aside>
    </div>
  );
}

function SplitPage({ project, schema, setSchema, setMessage }) {
  const [split, setSplit] = useState({ train: 0.8, val: 0.15, test: 0.05, seed: 42 });
  const [result, setResult] = useState(null);

  async function makeSplit() {
    const next = await api.split(project.id, split);
    setResult(next);
    setMessage(`已划分：train=${next.train.length}, val=${next.val.length}, test=${next.test.length}`);
  }

  if (!project || !schema) return <div className="empty-state"><Scissors size={32} />请先选择项目</div>;

  return (
    <div className="page-grid two-col">
      <section className="panel">
        <h2><Scissors size={16} />数据集划分</h2>
        <div className="grid-2">
          <label>Train<input type="number" step="0.01" value={split.train} onChange={(e) => setSplit({ ...split, train: Number(e.target.value) })} /></label>
          <label>Val<input type="number" step="0.01" value={split.val} onChange={(e) => setSplit({ ...split, val: Number(e.target.value) })} /></label>
          <label>Test<input type="number" step="0.01" value={split.test} onChange={(e) => setSplit({ ...split, test: Number(e.target.value) })} /></label>
          <label>Seed<input type="number" value={split.seed} onChange={(e) => setSplit({ ...split, seed: Number(e.target.value) })} /></label>
        </div>
        <button className="primary" onClick={makeSplit}><Scissors size={15} />生成划分</button>
        {result && <pre>{JSON.stringify({ train: result.train.length, val: result.val.length, test: result.test.length, seed: result.seed }, null, 2)}</pre>}
      </section>
      <SchemaPanel schema={schema} setSchema={setSchema} selectedProject={project} />
    </div>
  );
}

function TrainingPage({ project, schema, validation, refreshValidation, setMessage }) {
  const [train, setTrain] = useState(blankTrain);
  const [job, setJob] = useState(null);
  const [materialized, setMaterialized] = useState(null);
  const [busy, setBusy] = useState("");

  useEffect(() => {
    if (!job || ["completed", "failed"].includes(job.status)) return;
    const timer = setInterval(async () => setJob(await api.job(job.id)), 1500);
    return () => clearInterval(timer);
  }, [job]);

  async function runValidation() {
    if (!project) return;
    setBusy("validation");
    try {
      await refreshValidation(project.id);
      setMessage("预检完成");
    } catch (err) {
      setMessage(err.message);
    } finally {
      setBusy("");
    }
  }

  async function materialize() {
    setBusy("materialize");
    try {
      const next = await api.materialize(project.id);
      setMaterialized(next);
      setMessage("YOLO 数据集已生成");
    } catch (err) {
      setMessage(err.message);
    } finally {
      setBusy("");
    }
  }

  async function startTrain() {
    const payload = { ...train, task_type: schema.task_type, model: train.model || null };
    try {
      setJob(await api.train(project.id, payload));
    } catch (err) {
      setMessage(err.message);
    }
  }

  async function exportOnnx() {
    if (!job) return;
    setJob(await api.exportOnnx(job.id));
  }

  if (!project || !schema) return <div className="empty-state"><Brain size={32} />请先选择项目</div>;
  const summary = validation?.summary || {};
  const trainReady = Boolean(validation?.train_ready);
  const artifacts = Object.entries(job?.artifacts || {});

  return (
    <section className="panel train-page workflow">
      <h2><Brain size={16} />训练闭环</h2>
      <div className={`preflight ${validation?.status || "unknown"}`}>
        <div>
          <strong>训练前检查：{validation?.status || "未检查"}</strong>
          <span>{summary.annotated_images || 0}/{summary.total_images || 0} 已标注，{summary.invalid_images || 0} 张错误，{summary.empty_annotations || 0} 张空标注</span>
        </div>
        <button onClick={runValidation} disabled={busy === "validation"}><Settings size={15} />重新预检</button>
      </div>
      {validation?.issues?.length > 0 && (
        <div className="issue-list">
          {validation.issues.slice(0, 12).map((issue, idx) => (
            <div key={`${issue.code}-${issue.image}-${idx}`} className={`issue ${issue.severity}`}>
              <b>{issue.severity}</b><span>{issue.image || "项目"}</span><p>{issue.message}</p>
            </div>
          ))}
        </div>
      )}
      <div className="workflow-step">
        <div>
          <strong>1. 生成 YOLO 数据集</strong>
          <span>预检通过后生成训练目录并展示 data.yaml。</span>
        </div>
        <button onClick={materialize} disabled={!trainReady || busy === "materialize"}><GitBranch size={15} />生成数据集</button>
      </div>
      {materialized && (
        <div className="materialized">
          <div className="split-counts">
            {Object.entries(materialized.splits || {}).map(([name, value]) => <span key={name}>{name}: {value.images} 图 / {value.labels} 标</span>)}
            <span>缺失标签：{materialized.missing_labels}</span>
          </div>
          <pre>{materialized.data_yaml}</pre>
        </div>
      )}
      <div className="workflow-step">
        <div>
          <strong>2. 训练参数</strong>
          <span>训练按钮会在预检失败时禁用。</span>
        </div>
      </div>
      <div className="grid-4">
        <label>模型<input placeholder={schema.task_type === "pose" ? "yolov8n-pose.pt" : "yolov8n-seg.pt"} value={train.model} onChange={(e) => setTrain({ ...train, model: e.target.value })} /></label>
        <label>名称<input value={train.name} onChange={(e) => setTrain({ ...train, name: e.target.value })} /></label>
        <label>Epochs<input type="number" value={train.epochs} onChange={(e) => setTrain({ ...train, epochs: Number(e.target.value) })} /></label>
        <label>Imgsz<input type="number" value={train.imgsz} onChange={(e) => setTrain({ ...train, imgsz: Number(e.target.value) })} /></label>
        <label>Batch<input type="number" value={train.batch} onChange={(e) => setTrain({ ...train, batch: Number(e.target.value) })} /></label>
        <label>Device<input value={train.device} onChange={(e) => setTrain({ ...train, device: e.target.value })} /></label>
        <label>LR<input type="number" step="0.001" value={train.lr0} onChange={(e) => setTrain({ ...train, lr0: Number(e.target.value) })} /></label>
        <label>Patience<input type="number" value={train.patience} onChange={(e) => setTrain({ ...train, patience: Number(e.target.value) })} /></label>
      </div>
      <div className="button-row">
        <button className="primary" disabled={!trainReady} onClick={startTrain}><Brain size={15} />开始训练</button>
        {job && artifacts.some(([name]) => name.endsWith(".pt")) && <button onClick={exportOnnx}><GitBranch size={15} />导出 ONNX</button>}
      </div>
      {job && (
        <div className="job">
          <div className="job-head"><span>{job.status}</span>{job.error && <b>{job.error}</b>}</div>
          <pre>{job.log || "等待日志..."}</pre>
          <div className="downloads">
            {artifacts.map(([name, meta]) => <a key={name} href={artifactUrl(job.id, name)}><Download size={14} />{name}{meta?.size ? ` (${Math.round(meta.size / 1024)} KB)` : ""}</a>)}
          </div>
        </div>
      )}
    </section>
  );
}

export default function App() {
  const [page, setPage] = useState("projects");
  const [navOpen, setNavOpen] = useState(true);
  const [projects, setProjects] = useState([]);
  const [selectedProjectId, setSelectedProjectId] = useState("");
  const [images, setImages] = useState([]);
  const [selectedImageName, setSelectedImageName] = useState("");
  const [schema, setSchema] = useState(null);
  const [annotation, setAnnotation] = useState({ version: 1, instances: [] });
  const [activeClass, setActiveClass] = useState(0);
  const [activeKeypoint, setActiveKeypoint] = useState("");
  const [tool, setTool] = useState("polygon");
  const [zoom, setZoom] = useState(1);
  const [importForm, setImportForm] = useState(blankImport);
  const [createForm, setCreateForm] = useState(blankCreate);
  const [message, setMessage] = useState("");
  const [validation, setValidation] = useState(null);
  const [saveState, setSaveState] = useState("saved");
  const [historyPast, setHistoryPast] = useState([]);
  const [historyFuture, setHistoryFuture] = useState([]);
  const [loadedSignature, setLoadedSignature] = useState(annotationSignature(annotation));

  const selectedProject = useMemo(() => projects.find((p) => p.id === selectedProjectId), [projects, selectedProjectId]);
  const selectedImage = useMemo(() => images.find((img) => img.name === selectedImageName), [images, selectedImageName]);

  async function refreshProjects(preferredId = selectedProjectId) {
    try {
      const loaded = await api.projects();
      setProjects(loaded);
      const nextId = preferredId || "";
      if (nextId) setSelectedProjectId(nextId);
      setMessage(loaded.length ? "" : "还没有项目。请在项目中心创建或导入项目。");
    } catch (err) {
      setMessage(`后端未连接：${err.message}`);
    }
  }

  async function refreshProjectData(projectId = selectedProjectId) {
    if (!projectId) return;
    const [imgData, schemaData, validationData] = await Promise.all([api.images(projectId), api.schema(projectId), api.validation(projectId).catch(() => null)]);
    setImages(imgData.items);
    setSchema(schemaData);
    setValidation(validationData);
    setActiveClass(schemaData.classes?.[0]?.id ?? 0);
    setActiveKeypoint(schemaData.keypoints?.[0] || "");
    setSelectedImageName((current) => imgData.items.some((img) => img.name === current) ? current : imgData.items[0]?.name || "");
    setTool(schemaData.task_type === "pose" ? "bbox" : "polygon");
  }

  useEffect(() => {
    refreshProjects();
  }, []);

  useEffect(() => {
    refreshProjectData().catch((err) => setMessage(err.message));
  }, [selectedProjectId]);

  useEffect(() => {
    if (!selectedProjectId || !selectedImageName) return;
    api.annotation(selectedProjectId, selectedImageName)
      .then((data) => {
        setAnnotation(data.annotation);
        setLoadedSignature(annotationSignature(data.annotation));
        setHistoryPast([]);
        setHistoryFuture([]);
        setSaveState("saved");
      })
      .catch((err) => setMessage(err.message));
  }, [selectedProjectId, selectedImageName]);

  useEffect(() => {
    setSaveState(annotationSignature(annotation) === loadedSignature ? "saved" : "dirty");
  }, [annotation, loadedSignature]);

  async function refreshValidation(projectId = selectedProjectId) {
    if (!projectId) return null;
    const next = await api.validation(projectId);
    setValidation(next);
    return next;
  }

  function updateAnnotation(nextOrUpdater) {
    setAnnotation((current) => {
      const next = typeof nextOrUpdater === "function" ? nextOrUpdater(current) : nextOrUpdater;
      if (annotationSignature(next) === annotationSignature(current)) return current;
      setHistoryPast((past) => [...past.slice(-30), current]);
      setHistoryFuture([]);
      return next;
    });
  }

  async function saveAnnotation(options = {}) {
    if (!selectedProject || !selectedImage) return;
    if (annotationSignature(annotation) === loadedSignature && !options.force) return;
    setSaveState("saving");
    await api.saveAnnotation(selectedProject.id, selectedImage.name, annotation);
    setLoadedSignature(annotationSignature(annotation));
    setSaveState("saved");
    setMessage("标注已保存");
    await refreshProjectData(selectedProject.id);
    await refreshValidation(selectedProject.id).catch(() => null);
  }

  function removeSelectedInstance() {
    updateAnnotation({ ...annotation, instances: (annotation.instances || []).slice(0, -1) });
  }

  function undoAnnotation() {
    setHistoryPast((past) => {
      if (!past.length) return past;
      const previous = past[past.length - 1];
      setHistoryFuture((future) => [annotation, ...future]);
      setAnnotation(previous);
      return past.slice(0, -1);
    });
  }

  function redoAnnotation() {
    setHistoryFuture((future) => {
      if (!future.length) return future;
      const next = future[0];
      setHistoryPast((past) => [...past, annotation]);
      setAnnotation(next);
      return future.slice(1);
    });
  }

  function leaveProject() {
    setSelectedProjectId("");
    setSelectedImageName("");
    setImages([]);
    setSchema(null);
    setValidation(null);
    setAnnotation({ version: 1, instances: [] });
    setPage("projects");
  }

  useEffect(() => {
    if (saveState !== "dirty" || !selectedProject || !selectedImage) return;
    const timer = setTimeout(() => {
      saveAnnotation().catch((err) => setMessage(err.message));
    }, 1200);
    return () => clearTimeout(timer);
  }, [saveState, annotation, selectedProject?.id, selectedImage?.name]);

  useEffect(() => {
    function onKeyDown(evt) {
      const tag = evt.target?.tagName?.toLowerCase();
      if (tag === "input" || tag === "textarea" || tag === "select") return;
      if ((evt.ctrlKey || evt.metaKey) && evt.key.toLowerCase() === "s") {
        evt.preventDefault();
        saveAnnotation({ force: true }).catch((err) => setMessage(err.message));
      } else if ((evt.ctrlKey || evt.metaKey) && evt.key.toLowerCase() === "z") {
        evt.preventDefault();
        undoAnnotation();
      } else if ((evt.ctrlKey || evt.metaKey) && evt.key.toLowerCase() === "y") {
        evt.preventDefault();
        redoAnnotation();
      } else if (evt.key === "ArrowRight" && page === "annotate" && selectedProjectId) {
        const idx = images.findIndex((img) => img.name === selectedImageName);
        if (idx >= 0 && images[idx + 1]) setSelectedImageName(images[idx + 1].name);
      } else if (evt.key === "ArrowLeft" && page === "annotate" && selectedProjectId) {
        const idx = images.findIndex((img) => img.name === selectedImageName);
        if (idx > 0) setSelectedImageName(images[idx - 1].name);
      } else if (evt.key.toLowerCase() === "b" && schema?.task_type === "pose") {
        setTool("bbox");
      } else if (evt.key.toLowerCase() === "k" && schema?.task_type === "pose") {
        setTool("keypoint");
      } else if (evt.key.toLowerCase() === "p" && schema?.task_type === "segment") {
        setTool("polygon");
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [annotation, historyPast, historyFuture, images, page, schema, selectedImageName, saveState]);

  return (
    <div className="app">
      <header>
        <div>
          <h1>Vision Studio</h1>
          <p>{selectedProject ? `当前项目：${selectedProject.name}` : "项目优先的本地图像标注、训练与导出工作台"}</p>
        </div>
        <div className="api-pill">{apiBase}</div>
      </header>
      {!selectedProject ? (
        <main className="project-shell">
          <ProjectCenter
            projects={projects}
            setSelectedProjectId={setSelectedProjectId}
            setPage={setPage}
            importForm={importForm}
            setImportForm={setImportForm}
            createForm={createForm}
            setCreateForm={setCreateForm}
            refreshProjects={refreshProjects}
            setMessage={setMessage}
          />
          {message && <p className="global-message">{message}</p>}
        </main>
      ) : (
        <div className="workspace-shell">
          <section className="project-header">
            <button onClick={leaveProject}>返回项目列表</button>
            <div>
              <span className="eyebrow">Project Workspace</span>
              <h2>{selectedProject.name}</h2>
            </div>
            <div className="project-meta">
              <span>{selectedProject.task_type || schema?.task_type}</span>
              <span>{images.length} 图片</span>
              <span>{images.filter((img) => img.annotated).length} 已标</span>
              <span>{validation?.status || "未检查"}</span>
            </div>
          </section>
          <nav className="workspace-tabs" aria-label="项目子页面">
            {[
              ["overview", "概览"],
              ["data", "数据"],
              ["labels", "标签与骨架"],
              ["annotate", "标注"],
              ["split", "划分"],
              ["train", "训练导出"],
            ].map(([id, label]) => (
              <button key={id} className={page === id ? "selected" : ""} onClick={() => setPage(id)}>{label}</button>
            ))}
          </nav>
          <main className="page-main workspace-main">
            {page === "overview" && <ProjectOverview project={selectedProject} validation={validation} setPage={setPage} />}
            {page === "data" && <ProjectDataPage selectedProject={selectedProject} refreshProjects={refreshProjects} setMessage={setMessage} />}
            {page === "labels" && schema && <SchemaPanel schema={schema} setSchema={setSchema} selectedProject={selectedProject} />}
            {page === "annotate" && (
              <AnnotatePage
                images={images}
                selectedImageName={selectedImageName}
                setSelectedImageName={setSelectedImageName}
                schema={schema}
                selectedProject={selectedProject}
                selectedImage={selectedImage}
                annotation={annotation}
                setAnnotation={updateAnnotation}
                activeClass={activeClass}
                setActiveClass={setActiveClass}
                activeKeypoint={activeKeypoint}
                setActiveKeypoint={setActiveKeypoint}
                tool={tool}
                setTool={setTool}
                saveAnnotation={saveAnnotation}
                undoAnnotation={undoAnnotation}
                redoAnnotation={redoAnnotation}
                canUndo={historyPast.length > 0}
                canRedo={historyFuture.length > 0}
                saveState={saveState}
                validation={validation}
                removeSelectedInstance={removeSelectedInstance}
                zoom={zoom}
                setZoom={setZoom}
                message={message}
              />
            )}
            {page === "split" && <SplitPage project={selectedProject} schema={schema} setSchema={setSchema} setMessage={setMessage} />}
            {page === "train" && <TrainingPage project={selectedProject} schema={schema} validation={validation} refreshValidation={refreshValidation} setMessage={setMessage} />}
            {message && page !== "annotate" && <p className="global-message">{message}</p>}
          </main>
        </div>
      )}
    </div>
  );
}
