# New Run Wizard Step2 Strategy — T3 Worker auto backend + engine_meta audit

## Funkció

Ez a task a `New Run Wizard Step2 — Nesting Stratégia + Beállítások` fejlesztés harmadik backend/worker lépése.

A T1 létrehozta a backend contract alapjait: `run_configs` strategy mezők, run create request mezők, `run_config_id` mentés és explicit snapshot override támogatás.
A T2 létrehozta a strategy resolvert és bekötötte a run creation + snapshot láncba, így a snapshot `solver_config_jsonb` már tartalmazza az effektív strategy truth mezőket.

A T3 célja, hogy a worker ténylegesen a snapshotolt `solver_config_jsonb.engine_backend_hint` alapján válasszon futtató backendet, amikor `WORKER_ENGINE_BACKEND=auto`, és az `engine_meta.json` teljes auditnyomot adjon a backend- és strategy-feloldásról.

A T3 végeredménye:

- `WORKER_ENGINE_BACKEND` fogadja az `auto` értéket;
- az `auto` legyen az új worker default;
- `auto` módban a worker a snapshot `solver_config_jsonb.engine_backend_hint` mezőjét használja;
- hiányzó vagy invalid hint esetén kontrollált fallback legyen `sparrow_v1` backendválasztással és warning loggal;
- explicit `WORKER_ENGINE_BACKEND=sparrow_v1` vagy `nesting_engine_v2` esetén a worker továbbra is env alapján döntsön;
- az engine runner kiválasztás, solver input mapping, profile effect és CLI arg mapping az effektív backend alapján történjen;
- az `engine_meta.json` visszakereshetően tartalmazza a requested/effective backendet, backend resolution source-t és a T2 strategy trace mezőket;
- legyen dedikált smoke, amely DB/solver nélkül bizonyítja a backend resolution és engine_meta payload logikát.

## Kiinduló valós repo-állapot T2 után

A friss repo alapján:

- `api/services/run_strategy_resolution.py`
  - létezik;
  - kiszámolja az effektív `engine_backend_hint` mezőt;
  - a támogatott hint érték jelenleg: `sparrow_v1`, `nesting_engine_v2`;
  - `auto` nem API/snapshot hint, hanem worker runtime mód.

- `api/services/run_creation.py`
  - a snapshot builder előtt hívja a resolvert;
  - a run `request_payload_jsonb` tartalmaz strategy summary mezőket.

- `api/services/run_snapshot_builder.py`
  - a `solver_config_jsonb` tartalmazza:
    - `quality_profile`,
    - `engine_backend_hint`,
    - `nesting_engine_runtime_policy`,
    - `strategy_profile_version_id`,
    - `strategy_resolution_source`,
    - `strategy_field_sources`,
    - `strategy_overrides_applied`.

- `worker/main.py`
  - konstansok:
    - `ENGINE_BACKEND_SPARROW_V1 = "sparrow_v1"`
    - `ENGINE_BACKEND_NESTING_V2 = "nesting_engine_v2"`
  - `_SUPPORTED_WORKER_ENGINE_BACKENDS` jelenleg csak a két konkrét backendet tartalmazza;
  - `_resolve_worker_engine_backend(...)` jelenleg nem fogad `auto` értéket;
  - `load_settings(...)` jelenleg `WORKER_ENGINE_BACKEND` defaultként `sparrow_v1` értéket használ;
  - `process_run(...)` környékén az `engine_backend = settings.engine_backend` fixen env-alapú;
  - `_resolve_engine_profile_resolution(...)` már backend-paramétert kap, és helyesen kezeli:
    - `nesting_engine_v2` esetén CLI args építés runtime policyból;
    - `sparrow_v1` esetén `profile_effect = "noop_non_nesting_backend"`;
  - az `engine_meta.json` már létezik, de jelenleg csak `engine_backend` mezőt ír, nincs benne requested/effective/backend source audit bontás.

## Scope

### Benne van

