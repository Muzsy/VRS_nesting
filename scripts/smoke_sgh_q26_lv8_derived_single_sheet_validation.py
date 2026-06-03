#!/usr/bin/env python3
"""SGH-Q26 — LV8-derived 40-80 instance real-DXF single-sheet validation.

This is the Level 4B gate of the SGH-Q26 single-sheet validation suite. It is a
correctness/stability gate, NOT a benchmark: it proves that a deterministic
40-80 instance subset of the real LV8 part geometry places on a single
1500x3000 sheet through the repo's existing DXF -> Sparrow pipeline
(`scripts/run_real_dxf_sparrow_pipeline.py`, `dxf_v1` contract).

Source provenance
-----------------
The raw LV8 DXFs live in `samples/real_work_dxf/0014-01H/lv8jav`. Those raw files
carry their cut geometry on AutoCAD layer `0` (mixed with `Gravir` TEXT and
multiple closed bore contours), which is incompatible with the strict
`CUT_OUTER`/`CUT_INNER` convention the `dxf_v1` importer enforces. This gate
therefore consumes the *normalized* LV8 derivatives (same parts, geometry moved
to `CUT_OUTER`/`CUT_INNER`, text dropped) that import cleanly through the
existing pipeline. The normalized directory is, in order of precedence:

  1. $Q26_LV8_NORMALIZED_DIR (if set)
  2. samples/real_work_dxf/0014-01H/lv8jav_normalized   (committed default)

Hard scope (SGH-Q26)
--------------------
- single 1500x3000 stock, quantity 1; one sheet only; no `sheet_002.dxf`;
- deterministic subset totaling 40-80 instances with broad LV8 type coverage;
- status ok, unplaced_count == 0, placements_count == selected_instance_count;
- NOT the full LV8 production part set, NOT a utilization benchmark.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Source (raw, non-importable) and the normalized derivative directories.
LV8_RAW_DIR = ROOT / "samples" / "real_work_dxf" / "0014-01H" / "lv8jav"
LV8_NORMALIZED_DEFAULT = ROOT / "samples" / "real_work_dxf" / "0014-01H" / "lv8jav_normalized"

MANIFEST_PATH = (
    ROOT
    / "rust"
    / "vrs_solver"
    / "tests"
    / "fixtures"
    / "sgh_q26_single_sheet_validation"
    / "lv8_derived_subset_manifest.json"
)

# Single-sheet contract.
SHEET_W_MM = 1500.0
SHEET_H_MM = 3000.0
SPACING_MM = 10.0
MARGIN_MM = 10.0
SEED = 0
# Deterministic subset must land in [MIN_INSTANCES, MAX_INSTANCES].
MIN_INSTANCES = 40
MAX_INSTANCES = 80
# Per-file deterministic caps (broad coverage, comfortable single-sheet density).
CAP_LARGE = 3   # part bbox area >= LARGE_AREA_M2
CAP_SMALL = 6
LARGE_AREA_M2 = 0.05
# The strip packer runs for the full time budget; this is sufficient for a
# single-sheet placement gate (not a density benchmark) and keeps it practical.
DEFAULT_TIME_LIMIT_S = 120


class SmokeError(AssertionError):
    pass


def _require_ezdxf() -> None:
    if importlib.util.find_spec("ezdxf") is None:
        raise SmokeError(
            "ezdxf dependency missing for LV8-derived DXF smoke. "
            "Install with: python3 -m pip install --break-system-packages ezdxf"
        )


def _resolve_normalized_dir() -> Path:
    override = os.environ.get("Q26_LV8_NORMALIZED_DIR", "").strip()
    if override:
        d = Path(override)
        if not d.is_dir():
            raise SmokeError(f"Q26_LV8_NORMALIZED_DIR is not a directory: {d}")
        return d
    if LV8_NORMALIZED_DEFAULT.is_dir():
        return LV8_NORMALIZED_DEFAULT
    raise SmokeError(
        "normalized LV8 directory not found. Expected committed dir "
        f"{LV8_NORMALIZED_DEFAULT} or set $Q26_LV8_NORMALIZED_DIR."
    )


def _resolve_sparrow_bin() -> str | None:
    sparrow_bin = os.environ.get("SPARROW_BIN", "").strip()
    if sparrow_bin:
        return sparrow_bin
    candidate = ROOT / ".cache" / "sparrow" / "target" / "release" / "sparrow"
    if candidate.is_file():
        return str(candidate)
    return None


def _parse_quantity(name: str) -> int:
    m = re.search(r"_(\d+)db", name, re.IGNORECASE)
    return int(m.group(1)) if m else 1


def _select_subset(normalized_dir: Path) -> list[dict]:
    """Deterministic LV8 subset selection.

    Sorted by file name. Excludes parts whose bbox max dimension exceeds the
    sheet's shorter side (oversized for a single 1500x3000 at 0 deg). For the
    rest, select min(cap, parsed_db) instances, with a lower cap for large parts
    so a single large type cannot dominate the sheet area.
    """
    from vrs_nesting.dxf.importer import import_part_raw
    from vrs_nesting.geometry.offset import polygon_bbox
    from vrs_nesting.geometry.polygonize import polygonize_part_raw

    # Only real normalized LV8 DXF parts; ignore backup *.dxf~ files.
    files = sorted(
        p
        for p in normalized_dir.iterdir()
        if p.suffix.lower() == ".dxf" and not p.name.endswith("~")
    )
    if not files:
        raise SmokeError(f"no normalized LV8 .dxf files found in {normalized_dir}")

    rows: list[dict] = []
    for f in files:
        db = _parse_quantity(f.name)
        try:
            raw = import_part_raw(f)
            poly = polygonize_part_raw(raw.to_dict())
            min_x, min_y, max_x, max_y = polygon_bbox(poly)
        except Exception as exc:  # noqa: BLE001
            rows.append(
                {
                    "file": f.name,
                    "path": str(f),
                    "parsed_db": db,
                    "selected_quantity": 0,
                    "decision": f"excluded_import_error:{type(exc).__name__}",
                    "width_mm": None,
                    "height_mm": None,
                    "area_m2": None,
                }
            )
            continue
        w = float(max_x - min_x)
        h = float(max_y - min_y)
        area_m2 = (w * h) / 1.0e6
        max_dim = max(w, h)
        if max_dim > min(SHEET_W_MM, SHEET_H_MM):
            decision = "excluded_oversized_for_single_1500x3000"
            qty = 0
        else:
            cap = CAP_LARGE if area_m2 >= LARGE_AREA_M2 else CAP_SMALL
            qty = min(cap, db)
            decision = "selected"
        rows.append(
            {
                "file": f.name,
                "path": str(f),
                "parsed_db": db,
                "selected_quantity": qty,
                "decision": decision,
                "width_mm": round(w, 3),
                "height_mm": round(h, 3),
                "area_m2": round(area_m2, 6),
            }
        )
    return rows


def _write_manifest(normalized_dir: Path, rows: list[dict], total: int, selected_area_m2: float) -> None:
    selected = [r for r in rows if r["selected_quantity"] > 0]
    excluded = [r for r in rows if r["selected_quantity"] == 0]
    manifest = {
        "contract_version": "q26_lv8_derived_single_sheet_v1",
        "purpose": "deterministic LV8-derived single-sheet validation subset (NOT a benchmark)",
        "lv8_source_directory": str(LV8_RAW_DIR.relative_to(ROOT)),
        "lv8_normalized_directory": str(normalized_dir),
        "sheet": {"width_mm": SHEET_W_MM, "height_mm": SHEET_H_MM, "quantity": 1},
        "spacing_mm": SPACING_MM,
        "margin_mm": MARGIN_MM,
        "seed": SEED,
        "allowed_rotations_deg": [0, 90],
        "selection_rule": {
            "sort": "by file name ascending",
            "exclude": "bbox max dimension > min(sheet_w, sheet_h)",
            "cap_large": {"area_m2_threshold": LARGE_AREA_M2, "cap": CAP_LARGE},
            "cap_small": {"cap": CAP_SMALL},
            "quantity": "min(cap, parsed _<N>db)",
        },
        "selected_part_types": len(selected),
        "total_selected_instances": total,
        "selected_instance_count": total,
        "selected_area_m2": round(selected_area_m2, 6),
        "sheet_area_m2": round(SHEET_W_MM * SHEET_H_MM / 1.0e6, 6),
        "is_full_part_set": False,
        "is_density_benchmark": False,
        "selected_files": selected,
        "files": rows,
    }
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def _make_stock_dxf(path: Path) -> None:
    import ezdxf

    doc = ezdxf.new()
    doc.header["$INSUNITS"] = 4  # millimeters -> importer scale 1.0
    if "CUT_OUTER" not in doc.layers:
        doc.layers.add("CUT_OUTER")
    doc.modelspace().add_lwpolyline(
        [(0.0, 0.0), (SHEET_W_MM, 0.0), (SHEET_W_MM, SHEET_H_MM), (0.0, SHEET_H_MM)],
        close=True,
        dxfattribs={"layer": "CUT_OUTER"},
    )
    doc.saveas(str(path))


def _assert_native_diagnostics_if_present(solver_output: dict) -> str:
    diag = solver_output.get("optimizer_diagnostics")
    if not isinstance(diag, dict):
        return (
            "optimizer_diagnostics ABSENT in solver_output.json "
            "(dxf_v1 pipeline runs the upstream Sparrow strip packer; native "
            "sparrow_cde diagnostics are asserted by the Rust integration suite)"
        )
    checks = {
        "pipeline_used": ("sparrow_cde", diag.get("pipeline_used")),
        "sparrow_invoked": (True, diag.get("sparrow_invoked")),
        "sparrow_native_model_active": (True, diag.get("sparrow_native_model_active")),
        "sparrow_native_tracker_active": (True, diag.get("sparrow_native_tracker_active")),
        "sparrow_old_core_used": (False, diag.get("sparrow_old_core_used")),
        "sparrow_compression_passes": (0, diag.get("sparrow_compression_passes")),
    }
    for key, (expected, actual) in checks.items():
        if actual != expected:
            raise SmokeError(
                f"native Sparrow diagnostics present but {key}={actual!r} != {expected!r}"
            )
    return "optimizer_diagnostics PRESENT and native Sparrow flags asserted"


def main() -> int:
    _require_ezdxf()
    normalized_dir = _resolve_normalized_dir()

    rows = _select_subset(normalized_dir)
    selected_rows = [r for r in rows if r["selected_quantity"] > 0]
    total = sum(r["selected_quantity"] for r in selected_rows)
    selected_area_m2 = sum(
        (r["area_m2"] or 0.0) * r["selected_quantity"] for r in selected_rows
    )
    _write_manifest(normalized_dir, rows, total, selected_area_m2)

    if not (MIN_INSTANCES <= total <= MAX_INSTANCES):
        raise SmokeError(
            f"deterministic subset total {total} outside [{MIN_INSTANCES}, {MAX_INSTANCES}]"
        )
    if len(selected_rows) < 5:
        raise SmokeError(
            f"subset must cover many LV8 part types (got {len(selected_rows)})"
        )
    # The [MIN_INSTANCES, MAX_INSTANCES] bound above already keeps this subset far
    # below any full-set / benchmark scale.

    time_limit_s = int(os.environ.get("Q26_LV8_TIME_LIMIT_S", str(DEFAULT_TIME_LIMIT_S)))

    with tempfile.TemporaryDirectory(prefix="q26_lv8_derived_smoke_") as tmp:
        tmp_dir = Path(tmp)
        stock_path = tmp_dir / "stock_1500x3000.dxf"
        _make_stock_dxf(stock_path)

        parts_dxf = [
            {
                "id": Path(r["file"]).stem,
                "path": r["path"],
                "quantity": r["selected_quantity"],
                "allowed_rotations_deg": [0, 90],
            }
            for r in selected_rows
        ]

        project = {
            "version": "dxf_v1",
            "name": "q26_lv8_derived_single_sheet_validation",
            "seed": SEED,
            "time_limit_s": time_limit_s,
            "units": "mm",
            "spacing_mm": SPACING_MM,
            "margin_mm": MARGIN_MM,
            "stocks_dxf": [
                {
                    "id": "stock_1500x3000",
                    "path": str(stock_path),
                    "quantity": 1,
                    "allowed_rotations_deg": [0],
                }
            ],
            "parts_dxf": parts_dxf,
        }
        project_path = tmp_dir / "project_dxf_v1.json"
        project_path.write_text(
            json.dumps(project, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

        run_root = tmp_dir / "runs"
        cmd = [
            sys.executable,
            str(ROOT / "scripts" / "run_real_dxf_sparrow_pipeline.py"),
            "--project",
            str(project_path),
            "--run-root",
            str(run_root),
        ]
        sparrow_bin = _resolve_sparrow_bin()
        if sparrow_bin:
            cmd.extend(["--sparrow-bin", sparrow_bin])

        proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            raise SmokeError(
                f"LV8-derived pipeline failed rc={proc.returncode}\nstderr={proc.stderr[-2000:]}"
            )

        stdout_lines = [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]
        if not stdout_lines:
            raise SmokeError("pipeline produced no run_dir on stdout")
        run_dir = Path(stdout_lines[-1]).resolve()
        if not run_dir.is_dir():
            raise SmokeError(f"invalid run_dir from stdout: {run_dir}")

        report = json.loads((run_dir / "report.json").read_text(encoding="utf-8"))
        solver_output = json.loads((run_dir / "solver_output.json").read_text(encoding="utf-8"))

        status = str(report.get("status"))
        if status != "ok":
            raise SmokeError(f"LV8-derived report status must be ok, got {status!r}")

        placements = solver_output.get("placements", [])
        placements_count = int(report["metrics"]["placements_count"])
        unplaced_count = int(report["metrics"]["unplaced_count"])
        if unplaced_count != 0:
            raise SmokeError(f"unplaced_count must be 0, got {unplaced_count}")
        if placements_count != total:
            raise SmokeError(
                f"placements_count {placements_count} != selected_instance_count {total}"
            )

        # Every placement on the first sheet (sheet_index 0).
        sheets_used = sorted({int(p.get("sheet_index", -1)) for p in placements})
        if sheets_used != [0]:
            raise SmokeError(f"all placements must be on sheet 0, got sheets {sheets_used}")

        # No second physical sheet artifact.
        out_dir = run_dir / "out"
        out_files = sorted(p.name for p in out_dir.iterdir())
        if "sheet_002.dxf" in out_files:
            raise SmokeError(f"second sheet artifact sheet_002.dxf produced: {out_files}")
        if "sheet_001.dxf" not in out_files:
            raise SmokeError(f"expected sheet_001.dxf in out dir, got {out_files}")

        diag_note = _assert_native_diagnostics_if_present(solver_output)

    print("[OK] SGH-Q26 LV8-derived single-sheet validation passed")
    print(f"  normalized_dir         : {normalized_dir}")
    print(f"  selected part types    : {len(selected_rows)}")
    print(f"  selected instances     : {total} (in [{MIN_INSTANCES}, {MAX_INSTANCES}])")
    print(f"  selected area          : {selected_area_m2:.4f} m^2 of {SHEET_W_MM*SHEET_H_MM/1e6:.2f} m^2 sheet")
    print(f"  sheet                  : {SHEET_W_MM:.0f} x {SHEET_H_MM:.0f} mm, quantity 1")
    print(f"  spacing_mm/margin_mm   : {SPACING_MM} / {MARGIN_MM}")
    print(f"  time_limit_s           : {time_limit_s}")
    print(f"  status                 : {status}")
    print(f"  placements_count       : {placements_count}")
    print(f"  unplaced_count         : {unplaced_count}")
    print(f"  out files              : {out_files}")
    print(f"  diagnostics            : {diag_note}")
    print(f"  manifest               : {MANIFEST_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SmokeError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        raise SystemExit(1)
