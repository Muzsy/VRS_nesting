# New Run Wizard Step2 Strategy — T2 Resolver + snapshot precedence integration

## Funkció

Ez a task a `New Run Wizard Step2 — Nesting Stratégia + Beállítások` fejlesztés második backend lépése.
A T1 már létrehozta a backend contract alapjait: `run_configs` strategy mezők, `RunCreateRequest` mezők,
`run_config_id` mentése, explicit request override-ok snapshotba átadása. A T2 célja, hogy ezek a mezők ne csak
különálló request contractként létezzenek, hanem determinisztikus strategy resolution folyamatban álljanak össze
végső, snapshotolt solver truth-á.

A T2 végeredménye:

- legyen külön resolver service, amely a run létrehozáskor összefésüli a request, run_config, project selection és global default forrásokat;
- a precedence sorrend ténylegesen működjön;
- a snapshot `solver_config_jsonb` tartalmazza az effektív strategy/profile/runtime/backend truth-ot és a resolution trace mezőket;
- a run `request_payload_jsonb` audit alapon visszakereshetően jelezze, miből lett a végső strategy;
- legyen dedikált smoke, amely Supabase/worker/solver nélkül bizonyítja a precedence logikát.

## Kiinduló valós repo-állapot T1 után

A friss repo alapján:

- `supabase/migrations/20260425110000_new_run_wizard_step2_strategy_t1_runconfig_contract.sql`
  - hozzáadta az `app.run_configs.run_strategy_profile_version_id` mezőt;
  - hozzáadta az `app.run_configs.solver_config_overrides_jsonb` mezőt;
  - frissítette a `public.run_configs` view/IUD bridge-et.
- `api/routes/run_configs.py`
  - `RunConfigCreateRequest` már fogad `run_strategy_profile_version_id` és `solver_config_overrides_jsonb` mezőket;
  - van owner + active strategy version ellenőrzés;
  - van override whitelist/normalizálás.
- `api/routes/runs.py`
  - `RunCreateRequest` már fogadja a T1 mezőket: `run_config_id`, `run_strategy_profile_version_id`, `quality_profile`, `engine_backend_hint`, `nesting_engine_runtime_policy`, `sa_eval_budget_sec`.
- `api/services/run_creation.py`
  - `create_queued_run_from_project_snapshot(...)` már kapja ezeket a mezőket;
  - `run_config_id` scope ellenőrzése és run sorba mentése már megvan;
  - viszont a `run_config` tartalmat még nem használja a snapshot feloldásban;
  - nincs request > run_config > project selection > default precedence.
- `api/services/run_snapshot_builder.py`
  - már fogad explicit request `quality_profile`, `engine_backend_hint`, `nesting_engine_runtime_policy`, `sa_eval_budget_sec` mezőket;
  - viszont nincs `strategy_profile_version_id`, `strategy_resolution_source`, `field_sources` vagy `overrides_applied` trace;
  - a builder még nem kap resolverből előállított, teljes strategy contextet.
- `api/services/project_strategy_scoring_selection.py`
  - a strategy version loader selectje már tartalmazza: `solver_config_jsonb`, `placement_config_jsonb`, `manufacturing_bias_jsonb`.
- Dedikált T1 smoke:
  - `scripts/smoke_new_run_wizard_step2_strategy_t1_backend_contract_runconfig.py`
  - contract szinten PASS, de nem bizonyít teljes precedence feloldást.

## Scope

### Benne van

1. Új service:
   - `api/services/run_strategy_resolution.py`

2. Strategy resolver felelősségek:
   - request mezők normalizálása;
   - `run_config_id` esetén a run_config tartalmi betöltése: `id`, `project_id`, `created_by`, `run_strategy_profile_version_id`, `solver_config_overrides_jsonb`;
   - project-level strategy selection betöltése, ha magasabb precedence forrás nem ad strategy profile versiont;
   - strategy profile version betöltése owner scope-pal;
   - végső mezők kiszámítása: `quality_profile`, `nesting_engine_runtime_policy`, `sa_eval_budget_sec`, `engine_backend_hint`, `strategy_profile_version_id`;
   - observability trace előállítása: `strategy_resolution_source`, `effective_strategy_profile_version_id`, `field_sources`, `overrides_applied`.

3. Precedence sorrend implementálása:

   Strategy profile version forrás:
   1. explicit run create request `run_strategy_profile_version_id`
   2. `run_config.run_strategy_profile_version_id`
   3. `project_run_strategy_selection.active_run_strategy_profile_version_id`
   4. nincs profile, global default

   Egyedi solver mezők forrása:
   1. explicit run create request mezők
   2. `run_config.solver_config_overrides_jsonb`
   3. választott strategy profile version `solver_config_jsonb`
   4. global default quality profile/runtime policy/backend default

