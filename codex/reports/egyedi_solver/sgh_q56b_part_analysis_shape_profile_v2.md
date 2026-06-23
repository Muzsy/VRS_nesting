STATUS: PASS

# Q56B — PartAnalysis / ShapeProfileV2 — Report

> Implementálva és verifikálva. `verify.sh` **PASS** (exit 0, determinizmus 10/10 byte-azonos → nincs
> regresszió). A `PartAnalysis` réteg újrahasználja a `PartShapeProfile`-t és a Q56A
> `OrientationCatalog`-ot (nem duplikál), part-típusonként egyszer derivál soft döntéstámogató jeleket.

## 1) Meta

- **Task slug:** `sgh_q56b_part_analysis_shape_profile_v2`
- **Kapcsolódó canvas:** `canvases/egyedi_solver/sgh_q56b_part_analysis_shape_profile_v2.md`
- **Kapcsolódó goal YAML:** `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q56b_part_analysis_shape_profile_v2.yaml`
- **Futás dátuma:** 2026-06-22
- **Branch / commit:** `main@84eea82` (working tree)
- **Fókusz terület:** `Solver preprocessing | Analysis layer`

## 2) Scope

### 2.1 Cél
- Part-szintű analízis réteg (PartAnalysis/ShapeProfileV2) a meglévő profil + kontúrfeature fölött.
- Soft döntéstámogató jelek, shape tag-ek, fit-difficulty, family kulcs, diagnosztikával.

### 2.2 Nem-cél
- Final placement átírása; PairCompatibilityIndex/SheetFeasibilityHints számítása; cavity prepack Rustban.

## 3) Changed files

- **Rust:** `rust/vrs_solver/src/optimizer/sparrow/part_analysis.rs` (új), `.../mod.rs`,
  `.../model.rs`, `.../shape_profile.rs`, `rust/vrs_solver/src/io.rs`,
  `rust/vrs_solver/tests/sparrow_part_analysis.rs` (új)
- **Artifacts:** `artifacts/benchmarks/sgh_q56b/part_analysis_summary.json`
- **Docs/Codex:** ez a report + checklist

