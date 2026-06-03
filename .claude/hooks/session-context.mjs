import { execSync } from "child_process";
import { readdirSync, readFileSync, existsSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const projectRoot = join(__dirname, "../..");

const run = (cmd) => {
  try {
    return execSync(cmd, { cwd: projectRoot, encoding: "utf-8", timeout: 3000, windowsHide: true }).trim();
  } catch {
    return "";
  }
};

const branch = run("git rev-parse --abbrev-ref HEAD") || "（非 git 目录）";
const status = run("git status --short") || "";
const log = run("git log --oneline -10") || "";

const lines = ["--- SessionStart Hook ---", `分支: ${branch}`];

if (status) {
  lines.push("---", "变更:");
  lines.push(status);
} else {
  lines.push("---", "无未提交变更");
}

if (log) {
  lines.push("---", "最近 10 条提交:");
  lines.push(log);
}

// Harness 状态感知（阶段 + 模式）
const statePath = join(projectRoot, ".claude/.harness-state");
if (existsSync(statePath)) {
  try {
    const state = JSON.parse(readFileSync(statePath, "utf-8"));
    lines.push("---");
    lines.push(`Harness 状态: 阶段=${state.phase || "build"}  模式=${state.mode || "full"}`);
  } catch {}
}

// 加载最近 5 次审查报告
const reviewsDir = join(projectRoot, ".claude/reviews");
if (existsSync(reviewsDir)) {
  const reviewFiles = readdirSync(reviewsDir)
    .filter(f => f.endsWith(".md"))
    .sort()
    .reverse()
    .slice(0, 5);

  if (reviewFiles.length > 0) {
    lines.push("---", `最近 ${reviewFiles.length} 次审查:`);
    for (const file of reviewFiles) {
      const content = readFileSync(join(reviewsDir, file), "utf-8");
      const flagSection = (content.split("### 规则检查\n")[1] || "").split("\n###")[0] || "";
      const flags = flagSection.split("\n").filter(l => l.trim());
      lines.push(`${file.replace(".md", "")}:`);
      lines.push(...flags.map(f => `  ${f}`));
    }
  }
}

// OpenSpec 待处理变更
const openspecChangesDir = join(projectRoot, "openspec/changes");
const openspecChanges = existsSync(openspecChangesDir)
  ? readdirSync(openspecChangesDir).filter(f => f !== "archive" && !f.startsWith("."))
  : [];
if (openspecChanges.length > 0) {
  lines.push("---", "OpenSpec 待处理变更:");
  lines.push(...openspecChanges.map(c => "  " + c));
}

// 检查 CLAUDE.md 是否未初始化
const claudeMdPath = join(projectRoot, "CLAUDE.md");
if (existsSync(claudeMdPath)) {
  const claudeContent = readFileSync(claudeMdPath, "utf-8");
  if (claudeContent.includes("【待填写")) {
    lines.push("---", "⚠️ CLAUDE.md 还有占位符未替换，请对 AI 说：帮我初始化 Harness");
  }
}

lines.push("------------------------");

process.stdout.write(lines.join("\n"));
