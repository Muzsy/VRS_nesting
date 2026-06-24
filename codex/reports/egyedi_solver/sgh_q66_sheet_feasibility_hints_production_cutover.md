# DONE - SGH-Q66 SheetFeasibilityHints production cutover

## 1) Meta

- **Task slug:** `sgh_q66_sheet_feasibility_hints_production_cutover`
- **Kapcsolodo canvas:** `canvases/egyedi_solver/sgh_q66_sheet_feasibility_hints_production_cutover.md`
- **Kapcsolodo goal YAML:** `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q66_sheet_feasibility_hints_production_cutover.yaml`
- **Futas datuma:** `2026-06-24`
- **Branch / commit:** `main`
- **Fokusz terulet:** `Q58 production cutover`

## 2) Scope

### 2.1 Cel

- A `sheet_feasibility.rs` es `sheet_feasibility_bpp.rs` helper-logika ne csak kulon modulban letezzen,
  hanem a production `build_critical_aware_seed()` tenylegesen fel is hasznalja a critical queue,
  per-sheet kvota, frontier es best-partial dontesekben.
- A solve boundaryn latszodjon, hogy a hint gate tenyleg bekapcsolt, milyen target distribution /
  kvota kepzodott, es ha a builder nem eri el a celkvotat, az is explicit diagnosztikaval jelenjen meg.

### 2.2 Nem-cel

- Nem teljes layout-quality helyreallitas az LV8 csomagon.
- Nem annak allitasa, hogy a hint bekotese onmagaban mar visszahozza a PDF-ben latott 2-tablas jo
  elrendezest.

## 3) Valtozasok osszefoglalasa

- A production builder kapott egy live hint-epito entry pointot, ami a solver mar cache-elt
  `SPInstance`/sheet adataibol allit elo `SheetFeasibilityHints` modellt, ugyanabban a solver-sheet
  koordinatarendszerben.
- A hint gate alatt a `critical_queue` most mar hint-aware reorderen mehet at, kiszamolodnak a
  `sheet_target_quotas`, es a builder ezek alapjan tudja meghosszabbitani a critical frontiert.
- A best-partial kovetes productionben is explicitte valt: rogzul a legjobb critical count, annak
  forrasa, a quota-met flag, es ha a celkvota nem teljesul, annak oka is bekerul a diagnosztikaba.
- Keszult kulon solve-boundary teszt es artifact, ami gate-off vs gate-on modban ugyanazon a live
  LV8 fixture-on megmutatja a production hint fogyasztast.
- A live artifact szerint a hint wiring mar aktiv, de az adott futasban a builder tovabbra sem eri
  el a `2` darabos per-sheet celkvotat: `max_per_sheet=1`, `sheet_target_quota_met=false`,
  `hint_quota_abandoned_reason="sheet=0 target_quota=2 best_partial=1 useful_partial=true close_reason=deadline"`.
  Vagyis ez a task a bekotest es a lathatosagot bizonyitja, nem egy kesz nesting-minosegi ugrasat.

## 4) Verifikacio

### 4.1 Kotelezo parancs

- `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q66_sheet_feasibility_hints_production_cutover.md` -> PASS

### 4.2 Opcionális, feladatfüggo parancsok

