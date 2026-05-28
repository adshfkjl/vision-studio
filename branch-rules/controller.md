# Controller Conversation Rules

This conversation is the controller for Vision Studio.

## Required Reading

Read these files before planning or merging work:

- `D:\projects\2\vision_studio\agent.md`
- `D:\projects\2\vision_studio\README.md`
- `D:\projects\2\vision_studio\AGENTS.md`
- `D:\projects\2\vision_studio\branch-rules\project-center.md`
- `D:\projects\2\vision_studio\branch-rules\model-workbench.md`

## Branch

Default branch:

- `main`

Feature branches currently delegated:

- `feature/project-center`
- `feature/model-workbench`

## Responsibilities

The controller may modify any project file when needed.

The controller owns:

- Branch planning.
- Cross-branch coordination.
- Reviewing delegated branch results.
- Merging `feature/project-center`.
- Merging `feature/model-workbench`.
- Resolving merge conflicts.
- Startup issues.
- Build issues.
- Final verification.
- Deciding when a change is ready to push, if the user asks to push.

## Rules

- Do not push unless the user explicitly asks.
- Before merging, inspect each branch's latest commit and diff.
- Do not silently overwrite delegated branch work.
- If both delegated branches changed the same file, review the conflict manually and preserve both intended behaviors.
- Keep `README.md` updated when setup, usage, structure, or behavior changes.
- Keep `agent.md` and branch rules updated when responsibilities change.

## Verification

When possible, run:

```powershell
cd D:\projects\2\vision_studio\frontend
npm run build
```

For backend changes, run the relevant backend test or import check before claiming the merge is safe.

## Final Report

After controller work, report:

- Current branch.
- Branches merged or created.
- Commit ids involved.
- Files changed.
- Verification commands and results.
- Remaining risks or manual checks.

