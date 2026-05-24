PASS

# Report — SGH-02 `sgh_02_vrs_separator_collision_tracker_v1`

## Status

PASS — `VrsCollisionTracker` és `VrsSeparator` implementálva, 8/8 separator teszt zöld, 114/114 total teszt zöld, scope safety teljesült, solver IO contract érintetlen.

## Meta

- **Task slug:** `sgh_02_vrs_separator_collision_tracker_v1`
- **Kapcsolódó canvas:** `canvases/egyedi_solver/sgh_02_vrs_separator_collision_tracker_v1.md`
- **Kapcsolódó goal YAML:** `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_02_vrs_separator_collision_tracker_v1.yaml`
- **Futás dátuma:** 2026-05-25
- **Fókusz terület:** Rust optimizer / separator

## Scope

### Cél

- SGH-01 dependency gate ellenőrzése.
- `VrsCollisionTracker` / collision-loss tracker V1 implementálása.
- `VrsSeparator` / WorkingLayout-alapú separator V1 implementálása.
- Unit tesztek és contract dokumentáció.

### Nem-cél

- Külső SparrowGH backend / vendor.
- Initializer, sheet elimination, moves integráció.
- IO contract / Python runner módosítás.
- Continuous rotation vagy solution pool.

---

## Dependency evidence

| Check | Result | Evidence |
|---|---|---|
| SGH-01 report létezik | PASS | `codex/reports/egyedi_solver/sgh_01_working_layout_infeasible_search_state_scaffold.md` |
| SGH-01 report első sora PASS | PASS | Első sor: `PASS` |
| SGH-01 report tartalmazza `SGH-02_STATUS: READY` | PASS | `grep "SGH-02_STATUS: READY"` → 1 találat |

---

## VRS current-state audit findings

1. **`WorkingLayout` létezik**, és csak `validate_and_commit()` után adható elfogadott output (`working.rs`). A commit gate meghívja `repair::find_violations()`.
2. **`repair::find_violations()`** commit gate előszűrő: visszaad `Vec<(usize, ViolationType)>` – `ViolationType::Overlap` és `ViolationType::BoundaryOrSheet`. Nem collision loss tracker.
3. **`PlacedBbox::overlaps()`** bool-alapú, EPS-tűréssel. A separator saját `bbox_overlap_area()` helper-t használ, amely a valós metszeti területet számítja.
4. **`generate_candidates_with_sheets()`** determinisztikus: sheet_index→y→x sorrendbe rendez, EPS-sel deduplikál. A separator ezt használja relocation jelöltekre.
5. **`bbox_from_placement()`** (`initializer.rs`) visszafejti a `PlacedBbox`-ot egy `Placement`-ből. **`placement_anchor_from_rect_min()`** (`item.rs`) az inverz – bbox-min-ből vissza placement ankort számít.
6. **`rect_within_boundary()`** (`boundary.rs`) a boundary policy kanonikus pontja – mind rektangulár, mind irreguláris sheet esetén.
7. **Solver IO contract nem változott.** `io.rs` érintetlen.

---

## Change summary

| Fájl | Változás |
|---|---|
| `rust/vrs_solver/src/optimizer/separator.rs` | ÚJ — `VrsCollisionTracker`, `VrsSeparator`, `VrsSeparatorConfig`, `VrsSeparatorDiagnostics`, `bbox_overlap_area()` helper, 8 unit teszt |
| `rust/vrs_solver/src/optimizer/mod.rs` | `pub mod separator;` export hozzáadva |
| `docs/egyedi_solver/sgh_02_vrs_separator_contract.md` | ÚJ — separator contract dokumentáció |
| `codex/codex_checklist/egyedi_solver/sgh_02_...md` | Checklistek [x]-re frissítve |
| `codex/reports/egyedi_solver/sgh_02_...md` | Ez a report |

---

## Implementation summary

### `bbox_overlap_area(a, b) -> f64`

Lokális helper a `separator.rs`-ben. Különböző sheeteken 0.0; azonos sheeten a metszeti területet adja vissza (dx×dy, min(0.0)). Nem módosítja `candidates.rs`-t.

### `VrsCollisionTracker`

