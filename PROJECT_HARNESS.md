# make-harness Project Harness

## Status

- run_mode: bootstrap
- bootstrap_status: configured
- sync_status: healthy
- Durable contract lives in `PROJECT_HARNESS.md` and `harness-contract.json`.
- Runtime interview/audit state lives in `harness-runtime.json`.
- Treat `/make-harness` as a single entry command: bootstrap when no harness exists, update when a healthy harness exists, and repair when drift or breakage is detected first.

## Canonical model

- `PROJECT_HARNESS.md`: human-readable durable contract
- `harness-contract.json`: machine-readable durable contract
- `harness-runtime.json`: volatile interview, audit, and sync state
- `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`: thin projections only

## Agent defaults

- Inspect the repository before asking for metadata that can be inferred.
- Confirm durable project defaults, project-local security guardrails, and execution guardrails only.
- Do not store framework-level tactics as permanent harness state.
- Use detect-first language selection: infer likely collaboration language from repo signals, then confirm if needed.
- Ask one interview question at a time and reflect runtime progress into `harness-runtime.json`.
- Prefer independent review for artifact quality; keep the review criteria and verification commands in the contract, not the workflow topology.

## Durable contract fields

These fields must stay synchronized across `PROJECT_HARNESS.md` and `harness-contract.json`:

- `communication_language`
- `project_type`
- `definition_of_done`
- `change_posture`
- `change_guardrails`
- `verification_policy`
- `approval_policy`
- `project_commands`
- `project_constraints`
- `rule_strengths`
- `communication_tone`
- `stack_summary`
- `environment`

## Durable contract values

- communication_language: zh-CN
- project_type: webapp
- definition_of_done: 默认完成标准：页面能打开；数据能保存；推理结果可视化正确；训练配置可复现；关键路径有测试或手动验证截图；相关前后端验证已运行并报告结果；完成后创建本地 commit。
- change_posture: conservative
- change_guardrails:
  - 不要 push，除非用户明确要求。
  - 完成后检查 diff、stage 变更并创建本地 commit。
  - 交付时必须报告 commit id、变更文件、验证命令和结果。
  - 修改前读取 AGENTS.md、README.md、agent.md，以及与工作范围相关的 branch-rules。
  - 保持原有网页风格，不做无关重构。
  - 遵守 controller / project-center / annotation-center / model-workbench 的 worktree 和分支边界。
  - 不要静默覆盖用户改动或其他分支/对话的工作。
  - 影响 setup、usage、structure 或 behavior 时同步更新 README.md。
  - Surgical Changes：只动必须动的文件和代码；不顺手重构无关模块。
  - Goal-Driven Execution：每个任务转成可验证目标；完成前运行相关验证并报告结果。
- verification_policy: required
- approval_policy: explicit_for_risky_changes
- project_commands:
  - frontend_dev: .\run_frontend.ps1
  - backend_dev: .\run_backend.ps1
  - backend_gpu_dev: .\run_backend_gpu.ps1
  - test: npm test
  - frontend_test: npm --prefix frontend test
  - e2e: npm run test:e2e
  - build: npm run build
  - harness_check: npm run harness:check
  - lint: 未配置独立 lint 脚本；默认用 npm test 与 npm run build 作为代码验证。
  - dev: backend: .\run_backend.ps1; frontend: .\run_frontend.ps1
- project_constraints:
  - repo_path: D:\projects\2\vision_studio
  - 项目定位：本地视觉标注、训练、推理与工业测量平台。
  - 当前核心模块：项目中心、标注中心、数据集导入、YOLO 训练、本地 pt / onnx 推理、预测页面、工业测量模块。
  - 主控 worktree 是 D:\projects\2\vision_studio，默认 main 分支。
  - 分支任务使用 D:\projects\2\vision_studio_worktrees 下对应 worktree。
  - 不要把真实 secret、硬编码密钥或调试后门写入仓库。
  - 训练、推理、数据导入导出等用户数据路径变更必须保持本地文件安全和可复现。
