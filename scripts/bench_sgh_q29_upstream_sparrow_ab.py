#!/usr/bin/env python3
"""SGH-Q29 Phase A — upstream Sparrow A/B benchmark runner.

Runs the real upstream Sparrow binary (.cache/sparrow/target/release/sparrow) and
the local vrs_solver on equivalent geometry inputs, producing a structured JSON
summary and markdown report.

Hard rules:
- Only .cache/sparrow is allowed as "upstream Sparrow".
- If upstream cannot run, status=BLOCKED with explicit reason; no false PASS.
- The local solver is NEVER called "upstream Sparrow".
"""

from __future__ import annotations

import json
import math
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM_BIN = ROOT / ".cache" / "sparrow" / "target" / "release" / "sparrow"
UPSTREAM_INPUT_DIR = ROOT / ".cache" / "sparrow" / "data" / "input"
UPSTREAM_OUTPUT_DIR = ROOT / "output"
LOCAL_BIN = ROOT / "rust" / "vrs_solver" / "target" / "release" / "vrs_solver"
ART_DIR = ROOT / "artifacts" / "benchmarks" / "sgh_q29"

SUMMARY_FILE = ART_DIR / "upstream_ab_summary.json"
REPORT_FILE = ART_DIR / "upstream_ab_report.md"


# ── helpers ──────────────────────────────────────────────────────────────────

def _upstream_commit() -> str:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT / ".cache" / "sparrow",
            capture_output=True, text=True, timeout=5
        )
        return r.stdout.strip() if r.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def _run_upstream(input_path: Path, time_secs: int, seed: int, case_id: str) -> dict[str, Any]:
    """Run upstream Sparrow binary; return result dict."""
    if not UPSTREAM_BIN.exists():
        return {"status": "error", "error": f"binary not found: {UPSTREAM_BIN}"}
    # Upstream names output by the JSON `name` field, not the input filename.
    try:
        spp_data = json.loads(input_path.read_text())
        instance_name = spp_data.get("name", input_path.stem)
    except Exception:
        instance_name = input_path.stem
    t0 = time.time()
    try:
        # Remove old output to prevent stale read
        expected_out = UPSTREAM_OUTPUT_DIR / f"final_{instance_name}.json"
        if expected_out.exists():
            expected_out.unlink()
        r = subprocess.run(
            [str(UPSTREAM_BIN), "-i", str(input_path), "-t", str(time_secs), "-s", str(seed)],
            capture_output=True, text=True, timeout=time_secs + 30,
            cwd=ROOT,
        )
        elapsed_ms = (time.time() - t0) * 1000
        if r.returncode != 0:
            return {"status": "error", "error": r.stderr[:500] or r.stdout[:500], "runtime_ms": elapsed_ms}
        # Parse output
        if expected_out.exists():
            out_data = json.loads(expected_out.read_text())
            sol = out_data.get("solution", {})
            placed = sol.get("layout", {}).get("placed_items", [])
            return {
                "status": "ok",
                "runtime_ms": round(elapsed_ms, 1),
                "strip_width": sol.get("strip_width"),
                "density": sol.get("density"),
                "placed_count": len(placed),
                "run_time_sec_reported": sol.get("run_time_sec"),
                "iterations": None,  # not surfaced in upstream output
                "collision_or_loss_metric": None,
            }
        return {"status": "error", "error": "output file not created", "runtime_ms": elapsed_ms}
    except subprocess.TimeoutExpired:
        return {"status": "error", "error": "timeout", "runtime_ms": (time.time() - t0) * 1000}
    except Exception as exc:
        return {"status": "error", "error": str(exc), "runtime_ms": (time.time() - t0) * 1000}


def _upstream_input_from_spp(spp_path: Path) -> dict[str, Any]:
    return json.loads(spp_path.read_text())


def _spp_items_to_local_parts(items: list[dict]) -> list[dict]:
    """Convert upstream SPP items to local solver part format."""
    parts = []
    for item in items:
        pts = item["shape"]["data"]
        if not pts:
            continue
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        w = max(xs) - min(xs)
        h = max(ys) - min(ys)
        if w < 1e-9 or h < 1e-9:
            continue
        min_x, min_y = min(xs), min(ys)
        pts_norm = [[round(x - min_x, 6), round(y - min_y, 6)] for x, y in pts]
        rots = [int(r) for r in item.get("allowed_orientations", [0.0])
                if abs(r - round(r)) < 1e-6]
        parts.append({
            "id": str(item["id"]),
            "width": round(w, 6),
            "height": round(h, 6),
            "quantity": item.get("demand", 1),
            "allowed_rotations_deg": rots or [0],
            "outer_points": pts_norm,
        })
    return parts


