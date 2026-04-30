#!/usr/bin/env python3
"""Smoke for cavity T8: legacy vs prepack benchmark evidence."""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from worker.cavity_prepack import build_cavity_prepacked_engine_input  # noqa: E402


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _rect(x0: float, y0: float, x1: float, y1: float) -> list[list[float]]:
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]


def _build_synthetic_input() -> dict[str, Any]:
    return {
        "version": "nesting_engine_v2",
        "seed": 7,
        "time_limit_sec": 12,
        "sheet": {
            "width_mm": 140.0,
            "height_mm": 120.0,
            "kerf_mm": 0.0,
            "spacing_mm": 0.0,
            "margin_mm": 0.0,
        },
        "parts": [
            {
                "id": "parent-a",
                "quantity": 1,
                "allowed_rotations_deg": [0, 90, 180, 270],
                "outer_points_mm": _rect(0.0, 0.0, 90.0, 90.0),
                "holes_points_mm": [_rect(15.0, 15.0, 75.0, 75.0)],
            },
            {
                "id": "child-a",
                "quantity": 8,
                "allowed_rotations_deg": [0, 90, 180, 270],
                "outer_points_mm": _rect(0.0, 0.0, 12.0, 12.0),
                "holes_points_mm": [],
            },
            {
                "id": "child-b",
                "quantity": 4,
                "allowed_rotations_deg": [0, 90, 180, 270],
                "outer_points_mm": _rect(0.0, 0.0, 18.0, 10.0),
                "holes_points_mm": [],
            },
        ],
    }


def _parse_json_line(prefix: str, stderr_text: str) -> dict[str, Any] | None:
    for line in stderr_text.splitlines():
        line = line.strip()
        if not line.startswith(prefix):
            continue
        payload = line[len(prefix) :].strip()
        try:
            loaded = json.loads(payload)
        except json.JSONDecodeError:
            return None
        if isinstance(loaded, dict):
            return loaded
        return None
    return None


def _count_reasons(unplaced_rows: list[dict[str, Any]]) -> dict[str, int]:
    out: dict[str, int] = {}
    for row in unplaced_rows:
        reason = str(row.get("reason") or "unknown").strip() or "unknown"
        out[reason] = int(out.get(reason, 0)) + 1
    return dict(sorted(out.items()))


def _build_minimal_snapshot_row(engine_input: dict[str, Any]) -> dict[str, Any]:
    parts_raw = engine_input.get("parts")
    if not isinstance(parts_raw, list):
        raise RuntimeError("invalid source input: parts must be list")
    manifest: list[dict[str, Any]] = []
    for idx, raw in enumerate(parts_raw):
        if not isinstance(raw, dict):
            raise RuntimeError(f"invalid source input: parts[{idx}] must be object")
        part_id = str(raw.get("id") or "").strip()
        qty = int(raw.get("quantity") or 0)
        _assert(bool(part_id), f"invalid source input: parts[{idx}].id missing")
        _assert(qty > 0, f"invalid source input: parts[{idx}].quantity must be >0")
        manifest.append(
            {
                "part_revision_id": part_id,
                "part_code": f"BENCH_{idx + 1:03d}",
                "source_geometry_revision_id": f"geo-{part_id}",
                "selected_nesting_derivative_id": f"drv-{part_id}",
                "required_qty": qty,
            }
        )
    return {"parts_manifest_jsonb": manifest}


def _run_engine_case(
    *,
    input_payload: dict[str, Any],
    part_in_part_mode: str,
    run_name: str,
) -> dict[str, Any]:
    run_dir = Path(tempfile.mkdtemp(prefix=f"smoke_cavity_t8_{run_name}_"))
    input_path = run_dir / "solver_input.json"
    stdout_path = run_dir / "stdout.json"
    stderr_path = run_dir / "stderr.log"
    input_path.write_text(json.dumps(input_payload, ensure_ascii=False), encoding="utf-8")

    cmd = [
        "cargo",
        "run",
        "--quiet",
        "--manifest-path",
        str(ROOT / "rust/nesting_engine/Cargo.toml"),
        "--bin",
        "nesting_engine",
        "--",
        "nest",
        "--placer",
        "nfp",
        "--search",
        "sa",
        "--part-in-part",
        part_in_part_mode,
        "--compaction",
        "slide",
        "--sa-iters",
        "192",
        "--sa-eval-budget-sec",
        "6",
    ]
    env = dict(os.environ)
    env["NESTING_ENGINE_EMIT_NFP_STATS"] = "1"

    started = time.monotonic()
    proc = subprocess.run(
        cmd,
        input=input_path.read_text(encoding="utf-8"),
        text=True,
        capture_output=True,
        env=env,
        cwd=ROOT,
        check=False,
    )
    elapsed_sec = round(time.monotonic() - started, 3)
    stdout_path.write_text(proc.stdout, encoding="utf-8")
    stderr_path.write_text(proc.stderr, encoding="utf-8")

    if proc.returncode != 0:
        raise RuntimeError(f"{run_name}: nesting engine failed with exit={proc.returncode}")
    try:
        solver_out = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{run_name}: invalid engine stdout JSON") from exc
    if not isinstance(solver_out, dict):
        raise RuntimeError(f"{run_name}: engine stdout is not object")

    placements_raw = solver_out.get("placements")
    unplaced_raw = solver_out.get("unplaced")
    placements = placements_raw if isinstance(placements_raw, list) else []
    unplaced = unplaced_raw if isinstance(unplaced_raw, list) else []
    nfp_stats = _parse_json_line("NEST_NFP_STATS_V1", proc.stderr)
    sa_profile = _parse_json_line("SA_PROFILE_V1", proc.stderr)
    blf_profile = _parse_json_line("BLF_PROFILE_V1", proc.stderr)
    fallback = "warning: --placer nfp fallback to blf" in proc.stderr
    effective = ""
    if isinstance(nfp_stats, dict):
        effective = str(nfp_stats.get("effective_placer") or "").strip().lower()

    return {
        "run_name": run_name,
        "exit_code": int(proc.returncode),
        "elapsed_sec_wall": elapsed_sec,
        "status": str(solver_out.get("status") or ""),
        "placed_count": len(placements),
        "unplaced_count": len(unplaced),
        "unplaced_reasons": _count_reasons([row for row in unplaced if isinstance(row, dict)]),
        "fallback_warning": fallback,
        "effective_placer": effective,
        "nfp_stats": nfp_stats,
        "sa_profile": sa_profile,
        "blf_profile": blf_profile,
        "run_dir": str(run_dir),
    }


