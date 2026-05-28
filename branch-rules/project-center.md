# Project Center Branch Rules

This branch owns the Vision Studio project center.

Annotation work is delegated to the child branch `feature/project-center-annotation`. The project center branch should not directly change annotation canvas behavior unless the controller conversation explicitly asks it to.

## Required Reading

Read these files before changing code:

- `D:\projects\2\vision_studio\agent.md`
- `D:\projects\2\vision_studio\README.md`
- `D:\projects\2\vision_studio\AGENTS.md`

## Branch

Use this branch:

```powershell
git checkout feature/project-center
```

## Scope

This conversation only owns:

- Project list.
- Project creation.
- Project import.
- Entering a project.
- Project metadata and project status organization.
- Project center layout, buttons, loading states, empty states, and error messages.
- CVAT-like project management experience.

## Allowed Changes

Allowed files and areas:

- `frontend/src/App.jsx` code directly related to the project center, project creation, project import, and project selection.
- `frontend/src/styles.css` styles directly related to the project center.
- `frontend/src/api.js` API calls needed by the project center.
- Backend endpoints directly related to project creation, project list, and project import.
- `README.md` if project center usage changes.

## Forbidden Changes

Do not modify:

- Annotation canvas interaction logic.
- bbox, polygon, or pose annotation behavior.
- Annotation center tool behavior delegated to `feature/project-center-annotation`.
- Training workflow.
- Model workbench.
- Model prediction.
- GPU or training job control.
- Unrelated refactors.

If a forbidden area must be changed, stop and report the reason to the controller conversation.

## Workflow

- Do not push.
- Check git status before changing files.
- Do not revert user changes or other branch work.
- Keep edits tightly scoped to this branch's responsibility.
- If shared component extraction or broad frontend restructuring is needed, stop and ask the controller conversation first.
- Commit locally when the task is complete.

## Deliverable

Report back with:

- Commit id.
- Files changed.
- What was changed.
- Verification commands and results.
- Any files or decisions that need controller review.

## Goal

Make the project center clearer, more stable, and easier to extend for multi-project and multi-model workflows.
