# SGH-Q04R — Phase orchestration wiring + infeasible pool correction

## Státusz

Corrective task. Az SGH-Q04 report PASS-t állított, de a valós kódaudit alapján az implementáció nem teljesíti a saját contractját.

## Miért kell Q04R?

Az SGH-Q04 után a következő kódszintű blokkolók látszanak:

1. `PhaseOptimizer::run()` nem hívja az új `ExplorationPhase` és `CompressionPhase` implementációkat.
   - `phase.rs` privát `run_exploration()` / `run_compression()` stubokon megy át.
   - Emiatt a phase orchestration foundation valójában nincs bekötve.

2. `InfeasibleSolutionPool::best()` hibás sorrendet ad.
   - A jelenlegi `BinaryHeap` max-heap comparator miatt a legnagyobb `raw_loss` kerül `best()`-be.
   - A test ezt tévesen el is fogadja.
   - Contract szerint loss-ascending pool kell: a legalacsonyabb loss a legjobb.

3. A time budget nem valós időt mér.
   - Jelenleg `elapsed = iteration as f64 * 0.01`.
   - Ez nem teljesíti a `time_limit_s` contractot.

4. `LargeItemSwapDisruption` contract részlegesen hamis.
   - `max_attempts` nincs ténylegesen kihasználva.
   - A helper contract szerint csak violation-free perturbation térhet vissza, de ezt jelenleg részben a hívó ellenőrzi.

5. `CompressionPhase` commit-score logikája gyanús.
   - Előbb egy kézzel módosított `new_placements` score-t számol, majd másik eredményt commitol `try_reinsert()` után.
   - A commit döntés score-ja a tényleges commit-jelöltre vonatkozzon.

6. `CompressionPhase` hardcoded `[0, 90, 180, 270]` listát használ.
   - SGH-Q04 nem RotationPolicy task, de nem szabad újabb hardcoded rotációs proxy-t erősíteni.
   - Legalább a jelenlegi `Part.allowed_rotations_deg` diszkrét lista legyen a forrás.

## Cél

Az SGH-Q04-ben létrehozott modulokból valóban működő, minimális, de valós phase orchestration foundation legyen:

```text
PhaseOptimizer::run()
  -> ExplorationPhase::run()
  -> CompressionPhase::run()
  -> validált, no-downgrade, determinisztikus PhaseResult
```

Ez továbbra sem teljes Sparrow parity, de a Q04 saját contractját ténylegesen teljesítenie kell.

## Production scope

Engedélyezett production fájlok:

```text
rust/vrs_solver/src/optimizer/phase.rs
rust/vrs_solver/src/optimizer/explore.rs
rust/vrs_solver/src/optimizer/compress.rs
rust/vrs_solver/src/optimizer/mod.rs      # csak ha szükséges
rust/vrs_solver/src/optimizer/moves.rs    # csak ha disruption helperhez tényleg kell
```

Tiltott scope:

```text
BPP phase loop / sheet elimination iteratív loop
continuous rotation / RotationPolicy teljes bevezetése
smooth LossModel / pole penetration
CollisionBackend / CDE backend
DXF/preflight
IO contract
Python runner
frontend/API
```

## Kötelező javítások

### 1. PhaseOptimizer valós bekötése

`PhaseOptimizer::run()` ne stub private methodokat hívjon, hanem:

```text
ExplorationPhase::new(config.clone()).run(...)
CompressionPhase::new(config.clone()).run(...)
```

Elvárás:

- exploration layout legyen a compression bemenete;
- final result a legjobb feasible incumbent legyen;
- `PhaseResult.layout`, `PhaseResult.score`, `PhaseResult.best_score`, `PhaseResult.unplaced` ugyanarra a final layout állapotra mutasson;
- ha nincs javulás, az input feasible incumbent megmaradjon;
- diagnostics ne hazudjon 0 iterációt, ha phase budget és phase futás megtörtént.

### 2. InfeasibleSolutionPool sorrend javítása

Contract:

```text
best() = legalacsonyabb raw_loss
capacity = a legalacsonyabb lossú N candidate maradjon bent
stable tie-break = raw_loss, score, iteration, placement_order
```

Elfogadható implementáció:

- egyszerű `Vec<InfeasibleCandidate>` + sort/truncate;
- vagy helyes min-heap / reversed comparator.

A lényeg: ne legyen olyan teszt, ami a highest loss-t nevezi best-nek.

### 3. Valós time budget

Exploration és compression használjon `std::time::Instant` alapú elapsed mérést.

Elvárás:

```text
max_iterations működik
time_limit_s működik
0.0 time_limit_s jelenthet no time limit vagy explicit immediate stop, de legyen dokumentált és tesztelt
```

A Q04 jelenlegi fake `iteration * 0.01` nem maradhat.

### 4. Disruption helper contract javítása

`LargeItemSwapDisruption::try_disrupt()`:

- használja a `max_attempts` értéket;
- próbáljon determinisztikusan több item-párt;
- csak olyan `Vec<Placement>`-et adjon vissza, amelyre `find_violations(...).is_empty()`;
- ha nincs valid perturbation, `None`.

### 5. Compression commit score javítása

Commit előtt a tényleges `try_result` placement vektorra kell score-t számolni.

Ne így:

```text
new_placements score alapján döntünk, majd try_result-et commitolunk
```

Hanem:

```text
try_result -> find_violations -> score(try_result) -> commit, ha jobb
```

### 6. Hardcoded rotációs lista megszüntetése Q04 scope-on belül

Ez nem teljes RotationPolicy task, de a compression ne használjon új `[0,90,180,270]` konstans világot.

Elvárás:

```text
part.allowed_rotations_deg legyen a jelenlegi discrete source of truth
```

Ha a part nem található, skip + diagnostics/report.

## Kötelező tesztek

Adj vagy javíts célzott Rust teszteket úgy, hogy a jelenlegi SGH-Q04 kód legalább részben elbukna rajtuk:

1. `PhaseOptimizer` tényleg meghívja a phase rétegeket.
   - Diagnostics / iterations / behavior bizonyítsa, hogy nem stub.

2. `InfeasibleSolutionPool::best()` a legalacsonyabb loss-t adja.
   - Példa: loss `5.0, 1.0, 3.0` esetén `best.raw_loss == 1.0`.

3. Capacity retention.
   - Capacity 3, loss `0,1,2,3,4` után bent a három legjobb maradjon.

4. Same-seed determinism.
   - Azonos input + config + seed → azonos output.

5. `PhaseResult` konzisztencia.
   - `result.unplaced == result.layout.unplaced`.
   - `result.score` a `result.layout` score-ja.

6. Disruption no-violation contract.
   - Ha `try_disrupt()` `Some`, akkor `find_violations` üres.

7. Compression commit score consistency.
   - Commitolt layout score-ja legyen az, amivel a döntés történt.

8. Compression allowed rotations source.
   - Part `allowed_rotations_deg` listán kívüli rotációt ne próbáljon/commitoljon.

## Dokumentáció/report

Hozz létre új Q04R reportot:

```text
codex/reports/egyedi_solver/sgh_q04r_phase_orchestration_wiring_and_pool_fix.md
codex/reports/egyedi_solver/sgh_q04r_phase_orchestration_wiring_and_pool_fix.verify.log
codex/codex_checklist/egyedi_solver/sgh_q04r_phase_orchestration_wiring_and_pool_fix.md
docs/egyedi_solver/sgh_q04r_phase_orchestration_correction_notes.md
```

A report első sora csak akkor lehet `PASS`, ha:

- minden fenti blocker javítva van;
- célzott Rust tesztek zöldek;
- `cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib` zöld;
- standard verify zöld;
- a report konkrét fájl/függvény evidenciát tartalmaz.

PASS esetén a report végén szerepelhet:

```text
SGH-Q05_STATUS: READY
```

Ha bármi nem teljesül:

```text
első sor: REVISE vagy BLOCKED
nincs SGH-Q05_STATUS: READY marker
```
