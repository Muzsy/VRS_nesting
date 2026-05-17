#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DEFAULT_PROFILES = ["quality_default_no_sa_shadow", "quality_aggressive_no_sa_shadow"]


@dataclass(frozen=True)
class FixtureSpec:
    family_id: str
    fixture_path: Path
    required: bool
    enabled: bool
    missing_reason: str | None = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_profiles(raw: str) -> list[str]:
    items = [part.strip() for part in str(raw or "").split(",")]
    return [item for item in items if item]


def _safe_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _cache_hit_rate(hits: int | None, misses: int | None) -> float | None:
    if hits is None or misses is None:
        return None
    total = hits + misses
    if total <= 0:
        return None
    return hits / total


def build_fixture_specs(include_lv8_179: str) -> list[FixtureSpec]:
    lv8_276 = REPO_ROOT / "tests/fixtures/nesting_engine/ne2_input_lv8jav.json"
    sa_guard = REPO_ROOT / "poc/nesting_engine/f2_4_sa_quality_fixture_v2.json"
    lv8_179 = REPO_ROOT / "tmp/lv8_singlesheet_etalon_20260514/inputs/lv8_sheet1_179.json"

    if include_lv8_179 == "1":
        lv8_179_enabled = True
        lv8_179_missing_reason = "fixture_missing"
    elif include_lv8_179 == "0":
        lv8_179_enabled = False
        lv8_179_missing_reason = "disabled_by_flag"
    else:
        lv8_179_enabled = lv8_179.is_file()
        lv8_179_missing_reason = "fixture_missing"

    return [
        FixtureSpec("lv8_276", lv8_276, required=True, enabled=lv8_276.is_file(), missing_reason="missing_fixture"),
        FixtureSpec("sa_guard", sa_guard, required=True, enabled=sa_guard.is_file(), missing_reason="missing_fixture"),
        FixtureSpec(
            "lv8_179",
            lv8_179,
            required=False,
            enabled=lv8_179_enabled and lv8_179.is_file(),
            missing_reason=lv8_179_missing_reason,
        ),
    ]


def build_fixture_inventory(include_lv8_179: str, profiles: list[str]) -> dict[str, Any]:
    specs = build_fixture_specs(include_lv8_179)
    return {
        "checked_at_utc": _now_iso(),
        "include_lv8_179": include_lv8_179,
        "profiles": profiles,
        "fixtures": {
            spec.family_id: {
                "path": str(spec.fixture_path.relative_to(REPO_ROOT)),
                "exists": spec.fixture_path.is_file(),
                "required": spec.required,
                "enabled": spec.enabled,
                "missing_reason": spec.missing_reason,
            }
            for spec in specs
        },
    }


def _run_harness(
    fixture: Path,
    out_dir: Path,
    quality_profile: str,
    time_limit_sec: int,
    seed: int,
    label: str,
) -> tuple[dict[str, Any], int]:
    summary_path = out_dir / "summary.json"
    if summary_path.is_file():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        return summary, int(summary.get("return_code") or 0)

    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts/experiments/lv8_2sheet_claude_search.py"),
        "--fixture",
        str(fixture),
        "--out-dir",
        str(out_dir),
        "--quality-profile",
        quality_profile,
        "--time-limit-sec",
        str(time_limit_sec),
        "--seed",
        str(seed),
        "--label",
        label,
    ]
    proc = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True, check=False)
    if summary_path.is_file():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    else:
        summary = {
            "label": label,
            "quality_profile": quality_profile,
            "fixture_path": str(fixture.relative_to(REPO_ROOT)),
            "return_code": proc.returncode,
            "timed_out": False,
            "valid": False,
            "engine_stats": {
                "available": False,
                "source": "NEST_NFP_STATS_V1",
                "parse_error": "summary_missing",
                "raw": None,
                "normalized": None,
            },
        }
    return summary, int(proc.returncode)