4. `api/services/run_creation.py` integráció:
   - a T1-ben megadott request mezőkből és optional `run_config_id`-ból hívja a resolvert;
   - a snapshot buildernek már resolver eredményt adjon tovább;
   - a run `request_payload_jsonb` tartalmazza a resolution summary mezőket.

5. `api/services/run_snapshot_builder.py` bővítés:
   - fogadjon resolver trace mezőket;
   - `solver_config_jsonb` tartalmazza: `quality_profile`, `engine_backend_hint`, `nesting_engine_runtime_policy`, `strategy_profile_version_id`, `strategy_resolution_source`, `strategy_field_sources`, `strategy_overrides_applied`;
   - default viselkedés maradjon kompatibilis régi hívásokkal.

6. Dedikált smoke:
   - `scripts/smoke_new_run_wizard_step2_strategy_t2_resolution_snapshot_precedence.py`
   - fake Supabase clienttel, worker/solver nélkül.

### Nincs benne

- Frontend Step2 UI;
- frontend API kliens bővítés;
- worker `WORKER_ENGINE_BACKEND=auto` megvalósítása;
- `engine_meta.json` worker artifact bővítés;
- új DB migration, ha nem feltétlenül szükséges;
- full UX summary oldal;
- algoritmus tuning.

## Resolver contract

### Javasolt új típusok

`api/services/run_strategy_resolution.py` tartalmazzon service-szintű, route-független típusokat:

- `RunStrategyResolutionError(Exception)`
  - `status_code: int`
  - `detail: str`

- `ResolvedRunStrategy`
  - `quality_profile: str`
  - `nesting_engine_runtime_policy: dict[str, Any]`
  - `sa_eval_budget_sec: int | None`
  - `engine_backend_hint: str`
  - `strategy_profile_version_id: str | None`
  - `strategy_resolution_source: str`
  - `field_sources: dict[str, str]`
  - `overrides_applied: list[str]`
  - `trace_jsonb: dict[str, Any]`

### Resolver függvény

Javasolt publikus belépési pont:

```python
resolve_run_strategy(
    *,
    supabase: SupabaseClient,
    access_token: str,
    owner_user_id: str,
    project_id: str,
    run_config_id: str | None,
    request_run_strategy_profile_version_id: str | None,
    request_quality_profile: str | None,
    request_engine_backend_hint: str | None,
    request_nesting_engine_runtime_policy: dict[str, Any] | None,
    request_sa_eval_budget_sec: int | None,
) -> ResolvedRunStrategy
```

A függvény ne importáljon FastAPI route modelleket. Route-layer helper helyett a domain helperre épüljön:

- `normalize_quality_profile_name(...)`
- `runtime_policy_for_quality_profile(...)`
- `validate_runtime_policy(...)`
- `compact_runtime_policy(...)`

### Engine backend hint

T2-ben érvényes backend hint értékek:

- `sparrow_v1`
- `nesting_engine_v2`

Az `auto` nem T2 scope. Az majd worker-scope-ban jön, mert worker oldali resolution is kell hozzá.

### Strategy profile version betöltés

A resolver a `app.run_strategy_profile_versions` sorból legalább ezeket kérje:

- `id`
- `run_strategy_profile_id`
- `owner_user_id`
- `version_no`
- `lifecycle`
- `is_active`
- `solver_config_jsonb`
- `placement_config_jsonb`
- `manufacturing_bias_jsonb`

Owner scope kötelező: `owner_user_id == owner_user_id`.

Aktivitás:

- explicit request profile version esetén csak active verzió fogadható el;
- project selection és run_config alapú snapshot reprodukálhatóság miatt legalább owner-scope legyen kötelező;
- ha a repo jelenlegi domain szabályai alapján inactive verzió tiltandó, akkor ezt a smoke-ban is explicit bizonyítani kell;
- a döntést dokumentálni kell a reportban.

### Profile solver_config_jsonb elvárt kezelése

A strategy profile version `solver_config_jsonb` mezőből a resolver csak ismert kulcsokat vegyen figyelembe:

- `quality_profile`
- `sa_eval_budget_sec`
- `nesting_engine_runtime_policy`
- `engine_backend_hint`

Ismeretlen profile config kulcsok ne okozzanak runtime crash-t; vagy ignore + trace advisory, vagy 400 hiba, de a döntést dokumentálni kell.
Run_config override-oknál már T1-ben strict whitelist van, de a resolver akkor se bízzon vakon a DB-ben.

## Precedence példák

### 1. Csak default

Ha nincs request override, nincs run_config, nincs project selection:

- `quality_profile = quality_default`
- runtime policy a `quality_default` registry alapján;
- `engine_backend_hint` a jelenlegi builder-kompatibilis default, vagyis `nesting_engine_v2`;
- `strategy_resolution_source = global_default`.

### 2. Project selection

Ha csak project-level strategy selection van:

- profile version a selectionből jön;
- profile `solver_config_jsonb` adja a base mezőket;
- `strategy_resolution_source = project_selection`.

### 3. Run config preset

Ha `run_config_id` van és a config tartalmaz `run_strategy_profile_version_id`-t:

- profile version a run_configból jön;
- profile `solver_config_jsonb` base;
- `run_config.solver_config_overrides_jsonb` felülírja a profile base-t;
- `strategy_resolution_source = run_config` vagy `run_config_with_profile`.

### 4. Explicit request override

Ha requestben van bármelyik strategy/solver mező:

- explicit request a legmagasabb precedence;
- `field_sources` mezőnként mutassa, hogy mi jött requestből;
- `strategy_resolution_source` legyen request vagy request_override;
- `overrides_applied` listában szerepeljenek az átírt mezők.

## Run creation integráció

`api/services/run_creation.py`:

- a T1-ben létező `_load_run_config_for_owner(...)` helper jelenleg csak validál. T2-ben vagy bővítendő, hogy visszaadja a strategy mezőket is, vagy a resolver töltse be újra a teljes run_configot;
- a resolver hívása a snapshot builder előtt történjen;
- snapshot buildernek ne nyers request mezők menjenek, hanem resolver output;
- `_insert_run(...)` request payloadja tartalmazza a resolution trace rövid összefoglalóját.

## Snapshot builder integráció

`api/services/run_snapshot_builder.py`:

- bővítse a `build_run_snapshot_payload(...)` optional paramétereit;
- ha nincs resolver trace megadva, régi kompatibilis defaultot használjon;
- `solver_config_jsonb` tartalmazza az új audit mezőket;
- a hash payloadba ezek bekerülnek, vagyis strategy változás tudatosan új snapshot hash-t eredményez.

## Teszt/smoke elvárások

Új smoke:

`python3 scripts/smoke_new_run_wizard_step2_strategy_t2_resolution_snapshot_precedence.py`

Legalább ezeket bizonyítsa:

1. resolver default-only esetben `quality_default` és `global_default` source;
2. project selection esetben profile version és profile solver config érvényesül;
3. run_config esetben a run_config profile version megelőzi a project selectiont;
4. run_config `solver_config_overrides_jsonb` megelőzi a profile solver configot;
5. explicit request `quality_profile`, `engine_backend_hint`, `nesting_engine_runtime_policy`, `sa_eval_budget_sec` megelőz minden más forrást;
6. snapshot `solver_config_jsonb` tartalmazza a trace mezőket;
7. run `request_payload_jsonb` tartalmazza a resolution summaryt;
8. idegen owner strategy profile version elutasításra kerül;
9. invalid runtime policy elutasításra kerül.

## DoD

A task kész, ha:

- `api/services/run_strategy_resolution.py` létezik és izoláltan tesztelhető;
- `create_queued_run_from_project_snapshot(...)` már a resolvert használja;
- a run_config strategy mezői ténylegesen beleszámítanak a snapshotba;
- project-level selection fallback működik;
- explicit request override precedence működik;
- snapshot `solver_config_jsonb` audit mezői teljesek;
- dedikált T2 smoke PASS;
- standard verify report frissül.

## Kockázatok és rollback

### Kockázat: snapshot hash változás

A strategy trace mezők bekerülnek a snapshot hash payloadba, ezért ugyanaz a projekt más strategyvel új hash-t kap.
Ez elvárt. A reportban külön jelezni kell.

Rollback:

- ha regression jelenik meg, a run_creation visszaállítható T1 direkt request override átadásra;
- az új resolver service izolált fájl, minimális rollbackkel kivehető.

### Kockázat: profile solver_config_jsonb mezők lazak

A korábbi profile sorok tartalmazhatnak hiányos vagy lazább JSON-t.

Mitigáció:

- csak ismert kulcsokat használjon a resolver;
- validálja a runtime policyt;
- hiba esetén determinisztikus service error legyen, ne worker-time failure.

### Kockázat: inactive profile version kezelése

Ha egy korábbi selection vagy run_config inactive verzióra mutat, a teljes tiltás ronthatja a reprodukálhatóságot.

Mitigáció:

- a választott policyt dokumentálni kell;
- explicit requestre szigorúbb active check javasolt;
- run_config/project selection esetben legalább owner-scope kötelező.

## Kötelező parancsok

```bash
python3 -m py_compile \
  api/services/run_strategy_resolution.py \
  api/services/run_creation.py \
  api/services/run_snapshot_builder.py \
  scripts/smoke_new_run_wizard_step2_strategy_t2_resolution_snapshot_precedence.py

python3 scripts/smoke_new_run_wizard_step2_strategy_t2_resolution_snapshot_precedence.py

./scripts/verify.sh --report codex/reports/web_platform/new_run_wizard_step2_strategy_t2_resolution_snapshot_precedence.md
```
