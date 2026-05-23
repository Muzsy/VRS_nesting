PASS

## 1) Meta

- **Task slug:** `jagua_optimizer_t07_layout_state_and_candidate_model`
- **Task ID:** `JG-07`
- **Kapcsolódó canvas:** `canvases/egyedi_solver/jagua_optimizer_t07_layout_state_and_candidate_model.md`
- **Kapcsolódó goal YAML:** `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t07_layout_state_and_candidate_model.yaml`
- **Runner prompt:** `codex/prompts/egyedi_solver/jagua_optimizer_t07_layout_state_and_candidate_model/run.md`
- **Futás dátuma:** `2026-05-23`
- **Fókusz terület:** `LayoutState | PlacementTransform | CandidateMove skeleton | ObjectiveBreakdown skeleton | serde diagnostics`

---

## 2) Dependency ellenőrzés

| Ellenőrzés | Eredmény |
|---|---|
| JG-06 report létezik | IGAZ |
| JG-06 report első sora | `PASS` |
| JG-06 report tartalmazza `JG-07_STATUS: READY` | IGAZOLT |
| Goal YAML sanity | YAML_OK, `steps: 9`, nincs sandbox path |

---

## 3) Valós kód audit

### `rust/vrs_solver/src/optimizer/mod.rs` (JG-07 előtt)

- `SheetCursor { x, y, row_h }` — row/cursor baseline.
- `try_place_on_sheet(instance, sheet, cursor, sheet_index) -> Option<Placement>` — iterál az allowed_rotations_deg-en, megpróbálja elhelyezni az instance-t, visszaad `io::Placement`-et.
- Nincs `state.rs`, `moves.rs`, `score.rs` — ezek JG-07 scope.

### `rust/vrs_solver/src/io.rs`

- `Placement { instance_id, part_id, sheet_index, x, y, rotation_deg }` — v1 output contract.
- `Unplaced { instance_id, part_id, reason }` — v1 output contract.
- `SolverOutput { contract_version, status, placements, unplaced, metrics }`.
- Ezeket JG-07 nem töri — az új `LayoutState` belső optimizáló állapot, nem v1 output.

### `rust/vrs_solver/src/adapter.rs`

- `solve()` — row/cursor baseline; `per_sheet_cursor` + `try_place_on_sheet()` loop.
- JG-07 nem nyúl hozzá: az új state modell önálló és nem kötötte be az `adapter.rs`-be.

### `rust/vrs_solver/src/item.rs` (JG-06 után)

- `ItemGeometryStore`, `ItemGeometryRecord`, `RotationCacheEntry`, `Instance`, `expand_instances()` — mind megmarad.

### `rust/vrs_solver/Cargo.toml`

- `serde = { version = "1", features = ["derive"] }` — Serialize/Deserialize elérhető.
- `serde_json = "1"` — diagnosztikai JSON elérhető.

---

## 4) Optimizer module design döntés

**Döntés: a meglévő `optimizer/mod.rs` baseline (`SheetCursor`, `try_place_on_sheet`) változatlanul marad.**

Három új almodul kerül hozzá `pub mod` deklarációval:

```
optimizer/
  mod.rs     — meglévő SheetCursor + try_place_on_sheet + pub mod state/moves/score
  state.rs   — ÚJ: LayoutState, PlacedItem, UnplacedItem, PlacementTransform
  moves.rs   — ÚJ: CandidateMove enum skeleton
  score.rs   — ÚJ: ObjectiveBreakdown skeleton
```

Az `adapter.rs` nem lett módosítva — a v1 output contract nem sérül.

---

## 5) Állapotmodell

```
LayoutState
├── placed: Vec<PlacedItem>
│   └── PlacedItem { instance_id, part_id, sheet_index, transform: PlacementTransform }
│       └── PlacementTransform { x, y, rotation_deg }
├── unplaced: Vec<UnplacedItem>
│   └── UnplacedItem { instance_id, part_id, reason }
├── sheet_count: usize   ← expanded sheet slots száma (stable index alap)
└── seed: i64            ← SolverInput.seed, determinizmus nyomkövetéshez
```