- `cargo test --manifest-path rust/vrs_solver/Cargo.toml sheet_feasibility_bpp -- --nocapture` -> PASS
- `cargo test --manifest-path rust/vrs_solver/Cargo.toml --test sparrow_q66_sheet_feasibility_cutover -- --nocapture` -> PASS

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo teszt/ellenorzes |
| -------- | ------: | ------------------------ | ---------- | --------------------------- |
| A production builder explicit gate alatt valoban fogyasztja a Q58 hint-eket | PASS | `rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs:2874`, `rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs:2912`, `rust/vrs_solver/tests/sparrow_q66_sheet_feasibility_cutover.rs:70` | A `VRS_SHEET_FEASIBILITY_HINTS` gate mellett a builder live hintet epit, felkapcsolja a `bpp_sheet_feasibility_hints_used` diagnostikat, es a boundary teszt ezt gate-on futasban meg is koveteli. | `cargo test --manifest-path rust/vrs_solver/Cargo.toml --test sparrow_q66_sheet_feasibility_cutover -- --nocapture` |
| A live hint modell a solver valos sheet/instance adataibol epul | PASS | `rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs:84`, `rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs:95`, `rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs:108` | A helper a live `SPInstance` tombbol szedi az egyedi partokat, majd a legnagyobb solver sheet kereteben epit hintet explicit spacinggel. | Kodolvasas + `cargo test --manifest-path rust/vrs_solver/Cargo.toml sheet_feasibility_bpp -- --nocapture` |
| A critical queue hint-aware reorderrel es target kvotakkal tud futni | PASS | `rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs:2881`, `rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs:2894`, `rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs:2911`, `rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs:2941` | A production builder a hint rank alapjan rendezheti a critical queue-t, majd per-sheet remaining quota alapjan szamol tovabb. | `cargo test --manifest-path rust/vrs_solver/Cargo.toml --test sparrow_q66_sheet_feasibility_cutover -- --nocapture` |
| A per-sheet target kvota es frontier extension diagnosztikailag latszik | PASS | `rust/vrs_solver/src/io.rs:397`, `rust/vrs_solver/src/io.rs:401`, `rust/vrs_solver/src/io.rs:409`, `rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs:2960`, `rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs:2969`, `artifacts/benchmarks/sgh_q66/sheet_feasibility_production_cutover.json:1` | A diagnostics schema explicit mezoket kapott a target distributionra, quota-ra es frontier extensionre; a live artifact ezek ertekeit ki is irja. | `cargo test --manifest-path rust/vrs_solver/Cargo.toml --test sparrow_q66_sheet_feasibility_cutover -- --nocapture` |
| A best partial critical count/source es quota abandoned reason rogzitve van | PASS | `rust/vrs_solver/src/io.rs:405`, `rust/vrs_solver/src/io.rs:412`, `rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs:3025`, `rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs:3048`, `rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs:3082`, `rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs:3095` | A builder productionben nyomon koveti a legjobb partial incumbentet, annak forrasat, es ha a quota nem teljesul, explicit abandoned reasont ir. | `cargo test --manifest-path rust/vrs_solver/Cargo.toml --test sparrow_q66_sheet_feasibility_cutover -- --nocapture` |
| Elkeszult a live Q66 artifact a solve boundaryrol | PASS | `rust/vrs_solver/tests/sparrow_q66_sheet_feasibility_cutover.rs:103`, `artifacts/benchmarks/sgh_q66/sheet_feasibility_production_cutover.json:1` | A kulon integracios teszt kiirja a gate-off/gate-on osszehasonlito artifactot. | `cargo test --manifest-path rust/vrs_solver/Cargo.toml --test sparrow_q66_sheet_feasibility_cutover -- --nocapture` |
| Minden letrehozott/modositott fajl szerepel a YAML outputs listajaban | PASS | `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q66_sheet_feasibility_hints_production_cutover.yaml:18`, `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q66_sheet_feasibility_hints_production_cutover.yaml:27`, `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q66_sheet_feasibility_hints_production_cutover.yaml:34`, `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q66_sheet_feasibility_hints_production_cutover.yaml:41` | A task artefaktok, a Rust kodvaltozasok, a teszt, az artifact es a verify log is fel van sorolva az outputs listakban. | Kezi file read |
| `./scripts/verify.sh --report ...` lefutott | PASS | `codex/reports/egyedi_solver/sgh_q66_sheet_feasibility_hints_production_cutover.verify.log` | A standard repo gate PASS-szal zart. | `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q66_sheet_feasibility_hints_production_cutover.md` |
| Report Standard v2 DoD->Evidence Matrix kitoltve | PASS | Ez a tabla | A vegleges report konkret path+line bizonyitekokkal lett kitoltve. | Kezi file read |

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-06-24T06:35:26+02:00 → 2026-06-24T06:43:35+02:00 (489s)
- parancs: `./scripts/check.sh`
- log: `/mnt/workspace/VRS_nesting/codex/reports/egyedi_solver/sgh_q66_sheet_feasibility_hints_production_cutover.verify.log`
- git: `main@066fd1e`
- módosított fájlok (git status): 88

**git diff --stat**

