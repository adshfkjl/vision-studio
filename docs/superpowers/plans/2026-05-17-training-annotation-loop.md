# Training Annotation Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reliable local workflow for validating annotations, materializing YOLO data, training, monitoring jobs, exporting ONNX, and safely editing annotations.

**Architecture:** Add backend validation and materialization preview services, expose them through FastAPI, and wire the React training page into a guided preflight-to-export workflow. Add lightweight annotation history and save-state handling in the existing frontend before larger component extraction.

**Tech Stack:** FastAPI, Python unittest, React, Vite, file-based JSON project storage, Ultralytics YOLO.

---

### Task 1: Backend Validation

**Files:**
- Create: `backend/vision_studio/validation.py`
- Modify: `backend/vision_studio/main.py`
- Test: `backend/tests/test_validation.py`

- [ ] Add failing tests for valid pose data, invalid coordinates, and missing keypoints.
- [ ] Implement `validate_project(project)`.
- [ ] Add `GET /api/projects/{project_id}/validation`.
- [ ] Run backend tests.

### Task 2: Materialization Preview

**Files:**
- Modify: `backend/vision_studio/datasets.py`
- Modify: `backend/vision_studio/main.py`
- Test: `backend/tests/test_materialize_preview.py`

- [ ] Add failing test for preview counts and `data.yaml` output.
- [ ] Implement `materialize_preview(project, dataset)`.
- [ ] Change `/api/projects/{project_id}/materialize` to return dataset metadata.
- [ ] Run backend tests.

### Task 3: Training Job States

**Files:**
- Modify: `backend/vision_studio/jobs.py`
- Modify: `backend/vision_studio/train_runner.py`
- Modify: `backend/vision_studio/main.py`
- Test: `backend/tests/test_training_gate.py`

- [ ] Add failing test that invalid projects cannot start training.
- [ ] Validate before `start_training`.
- [ ] Store clearer job status and artifact metadata.
- [ ] Run backend tests.

### Task 4: Frontend API And Training Workflow

**Files:**
- Modify: `frontend/src/api.js`
- Modify: `frontend/src/App.jsx`
- Modify: `frontend/src/styles.css`

- [ ] Add API client functions for validation and materialization.
- [ ] Replace training page with guided preflight, materialize, train, export sections.
- [ ] Disable training when validation has blocking errors.
- [ ] Run frontend build.

### Task 5: Annotation Safety

**Files:**
- Modify: `frontend/src/App.jsx`
- Modify: `frontend/src/styles.css`

- [ ] Add annotation history state for undo and redo.
- [ ] Add dirty/saving/saved status.
- [ ] Autosave after edits and save before image navigation.
- [ ] Add keyboard shortcuts for save, undo, redo, previous image, next image, and tool switching.
- [ ] Run frontend build.

### Task 6: Git Repository

**Files:**
- Create: `.gitignore`

- [ ] Initialize git in `vision_studio` if absent.
- [ ] Ignore generated data, dependency folders, logs, caches, build output, and model weights.
- [ ] Commit source, docs, and lockfiles.
