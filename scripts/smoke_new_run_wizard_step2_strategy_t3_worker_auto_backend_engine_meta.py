#!/usr/bin/env python3
"""T3 smoke: worker auto backend resolution + engine_meta payload — no DB, no solver."""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from worker.main import (
    ENGINE_BACKEND_AUTO,
    ENGINE_BACKEND_NESTING_V2,
    ENGINE_BACKEND_SPARROW_V1,
    EngineProfileResolution,
    SolverRunnerInvocation,
    WorkerEngineBackendResolution,
    WorkerSettings,
    _build_engine_meta_payload,
    _resolve_effective_engine_backend,
    _resolve_worker_engine_backend,
)
from vrs_nesting.config.nesting_quality_profiles import (
    DEFAULT_QUALITY_PROFILE,
    build_nesting_engine_cli_args_from_runtime_policy,
    compact_runtime_policy,
    runtime_policy_for_quality_profile,
)

PASS_COUNT = 0
FAIL_COUNT = 0


def _check(label: str, condition: bool) -> None:
    global PASS_COUNT, FAIL_COUNT
    if condition:
        PASS_COUNT += 1
        print(f"  PASS  {label}")
    else:
        FAIL_COUNT += 1
        print(f"  FAIL  {label}")


def _snapshot(hint: str | None) -> dict:
    if hint is None:
        return {"solver_config_jsonb": {}}
    if hint == "__missing_key__":
        return {"solver_config_jsonb": {}}
    return {"solver_config_jsonb": {"engine_backend_hint": hint}}


def _profile(backend: str) -> EngineProfileResolution:
    if backend == ENGINE_BACKEND_NESTING_V2:
        policy = compact_runtime_policy(runtime_policy_for_quality_profile(DEFAULT_QUALITY_PROFILE))
        cli_args = build_nesting_engine_cli_args_from_runtime_policy(policy)
        return EngineProfileResolution(
            requested_engine_profile=DEFAULT_QUALITY_PROFILE,
            effective_engine_profile=DEFAULT_QUALITY_PROFILE,
            engine_profile_match=True,
            profile_resolution_source="registry",
            runtime_policy_source="registry",
            profile_effect="applied_to_nesting_engine_v2",
            nesting_engine_runtime_policy=policy,
            nesting_engine_cli_args=cli_args,
        )
    policy = compact_runtime_policy(runtime_policy_for_quality_profile(DEFAULT_QUALITY_PROFILE))
    return EngineProfileResolution(
        requested_engine_profile=DEFAULT_QUALITY_PROFILE,
        effective_engine_profile="sparrow_v1_noop",
        engine_profile_match=False,
        profile_resolution_source="registry",
        runtime_policy_source="registry",
        profile_effect="noop_non_nesting_backend",
        nesting_engine_runtime_policy=policy,
        nesting_engine_cli_args=[],
    )


def _invocation(backend: str) -> SolverRunnerInvocation:
    module = (
        "vrs_nesting.runner.nesting_engine_runner"
        if backend == ENGINE_BACKEND_NESTING_V2
        else "vrs_nesting.runner.vrs_solver_runner"
    )
    return SolverRunnerInvocation(cmd=["python3", "-m", module], run_dir=None, timeout_s=180, solver_runner_module=module)


def test_resolve_worker_engine_backend_accepts_auto() -> None:
    print("\n[1] _resolve_worker_engine_backend accepts 'auto'")
    result = _resolve_worker_engine_backend("auto")
    _check("returns ENGINE_BACKEND_AUTO constant", result == ENGINE_BACKEND_AUTO)
    _check("value is 'auto'", result == "auto")


def test_explicit_sparrow_v1_not_overridden() -> None:
    print("\n[2] explicit sparrow_v1 — snapshot hint does not override")
    snapshot = _snapshot("nesting_engine_v2")
    res = _resolve_effective_engine_backend(
        requested_engine_backend=ENGINE_BACKEND_SPARROW_V1,
        snapshot_row=snapshot,
    )
    _check("effective backend is sparrow_v1", res.effective_engine_backend == ENGINE_BACKEND_SPARROW_V1)
    _check("source is worker_env_explicit", res.backend_resolution_source == "worker_env_explicit")
    _check("requested is sparrow_v1", res.requested_engine_backend == ENGINE_BACKEND_SPARROW_V1)


def test_explicit_nesting_engine_v2_not_overridden() -> None:
    print("\n[3] explicit nesting_engine_v2 — snapshot hint does not override")
    snapshot = _snapshot("sparrow_v1")
    res = _resolve_effective_engine_backend(
        requested_engine_backend=ENGINE_BACKEND_NESTING_V2,
        snapshot_row=snapshot,
    )
    _check("effective backend is nesting_engine_v2", res.effective_engine_backend == ENGINE_BACKEND_NESTING_V2)
    _check("source is worker_env_explicit", res.backend_resolution_source == "worker_env_explicit")
    _check("requested is nesting_engine_v2", res.requested_engine_backend == ENGINE_BACKEND_NESTING_V2)


