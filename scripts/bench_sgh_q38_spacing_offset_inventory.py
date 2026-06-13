#!/usr/bin/env python3
"""SGH-Q38 — robust spacing-offset inventory over the real LV8 parts.

For each spacing in {2,5,10,20,40} the OFFSET STATUS per part is taken AUTHORITATIVELY
from the Rust solver: a single-instance-per-part input on a large sheet is solved, and any
part emitted unplaced with reason UNSUPPORTED_SPACING_OFFSET_Q36 is recorded as unsupported
at that spacing (the Rust `build_spacing_expanded_outer_polygon` is the production offset).
Per-part offset geometry detail columns (vertex/area/bbox/ratio) are computed with a
reference robust buffer (shapely) for the supported parts.

Outputs:
  artifacts/benchmarks/sgh_q38/tables/q38_spacing_offset_inventory.csv
  artifacts/benchmarks/sgh_q38/tables/q38_spacing_offset_manifest.json
"""
from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOLVER_BIN = ROOT / "rust" / "vrs_solver" / "target" / "release" / "vrs_solver"
BASE_FULL276 = ROOT / "artifacts/benchmarks/sgh_q32/inputs/case_01_2x1500x3000.json"
Q38 = ROOT / "artifacts/benchmarks/sgh_q38"
TABLES = Q38 / "tables"
INPUTS = Q38 / "inputs"
OUTPUTS = Q38 / "outputs"

SPACINGS = [2, 5, 10, 20, 40]
UNSUPPORTED = "UNSUPPORTED_SPACING_OFFSET_Q36"

try:
    from shapely.geometry import Polygon as ShPoly
    HAVE_SHAPELY = True
except Exception:
    HAVE_SHAPELY = False


def parts() -> list[dict]:
    return json.loads(BASE_FULL276.read_text())["parts"]


def part_polygon(p: dict):
    raw = p.get("prepared_outer_points") or p.get("outer_points")
    if not raw:
        return None
    pts = [(float(a[0]), float(a[1])) for a in raw if len(a) >= 2]
    return pts if len(pts) >= 3 else None


def poly_area(pts):
    n = len(pts)
    return abs(0.5 * sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1] for i in range(n)))


def bbox_area(pts):
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    return (max(xs) - min(xs)) * (max(ys) - min(ys))


def rust_offset_status_by_spacing() -> dict[int, set[str]]:
    """Return {spacing: set(part_ids unsupported at that spacing)} from the Rust solver."""
    INPUTS.mkdir(parents=True, exist_ok=True)
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    ps = parts()
    failed: dict[int, set[str]] = {}
    for spacing in SPACINGS:
        doc = {
            "contract_version": "v1",
            "project_name": f"q38_offset_probe_s{spacing}",
            "seed": 42,
            "time_limit_s": 3,
            "optimizer_pipeline": "sparrow_cde_multisheet",
            "collision_backend": "cde",
            "solver_profile": "jagua_optimizer_phase1_outer_only",
            "margin_mm": 0.0,
            "spacing_mm": float(spacing),
            "kerf_mm": 0.0,
            # Large sheet so the only unplaced reason is offset failure, not capacity.
            "stocks": [{"id": "BIG", "quantity": 1, "width": 8000.0, "height": 8000.0}],
            "parts": [dict(p, quantity=1) for p in ps],
        }
        inp = INPUTS / f"offset_probe_s{spacing}.json"
        inp.write_text(json.dumps(doc, indent=2))
        out = OUTPUTS / f"offset_probe_s{spacing}_output.json"
        proc = subprocess.run(
            [str(SOLVER_BIN), "--input", str(inp), "--output", str(out)],
            capture_output=True, text=True, timeout=120,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"solver exit {proc.returncode} (spacing {spacing}): {proc.stderr[:300]}")
        o = json.loads(out.read_text())
        bad = {u["part_id"] for u in o.get("unplaced", []) if u.get("reason") == UNSUPPORTED}
        failed[spacing] = bad
        d = o.get("optimizer_diagnostics", {})
        print(f"  spacing {spacing}: offset_failure_count={d.get('technology_spacing_offset_failure_count')} "
              f"offset_part_count={d.get('technology_spacing_offset_part_count')} unsupported_parts={sorted(bad)}")
    return failed


