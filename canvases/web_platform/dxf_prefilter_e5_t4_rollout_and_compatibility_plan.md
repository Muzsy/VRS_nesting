# DXF Prefilter E5-T4 — Rollout es kompatibilitasi terv

## Cel
A DXF prefilter lane backend es frontend current-code implementacioja mostanra bent van a repoban:
- backend prefilter pipeline (E2, E3) kesz;
- env-level rollout gate es legacy fallback (E3-T5) kesz;
- DXF Intake UI es a fo user-facing flow-k (E4, E5-T3) keszek.

A taskbontas szerint az E5-T4 celja mar **nem uj feature**, hanem egy repo-grounded, uzemeltethetö
**rollout es kompatibilitasi terv** letrehozasa. A feladatnak egyertelmuen rogzitenie kell:
- hogyan kapcsoljuk be / ki a prefilter lane-t biztonsagosan;
- hogyan marad kompatibilis a legacy upload -> direct geometry import utvonal;
- milyen support/debug checklist kell incident vagy rollback eseten;
- milyen meroszamokkal kovetjuk a bevezetest;
- mi az eventual legacy sunset terv, de current-code truth szerint megmarado fallbackkel.

Ez a task current-code truth szerint alapvetoen **docs/ops/safety** feladat. Nem kell uj product flow,
uj endpoint vagy uj persistence. A repoban mar letezo feature flag, fallback es UI gate viselkedeset
kell dokumentalni, operationalizalni es ellenorizheto runbookka alakitani.

## Miert most?
A jelenlegi repo-grounded helyzet:
- az E3-T5 ota a backend canonical flag (`API_DXF_PREFLIGHT_REQUIRED`) es a frontend build-time mirror
  (`VITE_DXF_PREFLIGHT_ENABLED`) bent van;
- a `complete_upload` ma rollout ON eseten preflight runtime-ot, OFF eseten legacy direct geometry importot indit;
- a `replace_file` flow rollout OFF eseten gate-elve van;
- a DXF Intake route/CTA rollout OFF eseten nem latszik;
- az E5-T2/E5-T3 mar route-level es browser-level bizonyitekot is ad a lane-re.

Ami jelenleg hianyzik, az nem kod, hanem **egyseges rollout truth**:
- nincs kulon dokumentum, ami leirja az ON/OFF matrixot;
- nincs egy helyen a support/debug runbook;
- nincs kimondva a legacy fallback statusza, a sunset elofeltetelei es a rollback menete;
- nincs egy helyen a rollout KPI-k es azok interpretationje.

Az E5-T4 helyes kovetkezo lepese ezert:
**egy repo-grounded rollout/compatibility runbook + support checklist + metrics terv + minimalis structural smoke**.

## Scope boundary

### In-scope
- Kulon dokumentum a DXF prefilter rollout es compatibility truthhoz.
- A jelenlegi ON/OFF viselkedesmatrix dokumentalasa:
  - backend finalize path,
  - replacement route gate,
  - frontend route/CTA visibility,
  - files/projection truth.
- Rollout fazisok / stage-ek leirasa current-code truth szerint.
- Rollback es emergency fallback eljaras dokumentalasa a meglovo env flagre epitve.
- Support/debug checklist dokumentalasa.
- KPI/meroszam terv dokumentalasa (pl. accepted/review/rejected aranyok, replacement volume, geometry import fallback activity).
- Legacy compatibility es eventual sunset criteria dokumentalasa.
- Minimalis task-specifikus structural smoke, amely bizonyitja, hogy a dokumentum a current-code flag/fallback truthra epul.

### Out-of-scope
- Uj backend feature flag vagy config mező.
- Uj frontend route/visibility logika.
- Uj endpoint, migration, persistence vagy analytics pipeline.
- Project-level rollout settings domain.
- UI redesign vagy uj support UI.
- E5-T2 / E5-T3 tesztek ujrairasa.
- A legacy fallback tenyleges eltavolitasa.

## Talalt relevans fajlok (meglevo kodhelyzet)
- `api/config.py`
  - canonical backend env gate: `API_DXF_PREFLIGHT_REQUIRED` (+ alias `DXF_PREFLIGHT_REQUIRED`).
- `api/routes/files.py`
  - `complete_upload` ON/OFF finalize branching;
  - `replace_file` route gate OFF eseten.
