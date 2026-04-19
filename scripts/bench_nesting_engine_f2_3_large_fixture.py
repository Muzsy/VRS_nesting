#!/usr/bin/env python3
"""Benchmark nesting_engine on large F2-3 fixtures (BLF vs NFP)."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import statistics
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STAT_PREFIX = "NEST_NFP_STATS_V1 "
BENCH_VERSION = "nesting_engine_f2_3_large_fixture_benchmark_v1"
DEFAULT_BIN = ROOT / "rust/nesting_engine/target/release/nesting_engine"
DEFAULT_OUT = ROOT / "runs/benchmarks/nesting_engine_f2_3_large_fixture_benchmark.json"
TIME_LIMIT_RUNTIME_TOLERANCE_SEC = 0.05
DEFAULT_WORK_UNITS_PER_SEC = 50_000
DEFAULT_HARD_TIMEOUT_GRACE_SEC = 60


@dataclass(frozen=True)
class BenchRun:
    run_index: int
    runtime_sec: float
    determinism_hash: str
    sheets_used: int
    placed_count: int
    utilization_pct: float | None
    timeout_bound: bool
    nfp_stats: dict[str, Any] | None

    def as_json(self) -> dict[str, Any]:
        return {
            "run_index": self.run_index,
            "runtime_sec": round(self.runtime_sec, 6),
            "determinism_hash": self.determinism_hash,
            "sheets_used": self.sheets_used,
            "placed_count": self.placed_count,
            "utilization_pct": self.utilization_pct,
            "timeout_bound": self.timeout_bound,
            "nfp_stats": self.nfp_stats,
        }


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _parse_stats(stderr_text: str, require_stats: bool) -> dict[str, Any] | None:
    matches = [line for line in stderr_text.splitlines() if line.startswith(STAT_PREFIX)]
    if require_stats:
        if len(matches) != 1:
            raise AssertionError(f"expected exactly 1 '{STAT_PREFIX.strip()}' line, got {len(matches)}")
        payload = matches[0][len(STAT_PREFIX) :].strip()
        parsed = json.loads(payload)
        if not isinstance(parsed, dict):
            raise AssertionError("NFP stats payload must be a JSON object")
        return parsed
    if matches:
        raise AssertionError(f"unexpected NFP stats line in BLF mode: count={len(matches)}")
    return None


def _as_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise AssertionError(f"{name} must be integer, got {value!r}")
    return value


def _as_float_optional(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _read_time_limit_sec(input_path: Path) -> int:
    payload = _read_json(input_path)
    raw = payload.get("time_limit_sec")
    if isinstance(raw, bool) or not isinstance(raw, int):
        raise AssertionError("input.time_limit_sec must be integer")
    if raw <= 0:
        raise AssertionError("input.time_limit_sec must be > 0")
    return raw


def _is_timeout_bound_run(out: dict[str, Any], runtime_sec: float, time_limit_sec: int) -> bool:
    unplaced = out.get("unplaced")
    timed_out_reason = False
    if isinstance(unplaced, list):
        for item in unplaced:
            if not isinstance(item, dict):
                continue
            if str(item.get("reason", "")).strip() == "TIME_LIMIT_EXCEEDED":
                timed_out_reason = True
                break

    runtime_near_limit = runtime_sec >= max(0.0, float(time_limit_sec) - TIME_LIMIT_RUNTIME_TOLERANCE_SEC)
    return timed_out_reason or runtime_near_limit


def _run_once(
    bin_path: Path,
    input_path: Path,
    placer: str,
    run_index: int,
    time_limit_sec: int,
    stop_mode_env: dict[str, str] | None,
) -> BenchRun:
    cmd = [str(bin_path), "nest"]
    require_stats = placer == "nfp"
    if placer == "nfp":
        cmd.extend(["--placer", "nfp"])

    env = dict(os.environ)
    if require_stats:
        env["NESTING_ENGINE_EMIT_NFP_STATS"] = "1"
    else:
        env.pop("NESTING_ENGINE_EMIT_NFP_STATS", None)
    if stop_mode_env:
        env.update(stop_mode_env)

    started = time.perf_counter()
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        input=input_path.read_bytes(),
        capture_output=True,
        check=False,
        env=env,
    )
    elapsed = time.perf_counter() - started

    if proc.returncode != 0:
        err = proc.stderr.decode("utf-8", errors="replace")
        raise AssertionError(
            f"nesting_engine failed (rc={proc.returncode}) for placer={placer}, run={run_index}\n"
            f"cmd={' '.join(cmd)}\n{err}"
        )

    out = json.loads(proc.stdout.decode("utf-8", errors="strict"))
    if not isinstance(out, dict):
        raise AssertionError("nest output must be a JSON object")

    meta = out.get("meta")
    if not isinstance(meta, dict):
        raise AssertionError("output.meta must be object")
    determinism_hash = str(meta.get("determinism_hash", "")).strip()
    if not determinism_hash:
        raise AssertionError("missing output.meta.determinism_hash")

    sheets_used = _as_int(out.get("sheets_used"), "output.sheets_used")
    placements = out.get("placements")
    if not isinstance(placements, list):
        raise AssertionError("output.placements must be list")
    placed_count = len(placements)

    objective = out.get("objective")
    utilization: float | None = None
    if isinstance(objective, dict):
        utilization = _as_float_optional(objective.get("utilization_pct"))
    timeout_bound = _is_timeout_bound_run(out, elapsed, time_limit_sec)

    stderr_text = proc.stderr.decode("utf-8", errors="replace")
    nfp_stats = _parse_stats(stderr_text, require_stats=require_stats)

    return BenchRun(
        run_index=run_index,
        runtime_sec=elapsed,
        determinism_hash=determinism_hash,
        sheets_used=sheets_used,
        placed_count=placed_count,
        utilization_pct=utilization,
        timeout_bound=timeout_bound,
        nfp_stats=nfp_stats,
    )


def _summary(runs: list[BenchRun]) -> dict[str, Any]:
    if not runs:
        raise AssertionError("cannot summarize empty run list")

    hashes = [r.determinism_hash for r in runs]
    unique_hashes = sorted(set(hashes))
    determinism_stable = len(unique_hashes) == 1

    runtime_values = [r.runtime_sec for r in runs]
    sheets_values = [r.sheets_used for r in runs]
    placed_values = [r.placed_count for r in runs]
    timeout_bound_present = any(r.timeout_bound for r in runs)
    util_values = [r.utilization_pct for r in runs if r.utilization_pct is not None]
    if determinism_stable:
        determinism_class = "stable"
    elif timeout_bound_present:
        determinism_class = "timeout_bound_drift"
    else:
        determinism_class = "unstable"

    return {
        "runs": len(runs),
        "determinism_stable": determinism_stable,
        "determinism_class": determinism_class,
        "determinism_hash": unique_hashes[0] if determinism_stable else None,
        "determinism_hashes": unique_hashes,
        "timeout_bound_present": timeout_bound_present,
        "runtime_sec_median": round(float(statistics.median(runtime_values)), 6),
        "runtime_sec_min": round(float(min(runtime_values)), 6),
        "runtime_sec_max": round(float(max(runtime_values)), 6),
        "sheets_used_median": int(statistics.median(sheets_values)),
        "placed_count_median": int(statistics.median(placed_values)),
        "utilization_pct_median": (
            round(float(statistics.median(util_values)), 6) if util_values else None
        ),
    }


def _load_out(path: Path, env_info: dict[str, Any]) -> dict[str, Any]:
    if path.is_file():
        payload = _read_json(path)
        version = str(payload.get("version", "")).strip()
        if version != BENCH_VERSION:
            raise AssertionError(
                f"unsupported benchmark output version '{version}', expected '{BENCH_VERSION}'"
            )
        entries = payload.get("entries")
        if not isinstance(entries, list):
            raise AssertionError("benchmark output entries must be a list")
        payload["generated_at_utc"] = datetime.now(timezone.utc).isoformat()
        payload["environment"] = env_info
        return payload

    return {
        "version": BENCH_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "environment": env_info,
        "entries": [],
    }


def _merge_entry(payload: dict[str, Any], entry: dict[str, Any]) -> None:
    entries = payload["entries"]
    assert isinstance(entries, list)

    key_input = entry["input"]
    key_placer = entry["placer"]
    key_stop_mode = entry.get("meta", {}).get("stop_mode_env")
    for idx, existing in enumerate(entries):
        if not isinstance(existing, dict):
            continue
        existing_stop_mode = existing.get("meta", {}).get("stop_mode_env")
        if (
            existing.get("input") == key_input
            and existing.get("placer") == key_placer
            and existing_stop_mode == key_stop_mode
        ):
            entries[idx] = entry
            return
    entries.append(entry)


def _build_stop_mode_env(args: argparse.Namespace) -> dict[str, str] | None:
    stop_mode = args.stop_mode
    work_units_per_sec = args.work_units_per_sec
    hard_timeout_grace_sec = args.hard_timeout_grace_sec

    if stop_mode is None:
        if work_units_per_sec is not None or hard_timeout_grace_sec is not None:
            raise AssertionError(
                "--work-units-per-sec/--hard-timeout-grace-sec only allowed when --stop-mode is set"
            )
        return None

    if work_units_per_sec is not None and work_units_per_sec <= 0:
        raise AssertionError("--work-units-per-sec must be > 0")
    if hard_timeout_grace_sec is not None and hard_timeout_grace_sec < 0:
        raise AssertionError("--hard-timeout-grace-sec must be >= 0")

    env = {"NESTING_ENGINE_STOP_MODE": stop_mode}
    if stop_mode == "work_budget":
        env["NESTING_ENGINE_WORK_UNITS_PER_SEC"] = str(
            work_units_per_sec if work_units_per_sec is not None else DEFAULT_WORK_UNITS_PER_SEC
        )
        env["NESTING_ENGINE_HARD_TIMEOUT_GRACE_SEC"] = str(
            hard_timeout_grace_sec
            if hard_timeout_grace_sec is not None
            else DEFAULT_HARD_TIMEOUT_GRACE_SEC
        )
    return env


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bin", default=str(DEFAULT_BIN), help="Path to nesting_engine binary")
    parser.add_argument("--input", required=True, help="Input fixture JSON path")
    parser.add_argument("--runs", type=int, default=5, help="Number of repeated runs per placer")
    parser.add_argument(
        "--placer",
        choices=["blf", "nfp", "both"],
        default="both",
        help="Which placer(s) to benchmark",
    )
    parser.add_argument(
        "--out",
        default=str(DEFAULT_OUT),
        help="Output benchmark JSON path (merged/updated if exists)",
    )
    parser.add_argument(
        "--stop-mode",
        choices=["wall_clock", "work_budget"],
        default=None,
        help="Optional stop mode override passed via env to nesting_engine",
    )
    parser.add_argument(
        "--work-units-per-sec",
        type=int,
        default=None,
        help="Optional work budget units/sec (used with --stop-mode work_budget)",
    )
    parser.add_argument(
        "--hard-timeout-grace-sec",
        type=int,
        default=None,
        help="Optional hard wall-clock grace in sec (used with --stop-mode work_budget)",
    )
    args = parser.parse_args(argv)

    if args.runs <= 0:
        raise AssertionError("--runs must be > 0")

    bin_path = Path(args.bin)
    if not bin_path.is_absolute():
        bin_path = (ROOT / bin_path).resolve()
    if not (bin_path.is_file() and os.access(bin_path, os.X_OK)):
        raise AssertionError(f"invalid nesting_engine binary: {bin_path}")

    input_path = Path(args.input)
    if not input_path.is_absolute():
        input_path = (ROOT / input_path).resolve()
    if not input_path.is_file():
        raise AssertionError(f"input fixture missing: {input_path}")

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = ROOT / out_path

    stop_mode_env = _build_stop_mode_env(args)
    env_info = {
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "nesting_engine_bin": _rel(bin_path),
        "nesting_engine_bin_sha256": _sha256_file(bin_path),
        "host_machine": platform.machine(),
        "stop_mode_env": stop_mode_env,
    }
    payload = _load_out(out_path, env_info)

    placers = ["blf", "nfp"] if args.placer == "both" else [args.placer]
    input_rel = _rel(input_path)
    time_limit_sec = _read_time_limit_sec(input_path)

    for placer in placers:
        print(f"[RUN] input={input_rel} placer={placer} runs={args.runs} stop_mode_env={stop_mode_env}")
        run_results: list[BenchRun] = []
        for run_index in range(1, args.runs + 1):
            res = _run_once(
                bin_path,
                input_path,
                placer,
                run_index,
                time_limit_sec,
                stop_mode_env,
            )
            run_results.append(res)
            print(
                f"  - run#{run_index}: runtime={res.runtime_sec:.6f}s "
                f"hash={res.determinism_hash[:18]}... sheets={res.sheets_used} "
                f"placed={res.placed_count} timeout_bound={res.timeout_bound}"
            )

        summary = _summary(run_results)
        if not summary["determinism_stable"]:
            hashes = ", ".join(str(h) for h in summary["determinism_hashes"])
            if summary["timeout_bound_present"]:
                print(
                    "[WARN] "
                    f"placer={placer} timeout-bound drift: determinism hash mismatch across runs: {hashes}"
                )
            else:
                print(
                    "[WARN] "
                    f"placer={placer} determinism hash mismatch across runs (non-timeout): {hashes}"
                )
        print(
            "[OK] "
            f"placer={placer} median_runtime={summary['runtime_sec_median']:.6f}s "
            f"hash_stable={summary['determinism_stable']} "
            f"timeout_bound_present={summary['timeout_bound_present']} "
            f"class={summary['determinism_class']}"
        )

        entry = {
            "input": input_rel,
            "placer": placer,
            "meta": {
                "stop_mode_env": stop_mode_env,
            },
            "runs": [r.as_json() for r in run_results],
            "summary": summary,
        }
        _merge_entry(payload, entry)

    _write_json(out_path, payload)
    print(f"[OK] benchmark report written: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
