# WIP - SGH-Q68 Anchor catalog production authority cutover

## Meta

- Task slug: `sgh_q68_anchor_catalog_production_authority_cutover`
- Canvas: `canvases/egyedi_solver/sgh_q68_anchor_catalog_production_authority_cutover.md`
- Goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q68_anchor_catalog_production_authority_cutover.yaml`
- Fokusz: `Q56C production authority cutover`

## Audit gap

- A production Anchor agban a catalog jelenleg csak akkor nyerhet, ha nincs skeleton feature
  gyoztes (`best_skeleton.is_none()`), vagyis fallback-only szerepben van.

## Valtozasok

- A production Anchor agban bekerult az explicit authority chooser: ha van feature- es catalog-score
  is, akkor ugyanabban a versenyben indulnak, es tie vagy jobb catalog-score eseten a catalog nyer
  ([rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs](/mnt/workspace/VRS_nesting/rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs:171),
  [bpp_reduction.rs](/mnt/workspace/VRS_nesting/rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs:2911)).
- A production diagnostics megkapta a Q68 versenymezoket, igy mar latszik, hogy lefutott-e az
  anchor authority verseny, milyen score-okkal, es melyik ut nyert
  ([rust/vrs_solver/src/io.rs](/mnt/workspace/VRS_nesting/rust/vrs_solver/src/io.rs:360)).
- Elkeszult a focused live-instance Q68 runner: ugyanazzal a real `SPInstance` /
  `OrientationCatalog` adatutvonallal general anchor-catalog es sheet-edge feature seedeket, majd
  artifact JSON-ba irja a preview-kat es a policy-peldakat
  ([rust/vrs_solver/tests/sparrow_q68_anchor_catalog_cutover.rs](/mnt/workspace/VRS_nesting/rust/vrs_solver/tests/sparrow_q68_anchor_catalog_cutover.rs:75),
  [artifacts/benchmarks/sgh_q68/anchor_catalog_production_cutover.json](/mnt/workspace/VRS_nesting/artifacts/benchmarks/sgh_q68/anchor_catalog_production_cutover.json:1)).
- A chooserre ket celzott unit teszt is bekerult: catalog nyeri a tie/better score eseteket, feature
  marad amikor a catalog rosszabb
  ([bpp_reduction.rs](/mnt/workspace/VRS_nesting/rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs:4770)).

## DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo teszt/ellenorzes |
| -------- | ------: | ------------------------ | ---------- | --------------------------- |
| Q56C Anchor catalog first-class authority wiring megvalositva | PASS | [bpp_reduction.rs](/mnt/workspace/VRS_nesting/rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs:171), [bpp_reduction.rs](/mnt/workspace/VRS_nesting/rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs:2911) | A catalog mar nem fallback-only: ugyanazzal a free-space score versennyel indul, mint a feature winner, es tie/better eseten atveszi az authorityt. | `cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib anchor_catalog_wins_ties_and_better_scores -- --nocapture`; `cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib anchor_feature_kept_when_catalog_score_is_worse -- --nocapture` |
| A winnerrol explicit Q68 diagnosztika keszul | PASS | [io.rs](/mnt/workspace/VRS_nesting/rust/vrs_solver/src/io.rs:360), [bpp_reduction.rs](/mnt/workspace/VRS_nesting/rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs:2906) | A bpp diagnostics most rogzitik a competition flaget, a feature/catalog score-okat es a kivalasztott utat. | `cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib anchor_catalog_wins_ties_and_better_scores -- --nocapture` |
| Elkeszult a focused live-instance artifact a real candidate source-okrol | PASS | [sparrow_q68_anchor_catalog_cutover.rs](/mnt/workspace/VRS_nesting/rust/vrs_solver/tests/sparrow_q68_anchor_catalog_cutover.rs:75), [anchor_catalog_production_cutover.json](/mnt/workspace/VRS_nesting/artifacts/benchmarks/sgh_q68/anchor_catalog_production_cutover.json:1) | A runner ugyanazon LV8 fixture-bol epiti a live `SPInstance`-et, majd kiirja a catalog es a sheet-edge feature preview-kat, koztuk fractional rotacios peldakkal. | `cargo test --manifest-path rust/vrs_solver/Cargo.toml --test sparrow_q68_anchor_catalog_cutover -- --nocapture` |

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-06-24T15:13:15+02:00 → 2026-06-24T15:21:44+02:00 (509s)
- parancs: `./scripts/check.sh`
- log: `/mnt/workspace/VRS_nesting/codex/reports/egyedi_solver/sgh_q68_anchor_catalog_production_authority_cutover.verify.log`
- git: `main@066fd1e`
- módosított fájlok (git status): 102

**git diff --stat**

```text
 .../sgh_q60/critical_group_admission.json          |   28 +-
 .../sgh_q61/critical_3part_diagnostics_summary.md  |    8 +-
 .../sgh_q61/critical_3part_real_spacing.json       |   16 +-
 .../sgh_q61/critical_3part_real_spacing.svg        |   12 +-
 .../sgh_q61/critical_3part_spacing0.json           |   16 +-
 .../benchmarks/sgh_q61/critical_3part_spacing0.svg |   12 +-
 rust/vrs_solver/src/adapter.rs                     |  560 ++++++--
 rust/vrs_solver/src/io.rs                          |   52 +
 rust/vrs_solver/src/optimizer/cde_adapter.rs       |  159 ++-
 .../src/optimizer/sparrow/band_insert_slot_edge.rs |  122 +-
 .../src/optimizer/sparrow/bpp_reduction.rs         | 1415 +++++++++++++++++---
 .../src/optimizer/sparrow/critical_simultaneous.rs |  262 +++-
 .../sparrow/feature_candidate_generator.rs         |  146 +-
 .../src/optimizer/sparrow/interlock_pair.rs        |  280 +++-
 rust/vrs_solver/src/optimizer/sparrow/mod.rs       |    4 +-
 .../src/optimizer/sparrow/one_part_edge.rs         |   65 +-
 .../src/optimizer/sparrow/orientation_catalog.rs   |   46 +-
 .../src/optimizer/sparrow/part_analysis.rs         |   62 +-
 .../src/optimizer/sparrow/quantify/pair_matrix.rs  |  304 +++--
 .../sparrow/sheet_edge_placement_catalog.rs        |   64 +-
 .../src/optimizer/sparrow/sheet_feasibility.rs     |   60 +-
 .../src/optimizer/sparrow/sheet_feasibility_bpp.rs |   36 +-
 .../src/optimizer/sparrow/sheet_skeleton.rs        |   60 +-
 rust/vrs_solver/src/optimizer/sparrow/tests.rs     |    8 +-
 rust/vrs_solver/src/sheet.rs                       |   55 +-
 rust/vrs_solver/src/technology/spacing.rs          |   15 +-
 rust/vrs_solver/src/technology/spacing_geometry.rs |   11 +-
 .../tests/sparrow_band_insert_slot_edge.rs         |   15 +-
 rust/vrs_solver/tests/sparrow_contour_features.rs  |   12 +-
 .../tests/sparrow_critical_feature_admission.rs    |    4 +-
 .../sparrow_critical_simultaneous_admission.rs     |   24 +-
 rust/vrs_solver/tests/sparrow_density_admission.rs |   40 +-
 .../vrs_solver/tests/sparrow_density_compaction.rs |   33 +-
 .../vrs_solver/tests/sparrow_feature_candidates.rs |   29 +-
 .../tests/sparrow_finite_stock_multisheet.rs       |  175 ++-
 .../tests/sparrow_interlock_pair_candidates.rs     |    4 +-
 .../tests/sparrow_one_part_sheet_edge.rs           |   42 +-
 .../tests/sparrow_orientation_catalog.rs           |    9 +-
 .../tests/sparrow_pair_compatibility_index.rs      |   40 +-
 rust/vrs_solver/tests/sparrow_part_analysis.rs     |   57 +-
 .../sparrow_q61_integrated_critical_admission.rs   |  106 +-
 rust/vrs_solver/tests/sparrow_role_routing.rs      |   24 +-
 rust/vrs_solver/tests/sparrow_shape_profile.rs     |   32 +-
 rust/vrs_solver/tests/sparrow_sheet_builder.rs     |   21 +-
 rust/vrs_solver/tests/sparrow_sheet_edge_anchor.rs |   10 +-
 .../tests/sparrow_sheet_edge_anchor_catalog.rs     |   31 +-
 .../sparrow_sheet_feasibility_bpp_integration.rs   |   20 +-
 .../tests/sparrow_sheet_feasibility_hints.rs       |   18 +-
 rust/vrs_solver/tests/sparrow_sheet_skeleton.rs    |   26 +-
 .../tests/sparrow_single_sheet_validation.rs       |   40 +-
 .../tests/technology_clearance_policy.rs           |   35 +-
 rust/vrs_solver/tests/technology_part_spacing.rs   |   15 +-
 rust/vrs_solver/tests/technology_sheet_margin.rs   |   54 +-
 .../tests/technology_spacing_geometry.rs           |  118 +-
 .../tests/technology_spacing_offset_lv8.rs         |   42 +-
 55 files changed, 3942 insertions(+), 1012 deletions(-)
