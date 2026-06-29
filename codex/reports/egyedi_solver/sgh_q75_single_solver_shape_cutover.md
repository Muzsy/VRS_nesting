# SGH-Q75 Report - Single solver-shape cutover cleanup

## 0) Statusz

**PASS** - a Fazis 1-4 kesz, a `verify.sh` repo gate **PASS** (check.sh exit 0, 479s), 550 lib +
osszes erintett integracios teszt zold, es a cutover **megorizte a production eredmenyt**: a Q74 600s
post-cutover **274/276** (azonos a cutover elottivel), a Q72 600s 254 (wall-time-zaj az
exploration-nehez uton, nem kod-regresszio — a kivett dual-geometry spacing=0-nal bizonyitottan no-op).

A modositott architektura-leiras (`tmp/plans/solver_architektura_modositott_leiras.md`) fo tezise (egy
solver-shape) **mar production-aktiv volt (SGH-Q40)**; ez a task a maradek kod-higiéniat vegezte el,
byte-azonos production viselkedes mellett.

**Oszinte megjegyzes:** a gated-modul DIAGNOSZTIKAI artifactok (sgh_q55b/q56*/q57/q59/q60) megvaltoztak,
mert a standalone benchjeik korabban belul offseteltek (per-instance spacing shape); a cutover utan a
single solver-shape-et latjak. Ez NEM production-regresszio (production-ben a `base_shape` = a beegetett
offset, valtozatlan; a gated modulok productionben tovabbra is az offset konturt latjak az SPInstance-on
keresztul). A standalone benchek production-faithfulla tetele (offset-bake, mint a one_part harness)
kulon, kis kovetkezo lepes lehet.

## 1) Meta

- **Task slug:** `sgh_q75_single_solver_shape_cutover`
- **Kapcsolodo canvas:** `canvases/egyedi_solver/sgh_q75_single_solver_shape_cutover.md`
- **Kapcsolodo goal YAML:** `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q75_single_solver_shape_cutover.yaml`
- **Futas datuma:** 2026-06-26
- **Branch / commit:** `main@<commit>` (verify.sh AUTO_VERIFY blokk rogzi)
- **Fokusz terulet:** `Solver core (geometry model) | Cleanup`

## 2) Scope

### 2.1 Cel
- A kettos `base_shape` + `spacing_collision_base_shape` dontesmodell kivezetese -> egy solver-shape.
- Hard SolverInputGuard a top-level hole-okra.
- Furat-jel sehol nem dontesi input (igazolas + dokumentalas).
- Byte-azonos production (a placed_count nem valtozik a kivett no-op miatt).

### 2.2 Nem-cel
- Diagnosztikai mezo / output-sema atiras (zero-erteku churn).
- 3/tabla nesting (kulon task).

## 3) Valtozasok osszefoglaloja

- **model.rs:** `spacing_collision_base_shape` mezo + spacing-shape epites torolve; OrientationCatalog
  a `base_shape`-bol.
- **quantify/tracker.rs:** `spacing_applied` always-false (Q36 dual-ut kivezetve).
- **11 fajl:** `.spacing_collision_base_shape` -> `.base_shape` mezo-olvasas csere (spacing=0-nal azonos).
- **adapter.rs:** SolverInputGuard (`CAVITY_PREPACK_TOP_LEVEL_HOLES_REMAIN`) a pipeline elejen.
- **part_analysis.rs:** furat-mezok diagnosztika-only jellege dokumentalva.
- **orientation_catalog.rs / feature_candidate_generator.rs:** dual-geometry tesztek/harness a
  single-shape (offset-bake + spacing=0) modellre frissitve.

## 4) Verifikacio

### 4.1 Kotelezo parancs
- `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q75_single_solver_shape_cutover.md`

### 4.2 Feladatfuggo
- `cargo test --release --lib` (550+), `--test sparrow_one_part_sheet_edge`, `--test sparrow_sheet_builder`,
  technology/spacing tesztek.
- Q72/Q74 600s ujrafuttatas (production byte-azonossag, wall-time-zaj megjegyzessel).

### 4.3 Automatikus blokk
<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-06-29T23:19:29+02:00 → 2026-06-29T23:27:28+02:00 (479s)
- parancs: `./scripts/check.sh`
- log: `/mnt/workspace/VRS_nesting/codex/reports/egyedi_solver/sgh_q75_single_solver_shape_cutover.verify.log`
- git: `main@a96d649`
- módosított fájlok (git status): 75

**git diff --stat**

