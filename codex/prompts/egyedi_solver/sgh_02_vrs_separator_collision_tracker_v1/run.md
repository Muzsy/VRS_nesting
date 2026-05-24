# Runner prompt — SGH-02 `sgh_02_vrs_separator_collision_tracker_v1`

## Feladat

A helyi `VRS_nesting` repo gyökerében dolgozz. Hajtsd végre az SGH-02 taskot:

```text
SGH-02 — VrsSeparator + VrsCollisionTracker V1
```

Ez belső Rust optimizer alapréteg task. A cél: a Sparrow/SparrowGH migráció következő elemeként létrehozni egy saját VRS separator réteget, amely `WorkingLayout`-on dolgozik, bbox-alapú collision/boundary loss-t számol, és determinisztikus relocation ciklussal megpróbálja feloldani az ütközéseket.

**Ne integráld még a separator-t a teljes futási pipeline-ba. Ne módosítsd az initializer, sheet_elimination vagy moves algoritmust. Ne építs külső SparrowGH backendet. Ne vendorolj külső kódot.**

---

## Kötelező dependency preflight

Ellenőrizd:

```text
codex/reports/egyedi_solver/sgh_01_working_layout_infeasible_search_state_scaffold.md
```

Feltételek:

- a report létezik;
- első sora `PASS` vagy `PASS_WITH_NOTES`;
- tartalmazza: `SGH-02_STATUS: READY`.

Ha bármelyik feltétel nem teljesül, állj meg:

```text
STATUS: BLOCKED
REASON: Missing or non-PASS dependency: SGH-01 WorkingLayout scaffold
```

Ilyenkor csak ezeket frissítsd:

```text
codex/reports/egyedi_solver/sgh_02_vrs_separator_collision_tracker_v1.md
codex/codex_checklist/egyedi_solver/sgh_02_vrs_separator_collision_tracker_v1.md
```

---

## Kötelező olvasmányok

Olvasd el és kövesd:

```text
AGENTS.md
docs/codex/overview.md
docs/codex/yaml_schema.md
docs/codex/report_standard.md
docs/qa/testing_guidelines.md
docs/egyedi_solver/sparrow_sparrowgh_code_audit.md
docs/egyedi_solver/sparrowgh_vrs_migration_plan.md
docs/egyedi_solver/sgh_01_working_layout_state_contract.md
canvases/egyedi_solver/sgh_02_vrs_separator_collision_tracker_v1.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_02_vrs_separator_collision_tracker_v1.yaml
codex/codex_checklist/egyedi_solver/sgh_02_vrs_separator_collision_tracker_v1.md
```

Az `AGENTS.md` outputs szabálya kötelező: csak a YAML step `outputs` listáiban szereplő fájlokat módosíthatod.

---

## Valós kód audit

A megvalósítás előtt nézd át:

```text
rust/vrs_solver/src/optimizer/working.rs
rust/vrs_solver/src/optimizer/repair.rs
rust/vrs_solver/src/optimizer/candidates.rs
rust/vrs_solver/src/optimizer/initializer.rs
rust/vrs_solver/src/optimizer/boundary.rs
rust/vrs_solver/src/optimizer/stopping.rs
rust/vrs_solver/src/optimizer/mod.rs
rust/vrs_solver/src/io.rs
rust/vrs_solver/src/item.rs
rust/vrs_solver/src/sheet.rs
```

A reportban külön igazold:

1. `WorkingLayout` létezik, és csak `validate_and_commit()` után adható elfogadott output.
2. `repair::find_violations()` commit gate előszűrő, de nem collision loss tracker.
3. `PlacedBbox::overlaps()` bool alapú; a separatornak saját overlap-area helper kell.
4. `generate_candidates_with_sheets()` determinisztikus candidate generátor.
5. `bbox_from_placement()` és `placement_anchor_from_rect_min()` használható relocationhoz.
6. `rect_within_boundary()` a boundary policy kanonikus pontja.
7. Solver IO contract nem változhat.

---

## Implementációs irány

Hozd létre:

```text
rust/vrs_solver/src/optimizer/separator.rs
```

és exportáld:

```text
rust/vrs_solver/src/optimizer/mod.rs
```

### 1. VrsCollisionTracker

Implementálj `VrsCollisionTracker` vagy azonos funkciójú típust.

Kötelező funkciók:

```text
- placement bboxok visszafejtése bbox_from_placement() segítségével;
- pair loss: bbox intersection area ugyanazon sheeten;
- boundary loss: pozitív proxy invalid sheet vagy rect_within_boundary false esetén;
- total_loss és total_weighted_loss;
- colliding/violating placement indexek listája;
- GLS-like update_weights();
- determinisztikus működés.
```

Javasolt helper:

```rust
fn bbox_overlap_area(a: &PlacedBbox, b: &PlacedBbox) -> f64
```

Ne módosítsd `candidates.rs`-t csak azért, hogy area helper legyen; SGH-02-ben elég lokális helper a `separator.rs`-ben.

### 2. VrsSeparator

Implementálj `VrsSeparator` vagy azonos funkciójú típust.

Kötelező viselkedés:

```text
- bemenet: WorkingLayout
- kimenet: WorkingLayout + diagnostics
- nem épít LayoutState-et vagy SolverOutputot;
- best snapshotot tart;
- loss-csökkentő relocation próbákat tesz;
- generate_candidates_with_sheets() + allowed rotations alapján keres;
- boundary-invalid candidate-eket kihagyhatja V1-ben;
- a végén a best found state-et adja vissza;
- commit továbbra is WorkingLayout.validate_and_commit().
```

Javasolt diagnosztika:

```rust
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

### 3. Stop/iteration policy

SGH-02-ben nem kell bekötni a meglévő `StoppingPolicy`-t, de a separator konfiguráció determinisztikus limiteket tartalmazzon:

```text
max_strikes
max_inner_iterations
gls_weight_decay
gls_weight_max
```

Ne legyen végtelen ciklus.

---

## Tilos

Ne csináld ebben a taskban:

```text
- initializer.rs LBF + separator fallback integráció
- sheet_elimination.rs separator integráció
- moves.rs transfer/swap execution
- MultiSheetManager átírás
- SolverOutput / io.rs módosítás
- Python runner vagy exact validator módosítás
- külső SparrowGH backend adapter
- vendor/submodule hozzáadás
- continuous rotation
- solution pool / perturbáció
```

---

## Kötelező unit tesztek

Adj teszteket a `separator.rs` modulban.

Minimum:

```text
1. valid layouton total_loss == 0;
2. overlapes layouton pair loss > 0;
3. boundary/sheet violation esetén boundary loss > 0;
4. egyszerű két-elem overlap fixture-t a separator valid layouttá javít;
5. javított fixture után WorkingLayout.validate_for_commit(parts, sheets) Ok;
6. item count invariant megmarad;
7. azonos input kétszer azonos outputot ad;
8. nem javítható fixture nem panicel és diagnostics.converged == false vagy best_loss > 0.
```

A tesztek valós `Part`, `Stock`, `SheetShape`, `Placement`, `WorkingLayout` és `find_violations` logikát használjanak.

---

## Dokumentáció

Hozd létre:

```text
docs/egyedi_solver/sgh_02_vrs_separator_contract.md
```

Tartalma:

```text
# SGH-02 VrsSeparator contract

## Purpose
## Relationship to WorkingLayout
## Collision loss model V1
## Boundary loss policy V1
## GLS-like weight update V1
## Separator loop
## Commit and rollback rules
## Scope exclusions
## Preparation for SGH-03 / SGH-04
```

---

## Report és checklist

Töltsd ki:

```text
codex/codex_checklist/egyedi_solver/sgh_02_vrs_separator_collision_tracker_v1.md
codex/reports/egyedi_solver/sgh_02_vrs_separator_collision_tracker_v1.md
```

A report első sora csak akkor lehet `PASS`, ha minden DoD teljesült és a verify zöld.

A report tartalmazzon DoD → Evidence Matrixot konkrét fájl/funkció bizonyítékokkal.

---

## Focused ellenőrzés

Futtasd és dokumentáld:

```bash
cargo test optimizer::separator optimizer::working
```

Ha a cargo parancs helyi környezet miatt más formában működik, futtasd az ekvivalens célzott Rust tesztet, és írd be a reportba a pontos parancsot.

---

## Kötelező repo gate

Futtasd:

```bash
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_02_vrs_separator_collision_tracker_v1.md
```

Ha zöld, a report végén szerepeljen:

```text
SGH-03_STATUS: READY
```

Ha fail, ne adj PASS státuszt. Dokumentáld a pontos hibát és a következő javítási lépést.
