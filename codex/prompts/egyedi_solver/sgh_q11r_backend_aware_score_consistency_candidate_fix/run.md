# Runner — SGH-Q11R Backend-aware score consistency + candidate evaluation fix

Feladat: hajtsd végre a `canvases/egyedi_solver/sgh_q11r_backend_aware_score_consistency_candidate_fix.md` canvas és a hozzá tartozó goal YAML alapján az SGH-Q11R javító taskot.

## Dependency gate

Kötelező:

```text
codex/reports/egyedi_solver/sgh_q11_backend_aware_scoring_separator.md
```

Első sor: `PASS`.

A Q11 reportban lévő `SGH-Q12_STATUS: READY` marker Q11R PASS előtt nem érvényes. Q11R felülírja a továbbhaladási kaput.

Ha a Q11 report nincs meg vagy nem PASS: report első sora `BLOCKED`, production kódmódosítás nélkül.

## Kötelező bemenetek

Olvasd el:

```text
AGENTS.md
docs/codex/overview.md
docs/codex/yaml_schema.md
docs/codex/report_standard.md
docs/qa/testing_guidelines.md
canvases/egyedi_solver/sgh_q11_backend_aware_scoring_separator.md
codex/reports/egyedi_solver/sgh_q11_backend_aware_scoring_separator.md
docs/egyedi_solver/sgh_q11_backend_aware_scoring_contract.md
canvases/egyedi_solver/sgh_q11r_backend_aware_score_consistency_candidate_fix.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q11r_backend_aware_score_consistency_candidate_fix.yaml
rust/vrs_solver/src/adapter.rs
rust/vrs_solver/src/optimizer/phase.rs
rust/vrs_solver/src/optimizer/explore.rs
rust/vrs_solver/src/optimizer/compress.rs
rust/vrs_solver/src/optimizer/bpp_phase.rs
rust/vrs_solver/src/optimizer/separator.rs
rust/vrs_solver/src/optimizer/sheet_elimination.rs
rust/vrs_solver/src/optimizer/score.rs
rust/vrs_solver/src/optimizer/repair.rs
rust/vrs_solver/src/optimizer/collision_backend.rs
```

## Probléma

SGH-Q11 után a backend-aware commit/validation több ponton megvan, de a döntési és score path nem teljesen konzisztens:

```text
phase.rs: PhaseOptimizer initial/final score bbox-only
explore.rs: ExplorationPhase initial/incumbent score bbox-only
compress.rs: CompressionPhase initial/incumbent score bbox-only
adapter.rs: Phase1 score_breakdown bbox-only
separator.rs: find_best_candidate_for_target candidate ranking bbox-only
sheet_elimination.rs: SheetEliminationEngine backend nélküli, fallback/commit/LBF bbox-only
```

Ez exact backend mellett minőségi hiba: a bbox false-positive továbbra is elterelheti a searchöt, vagy félrevezető score-t adhat.

## Kötelező audit

Futtasd:

```bash
rg -n "score\(|score_with_backend|find_violations\(|validate_for_commit|VrsSeparatorConfig|SheetEliminationEngine|new_with_rotation_context|new_with_backend" rust/vrs_solver/src/optimizer rust/vrs_solver/src/adapter.rs
```

A reportba írd be a javítás előtti és utáni állapotot.

## Javítási követelmények

### 1. Score consistency

Használj `score_with_backend(..., &config.collision_backend)` hívást minden Q11R-scope döntési/diagnosztikai score helyen:

```text
PhaseOptimizer::run initial_score/final_score/result.score
ExplorationPhase::run initial_score/incumbent_score
CompressionPhase::run initial_score/incumbent_score
adapter Phase1 score_breakdown
```

Bbox esetén maradjon ugyanaz az eredmény, mint a régi score().

### 2. Separator exact candidate evaluation

`VrsSeparator::find_best_candidate_for_target()` exact backendnél ne csak bbox overlapből rangsoroljon.

Elvárt:

```text
candidate Placement megépítése
backend boundary check
backend pair checks a többi placement ellen
NoCollision -> 0
Collision -> bbox/smooth surrogate magnitude elfogadható
Unsupported -> hard loss vagy reject
nincs bbox-only korai break
```

### 3. Sheet elimination backend wiring

`SheetEliminationEngine` kapjon `CollisionBackendKind` mezőt és konstruktort:

```text
new -> Bbox
new_with_rotation_context -> Bbox
new_with_backend_and_rotation_context -> explicit backend
```

`BppPhase::run()` ezt használja `config.collision_backend`-del.

Javítandó:

```text
run() commit gate
try_separator_fallback_for_item() VrsSeparatorConfig
try_separator_fallback_for_item() validation
lbf_select_clear_reinsert exact candidate validation
```

### 4. No downgrade

Tilos:

```text
Unsupported -> NoCollision
Unsupported -> silent bbox fallback
exact backend output score_breakdown bbox false-positive overlap penaltyvel
CDE hamis siker
```

## Tesztek

Adj vagy javíts teszteket legalább ezekre:

```text
phase_optimizer_score_uses_backend_for_exact_notch
adapter_score_breakdown_uses_selected_backend
exploration_initial_score_uses_backend
compression_initial_score_uses_backend
separator_exact_candidate_selection_ignores_bbox_false_positive
sheet_elimination_engine_passes_backend_to_separator_fallback
sheet_elimination_exact_commit_gate_no_silent_bbox_fallback
bbox_default_still_matches_legacy_score
cde_internal_paths_reject_or_hard_penalty_no_silent_success
```

A név eltérhet, az invariáns nem.

## Verify

Futtasd legalább:

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::phase
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::explore
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::compress
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::separator
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::sheet_elimination
cargo test --manifest-path rust/vrs_solver/Cargo.toml adapter
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q11r_backend_aware_score_consistency_candidate_fix.md
```

Ha bármi fail: report első sora `REVISE` vagy `BLOCKED`, és nincs `SGH-Q12_STATUS: READY`.

## Kimenetek

Hozd létre:

```text
codex/codex_checklist/egyedi_solver/sgh_q11r_backend_aware_score_consistency_candidate_fix.md
docs/egyedi_solver/sgh_q11r_backend_aware_score_consistency_contract.md
codex/reports/egyedi_solver/sgh_q11r_backend_aware_score_consistency_candidate_fix.md
codex/reports/egyedi_solver/sgh_q11r_backend_aware_score_consistency_candidate_fix.verify.log
```

PASS esetén:

```text
PASS
...
SGH-Q12_STATUS: READY
```