def shapely_offset_detail(pts, half):
    if not HAVE_SHAPELY or half <= 0:
        return None
    try:
        poly = ShPoly(pts)
        if not poly.is_valid:
            poly = poly.buffer(0)
        buf = poly.buffer(half, join_style=2)  # mitre
        if buf.is_empty or buf.geom_type != "Polygon":
            return None
        ext = list(buf.exterior.coords)[:-1]
        return ext
    except Exception:
        return None


def main() -> int:
    if not SOLVER_BIN.exists():
        print(f"ERROR: solver binary missing: {SOLVER_BIN}")
        return 1
    for d in (TABLES, INPUTS, OUTPUTS):
        d.mkdir(parents=True, exist_ok=True)

    print("=== Q38 robust spacing-offset inventory (Rust-authoritative status) ===")
    failed = rust_offset_status_by_spacing()

    ps = parts()
    rows = []
    offsettable = {s: 0 for s in SPACINGS}
    unsupported = {s: 0 for s in SPACINGS}
    for p in ps:
        poly = part_polygon(p)
        row = {
            "part_id": p["id"],
            "declared_quantity": p["quantity"],
            "width": p.get("width"),
            "height": p.get("height"),
            "outer_vertex_count": len(poly) if poly else 0,
            "polygon_area": round(poly_area(poly), 4) if poly else 0.0,
            "bbox_area": round(bbox_area(poly), 4) if poly else 0.0,
            "area_to_bbox_ratio": round(poly_area(poly) / bbox_area(poly), 6) if poly and bbox_area(poly) > 0 else 0.0,
            "offset_error_reason": "",
        }
        for spacing in SPACINGS:
            tag = f"spacing_{spacing}"
            is_unsupported = p["id"] in failed.get(spacing, set())
            status = UNSUPPORTED if is_unsupported else "ok"
            row[f"{tag}_offset_status"] = status
            if status == "ok":
                offsettable[spacing] += 1
            else:
                unsupported[spacing] += 1
                row["offset_error_reason"] = status
            det = shapely_offset_detail(poly, spacing / 2.0) if (poly and status == "ok") else None
            if det:
                row[f"{tag}_offset_vertex_count"] = len(det)
                row[f"{tag}_offset_area"] = round(poly_area(det), 4)
                row[f"{tag}_offset_bbox_area"] = round(bbox_area(det), 4)
                row[f"{tag}_offset_area_ratio"] = round(poly_area(det) / poly_area(poly), 6) if poly_area(poly) > 0 else 0.0
            else:
                row[f"{tag}_offset_vertex_count"] = 0
                row[f"{tag}_offset_area"] = 0.0
                row[f"{tag}_offset_bbox_area"] = 0.0
                row[f"{tag}_offset_area_ratio"] = 0.0
        rows.append(row)

    # Column order matches the spec.
    cols = ["part_id", "declared_quantity", "width", "height", "outer_vertex_count",
            "polygon_area", "bbox_area", "area_to_bbox_ratio"]
    for s in SPACINGS:
        cols += [f"spacing_{s}_offset_status", f"spacing_{s}_offset_vertex_count",
                 f"spacing_{s}_offset_area", f"spacing_{s}_offset_bbox_area", f"spacing_{s}_offset_area_ratio"]
    cols.append("offset_error_reason")
    with (TABLES / "q38_spacing_offset_inventory.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow(r)

    manifest = {
        "spacing_values_mm": SPACINGS,
        "unique_part_count": len(ps),
        "offset_status_source": "rust_solver (build_spacing_expanded_outer_polygon)",
        "geometry_detail_source": "shapely mitre buffer (reference)" if HAVE_SHAPELY else "none",
        "offsettable_by_spacing": {str(s): offsettable[s] for s in SPACINGS},
        "unsupported_by_spacing": {str(s): unsupported[s] for s in SPACINGS},
    }
    (TABLES / "q38_spacing_offset_manifest.json").write_text(json.dumps(manifest, indent=2))

    print("\n=== offsettable by spacing (Rust-authoritative) ===")
    for s in SPACINGS:
        print(f"  spacing {s}: {offsettable[s]}/{len(ps)} offsettable, {unsupported[s]} unsupported")

    # Q38 acceptance: 12/12 at spacing 2/5/10.
    ok = all(unsupported[s] == 0 for s in (2, 5, 10))
    print(f"\n  spacing 2/5/10 all offsettable: {ok}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
