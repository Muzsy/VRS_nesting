# Report — h3_e1_t3_project_level_selectionok

**Status:** PASS

## 1) Meta

* **Task slug:** `h3_e1_t3_project_level_selectionok`
* **Kapcsolodo canvas:** `canvases/web_platform/h3_e1_t3_project_level_selectionok.md`
* **Kapcsolodo goal YAML:** `codex/goals/canvases/web_platform/fill_canvas_h3_e1_t3_project_level_selectionok.yaml`
* **Futtas datuma:** 2026-03-26
* **Branch / commit:** main
* **Fokusz terulet:** Schema | Service | Routes | Scripts

## 2) Scope

### 2.1 Cel
- Project-level strategy selection es scoring selection persisted truth bevezetese.
- Owner-scoped create-or-replace selection workflow mindket selectionhoz.
- GET / PUT / DELETE backend contract mindket selectionhoz.
- Task-specifikus smoke script.

### 2.2 Nem-cel (explicit)
- H3-E1-T1 strategy profile CRUD ujranyitasa.
- H3-E1-T2 scoring profile CRUD ujranyitasa.
- Run snapshot builder vagy run create flow bekotese.
- `run_batches`, `run_batch_items`, evaluation, ranking vagy best-by-objective.
- Remnant/inventory domain.
- Frontend preference UI.

## 3) Valtozasok osszefoglaloja

### 3.1 Erintett fajlok

* **Migration:**
  * `supabase/migrations/20260324120000_h3_e1_t3_project_level_selectionok.sql`
* **Service:**
  * `api/services/project_strategy_scoring_selection.py`
* **Route:**
  * `api/routes/project_strategy_scoring_selection.py`
* **App registration:**
  * `api/main.py`
* **Scripts:**
  * `scripts/smoke_h3_e1_t3_project_level_selectionok.py`
* **Codex artefaktok:**
  * `canvases/web_platform/h3_e1_t3_project_level_selectionok.md`
  * `codex/goals/canvases/web_platform/fill_canvas_h3_e1_t3_project_level_selectionok.yaml`
  * `codex/prompts/web_platform/h3_e1_t3_project_level_selectionok/run.md`
  * `codex/codex_checklist/web_platform/h3_e1_t3_project_level_selectionok.md`
  * `codex/reports/web_platform/h3_e1_t3_project_level_selectionok.md`

### 3.2 Miert valtoztak?

* **Migration:** Bevezeti az `app.project_run_strategy_selection` es `app.project_scoring_selection` projekt-szintu selection truth tablakat, RLS policykal.
* **Service:** Dedikalt project_strategy_scoring_selection service, owner-scope validacioval es create-or-replace selection viselkedessel.
* **Route:** Hat endpoint (GET/PUT/DELETE mindket selectionhoz), bekotve az `api/main.py`-ba.
* **Smoke:** Task-specifikus smoke script a sikeres es hibas agak lefedettsegehez.

## 4) Verifikacio

### 4.1 Kotelezo parancs
* `./scripts/verify.sh --report codex/reports/web_platform/h3_e1_t3_project_level_selectionok.md` -> PASS

