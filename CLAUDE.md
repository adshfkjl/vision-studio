# Vision Studio Claude Harness

用途：面向制造现场的视觉质量智能平台原型，覆盖项目管理、图像标注、数据集构建、YOLO 训练、模型导出、模型预测、预标注和质量分析演进。

技术栈：FastAPI backend + React/Vite frontend + Ultralytics/ONNX model tooling + local filesystem project storage.

跑测试：

```powershell
npm test
npm run test:e2e
npm run build
npm run harness:check
```

## 必读入口

所有 Claude 对话先读：

- `AGENTS.md`
- `README.md`
- `agent.md`

如果是主控对话，再读：

- `branch-rules/controller.md`

如果是分支对话，按分支只读并遵守对应文件：

- `branch-rules/project-center.md`
- `branch-rules/annotation-center.md`
- `branch-rules/model-workbench.md`

## 工作边界

- 不要 push，除非用户明确要求。
- 主控 worktree 是 `D:\projects\2\vision_studio`，保持在 `main`。
- 分支对话只能在自己的 worktree 工作，不要切换分支。
- 不要静默覆盖其他对话或用户已有改动。
- 修改 setup、usage、structure、behavior 时同步更新 `README.md`。
- 完成代码或内容修改后检查 diff，创建本地 commit。

## 行为准则（Karpathy 原则）

### Think Before Coding

- 先读项目结构和现有实现，再动代码。
- 假设必须说清楚，不确定就问。
- 有多个可行方案时说明取舍。

### 消除信息差

- 用户描述有歧义或缺失关键信息时，先追问再动手。
- 指令看似完整时也要核对上下文、现有分支和未提交改动。
- 质疑要带证据：说明观察到的问题和替代方案。

### 讨论与执行分离

- 讨论阶段只分析、提问、列方案，不修改文件。
- 用户明确要求执行后，按最小可验证目标推进。

### Simplicity First

- 不添加与当前目标无关的抽象、配置或灵活性。
- 优先复用项目现有模式和已有测试。

### Surgical Changes

- 只动必须动的代码。
- 不顺手重构无关模块。
- 每个改动都能追溯到用户请求或验证需求。

### Goal-Driven Execution

- 每个任务转成可验证目标。
- 多步骤任务先列计划，执行中保持状态透明。
- 完成前运行相关验证，失败要说明具体错误。

## Harness 自动审查闭环

- `PreToolUse`：拦截直接修改 `.env` 和危险命令。
- `SessionStart`：注入 git 状态、最近提交和最近审查摘要。
- `PreCompact`：压缩前保存当前分支、未提交文件和最近提交。
- `Stop`：生成轻量审查报告到 `.claude/reviews/`。
- `PostToolUse`：默认未启用；需要自动格式化时再打开。

## Skill 路由

| 任务类型 | 推荐 Skill | 触发条件 |
| --- | --- | --- |
| Harness 配置 | `harness-init` / `harness-mode` | 调整 `.claude` hooks、模式、检查脚本 |
| 前端设计 | `frontend-design` | 修改 React UI、标注界面、项目中心、模型工作台视觉体验 |
| Bug 修复 | `systematic-debugging` | 启动失败、交互异常、测试失败、环境差异 |
| 高风险改动 | `test-driven-development` | 标注交互、训练流程、API 契约、跨模块行为 |
| 完成验证 | `verification-before-completion` | 声称修复、完成、可合并、可提交前 |

