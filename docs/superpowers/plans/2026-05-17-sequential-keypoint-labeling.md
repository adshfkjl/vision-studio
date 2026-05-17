# Sequential Keypoint Labeling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make pose labeling faster by placing keypoints in schema order with one click per point, while preserving point selection and drag adjustment.

**Architecture:** Keep the existing SVG annotation canvas. Add keypoint color helpers and sequential active-keypoint advancement in React state, based entirely on `schema.keypoints` so projects can have any number of keypoints.

**Tech Stack:** React, Vite, SVG pointer events, existing FastAPI backend.

---

### Task 1: Sequential Placement State

**Files:**
- Modify: `frontend/src/App.jsx`

- [ ] Add helpers for keypoint color and next-keypoint lookup.
- [ ] After placing a keypoint, advance `activeKeypoint` to the next schema keypoint.
- [ ] Keep the keypoint dropdown as manual override.

### Task 2: Drag Existing Points

**Files:**
- Modify: `frontend/src/App.jsx`

- [ ] Preserve existing point drag behavior.
- [ ] Make already placed keypoints easier to hit and visibly selected.
- [ ] Ensure dragging a point does not advance the active keypoint.

### Task 3: Visual Semantics

**Files:**
- Modify: `frontend/src/App.jsx`
- Modify: `frontend/src/styles.css`

- [ ] Render each semantic keypoint in a stable color based on its schema index.
- [ ] Show the current keypoint color and name in the toolbar.
- [ ] Keep skeleton lines subdued so keypoint color remains readable.

### Task 4: Verification

**Files:**
- Existing tests and frontend build.

- [ ] Run `npm run build`.
- [ ] Run backend tests.
- [ ] Commit the implementation.
