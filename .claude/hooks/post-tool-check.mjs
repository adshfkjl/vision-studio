import { execSync } from "child_process";
import { existsSync, readFileSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const projectRoot = join(__dirname, "../..");

// PostToolUse — 在 Write/Edit 后自动格式化
// 支持多种格式化工具，找不到时静默跳过
const FORMATTERS = [
  { check: "node_modules/.bin/prettier", cmd: (f) => `npx prettier --write "${f}"` },
  { check: ".prettierrc", cmd: (f) => `npx prettier --write "${f}"` },
  { check: "node_modules/.bin/biome", cmd: (f) => `npx biome format --write "${f}"` },
];

const input = readFileSync(0, "utf-8").trim();
if (!input) process.exit(0);

let call;
try {
  call = JSON.parse(input);
} catch {
  process.exit(0);
}

const tool = call.tool || "";
const args = call.input || {};
const filePath = args.file_path || args.path || "";

// 只对 Write/Edit 操作执行格式化
if ((tool === "Write" || tool === "Edit") && filePath) {
  // 检查项目根目录是否有格式化工具配置
  const hasFormatter = FORMATTERS.some((f) => existsSync(join(projectRoot, f.check)));
  if (!hasFormatter) process.exit(0);

  // 运行格式化（静默模式，失败不报错）
  for (const f of FORMATTERS) {
    if (existsSync(join(projectRoot, f.check))) {
      try {
        execSync(f.cmd(filePath), { cwd: projectRoot, timeout: 5000, stdio: "pipe", windowsHide: true });
      } catch {
        // 格式化失败不阻塞操作
      }
      break;
    }
  }
}

process.exit(0);
