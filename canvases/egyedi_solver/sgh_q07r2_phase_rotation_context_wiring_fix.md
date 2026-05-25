# SGH-Q07R2 — Phase/exploration/compression RotationPolicy context wiring fix

## Státusz

Repair task.

## Előfeltétel

Az SGH-Q07R report létezzen és első sora legyen `PASS`:

```text
codex/reports/egyedi_solver/sgh_q07r_rotation_policy_global_wiring_fix.md
```

A Q07R reportban szerepelhet `SGH-Q08_STATUS: READY`, de ezt a Q07R2 audit felülbírálja: Q08 csak Q07R2 PASS után indulhat.

## Miért kell javítani?

A Q07R javította az adapter/multisheet útvonal nagy részét, de a phase-orchestration útvonalban kódszinten még maradt legacy/default rotation context.

Konkrét blokkolók az aktuális Q07R snapshotban:

```text
rust/vrs_solver/src/optimizer/explore.rs
- LargeItemSwapDisruption::try_disrupt(...) MoveExecutor::new(parts, sheets) hívással dolgozik.
- ExplorationPhase::run() VrsSeparatorConfig { seed, worker_count, ..Default } formában hoz létre separatort, ezért a config.rotation_context nem jut át.

rust/vrs_solver/src/optimizer/compress.rs
- CompressionPhase::run() MoveExecutor::new(parts, sheets) hívást használ.
- CompressionPhase::run() lokális RotationResolveContext::legacy_default() contextet hoz létre.
- Emiatt a compression rotation próbák nem a PhaseConfig.rotation_context alapján oldódnak fel.
```

Ez azt jelenti, hogy a Q07/Q07R contract még nem igaz teljesen: a `PhaseConfig.rotation_context` mező létezik, de exploration/disruption/compression útvonalon részben figyelmen kívül marad.

## Cél

A rotation policy context legyen végigvezetve a teljes phase pathon:

```text
PhaseConfig.rotation_context
  -> ExplorationPhase separator
  -> LargeItemSwapDisruption MoveExecutor
  -> CompressionPhase MoveExecutor
  -> CompressionPhase rotation candidate resolve
```

A contract változatlan:

```text
Part.rotation_policy > legacy Part.allowed_rotations_deg > SolverInput.rotation_policy > Orthogonal fallback
```

A Q07R2 célja nem új rotation feature, hanem a Q07R wiring hiányának javítása.

## Scope

### Engedélyezett production fájlok

```text
rust/vrs_solver/src/optimizer/explore.rs
rust/vrs_solver/src/optimizer/compress.rs
rust/vrs_solver/src/optimizer/moves.rs          # csak ha constructor/helper miatt szükséges
rust/vrs_solver/src/optimizer/phase.rs          # csak teszt/config bridge miatt szükséges
rust/vrs_solver/src/rotation_policy.rs          # csak teszt/helper miatt szükséges
rust/vrs_solver/src/item.rs                     # csak teszt/helper miatt szükséges
```

### Engedélyezett artefaktok

```text
canvases/egyedi_solver/sgh_q07r2_phase_rotation_context_wiring_fix.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q07r2_phase_rotation_context_wiring_fix.yaml
codex/prompts/egyedi_solver/sgh_q07r2_phase_rotation_context_wiring_fix/run.md
codex/codex_checklist/egyedi_solver/sgh_q07r2_phase_rotation_context_wiring_fix.md
codex/reports/egyedi_solver/sgh_q07r2_phase_rotation_context_wiring_fix.md
codex/reports/egyedi_solver/sgh_q07r2_phase_rotation_context_wiring_fix.verify.log
docs/egyedi_solver/sgh_q07_rotation_policy_contract.md
```

### Tiltott scope

```text
jagua-rs CDE backend
exact irregular polygon collision
hole/cavity semantics
DXF/preflight refaktor
új optimizer stratégia
Q08 implementáció
LossModel refaktor
BPP sheet elimination refaktor
```

## Kötelező javítások

### 1. Exploration separator config

`ExplorationPhase::run()` ne default rotation contexttel hozzon létre separatort.

Elvárt elv:

```rust
let sep_config = VrsSeparatorConfig {
    seed: self.config.seed as u64,
    worker_count: self.config.worker_count,
    rotation_context: self.config.rotation_context.clone(),
    ..VrsSeparatorConfig::default()
};
```

