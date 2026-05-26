# SGH-Q11 — Backend-aware scoring + separator loss path

## Státusz

Implementációs task, SGH-Q10 után.

## Előfeltétel

Kötelező:

```text
codex/reports/egyedi_solver/sgh_q10_collision_backend_policy_production_wiring.md
```

Első sor: `PASS`, és a report végén legyen:

```text
SGH-Q11_STATUS: READY
```

Ha ez nincs meg, állj meg `BLOCKED` reporttal, production kódmódosítás nélkül.

## Miért kell ez?

Q10-ben a `collision_backend` production acceptance gate bekötésre került, de a report helyesen rögzítette:

```text
QUALITY_RISK-Q11:
separator, compress, BPP, explore phases use bbox internally for candidate scoring and move evaluation.
```

Ez azt jelenti, hogy explicit `jagua_polygon_exact` esetén a végső commit gate már exact, de az optimizer belső keresése még bbox-alapú. Így a solver nem tudja kihasználni az irregular/notch geometriát, legfeljebb véletlenül elfogadja a végén.

A Q11 célja: **a kiválasztott collision backend ne csak final acceptance gate legyen, hanem a score/separator/commit döntési útvonalakban is érvényesüljön.**

## Cél

Vezesd végig a `CollisionBackendKind` policyt a PhaseOptimizer belső döntési útvonalain:

```text
PhaseConfig.collision_backend
VrsSeparatorConfig.collision_backend
VrsCollisionTracker backend-aware loss/violation detection
ScoreModel backend-aware scoring helper
MoveExecutor commit gate backend-aware
ExplorationPhase / CompressionPhase / BppPhase backend-aware validation + scoring
```

Kötelező elv:

```text
bbox default változatlan
jagua_polygon_exact explicit opt-in
exact backend esetén bbox false-positive nem irányíthatja el rosszul a searchöt
exact backend Unsupported nem válhat NoCollision-né vagy silent bbox fallbackké
CDE továbbra is Unsupported scaffold
accepted output továbbra is Q10 backend gate-en menjen át
```

## Kapcsolódó gap

```text
F04 — jagua-rs CDE / exact shape collision usage
F06 — separator collision quantification
F07 — GLS weights need real collision pairs
F18 — irregular container / outer_points boundary handling
P06 — no silent downgrade / no proxy hidden as parity
```

## Scope

### Engedélyezett production fájlok

```text
rust/vrs_solver/src/io.rs                         # csak ha output diagnostics bővítés szükséges
rust/vrs_solver/src/adapter.rs                    # collision_backend átadás PhaseConfigbe
rust/vrs_solver/src/optimizer/phase.rs            # PhaseConfig.collision_backend + factory wiring
rust/vrs_solver/src/optimizer/score.rs            # score_with_backend vagy equivalent helper
rust/vrs_solver/src/optimizer/repair.rs           # backend-aware validation helper újrahasznosítása / helper alias
rust/vrs_solver/src/optimizer/separator.rs        # VrsSeparatorConfig + tracker backend-aware loss
rust/vrs_solver/src/optimizer/moves.rs            # MoveExecutor backend-aware commit gate + separator config
rust/vrs_solver/src/optimizer/explore.rs          # separator/scoring/violation path backend-aware
rust/vrs_solver/src/optimizer/compress.rs         # try_result validation/scoring backend-aware
rust/vrs_solver/src/optimizer/bpp_phase.rs        # sheet elimination commit gate backend-aware
rust/vrs_solver/src/optimizer/sheet_elimination.rs # csak ha internal commit gate miatt kell
```

### Engedélyezett artefaktok

```text
canvases/egyedi_solver/sgh_q11_backend_aware_scoring_separator.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q11_backend_aware_scoring_separator.yaml
codex/prompts/egyedi_solver/sgh_q11_backend_aware_scoring_separator/run.md
codex/codex_checklist/egyedi_solver/sgh_q11_backend_aware_scoring_separator.md
codex/reports/egyedi_solver/sgh_q11_backend_aware_scoring_separator.md
codex/reports/egyedi_solver/sgh_q11_backend_aware_scoring_separator.verify.log
docs/egyedi_solver/sgh_q11_backend_aware_scoring_contract.md
```

### Tiltott scope

```text
CDE teljes implementáció
exact backend default bekapcsolása
hole/cavity semantics
DXF/preflight refaktor
új stochastic coordinate descent kereső
új full polygon penetration-depth loss algoritmus
legacy_multisheet default lecserélése
breaking JSON output change
```

## Kötelező pre-audit

Olvasd el és dokumentáld a reportban:

