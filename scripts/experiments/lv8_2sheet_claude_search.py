#!/usr/bin/env python3
"""LV8 2-sheet 10mm 600s quality search harness.

Runs one quality profile against an LV8 engine_input fixture, capturing:
  - prepacked solver input
  - cavity_plan
  - engine solver stdout/stderr
  - canonical run summary (placed_types/instances, sheets_used, valid, util, runtime, spacing, margin)

Writes one JSONL row to <out_dir>/runs.jsonl on success or failure.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from vrs_nesting.config.nesting_quality_profiles import (
    build_nesting_engine_cli_args_for_quality_profile,
)
from worker.cavity_prepack import build_cavity_prepacked_engine_input_v2


def _utc_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _resolve_bin() -> str:
    bin_path = REPO_ROOT / "rust" / "nesting_engine" / "target" / "release" / "nesting_engine"
    if not bin_path.is_file():
        raise FileNotFoundError(f"binary not built: {bin_path}")
    return str(bin_path)


def _synth_snapshot_row(base_engine_input: dict[str, Any]) -> dict[str, Any]:
    parts_manifest = []
    for idx, p in enumerate(base_engine_input.get("parts", [])):
        pid = str(p.get("id") or "").strip()
        if not pid:
            continue
        parts_manifest.append(
            {
                "project_part_requirement_id": f"req-{idx:06d}",
                "part_revision_id": pid,
                "part_definition_id": f"part-def-{pid}",
                "part_code": pid,
                "required_qty": int(p.get("quantity", 1)),
                "placement_priority": idx + 1,
                "selected_nesting_derivative_id": f"drv-{pid}",
                "source_geometry_revision_id": f"geo-{pid}",
            }
        )
    return {
        "parts_manifest_jsonb": parts_manifest,
        "geometry_manifest_jsonb": [],
        "project_manifest_jsonb": {"project_id": "lv8-claude-search", "project_name": "lv8_2sheet_10mm_600s"},
        "sheets_manifest_jsonb": [],
    }


def _instance_count_from_placements(
    placements: list[dict[str, Any]],
    virtual_parts: dict[str, dict[str, Any]],
) -> tuple[int, dict[str, int]]:
    """Reconcile solver placements (top-level virtual parents) to original instances.

    Each placement.part_id is a virtual_id when prepack was active. virtual_parts maps
    virtual_id -> {parent_id, parent_instance, children: [...]}.
    For each placed virtual_id, count 1 parent + len(children) original instances.
    """
    total = 0
    per_real: dict[str, int] = {}
    for placement in placements:
        vid = str(placement.get("part_id"))
        vinfo = virtual_parts.get(vid)
        if isinstance(vinfo, dict):
            parent_id = str(vinfo.get("parent_id") or vinfo.get("parent_part_id") or vid)
            per_real[parent_id] = per_real.get(parent_id, 0) + 1
            total += 1
            children = vinfo.get("children")
            if isinstance(children, list):
                for child in children:
                    cid = str(child.get("part_id") or child.get("child_part_id") or "")
                    if cid:
                        per_real[cid] = per_real.get(cid, 0) + 1
                        total += 1
        else:
            # No virtual mapping — treat as a real instance with its raw id.
            per_real[vid] = per_real.get(vid, 0) + 1
            total += 1
    return total, per_real


def run_one(
    fixture_path: Path,
    out_dir: Path,
    quality_profile: str,
    time_limit_sec: int,
    seed: int,
    label: str,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    bin_path = _resolve_bin()

    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    fixture["seed"] = seed
    fixture["time_limit_sec"] = time_limit_sec

    spacing_mm = float(fixture["sheet"].get("spacing_mm") or 0.0)
    margin_mm = float(fixture["sheet"].get("margin_mm") or 0.0)
    required_types = len(fixture.get("parts", []))
    required_instances = sum(int(p.get("quantity", 0)) for p in fixture.get("parts", []))

    snapshot_row = _synth_snapshot_row(fixture)

    t_prepack = time.perf_counter()
    prepacked_input, cavity_plan = build_cavity_prepacked_engine_input_v2(
        snapshot_row=snapshot_row,
        base_engine_input=fixture,
        enabled=True,
    )
    prepack_elapsed = round(time.perf_counter() - t_prepack, 6)

    (out_dir / "cavity_plan.json").write_text(
        json.dumps(cavity_plan, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "prepacked_solver_input.json").write_text(
        json.dumps(prepacked_input, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    virtual_parts = cavity_plan.get("virtual_parts") or {}
    quantity_delta = cavity_plan.get("quantity_delta") or {}
    virtual_parent_count = len(virtual_parts) if isinstance(virtual_parts, dict) else 0

    cli_args = build_nesting_engine_cli_args_for_quality_profile(quality_profile)

    # Ensure prepacked input has explicit time_limit_sec/seed and ALSO 10mm spacing/margin
    # (passed through from fixture). The prepacked input inherits the sheet block.
    prepacked_input["seed"] = seed
    prepacked_input["time_limit_sec"] = time_limit_sec
    prepacked_solver_input_path = out_dir / "prepacked_solver_input.json"
    prepacked_solver_input_path.write_text(
        json.dumps(prepacked_input, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    stdout_path = out_dir / "solver_stdout.json"
    stderr_path = out_dir / "solver_stderr.log"

    cmd = [bin_path, "nest", *cli_args]
    env = os.environ.copy()
    env.setdefault("NESTING_ENGINE_STOP_MODE", "wall_clock")
    # CGAL kernel env hint when profile asks for it
    if "cgal_reference" in quality_profile:
        env["NESTING_ENGINE_NFP_KERNEL"] = "cgal_reference"

    quiet = os.environ.get("LV8_HARNESS_QUIET", "1") == "1"
    t_solver_start = time.perf_counter()
    timed_out = False
    return_code = None
    try:
        with prepacked_solver_input_path.open("rb") as fin, stdout_path.open("wb") as fout:
            if quiet:
                # Stderr is dominated by [CONCAVE NFP DIAG] spam which blocks the engine
                # (megabytes per NFP query). Drop it; keep a marker file noting the policy.
                stderr_path.write_text(
                    "[harness] stderr discarded to avoid CONCAVE NFP DIAG bottleneck\n",
                    encoding="utf-8",
                )
                with open(os.devnull, "wb") as devnull:
                    proc = subprocess.run(
                        cmd, stdin=fin, stdout=fout, stderr=devnull,
                        env=env, timeout=time_limit_sec + 60, check=False,
                    )
            else:
                with stderr_path.open("wb") as ferr:
                    proc = subprocess.run(
                        cmd, stdin=fin, stdout=fout, stderr=ferr,
                        env=env, timeout=time_limit_sec + 60, check=False,
                    )
            return_code = proc.returncode
    except subprocess.TimeoutExpired:
        timed_out = True
    solver_elapsed = round(time.perf_counter() - t_solver_start, 6)

    solver_output: dict[str, Any] = {}
    try:
        solver_output = json.loads(stdout_path.read_text(encoding="utf-8"))
    except Exception:
        pass

    placements = solver_output.get("placements") or []
    unplaced = solver_output.get("unplaced") or []
    sheets_used = int(solver_output.get("sheets_used") or 0)
    util_pct = None
    obj = solver_output.get("objective") or {}
    if isinstance(obj, dict):
        util_pct = obj.get("utilization_pct")

    placed_virtual_count = len(placements)
    placed_instances, per_real_placed = _instance_count_from_placements(
        placements, virtual_parts if isinstance(virtual_parts, dict) else {}
    )
    placed_types = len({p.get("part_id") for p in placements}) if placements else 0
    # If virtual_parts mapping is empty (no prepack happened), placed_instances == placed_virtual_count.

    # Valid? Conservative check: solver completed, no timeout, no unplaced, sheets_used <= 2.
    valid = (
        not timed_out
        and return_code == 0
        and sheets_used > 0
        and sheets_used <= 2
        and len(unplaced) == 0
        and placed_instances == required_instances
    )

    summary = {
        "label": label,
        "quality_profile": quality_profile,
        "engine_cli_args": cli_args,
        "fixture_path": str(fixture_path.relative_to(REPO_ROOT)),
        "seed": seed,
        "time_limit_sec": time_limit_sec,
        "spacing_mm": spacing_mm,
        "margin_mm": margin_mm,
        "sheet_width_mm": float(fixture["sheet"]["width_mm"]),
        "sheet_height_mm": float(fixture["sheet"]["height_mm"]),
        "required_types": required_types,
        "required_instances": required_instances,
        "virtual_parent_count": virtual_parent_count,
        "placed_virtual_count": placed_virtual_count,
        "placed_types": placed_types,
        "placed_instances": placed_instances,
        "unplaced_virtual_count": len(unplaced),
        "sheets_used": sheets_used,
        "utilization_pct": util_pct,
        "prepack_elapsed_sec": prepack_elapsed,
        "solver_elapsed_sec": solver_elapsed,
        "runtime_sec": round(prepack_elapsed + solver_elapsed, 6),
        "return_code": return_code,
        "timed_out": timed_out,
        "valid": valid,
        "stdout_path": str(stdout_path.relative_to(REPO_ROOT)),
        "stderr_path": str(stderr_path.relative_to(REPO_ROOT)),
        "cavity_plan_path": str((out_dir / "cavity_plan.json").relative_to(REPO_ROOT)),
        "prepacked_input_path": str(prepacked_solver_input_path.relative_to(REPO_ROOT)),
        "out_dir": str(out_dir.relative_to(REPO_ROOT)),
        "wall_clock_utc": datetime.now(timezone.utc).isoformat(),
    }

    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--quality-profile", required=True)
    parser.add_argument("--time-limit-sec", type=int, default=600)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--label", default="run")
    parser.add_argument("--runs-jsonl", default=None)
    parser.add_argument("--runs-csv", default=None)
    args = parser.parse_args(argv)

    fixture = Path(args.fixture).resolve()
    out_dir = Path(args.out_dir).resolve()
    summary = run_one(
        fixture_path=fixture,
        out_dir=out_dir,
        quality_profile=args.quality_profile,
        time_limit_sec=args.time_limit_sec,
        seed=args.seed,
        label=args.label,
    )

    if args.runs_jsonl:
        Path(args.runs_jsonl).parent.mkdir(parents=True, exist_ok=True)
        with open(args.runs_jsonl, "a", encoding="utf-8") as f:
            f.write(json.dumps(summary, ensure_ascii=False) + "\n")
    if args.runs_csv:
        header = "label,quality_profile,seed,timeout,timed_out,return_code,sheets_used,placed_virtual,placed_instances,required_instances,util_pct,runtime_sec,valid\n"
        path = Path(args.runs_csv)
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text(header, encoding="utf-8")
        with path.open("a", encoding="utf-8") as f:
            f.write(
                f"{summary['label']},{summary['quality_profile']},{summary['seed']},"
                f"{summary['time_limit_sec']},{summary['timed_out']},{summary['return_code']},"
                f"{summary['sheets_used']},{summary['placed_virtual_count']},{summary['placed_instances']},"
                f"{summary['required_instances']},{summary['utilization_pct']},{summary['runtime_sec']},"
                f"{summary['valid']}\n"
            )

    print(json.dumps(summary, indent=2))
    return 0 if summary["return_code"] == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
