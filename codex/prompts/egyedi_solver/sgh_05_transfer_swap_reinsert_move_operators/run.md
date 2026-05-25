# Runner prompt — SGH-05 `sgh_05_transfer_swap_reinsert_move_operators`

## Feladat

A helyi `VRS_nesting` repo gyökerében dolgozz. Hajtsd végre az SGH-05 taskot:

```text
SGH-05 — Transfer / swap / reinsert move operators
```

Ez belső Rust optimizer migrációs task. A cél: a SparrowGH `bp_moves.rs` mintájából a VRS saját `optimizer/moves.rs` rétegébe portolni / újraimplementálni a rollback-safe move operátorokat.

**Ne építs külső SparrowGH backendet. Ne vendorolj külső kódot. Ne módosíts Python runnert, exact validatort vagy SolverOutput IO contractot. Ne kösd még be automatikusan a pipeline-ba.**

---

## Kötelező dependency preflight

Ellenőrizd:

```text
codex/reports/egyedi_solver/sgh_04_separator_backed_sheet_elimination.md
```

Feltételek:

- a report létezik;
- első sora `PASS` vagy `PASS_WITH_NOTES`;
- tartalmazza: `SGH-05_STATUS: READY`.

Ha bármelyik feltétel nem teljesül, állj meg:

```text
STATUS: BLOCKED
REASON: Missing or non-PASS dependency: SGH-04 separator-backed sheet elimination
```

Ilyenkor csak ezeket frissítsd:

```text
codex/reports/egyedi_solver/sgh_05_transfer_swap_reinsert_move_operators.md
codex/codex_checklist/egyedi_solver/sgh_05_transfer_swap_reinsert_move_operators.md
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
docs/egyedi_solver/sgh_02_vrs_separator_contract.md
docs/egyedi_solver/sgh_03_lbf_separator_construction_contract.md
docs/egyedi_solver/sgh_04_separator_backed_sheet_elimination_contract.md
canvases/egyedi_solver/sgh_05_transfer_swap_reinsert_move_operators.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_05_transfer_swap_reinsert_move_operators.yaml
codex/codex_checklist/egyedi_solver/sgh_05_transfer_swap_reinsert_move_operators.md
```

Az `AGENTS.md` outputs szabálya kötelező: csak a YAML step `outputs` listáiban szereplő fájlokat módosíthatod.

---

## Valós kód audit

A megvalósítás előtt nézd át:

```text
rust/vrs_solver/src/optimizer/moves.rs
rust/vrs_solver/src/optimizer/working.rs
rust/vrs_solver/src/optimizer/separator.rs
rust/vrs_solver/src/optimizer/sheet_elimination.rs
rust/vrs_solver/src/optimizer/candidates.rs
rust/vrs_solver/src/optimizer/boundary.rs
rust/vrs_solver/src/optimizer/initializer.rs
rust/vrs_solver/src/optimizer/repair.rs
rust/vrs_solver/src/optimizer/multisheet.rs
rust/vrs_solver/src/optimizer/stopping.rs
rust/vrs_solver/src/optimizer/state.rs
rust/vrs_solver/src/io.rs
rust/vrs_solver/src/item.rs
rust/vrs_solver/src/sheet.rs
```

A reportban külön igazold:

1. `moves.rs` jelenleg csak skeleton / serialization szint.
2. `WorkingLayout` commit gate-je használható move execution validálásra.
3. `VrsSeparatorConfig.allowed_sheet_indices` használható sheet-scope korlátozáshoz.
4. A move-ok failure esetén nem hagyhatnak partial invalid layoutot.
5. Pipeline-integráció, solution pool és perturbáció SGH-05-ben még tilos.

---

## Implementációs irány

### 1. Move execution API és diagnostics

A `moves.rs`-ben tartsd meg a `CandidateMove` enumot és meglévő serialization teszteket. Erre építve adj hozzá végrehajtási API-t.

Lehetséges forma:

```rust
pub struct MoveExecutor<'a> { ... }
pub struct MoveDiagnostics { ... }
pub enum MoveFailureReason { ... }
```

A pontos név nem kötelező, de legyen publikusan vagy legalább crate-szinten tesztelhető.

Diagnostics minimum:

```text
attempted
committed
rolled_back
separator_attempts
separator_successes
commit_gate_rejections
reason / last_reason
```

### 2. Reinsert operator

Implementálj rollback-safe reinsert operátort:

```text
snapshot
find instance
apply target sheet + transform/rotation seed
WorkingLayout
VrsSeparator::run() scoped to target sheet, ha kell
validate_for_commit + find_violations
commit vagy rollback
```

