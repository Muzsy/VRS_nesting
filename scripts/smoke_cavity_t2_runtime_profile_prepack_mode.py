#!/usr/bin/env python3
"""Smoke for cavity T2 runtime policy mapping (no solver execution)."""

from __future__ import annotations

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vrs_nesting.config.nesting_quality_profiles import (  # noqa: E402
    build_nesting_engine_cli_args_from_runtime_policy,
    compact_runtime_policy,
    get_quality_profile_registry,
    runtime_policy_for_quality_profile,
    validate_runtime_policy,
)
import worker.main as worker_main  # noqa: E402


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _settings(temp_root: Path) -> worker_main.WorkerSettings:
    return worker_main.WorkerSettings(
        supabase_url="https://example.supabase.co",
        supabase_project_ref="proj",
        supabase_access_token="token",
        supabase_service_role_key="service",
        storage_bucket="vrs-nesting",
        worker_id="worker-smoke-t2",
        poll_interval_s=0.1,
        retry_delay_s=1,
        alert_backlog_seconds=60,
        run_timeout_extra_s=0,
        run_log_sync_interval_s=1.0,
        queue_heartbeat_s=1.0,
        queue_lease_ttl_s=10,
        stale_temp_cleanup_max_age_s=60.0,
        run_root=temp_root / "runs-root",
        temp_root=temp_root,
        run_artifacts_bucket="run-artifacts",
        sparrow_bin="",
        once=True,
        engine_backend=worker_main.ENGINE_BACKEND_NESTING_V2,
        quality_profile_override=None,
    )


def _assert_registry_and_policy() -> None:
    registry = get_quality_profile_registry()
    _assert("quality_cavity_prepack" in registry, "quality_cavity_prepack profile missing")
    prepack = registry["quality_cavity_prepack"]
    _assert(prepack.get("placer") == "nfp", "quality_cavity_prepack placer mismatch")
    _assert(prepack.get("search") == "sa", "quality_cavity_prepack search mismatch")
    _assert(prepack.get("part_in_part") == "prepack", "quality_cavity_prepack part_in_part mismatch")
    _assert(prepack.get("compaction") == "slide", "quality_cavity_prepack compaction mismatch")

    qd = registry["quality_default"]
    _assert(qd.get("placer") == "nfp", "quality_default placer changed")
    _assert(qd.get("search") == "sa", "quality_default search changed")
    _assert(qd.get("part_in_part") == "auto", "quality_default part_in_part changed")
    _assert(qd.get("compaction") == "slide", "quality_default compaction changed")

    normalized = validate_runtime_policy(
        {
            "placer": "nfp",
            "search": "sa",
            "part_in_part": "prepack",
            "compaction": "slide",
        }
    )
    _assert(normalized.get("part_in_part") == "prepack", "validate_runtime_policy lost prepack policy")
    print("  PASS registry_and_policy")


def _assert_cli_mapping() -> None:
    prepack_policy = compact_runtime_policy(runtime_policy_for_quality_profile("quality_cavity_prepack"))
    prepack_cli = build_nesting_engine_cli_args_from_runtime_policy(prepack_policy)
    joined = " ".join(prepack_cli)
    _assert("--part-in-part off" in joined, "prepack policy must map to --part-in-part off")
    _assert("prepack" not in prepack_cli, "Rust CLI args must not contain prepack")

    default_policy = compact_runtime_policy(runtime_policy_for_quality_profile("quality_default"))
    default_cli = build_nesting_engine_cli_args_from_runtime_policy(default_policy)
    _assert("prepack" not in default_cli, "default policy unexpectedly contains prepack")
    _assert("--part-in-part auto" in " ".join(default_cli), "quality_default CLI part-in-part changed")
    print("  PASS cli_mapping")


def _assert_worker_resolution_trace() -> None:
    with TemporaryDirectory(prefix="smoke_cavity_t2_") as tmp:
        root = Path(tmp)
        settings = _settings(root)
        snapshot_row = {
            "solver_config_jsonb": {
                "quality_profile": "quality_cavity_prepack",
                "nesting_engine_runtime_policy": compact_runtime_policy(
                    runtime_policy_for_quality_profile("quality_cavity_prepack")
                ),
            }
        }
        resolution = worker_main._resolve_engine_profile_resolution(
            snapshot_row=snapshot_row,
            settings=settings,
            engine_backend=worker_main.ENGINE_BACKEND_NESTING_V2,
        )
        _assert(
            resolution.requested_part_in_part_policy == "prepack",
            f"unexpected requested_part_in_part_policy: {resolution.requested_part_in_part_policy}",
        )
        _assert(
            resolution.effective_engine_part_in_part == "off",
            f"unexpected effective_engine_part_in_part: {resolution.effective_engine_part_in_part}",
        )
        _assert(resolution.cavity_prepack_enabled is True, "cavity_prepack_enabled should be true")
        _assert("prepack" not in resolution.nesting_engine_cli_args, "prepack leaked into Rust CLI args")
        _assert(
            "--part-in-part off" in " ".join(resolution.nesting_engine_cli_args),
            "worker resolution must emit --part-in-part off",
        )
    print("  PASS worker_resolution_trace")


def main() -> int:
    _assert_registry_and_policy()
    _assert_cli_mapping()
    _assert_worker_resolution_trace()
    print("[smoke_cavity_t2_runtime_profile_prepack_mode] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
