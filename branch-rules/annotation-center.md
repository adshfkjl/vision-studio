# Annotation Center Branch Rules

This branch owns the Vision Studio annotation center.

## Required Reading

Read these files before changing code:

- `D:\projects\2\vision_studio\agent.md`
- `D:\projects\2\vision_studio\README.md`
- `D:\projects\2\vision_studio\AGENTS.md`
- `D:\projects\2\vision_studio\branch-rules\project-center.md`

## Branch

Use this branch:

```powershell
git checkout feature/project-center-annotation
```

Parent branch:

- `feature/project-center`

This branch is treated as a child workstream of the project center branch. The name uses `feature/project-center-annotation` because Git cannot create `feature/project-center/annotation-center` while `feature/project-center` already exists.

## Scope

This conversation only owns:

- Annotation workspace inside an opened project.
- Image selection/list behavior inside annotation flow.
- Annotation canvas behavior.
- bbox annotation.
- polygon/segmentation annotation.
- pose keypoint annotation.
- Annotation save/load behavior.
- Annotation-specific keyboard shortcuts.
- Annotation-specific right-click menu behavior.
- Annotation center layout and tool controls.

## Allowed Changes

Allowed files and areas:

- `frontend/src/App.jsx` code directly related to annotation center, annotation canvas, annotation tools, annotation save/load, and image navigation in annotation mode.
- `frontend/src/styles.css` styles directly related to annotation center and annotation canvas.
- `frontend/src/api.js` annotation save/load calls if needed.
- Backend endpoints and helpers directly related to annotation save/load or project image annotation retrieval.
- `README.md` if annotation usage changes.

## Forbidden Changes

Do not modify:

- Project creation flow.
- Project import flow.
- Project list page.
- Model workbench.
- Model prediction.
- Training workflow.
- Training job control.
- Dataset import/export format support unless the change is strictly required for annotation save/load.
- Broad frontend restructuring unrelated to annotation.

If a forbidden area must be changed, stop and report the reason to the controller conversation.

## Interaction Priorities

Annotation changes are high-risk. Preserve these behaviors unless the user explicitly changes the requirement:

- Mouse wheel zooms around the cursor and does not scroll the page.
- Holding the left button can pan the canvas without breaking annotation placement.
- bbox uses click first corner, click second corner.
- bbox drawing shows a live preview.
- Empty canvas click can start a new bbox when bbox tool is active.
- Existing bbox interior can select and move that bbox.
- Existing bbox border can select and move that bbox.
- Selected bbox has Word-like eight resize points.
- Top/bottom resize points change height only.
- Left/right resize points change width only.
- Corner resize points change width and height.
- Resize hit targets belong to the visible control points, not large invisible edge strips.
- Polygon/segmentation is user point drawing with closure/finish behavior.
- Pose keypoints should have live hover/placement feedback.
- Right-click "cancel current annotation" clears only the current unfinished annotation.
- Right-click "exit current mode" clears the current unfinished annotation and returns to mouse mode.

## Workflow

- Do not push.
- Check git status before changing files.
- Do not revert user changes or other branch work.
- Keep edits tightly scoped to annotation.
- If project-center navigation or project metadata must change, stop and ask the controller conversation first.
- Commit locally when the task is complete.

## Deliverable

Report back with:

- Commit id.
- Files changed.
- What was changed.
- Verification commands and results.
- Manual annotation interactions tested.
- Any files or decisions that need controller review.

## Goal

Make annotation reliable, predictable, and safe to evolve without breaking project management, training, or model workbench behavior.

