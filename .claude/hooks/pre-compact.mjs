import { execSync } from "child_process";
import { existsSync, readFileSync, readdirSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

// PreCompact Hook
// 在上下文压缩前保存关键状态，压缩后自动注入回系统提示
// 确保长会话中模型不会丢失当前任务目标

const __dirname = dirname(fileURLToPath(import.meta.url));
const projectRoot = join(__dirname, "../..");

const run = (cmd) => {
  try {
    return execSync(cmd, { cwd: projectRoot, encoding: "utf-8", timeout: 3000 }).trim();
  } catch {
    return "";
  }
};

const lines = [
  "[PreCompact: 会话状态快照]",
  "",
];

// 1. 当前任务（从 git 状态推断）
const branch = run("git rev-parse --abbrev-ref HEAD") || "（非 git 目录）";
const status = run("git status --short") || "";
const changedFiles = status.split("\n").filter(Boolean).map(l => l.trim());
if (changedFiles.length > 0) {
  lines.push(`当前分支: ${branch}`);
  lines.push(`未提交变更: ${changedFiles.length} 个文件`);
  lines.push(...changedFiles.slice(0, 10).map(f => `  ${f}`));
  if (changedFiles.length > 10) lines.push(`  ...及其他 ${changedFiles.length - 10} 个文件`);
  lines.push("");
}

// 2. 最近提交
const lastCommit = run("git log -1 --oneline");
if (lastCommit) {
  lines.push(`最近提交: ${lastCommit}`);
  lines.push("");
}

// 3. OpenSpec 待处理变更
const changesDir = join(projectRoot, "openspec/changes");
if (existsSync(changesDir)) {
  const pending = readdirSync(changesDir).filter(f => f !== "archive" && !f.startsWith("."));
  if (pending.length > 0) {
    lines.push(`OpenSpec 待处理: ${pending.join(", ")}`);
    lines.push("");
  }
}

// 4. 审查报告累积
const reviewsDir = join(projectRoot, ".claude/reviews");
if (existsSync(reviewsDir)) {
  const count = readdirSync(reviewsDir).filter(f => f.endsWith(".md")).length;
  if (count > 0) {
    lines.push(`审查报告: ${count} 次已累积`);
    lines.push("");
  }
}

lines.push("---");

process.stdout.write(lines.join("\n"));