```text
 .../benchmarks/sgh_q55b/one_part_sheet_edge.json   | 14434 +++++++++----------
 .../benchmarks/sgh_q55b/one_part_sheet_edge.svg    |     2 +-
 .../sgh_q55b/one_part_sheet_edge_accepted.json     |  2058 +--
 .../one_part_sheet_edge_minwidth_proof.svg         |     2 +-
 .../sgh_q56a/orientation_catalog_lv8_critical.json |    72 +-
 .../benchmarks/sgh_q56b/part_analysis_summary.json |     4 +-
 .../sgh_q56c/sheet_edge_anchor_candidates.json     |  1586 +-
 .../sgh_q56c/sheet_edge_anchor_candidates.svg      |    76 +-
 .../sgh_q57a/pair_compatibility_index.json         |    34 +-
 .../sgh_q58a/sheet_feasibility_hints.json          |     2 +-
 .../sgh_q59/band_insert_slot_edge_candidates.json  |   658 +-
 .../sgh_q59/band_insert_slot_edge_candidates.svg   |    76 +-
 .../sgh_q60/critical_group_admission.json          |    40 +-
 .../sgh_q60/critical_group_admission.svg           |     8 +-
 .../sgh_q61/critical_3part_real_spacing.svg        |     8 +-
 .../simultaneous_critical_production_cutover.json  |    38 +-
 rust/vrs_solver/src/adapter.rs                     |    23 +
 rust/vrs_solver/src/io.rs                          |    69 +
 .../src/optimizer/sparrow/band_insert_slot_edge.rs |     4 +-
 .../src/optimizer/sparrow/bpp_reduction.rs         |  1608 ++-
 .../src/optimizer/sparrow/critical_simultaneous.rs |     4 +-
 .../sparrow/feature_candidate_generator.rs         |    47 +-
 .../src/optimizer/sparrow/fixed_sheet.rs           |     1 -
 .../src/optimizer/sparrow/interlock_pair.rs        |     6 +-
 rust/vrs_solver/src/optimizer/sparrow/lbf.rs       |     4 +-
 rust/vrs_solver/src/optimizer/sparrow/model.rs     |    79 +-
 .../vrs_solver/src/optimizer/sparrow/multisheet.rs |    20 +-
 .../src/optimizer/sparrow/orientation_catalog.rs   |    19 +-
 .../src/optimizer/sparrow/part_analysis.rs         |     4 +
 .../src/optimizer/sparrow/quantify/pair_matrix.rs  |     4 +-
 .../src/optimizer/sparrow/quantify/tracker.rs      |    18 +-
 .../src/optimizer/sparrow/sample/search.rs         |     2 +-
 .../sparrow/sheet_edge_placement_catalog.rs        |    13 +-
 rust/vrs_solver/src/optimizer/sparrow/tests.rs     |     2 -
 rust/vrs_solver/src/optimizer/sparrow/worker.rs    |    10 +
 rust/vrs_solver/tests/sparrow_sheet_builder.rs     |   211 +
 36 files changed, 11499 insertions(+), 9747 deletions(-)
```

**git status --porcelain (preview)**

```text
 M artifacts/benchmarks/sgh_q55b/one_part_sheet_edge.json
 M artifacts/benchmarks/sgh_q55b/one_part_sheet_edge.svg
 M artifacts/benchmarks/sgh_q55b/one_part_sheet_edge_accepted.json
 M artifacts/benchmarks/sgh_q55b/one_part_sheet_edge_minwidth_proof.svg
 M artifacts/benchmarks/sgh_q56a/orientation_catalog_lv8_critical.json
 M artifacts/benchmarks/sgh_q56b/part_analysis_summary.json
 M artifacts/benchmarks/sgh_q56c/sheet_edge_anchor_candidates.json
 M artifacts/benchmarks/sgh_q56c/sheet_edge_anchor_candidates.svg
 M artifacts/benchmarks/sgh_q57a/pair_compatibility_index.json
 M artifacts/benchmarks/sgh_q58a/sheet_feasibility_hints.json
 M artifacts/benchmarks/sgh_q59/band_insert_slot_edge_candidates.json
 M artifacts/benchmarks/sgh_q59/band_insert_slot_edge_candidates.svg
 M artifacts/benchmarks/sgh_q60/critical_group_admission.json
 M artifacts/benchmarks/sgh_q60/critical_group_admission.svg
 M artifacts/benchmarks/sgh_q61/critical_3part_real_spacing.svg
 M artifacts/benchmarks/sgh_q67/simultaneous_critical_production_cutover.json
 M rust/vrs_solver/src/adapter.rs
 M rust/vrs_solver/src/io.rs
 M rust/vrs_solver/src/optimizer/sparrow/band_insert_slot_edge.rs
 M rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs
 M rust/vrs_solver/src/optimizer/sparrow/critical_simultaneous.rs
 M rust/vrs_solver/src/optimizer/sparrow/feature_candidate_generator.rs
 M rust/vrs_solver/src/optimizer/sparrow/fixed_sheet.rs
 M rust/vrs_solver/src/optimizer/sparrow/interlock_pair.rs
 M rust/vrs_solver/src/optimizer/sparrow/lbf.rs
 M rust/vrs_solver/src/optimizer/sparrow/model.rs
 M rust/vrs_solver/src/optimizer/sparrow/multisheet.rs
 M rust/vrs_solver/src/optimizer/sparrow/orientation_catalog.rs
 M rust/vrs_solver/src/optimizer/sparrow/part_analysis.rs
 M rust/vrs_solver/src/optimizer/sparrow/quantify/pair_matrix.rs
 M rust/vrs_solver/src/optimizer/sparrow/quantify/tracker.rs
 M rust/vrs_solver/src/optimizer/sparrow/sample/search.rs
 M rust/vrs_solver/src/optimizer/sparrow/sheet_edge_placement_catalog.rs
 M rust/vrs_solver/src/optimizer/sparrow/tests.rs
 M rust/vrs_solver/src/optimizer/sparrow/worker.rs
 M rust/vrs_solver/tests/sparrow_sheet_builder.rs
?? artifacts/benchmarks/sgh_q70/
?? artifacts/benchmarks/sgh_q71/
?? artifacts/benchmarks/sgh_q72/
?? artifacts/benchmarks/sgh_q73/
?? artifacts/benchmarks/sgh_q74/
?? canvases/egyedi_solver/sgh_q70_corner_first_residual_space_recovery.md
?? canvases/egyedi_solver/sgh_q71_anchor_edge_lock_and_flush_alignment.md
?? canvases/egyedi_solver/sgh_q72_full_instance_seed_fixed_bin_repack.md
?? canvases/egyedi_solver/sgh_q73_big_part_interlock_rowseed.md
?? canvases/egyedi_solver/sgh_q74_edge_anchored_interlock_pin.md
?? canvases/egyedi_solver/sgh_q75_single_solver_shape_cutover.md
?? codex/codex_checklist/egyedi_solver/sgh_q70_corner_first_residual_space_recovery.md
?? codex/codex_checklist/egyedi_solver/sgh_q71_anchor_edge_lock_and_flush_alignment.md
?? codex/codex_checklist/egyedi_solver/sgh_q72_full_instance_seed_fixed_bin_repack.md
?? codex/codex_checklist/egyedi_solver/sgh_q73_big_part_interlock_rowseed.md
?? codex/codex_checklist/egyedi_solver/sgh_q74_edge_anchored_interlock_pin.md
?? codex/codex_checklist/egyedi_solver/sgh_q75_single_solver_shape_cutover.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q70_corner_first_residual_space_recovery.yaml
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q71_anchor_edge_lock_and_flush_alignment.yaml
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q72_full_instance_seed_fixed_bin_repack.yaml
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q73_big_part_interlock_rowseed.yaml
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q74_edge_anchored_interlock_pin.yaml
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q75_single_solver_shape_cutover.yaml
?? codex/reports/egyedi_solver/sgh_q70_corner_first_residual_space_recovery.md
```