## 4) Verification commands

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml part_analysis
cargo test --manifest-path rust/vrs_solver/Cargo.toml --test sparrow_one_part_sheet_edge
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q56b_part_analysis_shape_profile_v2.md
```

## 5) DoD → Evidence Matrix

| DoD pont | Státusz | Bizonyíték (path + line) | Magyarázat | Kapcsolódó ellenőrzés |
| -------- | ------: | ------------------------ | ---------- | --------------------- |
| PartAnalysis létezik + integrált | PASS | `part_analysis.rs` (struct + compute), `model.rs:39` (mező), `model.rs:312-317` (push) | Rc<PartAnalysis> az SPInstance-en, part-típusonként egyszer | `cargo test part_analysis` (5+1 ok) |
| ShapeProfile/ContourFeature újrahasználat | PASS | `part_analysis.rs` `Rc::clone(shape_profile)` + reuse summary | Nem duplikál: a profil Rc-jét megosztja, mezőit verbatim olvassa | `reuses_shape_profile_values` |
| fit_difficulty külön riportolva | PASS | artifact: LV8 fit 0.6274 vs priority 0.6153; `fit_difficulty_components` blokk | Külön, dekomponált, explainable score | `fit_difficulty_is_deterministic_and_separate_from_priority` |
| Tag-ek geometriából (nem part-ID) | PASS | `part_analysis.rs` compute tag-derivation csak sp.*/summary mezőkből | LV8 tags: critical_large, high_interlock_potential, orientation_sensitive, edge_alignable… | `large_part_is_tagged...`, `tiny_filler_is_not_an_anchor` |
| hole_free_solver_input rögzítve | PASS | `part_analysis.rs` `crate::item::part_has_holes(part)`; artifact `hole_free_solver_input=true` | Worker prepack tisztelete; csak megfigyelt állapot | integ. teszt |
| Top kritikus partok artifact | PASS | `artifacts/benchmarks/sgh_q56b/part_analysis_summary.json` | by_priority/by_fit/by_interlock listák + per-part rekordok | `tests/sparrow_part_analysis.rs` |
| Q55B proof nem regresszál | PASS | determinizmus 10/10 byte-azonos (AUTO_VERIFY) | placement viselkedés változatlan; gate off byte-azonos | `verify.sh` PASS |

## 6) Task-specific evidence

- Top critical parts (priority): `["Lv8_11612_6db"]` (a reprezentatív 3-part halmazból egyetlen kritikus).
- Top critical parts (fit difficulty): `["Lv8_11612_6db"]` — fit 0.6274.
- LV8 soft jelek: orientation_sensitivity 0.7753, interlock_potential 0.8071, critical_anchor (span-driven),
  family_key azonos geometriára stabil (`family_key_is_stable_for_same_geometry`).
- Soft-only megerősítés: a `PartAnalysis` egyetlen mezője sem fogyasztódik placement/collision úton
  (read-only az SPInstance-en); ezért a teljes suite + determinizmus byte-azonos.

## 7) Advisory / Deviations

- **DEVIATION (io.rs):** mint Q56A-nál, az io.rs production export szándékosan érintetlen
  (determinizmus-hash védelme). A `part_analysis_summary.json` az integrációs teszt artifactjából áll
  elő; a réteg solver-adathoz kötött (`SPInstance.part_analysis`).
- A `cavity_prepack_bridge_status` itt csak a megfigyelt hole-free állapotot rögzíti
  (`hole_free_observed`); a teljes worker bridge-szerződés a Q56B2 feladata.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-06-22T23:52:12+02:00 → 2026-06-22T23:55:58+02:00 (226s)
- parancs: `./scripts/check.sh`
- log: `/mnt/workspace/VRS_nesting/codex/reports/egyedi_solver/sgh_q56b_part_analysis_shape_profile_v2.verify.log`
- git: `main@84eea82`
- módosított fájlok (git status): 71

**git diff --stat**

```text
 .../src/optimizer/sparrow/bpp_reduction.rs         |  8 +++++
 .../src/optimizer/sparrow/fixed_sheet.rs           |  4 +++
 rust/vrs_solver/src/optimizer/sparrow/mod.rs       |  4 +++
 rust/vrs_solver/src/optimizer/sparrow/model.rs     | 41 ++++++++++++++++++++++
 rust/vrs_solver/src/optimizer/sparrow/tests.rs     | 10 ++++--
 5 files changed, 65 insertions(+), 2 deletions(-)
```

**git status --porcelain (preview)**

```text
 M rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs
 M rust/vrs_solver/src/optimizer/sparrow/fixed_sheet.rs
 M rust/vrs_solver/src/optimizer/sparrow/mod.rs
 M rust/vrs_solver/src/optimizer/sparrow/model.rs
 M rust/vrs_solver/src/optimizer/sparrow/tests.rs