A pontos forma igazodhat a repo stílusához, de kötelező, hogy a separator a phase config rotation contextjét használja.

### 2. Exploration disruption / MoveExecutor

`LargeItemSwapDisruption::try_disrupt()` jelenleg nem kap rotation contextet, ezért `MoveExecutor::new(parts, sheets)` legacy defaulttal fut.

Javítási lehetőségek:

```text
A) try_disrupt(..., rotation_context: &RotationResolveContext)
   -> MoveExecutor::new_with_rotation_context(parts, sheets, rotation_context.clone())

vagy

B) LargeItemSwapDisruption tárolja a RotationResolveContext-et.
```

A cél: disruption közben a swap/reinsert/separator helper is ugyanazt a rotation policy-t használja, mint a phase.

### 3. Compression MoveExecutor + rotation resolve

`CompressionPhase::run()` ne használjon `RotationResolveContext::legacy_default()` lokális contextet és ne használjon `MoveExecutor::new(parts, sheets)` hívást.

Elvárt elv:

```rust
let rotation_context = self.config.rotation_context.clone();
let exec = MoveExecutor::new_with_rotation_context(parts, sheets, rotation_context.clone());
...
resolve_instance_rotation_angles(pt, &instance_id, &rotation_context)
```

Vagy közvetlenül `&self.config.rotation_context` használata, ha borrow/lifetime szempontból tisztább.

### 4. Auditálás

A reportban rögzítsd pre- és post-fix eredményekkel:

```bash
rg "MoveExecutor::new\(" rust/vrs_solver/src/optimizer/explore.rs rust/vrs_solver/src/optimizer/compress.rs
rg "RotationResolveContext::legacy_default\(\)" rust/vrs_solver/src/optimizer/explore.rs rust/vrs_solver/src/optimizer/compress.rs
rg "VrsSeparatorConfig \{" rust/vrs_solver/src/optimizer/explore.rs
```

PASS esetén:

```text
- explore.rs production pathban nincs MoveExecutor::new legacy defaulttal.
- compress.rs production pathban nincs MoveExecutor::new legacy defaulttal.
- compress.rs production pathban nincs lokális RotationResolveContext::legacy_default().
- ExplorationPhase separator config explicit átadja self.config.rotation_context-et.
```

A tesztekben maradhat legacy helper, de a reportban különítsd el a production és test előfordulásokat.

## Kötelező regressziós tesztek

Adj célzott Rust teszteket, minimum:

```text
exploration_separator_uses_phase_rotation_context
exploration_disruption_uses_phase_rotation_context_for_move_executor
compression_uses_phase_rotation_context_for_candidate_rotations
compression_move_executor_uses_phase_rotation_context
no_production_legacy_context_in_explore_or_compress_phase_paths
```

A tesztek lehetnek unit szintűek, de bizonyítsák a viselkedést, ne csak azt, hogy a függvények léteznek.

Javasolt fixture:

```text
part: 100 x 20, no legacy allowed_rotations_deg, no part policy
phase config: global FortyFive vagy Continuous
sheet/layout: olyan helyzet, ahol orthogonal defaulttal nincs hasznos rotation candidate, FortyFive/Continuous mellett viszont a candidate list eltér vagy a move/separator útvonalban megjelenik nem-orthogonal angle.
```

Ha a placement bizonyítása túl törékeny, legalább instrumentált/célzott helper teszttel igazold, hogy a phase pathban resolved angle list tartalmazza a global policy szerinti szögeket.

## Verify

Futtasd legalább:

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::explore
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::compress
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::phase
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::moves
cargo test --manifest-path rust/vrs_solver/Cargo.toml rotation_policy
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q07r2_phase_rotation_context_wiring_fix.md
```

Ha bármelyik fail, report első sora `REVISE` vagy `BLOCKED`, és nincs `SGH-Q08_STATUS: READY`.

## Report

PASS esetén a report első sora:

```text
PASS
```

és a végén:

```text
SGH-Q08_STATUS: READY
```

A reportnak külön tartalmaznia kell:

```text
- dependency gate eredmény
- pre-fix audit evidence
- konkrét javítások
- post-fix audit evidence
- tesztek listája
- verify log összefoglaló
```
