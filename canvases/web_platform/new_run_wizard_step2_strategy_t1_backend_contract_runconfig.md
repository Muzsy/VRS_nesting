# New Run Wizard Step2 Strategy — T1 Backend contract + DB migration + run_config strategy bekotes

## Funkcio

Ez a task a `New Run Wizard Step2 — Nesting Strategia + Beallitasok` fejlesztes elso, backend-alapozo lepese.
Celja, hogy a Step2-ben kesobb valaszthato strategia es finomhangolasi mezok backend oldalon mar stabil contractot kapjanak:

- a `run_configs` perzisztensen tudjon strategy profile versiont es solver override-okat tarolni;
- a `POST /projects/{project_id}/run-configs` API validalja es visszaadja ezeket;
- a `POST /projects/{project_id}/runs` API elfogadja a kesobbi Step2 mezoket, kulonosen a `run_config_id`-t;
- a run creation service ellenorizze a `run_config_id` ownership/project scope-jat, es a run sorba tenylegesen mentse a `run_config_id`-t;
- a snapshot builder legalabb a request-szintu explicit quality/runtime/backend mezoket fogadni tudja, anelkul hogy a teljes strategy precedence resolver megvalosulna.

Ez a T1 nem UI es nem worker rollout. Ez contract + schema + minimal backend bekotes, amelyre a kovetkezo T2 resolver/snapshot precedence task epul.

## Kiindulo valos repo-allapot

A task indulasakor a valos kod alapjan:

- `api/routes/run_configs.py`
  - `RunConfigCreateRequest` jelenleg csak `name`, `schema_version`, `seed`, `time_limit_s`, `spacing_mm`, `margin_mm`, `stock_file_id`, `parts_config` mezoket kezel;
  - a response/list select sem tartalmaz strategy mezoket;
  - van project owner check, file scope check es rotation validation.
- `api/routes/runs.py`
  - `RunCreateRequest` jelenleg csak `idempotency_key`, `run_purpose`, `time_limit_s`, `sa_eval_budget_sec` mezoket fogad;
  - `RunResponse` mar tartalmaz `run_config_id` mezot, de a create flow nem adja tovabb.
- `api/services/run_creation.py`
  - `create_queued_run_from_project_snapshot(...)` jelenleg nem kap `run_config_id`-t;
  - `_insert_run(...)` nem allit `run_config_id`-t;
  - nincs run_config ownership/project validation;
  - snapshot buildernek csak `time_limit_s` es `sa_eval_budget_sec` megy at.
- `api/services/run_snapshot_builder.py`
  - mar tartalmaz quality profile registry integraciot;
  - `solver_config_jsonb` jelenleg explicit `quality_profile`, `engine_backend_hint`, `nesting_engine_runtime_policy` mezoket ir;
  - `engine_backend_hint` jelenleg fixen `nesting_engine_v2`;
  - nincs run_config/request override precedence.
- `vrs_nesting/config/nesting_quality_profiles.py`
  - mar letezik kanonikus quality profile registry;
  - hasznalhato helper: `normalize_quality_profile_name`, `validate_runtime_policy`, `compact_runtime_policy`, `runtime_policy_for_quality_profile`.
- `api/services/project_strategy_scoring_selection.py`
  - project-level strategy selection mar letezik;
  - `_load_strategy_version_for_owner(...)` jelenleg csak meta mezoket selectel: `id,run_strategy_profile_id,owner_user_id,version_no,lifecycle,is_active`.
- DB migraciok:
  - `app.run_strategy_profiles` es `app.run_strategy_profile_versions` mar letezik;
  - `app.project_run_strategy_selection` mar letezik;
  - `app.run_configs` letezik, de nincs `run_strategy_profile_version_id` es `solver_config_overrides_jsonb`;
  - `app.nesting_runs` oldalon `run_config_id` mar a kod response modellje szerint letezo contract, de create oldalon nincs hasznalva.

## Scope

### Benne van

