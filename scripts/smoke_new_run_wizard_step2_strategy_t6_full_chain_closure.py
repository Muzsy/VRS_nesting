#!/usr/bin/env python3
"""
Offline source-level closure smoke for T6: Full-chain New Run Wizard Step2 strategy.
Validates T1–T6 critical contracts. No DB, Supabase, worker, solver binary, or node_modules required.
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
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. T1 — migration + run_configs API + runs API contract
# ---------------------------------------------------------------------------
print("\n[1] T1 — DB migration and backend contract")

migration_path = REPO_ROOT / "supabase" / "migrations" / "20260425110000_new_run_wizard_step2_strategy_t1_runconfig_contract.sql"
check("T1 migration file exists", migration_path.exists())
if migration_path.exists():
    mig = migration_path.read_text(encoding="utf-8")
    check("T1 migration: run_strategy_profile_version_id column", "run_strategy_profile_version_id" in mig)
    check("T1 migration: solver_config_overrides_jsonb column", "solver_config_overrides_jsonb" in mig)

run_configs_src = read(REPO_ROOT / "api" / "routes" / "run_configs.py")
check("run_configs.py: run_strategy_profile_version_id field", "run_strategy_profile_version_id" in run_configs_src)
check("run_configs.py: solver_config_overrides_jsonb field", "solver_config_overrides_jsonb" in run_configs_src)
check("run_configs.py: _ALLOWED_SOLVER_OVERRIDE_KEYS whitelist", "_ALLOWED_SOLVER_OVERRIDE_KEYS" in run_configs_src)
check("run_configs.py: engine_backend_hint in whitelist", "engine_backend_hint" in run_configs_src)

runs_src = read(REPO_ROOT / "api" / "routes" / "runs.py")
check("runs.py: RunCreateRequest run_config_id field", "run_config_id" in runs_src)
check("runs.py: RunCreateRequest run_strategy_profile_version_id", "run_strategy_profile_version_id" in runs_src)
check("runs.py: RunCreateRequest quality_profile field", "quality_profile" in runs_src)
check("runs.py: RunCreateRequest engine_backend_hint field", "engine_backend_hint" in runs_src)

# ---------------------------------------------------------------------------
# 2. T2 — resolver + snapshot precedence + run_creation + snapshot_builder
# ---------------------------------------------------------------------------
print("\n[2] T2 — Strategy resolver, run_creation, snapshot_builder")

resolver_path = REPO_ROOT / "api" / "services" / "run_strategy_resolution.py"
check("run_strategy_resolution.py exists", resolver_path.exists())
if resolver_path.exists():
    resolver_src = resolver_path.read_text(encoding="utf-8")
    check("resolver: ResolvedRunStrategy dataclass", "ResolvedRunStrategy" in resolver_src)
    check("resolver: precedence source — request", "request" in resolver_src)
    check("resolver: precedence source — run_config", "run_config" in resolver_src)
    check("resolver: precedence source — project_selection or project", "project" in resolver_src)
    check("resolver: global_default fallback", "global_default" in resolver_src)

creation_src = read(REPO_ROOT / "api" / "services" / "run_creation.py")
check("run_creation.py: calls resolve_run_strategy", "resolve_run_strategy(" in creation_src)
check("run_creation.py: passes strategy_profile_version_id to snapshot builder", "strategy_profile_version_id" in creation_src)
check("run_creation.py: passes strategy_resolution_source to snapshot builder", "strategy_resolution_source" in creation_src)

snapshot_src = read(REPO_ROOT / "api" / "services" / "run_snapshot_builder.py")
check("run_snapshot_builder.py: strategy_profile_version_id param", "strategy_profile_version_id" in snapshot_src)
check("run_snapshot_builder.py: strategy_resolution_source param", "strategy_resolution_source" in snapshot_src)
check("run_snapshot_builder.py: strategy_field_sources param", "strategy_field_sources" in snapshot_src)
check("run_snapshot_builder.py: strategy_overrides_applied param", "strategy_overrides_applied" in snapshot_src)

# ---------------------------------------------------------------------------
# 3. T3 — Worker auto backend + engine_meta audit fields
# ---------------------------------------------------------------------------
print("\n[3] T3 — Worker auto backend resolution + engine_meta audit")

worker_src = read(REPO_ROOT / "worker" / "main.py")
check("worker: ENGINE_BACKEND_AUTO constant", "ENGINE_BACKEND_AUTO" in worker_src or '"auto"' in worker_src)
check("worker: WORKER_ENGINE_BACKEND env support", "WORKER_ENGINE_BACKEND" in worker_src)
check("worker: engine_backend_hint from snapshot", "engine_backend_hint" in worker_src)
check("worker: _build_engine_meta_payload function", "_build_engine_meta_payload" in worker_src)
check("worker: requested_engine_backend in engine_meta", "requested_engine_backend" in worker_src)
check("worker: effective_engine_backend in engine_meta", "effective_engine_backend" in worker_src)
check("worker: backend_resolution_source in engine_meta", "backend_resolution_source" in worker_src)
check("worker: strategy_profile_version_id in engine_meta", "strategy_profile_version_id" in worker_src)
check("worker: strategy_resolution_source in engine_meta", "strategy_resolution_source" in worker_src)
check("worker: strategy_overrides_applied in engine_meta", "strategy_overrides_applied" in worker_src)

# ---------------------------------------------------------------------------
# 4. T4 — Frontend submit-flow
# ---------------------------------------------------------------------------
print("\n[4] T4 — Frontend NewRunPage submit-flow")

new_run_src = read(REPO_ROOT / "frontend" / "src" / "pages" / "NewRunPage.tsx")
check("NewRunPage: calls createRunConfig", "createRunConfig(" in new_run_src)
check("NewRunPage: calls createRun", "createRun(" in new_run_src)
check("NewRunPage: run_config_id forwarded to createRun", "run_config_id" in new_run_src)
check("NewRunPage: run_strategy_profile_version_id in payload", "run_strategy_profile_version_id" in new_run_src)
check("NewRunPage: quality_profile in payload", "quality_profile" in new_run_src)
check("NewRunPage: engine_backend_hint in payload", "engine_backend_hint" in new_run_src)
check("NewRunPage: solver_config_overrides_jsonb in payload", "solver_config_overrides_jsonb" in new_run_src)

t4_spec = REPO_ROOT / "frontend" / "e2e" / "new_run_wizard_step2_strategy_t4.spec.ts"
check("T4 Playwright spec exists", t4_spec.exists())

# ---------------------------------------------------------------------------
# 5. T5 — viewer-data observability + RunDetailPage audit card
# ---------------------------------------------------------------------------
print("\n[5] T5 — viewer-data observability + RunDetailPage audit card")

check("runs.py: ViewerDataResponse effective_engine_backend field", "effective_engine_backend" in runs_src)
check("runs.py: ViewerDataResponse backend_resolution_source field", "backend_resolution_source" in runs_src)
check("runs.py: ViewerDataResponse strategy_profile_version_id field", "strategy_profile_version_id" in runs_src)
check("runs.py: ViewerDataResponse strategy_overrides_applied field", "strategy_overrides_applied" in runs_src)

run_detail_src = read(REPO_ROOT / "frontend" / "src" / "pages" / "RunDetailPage.tsx")
check("RunDetailPage: calls api.getViewerData", "api.getViewerData(" in run_detail_src)
check("RunDetailPage: viewer-data non-fatal (try/catch)", "catch" in run_detail_src and "api.getViewerData" in run_detail_src)
check('RunDetailPage: "Strategy and engine audit" text', "Strategy and engine audit" in run_detail_src)
check("RunDetailPage: fallback Not available yet", "Not available yet" in run_detail_src)

t5_spec = REPO_ROOT / "frontend" / "e2e" / "new_run_wizard_step2_strategy_t5_run_detail_strategy_observability.spec.ts"
check("T5 Playwright spec exists", t5_spec.exists())

# ---------------------------------------------------------------------------
# 6. T6 artefaktok — E2E spec + rollout doc
# ---------------------------------------------------------------------------
print("\n[6] T6 — E2E spec + rollout doc")

t6_spec = REPO_ROOT / "frontend" / "e2e" / "new_run_wizard_step2_strategy_t6_full_chain_closure.spec.ts"
check("T6 Playwright spec exists", t6_spec.exists())
if t6_spec.exists():
    t6_src = t6_spec.read_text(encoding="utf-8")
    check("T6 spec: runConfigBodies assert", "runConfigBodies" in t6_src)
    check("T6 spec: runCreateBodies assert", "runCreateBodies" in t6_src)
    check("T6 spec: run_config_id assert", "run_config_id" in t6_src)
    check("T6 spec: quality_aggressive assert", "quality_aggressive" in t6_src)
    check("T6 spec: nesting_engine_v2 assert", "nesting_engine_v2" in t6_src)
    check("T6 spec: Strategy and engine audit assert", "Strategy and engine audit" in t6_src)
    check("T6 spec: strategy_profile_version_id / VERSION_ID assert", "VERSION_ID" in t6_src or "version-t6-1" in t6_src)
    check("T6 spec: snapshot_solver_config or backend resolution source assert", "snapshot_solver_config" in t6_src)

rollout_doc = REPO_ROOT / "docs" / "web_platform" / "architecture" / "new_run_wizard_step2_strategy_rollout_and_compatibility_plan.md"
check("T6 rollout doc exists", rollout_doc.exists())
if rollout_doc.exists():
    rdoc = rollout_doc.read_text(encoding="utf-8")
    check("rollout doc: deploy order section", "Deploy Order" in rdoc or "Deploy" in rdoc)
    check("rollout doc: compatibility section", "Compatibility" in rdoc or "compatibility" in rdoc)
    check("rollout doc: rollback strategy section", "Rollback" in rdoc)
    check("rollout doc: known limitations section", "Known Limitation" in rdoc or "known limitation" in rdoc.lower())
    check("rollout doc: WORKER_ENGINE_BACKEND=auto", "WORKER_ENGINE_BACKEND" in rdoc)
    check("rollout doc: sparrow_v1 fallback", "sparrow_v1" in rdoc)

# ---------------------------------------------------------------------------
# 7. Artefakt-fegyelem — T1–T6 saját alkönyvtár, nincs gyökérszintű duplikátum
# ---------------------------------------------------------------------------
print("\n[7] Artefakt-fegyelem — T1–T6 struktúra, nincs root-level duplikátum")

SLUGS = [
    "new_run_wizard_step2_strategy_t1_backend_contract_runconfig",
    "new_run_wizard_step2_strategy_t2_resolution_snapshot_precedence",
    "new_run_wizard_step2_strategy_t3_worker_auto_backend_engine_meta",
    "new_run_wizard_step2_strategy_t4_frontend_step2_api_submit_flow",
    "new_run_wizard_step2_strategy_t5_run_detail_strategy_observability",
    "new_run_wizard_step2_strategy_t6_rollout_closure_regression",
]

for slug in SLUGS:
    canvas_dir = REPO_ROOT / "canvases" / "web_platform" / slug
    check(f"canvas dir exists: {slug[:50]}", canvas_dir.is_dir())
    yaml_dir = REPO_ROOT / "codex" / "goals" / "canvases" / "web_platform" / slug
    check(f"goal yaml dir exists: {slug[:50]}", yaml_dir.is_dir())

# Check no root-level canvas/yaml duplicates
canvas_root = REPO_ROOT / "canvases" / "web_platform"
if canvas_root.exists():
    root_md_files = list(canvas_root.glob("new_run_wizard_step2_strategy_t*.md"))
    check("no root-level canvas .md duplicates", len(root_md_files) == 0,
          f"found: {[f.name for f in root_md_files]}")

goals_root = REPO_ROOT / "codex" / "goals" / "canvases" / "web_platform"
if goals_root.exists():
    root_yaml_files = list(goals_root.glob("new_run_wizard_step2_strategy_t*.yaml"))
    check("no root-level goal yaml duplicates", len(root_yaml_files) == 0,
          f"found: {[f.name for f in root_yaml_files]}")

# Check T1–T5 reports exist
for task_slug in SLUGS[:5]:
    report = REPO_ROOT / "codex" / "reports" / "web_platform" / f"{task_slug}.md"
    check(f"T1–T5 report exists: {task_slug[-30:]}", report.exists())

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
