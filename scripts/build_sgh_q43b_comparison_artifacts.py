#!/usr/bin/env python3
"""SGH-Q43b — Build comparison_summary.json and semantic_parity_matrix.json
for the own vrs_solver 1x1500x6000 strip baseline run.

Mirrors scripts/build_sgh_q43_comparison_artifacts.py but for Q43b. The
comparison is 3-way:
  - Q43 upstream Sparrow SPP 1500x6000 1200s
  - Q43b own vrs_solver 1x1500x6000 1200s
  - Q42 own vrs_solver 3x1500x3000 1200s
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
Q43 = ROOT / "artifacts" / "benchmarks" / "sgh_q43"
Q43B = ROOT / "artifacts" / "benchmarks" / "sgh_q43b"
Q42 = ROOT / "artifacts" / "benchmarks" / "sgh_q42"

VERDICTS = ["MATCH", "ADAPTED MATCH", "INTENTIONAL DIVERGENCE",
            "RISKY DIVERGENCE", "UNKNOWN / NOT VERIFIED"]


def load_json(p: Path) -> dict[str, Any] | None:
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def build_comparison() -> dict[str, Any]:
    q43 = load_json(Q43 / "upstream_summary.json") or {}
    q43b = load_json(Q43B / "upstream_summary.json") or {}
    q42 = load_json(Q42 / "q42_summary.json") or {}
    best_q42 = q42.get("best_run") if isinstance(q42, dict) else None

    def _cell(name: str) -> dict[str, Any]:
        return {
            "model_type": name,
            "container_or_sheet": None,
            "time_limit_s": None,
            "wall_time_s": None,
            "status": None,
            "placed_count": None,
            "unplaced_count": None,
            "validity": None,
            "objective_or_utilization": None,
            "rotation_evidence": None,
            "margin_spacing_handling": None,
        }

    row_q43 = _cell("upstream_SPP_1500x6000_1200s")
    row_q43b = _cell("own_vrs_solver_1x1500x6000_1200s")
    row_q42 = _cell("own_vrs_solver_3x1500x3000_1200s")

    # Q43 upstream
    if q43.get("run_a", {}).get("status") == "ok":
        a = q43["run_a"]
        row_q43.update({
            "container_or_sheet": "1500x6000 mm strip (SPP)",
            "time_limit_s": a.get("time_limit_s"),
            "wall_time_s": a.get("wall_time_s"),
            "status": a.get("status"),
            "placed_count": a.get("placed_count"),
            "unplaced_count": a.get("unplaced_count"),
            "validity": "valid (full placement, upstream SPP guarantees collision-free)",
            "objective_or_utilization": {
                "strip_width_used": a.get("strip_width_used"),
                "density": a.get("density"),
                "used_length_y": a.get("used_length_y")
            },
            "rotation_evidence": {
                "unique_rotation_count": a.get("unique_rotation_count"),
                "non_orthogonal_count": a.get("non_orthogonal_count"),
                "min_rotation_deg": a.get("min_rotation_deg"),
                "max_rotation_deg": a.get("max_rotation_deg")
            },
            "margin_spacing_handling": "not native in upstream SPP; none applied for Q43"
        })

    # Q43b own
    if q43b.get("run_a", {}).get("status") == "ok":
        a = q43b["run_a"]
        row_q43b.update({
            "container_or_sheet": "1x 1500x6000 mm finite stock (own solver)",
            "time_limit_s": a.get("time_limit_s"),
            "wall_time_s": a.get("wall_time_s"),
            "status": a.get("status_solver") or a.get("status"),
            "placed_count": a.get("placed_count"),
            "unplaced_count": a.get("unplaced_count"),
            "validity": "partial: 218/276 placed, 58 unplaced (Q40/Q41 spacing/margin expands effective polygons)",
            "objective_or_utilization": {
                "physical_utilization_pct": None,
                "usable_utilization_pct": None,
                "effective_density_proxy": round(a.get("placed_count", 0) / 276.0, 4)
            },
            "rotation_evidence": {
                "unique_rotation_count": a.get("unique_rotation_count"),
                "non_orthogonal_count": a.get("non_orthogonal_count"),
                "min_rotation_deg": a.get("min_rotation_deg"),
                "max_rotation_deg": a.get("max_rotation_deg")
            },
            "margin_spacing_handling": "Q40/Q41 unified model: margin_mm=5, spacing_mm=8, kerf_mm=0"
        })

    # Q42 own
    if best_q42:
        row_q42.update({
            "container_or_sheet": "3x 1500x3000 mm finite stock (own solver)",
            "time_limit_s": best_q42.get("time_limit_s"),
            "wall_time_s": best_q42.get("wall_time_s"),
            "status": best_q42.get("status"),
            "placed_count": best_q42.get("placed_count"),
            "unplaced_count": best_q42.get("unplaced_count"),
            "validity": "valid (3 sheets used; 2-sheet acceptance FAIL per Q42 spec)",
            "objective_or_utilization": {
                "physical_utilization_pct": best_q42.get("physical_utilization_pct"),
                "usable_utilization_pct": best_q42.get("usable_utilization_pct")
            },
            "rotation_evidence": {
                "unique_rotation_count": (best_q42.get("rotation_evidence") or {}).get("unique_rotation_values_count"),
                "non_orthogonal_count": best_q42.get("non_orthogonal_rotation_count")
            },
            "margin_spacing_handling": "Q40/Q41 unified model: margin_mm=5, spacing_mm=8, kerf_mm=0 (Q42 default); violations=0"
        })

    return {
        "task": "sgh_q43b_3_way_comparison",
        "direct_comparability": "PARTIAL_DIRECTLY_COMPARABLE",
        "reason": (
            "Q43 upstream SPP and Q43b own vrs_solver both use a 1500x6000 container; "
            "geometry is identical (12 part types / 276 instances from Q42). However, "
            "the inventory model (SPP single strip vs finite stock pool) and objective "
            "function (minimize used width vs maximize placed count) differ. Q42 is on a "
            "different inventory (3x1500x3000) and a different objective (minimize used sheet "
            "count). Numeric metrics are informative; they are not strict like-for-like benchmarks."
        ),
        "rows": [row_q43, row_q43b, row_q42]
    }


# Q43b-specific semantic parity matrix (from the OWN solver's perspective)
# Verdict categories mirror Q43's; verdicts are based on the static review
# performed for Q43 and re-applied here with the Q43b-specific evidence.
PARITY_TOPICS = [
    {
        "id": "problem_model",
        "title": "Problem model parity (own solver side)",
        "verdict": "INTENTIONAL DIVERGENCE",
        "verdict_reason": (
            "Q43b uses the own solver's finite-stock single-strip model. This is a subset of "
            "the full multisheet (Q32) — the solver is invoked with stocks=[1x1500x6000] so "
            "the finite-stock manager degenerates to a single-sheet run. The upstream SPP "
            "(Q43) is a different objective (min-width) on the same container."
        ),
        "evidence_upstream": [".cache/sparrow/src/ (SPP model)"],
        "evidence_own": [
            "rust/vrs_solver/src/optimizer/sparrow/multisheet.rs",
            "artifacts/benchmarks/sgh_q43b/inputs/q43b_full276_1x1500x6000_…json (stocks=1)"
        ]
    },
    {
        "id": "geometry_representation",
        "title": "Geometry representation parity",
        "verdict": "ADAPTED MATCH",
        "verdict_reason": (
            "Both upstream SPP and own solver use the same simple_polygon item format. Own "
            "solver applies Q40/Q41 spacing expansion (8mm) and sheet margin (5mm) to the "
            "CDE-input geometry. This expansion is upstream-invisible in Q43 baseline (no "
            "margin/spacing), which directly explains the 58 unplaced items in Q43b."
        ),
        "evidence_upstream": [".cache/sparrow/src/optimizer/"],
        "evidence_own": [
            "rust/vrs_solver/src/optimizer/sparrow/geometry/",
            "rust/vrs_solver/src/technology/clearance.rs"
        ]
    },
    {
        "id": "collision_cde",
        "title": "Collision / CDE parity",
        "verdict": "MATCH",
        "verdict_reason": (
            "Both upstream SPP and own solver use the jagua-rs CDE for narrow-phase collision "
            "queries. Q43b's collision pairs=0 confirms the CDE is consistent and the partial "
            "result is collision-free, not 'infeasible placement'."
        ),
        "evidence_upstream": [".cache/sparrow/src/quantify/"],
        "evidence_own": [
            "rust/vrs_solver/src/optimizer/sparrow/quantify/tracker.rs",
            "artifacts/benchmarks/sgh_q43b/q43b_summary.json:sparrow_collision_graph_final_pairs=0"
        ]
    },
    {
        "id": "search_sampling",
        "title": "Search / sampling / optimizer loop parity",
        "verdict": "MATCH",
        "verdict_reason": (
            "Q43b ran 212 iterations in 1138.96s (51508 search position calls). The loop is "
            "the same upstream-style structure (global sample gen + best-samples + coord "
            "descent + disruption). Q30 profiler confirms no semantic deviation in the loop."
        ),
        "evidence_upstream": [".cache/sparrow/src/sample/"],
        "evidence_own": [
            "rust/vrs_solver/src/optimizer/sparrow/sample/",
            "artifacts/benchmarks/sgh_q43b/q43b_summary.json:sparrow_iterations=212"
        ]
    },
    {
        "id": "lbf_initial_placement",
        "title": "LBF / initial placement parity",
        "verdict": "ADAPTED MATCH",
        "verdict_reason": (
            "LBF (Left-Bottom-Fill) is upstream default. Own lbf.rs mirrors the ordering. "
            "In Q43b the multisheet manager degenerates to 1 sheet so LBF is the primary "
            "initial placer; this is upstream-equivalent for a single-strip case."
        ),
        "evidence_upstream": [".cache/sparrow/src/optimizer/"],
        "evidence_own": ["rust/vrs_solver/src/optimizer/sparrow/lbf.rs"]
    },
    {
        "id": "rotation_policy",
        "title": "Rotation policy parity",
        "verdict": "MATCH",
        "verdict_reason": (
            "Continuous rotation effective in Q43b: 184 unique angles, 189 non-orthogonal, "
            "min -34.65 / max 367.45 deg. This is much finer than Q43 upstream SPP's 16-bin "
            "approximation, and matches the Q40/Q41-spec continuous handling."
        ),
        "evidence_upstream": [".cache/sparrow/src/sample/"],
        "evidence_own": [
            "rust/vrs_solver/src/rotation_policy.rs",
            "artifacts/benchmarks/sgh_q43b/q43b_summary.json:unique_rotation_count=184"
        ]
    },
    {
        "id": "multisheet_finite_stock",
        "title": "Strip vs finite-stock multisheet divergence",
        "verdict": "INTENTIONAL DIVERGENCE",
        "verdict_reason": (
            "Upstream is single-strip SPP; Q43b is a single finite stock (degenerate case of "
            "the finite-stock multisheet manager). They share the container area but not the "
            "inventory model."
        ),
        "evidence_upstream": [".cache/sparrow/src/ (no multisheet)"],
        "evidence_own": [
            "rust/vrs_solver/src/optimizer/sparrow/multisheet.rs",
            "artifacts/benchmarks/sgh_q43b/inputs/q43b_…json (stocks=1)"
        ]
    },
    {
        "id": "margin_spacing_kerf",
        "title": "Margin / spacing / kerf parity",
        "verdict": "INTENTIONAL DIVERGENCE",
        "verdict_reason": (
            "Q43b applies margin=5, spacing=8, kerf=0 (Q40/Q41 unified model). Q43 upstream "
            "SPP has no margin/spacing concept, so its raw polygons are smaller in the CDE "
            "input. This is the direct cause of the 58 unplaced items in Q43b vs 0 in Q43."
        ),
        "evidence_upstream": [".cache/sparrow/src/ (no margin/spacing)"],
        "evidence_own": [
            "rust/vrs_solver/src/technology/clearance.rs",
            "rust/vrs_solver/src/optimizer/sparrow/geometry/"
        ]
    },
    {
        "id": "output_validation",
        "title": "Output / validation parity",
        "verdict": "ADAPTED MATCH",
        "verdict_reason": (
            "Q43b's own solver output includes explicit per-placement (x, y, rotation_deg) "
            "and optimizer_diagnostics block. Collision-free (final_pairs=0). The partial "
            "status is reported via status='partial' on the top level, which is the same "
            "convention as Q23/Q24 series."
        ),
        "evidence_upstream": [".cache/sparrow/src/util/io.rs"],
        "evidence_own": [
            "rust/vrs_solver/src/adapter.rs",
            "artifacts/benchmarks/sgh_q43b/outputs/q43b_…output.json"
        ]
    }
]


def build_parity_matrix() -> dict[str, Any]:
    return {
        "task": "sgh_q43b_semantic_parity_matrix_own_solver_view",
        "methodology": (
            "Static review of upstream Sparrow source under .cache/sparrow/src and own "
            "solver source under rust/vrs_solver/src/optimizer/sparrow, with Q43b-specific "
            "evidence taken from artifacts/benchmarks/sgh_q43b/ (input, output, log, summary). "
            "Each topic is labelled MATCH / ADAPTED MATCH / INTENTIONAL DIVERGENCE / RISKY "
            "DIVERGENCE / UNKNOWN. No additional behavioural replay test was executed beyond "
            "the Q43b run itself."
        ),
        "topics": PARITY_TOPICS,
        "allowed_verdicts": VERDICTS
    }


def main() -> int:
    comparison = build_comparison()
    (Q43B / "comparison_summary.json").write_text(json.dumps(comparison, indent=2))
    parity = build_parity_matrix()
    (Q43B / "semantic_parity_matrix.json").write_text(json.dumps(parity, indent=2))
    print(f"wrote {Q43B / 'comparison_summary.json'}")
    print(f"wrote {Q43B / 'semantic_parity_matrix.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
