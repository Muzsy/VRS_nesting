# Report — h3_e2_t1_run_batch_modell

**Status:** PASS

## 1) Meta

* **Task slug:** `h3_e2_t1_run_batch_modell`
* **Kapcsolodo canvas:** `canvases/web_platform/h3_e2_t1_run_batch_modell.md`
* **Kapcsolodo goal YAML:** `codex/goals/canvases/web_platform/fill_canvas_h3_e2_t1_run_batch_modell.yaml`
* **Futtas datuma:** 2026-03-26
* **Branch / commit:** main
* **Fokusz terulet:** Schema | Service | Routes | Scripts

## 2) Scope

### 2.1 Cel
- H3 batch domain persisted truth reteg bevezetese: `app.run_batches` + `app.run_batch_items`.
- Owner/project-scope batch CRUD + item management backend contract.
- Candidate label es strategy/scoring version kontextus tarolasa batch-item szinten.
- Task-specifikus smoke a fo invariansokra.

### 2.2 Nem-cel (explicit)
- Uj queued run letrehozasa (orchestrator flow).
- `run_evaluations`, `run_ranking_results`, comparison projection.
- Review/selection workflow vagy runtime ranking logika.
- Worker/snapshot runtime attervezes.

## 3) Valtozasok osszefoglaloja

### 3.1 Erintett fajlok

* **Migration:**
  * `supabase/migrations/20260324130000_h3_e2_t1_run_batch_modell.sql`
* **Service:**
  * `api/services/run_batches.py`
* **Route:**
  * `api/routes/run_batches.py`
* **App registration:**
  * `api/main.py`
* **Scripts:**
  * `scripts/smoke_h3_e2_t1_run_batch_modell.py`
* **Codex artefaktok:**
  * `canvases/web_platform/h3_e2_t1_run_batch_modell.md`
  * `codex/goals/canvases/web_platform/fill_canvas_h3_e2_t1_run_batch_modell.yaml`
  * `codex/prompts/web_platform/h3_e2_t1_run_batch_modell/run.md`
  * `codex/codex_checklist/web_platform/h3_e2_t1_run_batch_modell.md`
  * `codex/reports/web_platform/h3_e2_t1_run_batch_modell.md`

### 3.2 Miert valtoztak?

* **Migration:** Letrehozza a H3-E2-T1 truth tablakat (`run_batches`, `run_batch_items`) es owner/project-scope RLS policykat.
* **Service:** Kizárólag batch CRUD + item attach/list/remove viselkedest ad, explicit project/run/version owner validacioval.
* **Route:** Minimalis REST contract a batch model task scope-jara, orchestrator/evaluation/ranking nelkul.
* **Smoke:** Bizonyitja a fo invariansokat: duplicate item tiltasa, idegen projekt run tiltasa, idegen owner strategy/scoring tiltasa, side-effect hiany.

## 4) Verifikacio

### 4.1 Kotelezo parancs
* `./scripts/verify.sh --report codex/reports/web_platform/h3_e2_t1_run_batch_modell.md` -> PASS