```text
 .../sgh_q60/critical_group_admission.json          |   4 +-
 .../sgh_q61/critical_3part_diagnostics_summary.md  |   4 +-
 .../sgh_q61/critical_3part_real_spacing.json       |   8 +-
 .../sgh_q61/critical_3part_real_spacing.svg        |  12 +-
 .../sgh_q61/critical_3part_spacing0.json           |   8 +-
 .../benchmarks/sgh_q61/critical_3part_spacing0.svg |  12 +-
 rust/vrs_solver/src/adapter.rs                     | 560 +++++++++++---
 rust/vrs_solver/src/io.rs                          |  27 +
 rust/vrs_solver/src/optimizer/cde_adapter.rs       | 159 ++--
 .../src/optimizer/sparrow/band_insert_slot_edge.rs | 122 ++-
 .../src/optimizer/sparrow/bpp_reduction.rs         | 854 ++++++++++++++++-----
 .../src/optimizer/sparrow/critical_simultaneous.rs | 144 +++-
 .../sparrow/feature_candidate_generator.rs         | 146 ++--
 .../src/optimizer/sparrow/interlock_pair.rs        | 280 ++++++-
 rust/vrs_solver/src/optimizer/sparrow/mod.rs       |   4 +-
 .../src/optimizer/sparrow/one_part_edge.rs         |  65 +-
 .../src/optimizer/sparrow/orientation_catalog.rs   |  46 +-
 .../src/optimizer/sparrow/part_analysis.rs         |  62 +-
 .../src/optimizer/sparrow/quantify/pair_matrix.rs  | 304 +++++---
 .../sparrow/sheet_edge_placement_catalog.rs        |  64 +-
 .../src/optimizer/sparrow/sheet_feasibility.rs     |  60 +-
 .../src/optimizer/sparrow/sheet_feasibility_bpp.rs |  36 +-
 .../src/optimizer/sparrow/sheet_skeleton.rs        |  60 +-
 rust/vrs_solver/src/optimizer/sparrow/tests.rs     |   8 +-
 rust/vrs_solver/src/sheet.rs                       |  55 +-
 rust/vrs_solver/src/technology/spacing.rs          |  15 +-
 rust/vrs_solver/src/technology/spacing_geometry.rs |  11 +-
 .../tests/sparrow_band_insert_slot_edge.rs         |  15 +-
 rust/vrs_solver/tests/sparrow_contour_features.rs  |  12 +-
 .../tests/sparrow_critical_feature_admission.rs    |   4 +-
 .../sparrow_critical_simultaneous_admission.rs     |  24 +-
 rust/vrs_solver/tests/sparrow_density_admission.rs |  40 +-
 .../vrs_solver/tests/sparrow_density_compaction.rs |  33 +-
 .../vrs_solver/tests/sparrow_feature_candidates.rs |  29 +-
 .../tests/sparrow_finite_stock_multisheet.rs       | 175 +++--
 .../tests/sparrow_interlock_pair_candidates.rs     |   4 +-
 .../tests/sparrow_one_part_sheet_edge.rs           |  42 +-
 .../tests/sparrow_orientation_catalog.rs           |   9 +-
 .../tests/sparrow_pair_compatibility_index.rs      |  40 +-
 rust/vrs_solver/tests/sparrow_part_analysis.rs     |  57 +-
 .../sparrow_q61_integrated_critical_admission.rs   | 106 ++-
 rust/vrs_solver/tests/sparrow_role_routing.rs      |  24 +-
 rust/vrs_solver/tests/sparrow_shape_profile.rs     |  32 +-
 rust/vrs_solver/tests/sparrow_sheet_builder.rs     |  21 +-
 rust/vrs_solver/tests/sparrow_sheet_edge_anchor.rs |  10 +-
 .../tests/sparrow_sheet_edge_anchor_catalog.rs     |  31 +-
 .../sparrow_sheet_feasibility_bpp_integration.rs   |  20 +-
 .../tests/sparrow_sheet_feasibility_hints.rs       |  18 +-
 rust/vrs_solver/tests/sparrow_sheet_skeleton.rs    |  26 +-
 .../tests/sparrow_single_sheet_validation.rs       |  40 +-
 .../tests/technology_clearance_policy.rs           |  35 +-
 rust/vrs_solver/tests/technology_part_spacing.rs   |  15 +-
 rust/vrs_solver/tests/technology_sheet_margin.rs   |  54 +-
 .../tests/technology_spacing_geometry.rs           | 118 ++-
 .../tests/technology_spacing_offset_lv8.rs         |  42 +-
 55 files changed, 3253 insertions(+), 953 deletions(-)
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
?? canvases/egyedi_solver/sgh_q62_full276_lv8_spacing5_two_sheet_rerun.md
```

<!-- AUTO_VERIFY_END -->