```text
AGENTS.md
docs/codex/overview.md
docs/codex/yaml_schema.md
docs/codex/report_standard.md
docs/qa/testing_guidelines.md
docs/egyedi_solver/sgh_q08_collision_backend_contract.md
docs/egyedi_solver/sgh_q10_collision_backend_policy_contract.md
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

Futtasd és tedd a reportba:

```bash
rg -n "find_violations\(|score\(|VrsSeparatorConfig|MoveExecutor::new|validate_for_commit|validate_and_commit" rust/vrs_solver/src/optimizer rust/vrs_solver/src/adapter.rs
```

A reportban külön válaszold meg:

```text
- mely belső optimizer döntések maradtak bbox-only Q10 után?
- mely pontokon kell CollisionBackendKind átadás?
- exact backend esetén hogyan kezeljük az Unsupported belső keresés közben?
```

## Kötelező implementáció

### 1. PhaseConfig backend policy

Adj `PhaseConfig` mezőt:

```rust
pub collision_backend: CollisionBackendKind
```

Default: `CollisionBackendKind::Bbox`.

Az `adapter::phase_config_from_input(...)` adja át a `resolve_backend_kind(input)` eredményét.

A `PhaseConfig::make_separator_config()` adja tovább a `VrsSeparatorConfig` felé.

### 2. Backend-aware validation helper

Használj vagy hozz létre egy központi helpert, például:

```rust
validate_placements_for_backend(
  placements,
  parts,
  sheets,
  backend_kind,
) -> BackendValidationResult
```

Kötelező:

```text
Bbox -> find_violations-szal azonos
JaguaPolygonExact -> validate_placements_with_backend_checked, no fallback
Cde -> Unsupported
Unsupported belső searchben nem NoCollision; legalább hard penalty / invalid candidate
```

### 3. Backend-aware ScoreModel

Adj `ScoreModel::score_with_backend(...)` vagy equivalent helper-t.

Kötelező:

```text
score(...) régi bbox behavior maradjon változatlan
score_with_backend(..., Bbox) == score(...)
score_with_backend(..., JaguaPolygonExact) exact backend alapján számolja overlap/boundary violation countot
Unsupported esetén explicit unsupported penalty / diagnostic, nem bbox fallback
```

Nem kell full polygon penetration-depth loss. Elfogadható átmeneti stratégia:

```text
exact backend Collision -> violation count + bbox/smooth surrogate magnitude ha kell
exact backend NoCollision -> 0 collision penalty akkor is, ha bbox overlap lenne
exact backend Unsupported -> nagyon magas penalty / invalid candidate
```

### 4. VrsSeparator backend-aware tracker

A `VrsCollisionTracker` ne csak bbox overlapből építse a collision setet, ha config backend exact.

Kötelező:

```text
VrsSeparatorConfig.collision_backend
Bbox -> jelenlegi behavior
JaguaPolygonExact -> pair collision existence backendből
JaguaPolygonExact -> boundary validity backendből
Unsupported -> nem silent fallback; loss > 0, diagnostics/unsupported count ha van
L-shape notch exact esetben ne legyen colliding pair, bbox esetben legyen
```

A loss magnitude lehet továbbra is `LossModelKind` surrogate, de csak backend-confirmed collisionre alkalmazható.

### 5. MoveExecutor + phase modules

Vezesd végig a backend policyt:

```text
MoveExecutor::new_with_rotation_context_and_backend vagy equivalent
commit_gate_ok backend-aware
run_separator_fix backend-aware separator config
ExplorationPhase: separator, sep_score, violations, disruption validation backend-aware
CompressionPhase: try_result validation/scoring backend-aware
BppPhase: commit gate backend-aware
PhaseOptimizer final score backend-aware
```

Bbox esetben ne változzon a viselkedés.

### 6. Dokumentáció

Hozd létre:

```text
docs/egyedi_solver/sgh_q11_backend_aware_scoring_contract.md
```

Tartalmazza:

```text
backend policy propagation map
bbox compatibility statement
exact search semantics
Unsupported handling
known limitations: CDE blocked, no full exact penetration-depth, holes/cavity out of scope
```

## Kötelező tesztek

Minimum:

```text
phase_config_defaults_collision_backend_bbox
adapter_phase_optimizer_passes_collision_backend_to_phase_config
score_with_backend_bbox_matches_legacy_score
score_with_backend_exact_notch_false_positive_removed
separator_tracker_exact_notch_pair_loss_zero_when_bbox_positive
separator_config_backend_default_bbox
move_executor_backend_aware_commit_gate_rejects_exact_unsupported
exploration_phase_uses_backend_aware_validation_for_exact
compression_phase_uses_backend_aware_validation_for_exact
bpp_phase_uses_backend_aware_commit_gate_for_exact
same_seed_same_backend_is_deterministic
explicit_exact_no_silent_bbox_fallback_in_internal_search
```

Ha valamelyik túl nagy integrációs teszt lenne, adj kisebb unit/integration tesztet ugyanarra az invariánsra, de a reportban indokold.

## Acceptance gate

PASS csak akkor lehet, ha:

```text
Q10 report PASS + SGH-Q11_STATUS READY megvan
bbox default tesztek zöldek
exact backendnél L-shape notch false-positive legalább score/separator szinten eltűnik
Unsupported exact geometry nem fallbackel bboxra belső searchben sem
cargo test --lib zöld
full verify zöld
reportban QUALITY_RISK-Q12 szerepel a következő még nyitott pontra
```

PASS esetén a report végén:

```text
SGH-Q12_STATUS: READY
```

Q12 várható témája: exact/CDE provider hardening vagy CDEngine API adaptation audit/pilot, a Q11 eredménye alapján.
