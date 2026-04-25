# Codex Checklist — new_run_wizard_step2_strategy_t2_resolution_snapshot_precedence

## Felderites

- [x] AGENTS.md elolvasva
- [x] docs/codex/overview.md elolvasva
- [x] docs/codex/yaml_schema.md elolvasva
- [x] docs/codex/report_standard.md elolvasva
- [x] docs/qa/testing_guidelines.md elolvasva
- [x] T1 canvas + report + forrasfajlok elolvasva
- [x] vrs_nesting/config/nesting_quality_profiles.py megertve (helperek: normalize, validate, compact, runtime_policy_for)
- [x] api/services/project_strategy_scoring_selection.py megertve (_load_strategy_version_for_owner mintaja)
- [x] supabase/migrations/20260425110000 T1 migration megertve

## Canvas

- [x] Canvas veglegesitve (scope: csak T2 resolver + snapshot precedence, frontend/worker kizarva)
- [x] Nem-celok explicit jelolve

## Goal YAML

- [x] YAML steps + outputs pontosak
- [x] Outputs szabaly betartva
- [x] Legutolso step: Repo gate

## Implementacio

- [x] `api/services/run_strategy_resolution.py` letrehozva (RunStrategyResolutionError, ResolvedRunStrategy, resolve_run_strategy)
- [x] Precedence sorrend implementalva: request > run_config overrides > profile solver_config > global default
- [x] Profile version betoltes owner scope-pal (owner_user_id check + is_active check ha request)
- [x] Engine backend hint validalas (sparrow_v1, nesting_engine_v2)
- [x] runtime policy validalas (validate_runtime_policy + compact_runtime_policy)
- [x] Trace mezok: strategy_resolution_source, field_sources, overrides_applied, trace_jsonb
- [x] `api/services/run_creation.py` frissitve: resolver hivas snapshot builder elott
- [x] _insert_run frissitve: resolved_strategy alapjan request_payload_jsonb resolution summary
- [x] `api/services/run_snapshot_builder.py` frissitve: 4 uj optional trace param, solver_config_jsonb tartalmazza oket
- [x] Regi hivasi kompatibilitas megmaradt (default None parameterek)

## Smoke

- [x] `scripts/smoke_new_run_wizard_step2_strategy_t2_resolution_snapshot_precedence.py` letrehozva
- [x] 9 teszteset mind PASS (41 assertion)
- [x] FakeSupabaseClient valodi DB/worker/solver nelkul
- [x] Idegen owner version -> 403 elutasitas tesztelve
- [x] Invalid runtime policy -> 400 elutasitas tesztelve

## Verify

- [x] `python3 -m py_compile` mind 4 fajlra PASS
- [x] `python3 scripts/smoke_...t2...py` -> 41/41 PASS
- [x] `./scripts/verify.sh --report ...` futtatva (AUTO_VERIFY blokk a reportban)

## Scope hatarok (nem ebben a taskban)

- [ ] Frontend Step2 UI
- [ ] Worker auto backend (engine_backend_hint=auto)
- [ ] engine_meta.json worker artifact bovites
- [ ] Full UX summary oldal
