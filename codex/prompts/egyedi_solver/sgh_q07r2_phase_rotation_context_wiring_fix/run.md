# Runner — SGH-Q07R2 Phase/exploration/compression RotationPolicy context wiring fix

Feladat: hajtsd végre a `canvases/egyedi_solver/sgh_q07r2_phase_rotation_context_wiring_fix.md` canvas és a hozzá tartozó goal YAML alapján az SGH-Q07R2 javító taskot.

## Dependency gate

Kötelező:

```text
codex/reports/egyedi_solver/sgh_q07r_rotation_policy_global_wiring_fix.md
```

Első sor: `PASS`.

Ha nincs, állj meg `BLOCKED` reporttal, production kódmódosítás nélkül.

## Kötelező bemenetek

Olvasd el:

```text
AGENTS.md
docs/codex/overview.md
docs/codex/yaml_schema.md
docs/codex/report_standard.md
docs/qa/testing_guidelines.md
canvases/egyedi_solver/sgh_q07_rotation_policy_continuous_foundation.md
canvases/egyedi_solver/sgh_q07r_rotation_policy_global_wiring_fix.md
docs/egyedi_solver/sgh_q07_rotation_policy_contract.md
canvases/egyedi_solver/sgh_q07r2_phase_rotation_context_wiring_fix.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q07r2_phase_rotation_context_wiring_fix.yaml
```

## Javítandó hiba

A Q07R után az adapter/multisheet path többnyire policy-aware, de a phase-orchestration pathban maradt legacy/default context.

Ellenőrizd:

```bash
rg "MoveExecutor::new\(" rust/vrs_solver/src/optimizer/explore.rs rust/vrs_solver/src/optimizer/compress.rs
rg "RotationResolveContext::legacy_default\(\)" rust/vrs_solver/src/optimizer/explore.rs rust/vrs_solver/src/optimizer/compress.rs
rg "VrsSeparatorConfig \{" rust/vrs_solver/src/optimizer/explore.rs
```

A reportban rögzítsd a pre-fix találatokat fájl/sor szinten.

## Kötelező javítás

### Exploration separator

`ExplorationPhase::run()` separator configja explicit kapja meg:

```text
self.config.rotation_context.clone()
```

Ne maradjon `..VrsSeparatorConfig::default()` miatt default rotation context a production pathban.

### Exploration disruption

`LargeItemSwapDisruption::try_disrupt()` ne `MoveExecutor::new(parts, sheets)` hívást használjon legacy default contexttel.

Elfogadható megoldás:

```text
try_disrupt(..., rotation_context: &RotationResolveContext)
MoveExecutor::new_with_rotation_context(parts, sheets, rotation_context.clone())
```

vagy repo-stílushoz illeszkedő ekvivalens.

### Compression

`CompressionPhase::run()` ne használjon:

```text
MoveExecutor::new(parts, sheets)
RotationResolveContext::legacy_default()
```

Helyette a `self.config.rotation_context` legyen a forrás mind a MoveExecutor, mind a `resolve_instance_rotation_angles` számára.

## Nem cél

Ne implementáld Q08-at:

```text
jagua-rs CDE backend
exact irregular polygon collision
hole/cavity semantics
DXF/preflight refaktor
új optimizer stratégia
LossModel refaktor
BPP refaktor
```

## Kötelező regression tesztek

Minimum:

```text
exploration_separator_uses_phase_rotation_context
exploration_disruption_uses_phase_rotation_context_for_move_executor
compression_uses_phase_rotation_context_for_candidate_rotations
compression_move_executor_uses_phase_rotation_context
no_production_legacy_context_in_explore_or_compress_phase_paths
```

A tesztek bizonyítsák, hogy a phase path a `PhaseConfig.rotation_context` alapján dolgozik. Test-only legacy wrapper előfordulás megengedett, production leakage nem.

## Verify

Futtasd:

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

Hozd létre/frissítsd:

```text
codex/codex_checklist/egyedi_solver/sgh_q07r2_phase_rotation_context_wiring_fix.md
codex/reports/egyedi_solver/sgh_q07r2_phase_rotation_context_wiring_fix.md
codex/reports/egyedi_solver/sgh_q07r2_phase_rotation_context_wiring_fix.verify.log
```

PASS esetén a report végén legyen:

```text
SGH-Q08_STATUS: READY
```
