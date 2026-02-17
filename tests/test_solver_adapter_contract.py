#!/usr/bin/env python3

from __future__ import annotations

import json
import stat
from pathlib import Path

import pytest

from vrs_nesting.runner.solver_adapter import SolverAdapterError, build_sparrow_solver_adapter, build_vrs_solver_adapter


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


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
part = payload["parts"][0]
out = {
    "contract_version": "v1",
    "status": "partial",
    "placements": [],
    "unplaced": [{"instance_id": f"{part['id']}__0001", "part_id": part["id"], "reason": "NO_CAPACITY"}],
}
output_path.write_text(json.dumps(out, ensure_ascii=False) + "\\n", encoding="utf-8")
""",
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


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
out_dir = Path.cwd() / "output"
out_dir.mkdir(parents=True, exist_ok=True)
(out_dir / f"final_{name}.json").write_text(
    json.dumps(
        {
            "solution": {
                "strip_width": 1000.0,
                "density": 0.4,
                "layout": {"placed_items": []},
            }
        }
    )
    + "\\n",
    encoding="utf-8",
)
""",
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


def test_vrs_solver_adapter_contract_with_fake_binary(tmp_path: Path):
    adapter = build_vrs_solver_adapter()
    fake_solver = tmp_path / "fake_vrs_solver.py"
    _write_fake_vrs_solver(fake_solver)

    run_dir = tmp_path / "run_vrs"
    run_dir.mkdir(parents=True, exist_ok=True)
    solver_input = tmp_path / "solver_input.json"
    _write_json(
        solver_input,
        {
            "contract_version": "v1",
            "project_name": "adapter_contract",
            "seed": 0,
            "time_limit_s": 30,
            "stocks": [{"id": "S1", "width": 100, "height": 100, "quantity": 1}],
            "parts": [{"id": "P1", "width": 10, "height": 10, "quantity": 1, "allowed_rotations_deg": [0]}],
        },
    )

    out_run_dir, meta = adapter.run_in_dir(
        input_path=str(solver_input),
        run_dir=run_dir,
        seed=0,
        time_limit_s=30,
        solver_bin=str(fake_solver),
    )

    assert out_run_dir.resolve() == run_dir.resolve()
    assert (run_dir / "solver_output.json").is_file()
    assert int(meta.get("return_code", -1)) == 0


def test_sparrow_solver_adapter_contract_with_fake_binary(tmp_path: Path):
    adapter = build_sparrow_solver_adapter()
    fake_sparrow = tmp_path / "fake_sparrow.py"
    _write_fake_sparrow(fake_sparrow)

    run_dir = tmp_path / "run_sparrow"
    run_dir.mkdir(parents=True, exist_ok=True)
    instance_input = tmp_path / "instance.json"
    _write_json(
        instance_input,
        {
            "name": "adapter_contract",
            "strip_height": 1000.0,
            "items": [],
        },
    )

    out_run_dir, meta = adapter.run_in_dir(
        input_path=str(instance_input),
        run_dir=run_dir,
        seed=0,
        time_limit_s=5,
        solver_bin=str(fake_sparrow),
    )

    assert out_run_dir.resolve() == run_dir.resolve()
    assert Path(str(meta.get("final_json_path", ""))).is_file()
    assert int(meta.get("return_code", -1)) == 0


def test_adapter_wraps_backend_errors(tmp_path: Path):
    adapter = build_vrs_solver_adapter()

    run_dir = tmp_path / "run_bad"
    run_dir.mkdir(parents=True, exist_ok=True)
    solver_input = tmp_path / "solver_input.json"
    _write_json(
        solver_input,
        {
            "contract_version": "v1",
            "project_name": "adapter_error",
            "seed": 0,
            "time_limit_s": 30,
            "stocks": [{"id": "S1", "width": 100, "height": 100, "quantity": 1}],
            "parts": [{"id": "P1", "width": 10, "height": 10, "quantity": 1, "allowed_rotations_deg": [0]}],
        },
    )

    with pytest.raises(SolverAdapterError):
        adapter.run_in_dir(
            input_path=str(solver_input),
            run_dir=run_dir,
            seed=0,
            time_limit_s=30,
            solver_bin=str(tmp_path / "missing_solver"),
        )
