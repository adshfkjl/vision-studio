# Agent Improvement Audit for `D:\projects\2`

本文件只基于 `D:\projects\2` 文件夹内可读到的记录整理，没有读取 `C:\Users\cnwyr\.codex` 中的原始会话日志。`codex_conversation_sync` 中列出的外部路径仅作为同步摘要里的文本证据来源，不在本次读取范围内展开。

## 1. 参考现有证据

本次读取的本地文件：

- `D:\projects\2\codex_conversation_sync\conversation_summary.md`
- `D:\projects\2\codex_conversation_sync\conversation_index.json`
- `D:\projects\2\PROJECT.md`
- `D:\projects\2\README.md`
- `D:\projects\2\vision_studio\README.md`
- `D:\projects\2\vision_studio\AGENTS.md`
- `D:\projects\2\vision_studio\docs\checkpoints\2026-05-26-model-workbench-checkpoint.md`

可见记录范围：

- `conversation_sync` 生成于 2026-05-17，索引 74 条会话。
- 当前日期为 2026-05-27；按近 30 天统计，`D:\projects\2` 内可见的高频工作包括：Vision Studio 网站构建、YOLO pose/seg 茎秆视觉流程、硬件工程师交付文档、Codex 对话同步、hatch-pet 动画生成、Codex 重连排查、Ansys/课程题目。

## 2. 审视工作范围

本次目标不是复述所有聊天记录，而是按图片要求识别“值得封装的重复性手动工作流”。

本次只处理：

- 在 `D:\projects\2` 内有明确记录的工作。
- 重复出现、输入输出稳定、后续可能继续用到的流程。
- 适合写入项目 handoff 或后续封装成技能/自动化的内容。

本次不处理：

- 单次课程题目、单张图片解题、临时问答。
- 已经有现成技能覆盖的任务。
- 需要外部账号、网络状态或未同步原始日志才能确认的内容。

## 3. 行动标准

候选项必须至少满足一项：

- 近 30 天内重复出现。
- 出现次数不多，但流程复杂、容易遗漏步骤。
- 有明确输入、操作步骤和输出。
- 封装后能减少重复排查或避免上下文丢失。

优先级判定：

- 高：可立即创建或扩展项目文档。
- 中：记录为候选，待用户确认后创建 skill/subagent/automation。
- 低：跳过。

## 4. 候选清单

### A. Vision Studio 项目接手与维护说明

- 建议形式：项目级 `agent.md`
- 优先级：高
- 证据：
  - `conversation_summary.md` 中的“构建视觉标注训练网站”会话。
  - `vision_studio\README.md`
  - `vision_studio\AGENTS.md`
  - `vision_studio\docs\checkpoints\2026-05-26-model-workbench-checkpoint.md`
- 原因：这是当前 `D:\projects\2` 中最明显的长期工程项目，涉及前端、后端、训练、模型导出和预测工作台，后续 agent 接手成本高。
- 处理：创建本文件作为项目级接手说明。

### B. YOLO Pose/Seg 茎秆视觉训练流程

- 建议形式：候选 skill 或项目手册
- 优先级：中高
- 证据：
  - `PROJECT.md` 描述 `yolo-seg`、`yolo-pose`、`predict_gui.py`、ONNX 导出、三点 pose 关键点。
  - `conversation_summary.md` 中 AnyLabeling 二次标注训练 pose、CVAT 预标注、茎秆节点/距离分析相关会话。
- 原因：流程重复度高，且与 Vision Studio 的目标一致。
- 处理：本次不创建独立 skill；先作为后续封装候选。若继续维护旧脚本与 Vision Studio 双线流程，可创建“stem-vision-training”技能。

### C. Codex 本地对话同步与审计流程

- 建议形式：候选 skill 或自动化
- 优先级：中
- 证据：
  - `codex_conversation_sync\conversation_summary.md`
  - `codex_conversation_sync\conversation_index.json`
  - `tools\sync_codex_conversations.ps1`
- 原因：用户明确有读取本地对话、同步对话、从历史中提取重复流程的需求。
- 处理：本次只写入 `agent.md`，不创建自动化。若用户希望周期性整理，可创建每月运行一次的 automation，输出新的候选清单。

### D. 硬件工程师交付文档流程

