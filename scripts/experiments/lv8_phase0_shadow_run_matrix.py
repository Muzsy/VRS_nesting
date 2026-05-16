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

from vrs_nesting.config.nesting_quality_profiles import get_phase0_shadow_profile_pairs


@dataclass(frozen=True)
class FixtureSpec:
    family_id: str
    fixture_path: Path
    enabled: bool
    missing_reason: str | None = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def build_fixture_inventory(include_lv8_179: str) -> dict[str, Any]:
    lv8_276 = REPO_ROOT / "tests/fixtures/nesting_engine/ne2_input_lv8jav.json"
    lv8_179 = REPO_ROOT / "tmp/lv8_singlesheet_etalon_20260514/inputs/lv8_sheet1_179.json"
    sa_guard = REPO_ROOT / "poc/nesting_engine/f2_4_sa_quality_fixture_v2.json"
    contract_smoke = REPO_ROOT / "scripts/smoke_svg_export.py"
    contract_stock = REPO_ROOT / "samples/dxf_demo/stock_rect_1000x2000.dxf"
    contract_part = REPO_ROOT / "samples/dxf_demo/part_arc_spline_chaining_ok.dxf"

    lv8_179_enabled = lv8_179.is_file() if include_lv8_179 == "auto" else include_lv8_179 == "1"
    return {
        "checked_at_utc": _now_iso(),
        "fixtures": {
            "lv8_276": {"path": str(lv8_276.relative_to(REPO_ROOT)), "exists": lv8_276.is_file()},
            "lv8_179": {
                "path": str(lv8_179.relative_to(REPO_ROOT)),
                "exists": lv8_179.is_file(),
                "enabled_for_runs": lv8_179_enabled,
                "include_mode": include_lv8_179,
            },
            "sa_guard": {"path": str(sa_guard.relative_to(REPO_ROOT)), "exists": sa_guard.is_file()},
        },
        "contract_freeze_anchors": {
            "smoke_script": {"path": str(contract_smoke.relative_to(REPO_ROOT)), "exists": contract_smoke.is_file()},
            "stock_dxf": {"path": str(contract_stock.relative_to(REPO_ROOT)), "exists": contract_stock.is_file()},
            "part_dxf": {"path": str(contract_part.relative_to(REPO_ROOT)), "exists": contract_part.is_file()},
        },
        "phase0_shadow_pairs": get_phase0_shadow_profile_pairs(),
    }


def eval_pair(legacy: dict[str, Any], shadow: dict[str, Any]) -> dict[str, Any]:
    legacy_placed = int(legacy.get("placed_instances") or 0)
    shadow_placed = int(shadow.get("placed_instances") or 0)
    legacy_poly = legacy.get("valid_polygon_gate") is True
    shadow_poly = shadow.get("valid_polygon_gate") is True
    legacy_timeout = legacy.get("timed_out") is True
    shadow_timeout = shadow.get("timed_out") is True
    legacy_rc = int(legacy.get("return_code") if legacy.get("return_code") is not None else 9999)
    shadow_rc = int(shadow.get("return_code") if shadow.get("return_code") is not None else 9999)
    legacy_util = _safe_float(legacy.get("utilization_pct"))
    shadow_util = _safe_float(shadow.get("utilization_pct"))

    util_ok = True
    if legacy_util is not None and shadow_util is not None:
        util_ok = shadow_util >= legacy_util

    pair_pass = (
        shadow_placed >= legacy_placed
        and util_ok
        and (int(shadow_poly) >= int(legacy_poly))
        and (int(shadow_timeout) <= int(legacy_timeout))
        and shadow_rc <= legacy_rc
    )

    return {
        "pair_pass": pair_pass,
        "legacy_failed_or_timeout": legacy_timeout or legacy_rc != 0,
        "checks": {
            "placed_ok": shadow_placed >= legacy_placed,
            "util_ok": util_ok,
            "polygon_gate_not_worse": int(shadow_poly) >= int(legacy_poly),
            "timeout_not_worse": int(shadow_timeout) <= int(legacy_timeout),
            "return_code_not_worse": shadow_rc <= legacy_rc,
        },
    }


