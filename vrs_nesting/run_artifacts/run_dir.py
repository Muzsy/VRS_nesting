#!/usr/bin/env python3
"""Helpers for deterministic per-run artifact directory handling."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RunContext:
    run_id: str
    run_dir: Path
    run_log_path: Path


def _new_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid.uuid4().hex[:8]


def create_run_dir(run_root: str = "runs") -> RunContext:
    root = Path(run_root).resolve()
    root.mkdir(parents=True, exist_ok=True)

    for _ in range(100):
        run_id = _new_run_id()
        run_dir = root / run_id
        try:
            run_dir.mkdir(parents=False, exist_ok=False)
            run_log_path = run_dir / "run.log"
            run_log_path.touch()
            return RunContext(run_id=run_id, run_dir=run_dir, run_log_path=run_log_path)
        except FileExistsError:
            continue

    raise RuntimeError("Failed to allocate unique run directory")


def write_project_snapshot(run_dir: Path, payload: dict[str, Any]) -> Path:
    snapshot_path = run_dir / "project.json"
    snapshot_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return snapshot_path


def append_run_log(run_log_path: Path, event: str, detail: str = "") -> None:
    timestamp = datetime.now(timezone.utc).isoformat()
    line = f"{timestamp} {event}" if not detail else f"{timestamp} {event} {detail}"
    with run_log_path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
