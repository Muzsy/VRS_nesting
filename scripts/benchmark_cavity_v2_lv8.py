#!/usr/bin/env python3
"""Cavity v2 LV8 benchmark runner."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from vrs_nesting.config.nesting_quality_profiles import build_nesting_engine_cli_args_for_quality_profile
from worker.cavity_prepack import build_cavity_prepacked_engine_input_v2, validate_prepack_solver_input_hole_free
from worker.cavity_validation import ValidationIssue, validate_cavity_plan_v2


def _count_top_level_holes(engine_input: dict[str, Any]) -> int:
    total = 0
    for part in engine_input.get("parts", []):
        if not isinstance(part, dict):
            continue
        holes = part.get("holes_points_mm")
        if isinstance(holes, list):
            total += len(holes)
    return int(total)


def _count_diagnostics_by_code(diagnostics: list[Any]) -> dict[str, int]:
    out: dict[str, int] = {}
    for item in diagnostics:
        if not isinstance(item, dict):
            continue
        code = str(item.get("code") or "").strip()
        if not code:
            continue
        out[code] = int(out.get(code, 0)) + 1
    return dict(sorted(out.items(), key=lambda kv: kv[0]))


def _count_tree_depth_metrics(placement_trees: dict[str, Any]) -> tuple[int, int]:
    internal_count = 0
    nested_count = 0

    def walk(node: Any, depth: int) -> None:
        nonlocal internal_count, nested_count
        if not isinstance(node, dict):
            return
        if depth >= 1:
            internal_count += 1
        if depth >= 2:
            nested_count += 1
        children = node.get("children", [])
        if not isinstance(children, list):
            return
        for child in children:
            walk(child, depth + 1)

    for root in placement_trees.values():
        if not isinstance(root, dict):
            continue
        children = root.get("children", [])
        if not isinstance(children, list):
            continue
        for child in children:
            walk(child, 1)
    return (int(internal_count), int(nested_count))


def _safe_int(raw: Any, default: int = 0) -> int:
    try:
        if isinstance(raw, bool):
            return default
        return int(raw)
    except (TypeError, ValueError):
        return default


def _synthesize_snapshot_row_from_engine_input(base_engine_input: dict[str, Any]) -> dict[str, Any]:
    parts_manifest: list[dict[str, Any]] = []
    parts = base_engine_input.get("parts", [])
    if isinstance(parts, list):
        for idx, raw_part in enumerate(parts):
            if not isinstance(raw_part, dict):
                continue
            part_id = str(raw_part.get("id") or "").strip()
            if not part_id:
                continue
            parts_manifest.append(
                {
                    "project_part_requirement_id": f"req-{idx:06d}",
                    "part_revision_id": part_id,
                    "part_definition_id": f"part-def-{part_id}",
                    "part_code": part_id,
                    "required_qty": _safe_int(raw_part.get("quantity"), 1),
                    "placement_priority": idx + 1,
                    "selected_nesting_derivative_id": f"drv-{part_id}",
                    "source_geometry_revision_id": f"geo-{part_id}",
                }
            )
    return {
        "parts_manifest_jsonb": parts_manifest,
        "geometry_manifest_jsonb": [],
        "project_manifest_jsonb": {"project_id": "benchmark", "project_name": "cavity_v2_lv8"},
        "sheets_manifest_jsonb": [],
    }


def _extract_fixture_payload(payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    snapshot_row_raw = payload.get("snapshot_row")
    if isinstance(snapshot_row_raw, dict):
        snapshot_row = snapshot_row_raw
    else:
        snapshot_row = payload

    base_engine_input_raw = payload.get("base_engine_input")
    if isinstance(base_engine_input_raw, dict):
        base_engine_input = base_engine_input_raw
    else:
        engine_input_raw = payload.get("engine_input")
        if isinstance(engine_input_raw, dict):
            base_engine_input = engine_input_raw
        else:
            base_engine_input = payload

    if "parts_manifest_jsonb" not in snapshot_row or not isinstance(snapshot_row.get("parts_manifest_jsonb"), list):
        snapshot_row = _synthesize_snapshot_row_from_engine_input(base_engine_input)

    return snapshot_row, base_engine_input


def _build_virtual_solver_placements(cavity_plan: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    virtual_parts = cavity_plan.get("virtual_parts", {})
    if not isinstance(virtual_parts, dict):
        return out
    for idx, (virtual_part_id, virtual_part_item) in enumerate(sorted(virtual_parts.items(), key=lambda kv: str(kv[0]))):
        if not isinstance(virtual_part_item, dict):
            continue
        out.append(
            {
                "part_id": str(virtual_part_id),
                "instance": idx,
                "sheet": 0,
                "x_mm": 0.0,
                "y_mm": 0.0,
                "rotation_deg": 0.0,
            }
        )
    return out


def _choose_auto_fixture() -> Path | None:
    candidates: list[Path] = []
    for pattern in (
        "tmp/*lv8*.json",
        "tmp/*LV8*.json",
        "poc/**/*lv8*.json",
        "poc/**/*LV8*.json",
        "tests/**/*lv8*.json",
        "tests/**/*LV8*.json",
    ):
        candidates.extend(REPO_ROOT.glob(pattern))

    for path in sorted(candidates):
        if not path.is_file():
            continue
        return path
    return None


def _build_synthetic_fixture_payload() -> dict[str, Any]:
    def rect(x0: float, y0: float, x1: float, y1: float) -> list[list[float]]:
        return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]

    return {
        "snapshot_row": {
            "project_manifest_jsonb": {"project_id": "synthetic", "project_name": "synthetic-cavity-v2-benchmark"},
            "parts_manifest_jsonb": [
                {
                    "part_revision_id": "parent-a",
                    "part_code": "PARENT_A",
                    "required_qty": 1,
                    "source_geometry_revision_id": "geo-parent-a",
                    "selected_nesting_derivative_id": "drv-parent-a",
                },
                {
                    "part_revision_id": "child-a",
                    "part_code": "CHILD_A",
                    "required_qty": 2,
                    "source_geometry_revision_id": "geo-child-a",
                    "selected_nesting_derivative_id": "drv-child-a",
                },
            ],
            "geometry_manifest_jsonb": [
                {
                    "selected_nesting_derivative_id": "drv-parent-a",
                    "polygon": {"outer_ring": rect(0.0, 0.0, 40.0, 40.0), "hole_rings": [rect(4.0, 4.0, 30.0, 30.0)]},
                    "bbox": {"min_x": 0.0, "min_y": 0.0, "max_x": 40.0, "max_y": 40.0, "width": 40.0, "height": 40.0},
                },
                {
                    "selected_nesting_derivative_id": "drv-child-a",
                    "polygon": {"outer_ring": rect(0.0, 0.0, 6.0, 6.0), "hole_rings": []},
                    "bbox": {"min_x": 0.0, "min_y": 0.0, "max_x": 6.0, "max_y": 6.0, "width": 6.0, "height": 6.0},
                },
            ],
            "sheets_manifest_jsonb": [],
        },
        "base_engine_input": {
            "version": "nesting_engine_v2",
            "seed": 0,
            "time_limit_sec": 10,
            "sheet": {"width_mm": 1500.0, "height_mm": 3000.0, "kerf_mm": 0.0, "spacing_mm": 0.0, "margin_mm": 0.0},
            "parts": [
                {
                    "id": "parent-a",
                    "quantity": 1,
                    "allowed_rotations_deg": [0, 90, 180, 270],
                    "outer_points_mm": rect(0.0, 0.0, 40.0, 40.0),
                    "holes_points_mm": [rect(4.0, 4.0, 30.0, 30.0)],
                },
                {
                    "id": "child-a",
                    "quantity": 2,
                    "allowed_rotations_deg": [0, 90, 180, 270],
                    "outer_points_mm": rect(0.0, 0.0, 6.0, 6.0),
                    "holes_points_mm": [],
                },
            ],
        },
    }


def run_benchmark(*, fixture_path: Path, output_dir: Path) -> tuple[dict[str, Any], Path]:
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"fixture payload must be dict: {fixture_path}")

    snapshot_row, base_engine_input = _extract_fixture_payload(payload)
    if not isinstance(base_engine_input, dict):
        raise RuntimeError("base_engine_input is invalid")

    holes_before = _count_top_level_holes(base_engine_input)
    t0 = time.perf_counter()
    prepacked_input, cavity_plan = build_cavity_prepacked_engine_input_v2(
        snapshot_row=snapshot_row,
        base_engine_input=base_engine_input,
        enabled=True,
    )
    prepack_elapsed_sec = round(time.perf_counter() - t0, 6)

    holes_after = _count_top_level_holes(prepacked_input)

    guard_passed = True
    guard_error: str | None = None
    try:
        validate_prepack_solver_input_hole_free(prepacked_input)
    except Exception as exc:  # noqa: BLE001
        guard_passed = False
        guard_error = str(exc)

    diagnostics = cavity_plan.get("diagnostics", [])
    if not isinstance(diagnostics, list):
        diagnostics = []
    diagnostics_by_code = _count_diagnostics_by_code(diagnostics)

    quantity_delta = cavity_plan.get("quantity_delta", {})
    if not isinstance(quantity_delta, dict):
        quantity_delta = {}
    quantity_mismatch_from_delta = 0
    for delta in quantity_delta.values():
        if not isinstance(delta, dict):
            continue
        original_required_qty = _safe_int(delta.get("original_required_qty"), 0)
        internal_qty = _safe_int(delta.get("internal_qty"), 0)
        top_level_qty = _safe_int(delta.get("top_level_qty"), 0)
        if internal_qty + top_level_qty != original_required_qty:
            quantity_mismatch_from_delta += 1

    virtual_solver_placements = _build_virtual_solver_placements(cavity_plan)
    base_parts = base_engine_input.get("parts", [])
    if not isinstance(base_parts, list):
        base_parts = []
    validation_issues: list[ValidationIssue] = validate_cavity_plan_v2(
        cavity_plan=cavity_plan,
        part_records=base_parts,
        solver_placements=virtual_solver_placements,
        strict=False,
    )
    validation_issues_json = [
        {
            "code": issue.code,
            "message": issue.message,
            "context": issue.context,
        }
        for issue in validation_issues
    ]

    overlap_count = sum(1 for issue in validation_issues if issue.code == "CAVITY_CHILD_CHILD_OVERLAP")
    bounds_violation_count = sum(1 for issue in validation_issues if issue.code == "CAVITY_CHILD_OUTSIDE_PARENT_CAVITY")
    quantity_mismatch_from_validator = sum(1 for issue in validation_issues if issue.code == "CAVITY_QUANTITY_MISMATCH")
    quantity_mismatch_count = max(int(quantity_mismatch_from_delta), int(quantity_mismatch_from_validator))

    cli_args = build_nesting_engine_cli_args_for_quality_profile("quality_cavity_prepack")
    cli_arg_str = " ".join(str(item) for item in cli_args)
    nfp_fallback_occurred = "--placer blf" in cli_arg_str

    summary = cavity_plan.get("summary", {})
    if not isinstance(summary, dict):
        summary = {}
    placement_trees = cavity_plan.get("placement_trees", {})
    if not isinstance(placement_trees, dict):
        placement_trees = {}
    internal_placement_count, nested_internal_placement_count = _count_tree_depth_metrics(placement_trees)

    virtual_parts = cavity_plan.get("virtual_parts", {})
    if not isinstance(virtual_parts, dict):
        virtual_parts = {}

    minimum_failures: list[str] = []
    if holes_after != 0:
        minimum_failures.append(f"holes_after={holes_after} (expected 0)")
    if quantity_mismatch_count != 0:
        minimum_failures.append(f"quantity_mismatch_count={quantity_mismatch_count} (expected 0)")
    if not guard_passed:
        minimum_failures.append("guard_passed=False (expected True)")

    result: dict[str, Any] = {
        "benchmark": "cavity_v2_t10_lv8",
        "fixture_path": str(fixture_path),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "quality_profile": "quality_cavity_prepack",
        "top_level_holes_count_before_prepack": int(holes_before),
        "top_level_holes_count_after_prepack": int(holes_after),
        "guard_passed": bool(guard_passed),
        "guard_error": guard_error,
        "virtual_parent_count": int(len(virtual_parts)),
        "usable_cavity_count": int(summary.get("usable_cavity_count") or 0),
        "holed_child_proxy_count": int(diagnostics_by_code.get("child_has_holes_outer_proxy_used", 0)),
        "quantity_delta_parts": int(len(quantity_delta)),
        "quantity_mismatch_count": int(quantity_mismatch_count),
        "engine_cli_args": cli_args,
        "engine_cli_args_expect_part_in_part_off": ("--part-in-part" in cli_args and "off" in cli_args),
        "nfp_fallback_occurred": bool(nfp_fallback_occurred),
        "validation_issues": validation_issues_json,
        "overlap_count": int(overlap_count),
        "bounds_violation_count": int(bounds_violation_count),
        "prepack_elapsed_sec": prepack_elapsed_sec,
        "internal_placement_count": int(
            summary.get("internal_placement_count") if isinstance(summary.get("internal_placement_count"), int) else internal_placement_count
        ),
        "nested_internal_placement_count": int(nested_internal_placement_count),
        "diagnostics_by_code": diagnostics_by_code,
        "timeout_occurred": False,
        "placed_count": None,
        "unplaced_count": None,
        "utilization_ratio": None,
        "minimum_criteria_passed": len(minimum_failures) == 0,
        "minimum_criteria_failures": minimum_failures,
    }

    output_dir_abs = (REPO_ROOT / output_dir).resolve()
    if not str(output_dir_abs).startswith(str((REPO_ROOT / "tmp/benchmark_results").resolve())):
        raise RuntimeError("output_dir must stay under tmp/benchmark_results")
    output_dir_abs.mkdir(parents=True, exist_ok=True)
    out_name = f"cavity_v2_lv8_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    out_path = output_dir_abs / out_name
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result, out_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cavity v2 LV8 benchmark runner")
    parser.add_argument("--fixture", type=Path, default=None, help="Benchmark fixture JSON path")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("tmp/benchmark_results"),
        help="Output directory for JSON benchmark artifact (must stay under tmp/benchmark_results)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    fixture_path = args.fixture
    if fixture_path is None:
        fixture_path = _choose_auto_fixture()
    if fixture_path is None:
        synthetic_payload = _build_synthetic_fixture_payload()
        output_dir_abs = (REPO_ROOT / args.output_dir).resolve()
        output_dir_abs.mkdir(parents=True, exist_ok=True)
        synthetic_fixture_path = output_dir_abs / "synthetic_cavity_v2_fixture.json"
        synthetic_fixture_path.write_text(
            json.dumps(synthetic_payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        fixture_path = synthetic_fixture_path
        print(
            f"WARNING: No fixture found. Using synthetic fallback fixture: {fixture_path}",
            file=sys.stderr,
        )
    if not fixture_path.is_file():
        print(f"ERROR: Fixture not found: {fixture_path}", file=sys.stderr)
        return 1

    result, out_path = run_benchmark(fixture_path=fixture_path, output_dir=args.output_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"\nSaved benchmark artifact: {out_path}")

    if bool(result.get("minimum_criteria_passed")):
        print("Minimum criteria: PASSED")
        return 0

    print("Minimum criteria: FAILED", file=sys.stderr)
    for item in result.get("minimum_criteria_failures", []):
        print(f" - {item}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
