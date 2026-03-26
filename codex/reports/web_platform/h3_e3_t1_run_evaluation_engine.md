# Report — h3_e3_t1_run_evaluation_engine

**Status:** PASS

## 1) Meta

* **Task slug:** `h3_e3_t1_run_evaluation_engine`
* **Kapcsolodo canvas:** `canvases/web_platform/h3_e3_t1_run_evaluation_engine.md`
* **Kapcsolodo goal YAML:** `codex/goals/canvases/web_platform/fill_canvas_h3_e3_t1_run_evaluation_engine.yaml`
* **Futtas datuma:** 2026-03-26
* **Branch / commit:** main
* **Fokusz terulet:** Schema | Service | Routes | Scripts

## 2) Scope

### 2.1 Cel
- `app.run_evaluations` persisted truth reteg bevezetese owner-scoped RLS policykkal.
- Dedikalt evaluation service (`api/services/run_evaluations.py`) explicit scoring version kontraktussal.
- Minimalis evaluation route (`POST/GET/DELETE /projects/{project_id}/runs/{run_id}/evaluation`) es app router bekotes.
- Bounded, komponens-szintu score formalizalasa H1/H2 persisted inputokra epitve.
- Task-specifikus smoke script a sikeres, hibas es out-of-scope agakkal.

### 2.2 Nem-cel (explicit)
- `run_ranking_results`, batch comparison projection, best-by-objective sorrend.
- `project_selected_runs`, review workflow, business metrics truth.
- H1/H2 truth tablák modositasa (`run_metrics`, `run_manufacturing_metrics` write).
- Worker/run snapshot pipeline atalakitasa.

## 3) Valtozasok osszefoglaloja

### 3.1 Erintett fajlok

* **Migration:**
  * `supabase/migrations/20260324140000_h3_e3_t1_run_evaluation_engine.sql`
* **Service:**
  * `api/services/run_evaluations.py`
* **Route:**
  * `api/routes/run_evaluations.py`
* **App registration:**
  * `api/main.py`
* **Scripts:**
  * `scripts/smoke_h3_e3_t1_run_evaluation_engine.py`
* **Codex artefaktok:**
  * `canvases/web_platform/h3_e3_t1_run_evaluation_engine.md`
  * `codex/goals/canvases/web_platform/fill_canvas_h3_e3_t1_run_evaluation_engine.yaml`
  * `codex/prompts/web_platform/h3_e3_t1_run_evaluation_engine/run.md`
  * `codex/codex_checklist/web_platform/h3_e3_t1_run_evaluation_engine.md`
  * `codex/reports/web_platform/h3_e3_t1_run_evaluation_engine.md`

### 3.2 Miert valtoztak?

* **Schema:** A H3-E3-T1 minimalis outputja (`run_evaluations`) kulon truth tablaban jelent meg (`run_id`, `scoring_profile_version_id`, `total_score`, `evaluation_jsonb`, `created_at`), bounded score checkkel es owner-scoped RLS policykkal.
* **Service:** A score kizarolag persisted H1/H2 inputokra epul (`run_metrics`, `run_manufacturing_metrics`), komponensenkenti indoklassal (`raw_value`, `normalized_value`, `weight`, `contribution`, `status`), threshold eredmenyekkel es tie-breaker input snapshotokkal.
* **Applied scoring kulcsok most:** `utilization_weight`, `unplaced_penalty`, `sheet_count_penalty`, feltetelesen `remnant_value_weight` es `process_time_penalty`.
* **Tudatosan unsupported/not_applied kulcsok:** pl. `priority_fulfilment_weight`, `inventory_consumption_penalty` `unsupported_metric` statusszal es `contribution=0`.
* **Route + wiring:** dedikalt evaluation endpointek, explicit scoring version path elsodlegesseggel, optionalis `project_scoring_selection` fallbackkal.
* **Smoke:** 9 csoportban bizonyitja az explicit pathot, deterministic replace viselkedest, fallbackot, missing metric agakat es a tiltott side effectek hianyat.

## 4) Verifikacio

### 4.1 Kotelezo parancs
* `./scripts/verify.sh --report codex/reports/web_platform/h3_e3_t1_run_evaluation_engine.md` -> PASS

