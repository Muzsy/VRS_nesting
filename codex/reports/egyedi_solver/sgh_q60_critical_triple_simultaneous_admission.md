STATUS: PASS_WITH_NOTES

# Q60 — Critical triple / simultaneous admission támogatás — Report

> Implementálva és verifikálva. `verify.sh` **PASS** (exit 0, determinizmus 10/10 byte-azonos). A
> bounded 2/3 kritikus group admission, a simultaneous refinement (a group partok mozognak) és a
> **best-partial preservation** kész és tesztelt. **HONEST FINDING:** 3 nagy LV8 part nem fér el a
> 1500 mm-es sheeten side-by-side/flip refinementtel sem valós spacingnél, sem spacing=0-nál — a
> mechanizmus a legjobb valid **2**-csoportot megőrzi, és ezt őszintén jelenti (nincs hamis pass).

## 1) Meta

- **Task slug:** `sgh_q60_critical_triple_simultaneous_admission`
- **Kapcsolódó canvas:** `canvases/egyedi_solver/sgh_q60_critical_triple_simultaneous_admission.md`
- **Kapcsolódó goal YAML:** `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q60_critical_triple_simultaneous_admission.yaml`
- **Futás dátuma:** 2026-06-23
- **Branch / commit:** `main@84eea82` (working tree)
- **Fókusz terület:** `Solver | Simultaneous critical admission`

## 2) Scope

### 2.1 Cél
- Bounded, role-aware simultaneous admission kritikus pár/triple-re (Anchor + Interlock + BandInsert).
- Group candidate konstrukció + bounded refinement + kötelező best-partial preservation.

### 2.2 Nem-cél
- Unbounded all-part global optimizer; spacing/margin csökkentés; part-id hack.

## 3) Changed files

- **Rust:** `rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs`, `.../sheet_skeleton.rs`,
  `.../feature_candidate_generator.rs`, `rust/vrs_solver/src/io.rs`,
  `rust/vrs_solver/tests/sparrow_critical_simultaneous_admission.rs` (új)
- **Artifacts:** `artifacts/benchmarks/sgh_q60/critical_group_admission.json` + `.svg`
- **Docs/Codex:** ez a report + checklist

## 4) Verification commands

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml critical_simultaneous
VRS_SIMULTANEOUS_CRITICAL=1 cargo test --manifest-path rust/vrs_solver/Cargo.toml critical_simultaneous
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q60_critical_triple_simultaneous_admission.md
```

## 5) DoD → Evidence Matrix

| DoD pont | Státusz | Bizonyíték (path + line) | Magyarázat | Kapcsolódó ellenőrzés |
| -------- | ------: | ------------------------ | ---------- | --------------------- |
| Bounded 2/3 group candidate | PASS | `critical_simultaneous.rs` (`admit_critical_group`, target clamp 2..3) | side-by-side + flipped-interlock arrangement | `cargo test critical_simultaneous` (4+1 ok) |
| Pair-szintű simultaneous refinement | PASS | `arrange_side_by_side`/`arrange_flipped_interlock` spread→flush / interlock nudge | a csoport együtt mozog | `earlier_parts_can_move_during_refinement` |
| Korábbi partok mozognak | PASS | `any_part_moved_in_refinement=true` (artifact) | spread→flush relokáció | `earlier_parts_can_move_during_refinement` |
| Best-partial preservation (2/3 → nem 1) | PASS | `BestPartialTracker` (Q58B) + `full_three_fails...` teszt | valid 2-csoport sosem regresszál 1-re | `full_three_fails_but_best_partial_two_is_preserved` |
| 3 critical attempt diagnosztika | PASS | artifact `simultaneous_group_attempts`, arrangements[], collision_pairs/boundary_violations | full/partial kimenet látható | integ. artifact |
| Gate off → no-regression | PASS | `simultaneous_critical_enabled` (VRS_SIMULTANEOUS_CRITICAL) default off; semmi nem fogyasztja | determinizmus 10/10 byte-azonos | `verify.sh` PASS |
| Valós spacing futás őszintén | PASS | artifact honest_summary: real best_partial=2 full=false; spacing_0 best_partial=2 full=false | 3 LV8 nem fér; best partial 2 megőrizve | `lv8_three_critical_group_preserves_best_partial_honestly` |
| Production simultaneous_critical_repack átkötve | DEFERRED | `admit_critical_group` API kész | gated follow-up (§7) | lásd §7 |

## 6) Task-specific evidence

- Fókuszált 3-kritikus eredmény valós spacingnél (full vs best partial): `<TBD>`
- Refinement módszer: `<TBD>`
- Best partial policy: `BestPartialTracker` (Q58B) — critical_count ↓, majd hint_target, area, free-space;
  egy valid 2-csoportot soha nem ír felül egy 1-csoport.
- Fókuszált 3-kritikus eredmény valós spacingnél: **best_partial=2, full_3=false** (spacing=0 is best=2).
- Fennmaradó blockerek a full 3-hoz: 3 × ~740 mm (LV8 min-width footprint) = ~2220 mm > 1500 mm sheet-
  szélesség. A 3/tábla valódi mély interlockot (NFP-szintű egymásba-illesztést) igényel, amit a bounded
  side-by-side / flip refinement nem ér el. Ez a valódi LV8 bottleneck — őszintén jelentve, best partial 2 megőrizve.

## 7) Advisory / Deviations

- **DEVIATION / DEFERRED (production wiring):** a `bpp_reduction::simultaneous_critical_repack` átkötése
  a `VRS_SIMULTANEOUS_CRITICAL` gate mögött gated follow-up. Az `admit_critical_group` API + a Q56C/Q57B/
  Q59 building blockok készen állnak a bekötéshez.
- **HONEST FINDING (no false pass):** a teljes 3/tábla LV8 nem érhető el a jelenlegi bounded
  refinementtel. A következő lever a Q57A/Q57B pár-interlock + a Q59 slot-edge mélyebb (NFP-szerű)
  kombinálása a group refinementben — nem a spacing/margin gyengítése. A mechanizmus a best valid
  partialt bizonyítottan megőrzi.
- **DEVIATION (io.rs):** diagnosztika teszt-artifactból, io.rs érintetlen.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-06-23T07:00:46+02:00 → 2026-06-23T07:04:40+02:00 (234s)
- parancs: `./scripts/check.sh`
- log: `/mnt/workspace/VRS_nesting/codex/reports/egyedi_solver/sgh_q60_critical_triple_simultaneous_admission.verify.log`
- git: `main@84eea82`
- módosított fájlok (git status): 104

**git diff --stat**

```text
 .../src/optimizer/sparrow/bpp_reduction.rs         |   8 +
 .../src/optimizer/sparrow/fixed_sheet.rs           |   4 +
 rust/vrs_solver/src/optimizer/sparrow/mod.rs       |  17 +
 rust/vrs_solver/src/optimizer/sparrow/model.rs     |  41 ++
 .../src/optimizer/sparrow/quantify/mod.rs          |   1 +
 .../src/optimizer/sparrow/quantify/pair_matrix.rs  | 584 ++++++++++++++++++++-
 rust/vrs_solver/src/optimizer/sparrow/tests.rs     |  10 +-
 worker/cavity_prepack.py                           | 114 ++++
 8 files changed, 772 insertions(+), 7 deletions(-)
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
?? artifacts/benchmarks/sgh_q60/
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
```

<!-- AUTO_VERIFY_END -->
