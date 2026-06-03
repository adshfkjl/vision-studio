import { existsSync, readFileSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";
import { execFileSync } from "child_process";

const __dirname = dirname(fileURLToPath(import.meta.url));
const projectRoot = join(__dirname, "..");

const checks = [];

function fileExists(path) {
  return existsSync(join(projectRoot, path));
}

function readJson(path) {
  try {
    return JSON.parse(readFileSync(join(projectRoot, path), "utf-8"));
  } catch {
    return null;
  }
}

function commandAvailable(command, args = ["--version"]) {
  try {
    execFileSync(command, args, { cwd: projectRoot, stdio: "pipe", timeout: 3000 });
    return true;
  } catch {
    return false;
  }
}

function add(name, ok, hint = "", level = "required") {
  checks.push({ name, ok, hint, level });
}

add("CLAUDE.md", fileExists("CLAUDE.md"), "Claude Code entry file is missing.");
add("AGENTS.md", fileExists("AGENTS.md"), "Codex entry file is missing.");
add("README.md", fileExists("README.md"), "Project usage documentation is missing.");
add(".claude/ directory", fileExists(".claude"), "Harness Starter directory is missing.");
add(".claude/settings.json", fileExists(".claude/settings.json"), "Claude hooks are not registered.");
add(".claude/.harness-state", fileExists(".claude/.harness-state"), "Harness mode and phase state is missing.");
add(".lsp.json", fileExists(".lsp.json"), "Language server configuration is missing.");
add("root package.json", fileExists("package.json"), "Root npm scripts are missing.");
add("script file: check.mjs", fileExists("scripts/check.mjs"), "Harness check script is missing.");
add("script file: upgrade.mjs", fileExists("scripts/upgrade.mjs"), "Harness upgrade script is missing.");
add("script file: init.mjs", fileExists("scripts/init.mjs"), "Harness init script is missing.");

const requiredHooks = [
  "pre-tool-check.mjs",
  "session-context.mjs",
  "session-review.mjs",
  "pre-compact.mjs",
];
for (const hook of requiredHooks) {
  add(`hook: ${hook}`, fileExists(`.claude/hooks/${hook}`), `${hook} is missing.`);
}
add(
  "optional hook: post-tool-check.mjs",
  fileExists(".claude/hooks/post-tool-check.mjs"),
  "PostToolUse formatter hook is optional and currently unavailable.",
  "optional",
);

add(
  "harness-init skill",
  fileExists(".claude/skills/harness-init/SKILL.md"),
  "Local Harness init skill is missing.",
);
add(
  "harness-mode skill",
  fileExists(".claude/skills/harness-mode/SKILL.md"),
  "Local Harness mode skill is missing.",
);

const rootPackage = readJson("package.json");
if (rootPackage) {
  const scripts = rootPackage.scripts || {};
  add("script: harness:check", !!scripts["harness:check"], "Add npm script harness:check.");
  add("script: harness:upgrade", !!scripts["harness:upgrade"], "Add npm script harness:upgrade.");
  add("script: test", !!scripts.test, "Add root npm test wrapper.");
  add("script: test:e2e", !!scripts["test:e2e"], "Add root npm test:e2e wrapper.");
  add("script: build", !!scripts.build, "Add root npm build wrapper.");
  add(
    "Harness Starter upstream",
    rootPackage.harnessStarter?.repository === "chenklein26-maker/Harness-Starter",
    "package.json should record chenklein26-maker/Harness-Starter as the upstream template.",
  );
}

add("frontend package.json", fileExists("frontend/package.json"), "Frontend package is missing.");
add("backend requirements.txt", fileExists("backend/requirements.txt"), "Backend dependency file is missing.");
add("controller branch rules", fileExists("branch-rules/controller.md"), "Controller branch rule is missing.");
add("annotation branch rules", fileExists("branch-rules/annotation-center.md"), "Annotation branch rule is missing.");
add("project-center branch rules", fileExists("branch-rules/project-center.md"), "Project-center branch rule is missing.");
add("model-workbench branch rules", fileExists("branch-rules/model-workbench.md"), "Model-workbench branch rule is missing.");

const claude = fileExists("CLAUDE.md") ? readFileSync(join(projectRoot, "CLAUDE.md"), "utf-8") : "";
add("CLAUDE.md initialized", claude.length > 0 && !claude.includes("【待填写"), "CLAUDE.md still contains template placeholders.");
add("CLAUDE.md points to branch rules", claude.includes("branch-rules"), "CLAUDE.md should point agents to branch-rules/.");
add("CLAUDE.md contains Surgical Changes", claude.includes("Surgical Changes"), "Add the Surgical Changes behavior rule.");
add("CLAUDE.md contains Goal-Driven Execution", claude.includes("Goal-Driven Execution"), "Add the Goal-Driven Execution behavior rule.");

const settings = readJson(".claude/settings.json");
if (settings) {
  const hooks = settings.hooks || {};
  for (const hookName of ["PreToolUse", "SessionStart", "Stop", "PreCompact"]) {
    add(`settings hook: ${hookName}`, Array.isArray(hooks[hookName]) && hooks[hookName].length > 0, `${hookName} is not registered.`);
  }
  add(
    "PostToolUse not required",
    !hooks.PostToolUse || Array.isArray(hooks.PostToolUse),
    "PostToolUse may be omitted or configured as an array.",
    "optional",
  );
}

const lsp = readJson(".lsp.json");
if (lsp) {
  add("LSP: JavaScript/React mapping", !!lsp.typescript?.extensionToLanguage?.[".jsx"], ".lsp.json should map .jsx files.");
  add("LSP: Python mapping", !!lsp.python?.extensionToLanguage?.[".py"], ".lsp.json should map .py files.");
}

add(
  "TypeScript language server available",
  commandAvailable("typescript-language-server"),
  "Optional: install with npm install -g typescript-language-server.",
  "optional",
);
add(
  "Python language server available",
  commandAvailable("pyright-langserver") || commandAvailable("pyright"),
  "Optional: install with pip install pyright.",
  "optional",
);

const requiredFailures = checks.filter((check) => check.level === "required" && !check.ok);
const warningFailures = checks.filter((check) => check.level !== "required" && !check.ok);
const okCount = checks.filter((check) => check.ok).length;

console.log(`\nVision Studio Harness health check: ${okCount}/${checks.length} passed\n`);
for (const check of checks) {
  const marker = check.ok ? "PASS" : check.level === "required" ? "FAIL" : "WARN";
  const suffix = !check.ok && check.hint ? ` - ${check.hint}` : "";
  console.log(`  [${marker}] ${check.name}${suffix}`);
}
console.log("");

if (requiredFailures.length > 0) {
  console.error(`Required Harness checks failed: ${requiredFailures.length}`);
  process.exit(1);
}

if (warningFailures.length > 0) {
  console.log(`Optional Harness warnings: ${warningFailures.length}`);
}
