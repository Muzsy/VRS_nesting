#!/usr/bin/env python3
"""Unit tests for the LV8 harness NEST_NFP_STATS_V1 parser and normalizer (T04)."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
_HARNESS_PATH = REPO_ROOT / "scripts" / "experiments" / "lv8_2sheet_claude_search.py"

spec = importlib.util.spec_from_file_location("lv8_2sheet_claude_search", _HARNESS_PATH)
assert spec is not None and spec.loader is not None
_harness = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_harness)  # type: ignore[arg-type]

_parse = _harness._parse_engine_stats_from_stderr
_normalize = _harness._normalize_engine_stats
STAT_PREFIX = _harness.STAT_PREFIX
PENDING_PHASE1_DONE: list[str] = []

_VALID_RAW: dict[str, Any] = {
    "nfp_cache_hits": 12,
    "nfp_cache_misses": 34,
    "nfp_cache_entries_end": 34,
    "nfp_cache_clear_all_events": 3,
    "nfp_cache_peak_entries": 777,
    "nfp_compute_calls": 34,
    "candidates_before_dedupe_total": 100,
    "candidates_after_dedupe_total": 80,
    "candidates_after_cap_total": 50,
    "can_place_profile_calls": 200,
    "effective_placer": "nfp",
    "sheets_used": 2,
    "actual_nfp_kernel": "old_concave",
    "actual_narrow_phase": "own",
}


def _make_stats_line(raw: dict[str, Any] | None = None) -> str:
    payload = raw if raw is not None else _VALID_RAW
    return STAT_PREFIX + json.dumps(payload)


class TestParseEngineStatsFromStderr:
    def test_valid_single_line(self) -> None:
        stderr = _make_stats_line()
        result = _parse(stderr)
        assert result["available"] is True
        assert result["parse_error"] is None
        assert result["source"] == "NEST_NFP_STATS_V1"
        assert result["raw"] == _VALID_RAW
        assert result["normalized"] is not None
        assert result["pending_phase1_fields"] == PENDING_PHASE1_DONE

    def test_missing_stats_line(self) -> None:
        result = _parse("no stats here\njust some other output\n")
        assert result["available"] is False
        assert result["parse_error"] == "missing_stats_line"
        assert result["raw"] is None
        assert result["normalized"] is None
        assert result["pending_phase1_fields"] == PENDING_PHASE1_DONE

    def test_empty_stderr(self) -> None:
        result = _parse("")
        assert result["available"] is False
        assert result["parse_error"] == "missing_stats_line"

    def test_two_stats_lines(self) -> None:
        stderr = _make_stats_line() + "\n" + _make_stats_line()
        result = _parse(stderr)
        assert result["available"] is False
        assert "expected_1_stats_line_got_2" in result["parse_error"]
        assert result["raw"] is None
        assert result["normalized"] is None
        assert result["pending_phase1_fields"] == PENDING_PHASE1_DONE

    def test_invalid_json(self) -> None:
        stderr = STAT_PREFIX + "{not valid json"
        result = _parse(stderr)
        assert result["available"] is False
        assert "invalid_json" in result["parse_error"]
        assert result["raw"] is None
        assert result["normalized"] is None
        assert result["pending_phase1_fields"] == PENDING_PHASE1_DONE

    def test_stats_line_mixed_with_other_output(self) -> None:
        stderr = "some preamble\n" + _make_stats_line() + "\nsome trailer\n"
        result = _parse(stderr)
        assert result["available"] is True
        assert result["raw"] == _VALID_RAW


class TestNormalizeEngineStats:
    def test_normalized_field_mapping(self) -> None:
        norm = _normalize(_VALID_RAW)
        assert norm["nfp_cache_hit_count"] == 12
        assert norm["nfp_cache_miss_count"] == 34
        assert norm["nfp_cache_entries_end"] == 34
        assert norm["nfp_cache_clear_all_events"] == 3
        assert norm["nfp_cache_peak_entries"] == 777
        assert norm["nfp_compute_count"] == 34
        assert norm["candidate_generate_count"] == 100
        assert norm["candidate_dedup_count"] == 80
        assert norm["candidate_after_cap_count"] == 50
        assert norm["can_place_call_count"] == 200
        assert norm["can_place_call_count_source"] == "can_place_profile_calls"
        assert norm["effective_placer"] == "nfp"
        assert norm["actual_nfp_kernel"] == "old_concave"
        assert norm["actual_narrow_phase"] == "own"

    def test_sheet_spillover_single_sheet(self) -> None:
        raw = {**_VALID_RAW, "sheets_used": 1}
        norm = _normalize(raw)
        assert norm["sheet_spillover_count"] == 0

    def test_sheet_spillover_two_sheets(self) -> None:
        norm = _normalize(_VALID_RAW)
        assert norm["sheet_spillover_count"] == 1

    def test_missing_fields_become_none(self) -> None:
        norm = _normalize({})
        assert norm["nfp_cache_hit_count"] is None
        assert norm["nfp_cache_miss_count"] is None
        assert norm["nfp_cache_clear_all_events"] is None
        assert norm["nfp_cache_peak_entries"] is None
        assert norm["nfp_compute_count"] is None
        assert norm["effective_placer"] is None
        assert norm["actual_nfp_kernel"] is None
        assert norm["actual_narrow_phase"] is None

    def test_missing_can_place_calls_is_none_not_zero(self) -> None:
        raw = {k: v for k, v in _VALID_RAW.items() if k != "can_place_profile_calls"}
        norm = _normalize(raw)
        assert norm["can_place_call_count"] is None

    def test_sheet_spillover_missing_sheets_used(self) -> None:
        raw = {k: v for k, v in _VALID_RAW.items() if k != "sheets_used"}
        norm = _normalize(raw)
        assert norm["sheet_spillover_count"] == 0


class TestPendingPhase1Fields:
    def test_pending_fields_present_on_success(self) -> None:
        result = _parse(_make_stats_line())
        assert result["pending_phase1_fields"] == PENDING_PHASE1_DONE

    def test_pending_fields_present_on_missing(self) -> None:
        result = _parse("")
        assert result["pending_phase1_fields"] == PENDING_PHASE1_DONE

    def test_pending_fields_present_on_multi_line(self) -> None:
        stderr = _make_stats_line() + "\n" + _make_stats_line()
        result = _parse(stderr)
        assert result["pending_phase1_fields"] == PENDING_PHASE1_DONE

    def test_pending_fields_present_on_invalid_json(self) -> None:
        result = _parse(STAT_PREFIX + "bad")
        assert result["pending_phase1_fields"] == PENDING_PHASE1_DONE

    def test_pending_fields_no_longer_contains_nfp_cache_clear_all_events(self) -> None:
        result = _parse(_make_stats_line())
        assert "nfp_cache_clear_all_events" not in result["pending_phase1_fields"]

    def test_pending_fields_no_longer_contains_nfp_cache_peak_entries(self) -> None:
        result = _parse(_make_stats_line())
        assert "nfp_cache_peak_entries" not in result["pending_phase1_fields"]
