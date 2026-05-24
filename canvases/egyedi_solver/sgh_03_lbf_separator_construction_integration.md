# SGH-03 — LBF + separator fallback construction integration

## Kontextus

SGH-00 lezárta a Sparrow/SparrowGH kódauditot és a VRS migrációs tervet. A döntés továbbra is:

```text
Do not use SparrowGH as external benchmark backend.
Use Sparrow/SparrowGH as audited algorithmic source.
Port or reimplement selected algorithms inside VRS jagua_optimizer.
```

SGH-01 bevezette a `WorkingLayout`-ot, amely ideiglenes, akár ütköző/infeasible keresési állapotot tarthat, de csak `validate_and_commit()` kapun keresztül adhat elfogadott outputot.

SGH-02 bevezette a belső `VrsCollisionTracker` + `VrsSeparator` V1 réteget. A separator `WorkingLayout`-on dolgozik, bbox overlap area + boundary loss alapján veszteséget számol, GLS-like súlyokat frissít, és determinisztikus relocation ciklussal a legjobb megtalált `WorkingLayout`-ot adja vissza.

SGH-03 célja az első **valódi konstrukciós integráció**: az initial construction ne csak első valid candidate-et fogadjon el, hanem SparrowGH `BpLbfBuilder` mintára LBF-scored clear placementet használjon, és ha ez nem elég, kontrollált separator fallbacket próbáljon.

Ez még **nem** sheet elimination, move operator, solution pool vagy perturbáció task.

---

## Task cél

Alakítsd át a jelenlegi `build_initial_layout()` initial construction logikát úgy, hogy:

```text
FFD / largest-first item order
    ↓
LBF-scored collision-free candidate selection
    ↓
ha nincs clear candidate: separator fallback WorkingLayout-on
    ↓
csak validate_for_commit / validate_and_commit után elfogadás
    ↓
ha ez sem sikerül: unplaced NO_CANDIDATE
```

A public IO contract és a `build_initial_layout()` külső visszatérési formája lehetőleg maradjon kompatibilis:

```rust
pub fn build_initial_layout(
    instances: &[Instance],
    parts: &[Part],
    sheets: &[SheetShape],
) -> (Vec<Placement>, Vec<Unplaced>, ConstructionDiagnostics)
```

Ha ettől eltérés kell, csak erős indokkal és explicit reportban dokumentálva. Alapesetben **ne változtasd meg**.

---

## Kötelező dependency gate

SGH-03 csak akkor indulhat, ha:

```text
codex/reports/egyedi_solver/sgh_02_vrs_separator_collision_tracker_v1.md
```

létezik, első sora `PASS` vagy `PASS_WITH_NOTES`, és tartalmazza:

```text
SGH-03_STATUS: READY
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
docs/egyedi_solver/sgh_02_vrs_separator_contract.md
codex/reports/egyedi_solver/sgh_02_vrs_separator_collision_tracker_v1.md
rust/vrs_solver/src/optimizer/initializer.rs
rust/vrs_solver/src/optimizer/candidates.rs
rust/vrs_solver/src/optimizer/separator.rs
rust/vrs_solver/src/optimizer/working.rs
rust/vrs_solver/src/optimizer/repair.rs
rust/vrs_solver/src/optimizer/boundary.rs
rust/vrs_solver/src/optimizer/score.rs
rust/vrs_solver/src/optimizer/state.rs
rust/vrs_solver/src/io.rs
rust/vrs_solver/src/item.rs
rust/vrs_solver/src/sheet.rs
```

---

## Kötelező kódaudit megállapítások

A reportban rögzítsd legalább ezeket:

1. `build_initial_layout()` jelenleg FFD/largest-first sorrendet használ, de a candidate választás alapvetően első valid candidate jellegű.
2. `generate_candidates_with_sheets()` determinisztikus, sheet→y→x sorrendű candidate forrás, és már irregular candidate forrásokat is ad.
3. `ConstructionDiagnostics` már tartalmaz candidate és irregular candidate számlálókat, de nincs LBF scoring / separator fallback diagnosztika.
4. `VrsSeparator::run()` már elérhető, `WorkingLayout` bemenet/kimenettel dolgozik, és nem commitol belsőleg.
5. `WorkingLayout::validate_for_commit()` / `validate_and_commit()` a kötelező elfogadási kapu.
6. `repair::find_violations()` a commit gate előszűrő, és nem váltható ki.
7. Solver IO contractot, Python exact validatort, `io.rs`-t és `adapter.rs`-t SGH-03-ban tilos módosítani.

---

## Tervezett implementáció

### 1. ConstructionDiagnostics bővítés

Bővítsd `ConstructionDiagnostics`-ot olyan mezőkkel, amelyekből látszik, mit csinált az új construction:

```rust
pub lbf_candidates_scored: usize,
pub lbf_clear_accepts: usize,
pub separator_fallback_attempts: usize,
pub separator_fallback_successes: usize,
pub separator_fallback_failures: usize,
pub separator_fallback_rejected_by_commit_gate: usize,
```

A pontos nevek eltérhetnek, de a reportban és tesztekben legyen egyértelmű, hogy mérhető:

```text
hány LBF candidate-et score-oltunk
hány clear placement lett LBF alapján elfogadva
hány separator fallback indult
hány fallback vezetett commitolható layoutig
hány fallback bukott el
```

A `summary()` tartalmazza az új mezőket.

### 2. LBF-scored clear candidate selection

A jelenlegi első-valid candidate helyett legyen explicit LBF scoring.

Elvárt V1 scoring:

```text
primary: már használt sheet előnyben az üres/unused sheet előtt, ha van használt sheet
secondary: kisebb y jobb
tertiary: kisebb x jobb
quaternary: kisebb sheet_index jobb
tie: rotation order / instance_id determinisztikus
```

Megjegyzés: a sheet-count fontosabb, mint az, hogy egy új sheet origója lokálisan „szebb” pont legyen. Emiatt V1-ben elfogadható, hogy használt sheet valid candidate-je előnyt kapjon egy unused sheet origójával szemben.

Kötelező:

- használja a valós `generate_candidates_with_sheets()`-t;
- használja a valós `rect_within_boundary()`-t;
- használja a valós `dims_for_rotation()` és `placement_anchor_from_rect_min()` helperöket;
- collision-free jelölt csak akkor clear, ha nem overlapel az aktuális `placed_bboxes`-szal;
- a selection determinisztikus legyen.

### 3. Separator fallback constructionben

Ha egy instance-hez nincs collision-free LBF candidate, próbálj separator fallbacket.

V1 elvárás:

1. Hozz létre egy ideiglenes `WorkingLayout`-ot az eddig elhelyezett itemekből + az aktuális item seed placementjéből.
2. A seed placement legyen determinisztikus:
   - preferáld a legnagyobb szabad becsült area-val rendelkező már használt sheetet;
   - ha nincs használt sheet, használd a legalacsonyabb indexű sheetet;
   - bbox-min seed lehet sheet origin `(0,0)` vagy a legjobb LBF seed candidate, ha a valós kód ehhez jobban illeszkedik;
   - csak olyan rotationt használj, amely `normalize_allowed_rotations()` szerint támogatott és a sheet boundary V1 ellenőrzésen átmegy, ha ilyen található.
3. Futtasd `VrsSeparator::run()`-t.
4. Csak akkor fogadd el a fallback eredményét, ha:
   - `diag.best_loss == 0.0` vagy `diag.converged == true`, **és**
   - `WorkingLayout::validate_for_commit(parts, sheets)` sikeres.
5. Siker esetén a teljes `placements` listát a separator által visszaadott commitolható állapotra cserélheted, majd építsd újra a `placed_bboxes` cache-t.
6. Sikertelenség esetén rollback: az előző placements/unplaced/placed_bboxes állapot maradjon érintetlen, az aktuális item pedig `NO_CANDIDATE` vagy pontosabb okkal `unplaced` legyen.

