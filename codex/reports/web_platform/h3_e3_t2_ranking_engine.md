# Report — h3_e3_t2_ranking_engine

**Status:** PASS

## 1) Meta

* **Task slug:** `h3_e3_t2_ranking_engine`
* **Kapcsolodo canvas:** `canvases/web_platform/h3_e3_t2_ranking_engine.md`
* **Kapcsolodo goal YAML:** `codex/goals/canvases/web_platform/fill_canvas_h3_e3_t2_ranking_engine.yaml`
* **Futtas datuma:** 2026-03-26
* **Branch / commit:** main
* **Fokusz terulet:** Schema | Service | Routes | Scripts

## 2) Scope

### 2.1 Cel
- `app.run_ranking_results` persisted truth reteg bevezetese owner/project scoped RLS-sel.
- Batch-szintu ranking service bevezetese, amely csak persisted `run_batches` + `run_batch_items` + `run_evaluations` truthra epul.
- Deterministic ranking policy (score DESC + tie-break + canonical fallback) es canonical replace write modell.
- Minimalis ranking route kontraktus (`POST/GET/DELETE`) es app router bekotes.
- Task-specifikus smoke es evidence-alapu checklist/report.

### 2.2 Nem-cel (explicit)
- `run_evaluations` ujraszamitasa vagy write.
- Batch orchestrator ujranyitasa vagy uj run inditas.
- Comparison projection / best-by-objective / selected-run workflow.
- Business metrics, remnant vagy inventory domain logika.

## 3) Valtozasok osszefoglaloja

### 3.1 Erintett fajlok

* **Migration:**
  * `supabase/migrations/20260324150000_h3_e3_t2_ranking_engine.sql`
* **Service:**
  * `api/services/run_rankings.py`
* **Route:**
  * `api/routes/run_rankings.py`
* **App registration:**
  * `api/main.py`
* **Scripts:**
  * `scripts/smoke_h3_e3_t2_ranking_engine.py`
* **Codex artefaktok:**
  * `canvases/web_platform/h3_e3_t2_ranking_engine.md`
  * `codex/goals/canvases/web_platform/fill_canvas_h3_e3_t2_ranking_engine.yaml`
  * `codex/prompts/web_platform/h3_e3_t2_ranking_engine/run.md`
  * `codex/codex_checklist/web_platform/h3_e3_t2_ranking_engine.md`
  * `codex/reports/web_platform/h3_e3_t2_ranking_engine.md`

### 3.2 Miert valtoztak?

* **Schema:** A `run_ranking_results` truth külön táblában lett bevezetve (`id`, `batch_id`, `run_id`, `rank_no`, `ranking_reason_jsonb`, `created_at`) batchen belüli egyediség és owner-scoped RLS policykkal.
* **Ranking input boundary:** A service csak persisted truthot olvas: `app.run_batches`, `app.run_batch_items`, `app.run_evaluations` (opcionálisan `app.scoring_profile_versions` tie-break policy-hoz). Új score-t nem számol.
* **Tie-break policy:** Elsődleges rendezés `total_score DESC`, majd profile tie-break kulcsok, majd canonical fallback (`utilization_ratio DESC`, `unplaced_ratio ASC`, `used_sheet_count ASC`, `estimated_process_time_s ASC`), végül `candidate_label ASC`, `run_id ASC`.
* **Auditálhatóság:** A `ranking_reason_jsonb` tartalmaz score snapshotot, scoring contextet, tie-break trace-t, warningokat és persisted evaluation referenciát.
* **Boundary-k:** Tudatosan nincs comparison/best-by-objective/selected-run/business-metrics scope.
* **Fail-fast:** Hiányzó evaluation és scoring-context mismatch esetén a ranking hibaággal leáll, részleges rangsort nem ír.

## 4) Verifikacio

### 4.1 Kotelezo parancs
* `./scripts/verify.sh --report codex/reports/web_platform/h3_e3_t2_ranking_engine.md` -> PASS