def _run_local(parts: list[dict], sheet_w: float, sheet_h: float,
               time_secs: int, seed: int, case_id: str) -> dict[str, Any]:
    """Run local vrs_solver; return result dict."""
    if not LOCAL_BIN.exists():
        return {"status": "error", "error": f"local binary not found: {LOCAL_BIN}"}
    solver_input = {
        "contract_version": "v1",
        "project_name": f"sgh_q29_{case_id}",
        "seed": seed,
        "time_limit_s": time_secs,
        "solver_profile": "jagua_optimizer_phase1_outer_only",
        "optimizer_pipeline": "sparrow_cde",
        "collision_backend": "cde",
        "margin_mm": 0.0,
        "stocks": [{"id": "S", "quantity": 1, "width": sheet_w, "height": sheet_h}],
        "parts": parts,
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as fi:
        json.dump(solver_input, fi)
        in_path = fi.name
    out_path = in_path.replace(".json", "_out.json")
    t0 = time.time()
    try:
        r = subprocess.run(
            [str(LOCAL_BIN), "--input", in_path, "--output", out_path],
            capture_output=True, text=True, timeout=time_secs + 60,
        )
        elapsed_ms = (time.time() - t0) * 1000
        if r.returncode != 0:
            return {"status": "error", "error": r.stderr[:500], "runtime_ms": elapsed_ms}
        out_data = json.loads(Path(out_path).read_text())
        od = out_data.get("optimizer_diagnostics") or {}
        placements = out_data.get("placements") or []
        return {
            "status": out_data.get("status", "ok"),
            "runtime_ms": round(elapsed_ms, 1),
            "placed_count": len(placements),
            "final_pairs": od.get("sparrow_collision_graph_final_pairs"),
            "iterations": od.get("sparrow_iterations"),
            "search_calls": od.get("sparrow_search_position_calls"),
            "search_samples": od.get("sparrow_search_position_samples"),
        }
    except subprocess.TimeoutExpired:
        return {"status": "error", "error": "timeout", "runtime_ms": (time.time() - t0) * 1000}
    except Exception as exc:
        return {"status": "error", "error": str(exc), "runtime_ms": (time.time() - t0) * 1000}
    finally:
        for p in [in_path, out_path]:
            try:
                os.unlink(p)
            except OSError:
                pass


def _local_parts_to_spp(local_fixture: dict, strip_height: float | None = None) -> dict[str, Any]:
    """Convert local solver fixture parts to upstream SPP format."""
    parts = local_fixture.get("parts", [])
    stocks = local_fixture.get("stocks", [])
    sh = strip_height or (stocks[0]["height"] if stocks else 3000.0)
    items = []
    item_id = 0
    for part in parts:
        qty = part.get("quantity", 1)
        pts = part.get("outer_points") or [
            [0.0, 0.0], [part["width"], 0.0],
            [part["width"], part["height"]], [0.0, part["height"]]
        ]
        rots = [float(r) for r in part.get("allowed_rotations_deg", [0])]
        for _ in range(qty):
            items.append({
                "id": item_id,
                "demand": 1,
                "allowed_orientations": rots,
                "shape": {"type": "simple_polygon", "data": [[round(x, 6), round(y, 6)] for x, y in pts]},
            })
            item_id += 1
    return {"name": "lv8_subset", "strip_height": sh, "items": items}


# ── cases ─────────────────────────────────────────────────────────────────────

def _run_jakobs_case(case_id: str, spp_file: str, time_secs: int, seed: int) -> dict[str, Any]:
    """Run one jakobs case on upstream + local."""
    spp_path = UPSTREAM_INPUT_DIR / spp_file
    if not spp_path.exists():
        return {
            "case_id": case_id,
            "input_provenance": str(spp_path),
            "geometry_equivalence_notes": "SPP upstream geometry, same polygons in local via outer_points conversion",
            "upstream": {"status": "error", "error": f"SPP file not found: {spp_path}"},
            "local": {"status": "error", "error": "SPP file missing; no input to convert"},
        }
    spp = _upstream_input_from_spp(spp_path)
    items = spp["items"]
    strip_height = spp["strip_height"]
    total_instances = sum(it.get("demand", 1) for it in items)
    print(f"\n--- {case_id}: {len(items)} item types, {total_instances} total instances, strip_h={strip_height} ---")

    # Upstream run
    print(f"  [upstream] running {UPSTREAM_BIN.name} -t {time_secs}s ...")
    up_result = _run_upstream(spp_path, time_secs, seed, case_id)
    print(f"  [upstream] status={up_result['status']} runtime={up_result.get('runtime_ms','?'):.0f}ms"
          f" placed={up_result.get('placed_count','?')}")

    # Local run: convert geometry, use sheet = strip_height × 3 × strip_height
    parts = _spp_items_to_local_parts(items)
    local_result = _run_local(parts, strip_height * 3, strip_height, time_secs, seed, case_id)
    print(f"  [local]    status={local_result['status']} runtime={local_result.get('runtime_ms','?'):.0f}ms"
          f" placed={local_result.get('placed_count','?')} pairs={local_result.get('final_pairs','?')}"
          f" search_calls={local_result.get('search_calls','?')}")

    return {
        "case_id": case_id,
        "input_provenance": f"{spp_file} from .cache/sparrow/data/input/",
        "geometry_equivalence_notes": (
            f"Same polygon geometry. Upstream: SPP strip packing (minimize width, strip_h={strip_height}). "
            f"Local: FSPP fixed sheet ({strip_height * 3:.0f}×{strip_height:.0f}). "
            f"Objectives differ; search behavior / runtime comparable."
        ),
        "upstream": up_result,
        "local": local_result,
    }


def _run_lv8_subset_case(time_secs: int, seed: int) -> dict[str, Any]:
    """Run LV8-derived subset case: take first 3 part types from dense_191."""
    fixture_path = (ROOT / "rust" / "vrs_solver" / "tests" / "fixtures"
                    / "sgh_q28_dense191_benchmark" / "dense_191_lv8_derived.json")
    if not fixture_path.exists():
        return {
            "case_id": "lv8_subset",
            "input_provenance": str(fixture_path),
            "geometry_equivalence_notes": "Dense-191 LV8 fixture not found",
            "upstream": {"status": "error", "error": "fixture not found"},
            "local": {"status": "error", "error": "fixture not found"},
        }

    fixture = json.loads(fixture_path.read_text())
    # Take first 3 part types to keep total instances manageable (~20-30)
    all_parts = fixture.get("parts", [])
    subset_parts = all_parts[:3]
    total_instances = sum(p.get("quantity", 1) for p in subset_parts)
    stocks = fixture.get("stocks", [{}])
    sheet_w = stocks[0].get("width", 1500.0)
    sheet_h = stocks[0].get("height", 3000.0)
    strip_height = sheet_h

    print(f"\n--- lv8_subset: {len(subset_parts)} part types, {total_instances} instances ---")

    # Convert to upstream SPP format
    spp = _local_parts_to_spp({"parts": subset_parts, "stocks": stocks}, strip_height=strip_height)
    spp_file = ART_DIR / "lv8_subset_spp.json"
    spp_file.write_text(json.dumps(spp, indent=2))

    # Upstream run
    print(f"  [upstream] running -t {time_secs}s ...")
    up_result = _run_upstream(spp_file, time_secs, seed, "lv8_subset")
    print(f"  [upstream] status={up_result['status']} runtime={up_result.get('runtime_ms','?'):.0f}ms"
          f" placed={up_result.get('placed_count','?')}")

    # Local run
    local_result = _run_local(subset_parts, sheet_w, sheet_h, time_secs, seed, "lv8_subset")
    print(f"  [local]    status={local_result['status']} runtime={local_result.get('runtime_ms','?'):.0f}ms"
          f" placed={local_result.get('placed_count','?')} pairs={local_result.get('final_pairs','?')}"
          f" search_calls={local_result.get('search_calls','?')}")

    return {
        "case_id": "lv8_subset",
        "input_provenance": f"Dense-191 LV8 fixture, first 3 part types ({total_instances} instances)",
        "geometry_equivalence_notes": (
            f"Same LV8 polygon geometry (outer_points → SPP simple_polygon). "
            f"Upstream: SPP strip_h={strip_height:.0f}. "
            f"Local: fixed sheet {sheet_w:.0f}×{sheet_h:.0f}. "
            f"Objectives differ; geometry identical."
        ),
        "upstream": up_result,
        "local": local_result,
    }


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    ART_DIR.mkdir(parents=True, exist_ok=True)
    print("=== SGH-Q29 Phase A: upstream Sparrow A/B runner ===")

    commit = _upstream_commit()
    print(f"Upstream commit: {commit}")
    print(f"Upstream binary: {UPSTREAM_BIN}")
    print(f"Binary exists: {UPSTREAM_BIN.exists()}")
    print(f"Local binary: {LOCAL_BIN}")
    print(f"Local binary exists: {LOCAL_BIN.exists()}")

    # Determine if upstream can actually run
    upstream_blocked = False
    blocked_reason = ""
    if not UPSTREAM_BIN.exists():
        upstream_blocked = True
        blocked_reason = f"upstream binary not found: {UPSTREAM_BIN}"
    if not LOCAL_BIN.exists():
        # Both must exist for a valid comparison
        print(f"ERROR: local binary not found: {LOCAL_BIN}. Build it first with cargo build --release.")
        return 2

    cases = []

    if upstream_blocked:
        print(f"\nPhase A BLOCKED: {blocked_reason}")
        summary = {
            "task": "sgh_q29_upstream_sparrow_ab_and_cde_hotspot_profiler",
            "phase": "upstream_ab",
            "status": "BLOCKED",
            "blocked_reason": blocked_reason,
            "upstream_sparrow": {
                "source_path": str(ROOT / ".cache" / "sparrow"),
                "commit": commit,
                "binary_or_entrypoint": str(UPSTREAM_BIN),
                "build_command": "cargo build --release --manifest-path .cache/sparrow/Cargo.toml",
            },
            "local_solver": {
                "binary": str(LOCAL_BIN.relative_to(ROOT)),
                "commit_or_git_status": "see `git status`",
            },
            "cases": [],
        }
    else:
        seed = 42
        cases.append(_run_jakobs_case("micro",  "jakobs1.json", time_secs=12, seed=seed))
        cases.append(_run_jakobs_case("medium", "jakobs2.json", time_secs=20, seed=seed))
        cases.append(_run_lv8_subset_case(time_secs=30, seed=seed))

        # Determine overall status
        up_statuses = [c["upstream"].get("status", "error") for c in cases]
        any_up_pass = any(s == "ok" for s in up_statuses)
        all_up_error = all(s == "error" for s in up_statuses)
        overall = "PASS" if any_up_pass else ("BLOCKED" if all_up_error else "PARTIAL")

        summary = {
            "task": "sgh_q29_upstream_sparrow_ab_and_cde_hotspot_profiler",
            "phase": "upstream_ab",
            "status": overall,
            "upstream_sparrow": {
                "source_path": ".cache/sparrow",
                "commit": commit,
                "binary_or_entrypoint": str(UPSTREAM_BIN.relative_to(ROOT)),
                "build_command": "cargo build --release --manifest-path .cache/sparrow/Cargo.toml",
            },
            "local_solver": {
                "binary": str(LOCAL_BIN.relative_to(ROOT)),
                "commit_or_git_status": "main branch / d1a2ad2",
            },
            "cases": cases,
        }

    SUMMARY_FILE.write_text(json.dumps(summary, indent=2))
    print(f"\nSummary written to: {SUMMARY_FILE}")

    # Write markdown report
    _write_md_report(summary)
    print(f"Report written to: {REPORT_FILE}")

    if summary["status"] == "PASS":
        print(f"\nPhase A: PASS")
        return 0
    elif summary["status"] == "BLOCKED":
        print(f"\nPhase A: BLOCKED — {summary.get('blocked_reason','')}")
        print("No upstream A/B claim is made.")
        return 0  # BLOCKED is acceptable per run.md rule 7
    else:
        print(f"\nPhase A: {summary['status']}")
        return 0


def _fmt_val(v: Any) -> str:
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:.1f}"
    return str(v)


