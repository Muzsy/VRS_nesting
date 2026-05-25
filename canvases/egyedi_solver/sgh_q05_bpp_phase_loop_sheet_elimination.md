# SGH-Q05 — BPP phase loop / iterative sheet elimination

## Státusz

Implementation task. Csak SGH-Q04R PASS után futtatható.

## Miért kell?

SGH-Q04/Q04R létrehozta a valós `ExplorationPhase` + `CompressionPhase` orchestration alapot, de a fixed-sheet / BPP jellegű sheet-count minimalizálás még nincs fázisszinten bekötve.

A jelenlegi `SheetEliminationEngine` egy passzt tud:

```text
highest used sheet -> displaced items -> lower-index sheets -> commit vagy rollback
```

SGH-Q05 célja ebből egy iteratív, budgetelt, rollback-safe BPP phase loopot építeni:

```text
incumbent layout
  -> try eliminate one sheet
  -> if valid and sheet_count_used decreases: commit
  -> repeat until no more improvement / budget exhausted
```

Ez a Sparrow/coroush BPP exploration irány VRS-natív, minimalista Phase 1 adaptációja.

## Source feature

Referencia irány:

```text
coroush/sparrow bp_explore.rs
iterative bin/sheet elimination attempt
separator-backed acceptance
rollback on failure
```

Nem külső backendként kell futtatni. A cél a VRS-ben meglévő `SheetEliminationEngine`, `WorkingLayout`, `PhaseOptimizer`, `find_violations`, `ScoreModel` rétegek közé illesztett saját moduláris loop.

## Scope

Engedélyezett production fájlok:

```text
rust/vrs_solver/src/optimizer/bpp_phase.rs      # új modul
rust/vrs_solver/src/optimizer/mod.rs            # új modul export
rust/vrs_solver/src/optimizer/phase.rs          # PhaseConfig + PhaseOptimizer bekötés
rust/vrs_solver/src/optimizer/sheet_elimination.rs # csak ha szükséges kisebb API/diag bővítés
```

Dokumentáció/report:

```text
docs/egyedi_solver/sgh_q05_bpp_phase_loop_contract.md
codex/codex_checklist/egyedi_solver/sgh_q05_bpp_phase_loop_sheet_elimination.md
codex/reports/egyedi_solver/sgh_q05_bpp_phase_loop_sheet_elimination.md
codex/reports/egyedi_solver/sgh_q05_bpp_phase_loop_sheet_elimination.verify.log
```

Tiltott scope:

```text
continuous rotation / RotationPolicy teljes bevezetése
smooth LossModel / pole penetration
CollisionBackend / CDE backend
DXF/preflight
IO contract
Python runner
frontend/API
új external benchmark backend
```

## Elvárt architektúra

### 1. Új BPP phase modul

Hozz létre új modult:

```text
rust/vrs_solver/src/optimizer/bpp_phase.rs
```

Javasolt public API:

```rust
pub struct BppPhase {
    config: PhaseConfig,
    score_model: ScoreModel,
}

pub struct BppPhaseDiagnostics {
    pub attempts: usize,
    pub successful_eliminations: usize,
    pub failed_eliminations: usize,
    pub rollback_count: usize,
    pub sheet_count_used_before: usize,
    pub sheet_count_used_after: usize,
    pub best_score: f64,
    pub initial_score: f64,
    pub stop_reason: PhaseStopReason,
    pub per_attempt: Vec<SheetEliminationDiagnostics>,
}

impl BppPhase {
    pub fn new(config: PhaseConfig) -> Self;
    pub fn run(&self, layout: WorkingLayout, parts: &[Part], sheets: &[SheetShape]) -> (WorkingLayout, BppPhaseDiagnostics);
}
```

A pontos név igazodhat a repo mintáihoz, de legyen külön modul és külön diagnostics.

### 2. PhaseConfig bővítés

Bővítsd a `PhaseConfig`-ot BPP budgettel:

```rust
pub bpp_budget: PhaseBudget,
pub bpp_max_eliminations: usize,
```

Default javaslat:

```text
bpp_budget = PhaseBudget::new(16, 30.0)
bpp_max_eliminations = 16
```

A budget legyen reprodukálható és determinisztikus. A time limit `Instant` alapú lehet, de a tesztekben használj kis max_iteration limitet, ne wall-clock érzékeny tesztet.

### 3. PhaseOptimizer bekötés

A `PhaseOptimizer::run()` Q05 után:

```text
initial score
  -> ExplorationPhase::run()
  -> CompressionPhase::run()
  -> BppPhase::run()
  -> final PhaseResult
```

Elfogadható alternatíva, ha indokolt:

```text
exploration -> compression -> bpp -> compression
```

De ne legyen rekurzív `PhaseOptimizer` hívás a BPP phase-ből.

A final `PhaseResult` legyen konzisztens:

```text
result.layout == final committed layout
result.score == score(final layout)
result.best_score == score(final layout) vagy annál nem jobb fiktív érték nélkül
result.unplaced == result.layout.unplaced
find_violations(result.layout.placements) == []
sheet_count_used(final) <= sheet_count_used(input)
```