- rule_strengths:
  - change_guardrails: enforced
  - verification_policy: enforced
  - approval_policy: guided
  - project_constraints: enforced
  - communication_tone: advisory
- communication_tone: concise
- stack_summary:
  - FastAPI backend
  - React 18 + Vite frontend
  - Ultralytics YOLO training/export
  - local .pt / .onnx inference
  - local filesystem project storage under vision_studio_data
  - Playwright e2e smoke tests
  - Node npm scripts as root verification wrappers
- environment:
  - development: Windows local development workspace
  - runtime: Python FastAPI backend + Node/Vite frontend
  - primary_os: Windows
  - default_backend_host: 127.0.0.1
  - default_backend_port: 8000
  - default_frontend_port: 5173
  - gpu_conda_env: vision-studio-gpu

## Runtime state fields

`harness-runtime.json` tracks only volatile state such as:

- run_mode:
  - bootstrap
- bootstrap_status:
  - configured
- interview_step:
  - complete
- pending_fields:
  - (none)
- confirmed_fields:
  - communication_language
  - project_type
  - definition_of_done
  - change_posture
  - change_guardrails
  - verification_policy
  - approval_policy
  - project_commands
  - project_constraints
  - rule_strengths
  - communication_tone
  - stack_summary
  - environment
- validated_shared_fields:
  - communication_language
  - project_type
  - definition_of_done
  - change_posture
  - change_guardrails
  - verification_policy
  - approval_policy
  - project_commands
  - project_constraints
  - rule_strengths
  - communication_tone
  - stack_summary
  - environment
- drift_reasons:
  - (none)
- sync_status:
  - healthy
- entry_files_sync:
  - status: healthy
  - entry_files:
    - AGENTS.md
    - CLAUDE.md
    - GEMINI.md
  - required_shared_fields:
    - communication_language
    - project_type
    - definition_of_done
    - change_posture
    - change_guardrails
    - verification_policy
    - approval_policy
    - project_commands
    - project_constraints
    - rule_strengths
    - communication_tone
    - stack_summary
    - environment
  - last_checked_at: 2026-07-09T05:20:43+00:00
  - notes:
    - Entry files generated as thin projections from harness-contract.json and harness-runtime.json.
- language_detection:
  - strategy: detect_first_then_confirm
  - repo_signal: Chinese user request and existing mixed Chinese/English project docs
  - confidence: high
- last_audit_at:
  - 2026-07-09T05:20:43+00:00
- last_validated_at:
  - 2026-07-09T05:20:43+00:00

## State invariants

- `configured` implies `pending_fields` is empty.
- `configured` implies `interview_step` is `complete`.
- `pending_fields` and `confirmed_fields` must not overlap.
- `validated_shared_fields` may contain only shared contract fields.
- `last_validated_at` requires an explicit `sync_status` of `healthy` or `drifted`.

## Entry file principles

- Keep entry files short enough to stay obviously non-canonical.
- Entry files point back to the canonical durable contract.
- Entry files may mention runtime-state recovery, but must not duplicate the full policy block.

## Repair order

1. `harness-contract.json`
2. `harness-runtime.json`
3. `PROJECT_HARNESS.md`
4. `AGENTS.md`
5. `CLAUDE.md`
6. `GEMINI.md`

Repair durable contract first, then volatile runtime state, then projections.

## Pre-completion checklist

- All managed files exist.
- `PROJECT_HARNESS.md` and `harness-contract.json` agree on shared contract fields.
- `harness-runtime.json` invariants hold.
- Entry files are thin and aligned.
- `validated_shared_fields` matches what was actually checked.
- Change history is updated when durable defaults change.

## Change history

| Date | Change | Target | Reason |
|------|--------|--------|--------|
| 2026-07-09 | Initial make-harness bootstrap for Vision Studio | AGENTS.md, CLAUDE.md, GEMINI.md, PROJECT_HARNESS.md, harness-contract.json, harness-runtime.json | Persist project context, default execution rules, verification gates, and handoff reporting requirements. |
