# DXF Nesting Platform Codex Task — New Run Wizard Step2 Strategy T1 backend contract + DB migration + run_config bekotes

TASK_SLUG: new_run_wizard_step2_strategy_t1_backend_contract_runconfig

Olvasd el:

- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `canvases/web_platform/new_run_wizard_step2_strategy_t1_backend_contract_runconfig/new_run_wizard_step2_strategy_t1_backend_contract_runconfig.md`
- `codex/goals/canvases/web_platform/new_run_wizard_step2_strategy_t1_backend_contract_runconfig/fill_canvas_new_run_wizard_step2_strategy_t1_backend_contract_runconfig.yaml`
- `canvases/web_platform/h3_e1_t1_run_strategy_profile_modellek.md`
- `canvases/web_platform/h3_e1_t3_project_level_selectionok.md`
- `canvases/web_platform/h3_quality_t7_quality_profiles_and_run_config_integration.md`
- `api/routes/run_configs.py`
- `api/routes/runs.py`
- `api/services/run_creation.py`
- `api/services/run_snapshot_builder.py`
- `api/services/project_strategy_scoring_selection.py`
- `vrs_nesting/config/nesting_quality_profiles.py`
- `supabase/migrations/20260318103000_h1_e3_t3_security_and_schema_bridge_fixes.sql`
- `supabase/migrations/20260324100000_h3_e1_t1_run_strategy_profile_modellek.sql`
- `supabase/migrations/20260324120000_h3_e1_t3_project_level_selectionok.sql`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

## Nem alkukepes szabalyok

- Csak olyan fajlt hozhatsz letre vagy modosithatsz, amely szerepel valamelyik YAML step `outputs` listajaban.
- Ne talalj ki nem letezo mezoket, endpointokat vagy helperfajlokat. Minden implementacios dontest a valos kodhoz igazits.
- Ez T1 backend contract + DB migration + run_config bekotes. Nem frontend UI, nem worker `auto` backend, nem teljes resolver/precedence task.
- Minden uj request mezo optional legyen; regi run create es run_config create hivasok maradjanak mukodokepesek.
- Ne tarolj titkot, tokent vagy lokalis env erteket.

## Implementacios cel

A New Run Wizard Step2 kesobbi strategy UI-ja backend oldalon kapjon stabil alapot:

1. `app.run_configs` tudjon strategy profile versiont es solver override JSON-t tarolni.
2. `POST /projects/{project_id}/run-configs` validalja, normalizalja, tarolja es visszaadja ezeket.
3. `POST /projects/{project_id}/runs` elfogadja a kesobbi Step2 contract mezoket.
4. `run_config_id` validaltan bekeruljon a `nesting_runs.run_config_id` mezobe.
5. Explicit request override-ok megjelenjenek a snapshot `solver_config_jsonb` truthban.
6. A project strategy selection loader mar teljes strategy config payloadot kerjen le.

## Reszletes kovetelmenyek

### Migration

Hozz letre uj migrationt:

- `supabase/migrations/20260425110000_new_run_wizard_step2_strategy_t1_runconfig_contract.sql`

A vegleges timestampet a repo migracios sorrendjehez igazitsd, de a fajl neve ezt a slugot tartalmazza.

A migration:

- adja hozza az `app.run_configs.run_strategy_profile_version_id` mezot:
  - `uuid null`
  - references `app.run_strategy_profile_versions(id)`
  - `on delete set null`
- adja hozza az `app.run_configs.solver_config_overrides_jsonb` mezot:
  - `jsonb not null default '{}'::jsonb`
- hozzon letre indexet a strategy version id-ra;
- legyen idempotens;
- frissitse a `public.run_configs` view/IUD bridge-et, ha a jelenlegi migration minta alapjan ez szukseges az API/PostgREST mukodeshez.

### Run config API

`api/routes/run_configs.py`:

- `RunConfigCreateRequest` kapja meg:
  - `run_strategy_profile_version_id: UUID | None`
  - `solver_config_overrides_jsonb: dict[str, Any] | None`
- `RunConfigResponse` adja vissza ugyanezeket.
- `create_run_config(...)`:
  - validalja a strategy versiont, ha erkezik;
  - csak az aktualis userhez tartozo, active strategy versiont fogadjon el;
  - normalizalja a solver override JSON-t.
- `list_run_configs(...)` select listaja tartalmazza az uj oszlopokat.

Override whitelist:

- `quality_profile`
- `sa_eval_budget_sec`
- `nesting_engine_runtime_policy`
- `engine_backend_hint`

Validacio:

- `quality_profile`: `normalize_quality_profile_name(...)`
- `nesting_engine_runtime_policy`: `validate_runtime_policy(...)` majd kompakt forma
- `sa_eval_budget_sec`: int, 1..3600
- `engine_backend_hint`: csak `sparrow_v1` vagy `nesting_engine_v2`
- barmilyen mas kulcs: HTTP 400

