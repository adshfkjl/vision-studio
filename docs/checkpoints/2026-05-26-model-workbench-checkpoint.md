---
status: in-progress
branch: main
timestamp: 2026-05-26T13:17:00+08:00
files_modified: []
---

## Working on: Model Workbench Checkpoint

### Summary

Current state is saved after adding the standalone model workbench and prediction flow for Vision Studio. The latest `App.jsx` bbox interaction edits were preserved as a checkpoint commit.

### Decisions Made

- Prediction is independent from the crowded project workspace tabs and is exposed through the top-level `模型工作台` entry.
- Backend prediction supports trained artifacts or local `.pt` / `.onnx` paths and returns preview URLs plus structured instances for future pre-labeling.
- Rollback marker: `checkpoint-20260526-model-workbench`.
- Feature commit: `889252f feat: add model prediction workbench`.
- Checkpoint commit before this note: `314dd50 chore: checkpoint current app state`.

### Remaining Work

1. Add model pre-labeling by saving prediction output as editable draft annotations.
2. Add batch prediction for project folders and selected project images.
3. Add evaluation dashboards for false positives, false negatives, class distribution, and industrial metrics.
4. Verify the UI visually in browser when local browser policy allows localhost access.

### Notes

- Working tree was clean after saving the checkpoint commit.
- Validation already run before checkpoint: backend unittest suite passed, frontend production build passed, and diff whitespace check passed.
- Browser automation was blocked by local security policy for `http://127.0.0.1:5173`, so no screenshot was captured.