```rust
pub struct VrsCollisionTracker {
    n: usize,
    pair_weights: HashMap<(usize, usize), f64>,  // (min(i,j), max(i,j)) → weight
    boundary_weights: Vec<f64>,
    bboxes: Vec<Option<PlacedBbox>>,
    boundary_valid: Vec<bool>,
}
```

- `build()`: `bbox_from_placement()` + `rect_within_boundary()` minden placementhez.
- `pair_loss(i, j)`: `bbox_overlap_area()` a két bbox között.
- `boundary_loss(i)`: `BOUNDARY_LOSS_PROXY = 1.0` ha invalid, egyébként 0.0.
- `total_loss()`: Σ pair_loss + Σ boundary_loss (O(n²), V1).
- `total_weighted_loss()`: súlyozott változat GLS weightekkel.
- `colliding_indices()`: determinisztikus lista (sort_unstable).
- `weighted_loss_for_item(idx)`: adott elem összes súlyozott veszteségének összege.
- `update_weights(decay, max)`: GLS Algorithm 8 — `w ← min(w + 1/(1+w×decay), max)` — csak rollback esetén hívódik.
- `update_placement(idx, …)`: egy elem bbox és boundary_valid frissítése.
- `restore_item(idx, bbox, valid)`: rollback után állapot visszaállítása (weight megmarad).

### `VrsSeparator`

```rust
pub struct VrsSeparatorConfig {
    pub max_strikes: usize,
    pub max_inner_iterations: usize,
    pub gls_weight_decay: f64,
    pub gls_weight_max: f64,
}
// Default: 20 strikes, 200 iterations, decay=0.01, max=100.0

pub struct VrsSeparatorDiagnostics {
    pub initial_loss: f64,
    pub best_loss: f64,
    pub iterations: usize,
    pub moves_attempted: usize,
    pub moves_accepted: usize,
    pub rollback_count: usize,
    pub converged: bool,
}
```

`run(layout, parts, sheets) -> (WorkingLayout, VrsSeparatorDiagnostics)`:
1. Tracker build + initial_loss számítás.
2. Ha 0.0 → azonnali visszatérés (`converged=true`).
3. Ciklus: legrosszabb kollider (weighted_loss_for_item max, tie→index) kiválasztása.
4. `generate_candidates_with_sheets()` az összes többi item bboxával.
5. Legjobb kandidáns keresése: `bbox_overlap_area` min az összes többi elemmel, boundary-invalid kihagyva.
6. Elfogadás ha `new_loss < current_loss`; best snapshot ha `new_loss < best_loss`.
7. Rollback + `update_weights()` + strike++ ha nem javít.
8. Terminálás: `max_inner_iterations` vagy `max_strikes` eléréskor.
9. `best_layout` visszaadása (a legjobb látott `WorkingLayout`).

Commit nem hívódik belsőleg. Nincs RNG. Teljes determinizmus.

---

## Tests

```bash
cargo test separator
```

```
test optimizer::separator::tests::tracker_valid_layout_total_loss_zero ... ok
test optimizer::separator::tests::tracker_overlap_gives_positive_pair_loss ... ok
test optimizer::separator::tests::tracker_boundary_violation_gives_positive_boundary_loss ... ok
test optimizer::separator::tests::separator_fixes_simple_overlap ... ok
test optimizer::separator::tests::separator_fixed_layout_passes_commit_gate ... ok
test optimizer::separator::tests::separator_preserves_item_count ... ok
test optimizer::separator::tests::separator_is_deterministic ... ok
test optimizer::separator::tests::separator_non_fixable_does_not_panic ... ok
test result: ok. 8 passed; 0 failed
```

Teljes teszt suite: **114 passed; 0 failed** (az előző 106-ról nőtt a 8 új teszttel).

---

## DoD → Evidence Matrix