### Run create API

`api/routes/runs.py`:

- `RunCreateRequest` kapja meg:
  - `run_config_id: UUID | None`
  - `run_strategy_profile_version_id: UUID | None`
  - `quality_profile: str | None`
  - `engine_backend_hint: str | None`
  - `nesting_engine_runtime_policy: dict[str, Any] | None`
- `sa_eval_budget_sec` marad.
- A route adja tovabb ezeket `create_queued_run_from_project_snapshot(...)` fele.

### Run creation service

`api/services/run_creation.py`:

- `create_queued_run_from_project_snapshot(...)` kapja meg az uj optional parametereket.
- Legyen run_config loader/validator:
  - a config id letezik;
  - ugyanahhoz a projecthez tartozik;
  - az aktualis owner/user scope-jaba tartozik.
- `_insert_run(...)` optional `run_config_id`-t kapjon es mentse a run sorba.
- `request_payload_jsonb` audit mezokben szerepeljen:
  - `source`
  - `snapshot_hash_sha256`
  - `run_config_id`
  - `run_strategy_profile_version_id`
  - `quality_profile`
  - `engine_backend_hint`
  - `has_nesting_engine_runtime_policy`
  - `sa_eval_budget_sec`
- Explicit request override-ok menjenek tovabb a snapshot buildernek.
- Ne implementald meg a teljes precedence resolver logikat. Ha `run_config_id` be van adva, T1-ben az elsodleges kotelezo bizonyitek a validalas + run row persistence; a run_config tartalmi precedence a kovetkezo task.

### Snapshot builder

`api/services/run_snapshot_builder.py`:

- fogadjon optional:
  - `quality_profile`
  - `engine_backend_hint`
  - `nesting_engine_runtime_policy`
- validalja ezeket;
- default esetben a jelenlegi kompatibilis default maradjon;
- explicit request eseten a `solver_config_jsonb` mezok normalizaltan valtozzanak:
  - `quality_profile`
  - `engine_backend_hint`
  - `nesting_engine_runtime_policy`
- `sa_eval_budget_sec` tovabbra is mukodjon es a runtime policybe is bekeruljon, ha megadott.

### Project strategy selection loader

`api/services/project_strategy_scoring_selection.py`:

A strategy version select listaba keruljon be:

- `solver_config_jsonb`
- `placement_config_jsonb`
- `manufacturing_bias_jsonb`

Ez T1-ben csak payload-preload elokeszites; a project-level selection fallback resolver nem ennek a tasknak a resze.

## Smoke

Hozd letre:

- `scripts/smoke_new_run_wizard_step2_strategy_t1_backend_contract_runconfig.py`

A smoke valodi Supabase/worker/solver nelkul bizonyitsa legalabb:

- migration tartalmazza az uj oszlopokat es indexet;
- run_config request/response valid mezoket kezel;
- invalid override kulcs 400;
- invalid backend hint 400;
- mas owner vagy inactive strategy version bukik;
- valid strategy version + overrides bekerul az insert payloadba;
- run create request modell elfogadja az uj mezoket;
- run_creation validalja es menti a `run_config_id`-t;
- snapshot builder explicit override-okkal `solver_config_jsonb` truthot ad;
- strategy selection loader select stringje tartalmazza a harom uj JSONB mezot.

## Report

A reportban kulon nevezd meg:

- pontos migration fajl;
- pontos API model/validator valtozasok;
- hogyan tortenik strategy version owner + active check;
- hogyan tortenik override whitelist;
- hogyan kerul a `run_config_id` a run row-ba;
- mely explicit override-ok jelennek meg snapshot truthkent;
- mi marad T2 scope-ban: teljes precedence resolver, run_config tartalmi feloldas, project selection fallback;
- mi marad kesobbi scope-ban: frontend Step2 UI, worker auto backend, engine_meta bovites.

## Kotelezo ellenorzesek

Futtasd:

```bash
python3 -m py_compile \
  api/routes/run_configs.py \
  api/routes/runs.py \
  api/services/run_creation.py \
  api/services/run_snapshot_builder.py \
  api/services/project_strategy_scoring_selection.py \
  scripts/smoke_new_run_wizard_step2_strategy_t1_backend_contract_runconfig.py

python3 scripts/smoke_new_run_wizard_step2_strategy_t1_backend_contract_runconfig.py

./scripts/verify.sh --report codex/reports/web_platform/new_run_wizard_step2_strategy_t1_backend_contract_runconfig.md
```

Eredmeny:

- checklist frissitve;
- report evidence matrixszal;
- AUTO_VERIFY blokk korrektul kitoltve;
- verify log letrejon.