<!-- AUTO_VERIFY_END -->

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Ellenorzes |
| -------- | ------: | ------------------------ | ---------- | --------------------------- |
| 1. Nincs dual-geometry (egy alak) | DONE | `model.rs` (`SPInstance` mezo torolve), `quantify/tracker.rs` (`spacing_applied=false`) | A collision/boundary egy `base_shape`-en; 0 `spacing_collision_base_shape` referencia a kodban. | grep + build |
| 2. SolverInputGuard | DONE | `rust/vrs_solver/src/adapter.rs` (`CAVITY_PREPACK_TOP_LEVEL_HOLES_REMAIN`) | A pipeline elejen hard-fail top-level hole-ra (production hole-free -> nem aktivalodik). | kod-review |
| 3. Furat nem dontesi jel | DONE | `optimizer/sparrow/part_analysis.rs` (diagnosztika-only komment; sehol kivul nem olvasott) | A fit_score/priority/criticality outer-alak metrikakbol; furat-mezo csak diagnosztika. | grep (0 kulso olvaso) |
| 4. Tesztek zoldek a single-shape modellen | DONE | 550 lib pass; `sparrow_sheet_builder` 7/7; `sparrow_one_part_sheet_edge` 1/1; technology/spacing zold | A dual-geometry tesztek a single-shape (offset-bake) modellre frissitve. | cargo test / verify.sh |
| 5. Production no-regress | DONE | `artifacts/benchmarks/sgh_q74/q74_summary.json` (placed **274**, azonos a cutover elottivel); Q72 254 = wall-time-zaj | A kivett ut spacing=0-nal no-op; production `base_shape` = offset, valtozatlan. | Q72/Q74 600s |
| 6. verify.sh PASS | DONE | `codex/reports/egyedi_solver/sgh_q75_single_solver_shape_cutover.verify.log` (check.sh exit 0, 479s); AUTO_VERIFY blokk PASS | repo gate (pytest+mypy+Sparrow smoke+determinizmus) zold. | verify.sh |

## 6) Finding

A leiras fo architekturalis tezise (single solver-shape, spacing beegetve, spacing=0 belul) mar
production-aktiv volt (SGH-Q40; Q39 kontroll: 257 vs 146). Ez a task a maradek dual-geometry kodot
(Q36 `spacing_collision_base_shape`) vezeti ki es huzza be a SolverInputGuardot, byte-azonos
production mellett. A furat-jelek igazoltan diagnosztika-only-k. A diagnosztikai mezok/sema szandekosan
valtozatlanok (minimal-invaziv, zero-erteku churn elkerulese).
