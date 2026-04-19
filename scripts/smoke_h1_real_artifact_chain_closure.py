#!/usr/bin/env python3
"""Strict H1 artifact-chain smoke using real infra + deterministic placeable solver fixture."""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _write_fixture_solver(path: Path) -> None:
    script = """#!/usr/bin/env python3
import json
import sys

def parse_args(argv):
    out = {}
    idx = 0
    while idx < len(argv):
        key = argv[idx]
        if not key.startswith("--") or idx + 1 >= len(argv):
            raise SystemExit(f"invalid args at {key!r}")
        out[key] = argv[idx + 1]
        idx += 2
    return out

args = parse_args(sys.argv[1:])
input_path = args.get("--input")
output_path = args.get("--output")
if not input_path or not output_path:
    raise SystemExit("--input and --output are required")

payload = json.loads(open(input_path, "r", encoding="utf-8").read())
parts = payload.get("parts", [])
placements = []
unplaced = []
placed_any = False

for part in parts:
    if not isinstance(part, dict):
        continue
    part_id = str(part.get("id", "")).strip()
    qty = int(part.get("quantity", 0) or 0)
    if not part_id or qty <= 0:
        continue
    for index in range(1, qty + 1):
        instance_id = f"{part_id}__{index:04d}"
        if not placed_any:
            placements.append(
                {
                    "instance_id": instance_id,
                    "part_id": part_id,
                    "sheet_index": 0,
                    "x": 10.0,
                    "y": 10.0,
                    "rotation_deg": 0,
                }
            )
            placed_any = True
        else:
            unplaced.append(
                {
                    "instance_id": instance_id,
                    "part_id": part_id,
                    "reason": "NO_CAPACITY",
                }
            )

status = "ok" if not unplaced else "partial"
out = {
    "contract_version": "v1",
    "status": status,
    "placements": placements,
    "unplaced": unplaced,
    "metrics": {
        "placed_count": len(placements),
        "unplaced_count": len(unplaced),
        "sheet_count_used": 1 if placements else 0,
        "seed": int(payload.get("seed", 0) or 0),
        "time_limit_s": int(payload.get("time_limit_s", 60) or 60),
        "project_name": str(payload.get("project_name", "fixture")),
    },
}
with open(output_path, "w", encoding="utf-8") as handle:
    handle.write(json.dumps(out, ensure_ascii=False, indent=2) + "\\n")
"""
    path.write_text(script, encoding="utf-8")
    mode = path.stat().st_mode
    path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="h1_artifact_chain_solver_") as tmp:
        solver_path = Path(tmp) / "fixture_solver.py"
        _write_fixture_solver(solver_path)

        env = dict(os.environ)
        env["VRS_SOLVER_BIN"] = str(solver_path)

        cmd = [
            sys.executable,
            str(ROOT / "scripts" / "smoke_h1_real_infra_closure.py"),
            "--mode",
            "artifact-chain",
            "--part-required-qty",
            "2",
            "--part-width-mm",
            "0.12",
            "--part-height-mm",
            "0.08",
            "--sheet-width-mm",
            "500",
            "--sheet-height-mm",
            "300",
            "--project-name",
            "H1 Real Artifact Chain",
        ]
        proc = subprocess.run(cmd, cwd=ROOT, env=env, check=False)
        return int(proc.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
