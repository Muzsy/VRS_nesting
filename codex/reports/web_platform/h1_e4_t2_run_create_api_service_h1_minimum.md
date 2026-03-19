PASS

## 1) Meta
- Task slug: `h1_e4_t2_run_create_api_service_h1_minimum`
- Kapcsolodo canvas: `canvases/web_platform/h1_e4_t2_run_create_api_service_h1_minimum.md`
- Kapcsolodo goal YAML: `codex/goals/canvases/web_platform/fill_canvas_h1_e4_t2_run_create_api_service_h1_minimum.yaml`
- Futas datuma: `2026-03-19`
- Branch / commit: `main @ b962122 (dirty working tree)`
- Fokusz terulet: `Run create service + route create ag realignment + smoke + codex artefaktok`

## 2) Scope

### 2.1 Cel
- Explicit run creation service bevezetese a H1-E4-T1 snapshot builderre epitve.
- Canonical H0/H1 tablavilagba iras: `app.nesting_runs`, `app.nesting_run_snapshots`, `app.run_queue`.
- Request oldali idempotencia es snapshot hash dedup kezeles explicitten.
- Task-specifikus smoke script keszitese success es hibas agakra.

### 2.2 Nem-cel (explicit)
- Worker lease/recovery, solver futtatas, result normalizer, layout/projection, artifact workflow.
- Queue worker vagy run executor orchestration bevezetese.
- Legacy `enqueue_run_with_quota` helper ujra-canonicalizalasa.

## 3) Valtozasok osszefoglalasa

### 3.1 Erintett fajlok
- `canvases/web_platform/h1_e4_t2_run_create_api_service_h1_minimum.md`
- `codex/goals/canvases/web_platform/fill_canvas_h1_e4_t2_run_create_api_service_h1_minimum.yaml`
- `codex/prompts/web_platform/h1_e4_t2_run_create_api_service_h1_minimum/run.md`
- `api/services/run_creation.py`
- `api/routes/runs.py`
- `scripts/smoke_h1_e4_t2_run_create_api_service_h1_minimum.py`
- `codex/codex_checklist/web_platform/h1_e4_t2_run_create_api_service_h1_minimum.md`
- `codex/reports/web_platform/h1_e4_t2_run_create_api_service_h1_minimum.md`

### 3.2 Mit szallit le a task (H1 minimum run create)
- `create_queued_run_from_project_snapshot(...)` service owner/project guarddal es H1-E4-T1 snapshot builder hivassal.
- Sikeres create eseten canonical row-trio letrehozas:
  - `app.nesting_runs` -> `status='queued'`
  - `app.nesting_run_snapshots` -> `status='ready'`
  - `app.run_queue` -> `queue_state='pending'`
- Explicit idempotencia/dedup szemantika:
  - `idempotency_key` alapu visszaadas (`idempotency_key` / `idempotency_key_race`)
  - `snapshot_hash_sha256` alapu visszaadas (`snapshot_hash` / `snapshot_hash_race`)
- Best-effort cleanup, hogy reszleges write eseten ne maradjon felkesz run.
- `api/routes/runs.py` create ag service-re kotese; list/log/artifact pathok erintetlenul hagyva.

### 3.3 Mit NEM szallit le meg
- Worker lease/failure recovery/futtatasi lifecycle.
- Solver invocation es output normalizalas.
- Artifact/projection pipeline.

### 3.4 Plusz schema/runtime fuggoseg
- Uj migracio nem keszult.
- A create service runtime fuggosege a canonical run/snapshot/queue schema:
  - `supabase/migrations/20260314100000_h0_e5_t1_nesting_run_es_snapshot_modellek.sql`
  - `supabase/migrations/20260314103000_h0_e5_t2_queue_es_log_modellek.sql`
- A legacy `api/sql/phase4_run_quota_atomic.sql` helper referencia marad, de a route create ag canonicalan mar nem erre epit.

## 4) Verifikacio (How tested)

### 4.1 Opcionais, feladatfuggo ellenorzes
- `python3 -m py_compile api/services/run_creation.py api/routes/runs.py scripts/smoke_h1_e4_t2_run_create_api_service_h1_minimum.py` -> PASS
- `python3 scripts/smoke_h1_e4_t2_run_create_api_service_h1_minimum.py` -> PASS

