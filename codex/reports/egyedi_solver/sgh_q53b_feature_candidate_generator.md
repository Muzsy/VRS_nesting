# PASS_WITH_NOTES - SGH-Q53B feature candidate generator

## 1) Meta

- **Task slug:** `sgh_q53b_feature_candidate_generator`
- **Kapcsolodo canvas:** `canvases/egyedi_solver/sgh_q53b_feature_candidate_generator.md`
- **Kapcsolodo goal YAML:** `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q53b_feature_candidate_generator.yaml`
- **Futas datuma:** `2026-06-18`
- **Branch / commit:** `main@f287056`
- **Fokusz terulet:** `Sparrow critical admission seeding`

## 2) Scope

### 2.1 Cel

- Q53A outer-contour feature-eibol valodi feature-to-feature placement seedeket generalni.
- Critical partoknal a feature seed legyen az elso probalt jeloltter, a regi contour-near bbox-corner ut kulon fallback maradjon.
- A BPP diagnosztikaban kulon szamlalni a feature seedeket es a bbox-corner fallback seedeket.
- Nyilvanos debug/test feluletet adni a generatorhoz, hogy a seedeles a solvertol fuggetlenul is bizonyithato legyen.

### 2.2 Nem-cel

- Production default viselkedes atirasa gate nelkul.
- CDE clearance szabalyok gyengitese vagy bbox collision shortcut bevezetese.
- Continuous refine logika befejezese; az a Q53C feladata.

## 3) Valtozasok osszefoglalasa

### 3.1 Erintett fajlok

- `rust/vrs_solver/src/optimizer/sparrow/feature_candidate_generator.rs`
- `rust/vrs_solver/src/optimizer/sparrow/mod.rs`
- `rust/vrs_solver/src/optimizer/sparrow/density.rs`
- `rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs`
- `rust/vrs_solver/src/optimizer/sparrow/diagnostics.rs`
- `rust/vrs_solver/src/io.rs`
- `rust/vrs_solver/tests/sparrow_feature_candidates.rs`

### 3.2 Miert valtoztak?

A Q48-Q52 contour-near ut csak neighbour-vertex -> moving-bbox-corner jelolteket adott. Q53B ehhez kepest kulon modulban general moving dominant-edge, protrusion, extreme-point es vertex alaprol sheet-edge vagy neighbour contour feature celokra seedeket, majd a critical admission density insertion ezt gated modon elore veszi, mikozben a bbox-corner fallback kulon diagnosztikaban megmarad.

## 4) Verifikacio

### 4.1 Kotelezo parancs

- `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q53b_feature_candidate_generator.md` -> pending a report auto-update blokkban

### 4.2 Celozott parancsok

- `cargo test --manifest-path rust/vrs_solver/Cargo.toml feature_candidate` -> PASS
- `cargo test --manifest-path rust/vrs_solver/Cargo.toml density` -> PASS

### 4.3 Ha valami kimaradt

Kulon benchmark vagy full LV8 proof meg nincs ebben a taskban; az a Q53E feladata. A feature path defaultban tovabbra is kikapcsolt (`VRS_FEATURE_CANDIDATES=1` kell hozza), igy regresszio-kockazatot nem vittem be az alap futasi utra.

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek | Magyarazat | Kapcsolodo ellenorzes |
| --- | --- | --- | --- | --- |
| Valodi feature candidate generator letrejott moving contour feature + sheet/neighbour feature alaprol | PASS | `rust/vrs_solver/src/optimizer/sparrow/feature_candidate_generator.rs:L15-L42`; `rust/vrs_solver/src/optimizer/sparrow/feature_candidate_generator.rs:L97-L177`; `rust/vrs_solver/src/optimizer/sparrow/feature_candidate_generator.rs:L195-L482`; `rust/vrs_solver/src/optimizer/sparrow/mod.rs:L28-L35`; `rust/vrs_solver/src/optimizer/sparrow/mod.rs:L56-L63` | Az uj modul kulon CandidateSeed metadata formatumot vezet be, tartalmaz debug API-t es solver-beli bekotest, majd sheet-edge es neighbour-feature seedeket general bounded/dedupalt listaba. | `cargo test --manifest-path rust/vrs_solver/Cargo.toml feature_candidate` |
| Moving bbox-corner nem primary feature path | PASS | `rust/vrs_solver/src/optimizer/sparrow/feature_candidate_generator.rs:L323-L406`; `rust/vrs_solver/tests/sparrow_feature_candidates.rs:L125-L148` | A generator protrusion, extreme-point es vertex feature-eket hasznal; nincs `bbox_corner` moving feature tipus. Az integration teszt ezt explicit ellenorzi. | `cargo test --manifest-path rust/vrs_solver/Cargo.toml feature_candidate` |
| Sheet-edge alignment candidate letrejon hosszabb/critical alkatresznel | PASS | `rust/vrs_solver/src/optimizer/sparrow/feature_candidate_generator.rs:L195-L272`; `rust/vrs_solver/tests/sparrow_feature_candidates.rs:L86-L98` | A dominant-edge -> sheet-edge seedek rotaciot es egyik tengelyen valodi feature-igazitast hasznalnak, nem csak egy sima BL corner seedinget. | `cargo test --manifest-path rust/vrs_solver/Cargo.toml feature_candidate` |
| Neighbour contour feature alignment letrejon concave/feature-rich parnal | PASS | `rust/vrs_solver/src/optimizer/sparrow/feature_candidate_generator.rs:L274-L406`; `rust/vrs_solver/tests/sparrow_feature_candidates.rs:L100-L123` | A generator dominant-edge, protrusion->concave-zone es point->vertex/edge projection utakat is general. Az integration teszt egy concave U + protrusion shape paron ellenorzi, hogy keletkezik neighbour-driven seed. | `cargo test --manifest-path rust/vrs_solver/Cargo.toml feature_candidate` |
| Critical admissionben a feature seed primary, bbox-corner kulon fallback | PASS | `rust/vrs_solver/src/optimizer/sparrow/density.rs:L195-L208`; `rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs:L1367-L1515` | A density insertion gated modon eloszor feature seedeket general es probal, utana kulon bbox fallback poziciokat, vegul uniform mintakat. A fallback kulon API nev alatt marad a regi contour-near path. | `cargo test --manifest-path rust/vrs_solver/Cargo.toml density` |
| Diagnosztika kulon szamolja a feature es bbox-corner seedeket | PASS | `rust/vrs_solver/src/optimizer/sparrow/diagnostics.rs:L213-L217`; `rust/vrs_solver/src/optimizer/sparrow/diagnostics.rs:L333-L337`; `rust/vrs_solver/src/io.rs:L299-L305`; `rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs:L1406-L1427`; `rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs:L1500-L1515` | Additive mezok kerultek be mind a belso SparrowDiagnostics-ba, mind a BPP exportalt IO diagnosztikaba, es a density insertion elfogadasnal a pair type is eltarolodik. | `cargo test --manifest-path rust/vrs_solver/Cargo.toml density`; `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q53b_feature_candidate_generator.md` |

