# DXF Nesting Platform Codex Task — New Run Wizard Step2 Strategy T2 resolver + snapshot precedence

TASK_SLUG: new_run_wizard_step2_strategy_t2_resolution_snapshot_precedence

Olvasd el:

- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `canvases/web_platform/new_run_wizard_step2_strategy_t2_resolution_snapshot_precedence/new_run_wizard_step2_strategy_t2_resolution_snapshot_precedence.md`
- `codex/goals/canvases/web_platform/new_run_wizard_step2_strategy_t2_resolution_snapshot_precedence/fill_canvas_new_run_wizard_step2_strategy_t2_resolution_snapshot_precedence.yaml`
- `canvases/web_platform/new_run_wizard_step2_strategy_t1_backend_contract_runconfig/new_run_wizard_step2_strategy_t1_backend_contract_runconfig.md`
- `codex/reports/web_platform/new_run_wizard_step2_strategy_t1_backend_contract_runconfig.md`
- `api/routes/run_configs.py`
- `api/routes/runs.py`
- `api/services/run_creation.py`
- `api/services/run_snapshot_builder.py`
- `api/services/project_strategy_scoring_selection.py`
- `vrs_nesting/config/nesting_quality_profiles.py`
- `supabase/migrations/20260425110000_new_run_wizard_step2_strategy_t1_runconfig_contract.sql`

Majd hajtsd végre a YAML `steps` lépéseit sorrendben.

## Nem alkuképes szabályok

- Csak olyan fájlt hozhatsz létre vagy módosíthatsz, amely szerepel valamely YAML step `outputs` listájában.
- Ne találj ki nem létező mezőket, endpointokat vagy helperfájlokat. Minden implementációs döntést a valós kódhoz igazíts.
- Ez T2 backend resolver + snapshot precedence task. Nem frontend UI, nem worker `auto` backend, nem `engine_meta.json` worker artifact bővítés.
- Minden új request/trace mező optional-kompatibilis legyen; régi run create hívások továbbra is működjenek.
- Ne tárolj titkot, tokent vagy lokális env értéket.

## Implementációs cél

A T1 után a backend már elfogadja és részben továbbítja a Step2 strategy mezőket, de még nincs valódi precedence feloldás.
Ebben a taskban meg kell valósítani a determinisztikus strategy resolution láncot:

1. explicit run create request mezők
2. `run_config` mezők és `solver_config_overrides_jsonb`
3. `project_run_strategy_selection`
4. global default `quality_default`

A végső truth a snapshot `solver_config_jsonb` mezőbe kerüljön, audit trace-szel együtt.

## Részletes követelmények

### Új resolver service

Hozd létre:

- `api/services/run_strategy_resolution.py`

Legyen benne:

- `RunStrategyResolutionError(status_code: int, detail: str)`
- `ResolvedRunStrategy` dataclass vagy ekvivalens típus
- `resolve_run_strategy(...)` publikus függvény

A resolver:

- töltse be a run_configot, ha `run_config_id` van;
- töltse be a project-level strategy selectiont, ha nincs magasabb precedence profile version;
- töltse be owner scope-pal a választott strategy profile versiont;
- alkalmazza a precedence sorrendet;
- validálja a runtime policyt és backend hintet;
- adjon vissza trace mezőket: `strategy_resolution_source`, `strategy_profile_version_id`, `field_sources`, `overrides_applied`, `trace_jsonb`.

### Precedence

Profile version:

1. `request_run_strategy_profile_version_id`
2. `run_config.run_strategy_profile_version_id`
3. `project_run_strategy_selection.active_run_strategy_profile_version_id`
4. `None`, global default

Solver mezők:

1. explicit request mezők
2. `run_config.solver_config_overrides_jsonb`
3. selected strategy profile version `solver_config_jsonb`
4. global default

Figyelj arra, hogy a profile solver config csak ismert kulcsokat használjon:

- `quality_profile`
- `sa_eval_budget_sec`
- `nesting_engine_runtime_policy`
- `engine_backend_hint`

### Run creation

`api/services/run_creation.py`:

- a snapshot builder előtt hívja a resolvert;
- a snapshot buildernek már resolver output menjen;
- `_insert_run(...)` request payloadja tartalmazza a resolution summaryt;
- a T1 `run_config_id` persistence ne romoljon el;
- az idempotency/snapshot hash dedupe logika maradjon kompatibilis, azzal a tudatos változással, hogy strategy trace/hash változhat.

### Snapshot builder

`api/services/run_snapshot_builder.py`:

- fogadjon optional trace mezőket;
- `solver_config_jsonb` tartalmazza:
  - `quality_profile`
  - `engine_backend_hint`
  - `nesting_engine_runtime_policy`
  - `strategy_profile_version_id`
  - `strategy_resolution_source`
  - `strategy_field_sources`
  - `strategy_overrides_applied`
- régi hívások defaultja maradjon működőképes.

### Smoke

Hozd létre:

- `scripts/smoke_new_run_wizard_step2_strategy_t2_resolution_snapshot_precedence.py`

A smoke bizonyítsa:

- default-only -> `quality_default`, `global_default`;
- project selection fallback -> profile config érvényesül;
- run_config profile -> megelőzi project selectiont;
- run_config override -> megelőzi profile configot;
- explicit request override -> megelőz mindent;
- snapshot trace mezők jelen vannak;
- run request payload summary jelen van;
- idegen owner strategy version bukik;
- invalid runtime policy bukik.

## Kötelező ellenőrzések

Futtasd:

```bash
python3 -m py_compile \
  api/services/run_strategy_resolution.py \
  api/services/run_creation.py \
  api/services/run_snapshot_builder.py \
  scripts/smoke_new_run_wizard_step2_strategy_t2_resolution_snapshot_precedence.py

python3 scripts/smoke_new_run_wizard_step2_strategy_t2_resolution_snapshot_precedence.py

./scripts/verify.sh --report codex/reports/web_platform/new_run_wizard_step2_strategy_t2_resolution_snapshot_precedence.md
```

A végén:

- checklist frissítve;
- report DoD -> Evidence matrixszal;
- AUTO_VERIFY blokk kitöltve;
- verify log létrejött.