| DoD pont | Státusz | Bizonyíték | Magyarázat |
|---|---|---|---|
| SGH-01 dependency gate zöld | PASS | Dependency evidence table | SGH-01 PASS, SGH-02_STATUS: READY |
| `optimizer/separator.rs` létrejött | PASS | `separator.rs` — új fájl | `VrsCollisionTracker` + `VrsSeparator` |
| `mod.rs` exportálja a separatort | PASS | `mod.rs` — `pub mod separator;` | 5. sor |
| `VrsCollisionTracker` implementálva | PASS | `separator.rs:31` — `pub struct VrsCollisionTracker` | Pair loss, boundary loss, weighted loss, colliding indices, update_weights |
| Pair loss bbox intersection area alapján | PASS | `separator.rs:14` — `fn bbox_overlap_area` | `dx×dy`, nem bool |
| Boundary loss pozitív invalid esetén | PASS | `separator.rs:73` — `boundary_loss()` | `BOUNDARY_LOSS_PROXY=1.0` |
| Weighted total loss + GLS update | PASS | `separator.rs:85` — `total_weighted_loss()`, `separator.rs:107` — `update_weights()` | Algorithm 8 |
| Colliding indices lekérhető | PASS | `separator.rs:97` — `colliding_indices()` | Sort + HashSet |
| `VrsSeparator` WorkingLayout I/O | PASS | `separator.rs:164` — `pub fn run(…)` | Bemenet+kimenet `WorkingLayout` |
| Separator nem épít LayoutState/SolverOutput-ot | PASS | `separator.rs` — nincs `LayoutState`/`SolverOutput` import | Scope-safe |
| Valós candidate/bbox/boundary helper | PASS | `separator.rs` imports — `generate_candidates_with_sheets`, `bbox_from_placement`, `rect_within_boundary` | Valós VRS funkciók |
| Snapshot/rollback minta implementálva | PASS | `separator.rs:240` — `best_layout = current.snapshot()` + `restore_item()` | |
| Determinisztikus (RNG nélkül) | PASS | teszt: `separator_is_deterministic` | Két futás byte-azonos output |
| Javítható fixture valid layouttá javul | PASS | teszt: `separator_fixes_simple_overlap` | initial_loss=900 → best_loss=0 |
| Javítható fixture commit gate zöld | PASS | teszt: `separator_fixed_layout_passes_commit_gate` | `validate_for_commit()` → Ok |
| Item count invariant megmarad | PASS | teszt: `separator_preserves_item_count` | placed+unplaced konstans |
| Nem javítható fixture nem panicel | PASS | teszt: `separator_non_fixable_does_not_panic` | converged=false és/vagy best_loss>0 |
| Scope safety teljesült | PASS | lásd Scope safety | Nincs tiltott módosítás |
| Solver IO contract nem változott | PASS | `io.rs` érintetlen | git diff üres |
| Focused Rust test zöld | PASS | `cargo test separator` → 8/8 ok | |
| Repo verify zöld | PASS | verify.sh → PASS, exit 0 | |

---

## Scope safety

- Nincs Sparrow/SparrowGH vendorolás.
- Nincs külső backend adapter.
- `io.rs` érintetlen.
- `adapter.rs` érintetlen.
- `initializer.rs` érintetlen.
- `sheet_elimination.rs` érintetlen.
- `moves.rs` érintetlen.
- Python runner / exact validator érintetlen.
- Continuous rotation nem lett bevezetve.
- Solution pool / perturbáció nincs.

---

## Verification

```bash
cargo test separator
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_02_vrs_separator_collision_tracker_v1.md
```

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-05-25T00:03:24+02:00 → 2026-05-25T00:06:39+02:00 (195s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/sgh_02_vrs_separator_collision_tracker_v1.verify.log`
- git: `main@aa52948`
- módosított fájlok (git status): 9

**git diff --stat**

```text
 rust/vrs_solver/src/optimizer/mod.rs | 1 +
 1 file changed, 1 insertion(+)
```

**git status --porcelain (preview)**

```text
 M rust/vrs_solver/src/optimizer/mod.rs
?? canvases/egyedi_solver/sgh_02_vrs_separator_collision_tracker_v1.md
?? codex/codex_checklist/egyedi_solver/sgh_02_vrs_separator_collision_tracker_v1.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_02_vrs_separator_collision_tracker_v1.yaml
?? codex/prompts/egyedi_solver/sgh_02_vrs_separator_collision_tracker_v1/
?? codex/reports/egyedi_solver/sgh_02_vrs_separator_collision_tracker_v1.md
?? codex/reports/egyedi_solver/sgh_02_vrs_separator_collision_tracker_v1.verify.log
?? docs/egyedi_solver/sgh_02_vrs_separator_contract.md
?? rust/vrs_solver/src/optimizer/separator.rs
```

<!-- AUTO_VERIFY_END -->

## Final marker

SGH-03_STATUS: READY