### 4.2 Feladat-specifikus ellenorzes
* `python3 -m py_compile api/services/run_rankings.py api/routes/run_rankings.py api/main.py scripts/smoke_h3_e3_t2_ranking_engine.py` -> PASS
* `python3 scripts/smoke_h3_e3_t2_ranking_engine.py` -> PASS (`24/24`)

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo teszt/ellenorzes |
| --- | ---: | --- | --- | --- |
| #1 Letrejott az `app.run_ranking_results` persisted truth reteg. | PASS | `supabase/migrations/20260324150000_h3_e3_t2_ranking_engine.sql:L5-L29` | A tabla, unique szabalyok (`batch_id,run_id` + `batch_id,rank_no`) es RLS bekapcsolasa implementalt. | smoke 1 |
| #2 Egy batch candidate-halmazahoz reprodukalhato ranking kepezheto. | PASS | `api/services/run_rankings.py:L469-L629` | A service batchenkent deterministic sorrendet kepez es persisted rangsort ir. | smoke 1,2,3 |
| #3 A ranking kizarolag a mar persisted batch + evaluation truthra epul. | PASS | `api/services/run_rankings.py:L135`; `api/services/run_rankings.py:L156`; `api/services/run_rankings.py:L173`; `api/services/run_rankings.py:L464` | Input forrasok: batch/batch-item/evaluation (+ opcionális scoring profile tie-break), explicit `score_recalculated_by_ranking=false`. | smoke 7 |
| #4 Hianyzo evaluation eseten a task nem gyart reszleges sorrendet. | PASS | `api/services/run_rankings.py:L511` | Missing evaluation esetén fail-fast hiba. | smoke 4 |
| #5 A batch-item scoring context es az evaluation scoring context konzisztenciaja ellenorzott. | PASS | `api/services/run_rankings.py:L528-L537` | Scoring version mismatch vagy null/nonnull konfliktus esetén ranking hiba. | smoke 5 |
| #6 Azonos `total_score` eseten deterministic tie-break logika ervenyesul. | PASS | `api/services/run_rankings.py:L41-L46`; `api/services/run_rankings.py:L320-L360`; `api/services/run_rankings.py:L571-L577` | Dokumentált fallback sorrend + comparator alapú rendezés, stabil tie-break terminal fallbackkal. | smoke 3 |
| #7 A `ranking_reason_jsonb` auditálhato indoklast es tie-break trace-et tarol. | PASS | `api/services/run_rankings.py:L422-L466` | Reason payloadban score snapshot, tie-break trace, warnings, evaluation referencia szerepel. | smoke 1 |
| #8 Keszult minimalis POST / GET (es ha kell DELETE) ranking backend contract. | PASS | `api/routes/run_rankings.py:L22`; `api/routes/run_rankings.py:L64`; `api/routes/run_rankings.py:L97`; `api/routes/run_rankings.py:L124`; `api/main.py:L25`; `api/main.py:L126` | Dedikalt ranking router + `main.py` bekotes, POST/GET/DELETE endpointtal. | py_compile PASS |
| #9 A task nem csuszik at comparison / selected-run / business-metrics scope-ba. | PASS | `api/services/run_rankings.py:L590-L610`; `scripts/smoke_h3_e3_t2_ranking_engine.py:L589-L630` | Write csak `app.run_ranking_results`, tiltott tabellekbe nincs side effect. | smoke 7 |
| #10 Keszult task-specifikus smoke script. | PASS | `scripts/smoke_h3_e3_t2_ranking_engine.py:L300-L674` | 8 tesztcsoport lefedi a ranking success/fail-fast/scope boundary eseteket. | `python3 scripts/smoke_h3_e3_t2_ranking_engine.py` |
| #11 Checklist es report evidence-alapon frissitve. | PASS | `codex/codex_checklist/web_platform/h3_e3_t2_ranking_engine.md`; jelen report | A canvas DoD pontok 1:1 evidenciával szerepelnek. | jelen report |
| #12 `./scripts/verify.sh --report codex/reports/web_platform/h3_e3_t2_ranking_engine.md` PASS. | PASS | `codex/reports/web_platform/h3_e3_t2_ranking_engine.verify.log` | A kötelező wrapper gate lefutott zölden. | `./scripts/verify.sh --report ...` |

## 6) IO contract / mintak

Nem relevans.

## 7) Doksi szinkron

Nem relevans.

## 8) Advisory notes

- A ranking engine kizárólag persisted evaluation truth-ot rangsorol; nem keveri össze az evaluation számítással.
- A scoring context mismatch explicit fail-fast, így a batch nem kerül csendes, kevert ranking állapotba.
- A tie-break policy kódolt és determinisztikus, így ugyanarra a batch truth-ra stabil sorrend adódik.
- A `ranking_reason_jsonb` rövid, de auditálható; nem duplikálja teljesen az evaluation payloadot.

## 9) Follow-ups

- H3-E3-T3: best-by-objective projection bevezetése a már persisted `run_ranking_results` truth-ra építve.
- H3-E5/H3-E6: comparison/business/review workflow rétegek bekötése ranking truth fölé, külön scope-ban.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-03-26T22:33:51+01:00 → 2026-03-26T22:37:34+01:00 (223s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/h3_e3_t2_ranking_engine.verify.log`
- git: `main@bc1711b`
- módosított fájlok (git status): 11

**git diff --stat**

```text
 api/main.py | 2 ++
 1 file changed, 2 insertions(+)
```

**git status --porcelain (preview)**

```text
 M api/main.py
?? api/routes/run_rankings.py
?? api/services/run_rankings.py
?? canvases/web_platform/h3_e3_t2_ranking_engine.md
?? codex/codex_checklist/web_platform/h3_e3_t2_ranking_engine.md
?? codex/goals/canvases/web_platform/fill_canvas_h3_e3_t2_ranking_engine.yaml
?? codex/prompts/web_platform/h3_e3_t2_ranking_engine/
?? codex/reports/web_platform/h3_e3_t2_ranking_engine.md
?? codex/reports/web_platform/h3_e3_t2_ranking_engine.verify.log
?? scripts/smoke_h3_e3_t2_ranking_engine.py
?? supabase/migrations/20260324150000_h3_e3_t2_ranking_engine.sql
```

<!-- AUTO_VERIFY_END -->
