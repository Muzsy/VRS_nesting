# Q59 — BandInsert true-extreme slot-edge placement

## Goal / Funkció

Emeld a `SkeletonRole::BandInsert` placementet a durva bbox/ortogonális slot-seedről true-extreme,
continuous, spacing-correct slot-edge placementre — ugyanazzal a geometriai sztenderddel, mint a
Q55B Anchor út.

## Context / Háttér

A jelenlegi `band_insert_seeds(...)` kb. így működik: legnagyobb szabad slot bbox → long/short
orientációk → 0/90/180/270-szerű rotációk → rect-min a slot sarkokba. Ez nem elég continuous rotation
és valódi kontúr placement esetén. A BandInsert helyette: szabad slot él → valós part kontúr
orientáció → forgatott spacing-offset true extrema → margin/slot-edge igazított transláció → exact
validáció. A slot bbox csak ranking/target régió, **nem** collision truth.

## Source of truth

- `AGENTS.md`, `docs/codex/overview.md`, `docs/codex/yaml_schema.md`,
  `docs/codex/report_standard.md`, `docs/qa/testing_guidelines.md`
- Forrásterv: `tmp/plans/q56_q60_preprocessing_tasks/Q59_BandInsert_true_extreme_slot_edge_placement.md`
- Kapcsolódó proof: `codex/reports/egyedi_solver/sgh_q55b_fix_one_part_sheet_edge.md`

## Existing code anchors

- `rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs` — `band_insert_seeds(...)`,
  `try_admit_critical(...)`, BandInsert role ág.
- `rust/vrs_solver/src/optimizer/sparrow/sheet_skeleton.rs` —
  `largest_edge_connected_free_slot(...)`.
- `rust/vrs_solver/src/optimizer/sparrow/feature_candidate_generator.rs` — Q55B true-extreme
  sheet-edge logika, `bounded_sheet_edge_repair(...)`, `min_width_rotations(...)`.
- `rust/vrs_solver/src/optimizer/sparrow/orientation_catalog.rs` (Q56A) — rotations, ha létezik.

## Valós repo anchorok

```text
rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs
rust/vrs_solver/src/optimizer/sparrow/sheet_skeleton.rs
rust/vrs_solver/src/optimizer/sparrow/feature_candidate_generator.rs
rust/vrs_solver/src/optimizer/sparrow/model.rs
rust/vrs_solver/src/io.rs
```

## Scope

- `SlotEdgePlacementCandidate` (vagy ekvivalens) slot-edge placement candidate modell.
- Slot-edge candidate generálás (corner + center fallback) a szabad slot bbox-ból.
- True-extreme geometria + exact CDE/boundary validáció a teljes sheet és a placed partok ellen.
- Gate: `VRS_BAND_INSERT_TRUE_EXTREME=1`; fallback megőrizve + logolva.
- JSON + SVG artifact.

## Out of scope

- Anchor/Interlock role átírása (Q56C / Q57B).
- Simultaneous triple admission (Q60).
- A meglévő `band_insert_seeds(...)` fallback törlése a bizonyítás előtt.

## Required implementation

`SlotEdgePlacementCandidate` mezők: `candidate_source` (`true_extreme_slot_edge_band_insert`),
`slot_bbox [f64;4]`, `target_slot_edge`, `secondary_axis_policy`, `rotation_deg`,
`selected_edge_index`, `selected_edge_angle_deg`, `translation_x`, `translation_y`,
`slot_edge_margin_error`, `boundary_clear`, `collision_clear`, `score`.

Slot-edge generálás egy szabad slot bbox-ra: `slot_left-bottom/top`, `slot_right-bottom/top`,
`slot_bottom-left/right`, `slot_top-left/right`, `slot_center` fallback. A placement **a teljes
sheet és a placed partok** ellen validálva/klippelve; a slot bbox ranking/target régió, nem collision
truth.

Geometria: OrientationCatalog rotációk, `spacing_collision_base_shape` true extrema rotáció után,
slot-edge alignment (a sheet-edge alignment analógiája), exact CDE a placed szomszédok ellen, exact
boundary a sheet ellen. **Ne** használd a `dims_for_rotation(part.width, part.height, rot)`-ot final
fit alapként; maradhat olcsó prefilternek, ha a végül elfogadott placement true-extreme/CDE validált.