### 4.2 Feladat-specifikus ellenorzes
* `python3 -m py_compile api/services/run_evaluations.py api/routes/run_evaluations.py api/main.py scripts/smoke_h3_e3_t1_run_evaluation_engine.py` -> PASS
* `python3 scripts/smoke_h3_e3_t1_run_evaluation_engine.py` -> PASS (`27/27`)

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo teszt/ellenorzes |
| --- | ---: | --- | --- | --- |
| #1 Letrejott az `app.run_evaluations` persisted truth reteg. | PASS | `supabase/migrations/20260324140000_h3_e3_t1_run_evaluation_engine.sql:L5-L20` | Tabla, indexek, bounded `total_score` check es RLS bekapcsolas bevezetve. | smoke 1 + migration scan |
| #2 Az evaluation egy runhoz reprodukalhato `total_score`-t tud kepezni. | PASS | `api/services/run_evaluations.py:L305-L579` | A score formula determinisztikus, normalizalt komponensekbol kepzett `total_score`-t ad. | smoke 3 |
| #3 A score komponensekre bontva, indokolhatoan kerul az `evaluation_jsonb`-be. | PASS | `api/services/run_evaluations.py:L284-L303`; `api/services/run_evaluations.py:L553-L573` | Komponensenkent `raw/normalized/weight/contribution/status`, plus score_summary mentodik. | smoke 1,8 |
| #4 Az engine explicit `scoring_profile_version_id` alapu kontraktussal mukodik. | PASS | `api/services/run_evaluations.py:L611-L619`; `api/routes/run_evaluations.py:L58-L92` | POST explicit versionnel ertekel, owner + active validacioval. | smoke 1 |
| #5 Optionalis project-level scoring selection fallback dokumentalt es ellenorzott. | PASS | `api/services/run_evaluations.py:L621-L643`; `api/services/run_evaluations.py:L693`; `api/routes/run_evaluations.py:L91` | Explicit ID hianyaban a projekt aktiv scoring selectionje hasznalhato, kulon flaggel jelezve. | smoke 7 |
| #6 Csak a mar letezo H1/H2 persisted metrikakra epul score-komponens. | PASS | `api/services/run_evaluations.py:L214-L251`; `api/services/run_evaluations.py:L317-L330` | Input forrasok kizarolag `app.run_metrics` es optionalis `app.run_manufacturing_metrics`. | smoke 5 |
| #7 A meg nem letezo H3 jelek nem kerulnek kitalalasra; unsupported/not_applied allapotban latszanak. | PASS | `api/services/run_evaluations.py:L440-L453`; `api/services/run_evaluations.py:L377-L393`; `api/services/run_evaluations.py:L410-L426` | Unsupported weightek `unsupported_metric`, hianyzo metric/threshold eseten `not_applied` + `contribution=0`. | smoke 5,8 |
| #8 A threshold eredmenyek es tie-breaker inputok elerhetok, de ranking nem keszul. | PASS | `api/services/run_evaluations.py:L455-L513`; `api/services/run_evaluations.py:L528-L547`; `api/services/run_evaluations.py:L564-L565` | Ismert threshold kulcsokra eredmeny keletkezik, tie-breaker input snapshot mentodik, ranking write nincs. | smoke 1,9 |
| #9 Az evaluation write viselkedese run-szintu idempotens replace. | PASS | `api/services/run_evaluations.py:L661-L685` | Ujraertekeleskor `run_id` alapu delete-then-insert replace tortenik egyetlen canonical sorral. | smoke 2 |
| #10 A task nem nyul a H1/H2 truth tablakhoz es nem csuszik at ranking/comparison scope-ba. | PASS | `api/services/run_evaluations.py:L668-L685`; `scripts/smoke_h3_e3_t1_run_evaluation_engine.py:L600-L635` | Write csak `app.run_evaluations`-be megy; ranking/batch/selection write side effect tiltott. | smoke 9 |
| #11 Keszult dedikalt service, route es task-specifikus smoke script. | PASS | `api/services/run_evaluations.py`; `api/routes/run_evaluations.py`; `scripts/smoke_h3_e3_t1_run_evaluation_engine.py:L259-L650` | Kulon service+route+smoke artefakt elkeszult a task scope-ban. | py_compile + smoke |
| #12 Checklist es report evidence-alapon ki van toltve. | PASS | `codex/codex_checklist/web_platform/h3_e3_t1_run_evaluation_engine.md`; jelen report | A canvas DoD pontok 1:1 evidence referenciaval szerepelnek. | jelen report |
| #13 `./scripts/verify.sh --report ...` PASS. | PASS | `codex/reports/web_platform/h3_e3_t1_run_evaluation_engine.verify.log` | A kotelezo wrapper quality gate lefutott es zold. | `./scripts/verify.sh --report ...` |

## 6) IO contract / mintak

Nem relevans.

## 7) Doksi szinkron

Nem relevans.

## 8) Advisory notes

- Ez a task szandekosan csak a `run_evaluations` truth reteget szallitja; nincs ranking/comparison/business-metrics workflow.
- A `total_score` bounded normalizalast hasznal, igy a nyers count metrikak nem nyomjak el a tobbi komponest.
- Az explicit `scoring_profile_version_id` ut az elsodleges kontraktus; a project-level selection fallback csak convenience.
- A most nem persisted inputot igenylo scoring kulcsok explicit `unsupported_metric` allapotban maradnak, csendes adatvesztes nelkul.

## 9) Follow-ups

- H3-E4: ranking/comparison reteg bevezetese mar a persisted `run_evaluations` truthra epitve.
- H3-E5: business metric truth bevezetese utan uj scoring komponensek aktivalasa.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-03-26T21:55:58+01:00 → 2026-03-26T21:59:34+01:00 (216s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/h3_e3_t1_run_evaluation_engine.verify.log`
- git: `main@6d8173f`
- módosított fájlok (git status): 11

**git diff --stat**

```text
 api/main.py | 2 ++
 1 file changed, 2 insertions(+)
```

**git status --porcelain (preview)**

```text
 M api/main.py
?? api/routes/run_evaluations.py
?? api/services/run_evaluations.py
?? canvases/web_platform/h3_e3_t1_run_evaluation_engine.md
?? codex/codex_checklist/web_platform/h3_e3_t1_run_evaluation_engine.md
?? codex/goals/canvases/web_platform/fill_canvas_h3_e3_t1_run_evaluation_engine.yaml
?? codex/prompts/web_platform/h3_e3_t1_run_evaluation_engine/
?? codex/reports/web_platform/h3_e3_t1_run_evaluation_engine.md
?? codex/reports/web_platform/h3_e3_t1_run_evaluation_engine.verify.log
?? scripts/smoke_h3_e3_t1_run_evaluation_engine.py
?? supabase/migrations/20260324140000_h3_e3_t1_run_evaluation_engine.sql
```

<!-- AUTO_VERIFY_END -->
