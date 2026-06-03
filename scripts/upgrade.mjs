#!/usr/bin/env node

import { execFileSync } from "child_process";
import { cpSync, existsSync, mkdirSync, rmSync } from "fs";
import { dirname, join } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const projectRoot = join(__dirname, "..");
const tmpDir = join(projectRoot, ".claude", ".upgrade-tmp");
const backupDir = join(projectRoot, ".claude", ".upgrade-backups", new Date().toISOString().replace(/[:.]/g, "-"));
const upstream = "chenklein26-maker/Harness-Starter";
const apply = process.argv.includes("--apply");

const managedFiles = [
  ".claude/hooks/pre-tool-check.mjs",
  ".claude/hooks/session-context.mjs",
  ".claude/hooks/session-review.mjs",
  ".claude/hooks/post-tool-check.mjs",
  ".claude/hooks/pre-compact.mjs",
  ".claude/skills/harness-init/SKILL.md",
  ".claude/skills/harness-mode/SKILL.md",
  "scripts/init.mjs",
];

function run(command, args) {
  return execFileSync(command, args, {
    cwd: projectRoot,
    encoding: "utf-8",
    stdio: "pipe",
    timeout: 30000,
    windowsHide: true,
  }).trim();
}

console.log("\n=== Vision Studio Harness upgrade check ===\n");
console.log(`Upstream: https://github.com/${upstream}`);
console.log(`Mode: ${apply ? "apply with backup" : "check only"}\n`);

if (existsSync(tmpDir)) {
  rmSync(tmpDir, { recursive: true, force: true });
}
mkdirSync(dirname(tmpDir), { recursive: true });

run("git", ["clone", "--depth", "1", `https://github.com/${upstream}.git`, tmpDir]);

let available = 0;
let updated = 0;
for (const relativePath of managedFiles) {
  const source = join(tmpDir, relativePath);
  const target = join(projectRoot, relativePath);
  if (!existsSync(source)) {
    console.log(`SKIP    ${relativePath}`);
    continue;
  }

  available += 1;
  if (!apply) {
    console.log(`READY   ${relativePath}`);
    continue;
  }

  if (existsSync(target)) {
    const backup = join(backupDir, relativePath);
    mkdirSync(dirname(backup), { recursive: true });
    cpSync(target, backup, { recursive: true });
  }

  mkdirSync(dirname(target), { recursive: true });
  cpSync(source, target, { recursive: true });
  console.log(`UPDATED ${relativePath}`);
  updated += 1;
}

rmSync(tmpDir, { recursive: true, force: true });

if (!apply) {
  console.log(`\nFound ${available} upstream Harness-managed files.`);
  console.log("No project files were changed.");
  console.log("To apply upstream files with backups, run: npm run harness:upgrade -- --apply\n");
} else {
  console.log(`\nUpdated ${updated} files.`);
  console.log(`Backups are under: ${backupDir}`);
  console.log("Review the diff, then rerun: npm run harness:check\n");
}