def decide_hard_cut(matrix_rows: list[dict[str, Any]]) -> dict[str, Any]:
    if any(r.get("row_type") == "fixture_missing" and r.get("family_id") == "lv8_179" for r in matrix_rows):
        return {
            "hard_cut_decision": "DEFER_HARD_CUT",
            "reason": "lv8_179 fixture missing or disabled",
        }
    engine_pairs = [r for r in matrix_rows if r.get("row_type") == "engine_pair"]
    if not engine_pairs:
        return {"hard_cut_decision": "BLOCKED", "reason": "no_engine_pair_rows"}
    if all(r.get("pair_pass") is True for r in engine_pairs):
        return {"hard_cut_decision": "APPROVE_NO_SA_HARD_CUT", "reason": "all_engine_pairs_passed"}
    return {"hard_cut_decision": "DEFER_HARD_CUT", "reason": "at_least_one_engine_pair_failed"}


def _run_engine_harness(
    fixture: Path,
    quality_profile: str,
    out_dir: Path,
    time_limit_sec: int,
    seed: int,
    label: str,
) -> tuple[dict[str, Any], int, str]:
    summary_path = out_dir / "summary.json"
    if summary_path.is_file():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        return summary, int(summary.get("return_code") or 0), ""

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
            "stderr_preview": proc.stderr[-2000:],
            "stdout_preview": proc.stdout[-2000:],
        }
    return summary, proc.returncode, proc.stderr


def _run_contract_freeze_smoke() -> dict[str, Any]:
    cmd = [sys.executable, str(REPO_ROOT / "scripts/smoke_svg_export.py")]
    proc = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True, check=False)
    return {
        "row_type": "contract_freeze_regression",
        "family_id": "web_platform_contract_freeze",
        "shadow_profile_applicability": "not_applicable",
        "regression_gate": "PASS" if proc.returncode == 0 else "FAIL",
        "return_code": proc.returncode,
    }


def _matrix_md(rows: list[dict[str, Any]], decision: dict[str, Any]) -> str:
    lines = [
        "# LV8 Phase0 Shadow Matrix",
        "",
        f"- generated_at_utc: { _now_iso() }",
        f"- hard_cut_decision: {decision.get('hard_cut_decision')}",
        f"- reason: {decision.get('reason')}",
        "",
        "| row_type | family_id | legacy_profile | shadow_profile | pair_pass | valid |",
        "|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row.get('row_type','')} | {row.get('family_id','')} | {row.get('legacy_profile','')} | "
            f"{row.get('shadow_profile','')} | {row.get('pair_pass','')} | {row.get('valid','')} |"
        )
    return "\n".join(lines) + "\n"


