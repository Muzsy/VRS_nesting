# SGH-05 — Transfer / swap / reinsert move operators

## Kontextus

SGH-00 lezárta a Sparrow/SparrowGH kódauditot és kimondta a stratégiai döntést:

```text
Do not run SparrowGH as an external backend.
Use Sparrow/SparrowGH as audited algorithmic source.
Port / reimplement selected algorithms inside the VRS jagua_optimizer.
```

SGH-01 bevezette a `WorkingLayout`-ot, amely ideiglenesen infeasible / colliding keresési állapotot is tarthat, de csak explicit commit gate után adhat elfogadott outputot.

SGH-02 bevezette a saját `VrsCollisionTracker` + `VrsSeparator` V1 réteget.

SGH-03 bekötötte a separatort az initial constructionbe LBF-scored clear placement + separator fallback mintával.

SGH-04 V2-re emelte a sheet eliminationt: highest-used sheet target, lower-index redistribution, LBF clear reinsert, separator fallback, strict commit/rollback gate.

SGH-05 következő lépése a SparrowGH `bp_moves.rs` mintájának VRS-be portolása: transfer / swap / reinsert move operátorok végrehajtása rollback-safe módon. Ez még **nem** pipeline-integráció, nem solution pool, nem perturbáció és nem multi-restart.

---

## Task cél

Implementáld a `rust/vrs_solver/src/optimizer/moves.rs` jelenlegi skeleton állapotából a VRS-internal move execution alaprétegét.

A cél, hogy legyenek determinisztikus, rollback-safe, separatort használó move operátorok:

```text
try_transfer
try_swap
try_reinsert / try_rotate_reinsert
resolve_by_transfers
```

A move-ok csak akkor commitolhatnak, ha az eredmény:

```text
find_violations() == []
WorkingLayout::validate_for_commit() Ok
placement count invariant preserved
same instance set preserved
no out-of-boundary / overlap violation
```

Failure esetén az eredeti placement snapshot változatlanul visszaáll.

---

## Kötelező dependency gate

SGH-05 csak akkor indulhat, ha:

```text
codex/reports/egyedi_solver/sgh_04_separator_backed_sheet_elimination.md
```

létezik, első sora `PASS` vagy `PASS_WITH_NOTES`, és tartalmazza:

```text
SGH-05_STATUS: READY
```

Ha bármely feltétel hiányzik, állj meg `BLOCKED` státusszal, és csak ezeket frissítsd:

```text
codex/reports/egyedi_solver/sgh_05_transfer_swap_reinsert_move_operators.md
codex/codex_checklist/egyedi_solver/sgh_05_transfer_swap_reinsert_move_operators.md
```

---

## Kötelező repo anchorok

Olvasd el és auditáld, ne feltételezd:

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
codex/reports/egyedi_solver/sgh_04_separator_backed_sheet_elimination.md
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

---

## Kötelező kódaudit megállapítások

A reportban rögzítsd legalább ezeket:

1. `moves.rs` jelenleg csak `CandidateMove` enum skeleton + serialization teszteket tartalmaz, tényleges execution nélkül.
2. `WorkingLayout` már alkalmas ideiglenesen ütköző állapot tárolására, de commit csak `validate_for_commit()` után lehet.
3. `VrsSeparatorConfig.allowed_sheet_indices` SGH-04 óta használható arra, hogy egy move repair csak meghatározott sheeteken mozogjon.
4. `find_violations()` a VRS oldali accepted-output safety gate.
5. `Placement` IO contractot nem szabad módosítani.
6. SGH-05-ben a move execution még nem köthető automatikusan az optimizer pipeline-ba; csak belső API + unit teszt lefedés kell.
7. A move-oknak deterministicnek kell lenniük: azonos input + azonos move → azonos output.
8. Nincs külső SparrowGH backend, vendor/submodule vagy CLI adapter.

---

## Tervezett implementáció

### 1. Move execution API

A `moves.rs`-ben vezesd be a jelenlegi `CandidateMove` skeleton megtartása mellett a végrehajtási API-t.

Javasolt, de nem kötelező struktúra:

```rust
pub struct MoveExecutor<'a> {
    parts: &'a [Part],
    sheets: &'a [SheetShape],
}

pub struct MoveDiagnostics {
    pub attempted: usize,
    pub committed: usize,
    pub rolled_back: usize,
    pub separator_attempts: usize,
    pub separator_successes: usize,
    pub commit_gate_rejections: usize,
    pub reason: String,
}
```

A pontos név eltérhet, de legyen világos:

```text
melyik move indult
lefutott-e separator
commitolt-e
rollback történt-e
miért fail
```

### 2. `try_reinsert` / `try_rotate_reinsert`

Implementáld az egyszerű alapoperátort:

```text
snapshot placements
find instance by instance_id
replace sheet_index + transform / rotation
build WorkingLayout
run VrsSeparator with allowed_sheet_indices = target sheet vagy explicit scope
validate_for_commit + find_violations
commit if valid
else rollback
```

Elvárások:

```text
- invalid instance_id -> no commit, rollback/failure diagnostics;
- invalid sheet index -> no commit;
- unsupported rotation -> no commit;
- overlapping seed is allowed only inside WorkingLayout;
- accepted result must be violation-free;
- placement count unchanged;
- instance set unchanged.
```

### 3. `try_transfer`