def test_auto_with_nesting_engine_v2_hint() -> None:
    print("\n[4] auto + nesting_engine_v2 hint -> effective nesting_engine_v2")
    snapshot = _snapshot("nesting_engine_v2")
    res = _resolve_effective_engine_backend(
        requested_engine_backend=ENGINE_BACKEND_AUTO,
        snapshot_row=snapshot,
    )
    _check("effective backend is nesting_engine_v2", res.effective_engine_backend == ENGINE_BACKEND_NESTING_V2)
    _check("source is snapshot_solver_config", res.backend_resolution_source == "snapshot_solver_config")
    _check("hint captured", res.snapshot_engine_backend_hint == "nesting_engine_v2")
    _check("requested is auto", res.requested_engine_backend == ENGINE_BACKEND_AUTO)


def test_auto_with_sparrow_v1_hint() -> None:
    print("\n[5] auto + sparrow_v1 hint -> effective sparrow_v1")
    snapshot = _snapshot("sparrow_v1")
    res = _resolve_effective_engine_backend(
        requested_engine_backend=ENGINE_BACKEND_AUTO,
        snapshot_row=snapshot,
    )
    _check("effective backend is sparrow_v1", res.effective_engine_backend == ENGINE_BACKEND_SPARROW_V1)
    _check("source is snapshot_solver_config", res.backend_resolution_source == "snapshot_solver_config")
    _check("hint captured", res.snapshot_engine_backend_hint == "sparrow_v1")


def test_auto_with_missing_hint() -> None:
    print("\n[6] auto + missing hint -> fallback sparrow_v1")
    snapshot = _snapshot("__missing_key__")
    res = _resolve_effective_engine_backend(
        requested_engine_backend=ENGINE_BACKEND_AUTO,
        snapshot_row=snapshot,
    )
    _check("effective backend is sparrow_v1", res.effective_engine_backend == ENGINE_BACKEND_SPARROW_V1)
    _check("source is fallback_missing", res.backend_resolution_source == "fallback_missing_snapshot_engine_backend_hint")
    _check("hint is None", res.snapshot_engine_backend_hint is None)


def test_auto_with_invalid_hint() -> None:
    print("\n[7] auto + invalid hint -> fallback sparrow_v1")
    snapshot = _snapshot("unknown_backend_xyz")
    res = _resolve_effective_engine_backend(
        requested_engine_backend=ENGINE_BACKEND_AUTO,
        snapshot_row=snapshot,
    )
    _check("effective backend is sparrow_v1", res.effective_engine_backend == ENGINE_BACKEND_SPARROW_V1)
    _check("source is fallback_invalid", res.backend_resolution_source == "fallback_invalid_snapshot_engine_backend_hint")
    _check("hint captured raw", res.snapshot_engine_backend_hint == "unknown_backend_xyz")


def test_engine_meta_requested_effective_source_fields() -> None:
    print("\n[8] engine_meta payload contains requested/effective/source fields")
    snapshot = {"solver_config_jsonb": {"engine_backend_hint": "nesting_engine_v2"}}
    backend_res = _resolve_effective_engine_backend(
        requested_engine_backend=ENGINE_BACKEND_AUTO,
        snapshot_row=snapshot,
    )
    profile = _profile(backend_res.effective_engine_backend)
    inv = _invocation(backend_res.effective_engine_backend)
    meta = _build_engine_meta_payload(
        backend_resolution=backend_res,
        snapshot_row=snapshot,
        engine_contract_version="nesting_engine_v2",
        profile_resolution=profile,
        invocation=inv,
        solver_input_hash="abc123",
    )
    _check("engine_backend present", "engine_backend" in meta)
    _check("engine_backend is effective", meta["engine_backend"] == "nesting_engine_v2")
    _check("requested_engine_backend present", "requested_engine_backend" in meta)
    _check("requested_engine_backend is auto", meta["requested_engine_backend"] == "auto")
    _check("effective_engine_backend present", "effective_engine_backend" in meta)
    _check("effective_engine_backend is nesting_engine_v2", meta["effective_engine_backend"] == "nesting_engine_v2")
    _check("backend_resolution_source present", "backend_resolution_source" in meta)
    _check("backend_resolution_source is snapshot_solver_config", meta["backend_resolution_source"] == "snapshot_solver_config")
    _check("snapshot_engine_backend_hint present", "snapshot_engine_backend_hint" in meta)
    _check("snapshot_engine_backend_hint value", meta["snapshot_engine_backend_hint"] == "nesting_engine_v2")


