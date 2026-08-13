"""Job run status file: <job>/status.json (read by Pybox for notice progress)."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any


STATUS_NAME = "status.json"
PID_NAME = "run.pid"


def status_path(job: Path) -> Path:
    return job / STATUS_NAME


def pid_path(job: Path) -> Path:
    return job / PID_NAME


def write_status(job: Path, **fields: Any) -> Path:
    """Merge fields into status.json (atomic-ish replace)."""
    job = Path(job)
    job.mkdir(parents=True, exist_ok=True)
    path = status_path(job)
    data: dict[str, Any] = {}
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    data.update(fields)
    data["updated_at"] = time.time()
    if "pid" not in data:
        data["pid"] = os.getpid()
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)
    return path


def read_status(job: Path) -> dict[str, Any]:
    path = status_path(Path(job))
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"state": "error", "message": "status.json unreadable"}


def format_notice(data: dict[str, Any]) -> str:
    if not data:
        return "Embr Matte: no status.json yet"
    state = data.get("state", "?")
    phase = data.get("phase", "")
    msg = data.get("message", "")
    cur = data.get("current")
    total = data.get("total")
    parts = [f"Embr Matte: {state}"]
    if phase:
        parts.append(str(phase))
    if cur is not None and total:
        try:
            pct = int(100 * float(cur) / float(total)) if float(total) else 0
            parts.append(f"{int(cur)}/{int(total)} ({pct}%)")
        except Exception:
            parts.append(f"{cur}/{total}")
    elif cur is not None:
        parts.append(str(cur))
    if msg:
        parts.append(str(msg))
    return " · ".join(parts)


def write_pid(job: Path, pid: int | None = None) -> None:
    pid_path(Path(job)).write_text(str(pid if pid is not None else os.getpid()), encoding="utf-8")


def clear_pid(job: Path) -> None:
    p = pid_path(Path(job))
    if p.is_file():
        p.unlink()


def is_pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def running_pid(job: Path) -> int | None:
    p = pid_path(Path(job))
    if not p.is_file():
        data = read_status(job)
        pid = data.get("pid")
        if isinstance(pid, int) and data.get("state") == "running" and is_pid_alive(pid):
            return pid
        return None
    try:
        pid = int(p.read_text(encoding="utf-8").strip())
    except Exception:
        return None
    return pid if is_pid_alive(pid) else None
