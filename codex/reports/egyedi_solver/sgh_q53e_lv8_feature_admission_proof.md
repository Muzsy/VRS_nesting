# FAIL - SGH-Q53E LV8 feature admission proof

## 1) Meta

- **Task slug:** `sgh_q53e_lv8_feature_admission_proof`
- **Kapcsolodo canvas:** `canvases/egyedi_solver/sgh_q53e_lv8_feature_admission_proof.md`
- **Kapcsolodo goal YAML:** `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q53e_lv8_feature_admission_proof.yaml`
- **Futas datuma:** `2026-06-18`
- **Branch / commit:** `main@f287056`
- **Fokusz terulet:** `Q53 feature-first critical admission benchmark proof`

## 2) Scope

### 2.1 Cel

- A Q53 feature-first critical admission kontrollalt benchmark bizonyitasa a `6x Lv8_11612`, spacing `5`, continuous rotation fixture-on.
- Q51/Q52 builder-only kontroll es Q53 feature-on arm futtatasa ugyanabban az artifact formaban.
- SVG/PNG tablatervek, raw outputok, logok es diagnosztikai osszefoglalo generalasa.

### 2.2 Nem-cel

- Uj solver-strategia bevezetese a benchmark utan.
- Spacing `8` vagy full276 advisory arm kotelezove tetele.
- Production default gate-ek bekapcsolasa.

## 3) Valtozasok osszefoglalasa

### 3.1 Erintett fajlok

- `scripts/bench_sgh_q53_feature_admission.py`
- `artifacts/benchmarks/sgh_q53/q53_summary.json`
- `artifacts/benchmarks/sgh_q53/q53_report.md`
- `artifacts/benchmarks/sgh_q53/outputs/`
- `artifacts/benchmarks/sgh_q53/logs/`
- `artifacts/benchmarks/sgh_q53/renders/`

### 3.2 Miert valtoztak?

A Q53E feladat nem uj solver-mechanizmust kert, hanem a Q53B-Q53D feature path valos benchmark bizonyitasat. Ehhez uj runner kellett, amely temp inputtal dolgozik (nem hoz letre repo-beli `inputs/` konyvtarat), lefuttatja a builder-only es feature-first armokat, majd ugyanabban a benchmark artifact szerkezetben irja ki a summary/report/log/render csomagot, mint a Q51/Q52 taskok.

## 4) Verifikacio

### 4.1 Kotelezo parancs

- `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q53e_lv8_feature_admission_proof.md` -> PASS

### 4.2 Celozott parancsok

- `python3 scripts/bench_sgh_q53_feature_admission.py --case 6big --spacing 5 --time-limit 600` -> **FAIL**
  - `feature_off`: valid `6/6`, `3` sheet, `2` nagy darab / sheet
  - `feature_on`: valid `6/6`, `3` sheet, `2` nagy darab / sheet
  - feature path bizonyitek: `306` feature candidate, `14` critical feature attempt, `0` success, rejection summary `seed_not_clear=38`
- `cargo test --manifest-path rust/vrs_solver/Cargo.toml critical_feature_admission -- --nocapture` -> PASS

### 4.3 Ha valami kimaradt

Spacing `8` es full276 advisory kontrollt ebben a taskban nem futtattam, mert a YAML acceptance a spacing-`5` mechanizmus-gate-re fokuszalt. A primary acceptance igy is egyertelmuen eldolt.

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek | Magyarazat | Kapcsolodo ellenorzes |
| --- | --- | --- | --- | --- |
| Runner a YAML outputokon belul marad, es nem ir repo-beli benchmark inputokat | PASS | `scripts/bench_sgh_q53_feature_admission.py:L43-L113` | A futtato temp input JSON-t hasznal `TemporaryDirectory` alatt, mikozben csak az engedelyezett `outputs/logs/renders/report/summary` artefaktokat irja a repoba. | Kezi file read; `python3 -m py_compile scripts/bench_sgh_q53_feature_admission.py` |
| A benchmark SVG es PNG tablaterveket general mindket armhoz | PASS | `scripts/bench_sgh_q53_feature_admission.py:L169-L229`; `artifacts/benchmarks/sgh_q53/q53_report.md:L36-L51` | A render helper mindket futashoz per-sheet SVG/PNG-t es overview SVG/PNG-t irt, a report pedig a manifesteket es a PNG jelenletet rogzitette. | `python3 scripts/bench_sgh_q53_feature_admission.py --case 6big --spacing 5 --time-limit 600` |
| A feature-first critical path valoban futott es diagnosztikaban bizonyitott | PASS | `rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs:L1257-L1278`; `rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs:L1919-L2025`; `rust/vrs_solver/src/io.rs:L299-L321`; `artifacts/benchmarks/sgh_q53/q53_summary.json:L63-L128` | A builder path feature-first critical admission attempt/success/failure es refine-rejection mezoket exportal, a benchmarkben pedig `306` feature candidate es `14` critical feature attempt jelent meg. | `cargo test --manifest-path rust/vrs_solver/Cargo.toml critical_feature_admission -- --nocapture`; benchmark output read |
| A spacing-5 primary acceptance teljesul: legalabb egy sheeten 3 nagy darab | FAIL | `artifacts/benchmarks/sgh_q53/q53_summary.json:L120-L128`; `artifacts/benchmarks/sgh_q53/q53_report.md:L11-L26` | A feature-on arm vegig valid maradt, de a `max_big_per_sheet` ertek `2` maradt, ugyanugy mint a builder-only kontrollban. | `python3 scripts/bench_sgh_q53_feature_admission.py --case 6big --spacing 5 --time-limit 600` |
| A feature-on futas tovabbra is CDE-valid es explicit fail reasont ad | PASS | `artifacts/benchmarks/sgh_q53/q53_summary.json:L63-L128`; `artifacts/benchmarks/sgh_q53/logs/feature_on.log`; `rust/vrs_solver/tests/sparrow_critical_feature_admission.rs:L82-L105` | A feature-on kimenet `final_pairs=0`, `boundary_violations=0`, a close reason `deadline`, a rejection summary `seed_not_clear=38`, es a regression testek kulon ellenorzik az ilyen diag mezok jelenletet. | `cargo test --manifest-path rust/vrs_solver/Cargo.toml critical_feature_admission -- --nocapture`; benchmark output read |