?? artifacts/benchmarks/sgh_q56a/
?? artifacts/benchmarks/sgh_q56b/
?? canvases/egyedi_solver/sgh_q56_q60_preprocessing_package_scaffold.md
?? canvases/egyedi_solver/sgh_q56_q60_preprocessing_task_index.md
?? canvases/egyedi_solver/sgh_q56a_orientation_catalog_alap.md
?? canvases/egyedi_solver/sgh_q56b2_cavity_prepack_bridge_hints.md
?? canvases/egyedi_solver/sgh_q56b_part_analysis_shape_profile_v2.md
?? canvases/egyedi_solver/sgh_q56c_sheet_edge_placement_catalog_edge_corner_anchor_candidates.md
?? canvases/egyedi_solver/sgh_q57a_pair_compatibility_index_critical_only.md
?? canvases/egyedi_solver/sgh_q57b_pair_candidates_to_interlock_role.md
?? canvases/egyedi_solver/sgh_q58a_sheet_feasibility_hints.md
?? canvases/egyedi_solver/sgh_q58b_sheet_feasibility_hints_to_bpp_sheet_builder.md
?? canvases/egyedi_solver/sgh_q59_band_insert_true_extreme_slot_edge_placement.md
?? canvases/egyedi_solver/sgh_q60_critical_triple_simultaneous_admission.md
?? codex/codex_checklist/egyedi_solver/sgh_q56_q60_preprocessing_package_scaffold.md
?? codex/codex_checklist/egyedi_solver/sgh_q56a_orientation_catalog_alap.md
?? codex/codex_checklist/egyedi_solver/sgh_q56b2_cavity_prepack_bridge_hints.md
?? codex/codex_checklist/egyedi_solver/sgh_q56b_part_analysis_shape_profile_v2.md
?? codex/codex_checklist/egyedi_solver/sgh_q56c_sheet_edge_placement_catalog_edge_corner_anchor_candidates.md
?? codex/codex_checklist/egyedi_solver/sgh_q57a_pair_compatibility_index_critical_only.md
?? codex/codex_checklist/egyedi_solver/sgh_q57b_pair_candidates_to_interlock_role.md
?? codex/codex_checklist/egyedi_solver/sgh_q58a_sheet_feasibility_hints.md
?? codex/codex_checklist/egyedi_solver/sgh_q58b_sheet_feasibility_hints_to_bpp_sheet_builder.md
?? codex/codex_checklist/egyedi_solver/sgh_q59_band_insert_true_extreme_slot_edge_placement.md
?? codex/codex_checklist/egyedi_solver/sgh_q60_critical_triple_simultaneous_admission.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q56_q60_preprocessing_package_scaffold.yaml
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q56a_orientation_catalog_alap.yaml
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q56b2_cavity_prepack_bridge_hints.yaml
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q56b_part_analysis_shape_profile_v2.yaml
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q56c_sheet_edge_placement_catalog_edge_corner_anchor_candidates.yaml
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q57a_pair_compatibility_index_critical_only.yaml
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q57b_pair_candidates_to_interlock_role.yaml
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q58a_sheet_feasibility_hints.yaml
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q58b_sheet_feasibility_hints_to_bpp_sheet_builder.yaml
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q59_band_insert_true_extreme_slot_edge_placement.yaml
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q60_critical_triple_simultaneous_admission.yaml
?? codex/prompts/egyedi_solver/sgh_q56_q60_preprocessing_master_runner.md
?? codex/prompts/egyedi_solver/sgh_q56_q60_preprocessing_package_scaffold/
?? codex/prompts/egyedi_solver/sgh_q56a_orientation_catalog_alap/
?? codex/prompts/egyedi_solver/sgh_q56b2_cavity_prepack_bridge_hints/
?? codex/prompts/egyedi_solver/sgh_q56b_part_analysis_shape_profile_v2/
?? codex/prompts/egyedi_solver/sgh_q56c_sheet_edge_placement_catalog_edge_corner_anchor_candidates/
?? codex/prompts/egyedi_solver/sgh_q57a_pair_compatibility_index_critical_only/
?? codex/prompts/egyedi_solver/sgh_q57b_pair_candidates_to_interlock_role/
?? codex/prompts/egyedi_solver/sgh_q58a_sheet_feasibility_hints/
?? codex/prompts/egyedi_solver/sgh_q58b_sheet_feasibility_hints_to_bpp_sheet_builder/
?? codex/prompts/egyedi_solver/sgh_q59_band_insert_true_extreme_slot_edge_placement/
?? codex/prompts/egyedi_solver/sgh_q60_critical_triple_simultaneous_admission/
?? codex/reports/egyedi_solver/sgh_q56_q60_preprocessing_package_scaffold.md
?? codex/reports/egyedi_solver/sgh_q56_q60_preprocessing_package_scaffold.verify.log
?? codex/reports/egyedi_solver/sgh_q56a_orientation_catalog_alap.md
?? codex/reports/egyedi_solver/sgh_q56a_orientation_catalog_alap.verify.log
?? codex/reports/egyedi_solver/sgh_q56b2_cavity_prepack_bridge_hints.md
?? codex/reports/egyedi_solver/sgh_q56b_part_analysis_shape_profile_v2.md
?? codex/reports/egyedi_solver/sgh_q56b_part_analysis_shape_profile_v2.verify.log
```

<!-- AUTO_VERIFY_END -->