Scoring: `+`fits a legnagyobb edge-connected szabad slotba, `+`maradék hasznos terület megőrzés,
`+`dead strip elkerülés, `+`target kvóta (ha Q58 hint van), `+`support/contact a slot-élhez/placed
párhoz, `-`túlzott befelé drift a slot-éltől, `-`collision/boundary hard fail.

## Required diagnostics

Mezők: `bpp_role_band_insert_slot_edge_generated/valid/accepted`,
`bpp_role_band_insert_accepted_source`, `bpp_role_band_insert_slot_bbox`,
`bpp_role_band_insert_target_slot_edge`, `bpp_role_band_insert_rotation_deg`,
`bpp_role_band_insert_slot_edge_margin_error`, `bpp_role_band_insert_rejection_summary`.

Artifact: `artifacts/benchmarks/sgh_q59/band_insert_slot_edge_candidates.json` + `.svg`. Az SVG
mutassa: sheet, placed Anchor/Interlock partok (ha vannak), legnagyobb edge-connected slot bbox,
BandInsert candidate-ek, kiválasztott BandInsert candidate.

## Required tests / runners

Teszt: `rust/vrs_solver/tests/sparrow_band_insert_slot_edge.rs`. Ellenőrzések:

1. A BandInsert role true-extreme slot-edge candidate-eket tud generálni.
2. A candidate rotációk continuous partoknál nem korlátozódnak fix ortogonális rotációkra.
3. Az elfogadott candidate spacing-expanded extrémát használ.
4. A meglévő bbox `band_insert_seeds(...)` út már nem az elsődleges elfogadott út, ha a Q59 gate be van kapcsolva.
5. A fallback elérhető és logolt.

Parancsok:

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml band_insert_slot_edge
VRS_BAND_INSERT_TRUE_EXTREME=1 cargo test --manifest-path rust/vrs_solver/Cargo.toml band_insert_slot_edge
cargo test --manifest-path rust/vrs_solver/Cargo.toml --test sparrow_one_part_sheet_edge
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q59_band_insert_true_extreme_slot_edge_placement.md
```

## Acceptance criteria

```text
- A BandInsert-nek van true-extreme slot-edge candidate útja.
- Explicit gate alatt vagy production útként, fallback logolva.
- Az elfogadott BandInsert placementek CDE/boundary validak.
- A diagnosztika és a vizuális artifact bizonyítja a source-ot és a geometriát.
- A Q55B/Q56C/Q57B utak továbbra is zöldek.
```

## Hard restrictions

```text
- a fallback nem törölhető az új út bizonyítása előtt
- nincs bbox-only slot fit elfogadás
- continuous BandInsert rotációk nem snappelhetők 0/90/180/270-re
- a slot bbox nem exact szabad tér
- a meglévő placed partok nem hagyhatók figyelmen kívül a validációnál
- nincs NFP, nincs part-id hack, nincs spacing/margin gyengítés
- cavity/hole logika nem kerülhet a Rust fősolverbe
- CDE/final exact validation marad az igazság
```

## Rollback

- `VRS_BAND_INSERT_TRUE_EXTREME` gate default off → a meglévő `band_insert_seeds(...)` bbox út marad
  (no-regression).
- Ha a true-extreme út valid candidate-et nem ad, a fallback bbox út lép be, logolva — nincs csendes
  romlás.

## Deliverables

```text
canvases/egyedi_solver/sgh_q59_band_insert_true_extreme_slot_edge_placement.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q59_band_insert_true_extreme_slot_edge_placement.yaml
codex/prompts/egyedi_solver/sgh_q59_band_insert_true_extreme_slot_edge_placement/run.md
codex/codex_checklist/egyedi_solver/sgh_q59_band_insert_true_extreme_slot_edge_placement.md
codex/reports/egyedi_solver/sgh_q59_band_insert_true_extreme_slot_edge_placement.md
codex/reports/egyedi_solver/sgh_q59_band_insert_true_extreme_slot_edge_placement.verify.log
```
