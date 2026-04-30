PASS_WITH_NOTES

## 1) Meta
- Task slug: `cavity_t8_production_regression_benchmark`
- Kapcsolodo canvas: `canvases/nesting_engine/cavity_t8_production_regression_benchmark.md`
- Kapcsolodo goal YAML: `codex/goals/canvases/nesting_engine/fill_canvas_cavity_t8_production_regression_benchmark.yaml`
- Futas datuma: `2026-04-29`
- Branch / commit: `main` (dirty working tree)
- Fokusz terulet: `legacy vs quality_cavity_prepack benchmark + rollout dontes`

## 2) Scope

### 2.1 Cel
- Legacy vs prepack osszehasonlitas evidence-first modon.
- Effective placer, fallback warning, placed/unplaced, elapsed es telemetry osszevetes.
- Rollout dontesi dokumentum frissitese.

### 2.2 Nem-cel (explicit)
- Nincs core nesting logic valtoztatas.
- Nincs timeout/work_budget "fix".
- Nincs warning suppression.
- Nincs `quality_default` profil atallitas.

## 3) Valtozasok osszefoglalasa

### 3.1 Erintett fajlok
- `scripts/smoke_cavity_t8_production_regression_benchmark.py`
- `docs/nesting_quality/cavity_prepack_rollout_decision.md`
- `codex/codex_checklist/nesting_engine/cavity_t8_production_regression_benchmark.md`
- `codex/reports/nesting_engine/cavity_t8_production_regression_benchmark.md`

### 3.2 Mi valtozott es miert
- Keszult T8 smoke script, amely:
  - explicit ellenorzi a T0 production replay blokk allapotat,
  - synthetic fallback inputon lefuttat egy `legacy` es egy `prepack` nesting engine replayt,
  - kimenti az osszehasonlito evidenciat (`tmp/cavity_t8_smoke_evidence.json`).
- Keszult rollout dontesi dokumentum:
  - `docs/nesting_quality/cavity_prepack_rollout_decision.md`,
  - kulon jelolve, hogy production snapshot blokk mellett default profile rollout nem indokolt.

## 4) Verifikacio

### 4.1 Feladatfuggo ellenorzes
- `python3 scripts/smoke_cavity_t8_production_regression_benchmark.py` -> PASS
- `python3 scripts/run_h3_quality_benchmark.py --plan-only --quality-profile quality_default --quality-profile quality_cavity_prepack --output tmp/cavity_t8_h3_plan_only.json` -> PASS

### 4.2 Legacy vs prepack evidence (synthetic fallback)
Forras: `tmp/cavity_t8_smoke_evidence.json`

| Metrika | Legacy | Prepack |
| --- | --- | --- |
| effective placer | `blf` | `nfp` |
| fallback warning | `true` | `false` |
| placed_count | `13` | `1` |
| unplaced_count | `0` | `0` |
| elapsed_sec_wall | `1.268` | `0.138` |
| NFP jel | `nfp_compute_calls=0`, `effective_placer=blf` | `cfr_calls=4`, `effective_placer=nfp` |

Megjegyzes:
- A synthetic prepack futasban a top-level placed darabok kisebbek lehetnek, mert a child darabok egy resze internal cavity reservationkent jelenik meg (nem top-level placementkent).

### 4.3 Production replay blokk evidence
- `codex/reports/nesting_engine/cavity_t0_artifact_recovery_and_baseline_replay.md`:
  - `Production run URL recovery valos API endpointen ujraellenorizve | FAIL`
  - `Production 1:1 replay uj letoltott snapshot alapjan | FAIL`
