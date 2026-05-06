#!/usr/bin/env python3
"""
Verify safe flatten: run full preflight chain on the two previously problematic DXFs.

Checks:
1. No review_required from nested island conflict
2. Full chain (T1→T6) completes without error
3. Acceptance outcome == accepted_for_import
4. Importer probe hole count is meaningful
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api.services.dxf_preflight_inspect import inspect_dxf_source
from api.services.dxf_preflight_role_resolver import resolve_dxf_roles
from api.services.dxf_preflight_gap_repair import repair_dxf_gaps
from api.services.dxf_preflight_duplicate_dedupe import dedupe_dxf_duplicate_contours
from api.services.dxf_preflight_normalized_dxf_writer import write_normalized_dxf
from api.services.dxf_preflight_acceptance_gate import evaluate_dxf_prefilter_acceptance_gate

_PROFILE = {
    "strict_mode": False,
    "auto_repair_enabled": True,
    "interactive_review_on_ambiguity": True,
    "max_gap_close_mm": 2.0,
    "duplicate_contour_merge_tolerance_mm": 0.1,
}


def verify_dxf(dxf_path: Path):
    print(f"\n{'='*70}")
    print(f"VERIFYING: {dxf_path.name}")
    print(f"{'='*70}")

    errors = []
    warnings = []

    # T1 inspect
    inspect_result = inspect_dxf_source(str(dxf_path))
    print(f"  T1 inspect: OK, {len(inspect_result.get('contour_candidates', []))} contours")

    # T2 role resolver
    role_result = resolve_dxf_roles(inspect_result, rules_profile=_PROFILE)
    contour_assignments = role_result.get("contour_role_assignments", [])
    review_required = role_result.get("review_required_candidates", [])
    blocking = role_result.get("blocking_conflicts", [])

    island_review = [r for r in review_required if r.get("family") == "contour_nested_island_unsupported"]
    if island_review:
        errors.append(f"NESTED_ISLAND_STILL_REVIEW: {len(island_review)} nested island conflicts remain")
    else:
        print(f"  T2 resolver: OK, 0 nested island conflicts")

    cut_outer = [a for a in contour_assignments if a.get("canonical_role") == "CUT_OUTER"]
    cut_inner = [a for a in contour_assignments if a.get("canonical_role") == "CUT_INNER"]
    print(f"  T2 roles: {len(cut_outer)} CUT_OUTER, {len(cut_inner)} CUT_INNER")

    # T3 gap repair
    gap_repair_result = repair_dxf_gaps(inspect_result, role_result, rules_profile=_PROFILE)
    print(f"  T3 gap repair: OK")

    # T4 dedupe
    dedupe_result = dedupe_dxf_duplicate_contours(
        inspect_result, role_result, gap_repair_result, rules_profile=_PROFILE
    )
    deduped = dedupe_result.get("deduped_contour_working_set", [])
    print(f"  T4 dedupe: OK, {len(deduped)} contours in working set")

    # T5 writer
    with tempfile.NamedTemporaryFile(suffix=".dxf", delete=False) as tf:
        out_path = tf.name
    writer_result = write_normalized_dxf(
        inspect_result, role_result, gap_repair_result, dedupe_result,
        output_path=out_path
    )
    norm_dxf = writer_result.get("normalized_dxf", {})
    written_path = norm_dxf.get("output_path", "")
    print(f"  T5 writer: OK, wrote {written_path}")

    # T6 acceptance gate
    gate_result = evaluate_dxf_prefilter_acceptance_gate(
        inspect_result, role_result, gap_repair_result, dedupe_result, writer_result
    )
    outcome = gate_result.get("acceptance_outcome", "UNKNOWN")
    probe = gate_result.get("importer_probe", {})
    hole_count = probe.get("hole_count", -1)
    outer_pts = probe.get("outer_point_count", -1)

    print(f"  T6 gate: outcome={outcome}")
    print(f"  T6 importer probe: outer_points={outer_pts}, holes={hole_count}")

    if outcome != "accepted_for_import":
        errors.append(f"NOT_ACCEPTED: outcome={outcome}")
        blockers = gate_result.get("blocking_reasons", [])
        reviews = gate_result.get("review_required_reasons", [])
        if blockers:
            print(f"    blocking_reasons: {blockers}")
        if reviews:
            print(f"    review_required_reasons: {reviews}")
    else:
        print(f"  PASS: accepted_for_import")

    # Sanity checks
    if len(cut_outer) == 0:
        errors.append("NO_OUTER_ASSIGNED")
    if hole_count < 0:
        warnings.append("IMPORTER_PROBE_NO_HOLE_COUNT")

    return {
        "file": dxf_path.name,
        "errors": errors,
        "warnings": warnings,
        "outcome": outcome,
        "cut_outer_count": len(cut_outer),
        "cut_inner_count": len(cut_inner),
        "hole_count": hole_count,
        "outer_points": outer_pts,
    }


def main():
    if len(sys.argv) < 3:
        print("Usage: verify_nested_flatten.py <lv6_dxf> <lv8_dxf>")
        sys.exit(1)

    lv6_path = Path(sys.argv[1])
    lv8_path = Path(sys.argv[2])

    results = []
    results.append(verify_dxf(lv6_path))
    results.append(verify_dxf(lv8_path))

    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")

    all_pass = True
    for r in results:
        status = "FAIL" if r["errors"] else "WARN" if r["warnings"] else "PASS"
        if r["errors"]:
            all_pass = False
        print(f"  {r['file']}: {status}")
        print(f"    outcome={r['outcome']}, outer={r['cut_outer_count']}, inner={r['cut_inner_count']}, holes={r['hole_count']}")
        for e in r["errors"]:
            print(f"    ERROR: {e}")
        for w in r["warnings"]:
            print(f"    WARN: {w}")

    if all_pass:
        print("\n  ALL PASS")
    else:
        print("\n  SOME FAILURES — see above")
        sys.exit(1)


if __name__ == "__main__":
    main()