def _row_from_summary(family_id: str, fixture_path: Path, quality_profile: str, summary: dict[str, Any]) -> dict[str, Any]:
    engine_stats = summary.get("engine_stats") or {}
    normalized = engine_stats.get("normalized") or {}
    hit_count = _safe_int(normalized.get("nfp_cache_hit_count"))
    miss_count = _safe_int(normalized.get("nfp_cache_miss_count"))
    entries_end = _safe_int(normalized.get("nfp_cache_entries_end"))
    clear_all_events = _safe_int(normalized.get("nfp_cache_clear_all_events"))
    peak_entries = _safe_int(normalized.get("nfp_cache_peak_entries"))
    compute_count = _safe_int(normalized.get("nfp_compute_count"))

    total_lookups = None
    if hit_count is not None and miss_count is not None:
        total_lookups = hit_count + miss_count

    return {
        "row_type": "engine_run",
        "family_id": family_id,
        "fixture_path": str(fixture_path.relative_to(REPO_ROOT)),
        "quality_profile": quality_profile,
        "summary_path": summary.get("out_dir", "") + "/summary.json" if summary.get("out_dir") else None,
        "engine_stats_available": engine_stats.get("available") is True,
        "nfp_cache_hit_count": hit_count,
        "nfp_cache_miss_count": miss_count,
        "nfp_cache_entries_end": entries_end,
        "nfp_cache_clear_all_events": clear_all_events,
        "nfp_cache_peak_entries": peak_entries,
        "nfp_compute_count": compute_count,
        "cache_total_lookups": total_lookups,
        "cache_hit_rate": _cache_hit_rate(hit_count, miss_count),
        "valid_polygon_gate": summary.get("valid_polygon_gate"),
        "valid_quantity_gate": summary.get("valid_quantity_gate"),
        "valid": summary.get("valid"),
        "placed_instances": _safe_int(summary.get("placed_instances")),
        "utilization_pct": _safe_float(summary.get("utilization_pct")),
        "runtime_sec": _safe_float(summary.get("runtime_sec")),
        "return_code": _safe_int(summary.get("return_code")),
        "timed_out": summary.get("timed_out") is True,
    }


def compute_decision(rows: list[dict[str, Any]], required_families: set[str], blocked_reason: str | None) -> dict[str, Any]:
    required_rows = [
        r
        for r in rows
        if r.get("row_type") == "engine_run" and str(r.get("family_id")) in required_families
    ]
    cache_stats_available_all_required_runs = all(r.get("engine_stats_available") is True for r in required_rows)
    polygon_gate_available_all_required_runs = all(r.get("valid_polygon_gate") is True for r in required_rows)
    lru_followup_required = any((_safe_int(r.get("nfp_cache_clear_all_events")) or 0) > 0 for r in required_rows)

    blocking_conditions = [
        blocked_reason is not None,
        not required_rows,
        not cache_stats_available_all_required_runs,
        not polygon_gate_available_all_required_runs,
    ]
    phase2a_ready = not any(blocking_conditions) and not lru_followup_required

    return {
        "phase2a_ready": phase2a_ready,
        "lru_followup_required": lru_followup_required,
        "cache_stats_available_all_required_runs": cache_stats_available_all_required_runs,
        "polygon_gate_available_all_required_runs": polygon_gate_available_all_required_runs,
        "required_run_count": len(required_rows),
        "blocked_reason": blocked_reason,
    }


def _matrix_md(rows: list[dict[str, Any]], decision: dict[str, Any]) -> str:
    lines = [
        "# LV8 Phase1 Cache Usage Matrix",
        "",
        f"- generated_at_utc: {_now_iso()}",
        f"- phase2a_ready: {decision.get('phase2a_ready')}",
        f"- lru_followup_required: {decision.get('lru_followup_required')}",
        f"- cache_stats_available_all_required_runs: {decision.get('cache_stats_available_all_required_runs')}",
        f"- polygon_gate_available_all_required_runs: {decision.get('polygon_gate_available_all_required_runs')}",
        f"- blocked_reason: {decision.get('blocked_reason')}",
        "",
        "| row_type | family_id | quality_profile | engine_stats_available | hit_rate | clear_all_events | valid_polygon_gate | valid |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row.get('row_type','')} | {row.get('family_id','')} | {row.get('quality_profile','')} | "
            f"{row.get('engine_stats_available','')} | {row.get('cache_hit_rate','')} | "
            f"{row.get('nfp_cache_clear_all_events','')} | {row.get('valid_polygon_gate','')} | {row.get('valid','')} |"
        )
    return "\n".join(lines) + "\n"


