# SGH-01 — WorkingLayout / infeasible search state scaffold

## Kontextus

Az SGH-00 audit és migrációs terv lezárult `PASS` státusszal. A döntés:

```text
Do not use SparrowGH as external benchmark backend.
Use Sparrow/SparrowGH as audited algorithmic source.
Port or reimplement selected algorithms inside VRS jagua_optimizer.
```

A következő migrációs lépés a Sparrow/SparrowGH separator-alapú keresés előfeltétele: a VRS optimizerben legyen külön **working / infeasible** állapot, amely ideiglenesen tárolhat ütköző vagy boundary-sértő köztes layoutot, de ilyen állapot soha nem kerülhet elfogadott solver outputba.

## Task cél

Implementálj egy minimális, típus-szinten elkülönített `WorkingLayout` scaffoldot a VRS optimizerben.

A cél nem még a separator, hanem az állapotmodell és commit gate megalapozása:

```text
valid LayoutState / solver output
        ↑
validate_and_commit()
        ↑
WorkingLayout  # ideiglenesen infeasible/colliding lehet
```

## Kötelező döntés

A `WorkingLayout` legyen külön típus. Ne lazítsd fel a meglévő `LayoutState` vagy solver output contract validitási elvét.

Elfogadott megvalósítás:

```text
rust/vrs_solver/src/optimizer/working.rs
rust/vrs_solver/src/optimizer/mod.rs
```

vagy ha a helyi kód alapján indokoltabb:

```text
rust/vrs_solver/src/optimizer/state.rs
```

A preferált út az új `optimizer/working.rs`, mert elválasztja a SparrowGH-szerű keresési munkaterületet a meglévő v1 állapotmodelltől.

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
codex/reports/egyedi_solver/sgh_00_sparrow_sparrowgh_code_audit_and_vrs_migration_plan.md
rust/vrs_solver/src/optimizer/state.rs
rust/vrs_solver/src/optimizer/repair.rs
rust/vrs_solver/src/optimizer/candidates.rs
rust/vrs_solver/src/optimizer/initializer.rs
rust/vrs_solver/src/optimizer/mod.rs
rust/vrs_solver/src/io.rs
rust/vrs_solver/src/item.rs
rust/vrs_solver/src/sheet.rs
```

## Kötelező dependency gate

SGH-01 csak akkor indulhat, ha:

```text
codex/reports/egyedi_solver/sgh_00_sparrow_sparrowgh_code_audit_and_vrs_migration_plan.md
```

létezik, első sora `PASS` vagy `PASS_WITH_NOTES`, és tartalmazza:

```text
SGH-01_STATUS: READY
```

Ha nem teljesül, állj meg `BLOCKED` státusszal, és csak a report/checklist dependency evidence részét frissítsd.

## Tervezett API / viselkedés

A konkrét Rust API-t a valós kódhoz igazítsd, de az alábbi koncepciót kell megvalósítani:

```rust
pub struct WorkingLayout {
    pub placements: Vec<Placement>,
    pub unplaced: Vec<Unplaced>,
    pub sheet_count: usize,
    pub seed: i64,
}
```

A `WorkingLayout`:

- tárolhat olyan `placements` listát, amelyben vannak overlap vagy boundary sértések;
- klónozható snapshot/rollback célra;
- nem lehet implicit módon elfogadott layouttá alakítani;
- csak validációs commit kapun keresztül adhat vissza elfogadott placementeket.

Kötelező commit gate:

```rust
validate_for_commit(...)
validate_and_commit(...)
```

A commit gate használja a meglévő valós VRS ellenőrzést:

```text
optimizer::repair::find_violations(...)
```

és csak akkor adhat vissza elfogadott `(Vec<Placement>, Vec<Unplaced>)` eredményt, ha `find_violations()` üres.

## Kötelező invariánsok

1. `WorkingLayout` lehet infeasible.
2. Elfogadott output nem lehet infeasible.
3. `WorkingLayout` → accepted placements csak explicit `validate_and_commit()` útvonalon történhet.
4. Nincs `From<WorkingLayout> for LayoutState` vagy hasonló validáció nélküli implicit konverzió.
5. Snapshot/rollback determinisztikus: clone/restore után ugyanazok az adatok maradnak.
6. A solver JSON output schema nem változhat.
7. `find_violations()` továbbra is a végső commit gate elsődleges Rust oldali előszűrője.
8. Python exact validator követelménye nem lazulhat.

## Nem-cél

Ebben a taskban tilos:

- SparrowGH/Sparrow kód vendorolása;
- külső SparrowGH backend vagy CLI adapter építése;
- separator / GLS collision tracker teljes implementációja;
- `repair.rs` átírása separatorrá;
- `sheet_elimination.rs` algoritmusának átírása;
- `initializer.rs` LBF fallback bevezetése;
- IO contract vagy Python runner módosítása;
- continuous rotation bevezetése.

## Kötelező tesztek

Adj Rust unit teszteket a working layout modulhoz.

Minimum tesztek:

1. `WorkingLayout` képes két egymást átfedő placementet eltárolni anélkül, hogy commitolná őket.
2. `validate_and_commit()` overlap esetén hibát ad.
3. `validate_and_commit()` boundary/sheet violation esetén hibát ad.
4. Valid layout esetén `validate_and_commit()` sikeres és az elemek száma megmarad.
5. Snapshot/clone/restore determinisztikus.
6. A hiba/diagnosztika külön számolja az overlap és boundary jellegű violationöket, a `ViolationType` alapján.

## Kötelező dokumentáció

Hozz létre rövid contract doksit:

```text
docs/egyedi_solver/sgh_01_working_layout_state_contract.md
```

Tartalmazza:

- mi a `WorkingLayout` szerepe;
- miben különbözik a `LayoutState` / solver output állapottól;
- milyen a commit gate;
- mik a tiltott implicit konverziók;
- hogyan készíti elő az SGH-02 `VrsSeparator` taskot.

## Acceptance gate

SGH-01 akkor PASS, ha:

- SGH-00 dependency gate zöld;
- `WorkingLayout` külön típusként létezik;
- commit gate `find_violations()`-re épül;
- invalid working layout nem commitolható;
- valid working layout commitolható;
- Rust unit tesztek lefedik a fenti eseteket;
- nincs solver IO contract módosítás;
- nincs külső vendor/backend;
- standard repo gate lefut:

```bash
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_01_working_layout_infeasible_search_state_scaffold.md
```

## Következő task

Ha SGH-01 PASS:

```text
SGH-02_STATUS: READY
```

Következő implementációs cél: `VrsSeparator` + `VrsCollisionTracker` V1, bbox alapú GLS collision loss-szal és rollbackkel.
