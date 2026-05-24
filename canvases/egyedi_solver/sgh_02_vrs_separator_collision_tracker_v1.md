# SGH-02 — VrsSeparator + VrsCollisionTracker V1

## Kontextus

SGH-00 lezárta a Sparrow/SparrowGH kódauditot és migrációs tervet. A döntés:

```text
Do not use SparrowGH as external benchmark backend.
Use Sparrow/SparrowGH as audited algorithmic source.
Port or reimplement selected algorithms inside VRS jagua_optimizer.
```

SGH-01 bevezette a `WorkingLayout` scaffoldot, amely ideiglenesen tárolhat infeasible / colliding állapotot, de csak explicit `validate_and_commit()` kapun keresztül adhat elfogadott placementeket. Ez a SparrowGH-szerű separator előfeltétele.

SGH-02 célja a következő alapréteg: egy **belső, VRS-owned per-sheet/per-layout separator V1**, amely bbox-alapú collision loss és determinisztikus item-relocation ciklus alapján megpróbálja feloldani a `WorkingLayout` sértéseit.

Ez még nem integrációs task. SGH-02 ne írja át a teljes nesting futást. A separator API-t és unit teszteket kell megalapozni.

---

## Task cél

Implementálj egy minimális, determinisztikus VRS separator réteget:

```text
WorkingLayout  # lehet colliding/infeasible
    ↓
VrsCollisionTracker  # bbox overlap + boundary loss + GLS-like weights
    ↓
VrsSeparator::separate()
    ↓
WorkingLayout  # best found state; commit csak WorkingLayout.validate_and_commit()-tel
```

Kötelező új modul:

```text
rust/vrs_solver/src/optimizer/separator.rs
```

és export:

```text
rust/vrs_solver/src/optimizer/mod.rs
```

---

## Kötelező dependency gate

SGH-02 csak akkor indulhat, ha:

```text
codex/reports/egyedi_solver/sgh_01_working_layout_infeasible_search_state_scaffold.md
```

létezik, első sora `PASS` vagy `PASS_WITH_NOTES`, és tartalmazza:

```text
SGH-02_STATUS: READY
```

Ha nem teljesül, állj meg `BLOCKED` státusszal, és csak a report/checklist dependency evidence részét frissítsd.

---

## Kötelező repo anchorok

A helyi agent ellenőrizze, ne feltételezze:

```text
AGENTS.md
docs/codex/overview.md
docs/codex/yaml_schema.md
docs/codex/report_standard.md
docs/qa/testing_guidelines.md
docs/egyedi_solver/sparrow_sparrowgh_code_audit.md
docs/egyedi_solver/sparrowgh_vrs_migration_plan.md
docs/egyedi_solver/sgh_01_working_layout_state_contract.md
codex/reports/egyedi_solver/sgh_01_working_layout_infeasible_search_state_scaffold.md
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

---

## Kötelező kódaudit megállapítások

A reportban rögzítsd:

1. `WorkingLayout` létezik, és `validate_and_commit()` továbbra is a commit gate.
2. `repair::find_violations()` validációs előszűrő, de nem collision-loss tracker.
3. `PlacedBbox::overlaps()` bool-alapú; a separatornak saját overlap-area helperre van szüksége.
4. `generate_candidates_with_sheets()` meglévő, determinisztikus candidate forrás; SGH-02-ben újrahasználható.
5. `bbox_from_placement()` vissza tudja fejteni a placement bboxot az eredeti part méretekből.
6. `rect_within_boundary()` a kanonikus boundary policy, irregular sheetre is.
7. Solver IO contractot SGH-02-ben tilos módosítani.

---

## Tervezett API

A konkrét Rust API-t a valós kódhoz igazítsd, de az alábbi fogalmaknak létezniük kell.

### `VrsCollisionTracker`

Feladata:

- placementenként bboxot számolni;
- ugyanazon sheeten lévő bbox-overlap loss-t mérni;
- boundary/sheet violation loss-t mérni;
- weighted total loss-t számolni;
- visszaadni a colliding/violating placement indexeket;
- GLS-like weight update-et adni.

Javasolt struktúrák:

```rust
pub struct VrsCollisionEntry {
    pub loss: f64,
    pub weight: f64,
}

