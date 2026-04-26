// Cross-platform launcher for the FastAPI backend.
// Resolves the right uvicorn binary (venv first, system PATH fallback)
// and runs it from the backend/ directory.
import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import path from "node:path";

const here = path.dirname(new URL(import.meta.url).pathname.replace(/^\/(\w:)/, "$1"));
const backendDir = path.resolve(here, "..", "..", "backend");
const isWin = process.platform === "win32";

const venvUvicorn = isWin
  ? path.join(backendDir, ".venv", "Scripts", "uvicorn.exe")
  : path.join(backendDir, ".venv", "bin", "uvicorn");

const cmd = existsSync(venvUvicorn) ? venvUvicorn : "uvicorn";
const args = ["app.main:app", "--host", "127.0.0.1", "--port", "8000", "--reload"];

if (cmd === "uvicorn" && !isWin) {
  console.error(
    "[api] backend/.venv not found. Either run `pip install -e .` in backend/, " +
      "or make sure `uvicorn` is on your system PATH."
  );
}

const proc = spawn(cmd, args, {
  cwd: backendDir,
  stdio: "inherit",
  env: { ...process.env, PYTHONUNBUFFERED: "1" },
  shell: false,
});

proc.on("error", (err) => {
  console.error(`[api] failed to start: ${err.message}`);
  process.exit(1);
});
proc.on("exit", (code, signal) => {
  if (signal) process.kill(process.pid, signal);
  else process.exit(code ?? 0);
});
process.on("SIGINT", () => proc.kill("SIGINT"));
process.on("SIGTERM", () => proc.kill("SIGTERM"));