### 4.2 Kotelezo repo gate
- `./scripts/verify.sh --report codex/reports/web_platform/h1_e4_t2_run_create_api_service_h1_minimum.md` -> PASS

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo ellenorzes |
| --- | --- | --- | --- | --- |
| Keszul explicit run creation service. | PASS | `api/services/run_creation.py:223` | A `create_queued_run_from_project_snapshot(...)` kulon service modulban valositja meg a run create folyamatot. | `py_compile` + smoke |
| A service owner/project guard utan a H1-E4-T1 buildert hivja. | PASS | `api/services/run_creation.py:40`; `api/services/run_creation.py:242` | A project ownership guard utan a service a `build_run_snapshot_payload(...)` builderre epul. | Smoke: foreign project + builder error |
| Sikeres create queued run recordot hoz letre. | PASS | `api/services/run_creation.py:133`; `api/services/run_creation.py:146` | A run insert `status='queued'` allapottal tortenik. | Smoke success branch |
| Sikeres create ready snapshot recordot hoz letre. | PASS | `api/services/run_creation.py:159`; `api/services/run_creation.py:169` | A snapshot insert `status='ready'` es canonical manifest payload mezoivel tortenik. | Smoke success branch |
| Sikeres create pending queue recordot hoz letre. | PASS | `api/services/run_creation.py:184`; `api/services/run_creation.py:194` | A queue insert `queue_state='pending'` allapotban tortenik. | Smoke success branch |
| Az idempotencia/dedup kezeles explicitten implementalt. | PASS | `api/services/run_creation.py:256`; `api/services/run_creation.py:299`; `api/services/run_creation.py:345`; `api/services/run_creation.py:392` | Idempotency key es snapshot hash alapu dedup branch is explicit kezelve van. | Smoke idempotency + hash dedup + race |
| Snapshot hash unique versenyhelyzet nem nyers DB hibaval all le. | PASS | `api/services/run_creation.py:392`; `api/services/run_creation.py:422`; `scripts/smoke_h1_e4_t2_run_create_api_service_h1_minimum.py:355`; `scripts/smoke_h1_e4_t2_run_create_api_service_h1_minimum.py:366` | Duplicate snapshot hash eseten cleanup + letezo run visszaadas tortenik (`snapshot_hash_race`). | Smoke snapshot race branch |
| Hibas reszleges create utan best-effort cleanup fut. | PASS | `api/services/run_creation.py:203`; `api/services/run_creation.py:393`; `api/services/run_creation.py:430`; `api/services/run_creation.py:456` | Snapshot/queue hiba eseten torlesi cleanup ved a reszleges iras ellen. | Smoke race branch |
| A run route create aga a service-re lett kotve es nem inline run_config vilag. | PASS | `api/routes/runs.py:27`; `api/routes/runs.py:335` | A create request mar `idempotency_key` + `run_purpose`, es a create ag explicit service-hivast hasznal. | `py_compile` + kodellenorzes |
| A list/log/artifact agak nem lettek ujratervezve ebben a taskban. | PASS | `api/routes/runs.py:353`; `api/routes/runs.py:430`; `api/routes/runs.py:586` | A task a create agra fokuszal; list/log/artifact endpointek meglevo implementacioja maradt. | Kodellenorzes |
| Keszult task-specifikus smoke script sikeres + hibas agakra. | PASS | `scripts/smoke_h1_e4_t2_run_create_api_service_h1_minimum.py:256`; `scripts/smoke_h1_e4_t2_run_create_api_service_h1_minimum.py:295`; `scripts/smoke_h1_e4_t2_run_create_api_service_h1_minimum.py:308`; `scripts/smoke_h1_e4_t2_run_create_api_service_h1_minimum.py:327`; `scripts/smoke_h1_e4_t2_run_create_api_service_h1_minimum.py:342`; `scripts/smoke_h1_e4_t2_run_create_api_service_h1_minimum.py:357` | A smoke lefedi a success, idempotency, snapshot dedup, builder error, foreign project es snapshot race branch-eket. | Smoke |

## 6) Advisory notes
- A task H1 minimum run create scope-ot ad: a request->snapshot->queue canonical letrehozas kesz.
- A worker lifecycle/scheduler/solver futtatasi felelosseg tovabbra is H1-E4-T3 + H1-E5 scope.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-03-19T19:41:44+01:00 → 2026-03-19T19:45:13+01:00 (209s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/h1_e4_t2_run_create_api_service_h1_minimum.verify.log`
- git: `main@b962122`
- módosított fájlok (git status): 9

**git diff --stat**

```text
 api/routes/runs.py | 168 +++++------------------------------------------------
 1 file changed, 14 insertions(+), 154 deletions(-)
```

**git status --porcelain (preview)**

```text
 M api/routes/runs.py
?? api/services/run_creation.py
?? canvases/web_platform/h1_e4_t2_run_create_api_service_h1_minimum.md
?? codex/codex_checklist/web_platform/h1_e4_t2_run_create_api_service_h1_minimum.md
?? codex/goals/canvases/web_platform/fill_canvas_h1_e4_t2_run_create_api_service_h1_minimum.yaml
?? codex/prompts/web_platform/h1_e4_t2_run_create_api_service_h1_minimum/
?? codex/reports/web_platform/h1_e4_t2_run_create_api_service_h1_minimum.md
?? codex/reports/web_platform/h1_e4_t2_run_create_api_service_h1_minimum.verify.log
?? scripts/smoke_h1_e4_t2_run_create_api_service_h1_minimum.py
```

<!-- AUTO_VERIFY_END -->
