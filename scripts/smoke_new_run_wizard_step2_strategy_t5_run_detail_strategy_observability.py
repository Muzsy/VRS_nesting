#!/usr/bin/env python3
"""
Offline source-level smoke for T5: Run Detail strategy/engine observability.
No DB, Supabase, worker, solver binary, or frontend node_modules required.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

passed: list[str] = []
failed: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        passed.append(name)
        print(f"  PASS  {name}")
    else:
        failed.append(name)
        print(f"  FAIL  {name}" + (f" — {detail}" if detail else ""))


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. Backend model fields
# ---------------------------------------------------------------------------
print("\n[1] api/routes/runs.py — ViewerDataResponse model fields")
backend_src = read(REPO_ROOT / "api" / "routes" / "runs.py")

T5_MODEL_FIELDS = [
    "requested_engine_backend",
    "effective_engine_backend",
    "backend_resolution_source",
    "snapshot_engine_backend_hint",
    "strategy_profile_version_id",
    "strategy_resolution_source",
    "strategy_field_sources",
    "strategy_overrides_applied",
]
for field in T5_MODEL_FIELDS:
    check(f"backend model field: {field}", f"{field}:" in backend_src or f"{field} :" in backend_src)

# ---------------------------------------------------------------------------
# 2. Backend return block populates new fields from engine_meta_payload
# ---------------------------------------------------------------------------
print("\n[2] api/routes/runs.py — get_viewer_data return populates new fields")

for field in T5_MODEL_FIELDS:
    check(
        f"backend return: {field}",
        f'{field}=' in backend_src or f'{field} =' in backend_src,
    )

check(
    "backend: effective_engine_backend fallback to engine_backend",
    "engine_backend" in backend_src and "effective_engine_backend" in backend_src and "_eff" in backend_src,
)
check(
    "backend: strategy_field_sources dict type check",
    "isinstance(_strategy_field_sources, dict)" in backend_src,
)
check(
    "backend: strategy_overrides_applied list type check",
    "isinstance(_strategy_overrides_applied_raw, list)" in backend_src,
)

# ---------------------------------------------------------------------------
# 3. Frontend types
# ---------------------------------------------------------------------------
print("\n[3] frontend/src/lib/types.ts — ViewerDataResponse interface fields")
frontend_types_src = read(REPO_ROOT / "frontend" / "src" / "lib" / "types.ts")

T5_TS_FIELDS = [
    "engine_backend",
    "engine_contract_version",
    "requested_engine_backend",
    "effective_engine_backend",
    "backend_resolution_source",
    "snapshot_engine_backend_hint",
    "strategy_profile_version_id",
    "strategy_resolution_source",
    "strategy_field_sources",
    "strategy_overrides_applied",
]
for field in T5_TS_FIELDS:
    check(f"frontend type field: {field}", f"{field}?" in frontend_types_src)

# ---------------------------------------------------------------------------
# 4. RunDetailPage: api.getViewerData call
# ---------------------------------------------------------------------------
print("\n[4] frontend/src/pages/RunDetailPage.tsx — api.getViewerData usage")
run_detail_src = read(REPO_ROOT / "frontend" / "src" / "pages" / "RunDetailPage.tsx")

check(
    "RunDetailPage: imports ViewerDataResponse",
    "ViewerDataResponse" in run_detail_src,
)
check(
    "RunDetailPage: calls api.getViewerData",
    "api.getViewerData(" in run_detail_src,
)
check(
    "RunDetailPage: viewer-data error is non-fatal (try/catch inside)",
    "catch" in run_detail_src and "api.getViewerData" in run_detail_src,
)

# ---------------------------------------------------------------------------
# 5. RunDetailPage: Strategy and engine audit UI
# ---------------------------------------------------------------------------
print("\n[5] frontend/src/pages/RunDetailPage.tsx — audit card UI text")

check(
    "RunDetailPage: Strategy and engine audit card text",
    "Strategy and engine audit" in run_detail_src,
)

AUDIT_UI_FIELDS = [
    "requested_engine_backend",
    "effective_engine_backend",
    "backend_resolution_source",
    "snapshot_engine_backend_hint",
    "strategy_profile_version_id",
    "strategy_resolution_source",
    "strategy_overrides_applied",
    "engine_meta",
]
for field in AUDIT_UI_FIELDS:
    check(f"RunDetailPage audit card references: {field}", field in run_detail_src)

check(
    "RunDetailPage: fallback text for missing viewer-data",
    "Not available yet" in run_detail_src,
)

# ---------------------------------------------------------------------------
# 6. Mock API ViewerData interface
# ---------------------------------------------------------------------------
print("\n[6] frontend/e2e/support/mockApi.ts — ViewerData interface fields")
mock_api_src = read(REPO_ROOT / "frontend" / "e2e" / "support" / "mockApi.ts")

MOCK_FIELDS = [
    "requested_engine_backend",
    "effective_engine_backend",
    "backend_resolution_source",
    "snapshot_engine_backend_hint",
    "strategy_profile_version_id",
    "strategy_resolution_source",
    "strategy_field_sources",
    "strategy_overrides_applied",
]
for field in MOCK_FIELDS:
    check(f"mockApi ViewerData interface field: {field}", field in mock_api_src)

# ---------------------------------------------------------------------------
# 7. T5 Playwright spec: required assertion texts
# ---------------------------------------------------------------------------
print("\n[7] frontend/e2e/new_run_wizard_step2_strategy_t5_run_detail_strategy_observability.spec.ts — assertions")
spec_path = (
    REPO_ROOT
    / "frontend"
    / "e2e"
    / "new_run_wizard_step2_strategy_t5_run_detail_strategy_observability.spec.ts"
)
check("T5 spec file exists", spec_path.exists())

if spec_path.exists():
    spec_src = spec_path.read_text(encoding="utf-8")
    T5_SPEC_ASSERTIONS = [
        "Strategy and engine audit",
        "nesting_engine_v2",
        "snapshot_solver_config",
        "version-t5-1",
        "run_config",
        "quality_profile",
        "engine_meta",
        "Not available yet",
    ]
    for assertion in T5_SPEC_ASSERTIONS:
        check(f"T5 spec contains assertion: {assertion!r}", assertion in spec_src)

    check("T5 spec has regression test (no viewer-data fallback)", "regression" in spec_src.lower() or "fallback" in spec_src.lower())

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
total = len(passed) + len(failed)
print(f"\n{'='*60}")
if failed:
    print(f"FAIL: {len(failed)} check(s) failed, {len(passed)} passed ({total} total)")
    for name in failed:
        print(f"  - {name}")
    sys.exit(1)
else:
    print(f"PASS: {len(passed)} checks passed ({total} total)")
    sys.exit(0)
