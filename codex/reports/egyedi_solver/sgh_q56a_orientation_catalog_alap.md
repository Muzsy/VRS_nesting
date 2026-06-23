STATUS: PASS

# Q56A — OrientationCatalog alap — Report

> Implementálva és verifikálva. A `verify.sh` repo gate **PASS** (exit 0, determinizmus 10/10
> byte-azonos → nincs regresszió). Az OrientationCatalog part-típusonként egyszer számolódik, valós
> spacing-expanded kontúr-extrémából, és a valós `Lv8_11612_6db` partra 92.75° fractional min-width
> candidate-et ad (egyezik a Q55B proof referencia-szögével), a 90° vertical alignmenttől különbözve.

## 1) Meta

- **Task slug:** `sgh_q56a_orientation_catalog_alap`
- **Kapcsolódó canvas:** `canvases/egyedi_solver/sgh_q56a_orientation_catalog_alap.md`
- **Kapcsolódó goal YAML:** `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q56a_orientation_catalog_alap.yaml`
- **Futás dátuma:** 2026-06-22
- **Branch / commit:** `main@84eea82` (working tree)
- **Fókusz terület:** `Geometry | Solver preprocessing`

## 2) Scope

### 2.1 Cél
- Production OrientationCatalog réteg minden egyedi part-típushoz, part-típusonként egyszer számolva.
- Spacing-expanded kontúr-extrema alapú orientációs jelöltek, diagnosztikával.

### 2.2 Nem-cél
- Placement stratégia átírása; NFP; bbox collision shortcut; cavity/hole logika a Rust fősolverben.

## 3) Changed files

- **Rust:** `rust/vrs_solver/src/optimizer/sparrow/orientation_catalog.rs` (új),
  `.../mod.rs`, `.../model.rs`, `rust/vrs_solver/src/io.rs`,
  `rust/vrs_solver/tests/sparrow_orientation_catalog.rs` (új)
- **Artifacts:** `artifacts/benchmarks/sgh_q56a/orientation_catalog_lv8_critical.json`
- **Docs/Codex:** ez a report + checklist