pub struct VrsCollisionTracker {
    pub pair: Vec<Vec<VrsCollisionEntry>>,
    pub boundary: Vec<VrsCollisionEntry>,
}
```

Nem kötelező pontosan ez a forma, de a funkciók nem maradhatnak el.

V1 loss policy:

```text
pair loss = bbox intersection area, ha ugyanazon sheeten overlap van, különben 0
boundary loss = pozitív érték, ha sheet_index invalid vagy rect_within_boundary false
```

Boundary loss V1 lehet konzervatív proxy:

```text
invalid sheet_index → bbox area vagy 1.0
rect outside rectangular sheet → outside-area proxy, ha egyszerűen számolható
irregular sheet outside → bbox area vagy 1.0 proxy
```

Fontos: SGH-02 célja nem a tökéletes geometriai loss, hanem a separator működési alapja. A végső commit továbbra is `find_violations()` + exact validator irány.

### `VrsSeparator`

Feladata:

- `WorkingLayout`-on dolgozni;
- ideiglenesen megtartani infeasible state-et;
- candidate relocation próbákkal csökkenteni a weighted collision losst;
- snapshot/rollback mintát használni;
- a legjobb megtalált state-et visszaadni;
- soha nem építeni `SolverOutput`-ot vagy `LayoutState`-et közvetlenül.

Javasolt API:

```rust
pub struct VrsSeparatorConfig {
    pub max_strikes: usize,
    pub max_inner_iterations: usize,
    pub gls_weight_decay: f64,
    pub gls_weight_max: f64,
}

pub struct VrsSeparatorDiagnostics {
    pub initial_loss: f64,
    pub best_loss: f64,
    pub iterations: usize,
    pub moves_attempted: usize,
    pub moves_accepted: usize,
    pub rollback_count: usize,
    pub converged: bool,
}

pub struct VrsSeparator<'a> {
    pub parts: &'a [Part],
    pub sheets: &'a [SheetShape],
    pub config: VrsSeparatorConfig,
}

impl<'a> VrsSeparator<'a> {
    pub fn separate(&self, working: WorkingLayout) -> (WorkingLayout, VrsSeparatorDiagnostics);
}
```

A pontos aláírás eltérhet, de az alábbi invariáns kötelező:

```text
separator bemenet: WorkingLayout
separator kimenet: WorkingLayout + diagnostics
accepted commit: csak WorkingLayout.validate_and_commit(parts, sheets)
```

---

## Separator V1 algoritmus

SGH-02 V1 legyen determinisztikus, RNG nélkül. A cél működő és tesztelhető alap, nem még teljes Sparrow-paritás.

Javasolt ciklus:

```text
1. Build tracker from WorkingLayout.
2. Save best snapshot and best_loss.
3. Amíg strike/no-improvement limit nem állítja meg:
   a. Ha total_loss == 0 → converged.
   b. Kérd le a colliding/violating placement indexeket.
   c. Minden érintett itemre determinisztikus sorrendben:
      - generálj candidate pontokat generate_candidates_with_sheets()-szel;
      - a moving itemet ideiglenesen hagyd ki az existing bbox listából;
      - próbáld az adott part allowed_rotations_deg rotációit;
      - számold a virtual weighted loss-t, ha oda kerülne;
      - válaszd a legjobb, loss-csökkentő pozíciót;
      - commitold a working layoutba, ha javít.
   d. Rebuild tracker.
   e. Ha javult best_loss → best snapshot frissül, strikes reset.
   f. Ha nem javult → strikes/no-improvement nő.
   g. update_weights() a GLS-like tracker logikával.