Fontos: Q04R-ben volt olyan kockázat, hogy `best_score` más állapotra vonatkozik, mint a final layout. Q05-ben ezt tilos visszahozni.

### 4. Iteratív sheet elimination loop

A loop minden iterációban:

1. snapshotolja az incumbentot;
2. meghívja a meglévő `SheetEliminationEngine::run(...)`-t;
3. ellenőrzi:
   - placement count invariant;
   - instance set invariant;
   - `find_violations == []`;
   - `compute_sheet_count_used` csökkent;
   - score nem romlik elfogadhatatlanul;
4. siker esetén commit;
5. sikertelenség esetén rollback és stop vagy következő próbálkozás csak akkor, ha a policy ezt biztonságosan indokolja.

Minimum elfogadás:

```text
successful elimination -> commit
failed elimination -> rollback to exact incumbent and stop_reason = NoImprovement vagy BudgetExhausted
```

Ne commitolj olyan layoutot, amely target/higher sheetet újrahasznál, violationt tartalmaz, vagy elveszít placementet.

### 5. Score és sheet-count viszony

A BPP phase elsődleges célja sheet-count csökkentés.

Acceptance policy:

```text
sheet_count_used csökkenése erősebb, mint layout compactness romlás
azonos sheet_count esetén csak score javulást commitolj
sheet_count növekedés soha nem commitolható
```

Ha a meglévő `ScoreModel` sheet-count büntetése ezt már kezeli, használd. Ha nem, dokumentáld a reportban, és minimális BPP commit policyvel őrizd a fenti invariánst.

## Kötelező tesztek

Adj célzott Rust teszteket, amelyek a Q05 előtti állapotot részben elkapnák.

Minimum:

1. `bpp_phase_iteratively_reduces_multiple_sheets`
   - fixture: több kicsi item több sheeten, geometriailag egy sheetre vagy kevesebb sheetre fér;
   - egyetlen SGH-04 passz nem feltétlenül elég;
   - Q05 loop több sikeres eliminációt tud commitolni.

2. `bpp_phase_failed_attempt_rolls_back_exact_incumbent`
   - fixture: nincs valós sheet-count reduction;
   - output placement count, instance set, x/y/rotation/sheet bit-identikusan megmarad.

3. `bpp_phase_never_increases_sheet_count`
   - bármely outputra `used_after <= used_before`.

4. `bpp_phase_output_is_violation_free`
   - minden committed output `find_violations == []`.

5. `phase_optimizer_invokes_bpp_phase_loop`
   - `PhaseOptimizer::run()` diagnosztikából vagy viselkedésből bizonyítható, hogy BPP phase is lefut.

6. `same_seed_bpp_phase_determinism`
   - azonos layout + parts + sheets + seed → bit-identikus placements.

7. `phase_result_score_layout_consistency_after_bpp`
   - `PhaseResult.score == score(PhaseResult.layout)`.

8. `bpp_budget_limits_attempts`
   - kis `bpp_max_eliminations` / `bpp_budget.max_iterations` mellett nem fut túl.

## Dokumentáció

Hozd létre:

```text
docs/egyedi_solver/sgh_q05_bpp_phase_loop_contract.md
```

Tartalmazza:

```text
- BPP phase célja
- kapcsolat SheetEliminationEngine és PhaseOptimizer között
- commit/rollback invariánsok
- score vs. sheet-count döntési szabály
- determinism contract
- remaining gaps: smooth loss, RotationPolicy, CDE backend
```

## Report elvárás

Hozd létre:

```text
codex/reports/egyedi_solver/sgh_q05_bpp_phase_loop_sheet_elimination.md
codex/reports/egyedi_solver/sgh_q05_bpp_phase_loop_sheet_elimination.verify.log
codex/codex_checklist/egyedi_solver/sgh_q05_bpp_phase_loop_sheet_elimination.md
```

A report első sora csak akkor lehet `PASS`, ha:

```text
- SGH-Q04R report PASS és SGH-Q05_STATUS: READY marker ellenőrizve
- BppPhase vagy ezzel ekvivalens modul létrejött
- PhaseOptimizer ténylegesen beköti a BPP phase-t
- iteratív sheet elimination loop legalább két sikeres eliminációt tud commitolni célzott fixture-n
- failed attempt rollback exact incumbent
- all accepted outputs violation-free
- same-seed determinism zöld
- cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib zöld
- ./scripts/verify.sh zöld
```

PASS esetén a report végén szerepeljen:

```text
SGH-Q06_STATUS: READY
```

Ha bármi nem teljesül:

```text
első sor: REVISE vagy BLOCKED
nincs SGH-Q06_STATUS: READY marker
```

## Nem-blokkoló Q04R észrevételek, amelyeket Q05-ben érdemes javítani, ha belefér

Ezek ne nyissák túl a scope-ot, de a BPP bekötésnél tisztázhatók:

```text
PhaseOptimizer combined diagnostics jelenleg durván összevonja a phase stop_reason-t.
Disruption attempts számláló inkább successful-disruption próbát mér, nem minden belső attemptet.
```

Ha nem módosítod őket, dokumentáld advisoryként, ne nevezd teljes diagnosztikai paritynek.