### 4.2 Feladat-specifikus ellenorzes
* `python3 -m py_compile api/services/run_batches.py api/routes/run_batches.py api/main.py scripts/smoke_h3_e2_t1_run_batch_modell.py`
* `python3 scripts/smoke_h3_e2_t1_run_batch_modell.py` -> PASS (`44/44`)

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo teszt/ellenorzes |
| --- | ---: | --- | --- | --- |
| #1 `run_batches` truth reteg | PASS | `supabase/migrations/20260324130000_h3_e2_t1_run_batch_modell.sql:L9` | `app.run_batches` tabla project-szintu grouping truthkent letrejon. | smoke 8 |
| #2 `run_batch_items` truth reteg | PASS | `supabase/migrations/20260324130000_h3_e2_t1_run_batch_modell.sql:L29` | `app.run_batch_items` tabla mar meglevo runok batch-hez kotesehez. | smoke 8 |
| #3 Batch CRUD owner/project-scope | PASS | `api/services/run_batches.py:L192,L226,L256,L286` | CRUD elott project owner validacio fut (`_load_project_for_owner`). | smoke 1 |
| #4 Item attach/list/remove mukodik | PASS | `api/services/run_batches.py:L325,L428,L467` | Attach/list/remove service API implementalva. | smoke 2 |
| #5 Strategy/scoring kontextus tarolhato | PASS | `supabase/migrations/20260324130000_h3_e2_t1_run_batch_modell.sql:L33-L35`, `api/services/run_batches.py:L325` | Item payload tartalmaz optional strategy/scoring version hivatkozast es validaciot. | smoke 2,5,6 |
| #6 Nincs uj queued run letrehozas | PASS | `api/services/run_batches.py` | Service csak `app.run_batches` es `app.run_batch_items` table write-ot vegez. | smoke 7 |
| #7 Nincs evaluation/ranking/comparison scope | PASS | `supabase/migrations/20260324130000_h3_e2_t1_run_batch_modell.sql`, `api/services/run_batches.py` | Nincs `run_evaluations` vagy `run_ranking_results` write/DDL. | smoke 7,8 |
| #8 Dedikalt batch service + route | PASS | `api/services/run_batches.py`, `api/routes/run_batches.py:L26` | Kulon service es kulon router prefixszel. | smoke 9 |
| #9 Route bekotes `api/main.py` | PASS | `api/main.py:L23,L122` | `run_batches_router` import + include_router megtortent. | py_compile |
| #10 Task-specifikus smoke | PASS | `scripts/smoke_h3_e2_t1_run_batch_modell.py:L213-L627` | 9 tesztblokk a canvas DoD invariansokra. | `python3 scripts/smoke_h3_e2_t1_run_batch_modell.py` |
| #11 Checklist + report evidence-alapon | PASS | `codex/codex_checklist/web_platform/h3_e2_t1_run_batch_modell.md`, jelen report | DoD pontok es evidenciak kitoltve. | jelen report |
| #12 verify.sh PASS | PASS | `codex/reports/web_platform/h3_e2_t1_run_batch_modell.verify.log` | Kotelezo repo gate wrapper futtatva. | `./scripts/verify.sh --report ...` |

## 6) IO contract / mintak

Nem relevans.

## 7) Doksi szinkron

Nem relevans.

## 8) Advisory notes

- A `run_batches` + `run_batch_items` kulon persisted truth reteget ad a H3 batch-vonalhoz.
- A `candidate_label` es strategy/scoring version hivatkozas mar most auditálhatoan tarolhato, de score-szamitast nem indit.
- Uj run-inditas szandekosan nincs ebben a taskban; az orchestrator a kovetkezo task scope-ja.
- Evaluation es ranking teljesen out-of-scope maradt.

## 9) Follow-ups

- H3-E2-T2 batch orchestrator service (uj queued runok letrehozasa + batch item binding).
- H3-E3 evaluation/ranking reteg a batch itemekre epitve.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-03-26T19:36:25+01:00 → 2026-03-26T19:39:57+01:00 (212s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/h3_e2_t1_run_batch_modell.verify.log`
- git: `main@d1add48`
- módosított fájlok (git status): 14

**git diff --stat**

```text
 api/main.py | 2 ++
 1 file changed, 2 insertions(+)
```

**git status --porcelain (preview)**

```text
 M api/main.py
?? api/routes/run_batches.py
?? api/services/run_batches.py
?? canvases/web_platform/h3_e2_t1_run_batch_modell.md
?? canvases/web_platform/h3_e2_t2_batch_run_orchestrator.md
?? codex/codex_checklist/web_platform/h3_e2_t1_run_batch_modell.md
?? codex/goals/canvases/web_platform/fill_canvas_h3_e2_t1_run_batch_modell.yaml
?? codex/goals/canvases/web_platform/fill_canvas_h3_e2_t2_batch_run_orchestrator.yaml
?? codex/prompts/web_platform/h3_e2_t1_run_batch_modell/
?? codex/prompts/web_platform/h3_e2_t2_batch_run_orchestrator/
?? codex/reports/web_platform/h3_e2_t1_run_batch_modell.md
?? codex/reports/web_platform/h3_e2_t1_run_batch_modell.verify.log
?? scripts/smoke_h3_e2_t1_run_batch_modell.py
?? supabase/migrations/20260324130000_h3_e2_t1_run_batch_modell.sql
```

<!-- AUTO_VERIFY_END -->
