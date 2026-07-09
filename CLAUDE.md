# Claude Entry

Read `PROJECT_HARNESS.md` first.
Read `harness-contract.json` for durable defaults.
Read `harness-runtime.json` only for current interview/runtime state.

Current defaults:
- language: zh-CN
- verification: npm test, 未配置独立 lint 脚本；默认用 npm test 与 npm run build 作为代码验证。, npm run build
- approval: explicit_for_risky_changes

- Treat `PROJECT_HARNESS.md` and `harness-contract.json` as canonical.
- If `bootstrap_status` is not `configured`, inspect first and continue the setup interview.
- Detect likely collaboration language from repo signals first; confirm it if unclear.
- Prefer independent reviewer/evaluator checks for artifact quality; keep only the criteria and commands in the canonical contract.
- Keep this file thin and preserve any user-authored content outside the harness-managed block.
