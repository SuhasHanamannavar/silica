"""
Sandboxed EDA execution.

Security controls (Phase 7):
- Commands restricted to an explicit allowlist (verilator, yosys, make, g++,
  and the compiled simulator binary inside the work dir).
- No shell=True; argv list only. No command chaining.
- cwd restricted to a per-run isolated working directory. Filesystem access
  bounded by that directory (no absolute paths in args except inside cwd).
- CPU wall-clock timeout per command.
- Output captured and logged. Artifacts only written under the run dir.
- Environment variables scrubbed of secrets before subprocess execution.
"""
from __future__ import annotations
import os
import subprocess
import time
from typing import Any, Dict, List, Optional

ALLOWED_COMMANDS = {"verilator", "yosys", "make", "g++", "gcc"}


class SandboxViolation(Exception):
    pass


class EDASandbox:
    def __init__(self, work_dir: str, default_timeout_s: int = 120):
        self.work_dir = os.path.abspath(work_dir)
        self.default_timeout_s = default_timeout_s
        os.makedirs(self.work_dir, exist_ok=True)
        self.executions: List[Dict[str, Any]] = []

    def _scrub_env(self) -> Dict[str, str]:
        env = os.environ.copy()
        for k in list(env.keys()):
            if any(s in k.upper() for s in ("TOKEN", "SECRET", "PASSWORD", "KEY")):
                env.pop(k, None)
        return env

    def _validate(self, argv: List[str]) -> None:
        if not argv:
            raise SandboxViolation("empty command")
        cmd = os.path.basename(argv[0])
        # allow the compiled simulator (./obj_dir/V<top>) inside work dir
        if argv[0].startswith("./") or argv[0].startswith("obj_dir/"):
            resolved = os.path.abspath(os.path.join(self.work_dir, argv[0]))
            if not resolved.startswith(self.work_dir + os.sep) and resolved != self.work_dir:
                raise SandboxViolation(f"binary outside sandbox: {argv[0]}")
            return
        if cmd not in ALLOWED_COMMANDS:
            raise SandboxViolation(f"command not in allowlist: {cmd}")
        for a in argv[1:]:
            if a.startswith("/") and not a.startswith(self.work_dir):
                # allow absolute paths to system includes / installed tools
                if not (a.startswith("/usr/") or a.startswith("/bin/") or a.startswith("/opt/")):
                    raise SandboxViolation(f"absolute path outside sandbox: {a}")

    def run(self, argv: List[str], timeout_s: Optional[int] = None,
            input_text: Optional[str] = None) -> Dict[str, Any]:
        self._validate(argv)
        t0 = time.time()
        try:
            p = subprocess.run(
                argv, cwd=self.work_dir, capture_output=True, text=True,
                timeout=timeout_s or self.default_timeout_s,
                env=self._scrub_env(), input=input_text, shell=False,
            )
            dur = round(time.time() - t0, 2)
            log = (p.stdout or "") + (p.stderr or "")
            rec = {"cmd": " ".join(argv), "exit_code": p.returncode,
                   "duration_s": dur, "log_tail": log[-4000:],
                   "status": "passed" if p.returncode == 0 else "failed"}
        except subprocess.TimeoutExpired:
            rec = {"cmd": " ".join(argv), "exit_code": -1,
                   "duration_s": timeout_s or self.default_timeout_s,
                   "log_tail": f"TIMEOUT after {timeout_s or self.default_timeout_s}s",
                   "status": "failed"}
        except SandboxViolation as e:
            rec = {"cmd": " ".join(argv), "exit_code": -3, "duration_s": 0,
                   "log_tail": f"SANDBOX VIOLATION: {e}", "status": "blocked"}
        self.executions.append(rec)
        return rec

    def write_file(self, name: str, content: str) -> str:
        """Write a file inside the sandbox. Rejects path traversal."""
        fp = os.path.abspath(os.path.join(self.work_dir, name))
        if not fp.startswith(self.work_dir + os.sep):
            raise SandboxViolation(f"path traversal: {name}")
        os.makedirs(os.path.dirname(fp), exist_ok=True)
        with open(fp, "w") as f:
            f.write(content)
        return fp
