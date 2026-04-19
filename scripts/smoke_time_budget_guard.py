#!/usr/bin/env python3
"""Timeout/performance guard smoke for vrs_solver_runner."""

from __future__ import annotations

import argparse
import json
import os
import stat
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER_CMD = [sys.executable, "-m", "vrs_nesting.runner.vrs_solver_runner"]
INPUT_PATH = ROOT / "samples" / "time_budget" / "timeout_guard_input.json"


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _latest_run_dir(run_root: Path) -> Path:
    runs = [p for p in run_root.iterdir() if p.is_dir()]
    if not runs:
        raise AssertionError(f"no run directories under {run_root}")
    return sorted(runs)[-1]


def _make_fake_slow_solver(tmp_dir: Path) -> Path:
    fake = tmp_dir / "fake_slow_solver.py"
    fake.write_text(
        "#!/usr/bin/env python3\n"
        "import json\n"
        "import sys\n"
        "import time\n"
        "from pathlib import Path\n"
        "args = sys.argv[1:]\n"
        "out_path = None\n"
        "if '--output' in args:\n"
        "  out_path = Path(args[args.index('--output') + 1])\n"
        "time.sleep(2.6)\n"
        "if out_path is not None:\n"
        "  out = {\n"
        "    'contract_version': 'v1',\n"
        "    'status': 'partial',\n"
        "    'placements': [],\n"
        "    'unplaced': [{'instance_id': 'fake__0001', 'part_id': 'fake', 'reason': 'TIME_LIMIT_REACHED'}]\n"
        "  }\n"
        "  out_path.write_text(json.dumps(out), encoding='utf-8')\n"
    , encoding="utf-8")
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    return fake


def _run_timeout_guard(fake_solver: Path, run_root: Path) -> None:
    cmd = RUNNER_CMD + [
        "--input",
        str(INPUT_PATH),
        "--solver-bin",
        str(fake_solver),
        "--seed",
        "0",
        "--time-limit",
        "1",
        "--run-root",
        str(run_root),
    ]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)

    if proc.returncode != 2:
        raise AssertionError(f"expected runner failure exit=2 on timeout, got {proc.returncode}")
    if "timed out" not in proc.stderr.lower():
        raise AssertionError(f"timeout message missing from stderr: {proc.stderr!r}")

    run_dir = _latest_run_dir(run_root)
    meta = _read_json(run_dir / "runner_meta.json")
    if int(meta.get("time_limit_s", -1)) != 1:
        raise AssertionError(f"expected runner_meta.time_limit_s=1, got {meta.get('time_limit_s')}")
    if int(meta.get("return_code", -1)) != 124:
        raise AssertionError(f"expected runner_meta.return_code=124 on timeout, got {meta.get('return_code')}")
    duration = float(meta.get("duration_sec", -1.0))
    if duration <= 0 or duration > 4.0:
        raise AssertionError(f"unexpected timeout duration_sec={duration}")


def _run_perf_guard(real_solver: Path, run_root: Path, *, perf_threshold_s: float) -> dict[str, object]:
    cmd = RUNNER_CMD + [
        "--input",
        str(INPUT_PATH),
        "--solver-bin",
        str(real_solver),
        "--seed",
        "0",
        "--time-limit",
        "60",
        "--run-root",
        str(run_root),
    ]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise AssertionError(f"real solver smoke failed: rc={proc.returncode}, stderr={proc.stderr}")

    run_dir = Path(proc.stdout.strip().splitlines()[-1])
    meta = _read_json(run_dir / "runner_meta.json")
    duration = float(meta.get("duration_sec", -1.0))
    if duration <= 0 or duration > perf_threshold_s:
        raise AssertionError(f"perf guard breached on tiny fixture: duration_sec={duration}")
    output_sha = str(meta.get("output_sha256", "")).strip()
    if not output_sha:
        raise AssertionError("missing output_sha256 in runner_meta")
    return {
        "status": "pass",
        "threshold_s": float(perf_threshold_s),
        "duration_sec": duration,
        "output_sha256": output_sha,
        "run_dir": str(run_dir.resolve()),
    }


def _write_baseline_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Timeout/perf guard smoke")
    parser.add_argument(
        "--require-real-solver",
        action="store_true",
        help="Fail if rust/vrs_solver binary is missing",
    )
    parser.add_argument(
        "--perf-threshold-s",
        type=float,
        default=5.0,
        help="Maximum allowed duration (seconds) for the tiny real-solver perf fixture.",
    )
    parser.add_argument(
        "--baseline-json",
        default=None,
        help="Optional path to write nightly baseline JSON payload.",
    )
    args = parser.parse_args(argv)

    if not INPUT_PATH.is_file():
        raise AssertionError(f"missing input fixture: {INPUT_PATH}")

    real_solver = ROOT / "rust" / "vrs_solver" / "target" / "release" / "vrs_solver"
    perf_result: dict[str, object] = {"status": "skipped"}

    with tempfile.TemporaryDirectory(prefix="vrs_timeout_guard_") as tmp:
        tmp_dir = Path(tmp)
        timeout_run_root = tmp_dir / "timeout_runs"
        timeout_run_root.mkdir(parents=True, exist_ok=True)
        fake_solver = _make_fake_slow_solver(tmp_dir)
        _run_timeout_guard(fake_solver, timeout_run_root)

        if real_solver.is_file() and os.access(real_solver, os.X_OK):
            perf_run_root = tmp_dir / "perf_runs"
            perf_run_root.mkdir(parents=True, exist_ok=True)
            perf_result = _run_perf_guard(real_solver, perf_run_root, perf_threshold_s=float(args.perf_threshold_s))
        elif args.require_real_solver:
            raise AssertionError(f"real solver binary missing: {real_solver}")

    if args.baseline_json:
        baseline_payload: dict[str, object] = {
            "contract_version": "v1",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "fixture": str(INPUT_PATH),
            "timeout_guard": {
                "status": "pass",
                "expected_runner_return_code": 124,
            },
            "perf_guard": perf_result,
        }
        _write_baseline_json(Path(args.baseline_json), baseline_payload)

    print("[OK] timeout/perf guard smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
