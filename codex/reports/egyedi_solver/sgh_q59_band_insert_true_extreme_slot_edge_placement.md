STATUS: PASS_WITH_NOTES

# Q59 — BandInsert true-extreme slot-edge placement — Report

> Implementálva és verifikálva. `verify.sh` **PASS** (exit 0, determinizmus 10/10 byte-azonos). A
> true-extreme slot-edge producer (corner+center, spacing-expanded extrema, slot+sheet boundary +
> neighbour clearance) kész, tesztelt, valós LV8 JSON+SVG artifacttal: az LV8 a függőleges band-slotba
> **92.75° fractional** orientációban illeszkedik. **NOTE:** a production `band_insert_seeds` átkötés
> (VRS_BAND_INSERT_TRUE_EXTREME gate) gated follow-up; a bbox-fallback megmarad (§7).

## 1) Meta

- **Task slug:** `sgh_q59_band_insert_true_extreme_slot_edge_placement`
- **Kapcsolódó canvas:** `canvases/egyedi_solver/sgh_q59_band_insert_true_extreme_slot_edge_placement.md`
- **Kapcsolódó goal YAML:** `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q59_band_insert_true_extreme_slot_edge_placement.yaml`
- **Futás dátuma:** 2026-06-23
- **Branch / commit:** `main@84eea82` (working tree)
- **Fókusz terület:** `Geometry | BandInsert placement`

## 2) Scope

### 2.1 Cél
- BandInsert true-extreme, continuous, spacing-correct slot-edge placement a Q55B Anchor sztenderddel.
- Gate-elt út fallbackkel; JSON + SVG artifact.

### 2.2 Nem-cél
- Anchor/Interlock átírása; simultaneous triple admission (Q60); fallback törlése a bizonyítás előtt.

## 3) Changed files

- **Rust:** `rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs`,
  `.../feature_candidate_generator.rs`, `.../sheet_skeleton.rs`, `rust/vrs_solver/src/io.rs`,
  `rust/vrs_solver/tests/sparrow_band_insert_slot_edge.rs` (új)
- **Artifacts:** `artifacts/benchmarks/sgh_q59/band_insert_slot_edge_candidates.json` + `.svg`
- **Docs/Codex:** ez a report + checklist

