# SGH-Q67 Simultaneous critical production cutover

## Meta

- Task slug: `sgh_q67_simultaneous_critical_production_cutover`
- Canvas: `canvases/egyedi_solver/sgh_q67_simultaneous_critical_production_cutover.md`
- Goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q67_simultaneous_critical_production_cutover.yaml`
- Fokusz: `Q60 production authority cutover`

## Audit gap

- A `critical_simultaneous.rs` bounded group admission modul megvan, de a production
  `try_admit_critical()` jelenleg nem ezt hasznalja explicit authoritykent; leginkabb csak a
  co-movable separation/repack altalanos utja latszik.

## Valtozasok

- A production `try_admit_critical()` elejere bekerult a same-part simultaneous authority proba,
  amely a 3. vagy kesobbi, ugyanazon sheeten levo critical admissionnel explicit megprobalja a
  bounded Q60 group admissiont, es siker eseten committed layoutot ad vissza
  ([rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs](/mnt/workspace/VRS_nesting/rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs:2238),
  [bpp_reduction.rs](/mnt/workspace/VRS_nesting/rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs:2482)).
- A live simultaneous helper mar a production `SPInstance` / `SheetShape` adatokbol dolgozik, az
  orientacio-katalogusbol valaszt preferalt forgatast, es az aktualis edge inset alapjan epiti fel
  a bounded group keretet
  ([rust/vrs_solver/src/optimizer/sparrow/critical_simultaneous.rs](/mnt/workspace/VRS_nesting/rust/vrs_solver/src/optimizer/sparrow/critical_simultaneous.rs:20),
  [critical_simultaneous.rs](/mnt/workspace/VRS_nesting/rust/vrs_solver/src/optimizer/sparrow/critical_simultaneous.rs:208)).
- A Q67 production diagnostikak megmaradnak a valos solve-ban akkor is, amikor a skeletonos builder
  a korabbi seedre esik vissza: a role-aware builder most a teljes konstruktiv ablakot megkapja, igy
  a pair/simultaneous authority tenylegesen lefut a Q61/Q67 utvonalon
  ([rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs](/mnt/workspace/VRS_nesting/rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs:3955)).
- Elkeszult a focused Q67 artifact runner es az artifact JSON
  ([rust/vrs_solver/tests/sparrow_q67_simultaneous_cutover.rs](/mnt/workspace/VRS_nesting/rust/vrs_solver/tests/sparrow_q67_simultaneous_cutover.rs:35),
  [artifacts/benchmarks/sgh_q67/simultaneous_critical_production_cutover.json](/mnt/workspace/VRS_nesting/artifacts/benchmarks/sgh_q67/simultaneous_critical_production_cutover.json:1)).

## DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo teszt/ellenorzes |
| -------- | ------: | ------------------------ | ---------- | --------------------------- |
| Q60 production simultaneous authority wiring megvalositva | PASS | [bpp_reduction.rs](/mnt/workspace/VRS_nesting/rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs:2238), [bpp_reduction.rs](/mnt/workspace/VRS_nesting/rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs:2482) | A production critical admission mar explicit same-part group authority probat futtat, es full successnel committed layoutot ad vissza. | `cargo test --manifest-path rust/vrs_solver/Cargo.toml --test sparrow_q67_simultaneous_cutover -- --nocapture` |
| Same-part 2-es group committed layoutot tud visszaadni | PASS | [critical_simultaneous.rs](/mnt/workspace/VRS_nesting/rust/vrs_solver/src/optimizer/sparrow/critical_simultaneous.rs:208), [sparrow_q67_simultaneous_cutover.rs](/mnt/workspace/VRS_nesting/rust/vrs_solver/tests/sparrow_q67_simultaneous_cutover.rs:37) | A focused runnerben a pair scenario `full_success`, es az artifact ezt explicit rogzitette. | `cargo test --manifest-path rust/vrs_solver/Cargo.toml --test sparrow_q67_simultaneous_cutover -- --nocapture` |
| 3-as group best partial / rejection summary explicit marad | PASS | [bpp_reduction.rs](/mnt/workspace/VRS_nesting/rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs:2341), [bpp_reduction.rs](/mnt/workspace/VRS_nesting/rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs:2420), [sparrow_q67_simultaneous_cutover.rs](/mnt/workspace/VRS_nesting/rust/vrs_solver/tests/sparrow_q67_simultaneous_cutover.rs:39) | A production helper a best partial count/source es a rejection summary mezoket is kitolti; a focused triple scenario 2-es valid partialt igazol. | `cargo test --manifest-path rust/vrs_solver/Cargo.toml --test sparrow_q67_simultaneous_cutover -- --nocapture` |
| A fallback tovabbra is elerheto, de a latest path nem tunik el tul koran | PASS | [bpp_reduction.rs](/mnt/workspace/VRS_nesting/rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs:3955), [rust/vrs_solver/tests/sparrow_q61_integrated_critical_admission.rs](/mnt/workspace/VRS_nesting/rust/vrs_solver/tests/sparrow_q61_integrated_critical_admission.rs:148) | A skeletonos builder tovabbra is fallbackolhat, de mar nem vesznek el a Q61/Q67 consult diagnostikak a tul agressziv builder-cap miatt. | `cargo test --manifest-path rust/vrs_solver/Cargo.toml --test sparrow_q61_integrated_critical_admission pair_index_is_consulted_before_neighbour_fallback -- --nocapture`; `cargo test --manifest-path rust/vrs_solver/Cargo.toml --test sparrow_q61_integrated_critical_admission diagnostics_expose_all_candidate_sources_and_rejections -- --nocapture` |

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-06-24T13:21:55+02:00 → 2026-06-24T13:30:21+02:00 (506s)
- parancs: `./scripts/check.sh`
- log: `/mnt/workspace/VRS_nesting/codex/reports/egyedi_solver/sgh_q67_simultaneous_critical_production_cutover.verify.log`
- git: `main@066fd1e`
- módosított fájlok (git status): 95

**git diff --stat**

```text
 .../sgh_q60/critical_group_admission.json          |   28 +-
 .../sgh_q61/critical_3part_diagnostics_summary.md  |    6 +-
 .../sgh_q61/critical_3part_real_spacing.json       |   10 +-
 .../sgh_q61/critical_3part_real_spacing.svg        |    8 +-
 .../sgh_q61/critical_3part_spacing0.json           |   10 +-
 .../benchmarks/sgh_q61/critical_3part_spacing0.svg |   12 +-
 rust/vrs_solver/src/adapter.rs                     |  560 +++++++--
 rust/vrs_solver/src/io.rs                          |   44 +
 rust/vrs_solver/src/optimizer/cde_adapter.rs       |  159 ++-
 .../src/optimizer/sparrow/band_insert_slot_edge.rs |  122 +-
 .../src/optimizer/sparrow/bpp_reduction.rs         | 1323 +++++++++++++++++---
 .../src/optimizer/sparrow/critical_simultaneous.rs |  262 +++-
 .../sparrow/feature_candidate_generator.rs         |  146 ++-
 .../src/optimizer/sparrow/interlock_pair.rs        |  280 ++++-
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
 55 files changed, 3843 insertions(+), 993 deletions(-)
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