4. A végén térj vissza a best snapshotra.
```

SGH-02-ben megengedett egyszerűsítés:

- csak bbox alapú rectangular item loss;
- boundary-invalid candidate-eket lehet eleve kihagyni;
- multi-worker/parallel separator nem szükséges;
- full solution pool/perturbáció nem szükséges;
- sheet elimination integráció nem szükséges.

---

## Kötelező invariánsok

1. Separator nem lazíthatja a solver output contractot.
2. Separator nem commitolhat validálatlan layoutot.
3. `WorkingLayout` marad az egyetlen infeasible working state.
4. `LayoutState` és `SolverOutput` nem kaphat implicit `From<WorkingLayout>` konverziót.
5. `find_violations()` üres kell legyen minden sikeres commit tesztben.
6. Item count megmarad: `placements.len() + unplaced.len()` a separator előtt és után azonos.
7. Determinizmus: azonos input → azonos separator output.
8. Allowed rotation policy változatlan: csak a meglévő 0/90/180/270 logika használható.
9. Irregular/remnant boundary policy változatlan: `rect_within_boundary()` az egyetlen boundary check.

---

## Nem-cél

Ebben a taskban tilos:

- külső Sparrow/SparrowGH backend adapter;
- Sparrow/SparrowGH vendorolás;
- `initializer.rs` LBF+separator fallback integráció;
- `sheet_elimination.rs` separator integráció;
- `moves.rs` transfer/swap execution;
- solution pool / perturbáció;
- continuous rotation;
- IO schema vagy Python runner módosítás;
- exact validator lazítása;
- teljes benchmark suite átírása.

---

## Kötelező unit tesztek

Adj Rust unit teszteket a `separator.rs` modulhoz.

Minimum:

1. `VrsCollisionTracker` nulla loss-t ad valid, nem átfedő layouton.
2. `VrsCollisionTracker` pozitív pair loss-t ad két átfedő placementre.
3. `VrsCollisionTracker` pozitív boundary loss-t ad out-of-sheet placementre.
4. `VrsSeparator` egyszerű két-elem overlap fixture-en nullára tudja csökkenteni a violationt.
5. Separator után `WorkingLayout.validate_for_commit(parts, sheets)` sikeres a javítható fixture-en.
6. Separator item count invariánst tart.
7. Separator determinisztikus: azonos input kétszer azonos placement koordinátákat ad.
8. Nem javítható fixture esetén nem panicel, visszaad egy best state-et, és a diagnostics jelzi, hogy nem konvergált.

A tesztek használjanak valós:

```text
Part
Stock / SheetShape
Placement
WorkingLayout
repair::find_violations
```

struktúrákat. Ne mockold ki a commit gate-et.

---

## Kötelező dokumentáció

Hozd létre:

```text
docs/egyedi_solver/sgh_02_vrs_separator_contract.md
```

Tartalmazza:

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

## Acceptance gate

SGH-02 akkor PASS, ha:

- SGH-01 dependency gate zöld;
- `optimizer/separator.rs` létrejött;
- `VrsCollisionTracker` vagy ekvivalens tracker létezik;
- `VrsSeparator` vagy ekvivalens separator létezik;
- a separator `WorkingLayout` bemenet/kimenet köré épül;
- bbox overlap loss és boundary loss tesztelve van;
- javítható overlap fixture-en a separator valid layoutot ad;
- nem javítható fixture-en nem panicel és diagnosztikát ad;
- item count és determinisztika tesztelve van;
- nincs IO contract / Python runner / külső backend módosítás;
- focused Rust test lefut, például:

```bash
cargo test optimizer::separator optimizer::working
```

- standard repo gate lefut:

```bash
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_02_vrs_separator_collision_tracker_v1.md
```

Ha minden zöld, a report végén szerepeljen:

```text
SGH-03_STATUS: READY
```
