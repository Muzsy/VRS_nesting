# Q56C — SheetEdgePlacementCatalog / edge-corner Anchor candidate-ek

## Goal / Funkció

Kösd össze a Q55B true-extreme sheet-edge placementet a meglévő skeleton `Anchor` szereppel és a
free-space scoringgal. Hozz létre egy újrahasználható `SheetEdgePlacementCatalog`-ot kritikus Anchor
placementhez, amely **edge+corner** variánsokat generál (nem csak edge+center), és a maradék hasznos,
edge-connected szabad teret megőrző jelöltet választja.

## Context / Háttér

A repo ma egy kritikus partot sheet-edge-re tud illeszteni (Q55B), de a production Anchor candidate út
gyenge: az él-illesztés megvan, de a másodlagos tengely középre húz, nem szándékos
corner/free-space-megőrző placementre. Egy kritikus nagy partot edge+corner variánsokban kell
értékelni, hogy a solver a leghasznosabb maradék él-kapcsolt szabad teret tartsa meg.

## Source of truth

- `AGENTS.md`, `docs/codex/overview.md`, `docs/codex/yaml_schema.md`,
  `docs/codex/report_standard.md`, `docs/qa/testing_guidelines.md`
- Forrásterv: `tmp/plans/q56_q60_preprocessing_tasks/Q56C_SheetEdgePlacementCatalog_edge_corner_anchor_candidates.md`
- Kapcsolódó proof: `codex/reports/egyedi_solver/sgh_q55b_fix_one_part_sheet_edge.md`

## Existing code anchors

- `rust/vrs_solver/src/optimizer/sparrow/feature_candidate_generator.rs` —
  `sheet_edge_candidates(...)`, `push_sheet_edge_anchors(...)`, `finalize_seeds(...)`,
  `bounded_sheet_edge_repair(...)`, `verify_one_part_sheet_edge_placement(...)`,
  `generate_feature_candidate_seeds_for_sheet(...)`, `min_width_rotations(...)`.
- `rust/vrs_solver/src/optimizer/sparrow/sheet_skeleton.rs` — `SkeletonRole::Anchor`,
  `largest_edge_connected_free_area(...)`.
- `rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs` — `try_admit_critical(...)`,
  `sheet_freespace_score(...)`, role filtering Anchor/Interlock/BandInsert körül.
- `rust/vrs_solver/src/optimizer/sparrow/orientation_catalog.rs` — Q56A rotations (ha létezik).

## Valós repo anchorok

```text
rust/vrs_solver/src/optimizer/sparrow/feature_candidate_generator.rs
rust/vrs_solver/src/optimizer/sparrow/sheet_skeleton.rs
rust/vrs_solver/src/optimizer/sparrow/bpp_reduction.rs
rust/vrs_solver/src/optimizer/sparrow/model.rs
rust/vrs_solver/src/io.rs
rust/vrs_solver/tests/sparrow_sheet_edge_anchor.rs
scripts/render_sgh_q56_one_part_edge.py
```

Megjegyzés: a `SheetEdgePlacementCatalog` lehet új modul vagy a `feature_candidate_generator.rs`
bővítése; a konkrét hely a repo mintájához igazodjon. Q56C **nem** függhet az Q58A-tól a fordításhoz.

## Scope

- `SheetEdgePlacementCatalog` (vagy ekvivalens) producer kritikus Anchor candidate-ekhez egy adott
  sheeten: left/right/bottom/top × bottom/top/center variánsok. A corner variánsok first-class, a
  center fallback/diagnosztika.
- Minden candidate teljes metaadattal (lásd alább).
- Bekötés a production Anchor útba (`try_admit_critical` / feature-first critical admission).
- Vizuális + JSON artifact valós kritikus nagy partra.

## Out of scope

- Interlock/BandInsert role átírása (Q57B / Q59).
- SheetFeasibilityHints számítása (Q58A); ha létezik, opcionálisan felhasználható, de nincs hard függés.
- NFP, bbox collision shortcut.

## Required implementation

Minden candidate mezői:

```text
candidate_source = true_extreme_sheet_edge_anchor
part_id, target_sheet_edge, secondary_axis_policy,
selected_edge_index, selected_edge_angle_deg, target_axis_angle_deg, computed_rotation_deg,
spacing_offset_true_extrema_before_translation, margin_line_x_or_y,
translation_x, translation_y, final_extrema, margin_error, boundary_clear,
candidate_score, free_space_score, rejection_reason
```

Geometria: valós kontúr-feature / OrientationCatalog rotáció → forgatott **spacing-expanded** kontúr
extrema → margin-aware transláció → exact boundary validáció. Primary él-illesztés:

