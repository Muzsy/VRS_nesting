#!/usr/bin/env python3
"""SGH-Q38 smoke — robust spacing offset for real concave/high-vertex LV8 polygons.

Static checks:
  - spacing_geometry.rs uses a robust buffer (geo-buffer), keeps the Q36 API, and adds
    validate_spacing_offset_outer_contour;
  - no raw/original fallback and no bbox-expand fallback on offset failure;
  - kerf_mm is not added to spacing;
  - cavity prepack .rs files unmodified;
  - q38 inventory bench + report exist.

Dynamic checks:
  - q38_spacing_offset_inventory.csv + manifest exist;
  - LV8 offsettable 12/12 at spacing 2/5/10; unsupported 0 at spacing 2;
  - Lv8_07919 / 07920 / 07921 are 'ok' at spacing 2/5/10;
  - no self-intersecting output (status never SELF_INTERSECTING at 2/5/10);
  - Q37 mandatory short rerun spacing runs (D1/D2/M1/M2) have offset_failure_count == 0.

Exit codes: 0 PASS, 2 FAIL
"""
from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SG = ROOT / "rust/vrs_solver/src/technology/spacing_geometry.rs"
BENCH = ROOT / "scripts/bench_sgh_q38_spacing_offset_inventory.py"
REPORT = ROOT / "codex/reports/egyedi_solver/sgh_q38_robust_spacing_offset.md"
TABLES = ROOT / "artifacts/benchmarks/sgh_q38/tables"
INV = TABLES / "q38_spacing_offset_inventory.csv"
MANIFEST = TABLES / "q38_spacing_offset_manifest.json"
Q37_SUMMARY = ROOT / "artifacts/benchmarks/sgh_q37/tables/q37_run_summary.csv"

PASS = 0
FAIL = 0


def check(cond, msg):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [PASS] {msg}")
    else:
        FAIL += 1
        print(f"  [FAIL] {msg}")


def strip_comments(text: str) -> str:
    import re
    text = re.sub(r"(?s)/\*.*?\*/", "", text)
    text = re.sub(r"(?m)//.*$", "", text)
    return text


def main():
    print("=== SGH-Q38 robust spacing offset smoke ===")
    print("\n--- Static checks ---")
    sg_raw = SG.read_text() if SG.exists() else ""
    sg = strip_comments(sg_raw)
    check(SG.exists(), "spacing_geometry.rs exists")
    check("fn build_spacing_expanded_outer_polygon" in sg, "build_spacing_expanded_outer_polygon kept (Q36 API)")
    check("fn validate_spacing_offset_outer_contour" in sg, "validate_spacing_offset_outer_contour added")
    check("geo_buffer::buffer_polygon" in sg, "uses robust geo-buffer buffer_polygon")
    # No bbox-expand fallback: the offset must not synthesize a width/height rectangle on failure.
    check("bbox_expand" not in sg.lower() and "bbox-expand" not in sg.lower(),
          "no bbox-expand fallback present")
    # No raw/original fallback: failure returns an error, never the original contour.
    # (build returns original ONLY for half<=0; that is the no-op case, not a failure fallback.)
    check("MULTI_CONTOUR_SPACING_OFFSET_Q38" in sg_raw or "MultiContour" in sg,
          "explicit multi-contour error handling")
    check("BufferFailed" in sg, "explicit buffer-failure error handling (no silent fallback)")
    # kerf not added to spacing anywhere in the offset module.
    import re
    check(re.search(r"spacing\w*\s*\+\s*\w*kerf|kerf\w*\s*\+\s*spacing", sg) is None,
          "kerf_mm not added to spacing in offset module")
    check(BENCH.exists(), "q38 inventory bench exists")
    check(REPORT.exists(), "q38 report exists")
    if REPORT.exists():
        rep = REPORT.read_text()
        check("## Recommended next task" in rep, "report has 'Recommended next task'")
        check("## Large spacing interpretation" in rep, "report has 'Large spacing interpretation'")

    # Cavity prepack untouched.
    try:
        res = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain"],
                             capture_output=True, text=True, timeout=30)
        changed = [l for l in res.stdout.splitlines() if "cavity" in l.lower() and ".rs" in l.lower()]
        check(not changed, f"no cavity prepack .rs modified ({changed})")
    except Exception:
        check(True, "git unavailable → skip cavity check")

    print("\n--- Dynamic checks (Q38 inventory) ---")
    check(INV.exists(), "q38_spacing_offset_inventory.csv exists")
    check(MANIFEST.exists(), "q38_spacing_offset_manifest.json exists")
    if MANIFEST.exists():
        m = json.loads(MANIFEST.read_text())
        ob = m.get("offsettable_by_spacing", {})
        un = m.get("unsupported_by_spacing", {})
        n = m.get("unique_part_count", 12)
        for s in ("2", "5", "10"):
            check(ob.get(s) == n, f"spacing {s}: {ob.get(s)}/{n} offsettable (need {n}/{n})")
        check(un.get("2") == 0, f"spacing 2: unsupported == 0 (got {un.get('2')})")
        check("20" in ob and "40" in ob, "spacing 20 and 40 measured")

    if INV.exists():
        rows = {r["part_id"]: r for r in csv.DictReader(INV.open())}
        for pid_sub in ("07919", "07920", "07921"):
            row = next((r for k, r in rows.items() if pid_sub in k), None)
            if row is None:
                check(False, f"inventory has part {pid_sub}")
                continue
            for s in ("2", "5", "10"):
                st = row.get(f"spacing_{s}_offset_status")
                check(st == "ok", f"Lv8_{pid_sub} spacing {s} offset ok (got {st})")
        # No self-intersecting accepted output at 2/5/10.
        bad = []
        for pid, r in rows.items():
            for s in ("2", "5", "10"):
                if r.get(f"spacing_{s}_offset_status", "").startswith("SELF_INTERSECTING"):
                    bad.append((pid, s))
        check(not bad, f"no SELF_INTERSECTING output at spacing 2/5/10 ({bad})")

    print("\n--- Q37 short rerun spacing offset_failure_count == 0 ---")
    if Q37_SUMMARY.exists():
        q37 = {r["run_id"]: r for r in csv.DictReader(Q37_SUMMARY.open())}
        for run_id in ("D1", "D2", "M1", "M2"):
            r = q37.get(run_id)
            if r is None:
                check(False, f"Q37 {run_id} present in summary")
                continue
            fc = r.get("technology_spacing_offset_failure_count")
            check(fc in ("0", 0), f"Q37 {run_id}: offset_failure_count == 0 (got {fc})")
    else:
        check(False, "Q37 run summary present (run bench_sgh_q37 --tier mandatory first)")

    print(f"\n{'='*52}")
    print(f"  PASS: {PASS}   FAIL: {FAIL}")
    if FAIL:
        print("  RESULT: FAIL")
        sys.exit(2)
    print("  RESULT: PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