SparrowGH `try_transfer()` VRS megfelelője:

```text
move one item from from_sheet to to_sheet
seed it on to_sheet, preferably with LBF clear placement; if not possible, seed at origin/explicit transform and run separator
run VrsSeparator with allowed_sheet_indices restricted to to_sheet, or clearly documented safe scope
source sheet remains valid after item removal
commit only if global find_violations() empty
rollback on fail
```

Javasolt prioritás:

1. Ha a caller explicit transformot ad, próbáld azt.
2. Ha nincs explicit transform, keress LBF clear candidate-et `to_sheet`-en.
3. Ha nincs clear candidate, seedeld boundary-valid origin/candidate pontra és futtasd a separatort.

### 4. `try_swap`

SparrowGH `try_swap()` VRS megfelelője:

```text
swap two placed instances between sheet A and sheet B
preserve instance_id + part_id
try each item at the other item's old transform if rotation supported / boundary plausible
then run VrsSeparator with allowed_sheet_indices = {sheet_a, sheet_b}
commit only if both affected sheets and global layout valid
rollback on fail
```

Elvárások:

```text
- same-sheet swap esetén determinisztikus no-op vagy documented behavior;
- invalid ids -> rollback/failure;
- unsupported rotations -> failure;
- placement count and instance set preserved;
- no global violation on commit.
```

### 5. `resolve_by_transfers`

Implementálj budget-limited helper réteget:

```text
input: placements, infeasible_sheet_indices, candidate destination sheet indices, budget
for each source sheet:
  for each item on source sheet in deterministic order:
    for each destination sheet in deterministic order:
      try_transfer
      if success and global layout valid: continue/return updated layout according to documented policy
stop when budget exhausted or policy should_stop
```

Minimum elvárás:

```text
- deterministic order: source sheet asc, item largest-first or instance_id asc, destination sheet asc;
- every failed attempt restores exact previous layout;
- budget respected;
- diagnostics includes attempts/commits/rollbacks;
- no partial invalid output.
```

### 6. Commit / rollback invariant helpers

Adj helper ellenőrzéseket, vagy tesztekkel bizonyítsd:

```text
placement_count preserved
instance_id set preserved
find_violations empty on commit
WorkingLayout::validate_for_commit Ok
no out-of-range sheet_index
same input order determinism, or documented stable sorted output
```

Ha a move sikeres, lehetőleg tartsd meg a stabil placement orderinget. Ha reorder történik, legyen determinisztikus és reportban dokumentált.

---

## Tilos ebben a taskban

Ne csináld:

```text
- külső SparrowGH backend adapter
- Sparrow/SparrowGH vendor/submodule
- Python runner vagy exact validator módosítás
- io.rs / SolverOutput / SolverInput contract módosítás
- adapter.rs módosítás
- initializer.rs, sheet_elimination.rs pipeline-behívás módosítás, kivéve ha csak import-kompatibilitás miatt szükséges és reportban indokolt
- score.rs objective rewrite
- solution pool / perturbáció / multi-restart
- continuous rotation
- nagy benchmark kampány / LV8 futtatás
- cavity-prepack
```

Engedélyezett production módosítás alapértelmezetten:

```text
rust/vrs_solver/src/optimizer/moves.rs
```

Ha a fordításhoz minimális `mod.rs` exportmódosítás kell, előbb ellenőrizd, hogy valóban szükséges-e. Csak akkor módosítsd, ha szerepel a YAML outputsban és a reportban külön indoklod. Alapesetben `moves.rs` már modul része, ezért `mod.rs` módosítás nem kell.

---

## Kötelező unit tesztek

Adj/frissíts Rust unit teszteket elsősorban `moves.rs` alatt.

Minimum tesztek:

```text
1. meglévő CandidateMove serialization tesztek zöldek maradnak;
2. try_reinsert valid move commitol és find_violations üres;
3. try_reinsert invalid/out-of-bound move rollback/fail;
4. try_transfer egy itemet másik sheetre visz, majd valid layoutot ad;
5. try_transfer invalid destination vagy unsupported rotation esetén rollback/fail;
6. try_swap két itemet determinisztikusan cserél és valid layoutot ad;
7. try_swap impossible/invalid esetben rollback-safe;
8. resolve_by_transfers tiszteletben tartja a budgetet;
9. resolve_by_transfers failure esetén nem hagy partial invalid outputot;
10. diagnostics summary tartalmaz attempt/commit/rollback/separator mezőket;
11. committed output placement count + instance set invariant megmarad;
12. deterministic smoke: ugyanaz az input + move kétszer ugyanazt az outputot adja.
```

A tesztek valós VRS típusokat használjanak:

```text
Part
Stock / SheetShape
Placement
WorkingLayout
VrsSeparator
find_violations
```

Ne mockold a commit gate-et.

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

## Done feltételek

PASS csak akkor adható, ha:

```text
- dependency gate zöld;
- moves.rs execution API elkészült;
- transfer/swap/reinsert rollback-safe;
- resolve_by_transfers budget-aware és rollback-safe;
- accepted output find_violations szerint valid;
- placement count + instance set invariant tesztelve;
- deterministic move output tesztelve;
- focused Rust tests zöldek;
- repo verify zöld;
- nincs külső backend/vendor;
- report végén szerepel: SGH-06_STATUS: READY.
```