- 建议形式：候选文档模板
- 优先级：中
- 证据：`conversation_summary.md` 中“语音识别模块最小系统板、原理图和 PCB 对接、双 INMP 麦克风、DC 电源输入、引脚分配”等记录。
- 原因：该类任务有稳定结构：读取固件/原理图、提取真实 IO、整理工程师对接需求。
- 处理：本次跳过创建，因为它不是 `vision_studio` 当前项目的直接需求。

### E. hatch-pet 动画生成与修复

- 建议形式：跳过
- 优先级：低
- 证据：`conversation_index.json` 中大量 running/jumping/review/waving 行生成与修复会话。
- 原因：虽然高频，但已有 `hatch-pet` 技能覆盖，重复在本项目创建会造成冗余。

### F. Ansys/课程题目/单次知识问答

- 建议形式：跳过
- 优先级：低
- 证据：Ansys 建模脚本、劳斯判据、机械原理题目等会话记录。
- 原因：上下文强依赖具体题目，不适合在 `vision_studio` 或 `D:\projects\2` 中创建长期资产。

## 5. 本次创建或扩展的内容

已创建/扩展：

- `D:\projects\2\vision_studio\agent.md`：本文件，记录从 `D:\projects\2` 内对话摘要与项目文件中提炼出的候选工作流。
- `D:\projects\2\vision_studio\README.md`：补充 `agent.md` 入口说明。

未创建：

- 新 skill：候选仍需确认边界。
- 新 custom subagent：没有足够稳定的接口和职责边界。
- 新 automation：用户尚未要求周期性执行。

## 6. 创建与取舍原则

后续继续审计时遵循：

- 只读取用户指定范围内的文件。
- 只封装高置信、重复、可验证的流程。
- 对已有技能覆盖的流程优先复用，不重复创建。
- 对一次性问题明确跳过。
- 对候选项保留证据来源和判断理由。

## 7. Vision Studio 后续接手要点

### 项目定位

Vision Studio 是本地 FastAPI + React 工作台，用于图像标注、数据集划分、YOLO 训练、模型导出和单图预测。

从项目文件可见的方向：

- 支持多项目管理。
- 支持 detection、segmentation、pose、classify、obb 等任务类型。
- 训练页面支持选择模型、超参数和设备。
- 模型工作台支持使用训练产物或本地 `.pt` / `.onnx` 模型做单图预测。

### 项目规则

来自 `vision_studio\AGENTS.md`：

- 每次变更都要把 `README.md` 作为必读文件。
- 影响 setup、usage、structure、behavior 时同步更新 `README.md`。
- 修改后检查 diff。
- 不要 push，除非用户明确要求。

### 启动方式

后端：

```powershell
cd D:\projects\2\vision_studio
.\run_backend.ps1
```

如果端口 `8000` 被占用：

```powershell
$env:VISION_STUDIO_PORT = "8010"
.\run_backend.ps1
```

前端：

```powershell
cd D:\projects\2\vision_studio
.\run_frontend.ps1
```

`frontend-dev.out.log` 显示：如果 5173 被占用，Vite 会自动使用 `http://127.0.0.1:5174/`。

### 已知排查点

从项目 README 与日志可见：

- 后端默认 `http://127.0.0.1:8000`。
- 前端默认通过当前 origin 的 `/api` 访问后端代理。
- 自定义后端端口时，需要设置 `VISION_STUDIO_API_PROXY_TARGET`。
- GPU 训练使用 `vision-studio-gpu` conda 环境与 `run_backend_gpu.ps1`。
- 训练产物位于 `vision_studio_data/projects/<project_id>/runs/<task>/<run_name>/weights/`。
- ONNX 导出复制到 `vision_studio_data/projects/<project_id>/exports/`。

### 后续建议

优先考虑创建的下一个资产：

- `stem-vision-training` skill：固化 `yolo-pose`、`yolo-seg`、AnyLabeling/CVAT、ONNX 导出与 Vision Studio 导入之间的流程。
- `conversation-audit` skill 或 automation：定期读取 `codex_conversation_sync`，生成“候选封装清单”。
- Vision Studio 浏览器回归测试脚本：在本地策略允许时，用 Playwright 验证项目创建、图片上传、标注画布、训练页和模型工作台。

