# DXF Nesting Platform Codex Task — New Run Wizard Step2 Strategy T3 worker auto backend + engine_meta

TASK_SLUG: new_run_wizard_step2_strategy_t3_worker_auto_backend_engine_meta

Olvasd el:

- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `canvases/web_platform/new_run_wizard_step2_strategy_t3_worker_auto_backend_engine_meta/new_run_wizard_step2_strategy_t3_worker_auto_backend_engine_meta.md`
- `codex/goals/canvases/web_platform/new_run_wizard_step2_strategy_t3_worker_auto_backend_engine_meta/fill_canvas_new_run_wizard_step2_strategy_t3_worker_auto_backend_engine_meta.yaml`
- `canvases/web_platform/new_run_wizard_step2_strategy_t1_backend_contract_runconfig/new_run_wizard_step2_strategy_t1_backend_contract_runconfig.md`
- `codex/reports/web_platform/new_run_wizard_step2_strategy_t1_backend_contract_runconfig.md`
- `canvases/web_platform/new_run_wizard_step2_strategy_t2_resolution_snapshot_precedence/new_run_wizard_step2_strategy_t2_resolution_snapshot_precedence.md`
- `codex/reports/web_platform/new_run_wizard_step2_strategy_t2_resolution_snapshot_precedence.md`
- `api/services/run_strategy_resolution.py`
- `api/services/run_creation.py`
- `api/services/run_snapshot_builder.py`
- `worker/main.py`
- `vrs_nesting/config/nesting_quality_profiles.py`

Majd hajtsd végre a YAML `steps` lépéseit sorrendben.

## Nem alkuképes szabályok

- Csak olyan fájlt hozhatsz létre vagy módosíthatsz, amely szerepel valamely YAML step `outputs` listájában.
- Ne találj ki nem létező mezőket, endpointokat vagy helperfájlokat. Minden implementációs döntést a valós kódhoz igazíts.
- Ez T3 worker task. Nem frontend UI, nem frontend API kliens, nem DB migration, nem API contract bővítés.
- Az `auto` worker runtime mód, nem solver/runner backend. Runnerhez csak `sparrow_v1` vagy `nesting_engine_v2` juthat el.
- Minden új engine_meta mező additive legyen; meglévő fogyasztókat ne törj el.
- Ne tárolj titkot, tokent vagy lokális env értéket.

## Implementációs cél

A T2 után a snapshot `solver_config_jsonb.engine_backend_hint` már a strategy resolver által feloldott truth. Ebben a taskban a workernek ezt kell ténylegesen használnia `WORKER_ENGINE_BACKEND=auto` módban, és az engine_meta artifactnak auditálhatóan mutatnia kell, hogyan lett a tényleges backend kiválasztva.

A cél backend resolution lánc:

1. Ha `WORKER_ENGINE_BACKEND=sparrow_v1` vagy `nesting_engine_v2`, akkor ez explicit worker env döntés, snapshot hint nem írja felül.
2. Ha `WORKER_ENGINE_BACKEND=auto`, akkor snapshot `solver_config_jsonb.engine_backend_hint` dönt.
3. Ha `auto` módban a snapshot hint hiányzik vagy invalid, fallback `sparrow_v1`, warning loggal.

## Részletes követelmények

### 1. Worker settings contract

`worker/main.py`:

- Add hozzá:
  - `ENGINE_BACKEND_AUTO = "auto"`
  - `_SUPPORTED_WORKER_ENGINE_BACKENDS = ("auto", "sparrow_v1", "nesting_engine_v2")`
- Ha szükséges, különítsd el az effektív backendeket:
  - `_SUPPORTED_EFFECTIVE_ENGINE_BACKENDS = ("sparrow_v1", "nesting_engine_v2")`
- `_resolve_worker_engine_backend(...)` fogadja az `auto` értéket.
- `load_settings(...)` defaultja legyen:
  - `_resolve_env("WORKER_ENGINE_BACKEND", ENGINE_BACKEND_AUTO)`

### 2. Effective backend resolution helper

Hozz létre izolált, smoke-olható helper logikát a `worker/main.py` fájlban.

Javasolt típus:

```python
@dataclass(frozen=True)
class WorkerEngineBackendResolution:
    requested_engine_backend: str
    effective_engine_backend: str
    backend_resolution_source: str
    snapshot_engine_backend_hint: str | None
```

Javasolt függvény:

```python
def _resolve_effective_engine_backend(
    *,
    requested_engine_backend: str,
    snapshot_row: dict[str, Any],
) -> WorkerEngineBackendResolution:
    ...
```

Elvárt viselkedés:

- explicit `sparrow_v1` -> effective `sparrow_v1`, source `worker_env_explicit`;
- explicit `nesting_engine_v2` -> effective `nesting_engine_v2`, source `worker_env_explicit`;
- `auto` + valid snapshot hint -> effective hint, source `snapshot_solver_config`;
- `auto` + missing/empty snapshot hint -> effective `sparrow_v1`, source `fallback_missing_snapshot_engine_backend_hint`, warning log;
- `auto` + invalid snapshot hint -> effective `sparrow_v1`, source `fallback_invalid_snapshot_engine_backend_hint`, warning log.