1. `worker/main.py` backend runtime mód bővítés:
   - új konstans: `ENGINE_BACKEND_AUTO = "auto"`;
   - `_SUPPORTED_WORKER_ENGINE_BACKENDS` bővítése `auto` értékkel;
   - `_resolve_worker_engine_backend(...)` fogadja az `auto` értéket;
   - `load_settings(...)` defaultja legyen `WORKER_ENGINE_BACKEND=auto`.

2. Worker per-run backend resolution:
   - snapshot betöltése után olvassa ki a `solver_config_jsonb.engine_backend_hint` mezőt;
   - `settings.engine_backend == "auto"` esetén ebből válasszon effektív backendet;
   - érvényes hint: `sparrow_v1`, `nesting_engine_v2`;
   - hiányzó/üres hint esetén fallback: `sparrow_v1`;
   - invalid hint esetén fallback: `sparrow_v1`;
   - fallback esetekben legyen explicit warning log.

3. Explicit env backend kompatibilitás:
   - ha `WORKER_ENGINE_BACKEND=sparrow_v1`, az effektív backend mindig `sparrow_v1`, snapshot hinttől függetlenül;
   - ha `WORKER_ENGINE_BACKEND=nesting_engine_v2`, az effektív backend mindig `nesting_engine_v2`, snapshot hinttől függetlenül;
   - csak `auto` esetén döntsön snapshot alapján.

4. Engine execution path frissítés:
   - solver input mapping az effektív backend alapján menjen;
   - `_resolve_engine_profile_resolution(...)` az effektív backendet kapja;
   - `_build_solver_runner_invocation(...)` az effektív backendet kapja;
   - unsupported backend hibák ne maradjanak elérhető állapotban valid settingsből.

5. `engine_meta.json` bővítés:
   - őrizze meg a meglévő, kompatibilitás miatt hasznos mezőket;
   - `engine_backend` maradjon, de az effektív backend értékével;
   - új mezők:
     - `requested_engine_backend`
     - `effective_engine_backend`
     - `backend_resolution_source`
     - `snapshot_engine_backend_hint`
     - `strategy_profile_version_id`
     - `strategy_resolution_source`
     - `strategy_field_sources`
     - `strategy_overrides_applied`
   - a `requested_engine_backend` az env/config szintű worker backend mód legyen, például `auto`;
   - az `effective_engine_backend` a ténylegesen futtatott backend legyen;
   - a `backend_resolution_source` legyen determinisztikus, például:
     - `worker_env_explicit`
     - `snapshot_solver_config`
     - `fallback_missing_snapshot_engine_backend_hint`
     - `fallback_invalid_snapshot_engine_backend_hint`.

6. Dedikált smoke:
   - `scripts/smoke_new_run_wizard_step2_strategy_t3_worker_auto_backend_engine_meta.py`
   - ne igényeljen Supabase-t, storage-ot, solver binárist vagy valós run-t;
   - importálható helperfüggvényeket teszteljen;
   - bizonyítsa az `auto` resolutiont, explicit env override-ot, fallbackokat és engine_meta strategy trace mezőit.

7. Report/checklist:
   - task checklist létrehozása;
   - report DoD -> Evidence matrixszal;
   - `verify.sh` AUTO_VERIFY blokk frissítése.

### Nincs benne

- Frontend Step2 UI;
- frontend API kliens bővítés;
- project default mentés UI-ból;
- strategy profile listázó UX;
- új DB migration;
- API contract további bővítése;
- nesting algoritmus tuning;
- solver output normalizer módosítása.

## Javasolt implementációs forma

### Worker backend mode konstansok

`worker/main.py` elején a backend konstansok legyenek egyértelműek:

```python
ENGINE_BACKEND_AUTO = "auto"
ENGINE_BACKEND_SPARROW_V1 = "sparrow_v1"
ENGINE_BACKEND_NESTING_V2 = "nesting_engine_v2"
_SUPPORTED_WORKER_ENGINE_BACKENDS = (
    ENGINE_BACKEND_AUTO,
    ENGINE_BACKEND_SPARROW_V1,
    ENGINE_BACKEND_NESTING_V2,
)
_SUPPORTED_EFFECTIVE_ENGINE_BACKENDS = (
    ENGINE_BACKEND_SPARROW_V1,
    ENGINE_BACKEND_NESTING_V2,
)
```