def main() -> int:
    source_input = _build_synthetic_input()
    source_parts = source_input.get("parts")
    if not isinstance(source_parts, list):
        raise RuntimeError("source solver input missing parts[]")

    tuned_input = copy.deepcopy(source_input)

    snapshot_row = _build_minimal_snapshot_row(tuned_input)
    prepacked_input, cavity_plan = build_cavity_prepacked_engine_input(
        snapshot_row=snapshot_row,
        base_engine_input=tuned_input,
        enabled=True,
    )
    _assert(cavity_plan.get("version") == "cavity_plan_v1", "unexpected cavity plan version")
    _assert(cavity_plan.get("enabled") is True, "cavity plan should be enabled")
    virtual_parts = cavity_plan.get("virtual_parts")
    _assert(isinstance(virtual_parts, dict) and len(virtual_parts) >= 1, "expected at least one virtual parent")

    legacy_result = _run_engine_case(
        input_payload=tuned_input,
        part_in_part_mode="auto",
        run_name="legacy",
    )
    prepack_result = _run_engine_case(
        input_payload=prepacked_input,
        part_in_part_mode="off",
        run_name="prepack",
    )

    legacy_effective = legacy_result.get("effective_placer")
    prepack_effective = prepack_result.get("effective_placer")
    _assert(legacy_result["fallback_warning"] is True, "legacy run should emit NFP->BLF fallback warning")
    _assert(legacy_effective == "blf", f"legacy effective placer mismatch: {legacy_effective}")
    _assert(prepack_result["fallback_warning"] is False, "prepack run must not emit NFP->BLF fallback warning")
    _assert(prepack_effective == "nfp", f"prepack effective placer mismatch: {prepack_effective}")

    t0_report_path = ROOT / "codex/reports/nesting_engine/cavity_t0_artifact_recovery_and_baseline_replay.md"
    t0_text = t0_report_path.read_text(encoding="utf-8")
    production_blocked = ("Production run URL recovery valos API endpointen ujraellenorizve | FAIL" in t0_text) and (
        "Production 1:1 replay uj letoltott snapshot alapjan | FAIL" in t0_text
    )

    evidence = {
        "version": "cavity_t8_smoke_v1",
        "source_input_path": "synthetic_cavity_t8_fixture_v1",
        "tuned_time_limit_sec": tuned_input.get("time_limit_sec"),
        "production_replay_blocked_per_t0_report": bool(production_blocked),
        "legacy": legacy_result,
        "prepack": prepack_result,
        "cavity_plan_summary": {
            "virtual_parent_count": len(virtual_parts),
            "instance_bases_count": len(cavity_plan.get("instance_bases", {}))
            if isinstance(cavity_plan.get("instance_bases"), dict)
            else 0,
            "quantity_delta_count": len(cavity_plan.get("quantity_delta", {}))
            if isinstance(cavity_plan.get("quantity_delta"), dict)
            else 0,
        },
    }

    out_path = ROOT / "tmp/cavity_t8_smoke_evidence.json"
    out_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print("[smoke_cavity_t8_production_regression_benchmark] PASS")
    print(f"evidence={out_path}")
    print(f"legacy_effective={legacy_effective} legacy_unplaced={legacy_result['unplaced_count']}")
    print(f"prepack_effective={prepack_effective} prepack_unplaced={prepack_result['unplaced_count']}")
    print(f"production_replay_blocked_per_t0_report={production_blocked}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