1. Uj Supabase migration:
   - `app.run_configs.run_strategy_profile_version_id uuid null references app.run_strategy_profile_versions(id) on delete set null`
   - `app.run_configs.solver_config_overrides_jsonb jsonb not null default '{}'::jsonb`
   - index a strategy version id-ra;
   - ha a repo public view/IUD bridge mintai alapjan szukseges, `public.run_configs` view es `public.run_configs_view_iud()` frissitese is, hogy az uj mezok ne akadjanak el a PostgREST bridge-en.

2. `api/routes/run_configs.py` bovites:
   - request mezok:
     - `run_strategy_profile_version_id: UUID | None`
     - `solver_config_overrides_jsonb: dict[str, Any] | None`
   - response mezok ugyanilyen tartalommal;
   - create es list select payload frissitese;
   - strategy version owner + active check;
   - strict override whitelist es runtime policy validation.

3. `api/routes/runs.py` backend contract bovites:
   - request mezok:
     - `run_config_id: UUID | None`
     - `run_strategy_profile_version_id: UUID | None`
     - `quality_profile: str | None`
     - `engine_backend_hint: str | None`
     - `nesting_engine_runtime_policy: dict[str, Any] | None`
   - `sa_eval_budget_sec` marad;
   - a route tovabbadja ezeket a service fele.

4. `api/services/run_creation.py` minimal bekotes:
   - `run_config_id` project/owner scope validation;
   - ha `run_config_id` megadott, a run sor `run_config_id` mezobe keruljon;
   - request payload JSONB-ben audit-olhatoan jelenjen meg, hogy milyen contract mezok erkeztek;
   - explicit request mezok tovabbitasa snapshot builder fele.

5. `api/services/run_snapshot_builder.py` minimal contract bovites:
   - fogadjon explicit `quality_profile`, `engine_backend_hint`, `nesting_engine_runtime_policy` inputokat;
   - validalja oket a letezo quality profile/runtime policy helperrel;
   - explicit request override eseten a snapshot `solver_config_jsonb` mar tartalmazza az override truthot;
   - full precedence logika meg nem itt keszul el, csak a request contract bekotese.

6. `api/services/project_strategy_scoring_selection.py` loader bovites:
   - a strategy version select tartalmazza:
     - `solver_config_jsonb`
     - `placement_config_jsonb`
     - `manufacturing_bias_jsonb`
   - ez elokesziti a Step2 default preloadot es a kesobbi resolver taskot.

7. Dedikalt smoke script:
   - `scripts/smoke_new_run_wizard_step2_strategy_t1_backend_contract_runconfig.py`
   - valodi Supabase nelkul, fake clienttel bizonyitsa a contractot.

### Nincs benne

- Frontend Step2 UI;
- frontend API kliens bovites;
- worker `auto` backend resolution;
- teljes strategy resolver service es precedence sorrend;
- project-level selection fallback bekotese a run create snapshotba;
- `engine_meta.json` bovites;
- algoritmus tuning.

## Contract reszletek

### Engedelyezett `solver_config_overrides_jsonb` kulcsok

A T1-ben csak ezek engedelyezettek:

- `quality_profile`
- `sa_eval_budget_sec`
- `nesting_engine_runtime_policy`
- `engine_backend_hint`

Minden mas kulcs `400` hibaval bukjon.

### `quality_profile`

Validalas:

- hasznalja a mar letezo `normalize_quality_profile_name(...)` helpert;
- ervenyes nevek a registry szerint: `fast_preview`, `quality_default`, `quality_aggressive`.

### `engine_backend_hint`

T1-ben engedelyezett ertekek:

- `sparrow_v1`
- `nesting_engine_v2`

Az `auto` worker mode csak kesobbi worker taskban jon, ezert T1-ben meg ne legyen elfogadott request/backend hint ertek.

### `nesting_engine_runtime_policy`

Validalas:

- hasznalja a mar letezo `validate_runtime_policy(...)` / `compact_runtime_policy(...)` helper logikat;
- csak dictionary lehet;
- a validalt/kompaktalt forma keruljon tarolasra/tovabbitasra.