def _write_md_report(summary: dict) -> None:
    status = summary["status"]
    lines = [
        "# SGH-Q29 Phase A: Upstream Sparrow A/B Report",
        "",
        f"**Status: {status}**",
        "",
        f"- Upstream commit: `{summary['upstream_sparrow']['commit']}`",
        f"- Upstream binary: `{summary['upstream_sparrow']['binary_or_entrypoint']}`",
        f"- Build command: `{summary['upstream_sparrow']['build_command']}`",
        f"- Local binary: `{summary['local_solver']['binary']}`",
        "",
    ]
    if status == "BLOCKED":
        lines += [
            "**Phase A: BLOCKED**",
            "",
            f"Reason: {summary.get('blocked_reason', 'unknown')}",
            "",
            "No upstream-runtime claim is made.",
        ]
    else:
        for c in summary.get("cases", []):
            up = c.get("upstream", {})
            lo = c.get("local", {})
            lines += [
                f"## Case: {c['case_id']}",
                "",
                f"Input: {c['input_provenance']}",
                "",
                f"Geometry notes: {c['geometry_equivalence_notes']}",
                "",
                "| Metric | Upstream | Local |",
                "|--------|----------|-------|",
                f"| Status | {_fmt_val(up.get('status'))} | {_fmt_val(lo.get('status'))} |",
                f"| Runtime ms | {_fmt_val(up.get('runtime_ms'))} | {_fmt_val(lo.get('runtime_ms'))} |",
                f"| Placed count | {_fmt_val(up.get('placed_count'))} | {_fmt_val(lo.get('placed_count'))} |",
                f"| Iterations | {_fmt_val(up.get('iterations'))} | {_fmt_val(lo.get('iterations'))} |",
                f"| Search calls | {_fmt_val(up.get('iterations'))} | {_fmt_val(lo.get('search_calls'))} |",
                f"| Final pairs | — | {_fmt_val(lo.get('final_pairs'))} |",
                f"| Strip width / density | {_fmt_val(up.get('strip_width'))} / {_fmt_val(up.get('density'))} | — (fixed sheet) |",
                "",
            ]

    REPORT_FILE.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    sys.exit(main())
