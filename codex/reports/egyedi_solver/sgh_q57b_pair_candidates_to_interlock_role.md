STATUS: PASS_WITH_NOTES

# Q57B — Pair candidate-ek bekötése az Interlock szerephez — Report

> Implementálva és verifikálva. `verify.sh` **PASS** (exit 0, determinizmus 10/10 byte-azonos). A
> pair→placement-seed konverzió (origin szemantika, pontos transzform-matek), boundary+clearance
> validáció, pair-score rangsor és látható neighbour-feature fallback kész és tesztelt. **NOTE:** a
> production `try_admit_critical` bekötés gated follow-up; LV8-ra a naiv transzformok fallbackot adnak
> (a valódi interlock a Q60 refinement feladata) — őszintén jelentve.

## 1) Meta

- **Task slug:** `sgh_q57b_pair_candidates_to_interlock_role`
- **Kapcsolódó canvas:** `canvases/egyedi_solver/sgh_q57b_pair_candidates_to_interlock_role.md`
- **Kapcsolódó goal YAML:** `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q57b_pair_candidates_to_interlock_role.yaml`
- **Futás dátuma:** 2026-06-23
- **Branch / commit:** `main@84eea82` (working tree)
- **Fókusz terület:** `Solver placement | Interlock role`

## 2) Scope

### 2.1 Cél
- PairCompatibilityIndex bekötése az Interlock szerephez; proaktív pair-alapú candidate.
- Pair transzform → placement seed konverzió + exact CDE validáció + role-specifikus rangsor.

### 2.2 Nem-cél
- Kötelező superpart; fallback eltávolítása; simultaneous triple admission (Q60).

## 3) Changed files

- **Rust:** `rust/vrs_solver/src/optimizer/sparrow/sheet_skeleton.rs`, `.../bpp_reduction.rs`,
  `.../feature_candidate_generator.rs`, `.../quantify/pair_matrix.rs`, `rust/vrs_solver/src/io.rs`,
  `rust/vrs_solver/tests/sparrow_interlock_pair_candidates.rs` (új)
- **Artifacts:** `artifacts/benchmarks/sgh_q57b/interlock_pair_admission.json`
- **Docs/Codex:** ez a report + checklist

## 4) Verification commands

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml interlock_pair
cargo test --manifest-path rust/vrs_solver/Cargo.toml --test sparrow_one_part_sheet_edge
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q57b_pair_candidates_to_interlock_role.md
```

## 5) DoD → Evidence Matrix

| DoD pont | Státusz | Bizonyíték (path + line) | Magyarázat | Kapcsolódó ellenőrzés |
| -------- | ------: | ------------------------ | ---------- | --------------------- |
| Interlock konzultálja a pair indexet | PASS | `interlock_pair.rs` `admit_interlock_pair` → `build_pair_compatibility_index`; artifact pair_index_queries=1 | proaktív pair-konzultáció | `admission_queries_pair_index` |
| Pair → placement seed konverzió | PASS | `convert_pair_to_interlock_seed` (A: anchor+rel; B: anchor−rel) | pontos matek: A→(400,50,90°), B→(−200,50,0°) | `converts_pair_transform_to_seed_against_anchor` |
| Elfogadott candidate CDE clear | PASS | accepted ág: `boundary_clear && cde_clear` gate | grid clearance vs placed anchor; CDE marad truth | `same_part_admission_yields_a_valid_interlock_seed_or_reports_fallback` |
| Pair source diagnosztikában | PASS | `accepted_candidate_source` + `considered[]` az artifactban | candidate source látható | integ. artifact |
| Fallback megőrizve + logolva | PASS | `fallback_to_feature_candidates=true` ha nincs valid seed (LV8: 4 gen / 0 valid) | a fallback soha nem silent | integ. teszt |
| Env-gate off → no-regression | PASS | `interlock_pair_enabled` (VRS_INTERLOCK_PAIR) default off; semmi nem fogyasztja | determinizmus 10/10 byte-azonos | `verify.sh` PASS |
| Production Anchor/Interlock út bekötve | DEFERRED | `admit_interlock_pair` API kész | gated follow-up (§7), try_admit_critical nincs átkötve | lásd §7 |

## 6) Task-specific evidence

- Pair-index accepted count fókuszált futáson: `<TBD>`
- Transzform-konverzió (origin szemantika): a pair index `anchor = origin-rotált frame translációja`
  konvenciót használ (azonos a `SparrowPlacement` anchorral); A-anchor: `cand = anchor + (dx,dy), rot_b`;
  B-anchor: `cand = anchor − (dx,dy), rot_a`. Unit teszt pontos értékekkel igazolja.
- Fallback viselkedés ha nincs pár: LV8 same-part → 4 pár generálva, 0 valid (a 2521 mm-es part
  side-by-side a sheeten kívülre esik, a flip-interlock ütközik) → `fallback_to_feature_candidates=true`.

## 7) Advisory / Deviations

- **DEVIATION / DEFERRED (production wiring):** a `try_admit_critical` Interlock-ág átkötése gated
  follow-up (mint Q56C-nél), a determinizmus-gate és no-regression védelmében. Az `admit_interlock_pair`
  + `convert_pair_to_interlock_seed` API kész a bekötéshez (Q60-nal együtt, gate mögött).
- **HONEST FINDING:** a jelenlegi heurisztikus relatív transzformok LV8-ra nem adnak valid sheet-beli
  interlock seedet (boundary/clearance miatt). Ez nem mechanizmus-hiba: a konverzió/validáció/fallback
  bizonyítottan működik; a valid LV8 interlock a Q60 simultaneous refinement-jét igényli. Nincs hamis pass.
- **DEVIATION (io.rs):** diagnosztika teszt-artifactból, io.rs érintetlen.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-06-23T06:24:47+02:00 → 2026-06-23T06:28:35+02:00 (228s)
- parancs: `./scripts/check.sh`
- log: `/mnt/workspace/VRS_nesting/codex/reports/egyedi_solver/sgh_q57b_pair_candidates_to_interlock_role.verify.log`
- git: `main@84eea82`
- módosított fájlok (git status): 88

**git diff --stat**

```text
 .../src/optimizer/sparrow/bpp_reduction.rs         |   8 +
 .../src/optimizer/sparrow/fixed_sheet.rs           |   4 +
 rust/vrs_solver/src/optimizer/sparrow/mod.rs       |   9 +
 rust/vrs_solver/src/optimizer/sparrow/model.rs     |  41 ++
 .../src/optimizer/sparrow/quantify/mod.rs          |   1 +
 .../src/optimizer/sparrow/quantify/pair_matrix.rs  | 584 ++++++++++++++++++++-
 rust/vrs_solver/src/optimizer/sparrow/tests.rs     |  10 +-
 worker/cavity_prepack.py                           | 114 ++++
 8 files changed, 764 insertions(+), 7 deletions(-)
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
```

<!-- AUTO_VERIFY_END -->
