# Project First Navigation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Vision Studio use a CVAT-like project-first workflow and redesign the frontend into a clearer local workbench where users must select or create a project before uploading, annotating, splitting, or training.

**Architecture:** Keep the current React single-page app and FastAPI backend. Rework the frontend shell into two modes: project center with project cards, and project workspace with scoped sub-navigation, persistent project header, denser panels, clearer status indicators, and less form clutter.

**Tech Stack:** React, Vite, FastAPI API client already present in `frontend/src/api.js`.

---

### Task 1: Project Center

**Files:**
- Modify: `frontend/src/App.jsx`
- Modify: `frontend/src/styles.css`

- [ ] Create a project center view that shows create/import controls and project cards.
- [ ] Selecting a project enters the workspace and defaults to the project overview/data page.
- [ ] Keep visible success/error feedback for create/import.
- [ ] Use a workbench-style visual design with compact cards, direct actions, and visible project metadata.

### Task 2: Project Workspace

**Files:**
- Modify: `frontend/src/App.jsx`
- Modify: `frontend/src/styles.css`

- [ ] Hide upload, annotation, split, and training pages unless a project is selected.
- [ ] Add a persistent project header with project name, task type, image count, annotated count, and back-to-projects action.
- [ ] Replace global nav with project-scoped tabs: Overview, Data, Labels, Annotate, Split, Train.
- [ ] Restyle the shell so the current project is visually dominant and the API/status metadata is secondary.

### Task 3: Scoped Pages

**Files:**
- Modify: `frontend/src/App.jsx`
- Modify: `frontend/src/styles.css`

- [ ] Add an overview page with project health and next actions.
- [ ] Move upload controls into the project data page.
- [ ] Keep schema editor in the labels page.

### Task 4: Verification And Commit

**Files:**
- Existing tests and frontend build.

- [ ] Run backend tests.
- [ ] Run `npm run build`.
- [ ] Commit the navigation refactor.
