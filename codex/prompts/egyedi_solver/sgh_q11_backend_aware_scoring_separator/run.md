# Runner — SGH-Q11 Backend-aware scoring + separator loss path

Feladat: hajtsd végre a `canvases/egyedi_solver/sgh_q11_backend_aware_scoring_separator.md` canvas és a hozzá tartozó goal YAML alapján az SGH-Q11 taskot.

## Dependency gate

Kötelező:

```text
codex/reports/egyedi_solver/sgh_q10_collision_backend_policy_production_wiring.md
```

Első sor: `PASS`.

A report végén legyen:

```text
SGH-Q11_STATUS: READY
```

Ha nincs, állj meg `BLOCKED` reporttal, production kódmódosítás nélkül.

## Kötelező bemenetek

Olvasd el:

```text
AGENTS.md
docs/codex/overview.md
docs/codex/yaml_schema.md
docs/codex/report_standard.md
docs/qa/testing_guidelines.md
docs/egyedi_solver/sgh_q08_collision_backend_contract.md
docs/egyedi_solver/sgh_q10_collision_backend_policy_contract.md
canvases/egyedi_solver/sgh_q11_backend_aware_scoring_separator.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q11_backend_aware_scoring_separator.yaml
codex/reports/egyedi_solver/sgh_q10_collision_backend_policy_production_wiring.md
rust/vrs_solver/src/adapter.rs
rust/vrs_solver/src/io.rs
rust/vrs_solver/src/optimizer/phase.rs
rust/vrs_solver/src/optimizer/score.rs
rust/vrs_solver/src/optimizer/separator.rs
rust/vrs_solver/src/optimizer/moves.rs
rust/vrs_solver/src/optimizer/explore.rs
rust/vrs_solver/src/optimizer/compress.rs
rust/vrs_solver/src/optimizer/bpp_phase.rs
rust/vrs_solver/src/optimizer/repair.rs
rust/vrs_solver/src/optimizer/collision_backend.rs
```

## Alapprobléma

Q10 után a `collision_backend` már production acceptance policy, de a belső kereső még bbox alapján dönt:

```text
score model
separator loss/colliding_indices
move executor commit gate
exploration/compression/BPP validation gates
```

Explicit `jagua_polygon_exact` esetén ez minőségi plafon: a final gate exact, de a search nem használja az exact geometriát.

## Előzetes audit — kötelező

Futtasd:

```bash
rg -n "find_violations\(|score\(|VrsSeparatorConfig|MoveExecutor::new|validate_for_commit|validate_and_commit" rust/vrs_solver/src/optimizer rust/vrs_solver/src/adapter.rs
```

A reportban írd le:

```text
- Q10 után mely belső utak maradtak bbox-only
- melyik modulban milyen backend policy átadás kell
- exact backend Unsupported hogyan lesz kezelve belső searchben
```

## Implementációs irány

### 1. Backend policy a PhaseConfigben

Add hozzá:

```rust
pub collision_backend: CollisionBackendKind
```

Default: `Bbox`. Az adapter adja át az inputból. A separator config is kapja meg.

### 2. Backend-aware validation + scoring

Legyen központi helper és/vagy `ScoreModel::score_with_backend(...)`.

Elv:

```text
score(...): régi bbox behavior marad
score_with_backend(..., Bbox) == score(...)
score_with_backend(..., JaguaPolygonExact): exact backend violation count alapján dolgozik
Unsupported: explicit penalty / invalid candidate, nem fallback
```

### 3. Separator tracker

A `VrsCollisionTracker` exact backendnél ne bbox overlapből döntse el a colliding pairt.

Minimum elvárt átmeneti stratégia:

```text
backend NoCollision => pair loss 0
backend Collision => loss_model surrogate loss számolható bbox alapján
backend Unsupported => positive hard loss + unsupported counter
```

### 4. Move/phase útvonalak

Vezesd végig a policyt:

```text
MoveExecutor commit_gate_ok
MoveExecutor run_separator_fix
ExplorationPhase separator/scoring/violations/disruption
CompressionPhase try_result validation/scoring
BppPhase commit gate
PhaseOptimizer final score
```

### 5. Tesztek

Kötelező legalább:

```text
phase_config_defaults_collision_backend_bbox
score_with_backend_bbox_matches_legacy_score
score_with_backend_exact_notch_false_positive_removed
separator_tracker_exact_notch_pair_loss_zero_when_bbox_positive
move_executor_backend_aware_commit_gate_rejects_exact_unsupported
exploration_phase_uses_backend_aware_validation_for_exact
compression_phase_uses_backend_aware_validation_for_exact
bpp_phase_uses_backend_aware_commit_gate_for_exact
same_seed_same_backend_is_deterministic
explicit_exact_no_silent_bbox_fallback_in_internal_search
```

A pontos tesztnevek eltérhetnek, de az invariánsokat kötelező fedni.

## Nem cél

Ne csináld most:

```text
CDE teljes implementáció
exact backend default
hole/cavity semantics
full polygon penetration-depth loss
új stochastic coordinate descent
legacy_multisheet default lecserélése
breaking JSON output change
```

## Verify

Futtasd legalább:

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::score
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::separator
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::phase
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::moves
cargo test --manifest-path rust/vrs_solver/Cargo.toml adapter
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q11_backend_aware_scoring_separator.md
```

Ha bármi fail: report első sora `REVISE` vagy `BLOCKED`, és nincs `SGH-Q12_STATUS: READY`.

## Report és checklist

Hozd létre:

```text
codex/codex_checklist/egyedi_solver/sgh_q11_backend_aware_scoring_separator.md
docs/egyedi_solver/sgh_q11_backend_aware_scoring_contract.md
codex/reports/egyedi_solver/sgh_q11_backend_aware_scoring_separator.md
codex/reports/egyedi_solver/sgh_q11_backend_aware_scoring_separator.verify.log
```

PASS esetén report első sora:

```text
PASS
```

PASS esetén report végén:

```text
SGH-Q12_STATUS: READY
```
