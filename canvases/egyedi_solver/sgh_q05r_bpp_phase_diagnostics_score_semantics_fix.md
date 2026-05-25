# SGH-Q05R — BPP phase diagnostics + PhaseResult score semantics fix

## Státusz

Revision task. SGH-Q05 után futtatandó, mert a Q05 core BPP loop működik, de a kódszintű audit két szerződésbeli hiányt talált.

## Miért kell?

SGH-Q05 létrehozta a `BppPhase` modult és bekötötte a `PhaseOptimizer::run()` végére. A core commit gate rendben van, de a Q05 canvas/YAML szerződésből két pont nem teljesült elég tisztán:

```text
1. BppPhaseDiagnostics nem tartalmazza a kért per-attempt diagnostics + initial_score/best_score mezőket.
2. PhaseOptimizer::run() kommentje azt állítja, hogy best_score a final layout score-ja, de a kód min(exploration, compression, bpp/final, initial) értéket használ.
```

Ez nem geometriai/logikai rollback hiba, de auditálhatósági és score-semantics kockázat. Q06 előtt javítani kell, hogy a későbbi LossModel mérések ne félrevezető `best_score` jelentésre épüljenek.

## Scope

Engedélyezett production fájlok:

```text
rust/vrs_solver/src/optimizer/bpp_phase.rs
rust/vrs_solver/src/optimizer/phase.rs
```

Dokumentáció/report:

```text
canvases/egyedi_solver/sgh_q05r_bpp_phase_diagnostics_score_semantics_fix.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q05r_bpp_phase_diagnostics_score_semantics_fix.yaml
codex/prompts/egyedi_solver/sgh_q05r_bpp_phase_diagnostics_score_semantics_fix/run.md
codex/codex_checklist/egyedi_solver/sgh_q05r_bpp_phase_diagnostics_score_semantics_fix.md
codex/reports/egyedi_solver/sgh_q05r_bpp_phase_diagnostics_score_semantics_fix.md
codex/reports/egyedi_solver/sgh_q05r_bpp_phase_diagnostics_score_semantics_fix.verify.log
docs/egyedi_solver/sgh_q05_bpp_phase_loop_contract.md
```

Tiltott scope:

```text
Q06 LossModel / smooth loss
Q07 RotationPolicy
Q08 CDE backend
SheetEliminationEngine algoritmus átírása
Phase orchestration újratervezése
DXF/API/frontend/runner módosítás
```

## Javítandó pontok

### 1. BppPhaseDiagnostics bővítés

Bővítsd a diagnosztikát legalább ezekkel:

```rust
pub initial_score: f64,
pub best_score: f64,
pub per_attempt: Vec<SheetEliminationDiagnostics>,
```

A meglévő mezők maradjanak backward-compatible módon, vagy legyen egyértelmű átnevezés dokumentálva:

```text
initial_sheet_count / final_sheet_count
attempts
successful_eliminations
failed_eliminations
rollback_count
stop_reason
```

A `BppPhase::run()` scoringhoz használja a meglévő `ScoreModel`-t a `PhaseConfig.score_weights` alapján. A `best_score` csak ténylegesen látott/committed layout score lehet.

### 2. Per-attempt diagnostics

Minden `SheetEliminationEngine::run()` eredményét mentsd el:

```rust
per_attempt.push(elim_diag.clone())
```

Ez kell későbbi auditokhoz: melyik target sheet, hány displaced item, miért commit/rollback.

### 3. PhaseResult score semantics

A `PhaseResult.score` továbbra is a final returned layout score-ja legyen.

A `PhaseResult.best_score` ne állítson olyan értéket, amelyhez a `PhaseResult` nem ad vissza layoutot. Minimum elfogadás:

```rust
let best_score = final_score.total_cost;
```

Ha meg akarod tartani a „best seen during phases” információt, azt csak diagnostics mezőben dokumentáld, ne a `PhaseResult.best_score` mezőben, amíg nincs hozzá visszaadott layout vagy explicit `best_seen_score` mező.

Javítsd a félrevezető kommentet is.

### 4. Tesztek szigorítása

A Q05 teszteket egészítsd ki vagy szigorítsd:

```text
bpp_phase_iteratively_reduces_multiple_sheets
  - a 3 item / 3 sheet / 100x100 fixture esetén final sheet count legyen 1, vagy successful_eliminations >= 2.

bpp_phase_diagnostics_records_per_attempt
  - attempts == per_attempt.len()
  - minden attempt tartalmaz selected_sheet/stop_reason jellegű adatot.

bpp_phase_diagnostics_score_fields_are_real
  - initial_score == score(input layout)
  - best_score <= initial_score csak akkor, ha tényleges committed improvement történt
  - best_score valamely committed incumbent score-ja legyen.

phase_result_best_score_equals_final_layout_score_after_bpp
  - result.best_score == result.score.total_cost.
```

## Dokumentáció

Frissítsd:

```text
docs/egyedi_solver/sgh_q05_bpp_phase_loop_contract.md
```

Rögzítse:

```text
- BppPhaseDiagnostics mezők
- per_attempt audit szerepe
- PhaseResult.score és PhaseResult.best_score jelentése
- ha best-seen metrika kell később, külön mezőben kell bevezetni
```

## Verify

Futtasd:

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::bpp_phase
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::phase
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q05r_bpp_phase_diagnostics_score_semantics_fix.md
```

Ha bármi fail:

```text
report első sora: REVISE vagy BLOCKED
ne legyen SGH-Q06_STATUS marker
```

Ha minden zöld:

```text
report első sora: PASS
report vége: SGH-Q06_STATUS: READY
```