### 4.2 Feladat-specifikus ellenorzes
* `python3 -m py_compile api/services/project_strategy_scoring_selection.py api/routes/project_strategy_scoring_selection.py api/main.py scripts/smoke_h3_e1_t3_project_level_selectionok.py`
* `python3 scripts/smoke_h3_e1_t3_project_level_selectionok.py`

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo teszt/ellenorzes |
| --- | ---: | --- | --- | --- |
| #1 project_run_strategy_selection truth | PASS | `supabase/migrations/20260324120000_h3_e1_t3_project_level_selectionok.sql:L11-L16` | CREATE TABLE app.project_run_strategy_selection, project_id PK, FK run_strategy_profile_versions | smoke test 7: migration structure |
| #2 project_scoring_selection truth | PASS | `supabase/migrations/20260324120000_h3_e1_t3_project_level_selectionok.sql:L24-L29` | CREATE TABLE app.project_scoring_selection, project_id PK, FK scoring_profile_versions | smoke test 7: migration structure |
| #3 Max egy strategy selection / projekt | PASS | Migration: project_id PK; Service: create-or-replace upsert | PK biztositja az egyediseget, service upsert mintaval | smoke test 1: overwrite + only-one check |
| #4 Max egy scoring selection / projekt | PASS | Migration: project_id PK; Service: create-or-replace upsert | PK biztositja az egyediseget, service upsert mintaval | smoke test 2: overwrite + only-one check |
| #5 Owner scope CRUD | PASS | `api/services/project_strategy_scoring_selection.py:L58-L68` | _load_project_for_owner ellenorzi owner_user_id + lifecycle | smoke test 1,2,3 |
| #6 Csak sajat ervenyes version | PASS | `api/services/project_strategy_scoring_selection.py:L75-L96,L103-L124` | Owner + is_active validacio strategy es scoring versionokre | smoke test 4,5 |
| #7 Nem nyitja ujra T1/T2 CRUD-ot | PASS | Service forras: nincs profile CRUD, csak version read | A service kizarolag selection scope-ban marad | smoke test 6: source audit |
| #8 Nem nyul snapshot/batch/eval-hoz | PASS | Service forras: nincs hivatkozas tiltott tablakra | 9 tiltott tabla ellenorizve a write log-ban | smoke test 6: no forbidden side effects |
| #9 GET/PUT/DELETE contract | PASS | `api/routes/project_strategy_scoring_selection.py` | 6 endpoint: PUT/GET/DELETE mindket selectionhoz | smoke test 8: route structure |
| #10 Smoke script | PASS | `scripts/smoke_h3_e1_t3_project_level_selectionok.py` | 58/58 PASS, 9 test csoport | `python3 scripts/smoke_h3_e1_t3_project_level_selectionok.py` |
| #11 Checklist + report | PASS | `codex/codex_checklist/web_platform/h3_e1_t3_project_level_selectionok.md` | Minden DoD pont kipipalva | Jelen report |
| #12 verify.sh PASS | PASS | `codex/reports/web_platform/h3_e1_t3_project_level_selectionok.verify.log` | verify.sh PASS, check.sh exit 0, 217s | `./scripts/verify.sh --report ...` |

## 6) IO contract / mintak

Nem relevans.

## 7) Doksi szinkron

Nem relevans.

## 8) Advisory notes

- A project-level selection truth kulon retegkent lett bevezetve, a H3-E1-T1/T2 domain truth-ra epulve.
- A selection runtime alkalmazasa (snapshot binding, batch run world, evaluation/ranking) szandekosan out-of-scope; kesobbi H3 taskok scope-ja.
- A H3-E1 rovid DoD ugy ertelmezendo, hogy a selection persisted truth mar meglehet, de a runtime decision pipeline meg nem kerul osszekeveresre ezzel a taskkal.
- A create-or-replace upsert minta a H2-E1-T2 project_manufacturing_selection mintajat koveti.

## 9) Follow-ups

- H3-E2: Run batch modell, amely a project-level selectionokat runtime-ban hasznalja.
- H3-E3: Evaluation engine, amely a scoring selectiont alkalmazza runokra.
- Snapshot builder bovites: a project-level strategy/scoring selection snapshotba emelese.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-03-26T17:23:08+01:00 → 2026-03-26T17:26:45+01:00 (217s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/h3_e1_t3_project_level_selectionok.verify.log`
- git: `main@54c5d7f`
- módosított fájlok (git status): 11

**git diff --stat**

```text
 api/main.py | 4 ++++
 1 file changed, 4 insertions(+)
```

**git status --porcelain (preview)**

```text
 M api/main.py
?? api/routes/project_strategy_scoring_selection.py
?? api/services/project_strategy_scoring_selection.py
?? canvases/web_platform/h3_e1_t3_project_level_selectionok.md
?? codex/codex_checklist/web_platform/h3_e1_t3_project_level_selectionok.md
?? codex/goals/canvases/web_platform/fill_canvas_h3_e1_t3_project_level_selectionok.yaml
?? codex/prompts/web_platform/h3_e1_t3_project_level_selectionok/
?? codex/reports/web_platform/h3_e1_t3_project_level_selectionok.md
?? codex/reports/web_platform/h3_e1_t3_project_level_selectionok.verify.log
?? scripts/smoke_h3_e1_t3_project_level_selectionok.py
?? supabase/migrations/20260324120000_h3_e1_t3_project_level_selectionok.sql
```

<!-- AUTO_VERIFY_END -->
