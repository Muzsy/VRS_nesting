STATUS: PASS

# Q58A — SheetFeasibilityHints — Report

> Implementálva és verifikálva. `verify.sh` **PASS** (exit 0, determinizmus 10/10 byte-azonos). A
> `SheetFeasibilityHints` (area lower bound margin-shrunk basis-szal, kritikus kapacitás-becslés
> státusszal, target distribution, danger parts) kész, placement-mentes, confidence/basis-címkézett,
> valós LV8 artifacttal. Nem változtat placementet (Q58B köti be).

## 1) Meta

- **Task slug:** `sgh_q58a_sheet_feasibility_hints`
- **Kapcsolódó canvas:** `canvases/egyedi_solver/sgh_q58a_sheet_feasibility_hints.md`
- **Kapcsolódó goal YAML:** `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q58a_sheet_feasibility_hints.yaml`
- **Futás dátuma:** 2026-06-23
- **Branch / commit:** `main@84eea82` (working tree)
- **Fókusz terület:** `Solver preprocessing | Planning hints`

## 2) Scope

### 2.1 Cél
- SheetFeasibilityHints modell: area lower bound, kritikus kapacitás, target distribution, danger parts.
- Tiszta, confidence/basis-címkézett artifact.

### 2.2 Nem-cél
- BPP/sheet-builder viselkedés (Q58B); placement mutáció; final sheet-count proof.

## 3) Changed files

- **Rust:** `rust/vrs_solver/src/optimizer/sparrow/sheet_feasibility.rs` (új), `.../mod.rs`,
  `rust/vrs_solver/src/io.rs`, `rust/vrs_solver/tests/sparrow_sheet_feasibility_hints.rs` (új)
- **Artifacts:** `artifacts/benchmarks/sgh_q58a/sheet_feasibility_hints.json`
- **Docs/Codex:** ez a report + checklist

## 4) Verification commands

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml sheet_feasibility
cargo test --manifest-path rust/vrs_solver/Cargo.toml --test sparrow_one_part_sheet_edge
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q58a_sheet_feasibility_hints.md
```

## 5) DoD → Evidence Matrix

| DoD pont | Státusz | Bizonyíték (path + line) | Magyarázat | Kapcsolódó ellenőrzés |
| -------- | ------: | ------------------------ | ---------- | --------------------- |
| SheetFeasibilityHints létezik | PASS | `sheet_feasibility.rs` (`SheetFeasibilityHints`, `build_sheet_feasibility_hints`) | reusable modell + builder | `cargo test sheet_feasibility` (4+1 ok) |
| Area lower bound determinisztikus + margin-shrunk | PASS | `ceil(total/usable)`; `usable_sheet_area_basis="margin_shrunk"`; artifact area_lower_bound=1 | basis explicit | `area_lower_bound_is_deterministic_and_at_least_one` |
| Kapacitás státusz (nem exact proof) | PASS | `CapacityStatus` (unknown/plausible/...); LV8 status=unknown | sosem proven_by_focused_test itt | `estimates_are_labelled_not_proven` |
| Target distribution hint | PASS | LV8 est_max=2 → dist [2,2,2] (összeg=6) | ismételt kritikus típus eloszlás | `repeated_critical_type_gets_distribution_hint` |
| Danger parts lista | PASS | LV8 danger (large_sheet_span, high_fit_difficulty, large_repeated_quantity) | magas-criticality large anchor flag | `danger_parts_include_large_repeated_anchor` |
| Nincs placement mutáció | PASS | builder csak SparrowProblem-et olvas; semmit nem helyez | determinizmus byte-azonos | `verify.sh` PASS |
| Artifact stabil | PASS | `artifacts/benchmarks/sgh_q58a/sheet_feasibility_hints.json` | szerializálható, determinisztikus | integ. teszt |

## 6) Task-specific evidence

- Area lower bound valós benchmark inputon: `<TBD>`
- Top kritikus kapacitás-hintek: LV8 estimated_max_per_sheet=**2** (area_cap + span_cap konzervatív min),
  status=**unknown** (magas fit_difficulty), confidence ~0.55.
- Target distribution ismételt kritikus típusra: LV8 qty 6 → **[2, 2, 2]** (összeg 6).
- **HONEST FINDING:** az area-alapú becslés csak 2 LV8/tábla — a projektcél 3/tábla **nem** triviálisan
  area-feasible, interlockot/simultaneous admissiont igényel. A hint ezt helyesen `unknown`-ként jelzi;
  ez a Q58B/Q60 bemenete. Nincs hamis "3 feasible" állítás.

## 7) Advisory / Deviations

- **DEVIATION (io.rs):** a hint artifact a teszt-artifactból áll elő; az io.rs production export érintetlen.
- Q58A szándékosan **csak hint-számítás** — nincs BPP/sheet-builder mutáció (az a Q58B). A becslések
  confidence/basis-címkével és statusszal vannak ellátva; az area lower bound nem final sheet-count proof.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-06-23T06:32:27+02:00 → 2026-06-23T06:36:17+02:00 (230s)
- parancs: `./scripts/check.sh`
- log: `/mnt/workspace/VRS_nesting/codex/reports/egyedi_solver/sgh_q58a_sheet_feasibility_hints.verify.log`
- git: `main@84eea82`
- módosított fájlok (git status): 92

**git diff --stat**

```text
 .../src/optimizer/sparrow/bpp_reduction.rs         |   8 +
 .../src/optimizer/sparrow/fixed_sheet.rs           |   4 +
 rust/vrs_solver/src/optimizer/sparrow/mod.rs       |  11 +
 rust/vrs_solver/src/optimizer/sparrow/model.rs     |  41 ++
 .../src/optimizer/sparrow/quantify/mod.rs          |   1 +
 .../src/optimizer/sparrow/quantify/pair_matrix.rs  | 584 ++++++++++++++++++++-
 rust/vrs_solver/src/optimizer/sparrow/tests.rs     |  10 +-
 worker/cavity_prepack.py                           | 114 ++++
 8 files changed, 766 insertions(+), 7 deletions(-)
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
```

<!-- AUTO_VERIFY_END -->
