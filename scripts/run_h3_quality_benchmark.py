#!/usr/bin/env python3
"""Run H3 quality benchmark cases from manifest (with optional plan-only mode)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.gen_h3_quality_benchmark_fixtures import generate_benchmark_fixtures
from scripts.trial_run_tool_core import TrialRunConfig, TrialRunToolError, run_trial


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _as_float(value: Any, *, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TrialRunToolError(f"manifest field '{field}' must be numeric")
    return float(value)


def _as_int(value: Any, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TrialRunToolError(f"manifest field '{field}' must be integer")
    return int(value)


def _as_str(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TrialRunToolError(f"manifest field '{field}' must be non-empty string")
    return value.strip()


def _validate_manifest(path: Path) -> dict[str, Any]:
    payload = _load_json(path)
    if not isinstance(payload, dict):
        raise TrialRunToolError("manifest must be a JSON object")

    version = _as_str(payload.get("version"), field="version")
    if version != "trial_run_quality_benchmark_manifest_v1":
        raise TrialRunToolError(f"unsupported manifest version: {version}")

    fixtures_root = _as_str(payload.get("fixtures_root"), field="fixtures_root")
    cases_raw = payload.get("cases")
    if not isinstance(cases_raw, list) or not cases_raw:
        raise TrialRunToolError("manifest.cases must be a non-empty array")

    case_ids: set[str] = set()
    validated_cases: list[dict[str, Any]] = []
    for index, row in enumerate(cases_raw):
        if not isinstance(row, dict):
            raise TrialRunToolError(f"manifest.cases[{index}] must be an object")
        case_id = _as_str(row.get("case_id"), field=f"cases[{index}].case_id")
        if case_id in case_ids:
            raise TrialRunToolError(f"duplicate case_id in manifest: {case_id}")
        case_ids.add(case_id)

        fixture_kind = _as_str(row.get("fixture_kind"), field=f"cases[{index}].fixture_kind")
        sheet_width = _as_float(row.get("sheet_width_mm"), field=f"cases[{index}].sheet_width_mm")
        sheet_height = _as_float(row.get("sheet_height_mm"), field=f"cases[{index}].sheet_height_mm")
        default_qty = _as_int(row.get("default_qty"), field=f"cases[{index}].default_qty")
        if default_qty <= 0:
            raise TrialRunToolError(f"manifest default_qty must be > 0 for case_id={case_id}")

        overrides_raw = row.get("qty_overrides", {})
        if not isinstance(overrides_raw, dict):
            raise TrialRunToolError(f"manifest qty_overrides must be object for case_id={case_id}")
        qty_overrides: dict[str, int] = {}
        for key, value in sorted(overrides_raw.items()):
            file_key = _as_str(key, field=f"cases[{index}].qty_overrides key")
            qty_value = _as_int(value, field=f"cases[{index}].qty_overrides[{file_key}]")
            if qty_value <= 0:
                raise TrialRunToolError(f"qty override must be > 0 for case_id={case_id} key={file_key}")
            qty_overrides[file_key] = qty_value

        expected_signals_raw = row.get("expected_signals", [])
        if not isinstance(expected_signals_raw, list):
            raise TrialRunToolError(f"expected_signals must be array for case_id={case_id}")
        expected_signals = [_as_str(item, field=f"cases[{index}].expected_signals[]") for item in expected_signals_raw]

        validated_cases.append(
            {
                "case_id": case_id,
                "fixture_kind": fixture_kind,
                "sheet_width_mm": sheet_width,
                "sheet_height_mm": sheet_height,
                "default_qty": default_qty,
                "qty_overrides": qty_overrides,
                "notes": str(row.get("notes", "")).strip(),
                "expected_signals": expected_signals,
            }
        )

    return {
        "version": version,
        "fixtures_root": fixtures_root,
        "cases": validated_cases,
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        default="samples/trial_run_quality/benchmark_manifest_v1.json",
        help="Benchmark manifest JSON",
    )
    parser.add_argument(
        "--fixtures-root",
        default=None,
        help="Fixture root directory (defaults to manifest.fixtures_root)",
    )
    parser.add_argument(
        "--output",
        default="runs/benchmarks/h3_quality_benchmark_v1.json",
        help="Merged benchmark output JSON",
    )
    parser.add_argument("--case", action="append", default=[], help="Run only selected case_id (repeatable)")
    parser.add_argument("--plan-only", action="store_true", help="Resolve and output case plan without live run execution")
    parser.add_argument("--api-base-url", default="http://127.0.0.1:8000/v1", help="API base URL")
    parser.add_argument("--token", default="", help="Bearer token (optional; env-based resolution also works)")
    parser.add_argument("--supabase-url", default=None, help="Supabase URL")
    parser.add_argument("--supabase-anon-key", default=None, help="Supabase anon key")
    parser.add_argument("--output-base-dir", default="tmp/runs/h3_quality_benchmark", help="Run evidence base dir")
    parser.add_argument("--poll-interval-s", type=float, default=1.0, help="Run poll interval")
    parser.add_argument("--run-poll-timeout-s", type=float, default=300.0, help="Run poll timeout")
    parser.add_argument("--geometry-poll-timeout-s", type=float, default=60.0, help="Geometry poll timeout")
    parser.add_argument("--request-timeout-s", type=float, default=30.0, help="HTTP timeout")
    parser.add_argument("--health-timeout-s", type=float, default=30.0, help="Health timeout")
    parser.add_argument(
        "--auto-start-platform",
        dest="auto_start_platform",
        action="store_true",
        default=True,
        help="Auto-heal platform when components are down",
    )
    parser.add_argument(
        "--no-auto-start-platform",
        dest="auto_start_platform",
        action="store_false",
        help="Disable auto-start for platform services",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    manifest_path = Path(str(args.manifest))
    if not manifest_path.is_absolute():
        manifest_path = (ROOT / manifest_path).resolve()
    if not manifest_path.is_file():
        raise TrialRunToolError(f"manifest not found: {manifest_path}")
    manifest = _validate_manifest(manifest_path)

    selected_cases = [str(item).strip() for item in args.case if str(item).strip()]
    all_cases = list(manifest["cases"])
    if selected_cases:
        selected_set = set(selected_cases)
        missing = sorted(selected_set - {str(item["case_id"]) for item in all_cases})
        if missing:
            raise TrialRunToolError(f"requested case ids missing from manifest: {', '.join(missing)}")
        cases = [item for item in all_cases if str(item["case_id"]) in selected_set]
    else:
        cases = all_cases
    if not cases:
        raise TrialRunToolError("no benchmark cases selected")

    manifest_fixture_root = Path(str(manifest["fixtures_root"]))
    fixtures_root = Path(str(args.fixtures_root)) if args.fixtures_root else manifest_fixture_root
    if not fixtures_root.is_absolute():
        fixtures_root = (ROOT / fixtures_root).resolve()

    generated = generate_benchmark_fixtures(
        output_root=fixtures_root,
        case_ids=[str(item["case_id"]) for item in cases],
    )
    generated_map: dict[str, dict[str, Any]] = {
        str(item.get("case_id", "")): item for item in generated.get("cases", []) if isinstance(item, dict)
    }

    output_path = Path(str(args.output))
    if not output_path.is_absolute():
        output_path = (ROOT / output_path).resolve()

    output_base_dir = Path(str(args.output_base_dir))
    if not output_base_dir.is_absolute():
        output_base_dir = (ROOT / output_base_dir).resolve()

    entries: list[dict[str, Any]] = []
    for case in cases:
        case_id = str(case["case_id"])
        fixture = generated_map.get(case_id)
        if not isinstance(fixture, dict):
            raise TrialRunToolError(f"fixture generation result missing case_id={case_id}")
        dxf_dir = Path(str(fixture.get("parts_dir", ""))).resolve()
        if not dxf_dir.is_dir():
            raise TrialRunToolError(f"fixture parts dir missing for case_id={case_id}: {dxf_dir}")

        dxf_files = sorted(path.name for path in dxf_dir.glob("*.dxf") if path.is_file())
        if not dxf_files:
            raise TrialRunToolError(f"fixture has no DXF parts for case_id={case_id}: {dxf_dir}")

        base_entry: dict[str, Any] = {
            "case_id": case_id,
            "fixture_kind": case["fixture_kind"],
            "run_dir": None,
            "success": None,
            "final_run_status": None,
            "quality_summary_path": None,
            "quality_summary": None,
            "notes": {
                "manifest_notes": case["notes"],
                "expected_signals": case["expected_signals"],
                "dxf_dir": str(dxf_dir),
                "dxf_files": dxf_files,
            },
        }

        if args.plan_only:
            base_entry["notes"]["plan_only"] = True
            entries.append(base_entry)
            continue

        config = TrialRunConfig(
            dxf_dir=dxf_dir,
            bearer_token=str(args.token).strip(),
            token_source=("argv" if str(args.token).strip() else "auto"),
            api_base_url=str(args.api_base_url),
            sheet_width=float(case["sheet_width_mm"]),
            sheet_height=float(case["sheet_height_mm"]),
            default_qty=int(case["default_qty"]),
            per_file_qty=dict(case["qty_overrides"]),
            output_base_dir=output_base_dir,
            auto_start_platform=bool(args.auto_start_platform),
            health_timeout_s=float(args.health_timeout_s),
            poll_interval_s=float(args.poll_interval_s),
            run_poll_timeout_s=float(args.run_poll_timeout_s),
            geometry_poll_timeout_s=float(args.geometry_poll_timeout_s),
            request_timeout_s=float(args.request_timeout_s),
            supabase_url=(str(args.supabase_url).strip() or None) if args.supabase_url else None,
            supabase_anon_key=(str(args.supabase_anon_key).strip() or None) if args.supabase_anon_key else None,
            project_name=f"H3 quality benchmark {case_id}",
            project_description=f"H3 quality benchmark case={case_id}",
        )
        try:
            result = run_trial(config)
            quality_summary_path = result.run_dir / "quality_summary.json"
            quality_summary: dict[str, Any] | None = None
            if quality_summary_path.is_file():
                loaded = _load_json(quality_summary_path)
                if isinstance(loaded, dict):
                    quality_summary = loaded
            base_entry.update(
                {
                    "run_dir": str(result.run_dir),
                    "success": bool(result.success),
                    "final_run_status": result.final_run_status,
                    "quality_summary_path": str(quality_summary_path) if quality_summary_path.is_file() else None,
                    "quality_summary": quality_summary,
                }
            )
            if result.error_message:
                base_entry["notes"]["error"] = result.error_message
        except Exception as exc:  # noqa: BLE001
            base_entry.update(
                {
                    "run_dir": None,
                    "success": False,
                    "final_run_status": "error",
                    "quality_summary_path": None,
                    "quality_summary": None,
                }
            )
            base_entry["notes"]["error"] = str(exc)

        entries.append(base_entry)

    payload = {
        "version": "h3_quality_benchmark_runner_v1",
        "generated_at_utc": _now_iso(),
        "manifest_path": str(manifest_path),
        "plan_only": bool(args.plan_only),
        "fixtures_root": str(fixtures_root),
        "entries": entries,
    }
    _write_json(output_path, payload)

    print(f"benchmark_cases={len(entries)}")
    print(f"plan_only={bool(args.plan_only)}")
    print(f"output={output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
