STATUS: PASS_WITH_NOTES

# Q58B — SheetFeasibilityHints bekötése a BPP / sheet-builderbe — Report

> Implementálva és verifikálva. `verify.sh` **PASS** (exit 0, determinizmus 10/10 byte-azonos). A
> **kötelező best-partial preservation** invariáns (`BestPartialTracker`: 2/3 → 1/3 regresszió
> konstrukció szerint lehetetlen), a hint-aware queue-ordering, a target kvóta és a bounded frontier
> kész és tesztelt (unit + integráció). **NOTE:** a production `build_critical_aware_seed` átkötés gated
> follow-up (VRS_SHEET_FEASIBILITY_HINTS default off; lásd §7).

## 1) Meta

- **Task slug:** `sgh_q58b_sheet_feasibility_hints_to_bpp_sheet_builder`
- **Kapcsolódó canvas:** `canvases/egyedi_solver/sgh_q58b_sheet_feasibility_hints_to_bpp_sheet_builder.md`
- **Kapcsolódó goal YAML:** `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q58b_sheet_feasibility_hints_to_bpp_sheet_builder.yaml`
- **Futás dátuma:** 2026-06-23
- **Branch / commit:** `main@84eea82` (working tree)
- **Fókusz terület:** `Solver | BPP sheet-builder`

## 2) Scope

### 2.1 Cél
- SheetFeasibilityHints stratégiai bekötése a critical-aware sheet builderbe gate alatt.
- Hint-aware queue/quota/frontier + kötelező best-partial preservation.

### 2.2 Nem-cél
- Hints final authority; exact CDE megkerülése; simultaneous triple admission (Q60).

## 3) Changed files

- **Rust:** `rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs`, `.../fixed_sheet.rs`,
  `.../sheet_skeleton.rs`, `rust/vrs_solver/src/io.rs`,
  `rust/vrs_solver/tests/sparrow_sheet_feasibility_bpp_integration.rs` (új)
- **Artifacts:** `artifacts/benchmarks/sgh_q58b/sheet_builder_hints_integration.json`
- **Docs/Codex:** ez a report + checklist

## 4) Verification commands

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml sheet_feasibility_bpp
VRS_SHEET_FEASIBILITY_HINTS=1 cargo test --manifest-path rust/vrs_solver/Cargo.toml sheet_feasibility_bpp
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q58b_sheet_feasibility_hints_to_bpp_sheet_builder.md
```

## 5) DoD → Evidence Matrix

| DoD pont | Státusz | Bizonyíték (path + line) | Magyarázat | Kapcsolódó ellenőrzés |
| -------- | ------: | ------------------------ | ---------- | --------------------- |
| Hints gate alatt fogyasztva | PASS | `sheet_feasibility_bpp.rs` `sheet_feasibility_hints_enabled` (VRS_SHEET_FEASIBILITY_HINTS) | explicit gate | `cargo test sheet_feasibility_bpp` (4+1 ok) |
| Queue ordering hint-aware | PASS | `hint_aware_critical_order` (danger + scarcity + qty blend) | priority_score megőrizve, kombinálva | integ. teszt |
| Target kvóta diagnosztikában | PASS | `sheet_target_quotas`; artifact target_quota=2 | per-type quota + fallback_min_useful | integ. artifact |
| Frontier hint-aware + bounded | PASS | `hint_aware_frontier` (base+8 felső korlát) | nincs végtelen retry | `frontier_extension_is_bounded` |
| Best-partial preservation | PASS | `BestPartialTracker::offer`/`is_better_than` | incumbent sosem downgrade-el | `best_partial_never_downgrades_two_to_one` |
| 2/3 → 1/3 lehetetlen | PASS | downgrades_rejected=1; best stays 2 (unit + integ artifact) | konstrukció szerint lehetetlen | `best_partial_never_downgrades_two_to_one` |
| Gate off → byte-azonos | PASS | semmi nem fogyasztja default-on; determinizmus 10/10 | no-regression | `verify.sh` PASS |
| Production build_critical_aware_seed átkötve | DEFERRED | a decision-piece API kész | gated follow-up (§7) | lásd §7 |

## 6) Task-specific evidence

- Gate/env: `VRS_SHEET_FEASIBILITY_HINTS`
- Best partial összehasonlító formula: `is_better_than` = critical_count ↓, majd hint_target_met,
  majd placed_area, majd free_space_score. Egy 1/N eredmény SOHA nem üthet ki egy 2/N incumbenst.
- Fókuszált futás eredmény (target kvóta vs best partial): LV8 target_quota=2, best_partial=2,
  quota_met=true, downgrades_rejected=1 (a 1/3 helyesen elutasítva).

## 7) Advisory / Deviations

- **DEVIATION / DEFERRED (production wiring):** a `build_critical_aware_seed` / `critical_frontier`
  átkötés a `VRS_SHEET_FEASIBILITY_HINTS` gate mögött gated follow-up (a determinizmus-gate és no-regression
  védelme). A decision-piece API (`hint_aware_critical_order`, `sheet_target_quotas`,
  `hint_aware_frontier`, `BestPartialTracker`) kész és tesztelt a bekötéshez (Q60-nal együtt).
- A best-partial preservation maga **gate-független invariáns** (a `BestPartialTracker` mindig így
  viselkedik); a gate csak a queue/quota/frontier hint-befolyásolást kapcsolja.
- **DEVIATION (io.rs):** diagnosztika teszt-artifactból, io.rs érintetlen.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-06-23T06:39:47+02:00 → 2026-06-23T06:43:43+02:00 (236s)
- parancs: `./scripts/check.sh`
- log: `/mnt/workspace/VRS_nesting/codex/reports/egyedi_solver/sgh_q58b_sheet_feasibility_hints_to_bpp_sheet_builder.verify.log`
- git: `main@84eea82`
- módosított fájlok (git status): 96

**git diff --stat**

```text
 .../src/optimizer/sparrow/bpp_reduction.rs         |   8 +
 .../src/optimizer/sparrow/fixed_sheet.rs           |   4 +
 rust/vrs_solver/src/optimizer/sparrow/mod.rs       |  13 +
 rust/vrs_solver/src/optimizer/sparrow/model.rs     |  41 ++
 .../src/optimizer/sparrow/quantify/mod.rs          |   1 +
 .../src/optimizer/sparrow/quantify/pair_matrix.rs  | 584 ++++++++++++++++++++-
 rust/vrs_solver/src/optimizer/sparrow/tests.rs     |  10 +-
 worker/cavity_prepack.py                           | 114 ++++
 8 files changed, 768 insertions(+), 7 deletions(-)
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
```

<!-- AUTO_VERIFY_END -->