- `api/services/dxf_geometry_import.py`
  - legacy direct geometry import helper, amelyre a rollback/fallback epit.
- `frontend/src/lib/featureFlags.ts`
  - build-time mirror flag: `VITE_DXF_PREFLIGHT_ENABLED`.
- `frontend/src/App.tsx`
  - DXF Intake route visibility gate.
- `frontend/src/pages/ProjectDetailPage.tsx`
  - DXF Intake CTA visibility gate.
- `docs/web_platform/architecture/dxf_prefilter_v1_scope_and_boundary.md`
- `docs/web_platform/architecture/dxf_prefilter_api_contract_specification.md`
- `canvases/web_platform/dxf_prefilter_e3_t5_feature_flag_and_rollout_gate.md`
- `codex/reports/web_platform/dxf_prefilter_e3_t5_feature_flag_and_rollout_gate.md`
- `canvases/web_platform/dxf_prefilter_e5_t2_end_to_end_api_tests.md`
- `canvases/web_platform/dxf_prefilter_e5_t3_ui_smoke_and_integration_tests.md`

## Jelenlegi repo-grounded helyzetkep

### 1. A rollout gate mar implementalt
A repoban ma mar letezik a minimalis rollout gate:
- backend env gate;
- frontend visibility gate;
- legacy fallback path;
- replacement flow gate.

Ez azt jelenti, hogy E5-T4-ben nem kell uj rollout mechanizmust kitalalni.
A feladat a **mar implementalt truth operationalizalasa**.

### 2. A legacy ut meg nem sunsetelt
Current-code truth szerint rollout OFF eseten a source DXF finalize nem hal meg,
hanem visszaall a legacy direct geometry import helperre.
Ez nem tech debt veletlen, hanem tudatos compatibility bridge.
E5-T4-ben ezt dokumentalni kell:
- mikor hasznaljuk rollbackre;
- milyen korlatokkal jar;
- mikor lesz jogos a jovobeli eltavolitasa.

### 3. A frontend gate csak visibility gate
A `VITE_DXF_PREFLIGHT_ENABLED` current-code truth szerint nem runtime config,
csak build-time visibility gate. E5-T4-ben ezt tisztan ki kell mondani,
nehogy valaki runtime feature toggle-kent ertelmezze.

### 4. Support/debug jelenleg szetszort
A repo-ban mar van evidence a smoke-okban, reportokban es az E3-T5 logikaban,
de nincs egy helyen leirva:
- rollout ON/OFF ellenorzes parancsokkal;
- mit kell nezni replacement hiba eseten;
- mit kell nezni accepted/review/rejected aranyoknal;
- hogyan derul ki, hogy a frontend/backend flag szinkronban van-e.

### 5. Az E5-T4 current-code feladata docs-first
A helyes task itt nem uj backend teszt vagy frontend flow, hanem egy olyan dokumentacios/runbook csomag,
amit a support/qa/operator oldal tenylegesen hasznalni tud.

## Konkret elvarasok

### 1. Keszits kulon rollout es compatibility dokumentumot
Javasolt uj fajl:
- `docs/web_platform/architecture/dxf_prefilter_rollout_and_compatibility_plan.md`

A dokumentum legalabb ezeket tartalmazza:
- current-state summary;
- canonical flags es jelentesuk;
- ON/OFF behavior matrix;
- rollout fazisok/stage-ek;
- rollback/fallback eljaras;
- compatibility guarantees es current limitations;
- legacy sunset criteria;
- support/debug checklist;
- rollout meroszamok es interpretation.

### 2. A plan explicit current-code truthra epuljon
Kulon mondd ki a dokumentumban:
- backend canonical flag: `API_DXF_PREFLIGHT_REQUIRED`;
- alias: `DXF_PREFLIGHT_REQUIRED`;
- frontend build-time mirror: `VITE_DXF_PREFLIGHT_ENABLED`;
- rollout OFF eseten a `complete_upload` legacy geometry import fallbackot hasznal;
- rollout OFF eseten a `replace_file` gate-elve van;
- rollout OFF eseten a DXF Intake UI nem latszik.

### 3. ON/OFF matrix legyen egyertelmu es operativ
Minimum matrix sorok:
- Source DXF finalize viselkedes
- Replacement flow elerhetoseg
- DXF Intake route/CTA visibility
- Existing preflight projections varhato viselkedese
- Support elvart megfigyelesei

