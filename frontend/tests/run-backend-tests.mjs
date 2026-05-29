import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(__dirname, "..");
const projectRoot = path.resolve(frontendRoot, "..");
const backendRoot = path.join(projectRoot, "backend");
const depsPath = path.join(backendRoot, ".deps");
const separator = process.platform === "win32" ? ";" : ":";
const existingPythonPath = process.env.PYTHONPATH || "";

const env = {
  ...process.env,
  PYTHONPATH: [backendRoot, depsPath, existingPythonPath].filter(Boolean).join(separator),
};

const result = spawnSync(
  "python",
  ["-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-v"],
  {
    cwd: backendRoot,
    env,
    encoding: "utf-8",
    shell: process.platform === "win32",
  },
);

if (result.stdout) process.stdout.write(result.stdout);
if (result.stderr) process.stderr.write(result.stderr);

if (result.error) {
  console.error(`Backend regression tests could not start: ${result.error.message}`);
  process.exit(1);
}

if (result.status !== 0) {
  console.error(`Backend regression tests failed with exit code ${result.status}.`);
  process.exit(result.status || 1);
}