def run_matrix(
    out_root: Path,
    time_limit_sec: int,
    seed: int,
    include_lv8_179: str,
    run_contract_freeze_smoke: bool,
) -> dict[str, Any]:
    out_root.mkdir(parents=True, exist_ok=True)
    inventory = build_fixture_inventory(include_lv8_179=include_lv8_179)
    (out_root / "fixture_profile_inventory.json").write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    pairs = get_phase0_shadow_profile_pairs()
    fixtures: list[FixtureSpec] = []
    lv8_276 = REPO_ROOT / "tests/fixtures/nesting_engine/ne2_input_lv8jav.json"
    sa_guard = REPO_ROOT / "poc/nesting_engine/f2_4_sa_quality_fixture_v2.json"
    lv8_179 = REPO_ROOT / "tmp/lv8_singlesheet_etalon_20260514/inputs/lv8_sheet1_179.json"
    fixtures.append(FixtureSpec("lv8_276", lv8_276, lv8_276.is_file(), "missing_fixture"))
    fixtures.append(FixtureSpec("sa_guard", sa_guard, sa_guard.is_file(), "missing_fixture"))
    lv8_179_enabled = inventory["fixtures"]["lv8_179"]["enabled_for_runs"] is True
    fixtures.append(FixtureSpec("lv8_179", lv8_179, lv8_179_enabled and lv8_179.is_file(), "fixture_missing"))

    runs_rows: list[dict[str, Any]] = []
    for fx in fixtures:
        if not fx.enabled:
            runs_rows.append(
                {
                    "row_type": "fixture_missing",
                    "family_id": fx.family_id,
                    "fixture_path": str(fx.fixture_path.relative_to(REPO_ROOT)),
                    "status": fx.missing_reason or "missing",
                }
            )
            continue
        for legacy_profile, shadow_profile in pairs.items():
            family_dir = out_root / fx.family_id
            legacy_dir = family_dir / f"{legacy_profile}__legacy"
            shadow_dir = family_dir / f"{shadow_profile}__shadow"
            legacy_summary, _, _ = _run_engine_harness(
                fixture=fx.fixture_path,
                quality_profile=legacy_profile,
                out_dir=legacy_dir,
                time_limit_sec=time_limit_sec,
                seed=seed,
                label=f"{fx.family_id}:{legacy_profile}",
            )
            shadow_summary, _, _ = _run_engine_harness(
                fixture=fx.fixture_path,
                quality_profile=shadow_profile,
                out_dir=shadow_dir,
                time_limit_sec=time_limit_sec,
                seed=seed,
                label=f"{fx.family_id}:{shadow_profile}",
            )
            pair_eval = eval_pair(legacy_summary, shadow_summary)
            row = {
                "row_type": "engine_pair",
                "family_id": fx.family_id,
                "fixture_path": str(fx.fixture_path.relative_to(REPO_ROOT)),
                "legacy_profile": legacy_profile,
                "shadow_profile": shadow_profile,
                "legacy_summary_path": str((legacy_dir / "summary.json").relative_to(REPO_ROOT)),
                "shadow_summary_path": str((shadow_dir / "summary.json").relative_to(REPO_ROOT)),
                "legacy_valid": legacy_summary.get("valid"),
                "shadow_valid": shadow_summary.get("valid"),
                "legacy": legacy_summary,
                "shadow": shadow_summary,
            }
            row.update(pair_eval)
            runs_rows.append(row)

    if run_contract_freeze_smoke:
        runs_rows.append(_run_contract_freeze_smoke())

    runs_jsonl_path = out_root / "runs.jsonl"
    with runs_jsonl_path.open("w", encoding="utf-8") as f:
        for row in runs_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    decision = decide_hard_cut(runs_rows)
    (out_root / "hard_cut_decision.json").write_text(
        json.dumps(decision, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    matrix = {
        "generated_at_utc": _now_iso(),
        "phase0_shadow_pairs": pairs,
        "rows": runs_rows,
        "hard_cut_decision": decision,
    }
    (out_root / "phase0_shadow_matrix.json").write_text(
        json.dumps(matrix, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_root / "phase0_shadow_matrix.md").write_text(
        _matrix_md(runs_rows, decision), encoding="utf-8"
    )
    return matrix


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--time-limit-sec", type=int, default=600)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--include-lv8-179", choices=["auto", "0", "1"], default="auto")
    parser.add_argument("--run-contract-freeze-smoke", type=int, choices=[0, 1], default=1)
    args = parser.parse_args(argv)

    out_root = Path(args.out_root)
    if not out_root.is_absolute():
        out_root = (REPO_ROOT / out_root).resolve()

    matrix = run_matrix(
        out_root=out_root,
        time_limit_sec=args.time_limit_sec,
        seed=args.seed,
        include_lv8_179=args.include_lv8_179,
        run_contract_freeze_smoke=bool(args.run_contract_freeze_smoke),
    )
    print(json.dumps({"rows": len(matrix["rows"]), "decision": matrix["hard_cut_decision"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