### 4. Rollout fazisok / stage-ek
Current-code grounded javaslat:
- Stage 0: dark launch / backend available, operator-only verification
- Stage 1: guarded rollout (flags ON a megfelelo kornyezetekben, support fokozott figyelemmel)
- Stage 2: prefilter-default operation (legacy fallback csak rollbackre)
- Stage 3: sunset-ready state (csak kriteriumok, a legacy helper meg jelenleg marad)

Nem kell ehhez uj system state vagy DB mező.
Ez dokumentacios/operational stage modell.

### 5. Support / debug checklist
Kulon checklist kell legalabb ezekre:
- backend flag allapot ellenorzese;
- frontend flag/build alignment ellenorzese;
- replacement route gate elvart viselkedese;
- accepted / review_required / rejected anomaliak kivizsgalasa;
- legacy fallback activity felismerese;
- minimalis verify/smoke parancsok.

### 6. KPI / rollout metric terv
Current-code truth szerint ne talalj ki uj analytics pipeline-t.
A dokumentum csak definialja a kovetendo meroszamokat es azok forrasat, pl.:
- accepted_for_import arany;
- preflight_review_required arany;
- preflight_rejected arany;
- replacement flow trigger volumen;
- rollout OFF eseten legacy fallback activity;
- diagnostics issue family trendek (ha a persisted summarybol kiolvashato).

Mondd ki azt is, hogy ezek kozul melyekhez van mar current-code forras, es melyekhez kellene kesobbi observability.

### 7. Legacy sunset criteria
Current-code truth szerint a fallback meg marad.
A dokumentumban csak a **sunset criteria** legyen benne, peldaul:
- stabil smoke/E2E coverage;
- elfogadhato accepted/review/rejected arany tobb egymast koveto release-ben;
- nincs kritikus replacement-flow regresszio;
- support/load tapasztalatok megfeleloek;
- rollback nelkul stabil futas meghatarozott ideig.

A helper tenyleges eltavolitasa nem resze ennek a tasknak.

### 8. Minimalis structural smoke
Javasolt uj fajl:
- `scripts/smoke_dxf_prefilter_e5_t4_rollout_and_compatibility_plan.py`

A smoke minimum bizonyitsa:
- letezik a rollout/compatibility doc;
- a doc explicit nevezi a current-code canonical flag-eket;
- a doc explicit kimondja a legacy fallback truthot;
- a doc tartalmaz support/debug checklist es metrics szekciot;
- a doc nem hazudik runtime frontend flagrol vagy project-level flagrol.

### 9. Report evidence
A report kulon terjen ki erre:
- miert docs/ops task a helyes E5-T4, nem uj feature;
- hogyan epit a mar implementalt E3-T5 gate-re;
- mi a current compatibility guarantee;
- miert csak sunset criteria, es nem legacy removal a task celja.

## DoD
- [ ] Letrejott a kulon `dxf_prefilter_rollout_and_compatibility_plan.md` dokumentum.
- [ ] A dokumentum explicit current-code truthra epul (backend flag, frontend mirror, legacy fallback, replacement gate).
- [ ] Van egyertelmu ON/OFF behavior matrix.
- [ ] Van rollout stage modell, rollback/fallback leiras es support/debug checklist.
- [ ] Van KPI / rollout metrics terv current-code forrasmegjelolessel.
- [ ] Van legacy sunset criteria szekcio, helper removal nelkul.
- [ ] Van task-specifikus structural smoke.
- [ ] A report evidencia-alapon rogzitette, hogy az E5-T4 docs/ops jellegu task.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e5_t4_rollout_and_compatibility_plan.md` PASS.

## Erintett fajlok / tervezett outputok
- `canvases/web_platform/dxf_prefilter_e5_t4_rollout_and_compatibility_plan.md`
- `codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e5_t4_rollout_and_compatibility_plan.yaml`
- `codex/prompts/web_platform/dxf_prefilter_e5_t4_rollout_and_compatibility_plan/run.md`
- `docs/web_platform/architecture/dxf_prefilter_rollout_and_compatibility_plan.md`
- `scripts/smoke_dxf_prefilter_e5_t4_rollout_and_compatibility_plan.py`
- `codex/codex_checklist/web_platform/dxf_prefilter_e5_t4_rollout_and_compatibility_plan.md`
- `codex/reports/web_platform/dxf_prefilter_e5_t4_rollout_and_compatibility_plan.md`