- Placed/unplaced szeparáció: külön Vec, soha nem keverednek.
- Instance identity nem vész el: `instance_id` és `part_id` minden recordban szerepel.
- Sheet index stable: `PlacedItem.sheet_index` az expanded lista 0-alapú indexe, ugyanaz mint a v1 `Placement.sheet_index`.
- Serde: `#[derive(Serialize, Deserialize)]` minden új típuson — JSON diagnosztika elérhető.

---

## 6) CandidateMove skeleton

```rust
pub enum CandidateMove {
    Place    { instance_id, sheet_index, transform }
    Move     { instance_id, to_sheet_index, to_transform }
    Reinsert { instance_id, sheet_index, transform }
    Rotate   { instance_id, new_rotation_deg }
}
```

- Place: unplaced instance sheetre helyezése transzformmal.
- Move: már placed instance áthelyezése más sheetre/transzformra.
- Reinsert: placed vagy unplaced instance újrabehelyezése.
- Rotate: placed vagy candidate instance forgatása.
- Nincs collision check, candidate generation vagy score — ez JG-08+ scope.
- `#[derive(Serialize, Deserialize)]` — diagnosztikai JSON stabil.

---

## 7) ObjectiveBreakdown skeleton

```rust
pub struct ObjectiveBreakdown {
    placed_count: usize,
    unplaced_count: usize,
    sheet_count_used: usize,    // max(placed.sheet_index) + 1
    penalty_placeholder: f64,   // JG-10+ scope
}
```

- `from_layout_state(state)` — deterministikus számítás a state-ből.
- Nem score optimalizáló: `penalty_placeholder = 0.0` mindig.

---

## 8) Futtatási eredmények

### cargo build

```
Finished `dev` profile [unoptimized + debuginfo] target(s) in 1.73s
```

**PASS**

### cargo test (21/21)

```
test optimizer::moves::tests::candidate_move_all_variants_create ... ok
test optimizer::moves::tests::candidate_move_json_stable ... ok
test optimizer::moves::tests::candidate_move_place_creates ... ok
test optimizer::score::tests::objective_breakdown_empty_state ... ok
test optimizer::score::tests::objective_breakdown_from_state_counts ... ok
test optimizer::score::tests::objective_breakdown_sheet_count_used_max_index_plus_one ... ok
test optimizer::state::tests::deterministic_state_ordering ... ok
test optimizer::state::tests::layout_state_placed_unplaced_separation ... ok
test optimizer::state::tests::placed_item_retains_transform ... ok
test optimizer::state::tests::placement_transform_roundtrip ... ok
test optimizer::state::tests::state_json_serialization ... ok
test item::tests::item_geometry_store_all_four_rotations ... ok
test item::tests::item_geometry_store_area ... ok
test item::tests::item_geometry_store_deterministic ... ok
test item::tests::item_geometry_store_duplicate_rotation_deduped ... ok
test item::tests::item_geometry_store_rotation_cache_dims ... ok
test item::tests::item_geometry_store_unsupported_rotation_error ... ok
test item::tests::placement_anchor_from_rect_min_keeps_rotated_bbox_inside_target_rect ... ok
test item::tests::rotated_bbox_min_offset_matches_expected_quadrants ... ok
test sheet::tests::expand_sheets_stable_order_and_quantity ... ok
test sheet::tests::expand_sheets_zero_quantity_skipped ... ok

test result: ok. 21 passed; 0 failed
```

**PASS**

### python3 scripts/smoke_jagua_item_geometry_store.py (8/8)

```
=== RESULTS: 8 PASS, 0 FAIL ===
OVERALL: PASS
```

**PASS**

### python3 scripts/smoke_jagua_rectangular_sheet_provider.py (11/11)

```
=== RESULTS: 11 PASS, 0 FAIL ===
OVERALL: PASS
```

**PASS**

---

## 9) Contract summary