Az `auto` csak worker runtime mód, nem tényleges runner backend.
A runner invocation továbbra is csak `sparrow_v1` vagy `nesting_engine_v2` lehet.

### Backend resolution helper

Javasolt új dataclass:

```python
@dataclass(frozen=True)
class WorkerEngineBackendResolution:
    requested_engine_backend: str
    effective_engine_backend: str
    backend_resolution_source: str
    snapshot_engine_backend_hint: str | None
```

Javasolt helper:

```python
def _resolve_effective_engine_backend(
    *,
    requested_engine_backend: str,
    snapshot_row: dict[str, Any],
) -> WorkerEngineBackendResolution:
    ...
```

Viselkedés:

1. `requested_engine_backend != "auto"`:
   - `effective_engine_backend = requested_engine_backend`
   - `backend_resolution_source = "worker_env_explicit"`
   - `snapshot_engine_backend_hint` csak audit célból legyen kiolvasva, de ne befolyásolja a döntést.

2. `requested_engine_backend == "auto"` és snapshot hint érvényes:
   - `effective_engine_backend = snapshot_hint`
   - `backend_resolution_source = "snapshot_solver_config"`

3. `requested_engine_backend == "auto"` és snapshot hint hiányzik/üres:
   - `effective_engine_backend = "sparrow_v1"`
   - `backend_resolution_source = "fallback_missing_snapshot_engine_backend_hint"`
   - warning log.

4. `requested_engine_backend == "auto"` és snapshot hint invalid:
   - `effective_engine_backend = "sparrow_v1"`
   - `backend_resolution_source = "fallback_invalid_snapshot_engine_backend_hint"`
   - warning log, a nyers invalid értékkel.

### Strategy trace kiolvasás engine_meta-hoz

Az `engine_meta.json` összeállításakor a snapshotból olvasd ki:

```python
solver_config = snapshot_row.get("solver_config_jsonb") if isinstance(..., dict) else {}
strategy_profile_version_id = solver_config.get("strategy_profile_version_id")
strategy_resolution_source = solver_config.get("strategy_resolution_source")
strategy_field_sources = solver_config.get("strategy_field_sources")
strategy_overrides_applied = solver_config.get("strategy_overrides_applied")
```

A trace mezők ne okozzanak crasht, ha hiányoznak vagy rossz típusúak. Engine meta esetén audit-mezőként biztonságosan normalizáld őket:

- string mezők: `str(...).strip() or None`
- dict mezők: csak ha `dict`, különben `{}` vagy `None`
- list mezők: csak ha `list`, különben `[]` vagy `None`

## Elvárt engine_meta.json mezők

A meglévő mezők maradjanak, különösen:

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

```json
{
  "requested_engine_backend": "auto",
  "effective_engine_backend": "nesting_engine_v2",
  "backend_resolution_source": "snapshot_solver_config",
  "snapshot_engine_backend_hint": "nesting_engine_v2",
  "strategy_profile_version_id": "...",
  "strategy_resolution_source": "run_config",
  "strategy_field_sources": { "quality_profile": "run_config_override" },
  "strategy_overrides_applied": ["quality_profile"]
}
```

Kompatibilitási döntés:

- `engine_backend` maradjon meg, és az effektív backend értékét kapja;
- új fogyasztók használják az `effective_engine_backend` mezőt;
- régi fogyasztók ne törjenek el.

## Smoke elvárások

Új fájl:

`./scripts/smoke_new_run_wizard_step2_strategy_t3_worker_auto_backend_engine_meta.py`

Minimum tesztesetek:

1. `_resolve_worker_engine_backend("auto") == "auto"`.
2. `load_settings` default logika közvetetten vagy helper szinten az `auto` defaultot tükrözi. Ha a teljes `load_settings` env-igény miatt nehéz, legalább az env default hívás szövegszinten/helperrel legyen ellenőrizve.
3. Explicit `sparrow_v1` env esetén effective backend `sparrow_v1`, snapshot hint nem írja felül.
4. Explicit `nesting_engine_v2` env esetén effective backend `nesting_engine_v2`, snapshot hint nem írja felül.
5. `auto` + snapshot hint `nesting_engine_v2` -> effective `nesting_engine_v2`, source `snapshot_solver_config`.
6. `auto` + snapshot hint `sparrow_v1` -> effective `sparrow_v1`, source `snapshot_solver_config`.
7. `auto` + missing hint -> effective `sparrow_v1`, source `fallback_missing_snapshot_engine_backend_hint`.
8. `auto` + invalid hint -> effective `sparrow_v1`, source `fallback_invalid_snapshot_engine_backend_hint`.
9. `engine_meta` builder/helper vagy engine_meta payload tartalmazza a requested/effective/backend source mezőket.
10. `engine_meta` payload tartalmazza a T2 strategy trace mezőket.
11. `nesting_engine_v2` effective backend esetén a runtime policy CLI args továbbra is képződik.
12. `sparrow_v1` effective backend esetén `profile_effect == "noop_non_nesting_backend"` és CLI args üres.

Ha a jelenlegi worker kódban nincs külön engine_meta builder helper, érdemes létrehozni egy kicsi, izolált helperfüggvényt, hogy a smoke DB/solver nélkül tudja bizonyítani a payloadot. Például:

```python
def _build_engine_meta_payload(... ) -> dict[str, Any]:
    ...
```

Ne kelljen teljes `process_run(...)` futtatás a smoke-hoz.

## DoD

A task kész, ha mind teljesül:

1. `WORKER_ENGINE_BACKEND=auto` valid és default.
2. `auto` módban a snapshot `solver_config_jsonb.engine_backend_hint` dönt.
3. Explicit env backend továbbra is felülírja a snapshot hintet.
4. Missing/invalid snapshot hint fallback `sparrow_v1`, warning loggal.
5. Solver input mapping és runner invocation az effektív backend alapján történik.
6. `nesting_engine_v2` ágon a runtime policyból épített CLI args továbbra is érvényesül.
7. `sparrow_v1` ágon a profile effect továbbra is `noop_non_nesting_backend`.
8. `engine_meta.json` tartalmazza a requested/effective/backend source mezőket.
9. `engine_meta.json` tartalmazza a T2 strategy trace mezőket.
10. Dedikált T3 smoke PASS.
11. `./scripts/verify.sh --report codex/reports/web_platform/new_run_wizard_step2_strategy_t3_worker_auto_backend_engine_meta.md` PASS.

## Kockázatok és mitigáció

### Kockázat: `auto` default váratlanul backendváltást okoz

Mitigáció:

- snapshot hint a T2 után determinisztikusan kerül a snapshotba;
- invalid/missing hint fallback `sparrow_v1`;
- explicit env továbbra is használható rollback/override célra.

### Kockázat: régi fogyasztók `engine_meta.engine_backend` mezőt várnak

Mitigáció:

- a mező maradjon meg;
- értéke az effektív backend legyen;
- új mezők csak bővítik a payloadot.

### Kockázat: helperfüggvények nélkül a smoke túl nagy integrációs teszt lenne

Mitigáció:

- vezess be izolált backend resolution és engine_meta builder helperfüggvényeket;
- a teljes `process_run(...)` flow változtatása minimális legyen.

## Kötelező verifikáció

Futtatandó:

```bash
python3 -m py_compile \
  worker/main.py \
  scripts/smoke_new_run_wizard_step2_strategy_t3_worker_auto_backend_engine_meta.py

python3 scripts/smoke_new_run_wizard_step2_strategy_t3_worker_auto_backend_engine_meta.py

./scripts/verify.sh --report codex/reports/web_platform/new_run_wizard_step2_strategy_t3_worker_auto_backend_engine_meta.md
```

A reportban legyen:

- pontos módosított fájllista;
- DoD -> Evidence matrix;
- smoke eredmény;
- verify AUTO_VERIFY blokk;
- rövid megjegyzés, hogy a következő scope a frontend Step2 UI + API client submit flow javítása.
