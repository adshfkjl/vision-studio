# Controller Conversation Rules

This conversation is the controller for Vision Studio.

## Required Reading

Read these files before planning or merging work:

- `D:\projects\2\vision_studio\agent.md`
- `D:\projects\2\vision_studio\README.md`
- `D:\projects\2\vision_studio\AGENTS.md`
- `D:\projects\2\vision_studio\branch-rules\project-center.md`
- `D:\projects\2\vision_studio\branch-rules\annotation-center.md`
- `D:\projects\2\vision_studio\branch-rules\model-workbench.md`

## Branch

Default branch:

- `main`

Default controller worktree:

- `D:\projects\2\vision_studio`

Feature branches currently delegated:

- `feature/project-center`
- `feature/project-center-annotation`
- `feature/model-workbench`

Delegated worktrees:

- `D:\projects\2\vision_studio_worktrees\project-center` -> `feature/project-center`
- `D:\projects\2\vision_studio_worktrees\annotation-center` -> `feature/project-center-annotation`
- `D:\projects\2\vision_studio_worktrees\model-workbench` -> `feature/model-workbench`

## Responsibilities

The controller may modify any project file when needed.

The controller owns:

- Branch planning.
- Cross-branch coordination.
- Reviewing delegated branch results.
- Merging `feature/project-center`.
- Merging `feature/project-center-annotation`.
- Merging `feature/model-workbench`.
- Resolving merge conflicts.
- Startup issues.
- Build issues.
- Final verification.
- Deciding when a change is ready to push, if the user asks to push.

## Rules

- Do not push unless the user explicitly asks.
- Keep `D:\projects\2\vision_studio` as the controller worktree on `main`.
- Do not run delegated feature work in the controller worktree.
- Each delegated conversation must work only inside its assigned worktree.
- Do not let two conversations share the same worktree.
- Before merging, inspect each branch's latest commit and diff.
- Do not silently overwrite delegated branch work.
- If both delegated branches changed the same file, review the conflict manually and preserve both intended behaviors.
- Keep `README.md` updated when setup, usage, structure, or behavior changes.
- Keep `agent.md` and branch rules updated when responsibilities change.

## Git Lock Handling

If a delegated conversation reports `.git/index.lock` or cannot switch branches:

1. Do not delete the lock immediately.
2. Check for running git processes:

   ```powershell
   Get-Process git -ErrorAction SilentlyContinue
   ```

3. If a git process is still running, wait for it to finish.
4. If no git process exists and the lock is stale, the controller may remove the stale lock.
5. Prefer solving the cause by moving the conversation to its assigned worktree instead of repeatedly switching branches in one shared directory.

## Worktree Policy

Use these directories when assigning tasks:

```text
D:\projects\2\vision_studio                              main / controller only
D:\projects\2\vision_studio_worktrees\project-center     feature/project-center
D:\projects\2\vision_studio_worktrees\annotation-center  feature/project-center-annotation
D:\projects\2\vision_studio_worktrees\model-workbench    feature/model-workbench
```

If a new branch is created for parallel work, create a new worktree for it before giving it to another conversation.

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
