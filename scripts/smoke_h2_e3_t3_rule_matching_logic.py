#!/usr/bin/env python3
"""H2-E3-T3 smoke: cut-rule matching engine — deterministic rule selection."""

from __future__ import annotations

import copy
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.services.cut_rule_matching import match_rules_for_derivative


# ---------------------------------------------------------------------------
# Fake Supabase client (in-memory, read-only verification)
# ---------------------------------------------------------------------------

class FakeSupabaseClient:
    """Minimal in-memory Supabase stub for rule matching smoke."""

    def __init__(self) -> None:
        self.geometry_contour_classes: dict[str, dict[str, Any]] = {}
        self.cut_contour_rules: dict[str, dict[str, Any]] = {}
        # Track write calls to verify no-write guarantee
        self.write_calls: list[dict[str, Any]] = []

    def _get_store(self, table: str) -> dict[str, dict[str, Any]] | None:
        if table == "app.geometry_contour_classes":
            return self.geometry_contour_classes
        if table == "app.cut_contour_rules":
            return self.cut_contour_rules
        return None

    def select_rows(
        self,
        *,
        table: str,
        access_token: str,
        params: dict[str, str],
    ) -> list[dict[str, Any]]:
        _ = access_token
        store = self._get_store(table)
        if store is None:
            return []

        rows = list(store.values())
        meta_keys = {"select", "order", "limit", "offset"}

        for key, raw_filter in params.items():
            if key in meta_keys:
                continue
            if raw_filter.startswith("eq."):
                expected = raw_filter[3:]
                rows = [row for row in rows if str(row.get(key)).lower() == expected.lower()]

        order_clause = params.get("order", "").strip()
        if order_clause:
            for token in reversed([p.strip() for p in order_clause.split(",") if p.strip()]):
                field = token.split(".")[0]
                reverse = ".desc" in token
                rows.sort(key=lambda r, f=field: str(r.get(f) or ""), reverse=reverse)

        limit_raw = params.get("limit", "")
        if limit_raw:
            rows = rows[: int(limit_raw)]
        return [dict(row) for row in rows]

    def insert_row(self, *, table: str, access_token: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.write_calls.append({"op": "insert", "table": table, "payload": payload})
        raise RuntimeError(f"unexpected insert on {table} — matching engine must be read-only")

    def update_rows(self, *, table: str, access_token: str, payload: dict[str, Any], filters: dict[str, str]) -> list[dict[str, Any]]:
        self.write_calls.append({"op": "update", "table": table, "payload": payload, "filters": filters})
        raise RuntimeError(f"unexpected update on {table} — matching engine must be read-only")

    def delete_rows(self, *, table: str, access_token: str, filters: dict[str, str]) -> None:
        self.write_calls.append({"op": "delete", "table": table, "filters": filters})
        raise RuntimeError(f"unexpected delete on {table} — matching engine must be read-only")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _add_contour_class(
    fake: FakeSupabaseClient,
    *,
    derivative_id: str,
    contour_index: int,
    contour_kind: str,
    feature_class: str = "default",
    perimeter_mm: float = 400.0,
) -> str:
    row_id = str(uuid4())
    fake.geometry_contour_classes[row_id] = {
        "id": row_id,
        "geometry_derivative_id": derivative_id,
        "contour_index": contour_index,
        "contour_kind": contour_kind,
        "feature_class": feature_class,
        "is_closed": True,
        "area_mm2": 9600.0,
        "perimeter_mm": perimeter_mm,
        "bbox_jsonb": {},
        "metadata_jsonb": {},
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    return row_id


def _add_rule(
    fake: FakeSupabaseClient,
    *,
    rule_set_id: str,
    contour_kind: str,
    feature_class: str = "default",
    sort_order: int = 100,
    enabled: bool = True,
    min_contour_length_mm: float | None = None,
    max_contour_length_mm: float | None = None,
    rule_id: str | None = None,
) -> str:
    rid = rule_id or str(uuid4())
    fake.cut_contour_rules[rid] = {
        "id": rid,
        "cut_rule_set_id": rule_set_id,
        "contour_kind": contour_kind,
        "feature_class": feature_class,
        "lead_in_type": "line",
        "lead_out_type": "none",
        "sort_order": sort_order,
        "enabled": enabled,
        "min_contour_length_mm": min_contour_length_mm,
        "max_contour_length_mm": max_contour_length_mm,
        "metadata_jsonb": {},
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    return rid


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

passed = 0
failed = 0


def _test(name: str, ok: bool, detail: str = "") -> None:
    global passed, failed
    if ok:
        passed += 1
        print(f"  [PASS] {name}")
    else:
        failed += 1
        msg = f"  [FAIL] {name}"
        if detail:
            msg += f" -- {detail}"
        print(msg, file=sys.stderr)


def main() -> int:
    global passed, failed

    DERIV_ID = str(uuid4())
    RULE_SET_ID = str(uuid4())

    # ===================================================================
    # TEST 1: outer contour gets outer rule
    # ===================================================================
    print("Test 1: outer contour -> outer rule")
    fake = FakeSupabaseClient()
    _add_contour_class(fake, derivative_id=DERIV_ID, contour_index=0, contour_kind="outer")
    outer_rule = _add_rule(fake, rule_set_id=RULE_SET_ID, contour_kind="outer")

    result = match_rules_for_derivative(
        supabase=fake,  # type: ignore[arg-type]
        access_token="tok",
        cut_rule_set_id=RULE_SET_ID,
        geometry_derivative_id=DERIV_ID,
    )
    _test("matched_count == 1", result["matched_count"] == 1, f"got {result['matched_count']}")
    _test("contour 0 matched outer rule", result["contours"][0]["matched_rule_id"] == outer_rule)
    _test("matched_via == default", result["contours"][0]["matched_via"] == "default")

    # ===================================================================
    # TEST 2: inner contour gets inner rule
    # ===================================================================
    print("Test 2: inner contour -> inner rule")
    fake2 = FakeSupabaseClient()
    _add_contour_class(fake2, derivative_id=DERIV_ID, contour_index=0, contour_kind="inner")
    inner_rule = _add_rule(fake2, rule_set_id=RULE_SET_ID, contour_kind="inner")
    # Add outer rule too — must not match inner contour
    _add_rule(fake2, rule_set_id=RULE_SET_ID, contour_kind="outer")

    result2 = match_rules_for_derivative(
        supabase=fake2,  # type: ignore[arg-type]
        access_token="tok",
        cut_rule_set_id=RULE_SET_ID,
        geometry_derivative_id=DERIV_ID,
    )
    _test("inner matched_count == 1", result2["matched_count"] == 1)
    _test("inner matched inner rule", result2["contours"][0]["matched_rule_id"] == inner_rule)

    # ===================================================================
    # TEST 3: specific feature_class beats default
    # ===================================================================
    print("Test 3: specific feature_class > default fallback")
    fake3 = FakeSupabaseClient()
    _add_contour_class(fake3, derivative_id=DERIV_ID, contour_index=0, contour_kind="inner", feature_class="slot")
    default_rule = _add_rule(fake3, rule_set_id=RULE_SET_ID, contour_kind="inner", feature_class="default", sort_order=1)
    slot_rule = _add_rule(fake3, rule_set_id=RULE_SET_ID, contour_kind="inner", feature_class="slot", sort_order=10)

    result3 = match_rules_for_derivative(
        supabase=fake3,  # type: ignore[arg-type]
        access_token="tok",
        cut_rule_set_id=RULE_SET_ID,
        geometry_derivative_id=DERIV_ID,
    )
    _test("specific feature_class matched", result3["contours"][0]["matched_rule_id"] == slot_rule)
    _test("matched_via == feature_class", result3["contours"][0]["matched_via"] == "feature_class")

    # Also test: contour with feature_class=default should match the default rule
    fake3b = FakeSupabaseClient()
    _add_contour_class(fake3b, derivative_id=DERIV_ID, contour_index=0, contour_kind="inner", feature_class="default")
    default_rule3b = _add_rule(fake3b, rule_set_id=RULE_SET_ID, contour_kind="inner", feature_class="default", sort_order=1)
    _add_rule(fake3b, rule_set_id=RULE_SET_ID, contour_kind="inner", feature_class="slot", sort_order=10)

    result3b = match_rules_for_derivative(
        supabase=fake3b,  # type: ignore[arg-type]
        access_token="tok",
        cut_rule_set_id=RULE_SET_ID,
        geometry_derivative_id=DERIV_ID,
    )
    _test("default contour gets default rule", result3b["contours"][0]["matched_rule_id"] == default_rule3b)
    _test("matched_via == default for default contour", result3b["contours"][0]["matched_via"] == "default")

    # ===================================================================
    # TEST 4: disabled rule is excluded
    # ===================================================================
    print("Test 4: disabled rule excluded")
    fake4 = FakeSupabaseClient()
    _add_contour_class(fake4, derivative_id=DERIV_ID, contour_index=0, contour_kind="outer")
    _add_rule(fake4, rule_set_id=RULE_SET_ID, contour_kind="outer", enabled=False, sort_order=1)
    enabled_rule = _add_rule(fake4, rule_set_id=RULE_SET_ID, contour_kind="outer", enabled=True, sort_order=50)

    result4 = match_rules_for_derivative(
        supabase=fake4,  # type: ignore[arg-type]
        access_token="tok",
        cut_rule_set_id=RULE_SET_ID,
        geometry_derivative_id=DERIV_ID,
    )
    _test("disabled rule skipped", result4["contours"][0]["matched_rule_id"] == enabled_rule)

    # ===================================================================
    # TEST 5: perimeter out of range -> unmatched
    # ===================================================================
    print("Test 5: perimeter out of range -> unmatched")
    fake5 = FakeSupabaseClient()
    # Contour with perimeter 50mm
    _add_contour_class(fake5, derivative_id=DERIV_ID, contour_index=0, contour_kind="outer", perimeter_mm=50.0)
    # Rule requires 100-200mm
    _add_rule(fake5, rule_set_id=RULE_SET_ID, contour_kind="outer",
              min_contour_length_mm=100.0, max_contour_length_mm=200.0)

    result5 = match_rules_for_derivative(
        supabase=fake5,  # type: ignore[arg-type]
        access_token="tok",
        cut_rule_set_id=RULE_SET_ID,
        geometry_derivative_id=DERIV_ID,
    )
    _test("unmatched_count == 1", result5["unmatched_count"] == 1)
    _test("unmatched_reason mentions perimeter", "perimeter" in (result5["contours"][0].get("unmatched_reason") or "").lower())
    _test("matched_rule_id is None", result5["contours"][0]["matched_rule_id"] is None)

    # Also: perimeter within range should match
    fake5b = FakeSupabaseClient()
    _add_contour_class(fake5b, derivative_id=DERIV_ID, contour_index=0, contour_kind="outer", perimeter_mm=150.0)
    range_rule = _add_rule(fake5b, rule_set_id=RULE_SET_ID, contour_kind="outer",
                           min_contour_length_mm=100.0, max_contour_length_mm=200.0)

    result5b = match_rules_for_derivative(
        supabase=fake5b,  # type: ignore[arg-type]
        access_token="tok",
        cut_rule_set_id=RULE_SET_ID,
        geometry_derivative_id=DERIV_ID,
    )
    _test("perimeter in range matches", result5b["contours"][0]["matched_rule_id"] == range_rule)

    # ===================================================================
    # TEST 6: deterministic tie-break
    # ===================================================================
    print("Test 6: deterministic tie-break")
    fake6 = FakeSupabaseClient()
    _add_contour_class(fake6, derivative_id=DERIV_ID, contour_index=0, contour_kind="outer")

    # Create two rules with same sort_order — tie-break by id
    id_a = "00000000-0000-0000-0000-000000000aaa"
    id_b = "00000000-0000-0000-0000-000000000bbb"
    _add_rule(fake6, rule_set_id=RULE_SET_ID, contour_kind="outer", sort_order=10, rule_id=id_b)
    _add_rule(fake6, rule_set_id=RULE_SET_ID, contour_kind="outer", sort_order=10, rule_id=id_a)

    result6 = match_rules_for_derivative(
        supabase=fake6,  # type: ignore[arg-type]
        access_token="tok",
        cut_rule_set_id=RULE_SET_ID,
        geometry_derivative_id=DERIV_ID,
    )
    _test("tie-break picks lexicographic smaller id", result6["contours"][0]["matched_rule_id"] == id_a)

    # Run again to verify determinism
    result6b = match_rules_for_derivative(
        supabase=fake6,  # type: ignore[arg-type]
        access_token="tok",
        cut_rule_set_id=RULE_SET_ID,
        geometry_derivative_id=DERIV_ID,
    )
    _test("tie-break is repeatable", result6b["contours"][0]["matched_rule_id"] == id_a)

    # Lower sort_order wins regardless of id
    fake6c = FakeSupabaseClient()
    _add_contour_class(fake6c, derivative_id=DERIV_ID, contour_index=0, contour_kind="outer")
    _add_rule(fake6c, rule_set_id=RULE_SET_ID, contour_kind="outer", sort_order=5, rule_id=id_b)
    _add_rule(fake6c, rule_set_id=RULE_SET_ID, contour_kind="outer", sort_order=10, rule_id=id_a)

    result6c = match_rules_for_derivative(
        supabase=fake6c,  # type: ignore[arg-type]
        access_token="tok",
        cut_rule_set_id=RULE_SET_ID,
        geometry_derivative_id=DERIV_ID,
    )
    _test("lower sort_order wins", result6c["contours"][0]["matched_rule_id"] == id_b)

    # ===================================================================
    # TEST 7: no-write guarantee
    # ===================================================================
    print("Test 7: no-write guarantee")
    # Reuse fake6 which already ran matching — verify no writes were attempted
    _test("no write_calls on fake6", len(fake6.write_calls) == 0, f"got {len(fake6.write_calls)} write calls")

    # Run on a fresh fake with multiple contours and verify
    fake7 = FakeSupabaseClient()
    _add_contour_class(fake7, derivative_id=DERIV_ID, contour_index=0, contour_kind="outer")
    _add_contour_class(fake7, derivative_id=DERIV_ID, contour_index=1, contour_kind="inner")
    _add_rule(fake7, rule_set_id=RULE_SET_ID, contour_kind="outer")
    _add_rule(fake7, rule_set_id=RULE_SET_ID, contour_kind="inner")

    # Take snapshot of contour class state before matching
    cc_snapshot = copy.deepcopy(fake7.geometry_contour_classes)

    result7 = match_rules_for_derivative(
        supabase=fake7,  # type: ignore[arg-type]
        access_token="tok",
        cut_rule_set_id=RULE_SET_ID,
        geometry_derivative_id=DERIV_ID,
    )
    _test("matched 2 contours", result7["matched_count"] == 2)
    _test("no write calls after multi-contour match", len(fake7.write_calls) == 0)
    _test(
        "contour classes unchanged after match",
        fake7.geometry_contour_classes == cc_snapshot,
    )

    # ===================================================================
    # TEST 8: mixed contours (outer+inner) in one derivative
    # ===================================================================
    print("Test 8: mixed contours in one derivative")
    fake8 = FakeSupabaseClient()
    d8 = str(uuid4())
    _add_contour_class(fake8, derivative_id=d8, contour_index=0, contour_kind="outer", perimeter_mm=400.0)
    _add_contour_class(fake8, derivative_id=d8, contour_index=1, contour_kind="inner", perimeter_mm=90.0)
    _add_contour_class(fake8, derivative_id=d8, contour_index=2, contour_kind="inner", perimeter_mm=60.0)

    outer_r8 = _add_rule(fake8, rule_set_id=RULE_SET_ID, contour_kind="outer")
    inner_r8 = _add_rule(fake8, rule_set_id=RULE_SET_ID, contour_kind="inner")

    result8 = match_rules_for_derivative(
        supabase=fake8,  # type: ignore[arg-type]
        access_token="tok",
        cut_rule_set_id=RULE_SET_ID,
        geometry_derivative_id=d8,
    )
    _test("3 contour results", len(result8["contours"]) == 3)
    _test("contour 0 is outer", result8["contours"][0]["matched_rule_id"] == outer_r8)
    _test("contour 1 is inner", result8["contours"][1]["matched_rule_id"] == inner_r8)
    _test("contour 2 is inner", result8["contours"][2]["matched_rule_id"] == inner_r8)
    _test("matched_count == 3", result8["matched_count"] == 3)

    # ===================================================================
    # TEST 9: no contour classes -> empty result
    # ===================================================================
    print("Test 9: no contour classes -> empty result")
    fake9 = FakeSupabaseClient()
    _add_rule(fake9, rule_set_id=RULE_SET_ID, contour_kind="outer")
    result9 = match_rules_for_derivative(
        supabase=fake9,  # type: ignore[arg-type]
        access_token="tok",
        cut_rule_set_id=RULE_SET_ID,
        geometry_derivative_id=str(uuid4()),
    )
    _test("empty contours list", len(result9["contours"]) == 0)
    _test("matched=0 unmatched=0", result9["matched_count"] == 0 and result9["unmatched_count"] == 0)

    # ===================================================================
    # TEST 10: no rules -> all unmatched
    # ===================================================================
    print("Test 10: no rules -> all unmatched")
    fake10 = FakeSupabaseClient()
    d10 = str(uuid4())
    _add_contour_class(fake10, derivative_id=d10, contour_index=0, contour_kind="outer")
    result10 = match_rules_for_derivative(
        supabase=fake10,  # type: ignore[arg-type]
        access_token="tok",
        cut_rule_set_id=RULE_SET_ID,
        geometry_derivative_id=d10,
    )
    _test("unmatched_count == 1", result10["unmatched_count"] == 1)
    _test("unmatched_reason present", result10["contours"][0]["unmatched_reason"] is not None)

    # ===================================================================
    # TEST 11: matched_rule_summary contains expected fields
    # ===================================================================
    print("Test 11: matched_rule_summary structure")
    # Reuse result from Test 1
    summary = result["contours"][0].get("matched_rule_summary")
    _test("summary is dict", isinstance(summary, dict))
    for field in ("id", "contour_kind", "feature_class", "lead_in_type", "lead_out_type", "sort_order"):
        _test(f"summary has {field}", field in summary, f"missing {field}")

    # ===================================================================
    # Summary
    # ===================================================================
    total = passed + failed
    print(f"\n{'='*60}")
    if failed == 0:
        print(f"[PASS] smoke_h2_e3_t3_rule_matching_logic: {passed}/{total} tests passed")
        return 0
    else:
        print(f"[FAIL] smoke_h2_e3_t3_rule_matching_logic: {passed}/{total} passed, {failed} failed", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