```

**git status --porcelain (preview)**

```text
 M artifacts/benchmarks/sgh_q60/critical_group_admission.json
 M artifacts/benchmarks/sgh_q61/critical_3part_diagnostics_summary.md
 M artifacts/benchmarks/sgh_q61/critical_3part_real_spacing.json
 M artifacts/benchmarks/sgh_q61/critical_3part_real_spacing.svg
 M artifacts/benchmarks/sgh_q61/critical_3part_spacing0.json
 M artifacts/benchmarks/sgh_q61/critical_3part_spacing0.svg
 M rust/vrs_solver/src/adapter.rs
 M rust/vrs_solver/src/io.rs
 M rust/vrs_solver/src/optimizer/cde_adapter.rs
 M rust/vrs_solver/src/optimizer/sparrow/band_insert_slot_edge.rs
 M rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs
 M rust/vrs_solver/src/optimizer/sparrow/critical_simultaneous.rs
 M rust/vrs_solver/src/optimizer/sparrow/feature_candidate_generator.rs
 M rust/vrs_solver/src/optimizer/sparrow/interlock_pair.rs
 M rust/vrs_solver/src/optimizer/sparrow/mod.rs
 M rust/vrs_solver/src/optimizer/sparrow/one_part_edge.rs
 M rust/vrs_solver/src/optimizer/sparrow/orientation_catalog.rs
 M rust/vrs_solver/src/optimizer/sparrow/part_analysis.rs
 M rust/vrs_solver/src/optimizer/sparrow/quantify/pair_matrix.rs
 M rust/vrs_solver/src/optimizer/sparrow/sheet_edge_placement_catalog.rs
 M rust/vrs_solver/src/optimizer/sparrow/sheet_feasibility.rs
 M rust/vrs_solver/src/optimizer/sparrow/sheet_feasibility_bpp.rs
 M rust/vrs_solver/src/optimizer/sparrow/sheet_skeleton.rs
 M rust/vrs_solver/src/optimizer/sparrow/tests.rs
 M rust/vrs_solver/src/sheet.rs
 M rust/vrs_solver/src/technology/spacing.rs
 M rust/vrs_solver/src/technology/spacing_geometry.rs
 M rust/vrs_solver/tests/sparrow_band_insert_slot_edge.rs
 M rust/vrs_solver/tests/sparrow_contour_features.rs
 M rust/vrs_solver/tests/sparrow_critical_feature_admission.rs
 M rust/vrs_solver/tests/sparrow_critical_simultaneous_admission.rs
 M rust/vrs_solver/tests/sparrow_density_admission.rs
 M rust/vrs_solver/tests/sparrow_density_compaction.rs
 M rust/vrs_solver/tests/sparrow_feature_candidates.rs
 M rust/vrs_solver/tests/sparrow_finite_stock_multisheet.rs
 M rust/vrs_solver/tests/sparrow_interlock_pair_candidates.rs
 M rust/vrs_solver/tests/sparrow_one_part_sheet_edge.rs
 M rust/vrs_solver/tests/sparrow_orientation_catalog.rs
 M rust/vrs_solver/tests/sparrow_pair_compatibility_index.rs
 M rust/vrs_solver/tests/sparrow_part_analysis.rs
 M rust/vrs_solver/tests/sparrow_q61_integrated_critical_admission.rs
 M rust/vrs_solver/tests/sparrow_role_routing.rs
 M rust/vrs_solver/tests/sparrow_shape_profile.rs
 M rust/vrs_solver/tests/sparrow_sheet_builder.rs
 M rust/vrs_solver/tests/sparrow_sheet_edge_anchor.rs
 M rust/vrs_solver/tests/sparrow_sheet_edge_anchor_catalog.rs
 M rust/vrs_solver/tests/sparrow_sheet_feasibility_bpp_integration.rs
 M rust/vrs_solver/tests/sparrow_sheet_feasibility_hints.rs
 M rust/vrs_solver/tests/sparrow_sheet_skeleton.rs
 M rust/vrs_solver/tests/sparrow_single_sheet_validation.rs
 M rust/vrs_solver/tests/technology_clearance_policy.rs
 M rust/vrs_solver/tests/technology_part_spacing.rs
 M rust/vrs_solver/tests/technology_sheet_margin.rs
 M rust/vrs_solver/tests/technology_spacing_geometry.rs
 M rust/vrs_solver/tests/technology_spacing_offset_lv8.rs
?? artifacts/benchmarks/sgh_q62/
?? artifacts/benchmarks/sgh_q63/
?? artifacts/benchmarks/sgh_q65/
?? artifacts/benchmarks/sgh_q66/
?? artifacts/benchmarks/sgh_q67/
```

<!-- AUTO_VERIFY_END -->