```text
left:   final_min_x = sheet_min_x + margin
right:  final_max_x = sheet_max_x - margin
bottom: final_min_y = sheet_min_y + margin
top:    final_max_y = sheet_max_y - margin
```

Másodlagos tengely: corner (min/max margin-illesztés) vagy center (margin-shrunk intervallum közép).
Ha a `SheetShape` már margin-shrunk, bizonyítsd és logold; ne illessz csendben a nyers sheet
határhoz.

Scoring exact boundary validáció után: `boundary_clear` + `collision_clear` hard gate,
`largest_edge_connected_free_area` placement után, corner/support/contact score (+),
center_island_penalty / fragmentation / narrow_dead_strip penalty (−). Ha Q58A megvan, opcionálisan
`next_critical_fit_potential` és `critical_capacity_preservation`.

Anchor bekötés: `SkeletonRole::Anchor` → SheetEdgePlacementCatalog candidate-ek, `target_feature_type
== sheet_edge / true_extreme_sheet_edge_anchor`, free-space-megőrző score szerinti rangsor. Fallback
generic density placementre csak az összes catalog candidate bukása után, **diagnosztikában látható**
fallback source-szal.

## Required diagnostics

```text
artifacts/benchmarks/sgh_q56c/sheet_edge_anchor_candidates.json
artifacts/benchmarks/sgh_q56c/sheet_edge_anchor_candidates.svg
```

Az SVG mutassa: sheet outline, margin vonalak, candidate label-ek, kiválasztott candidate kiemelve,
part kontúr, rotation szög, free-space score.

## Required tests / runners

Teszt: `rust/vrs_solver/tests/sparrow_sheet_edge_anchor_catalog.rs`. Ellenőrzések:

1. Valós LV8 kritikus part candidate-eket ad mind a négy sheet-élre.
2. Corner variánsok léteznek.
3. A center nem az egyetlen másodlagos-tengely placement.
4. Minden elfogadott candidate spacing-expanded true extrémát használ.
5. A kiválasztott candidate-nek van rögzített free-space score-ja.
6. A Q55B one-part proof továbbra is zöld.

Parancsok:

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml sheet_edge_anchor_catalog
cargo test --manifest-path rust/vrs_solver/Cargo.toml --test sparrow_one_part_sheet_edge
cargo test --manifest-path rust/vrs_solver/Cargo.toml --test sparrow_sheet_edge_anchor
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q56c_sheet_edge_placement_catalog_edge_corner_anchor_candidates.md
```

## Acceptance criteria

```text
- SheetEdgePlacementCatalog vagy ekvivalens létezik.
- Anchor candidate-ek edge+corner variánsokat tartalmaznak, nem csak edge+center.
- A candidate-választás a maradék hasznos / edge-connected szabad tér szerint pontozott.
- A production Anchor út ezt a katalógust használja, ha a skeleton Anchor aktív.
- A diagnosztika azonosítja a candidate source-ot, élt, secondary-axis policy-t és score-t.
- Vizuális artifact létezik.
```

## Hard restrictions

```text
- nem csak több 90/270 seed
- a center placement nem maradhat az egyetlen production Anchor candidate
- spacing nélküli bbox nem lehet final placement truth
- aktív margin mellett nem illeszt a nyers sheet határhoz
- a generált candidate-eket a production Anchor út ténylegesen használja
- continuous rotation nem cserélhető diszkrét foklistára
- nincs NFP, nincs part-id hack, nincs spacing/margin gyengítés
- cavity/hole logika nem kerülhet a Rust fősolverbe
- CDE/final exact validation marad az igazság
```

## Rollback

- Ha a katalógus-bekötés Anchor regressziót okoz, gate-eld (opt-in) és tartsd meg a Q55B/Q55F
  viselkedést defaultként, amíg a no-regression nem bizonyított.
- Ha a free-space scoring instabil, essen vissza `largest_edge_connected_free_area`-ra, logolva.

## Deliverables

```text
canvases/egyedi_solver/sgh_q56c_sheet_edge_placement_catalog_edge_corner_anchor_candidates.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q56c_sheet_edge_placement_catalog_edge_corner_anchor_candidates.yaml
codex/prompts/egyedi_solver/sgh_q56c_sheet_edge_placement_catalog_edge_corner_anchor_candidates/run.md
codex/codex_checklist/egyedi_solver/sgh_q56c_sheet_edge_placement_catalog_edge_corner_anchor_candidates.md
codex/reports/egyedi_solver/sgh_q56c_sheet_edge_placement_catalog_edge_corner_anchor_candidates.md
codex/reports/egyedi_solver/sgh_q56c_sheet_edge_placement_catalog_edge_corner_anchor_candidates.verify.log
```