### `sa_eval_budget_sec`

Validalas:

- integer;
- `1..3600` tartomany;
- osszhangban a mar letezo `RunCreateRequest.sa_eval_budget_sec` tartomannyal.

## Implementacios elvarasok

### 1. Migration

Uj migration fajl nevkonvencio szerint, pelda:

`supabase/migrations/20260425xxxxxx_new_run_wizard_step2_strategy_t1_runconfig_contract.sql`

Kovetelmenyek:

- legyen idempotens, `if not exists` / catalog guard mintakkal;
- ne toroljon adatot;
- ne tegye kotelezove az uj strategy version mezot;
- a default override JSON legyen `{}`;
- tartalmazzon indexet;
- ha a `public.run_configs` view/IUD bridge a jelenlegi repo szerint explicit column listat hasznal, azt is frissitse.

### 2. Run config API

`api/routes/run_configs.py` bovuljon ugy, hogy:

- create request elfogadja az uj mezoket;
- ha `run_strategy_profile_version_id` erkezik:
  - ellenorizze, hogy a verzio letezik;
  - `owner_user_id == user.id`;
  - `is_active == true`;
- `solver_config_overrides_jsonb` legyen normalizalva;
- insert payload tarolja az uj mezoket;
- response es list endpoint visszaadja az uj mezoket;
- hibak legyenek felhasznalhatoak es ne nyeljek el a validacios okot.

### 3. Run create API

`api/routes/runs.py` bovuljon ugy, hogy:

- `RunCreateRequest` tartalmazza a T1 mezoket;
- a route tovabbadja oket `create_queued_run_from_project_snapshot(...)` fele;
- visszafele kompatibilis maradjon: ures request tovabbra is mukodik.

### 4. Run creation service

`api/services/run_creation.py` bovuljon ugy, hogy:

- legyen helper a `run_config_id` betoltesere es validalasara:
  - `app.run_configs.id == run_config_id`
  - `project_id == current project`
  - `created_by == owner_user_id` vagy a repo meglovo owner-logikajahoz illeszkedo ekvivalens;
- `_insert_run(...)` kapjon optional `run_config_id`-t es mentse a run row-ba;
- `request_payload_jsonb` tartalmazza legalabb:
  - `source`
  - `snapshot_hash_sha256`
  - `run_config_id`
  - `run_strategy_profile_version_id`
  - `quality_profile`
  - `engine_backend_hint`
  - `has_nesting_engine_runtime_policy`
  - `sa_eval_budget_sec`
- explicit request mezok menjenek at a snapshot buildernek.

### 5. Snapshot builder minimal override support

`api/services/run_snapshot_builder.py` bovuljon optional parameterekkel:

- `quality_profile`
- `engine_backend_hint`
- `nesting_engine_runtime_policy`

Elvart mukodes:

- default viselkedes maradjon kompatibilis;
- explicit `quality_profile` normalizalt formaban keruljon `solver_config_jsonb.quality_profile` mezobe;
- explicit `engine_backend_hint` validalt formaban keruljon `solver_config_jsonb.engine_backend_hint` mezobe;
- explicit `nesting_engine_runtime_policy` compact/validalt formaban keruljon `solver_config_jsonb.nesting_engine_runtime_policy` mezobe;
- `sa_eval_budget_sec` tovabbra is felulirhatja/kitoltheti a runtime policy budget mezot;
- ha validacio hibazik, determinisztikus `RunSnapshotBuilderError(400, ...)` legyen.

## Smoke kovetelmeny

Hozz letre:

`scripts/smoke_new_run_wizard_step2_strategy_t1_backend_contract_runconfig.py`

Minimum bizonyitsa:

1. migration fajl tartalmazza az uj `app.run_configs` oszlopokat es indexet;
2. run_config request/response modell elfogadja es visszaadja az uj mezoket;
3. invalid override kulcs 400-as validacios hibara vezet;
4. invalid engine backend hint bukik;
5. inactive vagy mas ownerhez tartozo strategy version bukik;
6. valid strategy version + overrides bekerul az insert payloadba;
7. run create request modell elfogadja a T1 mezoket;
8. `run_creation` validalja es elmenti a `run_config_id`-t;
9. snapshot builder explicit request override-okkal frissiti a `solver_config_jsonb` truthot;
10. project strategy selection loader select listaja tartalmazza a harom uj JSONB strategy config mezot.

A smoke ne igenyeljen valodi Supabase-t, worker processt vagy Rust solvert.

## Erintett fajlok / celzott outputok

- `canvases/web_platform/new_run_wizard_step2_strategy_t1_backend_contract_runconfig/new_run_wizard_step2_strategy_t1_backend_contract_runconfig.md`
- `codex/goals/canvases/web_platform/new_run_wizard_step2_strategy_t1_backend_contract_runconfig/fill_canvas_new_run_wizard_step2_strategy_t1_backend_contract_runconfig.yaml`
- `codex/prompts/web_platform/new_run_wizard_step2_strategy_t1_backend_contract_runconfig/run.md`
- `supabase/migrations/20260425xxxxxx_new_run_wizard_step2_strategy_t1_runconfig_contract.sql`
- `api/routes/run_configs.py`
- `api/routes/runs.py`
- `api/services/run_creation.py`
- `api/services/run_snapshot_builder.py`
- `api/services/project_strategy_scoring_selection.py`
- `scripts/smoke_new_run_wizard_step2_strategy_t1_backend_contract_runconfig.py`
- `codex/codex_checklist/web_platform/new_run_wizard_step2_strategy_t1_backend_contract_runconfig.md`
- `codex/reports/web_platform/new_run_wizard_step2_strategy_t1_backend_contract_runconfig.md`

## DoD

A task akkor kesz, ha:

- DB migration boviti a `run_configs` strategia mezokkel, visszafele kompatibilisen;
- `POST /run-configs` tarolja es visszaadja a strategy profile version + solver override mezoket;
- override whitelist es runtime policy validation mukodik;
- `POST /runs` elfogadja a T1 backend contract mezoket;
- `run_config_id` project/owner scoped, validalt es bekerul a `nesting_runs.run_config_id` mezobe;
- explicit request override-ok megjelennek a snapshot `solver_config_jsonb` mezoben;
- project strategy selection loader mar a teljes strategy config JSONB payloadot is betolti;
- dedikalt smoke PASS;
- standard verify PASS es report frissul.

## Kockazat + rollback

### Kockazatok

- A `public.run_configs` view/IUD bridge kimarad, emiatt PostgREST vagy API insert/list elterhet.
- A snapshot hash valtozhat, ha uj explicit override mezok bekerulnek a solver configba.
- A T1 tul sok resolver logikat probalna megoldani, es osszekeverne a kovetkezo T2 scope-javal.

### Mitigacio

- Migrationben kovetni kell a 20260318103000 bridge mintajat.
- Csak explicit request override valtoztassa a snapshot truthot; default futas maradjon kompatibilis.
- A teljes precedence sorrendet csak dokumentalni kell T2 bemenetkent, nem itt implementalni.

### Rollback

- A migration additive: oszlopok nullable/defaultosak, igy alkalmazas szinten visszagorditheto a kodmodositas.
- A route/service bovites optional mezokkel tortenik, regi kliensek mukodeset nem tori.

## Tesztallapot

Kotelezo:

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

A reportban legyen DoD -> Evidence matrix es AUTO_VERIFY blokk.

## Kapcsolodasok

- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `canvases/web_platform/h3_e1_t1_run_strategy_profile_modellek.md`
- `canvases/web_platform/h3_e1_t3_project_level_selectionok.md`
- `canvases/web_platform/h3_quality_t7_quality_profiles_and_run_config_integration.md`
- `new-run-wizard-step2-strategy-full-implementation-plan.md` input terv