## 4) Verification commands

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml orientation_catalog
cargo test --manifest-path rust/vrs_solver/Cargo.toml --test sparrow_one_part_sheet_edge
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q56a_orientation_catalog_alap.md
```

## 5) DoD → Evidence Matrix

| DoD pont | Státusz | Bizonyíték (path + line) | Magyarázat | Kapcsolódó ellenőrzés |
| -------- | ------: | ------------------------ | ---------- | --------------------- |
| OrientationCatalog létezik + integrált | PASS | `orientation_catalog.rs:141` (struct), `model.rs:35` (SPInstance mező), `model.rs:290-314` (push) | Reusable modul + Rc<OrientationCatalog> az SPInstance-en | `cargo test orientation_catalog` (6+1 ok) |
| Extrema spacing-expanded kontúrból | PASS | `orientation_catalog.rs:497` (`extrema_sample` forgatja a `local_pts`-t), `model.rs:293-300` (`spacing_collision_base_shape.as_ref()` átadva) | Nem part.width/height; valós forgatott spacing-offset pontok | `extrema_use_spacing_expanded_contour_not_bbox` |
| Continuous nem snappel | PASS | artifact: 92.75° `min_width` `is_fractional=true` | A continuous min-width valódi tört szög, nem 0/90/180/270 | `continuous_min_width_can_be_fractional` |
| Diszkrét policy tisztelet | PASS | `orientation_catalog.rs:153` compute discrete ág; `classify_discrete` | Diszkrét part csak allowed rotation-t kap, fractional nélkül | `discrete_part_only_receives_allowed_rotations` |
| Katalógus part-típusonként egyszer | PASS | `model.rs:125` cache, `model.rs:290` `entry(part_id)` | HashMap cache part_id-ra, instance-enként újrahasznál | `model.rs::from_solver_input` |
| LV8 diagnosztika artifact | PASS | `artifacts/benchmarks/sgh_q56a/orientation_catalog_lv8_critical.json` | part_id Lv8_11612_6db, 6 candidate, 2 fractional, 6 extrema sample | integ. teszt `tests/sparrow_orientation_catalog.rs:65` |
| Q55B proof nem regresszál | PASS | determinizmus 10/10 byte-azonos (AUTO_VERIFY) | `--test sparrow_one_part_sheet_edge` 1 passed; gate off byte-azonos | `verify.sh` PASS |

## 6) Task-specific evidence

- Candidate count `Lv8_11612_6db`-re: **6** (sheet_horizontal 0°, sheet_vertical 90°, min_width 92.75°,
  min_height ~2.75°, + 180° flip variánsok dedup után).
- Fractional candidate count: **2** (min_width 92.75°, min_height — mindkettő >0.25° az ortogonális
  tengelyektől).
- Extrema forrás megerősítése: `extrema_from_spacing_expanded=true` az artifactban; a `compute` a
  `spacing_collision_base_shape`-et kapja (`model.rs:293-300`), és a `extrema_sample`
  (`orientation_catalog.rs:497`) a valós `local_pts`-t forgatja — nem part.width/height.
- Min-width = 92.75° egyezik a Q55B proof referencia min-width orientációjával, és **különbözik** a 90°
  vertical alignmenttől (2.75° távolság > 0.01° dedup tolerancia), így mindkettő megmarad.
- Deprecation-jelölt orientációs kód: a `contour_features::sheet_edge_alignment_angles`,
  `feature_candidate_generator::min_width_rotations` és a density rotation jelöltek **most még
  párhuzamosan élnek**; a Q56C/Q57/Q59 taskok fogják a katalógusra terelni őket. Q56A csak a réteget
  hozza létre, placement utat nem cserél (ezért determinizmus byte-azonos).

## 7) Advisory / Deviations

- **DEVIATION (io.rs):** az io.rs production diagnosztika export szándékosan **nem** módosult, hogy a
  determinizmus-hash / IO contract smoke ne sérüljön. A katalógus így is solver-adathoz kötött
  (`SPInstance.orientation_catalog`), a JSON diagnosztika pedig az integrációs teszt artifactjából áll
  elő (`artifacts/benchmarks/sgh_q56a/...`). Ez a Q53A-mintát követi (additív, opcionális export csak
  ha indokolt). A YAML step io.rs-t megengedi, de nem kötelezi.
- A katalógus jelenleg read-only döntéstámogatás; egyetlen placement út sem fogyasztja még (a fogyasztás
  a Q56C+ feladata). Ezért a gate-off és a teljes suite byte-azonos.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-06-22T23:30:02+02:00 → 2026-06-22T23:33:47+02:00 (225s)
- parancs: `./scripts/check.sh`
- log: `/mnt/workspace/VRS_nesting/codex/reports/egyedi_solver/sgh_q56a_orientation_catalog_alap.verify.log`
- git: `main@84eea82`
- módosított fájlok (git status): 67

**git diff --stat**

```text
 .../src/optimizer/sparrow/bpp_reduction.rs         |  4 ++++
 .../src/optimizer/sparrow/fixed_sheet.rs           |  2 ++
 rust/vrs_solver/src/optimizer/sparrow/mod.rs       |  2 ++
 rust/vrs_solver/src/optimizer/sparrow/model.rs     | 24 ++++++++++++++++++++++
 rust/vrs_solver/src/optimizer/sparrow/tests.rs     |  3 +++
 5 files changed, 35 insertions(+)
```

**git status --porcelain (preview)**

```text
 M rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs
 M rust/vrs_solver/src/optimizer/sparrow/fixed_sheet.rs
 M rust/vrs_solver/src/optimizer/sparrow/mod.rs
 M rust/vrs_solver/src/optimizer/sparrow/model.rs
 M rust/vrs_solver/src/optimizer/sparrow/tests.rs
?? artifacts/benchmarks/sgh_q56a/
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
?? codex/reports/egyedi_solver/sgh_q56c_sheet_edge_placement_catalog_edge_corner_anchor_candidates.md
?? codex/reports/egyedi_solver/sgh_q57a_pair_compatibility_index_critical_only.md
```

<!-- AUTO_VERIFY_END -->