A snapshot hintet innen olvasd:

```python
solver_config_raw = snapshot_row.get("solver_config_jsonb")
solver_config = solver_config_raw if isinstance(solver_config_raw, dict) else {}
snapshot_hint = str(solver_config.get("engine_backend_hint") or "").strip().lower()
```

### 3. process_run bekötés

`process_run(...)` snapshot fetch után:

- hívd meg a backend resolution helpert;
- a további flow-ban az `effective_engine_backend` értéket használd;
- `_resolve_engine_profile_resolution(...)` az effektív backendet kapja;
- solver input mapping az effektív backend szerint történjen;
- `_build_solver_runner_invocation(...)` az effektív backendet kapja.

Ne változtasd meg a meglévő runner logikát azon túl, hogy az effektív backend alapján kap ágat.

### 4. engine_meta payload

A jelenlegi engine_meta payload maradjon kompatibilis, de bővüljön.

Kötelező meglévő mezők megtartása:

- `engine_backend`
- `engine_contract_version`
- `engine_profile`
- `requested_engine_profile`
- `effective_engine_profile`
- `engine_profile_match`
- `profile_resolution_source`
- `runtime_policy_source`
- `profile_effect`
- `nesting_engine_runtime_policy`
- `nesting_engine_cli_args`
- `solver_runner_module`
- `solver_input_hash`

Új mezők:

- `requested_engine_backend`
- `effective_engine_backend`
- `backend_resolution_source`
- `snapshot_engine_backend_hint`
- `strategy_profile_version_id`
- `strategy_resolution_source`
- `strategy_field_sources`
- `strategy_overrides_applied`

Kompatibilitás:

- `engine_backend` az effektív backend értékét kapja.
- Új fogyasztók `effective_engine_backend` mezőt használhatnak.
- A strategy trace mezők hiánya ne okozzon crasht régi snapshotoknál.

Ha a jelenlegi inline engine_meta összeállítás nehezen tesztelhető, hozz létre egy kis helperfüggvényt, például:

```python
def _build_engine_meta_payload(
    *,
    backend_resolution: WorkerEngineBackendResolution,
    snapshot_row: dict[str, Any],
    engine_contract_version: str,
    profile_resolution: EngineProfileResolution,
    invocation: SolverRunnerInvocation,
    solver_input_hash: str,
) -> dict[str, Any]:
    ...
```

A `process_run(...)` ezt a helpert használja.

### 5. Profile effect és CLI args regresszióvédelem

Ne romoljon el:

- `nesting_engine_v2` effective backend esetén:
  - `_resolve_engine_profile_resolution(...)` építse a `nesting_engine_cli_args` listát a runtime policyból;
  - `profile_effect = "applied_to_nesting_engine_v2"`.
- `sparrow_v1` effective backend esetén:
  - `nesting_engine_cli_args == []`;
  - `profile_effect = "noop_non_nesting_backend"`.

### 6. Smoke

Hozd létre:

- `scripts/smoke_new_run_wizard_step2_strategy_t3_worker_auto_backend_engine_meta.py`

A smoke ne indítson workert, ne használjon Supabase-t, ne futtasson solvert.

Minimum bizonyítás:

- `_resolve_worker_engine_backend("auto") == "auto"`;
- explicit `sparrow_v1` env mód nem engedi a snapshot hint felülírást;
- explicit `nesting_engine_v2` env mód nem engedi a snapshot hint felülírást;
- `auto` + snapshot `nesting_engine_v2` hint -> effective `nesting_engine_v2`;
- `auto` + snapshot `sparrow_v1` hint -> effective `sparrow_v1`;
- `auto` + missing hint -> fallback `sparrow_v1`;
- `auto` + invalid hint -> fallback `sparrow_v1`;
- engine_meta payload tartalmazza requested/effective/source mezőket;
- engine_meta payload tartalmazza strategy trace mezőket;
- `nesting_engine_v2` effective backendnél CLI args nem üres, ha a runtime policy erre okot ad;
- `sparrow_v1` effective backendnél CLI args üres és profile effect noop.

A smoke egyértelműen írja ki:

- PASS esetén `PASS`;
- FAIL esetén nem nulla exit code.

## Kötelező ellenőrzések

Futtasd:

```bash
python3 -m py_compile \
  worker/main.py \
  scripts/smoke_new_run_wizard_step2_strategy_t3_worker_auto_backend_engine_meta.py

python3 scripts/smoke_new_run_wizard_step2_strategy_t3_worker_auto_backend_engine_meta.py

./scripts/verify.sh --report codex/reports/web_platform/new_run_wizard_step2_strategy_t3_worker_auto_backend_engine_meta.md
```

A végén:

- checklist létrehozva/frissítve;
- report DoD -> Evidence matrixszal;
- T3 smoke eredmény szerepel;
- AUTO_VERIFY blokk kitöltve;
- verify log létrejött;
- a report jelölje, hogy a következő scope a frontend Step2 UI + API client submit flow.
