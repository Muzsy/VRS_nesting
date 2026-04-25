#!/usr/bin/env python3
"""Smoke: New Run Wizard Step2 Strategy T2 resolver + snapshot precedence.

Tests the full precedence chain without real Supabase / worker / solver:
  request > run_config overrides > profile solver_config > global default
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.services.run_strategy_resolution import (  # noqa: E402
    ResolvedRunStrategy,
    RunStrategyResolutionError,
    resolve_run_strategy,
)
from api.services.run_snapshot_builder import build_run_snapshot_payload  # noqa: E402

passed = 0
failed = 0


def _test(label: str, condition: bool, detail: str = "") -> None:
    global passed, failed
    if condition:
        passed += 1
        print(f"  [OK]   {label}")
    else:
        failed += 1
        msg = f"  [FAIL] {label}"
        if detail:
            msg += f" -- {detail}"
        print(msg, file=sys.stderr)


def _expect_resolution_error(fn: Any, *, status_code: int, detail_contains: str) -> RunStrategyResolutionError:
    try:
        fn()
    except RunStrategyResolutionError as exc:
        if exc.status_code != status_code:
            raise RuntimeError(f"unexpected status: {exc.status_code} != {status_code}: {exc.detail}")
        if detail_contains not in exc.detail:
            raise RuntimeError(f"unexpected detail: {exc.detail!r} (expected to contain {detail_contains!r})")
        return exc
    raise RuntimeError("expected RunStrategyResolutionError")


# ---------------------------------------------------------------------------
# Fake Supabase client
# ---------------------------------------------------------------------------

OWNER_ID = "user-owner-001"
OTHER_OWNER_ID = "user-other-002"
PROJECT_ID = "project-aaa-001"

PROFILE_VERSION_ID_A = "pv-aaa-001"
PROFILE_VERSION_ID_B = "pv-bbb-002"
PROFILE_VERSION_ID_FOREIGN = "pv-foreign-003"

RUN_CONFIG_ID_WITH_PROFILE = "rc-with-profile-001"
RUN_CONFIG_ID_WITH_OVERRIDES = "rc-with-overrides-002"
RUN_CONFIG_ID_PLAIN = "rc-plain-003"

_RUN_CONFIG_TABLE = {
    RUN_CONFIG_ID_WITH_PROFILE: {
        "id": RUN_CONFIG_ID_WITH_PROFILE,
        "project_id": PROJECT_ID,
        "created_by": OWNER_ID,
        "run_strategy_profile_version_id": PROFILE_VERSION_ID_B,
        "solver_config_overrides_jsonb": {},
    },
    RUN_CONFIG_ID_WITH_OVERRIDES: {
        "id": RUN_CONFIG_ID_WITH_OVERRIDES,
        "project_id": PROJECT_ID,
        "created_by": OWNER_ID,
        "run_strategy_profile_version_id": PROFILE_VERSION_ID_A,
        "solver_config_overrides_jsonb": {
            "quality_profile": "fast_preview",
            "engine_backend_hint": "sparrow_v1",
        },
    },
    RUN_CONFIG_ID_PLAIN: {
        "id": RUN_CONFIG_ID_PLAIN,
        "project_id": PROJECT_ID,
        "created_by": OWNER_ID,
        "run_strategy_profile_version_id": None,
        "solver_config_overrides_jsonb": {},
    },
}

_PROFILE_VERSION_TABLE = {
    PROFILE_VERSION_ID_A: {
        "id": PROFILE_VERSION_ID_A,
        "run_strategy_profile_id": "rsp-001",
        "owner_user_id": OWNER_ID,
        "version_no": 1,
        "lifecycle": "active",
        "is_active": True,
        "solver_config_jsonb": {
            "quality_profile": "quality_aggressive",
            "engine_backend_hint": "nesting_engine_v2",
        },
        "placement_config_jsonb": {},
        "manufacturing_bias_jsonb": {},
    },
    PROFILE_VERSION_ID_B: {
        "id": PROFILE_VERSION_ID_B,
        "run_strategy_profile_id": "rsp-001",
        "owner_user_id": OWNER_ID,
        "version_no": 2,
        "lifecycle": "active",
        "is_active": True,
        "solver_config_jsonb": {
            "quality_profile": "quality_default",
            "engine_backend_hint": "sparrow_v1",
        },
        "placement_config_jsonb": {},
        "manufacturing_bias_jsonb": {},
    },
    PROFILE_VERSION_ID_FOREIGN: {
        "id": PROFILE_VERSION_ID_FOREIGN,
        "run_strategy_profile_id": "rsp-foreign",
        "owner_user_id": OTHER_OWNER_ID,
        "version_no": 1,
        "lifecycle": "active",
        "is_active": True,
        "solver_config_jsonb": {},
        "placement_config_jsonb": {},
        "manufacturing_bias_jsonb": {},
    },
}

_PROJECT_SELECTION: dict[str, Any] | None = None


class FakeSupabaseClient:
    """Minimal fake that returns in-memory mock data."""

    def __init__(self, *, project_selection: dict[str, Any] | None = None) -> None:
        self._project_selection = project_selection

    def select_rows(self, *, table: str, access_token: str, params: dict[str, str]) -> list[dict[str, Any]]:
        relation = table.split(".", 1)[-1]

        if relation == "run_configs":
            rc_id = params.get("id", "").removeprefix("eq.")
            row = _RUN_CONFIG_TABLE.get(rc_id)
            return [row] if row else []

        if relation == "project_run_strategy_selection":
            return [self._project_selection] if self._project_selection else []

        if relation == "run_strategy_profile_versions":
            pv_id = params.get("id", "").removeprefix("eq.")
            row = _PROFILE_VERSION_TABLE.get(pv_id)
            return [row] if row else []

        return []

    # Unused in resolver but required by SupabaseClient protocol
    def insert_row(self, *, table: str, access_token: str, payload: dict[str, Any]) -> dict[str, Any]:
        return {"id": "fake-id"}

    def update_rows(self, *, table: str, access_token: str, payload: dict[str, Any], filters: dict[str, str]) -> list[dict[str, Any]]:
        return []

    def delete_rows(self, *, table: str, access_token: str, filters: dict[str, str]) -> None:
        pass


def _resolve(
    *,
    supabase: FakeSupabaseClient | None = None,
    project_selection: dict[str, Any] | None = None,
    run_config_id: str | None = None,
    request_run_strategy_profile_version_id: str | None = None,
    request_quality_profile: str | None = None,
    request_engine_backend_hint: str | None = None,
    request_nesting_engine_runtime_policy: dict[str, Any] | None = None,
    request_sa_eval_budget_sec: int | None = None,
) -> ResolvedRunStrategy:
    client = supabase or FakeSupabaseClient(project_selection=project_selection)
    return resolve_run_strategy(
        supabase=client,  # type: ignore[arg-type]
        access_token="fake-token",
        owner_user_id=OWNER_ID,
        project_id=PROJECT_ID,
        run_config_id=run_config_id,
        request_run_strategy_profile_version_id=request_run_strategy_profile_version_id,
        request_quality_profile=request_quality_profile,
        request_engine_backend_hint=request_engine_backend_hint,
        request_nesting_engine_runtime_policy=request_nesting_engine_runtime_policy,
        request_sa_eval_budget_sec=request_sa_eval_budget_sec,
    )


# ---------------------------------------------------------------------------
# Test case 1: default-only
# ---------------------------------------------------------------------------

def test_default_only() -> None:
    print("\n[1] default-only resolution")
    result = _resolve()
    _test("quality_profile == quality_default", result.quality_profile == "quality_default", result.quality_profile)
    _test("strategy_resolution_source == global_default", result.strategy_resolution_source == "global_default", result.strategy_resolution_source)
    _test("strategy_profile_version_id is None", result.strategy_profile_version_id is None)
    _test("engine_backend_hint == nesting_engine_v2", result.engine_backend_hint == "nesting_engine_v2", result.engine_backend_hint)
    _test("field_sources.quality_profile == global_default", result.field_sources.get("quality_profile") == "global_default")
    _test("overrides_applied is empty", result.overrides_applied == [])


# ---------------------------------------------------------------------------
# Test case 2: project selection fallback
# ---------------------------------------------------------------------------

def test_project_selection_fallback() -> None:
    print("\n[2] project selection fallback")
    selection = {
        "project_id": PROJECT_ID,
        "active_run_strategy_profile_version_id": PROFILE_VERSION_ID_A,
        "selected_at": "2026-01-01T00:00:00Z",
        "selected_by": OWNER_ID,
    }
    result = _resolve(project_selection=selection)
    _test("strategy_resolution_source == project_selection", result.strategy_resolution_source == "project_selection", result.strategy_resolution_source)
    _test("strategy_profile_version_id == PROFILE_VERSION_ID_A", result.strategy_profile_version_id == PROFILE_VERSION_ID_A)
    # Profile A has quality_aggressive
    _test("quality_profile from profile A == quality_aggressive", result.quality_profile == "quality_aggressive", result.quality_profile)
    _test("engine_backend_hint from profile A == nesting_engine_v2", result.engine_backend_hint == "nesting_engine_v2", result.engine_backend_hint)
    _test("field_sources.quality_profile == profile", result.field_sources.get("quality_profile") == "profile")


# ---------------------------------------------------------------------------
# Test case 3: run_config with profile overrides project selection
# ---------------------------------------------------------------------------

def test_run_config_profile_overrides_project_selection() -> None:
    print("\n[3] run_config profile version overrides project selection")
    selection = {
        "project_id": PROJECT_ID,
        "active_run_strategy_profile_version_id": PROFILE_VERSION_ID_A,
        "selected_at": "2026-01-01T00:00:00Z",
        "selected_by": OWNER_ID,
    }
    # run_config has profile B -> should win over project selection (profile A)
    result = _resolve(
        project_selection=selection,
        run_config_id=RUN_CONFIG_ID_WITH_PROFILE,
    )
    _test("strategy_resolution_source == run_config", result.strategy_resolution_source == "run_config", result.strategy_resolution_source)
    _test("strategy_profile_version_id == PROFILE_VERSION_ID_B", result.strategy_profile_version_id == PROFILE_VERSION_ID_B)
    # Profile B has quality_default and sparrow_v1
    _test("quality_profile from profile B == quality_default", result.quality_profile == "quality_default", result.quality_profile)
    _test("engine_backend_hint from profile B == sparrow_v1", result.engine_backend_hint == "sparrow_v1", result.engine_backend_hint)


# ---------------------------------------------------------------------------
# Test case 4: run_config solver_config_overrides overrides profile solver config
# ---------------------------------------------------------------------------

def test_run_config_override_overrides_profile_config() -> None:
    print("\n[4] run_config solver_config_overrides overrides profile solver_config")
    # RUN_CONFIG_ID_WITH_OVERRIDES has profile A (quality_aggressive / nesting_engine_v2)
    # but overrides quality_profile=fast_preview and engine_backend_hint=sparrow_v1
    result = _resolve(run_config_id=RUN_CONFIG_ID_WITH_OVERRIDES)
    _test("strategy_resolution_source == run_config", result.strategy_resolution_source == "run_config", result.strategy_resolution_source)
    _test("strategy_profile_version_id == PROFILE_VERSION_ID_A", result.strategy_profile_version_id == PROFILE_VERSION_ID_A)
    _test("quality_profile == fast_preview (override wins)", result.quality_profile == "fast_preview", result.quality_profile)
    _test("engine_backend_hint == sparrow_v1 (override wins)", result.engine_backend_hint == "sparrow_v1", result.engine_backend_hint)
    _test("quality_profile in field_sources as run_config_override", result.field_sources.get("quality_profile") == "run_config_override")
    _test("quality_profile in overrides_applied", "quality_profile" in result.overrides_applied)


# ---------------------------------------------------------------------------
# Test case 5: explicit request override overrides everything
# ---------------------------------------------------------------------------

def test_explicit_request_override_wins_all() -> None:
    print("\n[5] explicit request override overrides everything")
    selection = {
        "project_id": PROJECT_ID,
        "active_run_strategy_profile_version_id": PROFILE_VERSION_ID_A,
        "selected_at": "2026-01-01T00:00:00Z",
        "selected_by": OWNER_ID,
    }
    result = _resolve(
        project_selection=selection,
        run_config_id=RUN_CONFIG_ID_WITH_OVERRIDES,
        request_quality_profile="fast_preview",
        request_engine_backend_hint="nesting_engine_v2",
        request_sa_eval_budget_sec=42,
    )
    _test("quality_profile from request == fast_preview", result.quality_profile == "fast_preview", result.quality_profile)
    _test("engine_backend_hint from request == nesting_engine_v2", result.engine_backend_hint == "nesting_engine_v2", result.engine_backend_hint)
    _test("sa_eval_budget_sec from request == 42", result.sa_eval_budget_sec == 42, str(result.sa_eval_budget_sec))
    _test("field_sources.quality_profile == request", result.field_sources.get("quality_profile") == "request")
    _test("field_sources.engine_backend_hint == request", result.field_sources.get("engine_backend_hint") == "request")
    _test("request fields in overrides_applied", "quality_profile" in result.overrides_applied and "engine_backend_hint" in result.overrides_applied)


# ---------------------------------------------------------------------------
# Test case 6: snapshot solver_config_jsonb contains trace fields
# ---------------------------------------------------------------------------

class _SnapshotFakeClient(FakeSupabaseClient):
    """Extends fake client to support snapshot builder queries."""

    def select_rows(self, *, table: str, access_token: str, params: dict[str, str]) -> list[dict[str, Any]]:
        relation = table.split(".", 1)[-1]

        if relation == "projects":
            return [{
                "id": PROJECT_ID,
                "owner_user_id": OWNER_ID,
                "name": "Test Project",
                "lifecycle": "active",
            }]
        if relation == "project_settings":
            return [{
                "project_id": PROJECT_ID,
                "default_units": "mm",
                "default_rotation_step_deg": 90,
                "notes": None,
            }]
        if relation == "project_technology_setups":
            return [{
                "id": "ts-001",
                "project_id": PROJECT_ID,
                "preset_id": None,
                "display_name": "Default",
                "lifecycle": "approved",
                "is_default": True,
                "machine_code": "LASER_001",
                "material_code": "STEEL_3MM",
                "thickness_mm": 3.0,
                "kerf_mm": 0.2,
                "spacing_mm": 2.0,
                "margin_mm": 5.0,
                "rotation_step_deg": 90,
                "allow_free_rotation": False,
                "notes": None,
            }]
        if relation == "project_part_requirements":
            return [{
                "id": "ppr-001",
                "project_id": PROJECT_ID,
                "part_revision_id": "prev-001",
                "required_qty": 2,
                "placement_priority": 50,
                "placement_policy": "required",
                "is_active": True,
                "notes": None,
            }]
        if relation == "part_revisions":
            return [{
                "id": "prev-001",
                "part_definition_id": "pdef-001",
                "revision_no": 1,
                "lifecycle": "approved",
                "source_geometry_revision_id": "grev-001",
                "selected_nesting_derivative_id": "deriv-001",
            }]
        if relation == "part_definitions":
            return [{
                "id": "pdef-001",
                "owner_user_id": OWNER_ID,
                "code": "PART-A",
                "name": "Part A",
                "current_revision_id": "prev-001",
            }]
        if relation == "geometry_derivatives":
            return [{
                "id": "deriv-001",
                "geometry_revision_id": "grev-001",
                "derivative_kind": "nesting_canonical",
                "derivative_jsonb": {
                    "polygon": {
                        "outer_ring": [[0.0, 0.0], [100.0, 0.0], [100.0, 50.0], [0.0, 50.0]],
                        "hole_rings": [],
                    },
                    "bbox": {
                        "min_x": 0.0, "min_y": 0.0, "max_x": 100.0, "max_y": 50.0,
                        "width": 100.0, "height": 50.0,
                    },
                },
                "derivative_hash_sha256": "abc123",
                "source_geometry_hash_sha256": "def456",
            }]
        if relation == "project_sheet_inputs":
            return [{
                "id": "psi-001",
                "project_id": PROJECT_ID,
                "sheet_revision_id": "srev-001",
                "required_qty": 5,
                "is_active": True,
                "is_default": True,
                "placement_priority": 50,
                "notes": None,
            }]
        if relation == "sheet_revisions":
            return [{
                "id": "srev-001",
                "sheet_definition_id": "sdef-001",
                "revision_no": 1,
                "lifecycle": "approved",
                "width_mm": 1000.0,
                "height_mm": 2000.0,
                "grain_direction": None,
            }]
        if relation == "sheet_definitions":
            return [{
                "id": "sdef-001",
                "owner_user_id": OWNER_ID,
                "code": "SHEET-STD",
                "name": "Standard Sheet",
                "current_revision_id": "srev-001",
            }]
        if relation == "project_manufacturing_selection":
            return []

        return super().select_rows(table=table, access_token=access_token, params=params)


def test_snapshot_trace_fields_present() -> None:
    print("\n[6] snapshot solver_config_jsonb contains strategy trace fields")
    client = _SnapshotFakeClient()
    result = _resolve(supabase=client, request_quality_profile="fast_preview")
    snapshot = build_run_snapshot_payload(
        supabase=client,  # type: ignore[arg-type]
        access_token="fake-token",
        owner_user_id=OWNER_ID,
        project_id=PROJECT_ID,
        quality_profile=result.quality_profile,
        engine_backend_hint=result.engine_backend_hint,
        nesting_engine_runtime_policy=result.nesting_engine_runtime_policy,
        sa_eval_budget_sec=result.sa_eval_budget_sec,
        strategy_profile_version_id=result.strategy_profile_version_id,
        strategy_resolution_source=result.strategy_resolution_source,
        strategy_field_sources=result.field_sources,
        strategy_overrides_applied=result.overrides_applied,
    )
    solver_cfg = snapshot.get("solver_config_jsonb", {})
    _test("solver_config_jsonb.quality_profile present", "quality_profile" in solver_cfg)
    _test("solver_config_jsonb.engine_backend_hint present", "engine_backend_hint" in solver_cfg)
    _test("solver_config_jsonb.nesting_engine_runtime_policy present", "nesting_engine_runtime_policy" in solver_cfg)
    _test("solver_config_jsonb.strategy_resolution_source present", "strategy_resolution_source" in solver_cfg, str(list(solver_cfg.keys())))
    _test("solver_config_jsonb.strategy_field_sources present", "strategy_field_sources" in solver_cfg)
    _test("solver_config_jsonb.strategy_overrides_applied present", "strategy_overrides_applied" in solver_cfg)
    _test("snapshot_hash_sha256 is non-empty", bool(snapshot.get("snapshot_hash_sha256")))


# ---------------------------------------------------------------------------
# Test case 7: run request_payload_jsonb contains resolution summary
# ---------------------------------------------------------------------------

def test_request_payload_resolution_summary() -> None:
    print("\n[7] run request_payload_jsonb contains resolution summary")
    from api.services.run_creation import _insert_run, ResolvedRunStrategy  # noqa: F811

    resolved = _resolve(request_quality_profile="fast_preview")

    # Simulate what _insert_run would put in request_payload_jsonb
    # (we call it with a mock that records the payload)
    recorded: list[dict[str, Any]] = []

    class _RecordingClient(FakeSupabaseClient):
        def insert_row(self, *, table: str, access_token: str, payload: dict[str, Any]) -> dict[str, Any]:
            recorded.append({"table": table, "payload": payload})
            return {"id": "run-fake-001"}

    client = _RecordingClient()
    _insert_run(
        supabase=client,  # type: ignore[arg-type]
        access_token="fake-token",
        project_id=PROJECT_ID,
        owner_user_id=OWNER_ID,
        run_purpose="nesting",
        idempotency_key=None,
        snapshot_hash_sha256="abc" * 21,
        run_config_id=None,
        resolved_strategy=resolved,
    )

    _test("insert_run called", len(recorded) == 1)
    if recorded:
        rp = recorded[0]["payload"].get("request_payload_jsonb", {})
        _test("request_payload has strategy_resolution_source", "strategy_resolution_source" in rp)
        _test("request_payload has effective_strategy_profile_version_id", "effective_strategy_profile_version_id" in rp)
        _test("request_payload has strategy_field_sources", "strategy_field_sources" in rp)
        _test("request_payload has strategy_overrides_applied", "strategy_overrides_applied" in rp)


# ---------------------------------------------------------------------------
# Test case 8: foreign owner strategy version rejected
# ---------------------------------------------------------------------------

def test_foreign_owner_strategy_version_rejected() -> None:
    print("\n[8] foreign owner strategy version rejected")
    _expect_resolution_error(
        lambda: _resolve(request_run_strategy_profile_version_id=PROFILE_VERSION_ID_FOREIGN),
        status_code=403,
        detail_contains="does not belong to owner",
    )
    _test("foreign owner version raises 403", True)


# ---------------------------------------------------------------------------
# Test case 9: invalid runtime policy rejected
# ---------------------------------------------------------------------------

def test_invalid_runtime_policy_rejected() -> None:
    print("\n[9] invalid runtime policy rejected")
    invalid_policy = {"placer": "invalid_placer", "search": "none", "part_in_part": "off", "compaction": "off"}
    _expect_resolution_error(
        lambda: _resolve(request_nesting_engine_runtime_policy=invalid_policy),
        status_code=400,
        detail_contains="invalid nesting_engine_runtime_policy",
    )
    _test("invalid runtime policy raises 400", True)


# ---------------------------------------------------------------------------
# Run all tests
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    test_default_only()
    test_project_selection_fallback()
    test_run_config_profile_overrides_project_selection()
    test_run_config_override_overrides_profile_config()
    test_explicit_request_override_wins_all()
    test_snapshot_trace_fields_present()
    test_request_payload_resolution_summary()
    test_foreign_owner_strategy_version_rejected()
    test_invalid_runtime_policy_rejected()

    print(f"\n{'='*60}")
    print(f"T2 smoke: {passed} passed, {failed} failed")
    if failed:
        print("FAIL", file=sys.stderr)
        sys.exit(1)
    print("PASS")