def test_engine_meta_strategy_trace_fields() -> None:
    print("\n[9] engine_meta payload contains T2 strategy trace fields")
    snapshot = {
        "solver_config_jsonb": {
            "engine_backend_hint": "sparrow_v1",
            "strategy_profile_version_id": "pvid-abc",
            "strategy_resolution_source": "run_config",
            "strategy_field_sources": {"quality_profile": "run_config_override"},
            "strategy_overrides_applied": ["quality_profile"],
        }
    }
    backend_res = _resolve_effective_engine_backend(
        requested_engine_backend=ENGINE_BACKEND_AUTO,
        snapshot_row=snapshot,
    )
    profile = _profile(backend_res.effective_engine_backend)
    inv = _invocation(backend_res.effective_engine_backend)
    meta = _build_engine_meta_payload(
        backend_resolution=backend_res,
        snapshot_row=snapshot,
        engine_contract_version="v1",
        profile_resolution=profile,
        invocation=inv,
        solver_input_hash="def456",
    )
    _check("strategy_profile_version_id present", "strategy_profile_version_id" in meta)
    _check("strategy_profile_version_id value", meta["strategy_profile_version_id"] == "pvid-abc")
    _check("strategy_resolution_source present", "strategy_resolution_source" in meta)
    _check("strategy_resolution_source value", meta["strategy_resolution_source"] == "run_config")
    _check("strategy_field_sources present", "strategy_field_sources" in meta)
    _check("strategy_field_sources type dict", isinstance(meta["strategy_field_sources"], dict))
    _check("strategy_overrides_applied present", "strategy_overrides_applied" in meta)
    _check("strategy_overrides_applied type list", isinstance(meta["strategy_overrides_applied"], list))


def test_engine_meta_strategy_trace_missing_safe() -> None:
    print("\n[9b] engine_meta strategy trace fields absent when snapshot has no trace")
    snapshot = {"solver_config_jsonb": {"engine_backend_hint": "sparrow_v1"}}
    backend_res = _resolve_effective_engine_backend(
        requested_engine_backend=ENGINE_BACKEND_AUTO,
        snapshot_row=snapshot,
    )
    profile = _profile(backend_res.effective_engine_backend)
    inv = _invocation(backend_res.effective_engine_backend)
    meta = _build_engine_meta_payload(
        backend_resolution=backend_res,
        snapshot_row=snapshot,
        engine_contract_version="v1",
        profile_resolution=profile,
        invocation=inv,
        solver_input_hash="ghi789",
    )
    _check("no crash when trace fields absent", True)
    _check("strategy_profile_version_id absent", "strategy_profile_version_id" not in meta)
    _check("strategy_resolution_source absent", "strategy_resolution_source" not in meta)


def test_nesting_engine_v2_cli_args_non_empty() -> None:
    print("\n[10] nesting_engine_v2 effective backend — CLI args non-empty when policy gives reason")
    profile = _profile(ENGINE_BACKEND_NESTING_V2)
    _check("profile_effect is applied_to_nesting_engine_v2", profile.profile_effect == "applied_to_nesting_engine_v2")
    _check("nesting_engine_cli_args is list", isinstance(profile.nesting_engine_cli_args, list))
    _check("nesting_engine_cli_args non-empty", len(profile.nesting_engine_cli_args) > 0)


def test_sparrow_v1_noop_profile_effect() -> None:
    print("\n[11] sparrow_v1 effective backend — noop profile effect + empty CLI args")
    profile = _profile(ENGINE_BACKEND_SPARROW_V1)
    _check("profile_effect is noop_non_nesting_backend", profile.profile_effect == "noop_non_nesting_backend")
    _check("nesting_engine_cli_args is empty", profile.nesting_engine_cli_args == [])


def main() -> int:
    print("=" * 60)
    print("T3 smoke: worker auto backend resolution + engine_meta audit")
    print("=" * 60)

    tests = [
        test_resolve_worker_engine_backend_accepts_auto,
        test_explicit_sparrow_v1_not_overridden,
        test_explicit_nesting_engine_v2_not_overridden,
        test_auto_with_nesting_engine_v2_hint,
        test_auto_with_sparrow_v1_hint,
        test_auto_with_missing_hint,
        test_auto_with_invalid_hint,
        test_engine_meta_requested_effective_source_fields,
        test_engine_meta_strategy_trace_fields,
        test_engine_meta_strategy_trace_missing_safe,
        test_nesting_engine_v2_cli_args_non_empty,
        test_sparrow_v1_noop_profile_effect,
    ]

    for test_fn in tests:
        try:
            test_fn()
        except Exception:  # noqa: BLE001
            print(f"  ERROR  {test_fn.__name__}")
            traceback.print_exc()
            global FAIL_COUNT
            FAIL_COUNT += 1

    print(f"\n{'=' * 60}")
    print(f"Results: {PASS_COUNT} passed, {FAIL_COUNT} failed")
    if FAIL_COUNT == 0:
        print("PASS")
        return 0
    else:
        print("FAIL")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