## 6) IO contract / mintak

Publikus solver input schema nem valtozott. Az output csak additive BPP diagnostics mezokkel bovult: `bpp_feature_candidates_generated`, `bpp_feature_candidates_accepted`, `bpp_bbox_corner_candidates_generated`, `bpp_bbox_corner_candidates_accepted`, `bpp_accepted_feature_pair_type`.

## 7) Doksi szinkron

Kulon docs index frissites nem kellett. A task sajat canvas/YAML/checklist/report csomagja eleg a nyomkovethetoseghez.

## 8) Advisory notes

- A feature generator gate-je `VRS_FEATURE_CANDIDATES=1`; defaultban a production ut tovabbra is a Q52 viselkedest koveti.
- A workspace mar a task elott is tartalmazott nem-Q53B dirty fajlokat a Sparrow teruleten; ezeket nem revertaltam, csak a task output-listas fajljain dolgoztam.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-06-18T00:15:04+02:00 → 2026-06-18T00:17:37+02:00 (153s)
- parancs: `./scripts/check.sh`
- log: `/mnt/workspace/VRS_nesting/codex/reports/egyedi_solver/sgh_q53b_feature_candidate_generator.verify.log`
- git: `main@f287056`
- módosított fájlok (git status): 51

**git diff --stat**

```text
 rust/vrs_solver/src/io.rs                          |  17 +
 .../src/optimizer/sparrow/bpp_reduction.rs         | 963 +++++++++++++++++----
 rust/vrs_solver/src/optimizer/sparrow/density.rs   |  34 +-
 .../src/optimizer/sparrow/diagnostics.rs           |  10 +
 .../src/optimizer/sparrow/eval/sep_evaluator.rs    |  24 +-
 .../sparrow/eval/specialized_cde_pipeline.rs       |  34 +-
 rust/vrs_solver/src/optimizer/sparrow/explore.rs   |  29 +-
 .../src/optimizer/sparrow/fixed_sheet.rs           |   8 +-
 rust/vrs_solver/src/optimizer/sparrow/mod.rs       |   6 +-
 rust/vrs_solver/src/optimizer/sparrow/model.rs     |  20 +-
 .../vrs_solver/src/optimizer/sparrow/multisheet.rs | 129 ++-
 rust/vrs_solver/src/optimizer/sparrow/optimizer.rs |   3 +-
 .../src/optimizer/sparrow/quantify/tracker.rs      |  26 +-
 .../src/optimizer/sparrow/sample/best_samples.rs   |  18 +-
 .../src/optimizer/sparrow/sample/coord_descent.rs  |   8 +-
 .../src/optimizer/sparrow/sample/search.rs         |  73 +-
 .../optimizer/sparrow/sample/uniform_sampler.rs    |   6 +-
 rust/vrs_solver/src/optimizer/sparrow/separator.rs |  10 +-
 .../src/optimizer/sparrow/shape_profile.rs         |  94 +-
 rust/vrs_solver/src/optimizer/sparrow/tests.rs     |  17 +-
 rust/vrs_solver/src/optimizer/sparrow/worker.rs    |  76 +-
 21 files changed, 1258 insertions(+), 347 deletions(-)
```

**git status --porcelain (preview)**

```text
 M rust/vrs_solver/src/io.rs
 M rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs
 M rust/vrs_solver/src/optimizer/sparrow/density.rs
 M rust/vrs_solver/src/optimizer/sparrow/diagnostics.rs
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
?? rust/vrs_solver/src/optimizer/sparrow/contour_features.rs
?? rust/vrs_solver/src/optimizer/sparrow/feature_candidate_generator.rs
?? rust/vrs_solver/tests/sparrow_contour_features.rs
?? rust/vrs_solver/tests/sparrow_feature_candidates.rs
```

<!-- AUTO_VERIFY_END -->
