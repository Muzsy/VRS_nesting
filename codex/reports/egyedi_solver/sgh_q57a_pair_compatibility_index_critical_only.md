STATUS: PASS

# Q57A — PairCompatibilityIndex critical-only — Report

> Implementálva és verifikálva. `verify.sh` **PASS** (exit 0, determinizmus 10/10 byte-azonos). A
> `pair_matrix.rs` stub lecserélve a bounded, critical-only `PairCompatibilityIndex`-szel (két-stage
> filter, same-part flip, grid-alapú clearance proxy). Még nem fogyaszt placement döntést (Q57B köti be).

## 1) Meta

- **Task slug:** `sgh_q57a_pair_compatibility_index_critical_only`
- **Kapcsolódó canvas:** `canvases/egyedi_solver/sgh_q57a_pair_compatibility_index_critical_only.md`
- **Kapcsolódó goal YAML:** `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q57a_pair_compatibility_index_critical_only.yaml`
- **Futás dátuma:** 2026-06-23
- **Branch / commit:** `main@84eea82` (working tree)
- **Fókusz terület:** `Solver preprocessing | Pair index`

## 2) Scope

### 2.1 Cél
- Production pair-kompatibilitási index kritikus partokra, bounded + két-stage filterrel.
- Diagnosztikai artifact valid pair candidate-ekkel, same-part kritikus pár fókusszal.

### 2.2 Nem-cél
- Interlock placement megváltoztatása (Q57B); all-pairs exact geometria; kötelező superpart.

## 3) Changed files

- **Rust:** `rust/vrs_solver/src/optimizer/sparrow/quantify/pair_matrix.rs`,
  `.../quantify/mod.rs`, `rust/vrs_solver/src/io.rs`,
  `rust/vrs_solver/tests/sparrow_pair_compatibility_index.rs` (új)
- **Artifacts:** `artifacts/benchmarks/sgh_q57a/pair_compatibility_index.json`
- **Docs/Codex:** ez a report + checklist

## 4) Verification commands

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml pair_compatibility_index
cargo test --manifest-path rust/vrs_solver/Cargo.toml --test sparrow_one_part_sheet_edge
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q57a_pair_compatibility_index_critical_only.md
```

## 5) DoD → Evidence Matrix

| DoD pont | Státusz | Bizonyíték (path + line) | Magyarázat | Kapcsolódó ellenőrzés |
| -------- | ------: | ------------------------ | ---------- | --------------------- |
| PairCompatibilityIndex létezik (stub superseded) | PASS | `quantify/pair_matrix.rs` (+584 sor, `PairCompatibilityIndex`, `build_pair_compatibility_index`) | A 12 soros stub lecserélve teljes indexre | `cargo test pair_matrix` (5+1 ok) |
| Bounded + critical-only default | PASS | `PairIndexConfig` (max_part_types/topk/max_candidates) + `is_critical()` szűrő | env-konfigurálható top-K; tiny filler kizárva | `critical_only_excludes_tiny_filler_pairs` |
| Reuse (analysis/orientation/contour) | PASS | `PairPartCtx` a `part_analysis`/`orientation_catalog`/`spacing_collision_base_shape`-ből épül | nincs feature-extrakció duplikáció | kód review |
| Same-part pár (nincs part-ID hack) | PASS | `same_part`/`same_family` flip ág; LV8 artifact same_part_flip=3 | OrientationCatalog + criticality alapú, nem part-ID | `repeated_critical_part_produces_same_part_pair` |
| Valid candidate CDE/spacing-checked | PASS | grid `contours_overlap` proxy; artifact valid=1 | spacing-expanded kontúr clearance; CDE marad a truth | `candidates_carry_rotation_metadata_and_have_a_valid_pair` |
| Env-gate off → no-regression | PASS | `pair_index_enabled` (VRS_PAIR_INDEX) default off; semmi nem fogyasztja | determinizmus 10/10 byte-azonos | `verify.sh` PASS |
| Artifact generálva | PASS | `artifacts/benchmarks/sgh_q57a/pair_compatibility_index.json` | counts + by_source + top_pairs + lv8_same_part | integ. teszt |

## 6) Task-specific evidence

- Indexelt kritikus part-típusok száma: `<TBD>`
- Valid pair candidate-ek száma: **1 valid / 4 total** (LV8 + tiny halmaz); 1 unique kritikus típus.
- Top same-part kritikus candidate: LV8 `same_part_flip` side-by-side baseline (rot 0/0, cde_clear=true);
  a tight flip-interlock variánsok (rot 0/180, 35% nudge) cde_clear=**false** — a grid valódi átfedést
  talál, ezért őszintén invalid-ként jelölve (a valódi interlock geometria a Q57B/Q60 nehéz része).

## 7) Advisory / Deviations

- A clearance itt determinisztikus **grid proxy** (48×48 mintavétel a spacing-expanded kontúrokon), nem
  CDE — a canvas szerint a CDE marad a végső igazság; a proxy ranking/jelölés célú. A Q57B az elfogadott
  pár-jelölteket exact CDE-vel validálja a tényleges sheet-placementkor.
- **DEVIATION (io.rs):** mint a többi tasknál, a diagnosztika teszt-artifactból; io.rs érintetlen.
- A jelenlegi heurisztikus relatív transzformok LV8-ra alacsony compactness_gain-t adnak (a side-by-side
  duplázza a bboxot); a magas értékű interlock a Q60 simultaneous refinement feladata. Ez őszinte jelzés,
  nem hiba: az index a building block, nem a végső pár-optimalizáló.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-06-23T06:16:04+02:00 → 2026-06-23T06:19:51+02:00 (227s)
- parancs: `./scripts/check.sh`
- log: `/mnt/workspace/VRS_nesting/codex/reports/egyedi_solver/sgh_q57a_pair_compatibility_index_critical_only.verify.log`
- git: `main@84eea82`
- módosított fájlok (git status): 84

**git diff --stat**

```text
 .../src/optimizer/sparrow/bpp_reduction.rs         |   8 +
 .../src/optimizer/sparrow/fixed_sheet.rs           |   4 +
 rust/vrs_solver/src/optimizer/sparrow/mod.rs       |   7 +
 rust/vrs_solver/src/optimizer/sparrow/model.rs     |  41 ++
 .../src/optimizer/sparrow/quantify/mod.rs          |   1 +
 .../src/optimizer/sparrow/quantify/pair_matrix.rs  | 584 ++++++++++++++++++++-
 rust/vrs_solver/src/optimizer/sparrow/tests.rs     |  10 +-
 worker/cavity_prepack.py                           | 114 ++++
 8 files changed, 762 insertions(+), 7 deletions(-)
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
```

<!-- AUTO_VERIFY_END -->