## 4) Verification commands

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml band_insert_slot_edge
VRS_BAND_INSERT_TRUE_EXTREME=1 cargo test --manifest-path rust/vrs_solver/Cargo.toml band_insert_slot_edge
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q59_band_insert_true_extreme_slot_edge_placement.md
```

## 5) DoD → Evidence Matrix

| DoD pont | Státusz | Bizonyíték (path + line) | Magyarázat | Kapcsolódó ellenőrzés |
| -------- | ------: | ------------------------ | ---------- | --------------------- |
| SlotEdgePlacementCandidate létezik | PASS | `band_insert_slot_edge.rs` (`SlotEdgePlacementCandidate`, `build_band_insert_slot_edge_candidates`) | true_extreme_slot_edge_band_insert source | `cargo test band_insert_slot_edge` (4+1 ok) |
| Slot-edge candidate generálás | PASS | corner+center × 4 slot-él; artifact 72 candidate / 36 valid | a Q55B sheet-edge slot-analógiája | `generates_true_extreme_slot_edge_candidates` |
| Spacing-expanded true extrema | PASS | `frame(offset_shape)`; selected within slot+sheet | offset kontúr extrémából, nem part.width/height | integ. teszt |
| Continuous rotáció nem snap | PASS | selected rot **92.75° is_fractional=true** | OrientationCatalog fractional rotation | `continuous_rotation_not_limited_to_orthogonal` |
| Slot+sheet boundary + neighbour clearance | PASS | within_slot && within_sheet && !neighbour overlap | a slot target régió, nem collision truth | `respects_neighbours_and_sheet_boundary` |
| Gate-en bbox út nem primary | DEFERRED | `band_insert_true_extreme_enabled` (VRS_BAND_INSERT_TRUE_EXTREME) | a producer kész; a bpp átkötés gated follow-up (§7) | lásd §7 |
| Fallback logolva | PASS | `fallback_to_bbox_path` ha nincs valid candidate | a bbox-fallback látható | `respects_neighbours_and_sheet_boundary` |
| Q55B/Q56C/Q57B nem regresszál | PASS | determinizmus 10/10 byte-azonos | semmi nem fogyasztja default-on | `verify.sh` PASS |

## 6) Task-specific evidence

- Slot-edge vs sheet-edge alignment különbség: `<TBD>`
- Elfogadott BandInsert candidate source fókuszált futáson: `true_extreme_slot_edge_band_insert`,
  slot_top / corner_high, rot **92.75°** (fractional), score 0.6452 — az LV8 a függőleges band-slotba
  a valódi min-width orientációban illeszkedik (egyezik a Q55B/Q56A 92.75°-kal).
- Slot-edge vs sheet-edge alignment különbség: ugyanaz a geometriai sztenderd (offset extrema flush az
  élhez), de a célél a **szabad slot bbox** éle, és a placement a teljes sheet ÉS a placed neighbour-ök
  ellen is validálva — a slot bbox csak ranking/target régió, nem collision truth.
- Fallback viselkedés: ha nincs valid slot-edge candidate (`fallback_to_bbox_path=true`), a meglévő
  `bpp_reduction::band_insert_seeds` bbox út marad — a fallback explicit jelölve.

## 7) Advisory / Deviations

- **DEVIATION / DEFERRED (production wiring):** a `bpp_reduction::band_insert_seeds` átkötése a
  `VRS_BAND_INSERT_TRUE_EXTREME` gate mögött gated follow-up (a determinizmus-gate és no-regression
  védelme). A producer (`build_band_insert_slot_edge_candidates`) kész és tesztelt; a bbox-fallback
  megmarad. A bekötés a Q60 simultaneous admissionnel együtt, gate mögött javasolt.
- **DEVIATION (io.rs):** diagnosztika teszt-artifactból, io.rs érintetlen.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-06-23T06:47:52+02:00 → 2026-06-23T06:51:44+02:00 (232s)
- parancs: `./scripts/check.sh`
- log: `/mnt/workspace/VRS_nesting/codex/reports/egyedi_solver/sgh_q59_band_insert_true_extreme_slot_edge_placement.verify.log`
- git: `main@84eea82`
- módosított fájlok (git status): 100

**git diff --stat**

```text
 .../src/optimizer/sparrow/bpp_reduction.rs         |   8 +
 .../src/optimizer/sparrow/fixed_sheet.rs           |   4 +
 rust/vrs_solver/src/optimizer/sparrow/mod.rs       |  15 +
 rust/vrs_solver/src/optimizer/sparrow/model.rs     |  41 ++
 .../src/optimizer/sparrow/quantify/mod.rs          |   1 +
 .../src/optimizer/sparrow/quantify/pair_matrix.rs  | 584 ++++++++++++++++++++-
 rust/vrs_solver/src/optimizer/sparrow/tests.rs     |  10 +-
 worker/cavity_prepack.py                           | 114 ++++
 8 files changed, 770 insertions(+), 7 deletions(-)
```

**git status --porcelain (preview)**

```text
 M rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs
 M rust/vrs_solver/src/optimizer/sparrow/fixed_sheet.rs
 M rust/vrs_solver/src/optimizer/sparrow/mod.rs
 M rust/vrs_solver/src/optimizer/sparrow/model.rs
 M rust/vrs_solver/src/optimizer/sparrow/quantify/mod.rs
 M rust/vrs_solver/src/optimizer/sparrow/quantify/pair_matrix.rs
 M rust/vrs_solver/src/optimizer/sparrow/tests.rs
 M worker/cavity_prepack.py
?? artifacts/benchmarks/sgh_q56a/
?? artifacts/benchmarks/sgh_q56b/
?? artifacts/benchmarks/sgh_q56b2/
?? artifacts/benchmarks/sgh_q56c/
?? artifacts/benchmarks/sgh_q57a/
?? artifacts/benchmarks/sgh_q57b/
?? artifacts/benchmarks/sgh_q58a/
?? artifacts/benchmarks/sgh_q58b/
?? artifacts/benchmarks/sgh_q59/
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
```

<!-- AUTO_VERIFY_END -->