Fontos: SGH-03-ban a separator fallback **nem adhat ki invalid outputot**. Nincs „best partial accepted” ebben a taskban.

### 4. Bbox cache rebuild helper

Mivel a separator fallback mozgathat korábbi placementeket is, kell egy helper vagy lokális logika, amely a commitolt placement listából újraépíti a `placed_bboxes` cache-t.

Elvárás:

```text
rebuild_placed_bboxes(placements, parts) -> Vec<PlacedBbox>
```

vagy ekvivalens privát helper.

Ha valamely placementhez nem lehet bboxot visszafejteni, a fallback eredményt ne fogadd el PASS-ként; dokumentáld a reportban.

---

## Tilos ebben a taskban

Ne csináld:

```text
- sheet_elimination.rs módosítás
- moves.rs transfer/swap execution implementáció
- multisheet.rs átírás
- score.rs objective modell átírás
- SolverOutput / io.rs módosítás
- adapter.rs módosítás
- Python runner vagy exact validator módosítás
- külső SparrowGH backend adapter
- Sparrow/SparrowGH vendor/submodule hozzáadás
- continuous rotation
- solution pool / perturbáció
- nagy benchmark suite vagy LV8 futtatási kampány
```

---

## Kötelező tesztek

Adj vagy frissíts Rust unit teszteket, lehetőleg `initializer.rs`-ben.

Minimum:

```text
1. meglévő initializer tesztek továbbra is zöldek;
2. LBF scorer használt sheetet preferál unused sheet előtt, ha valid candidate létezik;
3. build_initial_layout determinisztikus: két azonos futás azonos placements/unplaced/diagnostics releváns mezők;
4. placed + unplaced == expanded instances továbbra is igaz;
5. separator fallback helper sikeres, ha egy kényszerített colliding seedből a VrsSeparator commitolható layoutot tud csinálni;
6. separator fallback failure esetén rollback történik: korábbi placementek száma és pozíciói nem sérülnek;
7. successful construction output `find_violations()` szerint valid;
8. diagnostics summary tartalmazza az új LBF/separator mezőket.
```

Ha a teljes `build_initial_layout()` természetes fixture-jein a fallback ritkán aktiválódik, tesztelheted a fallbacket privát helperen keresztül ugyanazon modul unit tesztjeiben. De a végső public construction outputnak továbbra is validnak kell lennie.

---

## Dokumentáció

Hozd létre:

```text
docs/egyedi_solver/sgh_03_lbf_separator_construction_contract.md
```

Kötelező szekciók:

```text
# SGH-03 LBF + separator construction contract

## Purpose
## Current initializer gap
## LBF candidate scoring V1
## Separator fallback V1
## Commit/rollback rules
## Diagnostics
## Scope exclusions
## Preparation for SGH-04
```

A doksi egyértelműen mondja ki:

```text
SGH-03 accepted output must remain violation-free.
Separator fallback may use infeasible WorkingLayout internally, but never commits it unless validate_for_commit passes.
```

---

## Definition of Done

SGH-03 csak akkor PASS, ha:

- dependency gate zöld;
- `initializer.rs` LBF-scored candidate selectiont használ;
- separator fallback be van kötve construction szinten;
- fallback csak commit-gate zöld eredményt fogad el;
- fallback failure rollback-safe;
- `ConstructionDiagnostics` bővült és summary frissült;
- a kötelező Rust tesztek zöldek;
- `io.rs`, `adapter.rs`, `sheet_elimination.rs`, `moves.rs`, Python runner és exact validator érintetlen;
- `docs/egyedi_solver/sgh_03_lbf_separator_construction_contract.md` elkészült;
- report DoD → Evidence Matrix konkrét fájl/funkció bizonyítékokat tartalmaz;
- `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_03_lbf_separator_construction_integration.md` zöld;
- zöld esetben a report végén szerepel:

```text
SGH-04_STATUS: READY
```