Elvárt failure esetek:

```text
unknown instance_id
invalid sheet index
unsupported rotation
boundary violation that separator cannot fix
overlap that separator cannot fix
```

### 3. Transfer operator

Implementálj rollback-safe transfer operátort:

```text
find item on from_sheet
move/seed to to_sheet
prefer LBF clear placement on to_sheet when explicit transform nincs
fallback separator on to_sheet
commit only if global layout valid
```

Ha a source sheet üres lesz, az rendben van; sheet elimination logikát azonban ne triggerelj itt automatikusan.

### 4. Swap operator

Implementálj rollback-safe swap operátort:

```text
find item A and item B
swap their sheet/transform seed states
run separator with allowed_sheet_indices = {sheet_a, sheet_b}
commit only if global layout valid
```

Same-sheet swap legyen determinisztikus: vagy no-op success, vagy documented failure. Válassz egyet, teszteld és dokumentáld.

### 5. Resolve-by-transfers helper

Implementálj budget-aware helper réteget:

```text
resolve_by_transfers(placements, infeasible_sheets, candidate_destinations, budget, policy)
```

A pontos signature eltérhet, de a viselkedés legyen:

```text
deterministic iteration order
budget respected
failed attempt rollback
success után valid layout
no partial invalid output
```

### 6. Invariant helper / commit gate

Adj helper ellenőrzést vagy belső függvényt:

```text
same placement count
same instance_id set
find_violations empty
WorkingLayout::validate_for_commit Ok
no invalid sheet index
```

Ezeket használd minden operator commit előtt.

---

## Scope szabályok

Engedélyezett production módosítás:

```text
rust/vrs_solver/src/optimizer/moves.rs
```

Dokumentáció / task artefaktok:

```text
docs/egyedi_solver/sgh_05_move_operators_contract.md
codex/codex_checklist/egyedi_solver/sgh_05_transfer_swap_reinsert_move_operators.md
codex/reports/egyedi_solver/sgh_05_transfer_swap_reinsert_move_operators.md
```

Tilos:

```text
- külső SparrowGH backend adapter
- Sparrow/SparrowGH vendor/submodule
- Python runner vagy exact validator módosítás
- io.rs / SolverOutput / SolverInput contract módosítás
- adapter.rs módosítás
- initializer.rs / sheet_elimination.rs pipeline integration
- score.rs objective rewrite
- solution pool / perturbation / multi-restart
- continuous rotation
- nagy benchmark kampány / LV8 futtatás
- cavity-prepack
```

---

## Tesztek

Adj/frissíts Rust unit teszteket `moves.rs` alatt.

Minimum:

```text
cargo test -p vrs_solver moves
cargo test -p vrs_solver separator sheet_elimination moves
```

Ha a workspace/package név miatt más a pontos parancs, használd a helyi ekvivalenst és dokumentáld.

Tesztelendő:

```text
- meglévő CandidateMove serialization tesztek zöldek;
- try_reinsert success + failure/rollback;
- try_transfer success + invalid destination rollback;
- try_swap success + impossible rollback;
- resolve_by_transfers budget respected;
- diagnostics summary mezők;
- placement count + instance set invariant;
- deterministic same input + move => same output;
- committed output find_violations() szerint valid.
```

---

## Kötelező dokumentáció

Hozd létre:

```text
docs/egyedi_solver/sgh_05_move_operators_contract.md
```

Kötelező szekciók:

```text
# SGH-05 Move operators contract

## Purpose
## Current moves.rs gap
## SparrowGH bp_moves.rs mapping
## Move execution API
## Reinsert operator
## Transfer operator
## Swap operator
## Resolve-by-transfers helper
## Commit/rollback gates
## Diagnostics
## Determinism rules
## Scope exclusions
## Preparation for SGH-06
```

---

## Checklist és report

Töltsd ki:

```text
codex/codex_checklist/egyedi_solver/sgh_05_transfer_swap_reinsert_move_operators.md
codex/reports/egyedi_solver/sgh_05_transfer_swap_reinsert_move_operators.md
```

A report tartalmazzon:

```text
Dependency evidence
Current-state audit findings
Change summary
Implementation summary
Tests
Scope safety
DoD -> Evidence Matrix
Advisory notes, ha van
```

PASS csak zöld focused Rust tesztek + zöld repo gate után adható.

---

## Repo gate

Futtasd:

```text
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_05_transfer_swap_reinsert_move_operators.md
```

Ha fail, a report első sora nem lehet PASS. Ha zöld, a report végén szerepeljen:

```text
SGH-06_STATUS: READY
```