| Contract pont | Státusz |
|---|---|
| `LayoutState` létrejött, placed/unplaced szeparált | ✓ IGAZOLT (unit teszt: layout_state_placed_unplaced_separation) |
| `PlacementTransform` tartalmaz x/y/rotation_deg | ✓ IGAZOLT (unit teszt: placed_item_retains_transform) |
| Transform roundtrip JSON serialization | ✓ IGAZOLT (unit teszt: placement_transform_roundtrip) |
| `CandidateMove` place/move/reinsert/rotate alapok | ✓ IGAZOLT (unit teszt: candidate_move_all_variants_create) |
| `CandidateMove` JSON diagnosztika stabil | ✓ IGAZOLT (unit teszt: candidate_move_json_stable) |
| `ObjectiveBreakdown` placed/unplaced/sheet_count | ✓ IGAZOLT (unit teszt: objective_breakdown_from_state_counts) |
| State JSON serialization | ✓ IGAZOLT (unit teszt: state_json_serialization) |
| Deterministic state ordering | ✓ IGAZOLT (unit teszt: deterministic_state_ordering) |
| V1 output contract (`Placement`, `Unplaced`) nem módosult | ✓ IGAZ (io.rs nem érintett, adapter.rs nem érintett) |
| JG-06 smoke regresszió | ✓ IGAZOLT (8/8 PASS) |
| JG-05 smoke regresszió | ✓ IGAZOLT (11/11 PASS) |
| seed mező előkészítve | ✓ IGAZ (`LayoutState.seed: i64`) |

---

## 10) Módosított / létrehozott fájlok

| Fájl | Változás |
|---|---|
| `rust/vrs_solver/src/optimizer/mod.rs` | `pub mod moves; pub mod score; pub mod state;` hozzáadva |
| `rust/vrs_solver/src/optimizer/state.rs` | ÚJ — `PlacementTransform`, `PlacedItem`, `UnplacedItem`, `LayoutState`, 5 unit teszt |
| `rust/vrs_solver/src/optimizer/moves.rs` | ÚJ — `CandidateMove` enum skeleton (4 variant), 3 unit teszt |
| `rust/vrs_solver/src/optimizer/score.rs` | ÚJ — `ObjectiveBreakdown` skeleton, `from_layout_state()`, 3 unit teszt |
| `codex/codex_checklist/egyedi_solver/jagua_optimizer_t07_layout_state_and_candidate_model.md` | Frissítve |
| `canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md` | JG-07 szekció frissítve |

---

JG-08_STATUS: READY

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-05-23T17:38:03+02:00 → 2026-05-23T17:41:01+02:00 (178s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/jagua_optimizer_t07_layout_state_and_candidate_model.verify.log`
- git: `main@75a0a55`
- módosított fájlok (git status): 11

**git diff --stat**

```text
 .../jagua_optimizer_task_progress_checklist.md     | 32 +++++++++++-----------
 rust/vrs_solver/src/optimizer/mod.rs               |  4 +++
 2 files changed, 20 insertions(+), 16 deletions(-)
```

**git status --porcelain (preview)**

```text
 M canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md
 M rust/vrs_solver/src/optimizer/mod.rs
?? canvases/egyedi_solver/jagua_optimizer_t07_layout_state_and_candidate_model.md
?? codex/codex_checklist/egyedi_solver/jagua_optimizer_t07_layout_state_and_candidate_model.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t07_layout_state_and_candidate_model.yaml
?? codex/prompts/egyedi_solver/jagua_optimizer_t07_layout_state_and_candidate_model/
?? codex/reports/egyedi_solver/jagua_optimizer_t07_layout_state_and_candidate_model.md
?? codex/reports/egyedi_solver/jagua_optimizer_t07_layout_state_and_candidate_model.verify.log
?? rust/vrs_solver/src/optimizer/moves.rs
?? rust/vrs_solver/src/optimizer/score.rs
?? rust/vrs_solver/src/optimizer/state.rs
```

<!-- AUTO_VERIFY_END -->
