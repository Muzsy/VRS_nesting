#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _make_executable(path: Path) -> None:
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


def _write_fake_vrs_solver(path: Path) -> None:
    path.write_text(
        """#!/usr/bin/env python3
import json
import sys
from pathlib import Path

args = sys.argv[1:]
if "--input" not in args or "--output" not in args:
    raise SystemExit(2)
input_path = Path(args[args.index("--input") + 1])
output_path = Path(args[args.index("--output") + 1])

payload = json.loads(input_path.read_text(encoding="utf-8"))
parts = payload.get("parts", [])
unplaced = []
for part in parts:
    part_id = str(part.get("id", "")).strip()
    qty = int(part.get("quantity", 0))
    for idx in range(1, max(0, qty) + 1):
        unplaced.append(
            {
                "instance_id": f"{part_id}__{idx:04d}",
                "part_id": part_id,
                "reason": "NO_CAPACITY",
            }
        )

out = {
    "contract_version": "v1",
    "status": "partial" if unplaced else "ok",
    "placements": [],
    "unplaced": unplaced,
    "metrics": {
        "placed_count": 0,
        "unplaced_count": len(unplaced),
        "sheet_count_used": 0,
    },
}
output_path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\\n", encoding="utf-8")
""",
        encoding="utf-8",
    )
    _make_executable(path)


def _write_fake_sparrow(path: Path) -> None:
    path.write_text(
        """#!/usr/bin/env python3
import json
import sys
from pathlib import Path

args = sys.argv[1:]
if "-i" not in args:
    raise SystemExit(2)
input_path = Path(args[args.index("-i") + 1])
payload = json.loads(input_path.read_text(encoding="utf-8"))
name = str(payload.get("name", input_path.stem)).strip() or input_path.stem
items = payload.get("items", [])

placed_items = []
for idx, item in enumerate(items):
    if not isinstance(item, dict):
        continue
    item_id = int(item.get("id", idx))
    orientations = item.get("allowed_orientations", [0.0])
    rotation = float(orientations[0]) if isinstance(orientations, list) and orientations else 0.0
    placed_items.append(
        {
            "item_id": item_id,
            "transformation": {
                "translation": [0.0, 0.0],
                "rotation": rotation,
            },
        }
    )

final_payload = {
    "solution": {
        "strip_width": 1000.0,
        "density": 0.5,
        "layout": {"placed_items": placed_items},
    }
}

out_dir = Path.cwd() / "output"
out_dir.mkdir(parents=True, exist_ok=True)
final_json = out_dir / f"final_{name}.json"
final_json.write_text(json.dumps(final_payload, indent=2, ensure_ascii=False) + "\\n", encoding="utf-8")
""",
        encoding="utf-8",
    )
    _make_executable(path)


def _non_empty_stdout_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def _assert_run_dir_stdout_contract(proc: subprocess.CompletedProcess[str]) -> Path:
    if proc.returncode != 0:
        raise AssertionError(f"CLI failed rc={proc.returncode}, stderr={proc.stderr}")
    lines = _non_empty_stdout_lines(proc.stdout)
    if len(lines) != 1:
        raise AssertionError(f"stdout contract violation: expected 1 non-empty line, got {lines!r}")
    run_dir = Path(lines[0]).resolve()
    if not run_dir.is_dir():
        raise AssertionError(f"stdout run_dir is not directory: {run_dir}")
    return run_dir


def test_cli_run_contract_end_to_end_with_fake_solver(tmp_path: Path):
    fake_solver = tmp_path / "fake_vrs_solver.py"
    _write_fake_vrs_solver(fake_solver)

    run_root = tmp_path / "runs"
    project_path = tmp_path / "project_v1.json"
    _write_json(
        project_path,
        {
            "version": "v1",
            "name": "e2e_cli_run",
            "seed": 0,
            "time_limit_s": 30,
            "stocks": [{"id": "S1", "width": 200, "height": 100, "quantity": 1}],
            "parts": [{"id": "P1", "width": 10, "height": 10, "quantity": 2, "allowed_rotations_deg": [0, 90]}],
        },
    )

    env = os.environ.copy()
    env["VRS_SOLVER_BIN"] = str(fake_solver)
    proc = subprocess.run(
        [sys.executable, "-m", "vrs_nesting.cli", "run", str(project_path), "--run-root", str(run_root)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    run_dir = _assert_run_dir_stdout_contract(proc)

    required = [
        run_dir / "project.json",
        run_dir / "run.log",
        run_dir / "solver_input.json",
        run_dir / "solver_output.json",
        run_dir / "runner_meta.json",
        run_dir / "report.json",
    ]
    for path in required:
        if not path.is_file():
            raise AssertionError(f"missing artifact: {path}")

    report = json.loads((run_dir / "report.json").read_text(encoding="utf-8"))
    for key in ("contract_version", "project_name", "seed", "time_limit_s", "run_dir", "status", "paths", "metrics", "export_summary"):
        if key not in report:
            raise AssertionError(f"missing report key: {key}")
    if report.get("contract_version") != "v1":
        raise AssertionError(f"unexpected contract version: {report.get('contract_version')!r}")


def test_cli_dxf_run_contract_end_to_end_with_fake_sparrow(tmp_path: Path):
    fake_sparrow = tmp_path / "fake_sparrow.py"
    _write_fake_sparrow(fake_sparrow)

    stock_fixture = ROOT / "samples" / "dxf_demo" / "stock_rect_1000x2000.dxf"
    part_fixture = ROOT / "samples" / "dxf_demo" / "part_arc_spline_chaining_ok.dxf"
    if not stock_fixture.is_file() or not part_fixture.is_file():
        raise AssertionError("required DXF fixtures are missing")

    run_root = tmp_path / "runs"
    project_path = tmp_path / "project_dxf_v1.json"
    _write_json(
        project_path,
        {
            "version": "dxf_v1",
            "name": "e2e_cli_dxf_run",
            "seed": 0,
            "time_limit_s": 10,
            "units": "mm",
            "spacing_mm": 0.0,
            "margin_mm": 0.0,
            "stocks_dxf": [{"id": "stock_1", "path": str(stock_fixture), "quantity": 1, "allowed_rotations_deg": [0]}],
            "parts_dxf": [{"id": "part_1", "path": str(part_fixture), "quantity": 1, "allowed_rotations_deg": [0]}],
        },
    )

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "vrs_nesting.cli",
            "dxf-run",
            str(project_path),
            "--run-root",
            str(run_root),
            "--sparrow-bin",
            str(fake_sparrow),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    run_dir = _assert_run_dir_stdout_contract(proc)

    required = [
        run_dir / "project.json",
        run_dir / "run.log",
        run_dir / "report.json",
        run_dir / "sparrow_instance.json",
        run_dir / "solver_input.json",
        run_dir / "sparrow_input_meta.json",
        run_dir / "sparrow_output.json",
        run_dir / "solver_output.json",
        run_dir / "source_geometry_map.json",
        run_dir / "sparrow_stdout.log",
        run_dir / "sparrow_stderr.log",
        run_dir / "out" / "sheet_001.dxf",
    ]
    for path in required:
        if not path.is_file():
            raise AssertionError(f"missing artifact: {path}")

    report = json.loads((run_dir / "report.json").read_text(encoding="utf-8"))
    for key in ("contract_version", "project_name", "seed", "time_limit_s", "run_dir", "status", "paths", "metrics", "export_summary"):
        if key not in report:
            raise AssertionError(f"missing report key: {key}")
    if report.get("contract_version") != "dxf_v1":
        raise AssertionError(f"unexpected contract version: {report.get('contract_version')!r}")
