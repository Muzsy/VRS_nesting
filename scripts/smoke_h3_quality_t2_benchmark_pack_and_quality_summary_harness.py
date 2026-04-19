#!/usr/bin/env python3
"""Offline smoke for H3 quality benchmark pack + quality summary harness."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import ezdxf  # type: ignore

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.gen_h3_quality_benchmark_fixtures import CASE_SPECS, generate_benchmark_fixtures  # noqa: E402
from scripts.smoke_trial_run_tool_cli_core import _FakeTransport  # noqa: E402
from scripts.trial_run_tool_core import TrialRunConfig, run_trial  # noqa: E402


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _entity_signature(entity: Any) -> tuple[Any, ...]:
    etype = entity.dxftype().upper()
    if etype == "LWPOLYLINE":
        points: list[tuple[float, float]] = []
        for item in entity.get_points():
            points.append((round(float(item[0]), 6), round(float(item[1]), 6)))
        closed = bool(entity.closed)
        return ("LWPOLYLINE", tuple(points), closed)
    if etype == "CIRCLE":
        center = entity.dxf.center
        return (
            "CIRCLE",
            round(float(center[0]), 6),
            round(float(center[1]), 6),
            round(float(entity.dxf.radius), 6),
        )
    raise RuntimeError(f"unsupported CUT_OUTER entity type in fixture: {etype}")


def _dxf_geometry_signature(path: Path) -> tuple[tuple[Any, ...], ...]:
    doc = ezdxf.readfile(path)
    signatures: list[tuple[Any, ...]] = []
    for entity in doc.modelspace():
        layer = str(getattr(entity.dxf, "layer", "")).strip().upper()
        if layer != "CUT_OUTER":
            continue
        signatures.append(_entity_signature(entity))
    return tuple(sorted(signatures))


def _collect_fixture_signatures(root: Path) -> dict[str, tuple[tuple[Any, ...], ...]]:
    out: dict[str, tuple[tuple[Any, ...], ...]] = {}
    for path in sorted(root.rglob("*.dxf")):
        rel = str(path.relative_to(root))
        out[rel] = _dxf_geometry_signature(path)
    return out


def _assert_generator_determinism() -> None:
    with TemporaryDirectory(prefix="h3_quality_gen_a_") as tmp_a, TemporaryDirectory(prefix="h3_quality_gen_b_") as tmp_b:
        out_a = Path(tmp_a) / "fixtures"
        out_b = Path(tmp_b) / "fixtures"
        generate_benchmark_fixtures(output_root=out_a)
        generate_benchmark_fixtures(output_root=out_b)

        sig_a = _collect_fixture_signatures(out_a)
        sig_b = _collect_fixture_signatures(out_b)
        if sig_a != sig_b:
            raise RuntimeError("benchmark fixture generator is not deterministic by geometry signature")

        expected_cases = sorted(CASE_SPECS.keys())
        generated_cases = sorted({item.split("/", 1)[0] for item in sig_a.keys()})
        if generated_cases != expected_cases:
            raise RuntimeError(f"generator case set mismatch: generated={generated_cases} expected={expected_cases}")


def _assert_manifest_schema() -> None:
    manifest_path = ROOT / "samples" / "trial_run_quality" / "benchmark_manifest_v1.json"
    payload = _load_json(manifest_path)
    if not isinstance(payload, dict):
        raise RuntimeError("benchmark manifest is not a JSON object")
    if payload.get("version") != "trial_run_quality_benchmark_manifest_v1":
        raise RuntimeError("benchmark manifest version mismatch")
    cases = payload.get("cases")
    if not isinstance(cases, list) or len(cases) < 3:
        raise RuntimeError("benchmark manifest must contain at least 3 cases")

    required = {"case_id", "fixture_kind", "sheet_width_mm", "sheet_height_mm", "default_qty", "qty_overrides", "notes", "expected_signals"}
    case_ids: list[str] = []
    for item in cases:
        if not isinstance(item, dict):
            raise RuntimeError("benchmark manifest case entry must be object")
        missing = sorted(required - set(item.keys()))
        if missing:
            raise RuntimeError(f"benchmark manifest case missing keys: {missing}")
        case_id = str(item.get("case_id", "")).strip()
        if not case_id:
            raise RuntimeError("manifest case_id must be non-empty")
        case_ids.append(case_id)
    if sorted(case_ids) != sorted(CASE_SPECS.keys()):
        raise RuntimeError(f"manifest case ids mismatch: {sorted(case_ids)}")


def _assert_quality_summary_schema() -> None:
    with TemporaryDirectory(prefix="h3_quality_summary_smoke_") as tmp:
        root = Path(tmp)
        dxf_dir = root / "dxf"
        out_dir = root / "runs"
        dxf_dir.mkdir(parents=True, exist_ok=True)
        (dxf_dir / "part_a.dxf").write_text("0\nEOF\n", encoding="utf-8")
        (dxf_dir / "part_b.dxf").write_text("0\nEOF\n", encoding="utf-8")

        cfg = TrialRunConfig(
            dxf_dir=dxf_dir,
            bearer_token="trial-secret-token-12345",
            token_source="argv",
            api_base_url="http://localhost:8000/v1",
            sheet_width=2000.0,
            sheet_height=1000.0,
            default_qty=2,
            per_file_qty={"part_b.dxf": 3},
            output_base_dir=out_dir,
            auto_start_platform=False,
            supabase_url="https://example.supabase.co",
            supabase_anon_key="anon-key",
            poll_interval_s=0.01,
            run_poll_timeout_s=2.0,
            geometry_poll_timeout_s=2.0,
        )
        result = run_trial(cfg, transport=_FakeTransport())
        if not result.success:
            raise RuntimeError(f"run_trial failed in quality summary smoke: {result.error_message}")

        quality_path = result.run_dir / "quality_summary.json"
        if not quality_path.is_file():
            raise RuntimeError("quality_summary.json missing after run_trial")
        quality = _load_json(quality_path)
        if not isinstance(quality, dict):
            raise RuntimeError("quality_summary.json is not a JSON object")

        required_keys = {
            "status",
            "run_id",
            "project_id",
            "engine_backend",
            "engine_contract_version",
            "engine_profile",
            "final_run_status",
            "placements_count",
            "unplaced_count",
            "sheets_used",
            "solver_utilization_pct",
            "sheet_width_mm",
            "sheet_height_mm",
            "unique_rotations_deg",
            "nonzero_rotation_count",
            "rotation_histogram",
            "occupied_extent_mm",
            "coverage_ratio_x",
            "coverage_ratio_y",
            "artifact_completeness",
            "artifact_presence",
            "signals",
        }
        missing = sorted(required_keys - set(quality.keys()))
        if missing:
            raise RuntimeError(f"quality_summary.json missing required keys: {missing}")
        artifact_presence = quality.get("artifact_presence")
        if not isinstance(artifact_presence, dict):
            raise RuntimeError("quality_summary.artifact_presence must be object")


def _assert_runner_plan_only() -> None:
    with TemporaryDirectory(prefix="h3_quality_plan_only_") as tmp:
        tmp_root = Path(tmp)
        output_json = tmp_root / "benchmark_plan.json"
        fixtures_root = tmp_root / "fixtures"

        cmd = [
            sys.executable,
            str(ROOT / "scripts" / "run_h3_quality_benchmark.py"),
            "--manifest",
            str(ROOT / "samples" / "trial_run_quality" / "benchmark_manifest_v1.json"),
            "--fixtures-root",
            str(fixtures_root),
            "--output",
            str(output_json),
            "--plan-only",
        ]
        proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            raise RuntimeError(
                "benchmark runner --plan-only failed\n"
                f"stdout:\n{proc.stdout}\n"
                f"stderr:\n{proc.stderr}"
            )
        payload = _load_json(output_json)
        if not isinstance(payload, dict):
            raise RuntimeError("benchmark plan output is not JSON object")
        if payload.get("plan_only") is not True:
            raise RuntimeError("benchmark plan output should mark plan_only=true")
        entries = payload.get("entries")
        if not isinstance(entries, list) or len(entries) != len(CASE_SPECS):
            raise RuntimeError("benchmark plan output has unexpected entries count")
        for entry in entries:
            if not isinstance(entry, dict):
                raise RuntimeError("benchmark plan entry must be object")
            for key in ("case_id", "fixture_kind", "run_dir", "success", "final_run_status", "quality_summary_path", "quality_summary", "notes"):
                if key not in entry:
                    raise RuntimeError(f"benchmark plan entry missing key: {key}")
            notes = entry.get("notes")
            if not isinstance(notes, dict):
                raise RuntimeError("benchmark plan notes must be object")
            dxf_files = notes.get("dxf_files")
            if not isinstance(dxf_files, list) or not dxf_files:
                raise RuntimeError("benchmark plan notes.dxf_files must be non-empty array")


def main() -> int:
    _assert_generator_determinism()
    _assert_manifest_schema()
    _assert_quality_summary_schema()
    _assert_runner_plan_only()
    print("PASS smoke_h3_quality_t2_benchmark_pack_and_quality_summary_harness")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