## 6) IO contract / mintak

Publikus solver IO contract nem valtozott. A benchmark futtato csak additive artifactokat general: raw output JSON, log, render manifest, SVG, PNG, summary JSON es benchmark report. A Q53D-ben bevezetett additive BPP diagnostics mezoket olvassa ki, de nem modosit publikus input sformatumot.

## 7) Doksi szinkron

Kulon docs index frissites nem kellett. A benchmark report explicit rogzitette, hogy a feature-on arm a `VRS_SHEET_BUILDER=1`, `VRS_SHEET_BUILDER_FEATURE_CRITICAL=1`, `VRS_FEATURE_CANDIDATES=1` gate-ekkel futott.

## 8) Advisory notes

- A mechanizmus-gate eredmenye negativ, de nem csendes hiba: a feature path vegig bizonyitottan futott, csak a spacing-`5` acceptance nem teljesult.
- A ket arm kozel azonos falido alatt futott le (`555.1s` vs `555.8s`), es mindketto deadline close reasont adott, ami arra utal, hogy a jelenlegi Q53D feature path a megadott keresesi keretben nem talal jobb critical admissiont, mint a builder-only kontroll.


<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-06-18T01:12:08+02:00 → 2026-06-18T01:14:33+02:00 (145s)
- parancs: `./scripts/check.sh`
- log: `/mnt/workspace/VRS_nesting/codex/reports/egyedi_solver/sgh_q53e_lv8_feature_admission_proof.verify.log`
- git: `main@f287056`
- módosított fájlok (git status): 62

**git diff --stat**

```text
 rust/vrs_solver/src/io.rs                          |   33 +
 .../src/optimizer/sparrow/bpp_reduction.rs         | 1317 ++++++++++++++++----
 rust/vrs_solver/src/optimizer/sparrow/density.rs   |   34 +-
 .../src/optimizer/sparrow/diagnostics.rs           |   22 +
 .../src/optimizer/sparrow/eval/lbf_evaluator.rs    |   62 +
 .../src/optimizer/sparrow/eval/sep_evaluator.rs    |   24 +-
 .../sparrow/eval/specialized_cde_pipeline.rs       |   34 +-
 rust/vrs_solver/src/optimizer/sparrow/explore.rs   |   29 +-
 .../src/optimizer/sparrow/fixed_sheet.rs           |    8 +-
 rust/vrs_solver/src/optimizer/sparrow/mod.rs       |    6 +-
 rust/vrs_solver/src/optimizer/sparrow/model.rs     |   20 +-
 .../vrs_solver/src/optimizer/sparrow/multisheet.rs |  129 +-
 rust/vrs_solver/src/optimizer/sparrow/optimizer.rs |    3 +-
 .../src/optimizer/sparrow/quantify/tracker.rs      |   26 +-
 .../src/optimizer/sparrow/sample/best_samples.rs   |   18 +-
 .../src/optimizer/sparrow/sample/coord_descent.rs  |   56 +-
 .../src/optimizer/sparrow/sample/search.rs         |   73 +-
 .../optimizer/sparrow/sample/uniform_sampler.rs    |    6 +-
 rust/vrs_solver/src/optimizer/sparrow/separator.rs |   10 +-
 .../src/optimizer/sparrow/shape_profile.rs         |   94 +-
 rust/vrs_solver/src/optimizer/sparrow/tests.rs     |   17 +-
 rust/vrs_solver/src/optimizer/sparrow/worker.rs    |   76 +-
 22 files changed, 1698 insertions(+), 399 deletions(-)
```

**git status --porcelain (preview)**