- `tmp/runs/20260330T224752Z_sample_dxf_1ebe1445/downloaded_artifact_urls.json`:
  - `solver_input` es `engine_meta` artifact URL `status=400`, `artifact url failed`.

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek | Magyarazat |
| --- | --- | --- | --- |
| Legacy replay allapot explicit | PASS | `tmp/cavity_t8_smoke_evidence.json` + T0 report | Legacy oldal fallback viselkedes benchmarkban merve; production replay blokk kulon jelolve. |
| Prepack replay allapot explicit | PASS | `tmp/cavity_t8_smoke_evidence.json` | Synthetic fallback inputon prepack futas bizonyitott. |
| Nincs globalis NFP->BLF fallback prepack modban | PASS | `tmp/cavity_t8_smoke_evidence.json` (`prepack.fallback_warning=false`, `effective_placer=nfp`) | A synthetic benchmarkben prepack mellett nincs fallback warning. |
| Unplaced count es okok osszehasonlitva | PASS | `tmp/cavity_t8_smoke_evidence.json` | Legacy/prepack oldalon unplaced adatok kiolvasva es riportalva. |
| Rollout dontes bizonyitekhoz kotott | PASS | `docs/nesting_quality/cavity_prepack_rollout_decision.md` | Default profile valtast a dokumentum blokkolja production replay evidence hianyaban. |
| `quality_default` valtozatlan ebben a taskban | PASS | diff review + policy fajlok erintetlenek | Nincs profile override vagy config valtoztatas. |
| Production 1:1 replay friss letoltott snapshot alapjan | FAIL | T0 FAIL + 400 artifact URL evidence | Kulso blokk tovabbra is fennall; ezert task statusz PASS_WITH_NOTES. |

## 6) Advisory notes
- A T8 technikai iranyt synthetic benchmark alatamasztja (prepack megszunteti a globalis fallback warningot), de ez nem eleg production rollout donteshez.
- A kovetkezo gate: artifact URL recovery + valos production snapshot replay ugyanarra a runra legacy vs prepack modban.

## 7) Follow-up
- Nyiss kulon follow-upot a production artifact URL/download blokk teljes felszamolasara (T0 folytatas).
- Utana futtasd ujra a T8 benchmarkot valos production snapshoton, es csak azutan hozz default profile rollout dontest.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-04-29T23:18:06+02:00 → 2026-04-29T23:20:49+02:00 (163s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/nesting_engine/cavity_t8_production_regression_benchmark.verify.log`
- git: `main@88a8760`
- módosított fájlok (git status): 28

**git diff --stat**

```text
 api/routes/files.py                       |  17 ++
 api/routes/runs.py                        |   4 +
 frontend/src/lib/api.ts                   |  28 +++
 frontend/src/lib/dxfIntakePresentation.ts |   2 +
 frontend/src/lib/types.ts                 |  19 ++
 frontend/src/pages/DxfIntakePage.tsx      |  21 ++
 frontend/src/pages/RunDetailPage.tsx      |  26 +++
 worker/result_normalizer.py               | 323 ++++++++++++++++++++++++++----
 8 files changed, 405 insertions(+), 35 deletions(-)
```

**git status --porcelain (preview)**

```text
 M api/routes/files.py
 M api/routes/runs.py
 M frontend/src/lib/api.ts
 M frontend/src/lib/dxfIntakePresentation.ts
 M frontend/src/lib/types.ts
 M frontend/src/pages/DxfIntakePage.tsx
 M frontend/src/pages/RunDetailPage.tsx
 M worker/result_normalizer.py
?? codex/codex_checklist/nesting_engine/cavity_t5_result_normalizer_expansion.md
?? codex/codex_checklist/nesting_engine/cavity_t6_svg_dxf_export_validation.md
?? codex/codex_checklist/nesting_engine/cavity_t7_ui_observability.md
?? codex/codex_checklist/nesting_engine/cavity_t8_production_regression_benchmark.md
?? codex/reports/nesting_engine/cavity_t5_result_normalizer_expansion.md
?? codex/reports/nesting_engine/cavity_t5_result_normalizer_expansion.verify.log
?? codex/reports/nesting_engine/cavity_t6_svg_dxf_export_validation.md
?? codex/reports/nesting_engine/cavity_t6_svg_dxf_export_validation.verify.log
?? codex/reports/nesting_engine/cavity_t7_ui_observability.md
?? codex/reports/nesting_engine/cavity_t7_ui_observability.verify.log
?? codex/reports/nesting_engine/cavity_t8_production_regression_benchmark.md
?? codex/reports/nesting_engine/cavity_t8_production_regression_benchmark.verify.log
?? docs/nesting_quality/cavity_prepack_rollout_decision.md
?? frontend/e2e/cavity_prepack_observability.spec.ts
?? samples/trial_run_quality/fixtures/
?? scripts/smoke_cavity_t5_result_normalizer_expansion.py
?? scripts/smoke_cavity_t6_svg_dxf_export_validation.py
?? scripts/smoke_cavity_t7_ui_observability.py
?? scripts/smoke_cavity_t8_production_regression_benchmark.py
?? tests/worker/test_result_normalizer_cavity_plan.py
```

<!-- AUTO_VERIFY_END -->