def run_matrix(
    out_root: Path,
    time_limit_sec: int,
    seed: int,
    include_lv8_179: str,
    profiles: list[str],
) -> tuple[dict[str, Any], int]:
    out_root.mkdir(parents=True, exist_ok=True)

    specs = build_fixture_specs(include_lv8_179)
    required_families = {spec.family_id for spec in specs if spec.required}
    rows: list[dict[str, Any]] = []

    blocked_reason: str | None = None
    for spec in specs:
        if spec.required and not spec.enabled:
            blocked_reason = f"required_fixture_missing:{spec.family_id}"
        if not spec.enabled:
            rows.append(
                {
                    "row_type": "fixture_missing",
                    "family_id": spec.family_id,
                    "fixture_path": str(spec.fixture_path.relative_to(REPO_ROOT)),
                    "status": spec.missing_reason or "missing",
                    "quality_profile": None,
                }
            )

    if blocked_reason is None:
        for spec in specs:
            if not spec.enabled:
                continue
            for profile in profiles:
                run_dir = out_root / spec.family_id / profile
                summary, return_code = _run_harness(
                    fixture=spec.fixture_path,
                    out_dir=run_dir,
                    quality_profile=profile,
                    time_limit_sec=time_limit_sec,
                    seed=seed,
                    label=f"{spec.family_id}:{profile}",
                )
                row = _row_from_summary(spec.family_id, spec.fixture_path, profile, summary)
                row["return_code"] = return_code if row.get("return_code") is None else row.get("return_code")
                rows.append(row)

    decision = compute_decision(rows, required_families=required_families, blocked_reason=blocked_reason)

    matrix = {
        "generated_at_utc": _now_iso(),
        "include_lv8_179": include_lv8_179,
        "profiles": profiles,
        "fixture_inventory": build_fixture_inventory(include_lv8_179, profiles),
        "rows": rows,
        **decision,
    }

    runs_jsonl = out_root / "runs.jsonl"
    with runs_jsonl.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    (out_root / "cache_usage_matrix.json").write_text(
        json.dumps(matrix, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (out_root / "cache_usage_matrix.md").write_text(_matrix_md(rows, decision), encoding="utf-8")

    if blocked_reason is not None:
        return matrix, 2
    if decision["cache_stats_available_all_required_runs"] is not True:
        return matrix, 3
    return matrix, 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--time-limit-sec", type=int, default=60)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--include-lv8-179", choices=["auto", "0", "1"], default="auto")
    parser.add_argument("--profiles", default=",".join(DEFAULT_PROFILES))
    args = parser.parse_args(argv)

    out_root = Path(args.out_root)
    if not out_root.is_absolute():
        out_root = (REPO_ROOT / out_root).resolve()

    profiles = parse_profiles(args.profiles)
    if not profiles:
        profiles = list(DEFAULT_PROFILES)

    matrix, exit_code = run_matrix(
        out_root=out_root,
        time_limit_sec=args.time_limit_sec,
        seed=args.seed,
        include_lv8_179=args.include_lv8_179,
        profiles=profiles,
    )

    summary = {
        "rows": len(matrix.get("rows") or []),
        "phase2a_ready": matrix.get("phase2a_ready"),
        "lru_followup_required": matrix.get("lru_followup_required"),
        "cache_stats_available_all_required_runs": matrix.get("cache_stats_available_all_required_runs"),
        "polygon_gate_available_all_required_runs": matrix.get("polygon_gate_available_all_required_runs"),
        "blocked_reason": matrix.get("blocked_reason"),
        "exit_code": exit_code,
    }
    print(json.dumps(summary, ensure_ascii=False))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