```text
 M rust/vrs_solver/src/io.rs
 M rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs
 M rust/vrs_solver/src/optimizer/sparrow/density.rs
 M rust/vrs_solver/src/optimizer/sparrow/diagnostics.rs
 M rust/vrs_solver/src/optimizer/sparrow/eval/lbf_evaluator.rs
 M rust/vrs_solver/src/optimizer/sparrow/eval/sep_evaluator.rs
 M rust/vrs_solver/src/optimizer/sparrow/eval/specialized_cde_pipeline.rs
 M rust/vrs_solver/src/optimizer/sparrow/explore.rs
 M rust/vrs_solver/src/optimizer/sparrow/fixed_sheet.rs
 M rust/vrs_solver/src/optimizer/sparrow/mod.rs
 M rust/vrs_solver/src/optimizer/sparrow/model.rs
 M rust/vrs_solver/src/optimizer/sparrow/multisheet.rs
 M rust/vrs_solver/src/optimizer/sparrow/optimizer.rs
 M rust/vrs_solver/src/optimizer/sparrow/quantify/tracker.rs
 M rust/vrs_solver/src/optimizer/sparrow/sample/best_samples.rs
 M rust/vrs_solver/src/optimizer/sparrow/sample/coord_descent.rs
 M rust/vrs_solver/src/optimizer/sparrow/sample/search.rs
 M rust/vrs_solver/src/optimizer/sparrow/sample/uniform_sampler.rs
 M rust/vrs_solver/src/optimizer/sparrow/separator.rs
 M rust/vrs_solver/src/optimizer/sparrow/shape_profile.rs
 M rust/vrs_solver/src/optimizer/sparrow/tests.rs
 M rust/vrs_solver/src/optimizer/sparrow/worker.rs
?? README_SGH_Q53_TRUE_CONTOUR_FEATURE_ADMISSION_PACKAGE.md
?? artifacts/benchmarks/sgh_q53/
?? canvases/egyedi_solver/sgh_q53a_contour_feature_extraction.md
?? canvases/egyedi_solver/sgh_q53b_feature_candidate_generator.md
?? canvases/egyedi_solver/sgh_q53c_continuous_feature_refine.md
?? canvases/egyedi_solver/sgh_q53d_critical_admission_integration.md
?? canvases/egyedi_solver/sgh_q53e_lv8_feature_admission_proof.md
?? codex/codex_checklist/egyedi_solver/sgh_q53a_contour_feature_extraction.md
?? codex/codex_checklist/egyedi_solver/sgh_q53b_feature_candidate_generator.md
?? codex/codex_checklist/egyedi_solver/sgh_q53c_continuous_feature_refine.md
?? codex/codex_checklist/egyedi_solver/sgh_q53d_critical_admission_integration.md
?? codex/codex_checklist/egyedi_solver/sgh_q53e_lv8_feature_admission_proof.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q53a_contour_feature_extraction.yaml
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q53b_feature_candidate_generator.yaml
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q53c_continuous_feature_refine.yaml
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q53d_critical_admission_integration.yaml
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q53e_lv8_feature_admission_proof.yaml
?? codex/prompts/egyedi_solver/sgh_q53_true_contour_feature_admission_master_runner.md
?? codex/prompts/egyedi_solver/sgh_q53a_contour_feature_extraction/
?? codex/prompts/egyedi_solver/sgh_q53b_feature_candidate_generator/
?? codex/prompts/egyedi_solver/sgh_q53c_continuous_feature_refine/
?? codex/prompts/egyedi_solver/sgh_q53d_critical_admission_integration/
?? codex/prompts/egyedi_solver/sgh_q53e_lv8_feature_admission_proof/
?? codex/reports/egyedi_solver/sgh_q53a_contour_feature_extraction.md
?? codex/reports/egyedi_solver/sgh_q53a_contour_feature_extraction.verify.log
?? codex/reports/egyedi_solver/sgh_q53b_feature_candidate_generator.md
?? codex/reports/egyedi_solver/sgh_q53b_feature_candidate_generator.verify.log
?? codex/reports/egyedi_solver/sgh_q53c_continuous_feature_refine.md
?? codex/reports/egyedi_solver/sgh_q53c_continuous_feature_refine.verify.log
?? codex/reports/egyedi_solver/sgh_q53d_critical_admission_integration.md
?? codex/reports/egyedi_solver/sgh_q53d_critical_admission_integration.verify.log
?? codex/reports/egyedi_solver/sgh_q53e_lv8_feature_admission_proof.md
?? codex/reports/egyedi_solver/sgh_q53e_lv8_feature_admission_proof.verify.log
?? rust/vrs_solver/src/optimizer/sparrow/contour_features.rs
?? rust/vrs_solver/src/optimizer/sparrow/feature_candidate_generator.rs
?? rust/vrs_solver/tests/sparrow_contour_features.rs
?? rust/vrs_solver/tests/sparrow_critical_feature_admission.rs
?? rust/vrs_solver/tests/sparrow_feature_candidates.rs
```

<!-- AUTO_VERIFY_END -->
