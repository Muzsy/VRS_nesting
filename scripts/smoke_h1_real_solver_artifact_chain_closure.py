#!/usr/bin/env python3
"""Strict real-solver H1 artifact-chain smoke (no fixture solver injection)."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _resolve_real_solver_bin() -> Path:
    explicit = os.environ.get("VRS_SOLVER_BIN", "").strip()
    if explicit:
        path = Path(explicit).expanduser().resolve()
        if path.is_file():
            return path
        raise RuntimeError(f"VRS_SOLVER_BIN is set but missing: {path}")

    default_path = ROOT / "rust" / "vrs_solver" / "target" / "release" / "vrs_solver"
    if default_path.is_file():
        return default_path.resolve()

    proc = subprocess.run(
        ["cargo", "build", "--release", "--manifest-path", str(ROOT / "rust" / "vrs_solver" / "Cargo.toml")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"failed to build real vrs_solver: {proc.stderr[-1200:]}")
    if not default_path.is_file():
        raise RuntimeError(f"real vrs_solver binary missing after build: {default_path}")
    return default_path.resolve()


def _probe_real_solver_places(*, solver_bin: Path) -> None:
    probe_input = """
{
  "contract_version": "v1",
  "project_name": "real_solver_probe",
  "seed": 0,
  "time_limit_s": 60,
  "stocks": [
    {
      "id": "SHEET_A",
      "quantity": 1,
      "outer_points": [[0, 0], [500, 0], [500, 300], [0, 300]],
      "holes_points": []
    }
  ],
  "parts": [
    {"id": "PART_A", "width": 120, "height": 80, "quantity": 1, "allowed_rotations_deg": [0]}
  ]
}
""".strip()
    with tempfile.TemporaryDirectory(prefix="h1_real_solver_probe_") as tmp:
        in_path = Path(tmp) / "solver_input.json"
        out_path = Path(tmp) / "solver_output.json"
        in_path.write_text(probe_input + "\n", encoding="utf-8")
        proc = subprocess.run(
            [
                str(solver_bin),
                "--input",
                str(in_path),
                "--output",
                str(out_path),
                "--seed",
                "0",
                "--time-limit",
                "60",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                "real solver probe failed before closure smoke. "
                f"exit={proc.returncode} stderr_tail={proc.stderr[-600:]}"
            )
        raw = out_path.read_text(encoding="utf-8")
        if '"placements": []' in raw:
            raise RuntimeError("real solver probe produced zero placements; cannot prove real artifact chain")


def main() -> int:
    solver_bin = _resolve_real_solver_bin()
    _probe_real_solver_places(solver_bin=solver_bin)

    env = dict(os.environ)
    env["VRS_SOLVER_BIN"] = str(solver_bin)

    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "smoke_h1_real_infra_closure.py"),
        "--mode",
        "artifact-chain",
        "--project-name",
        "H1 Real Solver Artifact Chain",
    ]
    proc = subprocess.run(cmd, cwd=ROOT, env=env, check=False)
    return int(proc.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
