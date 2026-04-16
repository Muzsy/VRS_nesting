#!/usr/bin/env python3
"""NFP placer deterministic stats + counter-based perf gate smoke."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STAT_PREFIX = "NEST_NFP_STATS_V1 "
BASELINE_VERSION = "nfp_perf_gate_v1"

DEFAULT_FIXTURES: list[dict[str, str]] = [
    {
        "id": "f0_sanity",
        "path": "poc/nesting_engine/f2_3_f0_sanity_noholes_v2.json",
    },
    {
        "id": "f4_cfr_order",
        "path": "poc/nesting_engine/f2_3_f4_cfr_order_hardening_noholes_v2.json",
    },
]

COUNTER_KEYS: list[str] = [
    "nfp_cache_hits",
    "nfp_cache_misses",
    "nfp_cache_entries_end",
    "nfp_compute_calls",
    "cfr_calls",
    "cfr_union_calls",
    "cfr_diff_calls",
    "candidates_before_dedupe_total",
    "candidates_after_dedupe_total",
    "candidates_after_cap_total",
    "cap_applied_count",
    "sheets_used",
]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _fixture_list_for_record(baseline_path: Path) -> list[dict[str, str]]:
    if baseline_path.is_file():
        payload = _read_json(baseline_path)
        fixtures_raw = payload.get("fixtures")
        if isinstance(fixtures_raw, list):
            fixtures: list[dict[str, str]] = []
            for item in fixtures_raw:
                if not isinstance(item, dict):
                    raise AssertionError(f"invalid fixture entry in baseline: {item!r}")
                fid = str(item.get("id", "")).strip()
                fpath = str(item.get("path", "")).strip()
                if not fid or not fpath:
                    raise AssertionError(f"fixture id/path missing in baseline entry: {item!r}")
                fixtures.append({"id": fid, "path": fpath})
            if fixtures:
                return fixtures
    return list(DEFAULT_FIXTURES)


def _fixtures_for_check(baseline_path: Path) -> list[dict[str, Any]]:
    if not baseline_path.is_file():
        raise AssertionError(f"missing baseline: {baseline_path}")

    payload = _read_json(baseline_path)
    version = str(payload.get("version", "")).strip()
    if version != BASELINE_VERSION:
        raise AssertionError(
            f"unsupported baseline version '{version}', expected '{BASELINE_VERSION}'"
        )

    fixtures_raw = payload.get("fixtures")
    if not isinstance(fixtures_raw, list) or not fixtures_raw:
        raise AssertionError("baseline fixtures must be a non-empty list")

    fixtures: list[dict[str, Any]] = []
    for item in fixtures_raw:
        if not isinstance(item, dict):
            raise AssertionError(f"invalid fixture entry in baseline: {item!r}")
        fid = str(item.get("id", "")).strip()
        fpath = str(item.get("path", "")).strip()
        max_map = item.get("max")
        if not fid or not fpath:
            raise AssertionError(f"fixture id/path missing in baseline entry: {item!r}")
        if not isinstance(max_map, dict):
            raise AssertionError(f"fixture max map missing for '{fid}'")

        missing = [k for k in COUNTER_KEYS if k not in max_map]
        if missing:
            raise AssertionError(f"fixture '{fid}' missing counter limits: {', '.join(missing)}")

        for key in COUNTER_KEYS:
            value = max_map.get(key)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise AssertionError(
                    f"fixture '{fid}' has invalid max['{key}'] value: {value!r}"
                )

        fixtures.append({"id": fid, "path": fpath, "max": max_map})

    return fixtures


def _parse_stats_line(stderr_text: str, fixture_id: str) -> dict[str, Any]:
    matches = [line for line in stderr_text.splitlines() if line.startswith(STAT_PREFIX)]
    if len(matches) != 1:
        raise AssertionError(
            f"fixture '{fixture_id}' expected exactly 1 stats line, got {len(matches)}"
        )

    payload = matches[0][len(STAT_PREFIX) :].strip()
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"fixture '{fixture_id}' emitted invalid stats JSON: {exc}") from exc

    if not isinstance(parsed, dict):
        raise AssertionError(f"fixture '{fixture_id}' stats payload must be an object")
    return parsed


def _normalize_and_validate_stats(stats: dict[str, Any], fixture_id: str) -> dict[str, Any]:
    normalized: dict[str, Any] = {}

    for key in COUNTER_KEYS:
        value = stats.get(key)
        if isinstance(value, bool) or not isinstance(value, int):
            raise AssertionError(
                f"fixture '{fixture_id}' stats['{key}'] must be integer, got {value!r}"
            )
        if value < 0:
            raise AssertionError(
                f"fixture '{fixture_id}' stats['{key}'] must be >= 0, got {value}"
            )
        normalized[key] = int(value)

    effective_placer = str(stats.get("effective_placer", "")).strip()
    if effective_placer not in {"nfp", "blf"}:
        raise AssertionError(
            f"fixture '{fixture_id}' invalid effective_placer: {effective_placer!r}"
        )
    if effective_placer != "nfp":
        raise AssertionError(
            f"fixture '{fixture_id}' expected effective_placer='nfp', got {effective_placer!r}"
        )
    normalized["effective_placer"] = effective_placer

    if normalized["candidates_after_dedupe_total"] > normalized["candidates_before_dedupe_total"]:
        raise AssertionError(
            f"fixture '{fixture_id}' invalid candidate monotonicity: after_dedupe > before_dedupe"
        )
    if normalized["candidates_after_cap_total"] > normalized["candidates_after_dedupe_total"]:
        raise AssertionError(
            f"fixture '{fixture_id}' invalid candidate monotonicity: after_cap > after_dedupe"
        )

    return normalized


def _run_fixture_once(bin_path: Path, fixture_id: str, fixture_path: Path) -> dict[str, Any]:
    if not fixture_path.is_file():
        raise AssertionError(f"fixture '{fixture_id}' missing file: {fixture_path}")

    cmd = [str(bin_path), "nest", "--placer", "nfp"]
    env = dict(os.environ)
    env["NESTING_ENGINE_EMIT_NFP_STATS"] = "1"

    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        input=fixture_path.read_bytes(),
        capture_output=True,
        check=False,
        env=env,
    )

    if proc.returncode != 0:
        stderr_text = proc.stderr.decode("utf-8", errors="replace")
        raise AssertionError(
            f"fixture '{fixture_id}' run failed (rc={proc.returncode})\n"
            f"cmd={' '.join(cmd)}\n"
            f"stderr:\n{stderr_text}"
        )

    stderr_text = proc.stderr.decode("utf-8", errors="replace")
    stats = _parse_stats_line(stderr_text, fixture_id)
    return _normalize_and_validate_stats(stats, fixture_id)


def _measure_fixture(bin_path: Path, fixture_id: str, fixture_path: Path) -> dict[str, Any]:
    first = _run_fixture_once(bin_path, fixture_id, fixture_path)
    second = _run_fixture_once(bin_path, fixture_id, fixture_path)

    if first != second:
        raise AssertionError(
            f"fixture '{fixture_id}' stats are non-deterministic across repeated runs\n"
            f"run_a={json.dumps(first, ensure_ascii=False, sort_keys=True)}\n"
            f"run_b={json.dumps(second, ensure_ascii=False, sort_keys=True)}"
        )

    return first


def run_record(bin_path: Path, baseline_path: Path) -> None:
    fixtures = _fixture_list_for_record(baseline_path)
    out_fixtures: list[dict[str, Any]] = []

    for fixture in fixtures:
        fixture_id = fixture["id"]
        fixture_rel = fixture["path"]
        fixture_path = ROOT / fixture_rel
        measured = _measure_fixture(bin_path, fixture_id, fixture_path)
        out_fixtures.append(
            {
                "id": fixture_id,
                "path": fixture_rel,
                "max": {key: measured[key] for key in COUNTER_KEYS},
            }
        )
        print(f"[RECORD] {fixture_id}: {json.dumps(out_fixtures[-1]['max'], sort_keys=True)}")

    payload = {
        "version": BASELINE_VERSION,
        "fixtures": out_fixtures,
    }
    _write_json(baseline_path, payload)
    print(f"[OK] baseline updated: {baseline_path}")


def run_check(bin_path: Path, baseline_path: Path) -> None:
    fixtures = _fixtures_for_check(baseline_path)
    failures: list[str] = []

    for fixture in fixtures:
        fixture_id = str(fixture["id"])
        fixture_rel = str(fixture["path"])
        fixture_path = ROOT / fixture_rel
        expected_max = fixture["max"]
        measured = _measure_fixture(bin_path, fixture_id, fixture_path)
        before_count = len(failures)

        for key in COUNTER_KEYS:
            cur = int(measured[key])
            limit = int(expected_max[key])
            if cur > limit:
                failures.append(
                    f"{fixture_id}:{key} current={cur} > baseline_max={limit}"
                )

        if len(failures) == before_count:
            print(f"[CHECK] {fixture_id}: PASS (stats <= baseline max)")
        else:
            print(f"[CHECK] {fixture_id}: FAIL")

    if failures:
        joined = "\n - ".join(failures)
        raise AssertionError(f"NFP perf gate regressions:\n - {joined}")

    print("[OK] NFP placer stats/perf gate passed")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="NFP placer stats/perf gate smoke")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--record", action="store_true", help="Record/update baseline with measured counters")
    mode.add_argument("--check", action="store_true", help="Check measured counters against baseline upper bounds")
    parser.add_argument("--bin", required=True, help="Path to nesting_engine binary")
    parser.add_argument("--baseline", required=True, help="Path to baseline JSON")
    args = parser.parse_args(argv)

    bin_path = Path(args.bin)
    if not bin_path.is_absolute():
        bin_path = (ROOT / bin_path).resolve()
    if not (bin_path.is_file() and os.access(bin_path, os.X_OK)):
        raise AssertionError(f"invalid nesting_engine binary: {bin_path}")

    baseline_path = Path(args.baseline)
    if not baseline_path.is_absolute():
        baseline_path = ROOT / baseline_path

    if args.record:
        run_record(bin_path, baseline_path)
    else:
        run_check(bin_path, baseline_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
