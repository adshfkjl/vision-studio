# Model Workbench Branch Rules

This branch owns the Vision Studio model workbench.

## Required Reading

Read these files before changing code:

- `D:\projects\2\vision_studio\agent.md`
- `D:\projects\2\vision_studio\README.md`
- `D:\projects\2\vision_studio\AGENTS.md`
- `D:\projects\2\vision_studio\docs\checkpoints\2026-05-26-model-workbench-checkpoint.md`

## Branch

Use this branch:

```powershell
cd D:\projects\2\vision_studio_worktrees\model-workbench
```

Assigned worktree:

- `D:\projects\2\vision_studio_worktrees\model-workbench`

Assigned branch:

- `feature/model-workbench`

Do not switch branches in this worktree. If another branch is needed, ask the controller conversation to create a new worktree.

## Scope

This conversation only owns:

- Model workbench page.
- Single-image prediction.
- Selecting project training artifacts such as `best.pt`, `last.pt`, or ONNX files.
- Using local `.pt` or `.onnx` model paths.
- Prediction result display.
- Design or implementation of future pre-labeling from prediction output.
- Backend prediction API related to the model workbench.

## Allowed Changes

Allowed files and areas:

- `frontend/src/App.jsx` code directly related to the model workbench, prediction, and model selection.
- `frontend/src/styles.css` styles directly related to the model workbench.
- `frontend/src/api.js` model prediction API calls.
- Backend endpoints and helpers directly related to model prediction, model artifact discovery, or `.pt` / `.onnx` inference.
- `README.md` if model workbench usage changes.

## Forbidden Changes

Do not modify:

- Project center creation or import flow.
- Annotation canvas interaction logic.
- bbox, polygon, or pose annotation behavior.
- Training job control logic, except for read-only access to training artifacts.
- Data import/export formats.
- Unrelated refactors.

If a forbidden area must be changed, stop and report the reason to the controller conversation.

## Workflow

- Do not push.
- Check git status before changing files.
- Work only inside `D:\projects\2\vision_studio_worktrees\model-workbench`.
- Do not use the controller worktree `D:\projects\2\vision_studio` for this branch.
- Do not switch branches from this worktree.
- Do not revert user changes or other branch work.
- Keep edits tightly scoped to this branch's responsibility.
- If the model workbench needs shared state or navigation changes in the project center, stop and ask the controller conversation first.
- Commit locally when the task is complete.

## Deliverable

Report back with:

- Commit id.
- Files changed.
- What was changed.
- Verification commands and results.
- Any files or decisions that need controller review.

## Goal

Keep the model workbench independent, clear, and ready to extend toward batch prediction and editable pre-labeling.
