# Checklist — New Run Wizard Step2 Strategy T3 Worker auto backend + engine_meta audit

## Felderites + canvas

- [x] AGENTS.md, Codex workflow docs elolvasva
- [x] T1 + T2 canvas + report elolvasva
- [x] worker/main.py, run_strategy_resolution.py, run_creation.py, run_snapshot_builder.py aktualis allapot felderitva
- [x] Canvas T3 scope veglegesitve (worker auto backend resolution + engine_meta audit bovites)

## Implementacio

- [x] `ENGINE_BACKEND_AUTO = "auto"` konstans hozzaadva
- [x] `_SUPPORTED_WORKER_ENGINE_BACKENDS` fogadja az `auto`, `sparrow_v1`, `nesting_engine_v2` ertekeket
- [x] `_SUPPORTED_EFFECTIVE_ENGINE_BACKENDS` konstans letrehozva
- [x] `load_settings` defaultja `WORKER_ENGINE_BACKEND=auto`
- [x] `WorkerEngineBackendResolution` dataclass letrehozva
- [x] `_resolve_effective_engine_backend(...)` helper letrehozva
- [x] explicit env backend eseten snapshot hint nem irja felul
- [x] `auto` + valid hint eseten snapshot hint donti el az effektiv backendet
- [x] missing hint esetn fallback `sparrow_v1`, warning loggal
- [x] invalid hint eseten fallback `sparrow_v1`, warning loggal
- [x] `_process_queue_item` bekotve: backend resolution a snapshot fetch utan fut
- [x] `engine_backend` az effektiv backend erteket hasznaljak a profilhoz + invocatiohoz
- [x] `_build_engine_meta_payload(...)` helper letrehozva
- [x] engine_meta uj mezok: `requested_engine_backend`, `effective_engine_backend`, `backend_resolution_source`, `snapshot_engine_backend_hint`
- [x] engine_meta strategy trace mezok: `strategy_profile_version_id`, `strategy_resolution_source`, `strategy_field_sources`, `strategy_overrides_applied`
- [x] `engine_backend` mezo az effektiv backend erteket kapja (backward compat)
- [x] strategy trace mezok hianyzasakor nincs crash

## Smoke

- [x] `scripts/smoke_new_run_wizard_step2_strategy_t3_worker_auto_backend_engine_meta.py` letrehozva
- [x] smoke nem hasznal Supabase-t, storage-ot, solver binarist
- [x] `_resolve_worker_engine_backend("auto") == "auto"` PASS
- [x] explicit sparrow_v1 — hint nem irja felul (worker_env_explicit) PASS
- [x] explicit nesting_engine_v2 — hint nem irja felul (worker_env_explicit) PASS
- [x] auto + nesting_engine_v2 hint -> effective nesting_engine_v2 (snapshot_solver_config) PASS
- [x] auto + sparrow_v1 hint -> effective sparrow_v1 (snapshot_solver_config) PASS
- [x] auto + missing hint -> fallback sparrow_v1 (fallback_missing_snapshot_engine_backend_hint) PASS
- [x] auto + invalid hint -> fallback sparrow_v1 (fallback_invalid_snapshot_engine_backend_hint) PASS
- [x] engine_meta requested/effective/source mezok PASS
- [x] engine_meta T2 strategy trace mezok PASS
- [x] engine_meta trace mezok hianyzasakor nincs crash PASS
- [x] nesting_engine_v2 agon CLI args nem ures PASS
- [x] sparrow_v1 agon noop profile effect + ures CLI args PASS
- [x] 47/47 assertion PASS

## Report + verify

- [x] report DoD -> Evidence matrix kitoltve
- [x] verify.sh futtatva, AUTO_VERIFY blokk frissitve
- [x] verify.log letrejott
