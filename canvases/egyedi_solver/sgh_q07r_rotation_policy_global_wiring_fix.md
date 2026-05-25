# SGH-Q07R — RotationPolicy global wiring + seed propagation fix

## Státusz

Repair task.

## Előfeltétel

Az SGH-Q07 report létezzen és első sora legyen `PASS`:

```text
codex/reports/egyedi_solver/sgh_q07_rotation_policy_continuous_foundation.md
```

A Q07 reportban lehet `SGH-Q08_STATUS: READY`, de ezt a Q07R audit felülbírálja: Q08 csak Q07R PASS után indulhat.

## Miért kell javítani?

Az SGH-Q07 bevezette a `RotationPolicyKind` modult, a `Part.rotation_policy` mezőt, a `SolverInput.rotation_policy` mezőt és a f64 rotation math-ot. Kódszintű audit alapján viszont a globális policy a valós solve pathban nem érvényesül.

Konkrét hibák az aktuális Q07 snapshotban:

```text
rust/vrs_solver/src/io.rs
- SolverInput.rotation_policy parse-olva van.

rust/vrs_solver/src/adapter.rs
- expand_instances(&input.parts) hívás nem kapja meg input.rotation_policy-t vagy input.seed-et.
- can_fit_any_stock(part, &sheets) hívások nem kapják meg a globális policy-t.

rust/vrs_solver/src/item.rs
- expand_instances(parts) resolve_part_rotation_angles(part, None, 0, 8) hívással dolgozik.
- build_item_geometry_store(parts) ugyanezt teszi.
- can_fit_any_stock(part, sheets) ugyanezt teszi.

optimizer call site-ok
- több helyen maradt resolve_part_rotation_angles(part, None, 0, 8): separator, compression, moves, repair, sheet_elimination, initializer fallback.
```

Ez azt jelenti, hogy egy input szintű:

```json
"rotation_policy": "forty_five"
```

vagy

```json
"rotation_policy": "continuous"
```

nem feltétlenül hat a tényleges példányokra és visszarakási útvonalakra. Ez contract szintű hiba, ezért Q08 előtt javítani kell.

## Cél

A Q07 rotation policy contract legyen igaz a teljes valós solve pathra:

```text
1. Part.rotation_policy > legacy Part.allowed_rotations_deg > SolverInput.rotation_policy > Orthogonal fallback.
2. A globális policy érvényesüljön adapter → instance expansion → construction → repair → separator → compression → sheet elimination útvonalon.
3. Continuous policy seedelt, determinisztikus és nem fake: ugyanazon input+seed ugyanazt adja, más seed legalább a candidate listát képes megváltoztatni.
4. Legacy allowed_rotations_deg viselkedés ne romoljon.
5. Q08 CDE backend csak ezután indulhat.
```

## Scope

### Engedélyezett production fájlok

```text
rust/vrs_solver/src/adapter.rs
rust/vrs_solver/src/item.rs
rust/vrs_solver/src/rotation_policy.rs
rust/vrs_solver/src/optimizer/initializer.rs
rust/vrs_solver/src/optimizer/separator.rs
rust/vrs_solver/src/optimizer/compress.rs
rust/vrs_solver/src/optimizer/moves.rs
rust/vrs_solver/src/optimizer/repair.rs
rust/vrs_solver/src/optimizer/sheet_elimination.rs
rust/vrs_solver/src/optimizer/multisheet.rs
rust/vrs_solver/src/optimizer/phase.rs          # csak ha config/context átvezetéshez szükséges
rust/vrs_solver/src/optimizer/bpp_phase.rs      # csak ha config/context átvezetéshez szükséges
```

### Engedélyezett artefaktok

```text
docs/egyedi_solver/sgh_q07_rotation_policy_contract.md
codex/codex_checklist/egyedi_solver/sgh_q07r_rotation_policy_global_wiring_fix.md
codex/reports/egyedi_solver/sgh_q07r_rotation_policy_global_wiring_fix.md
codex/reports/egyedi_solver/sgh_q07r_rotation_policy_global_wiring_fix.verify.log
```

### Tiltott scope

```text
jagua-rs CDE backend
exact irregular polygon collision
hole/cavity semantics
DXF/preflight refaktor
új optimizer stratégia
Q06 LossModel refaktor
Q08 implementáció
```

## Kötelező implementációs elv

Ne duplikáld tovább a `resolve_part_rotation_angles(part, None, 0, 8)` mintát.

Vezess be egy egyértelmű rotation contextet vagy kompatibilis helper-réteget. Például:

```rust
pub struct RotationResolveContext<'a> {
    pub global_policy: Option<&'a RotationPolicyKind>,
    pub seed: u64,
    pub continuous_sample_count: usize,
}
```

A pontos forma igazodhat a repo stílusához, de a lényeg kötelező:

```text
- global_policy átmegy az adapterből az instance expansionbe;
- seed nem hardcoded 0;
- continuous_sample_count nem szétszórt magic number;
- fallback call site-ok vagy az Instance már-resolved rotation listáját használják, vagy ugyanazt a contextet;
- nincs olyan production call site, amely indokolatlanul `None, 0, 8` paraméterrel felülírja a globális policy-t.
```

## Konkrét javítandó pontok

### 1. Adapter wiring

`adapter::solve(input)` a következőkre használja az input policy-t:

```text
expand_instances_with_policy(&input.parts, input.rotation_policy.as_ref(), input.seed, sample_count)
can_fit_any_stock_with_policy(part, &sheets, input.rotation_policy.as_ref(), input.seed, sample_count)
MultiSheetManager::new(...) vagy run(...) kapja meg a rotation contextet, ha a későbbi fázisoknak kell.
```

Ha a régi `expand_instances(parts)` API megmarad, az legyen backward-compatible wrapper Orthogonal/default contexttel, de a valós solve path ne azt használja.

### 2. Item helpers

`item.rs` helper szinten legyenek policy-aware variánsok:

```text
expand_instances_with_policy
can_fit_any_stock_with_policy
build_item_geometry_store_with_policy
```

A régi függvények maradhatnak test/backward compat wrapperként, de dokumentálni kell, hogy default/legacy contextet használnak.

### 3. Optimizer call site-ok

Auditáld és javítsd az összes production előfordulást:

```bash
rg "resolve_part_rotation_angles\([^\n]*None, 0, 8" rust/vrs_solver/src
rg "expand_instances\(&input.parts\)" rust/vrs_solver/src
rg "can_fit_any_stock\(" rust/vrs_solver/src
```

Ahol lehet, a már feloldott `Instance.allowed_rotations_deg` listát használd. Ahol csak `Part` van, add át a rotation contextet az adott structba/függvénybe.

Különösen nézd:

```text
adapter.rs
initializer.rs try_separator_fallback_for_instance
separator.rs find_best_candidate_for_target
compress.rs rotation próbák
moves.rs resolve_part_dims
repair.rs resolve_part_dims
sheet_elimination.rs resolve_dims
```

### 4. Continuous seed determinism

A continuous candidate-ek seedje ne mindig 0 legyen. Legyen determinisztikus, input seedből és part/instance azonosítóból származtatva.

Elvárt tulajdonságok:

```text
same input + same seed => byte-identical output
same input + different seed => legalább a continuous candidate angle list eltérhet
part/instance list sorrend stabil marad
canonical 0/90/180/270 továbbra is benne van continuous policy esetén
```

Nem kell Q07R-ben tökéletes Sparrow wiggle/coordinate descent. Csak a Q07 contract valódi wiringja kell.

## Kötelező tesztek

Adj célzott Rust regression teszteket, minimum:

```text
global_forty_five_policy_affects_expand_instances_when_part_has_no_legacy_rots
global_continuous_policy_affects_expand_instances_when_part_has_no_legacy_rots
adapter_solve_global_forty_five_places_100x20_on_90x90_sheet
adapter_solve_legacy_allowed_rotations_overrides_global_policy
part_policy_overrides_global_policy_in_real_solve_path
continuous_policy_same_seed_deterministic_through_solve
continuous_policy_different_seed_changes_resolved_candidate_angles
no_remaining_production_none_zero_eight_policy_resolution_without_justification
```

A 100x20 / 90x90 fixture:

```text
part: 100 x 20, quantity 1, no allowed_rotations_deg, no part policy
sheet: 90 x 90
case A: no global policy / Orthogonal => should not be placeable
case B: global forty_five => should be placeable
```

Ez a legfontosabb acceptance gate, mert bizonyítja, hogy a globális policy nem csak unit helperben működik, hanem a valós adapter solve pathban is.

## Verify

Futtasd legalább:

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml rotation_policy
cargo test --manifest-path rust/vrs_solver/Cargo.toml item
cargo test --manifest-path rust/vrs_solver/Cargo.toml adapter
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::initializer
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::separator
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::compress
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::moves
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::repair
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::sheet_elimination
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q07r_rotation_policy_global_wiring_fix.md
```

Ha bármelyik fail, report első sora `REVISE` vagy `BLOCKED`, és nincs Q08 marker.

## Report követelmény

A report tartalmazza:

```text
- első sor: PASS / REVISE / BLOCKED
- dependency evidence
- exact blocker list from pre-fix audit
- changed files/functions matrix
- global policy real solve path evidence
- remaining `resolve_part_rotation_angles(... None, 0, 8)` audit table, mindegyikhez indoklással
- continuous seed determinism evidence
- legacy no-downgrade evidence
- tests added/fixed list
- verify commands and results
```

PASS esetén a report végén legyen:

```text
SGH-Q08_STATUS: READY
```

