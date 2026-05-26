# SGH-Q11R — Backend-aware score consistency + candidate evaluation fix

## Státusz

Javító task az SGH-Q11 után.

## Előfeltétel

Kötelező:

```text
codex/reports/egyedi_solver/sgh_q11_backend_aware_scoring_separator.md
```

Első sor: `PASS`.

Fontos: az SGH-Q11 reportban lévő `SGH-Q12_STATUS: READY` marker **Q11R PASS előtt nem tekinthető érvényes továbbhaladási kapunak**. Q11R supersedes Q11 readiness.

Ha a Q11 report nincs meg vagy nem PASS, állj meg `BLOCKED` reporttal, production kódmódosítás nélkül.

## Miért kell ez?

Külső audit alapján az SGH-Q11 jó irányba vitte a backend-aware commit/validation kapukat, de nem teljesítette teljesen a saját szerződését.

Konkrét blokkolók az aktuális Q11 utáni kódban:

```text
rust/vrs_solver/src/optimizer/phase.rs
- PhaseOptimizer::run() initial_score és final_score még score(), azaz bbox-only.

rust/vrs_solver/src/optimizer/explore.rs
- ExplorationPhase::run() initial_score/incumbent_score még score(), azaz bbox-only.

rust/vrs_solver/src/optimizer/compress.rs
- CompressionPhase::run() initial_score/incumbent_score még score(), azaz bbox-only.

rust/vrs_solver/src/adapter.rs
- output score_breakdown Phase1 esetben még score(), azaz bbox-only.

rust/vrs_solver/src/optimizer/separator.rs
- find_best_candidate_for_target() candidate ranking még bbox-only:
  rect_within_boundary + bbox pair_loss + korai break bbox zero esetén.
  Exact backendnél ez a bbox false-positive alapján elterelheti a searchöt.

rust/vrs_solver/src/optimizer/sheet_elimination.rs
- SheetEliminationEngine nem kap CollisionBackendKind-et.
- separator fallback default Bbox configgel fut.
- internal commit gate validate_for_commit/find_violations bbox-only.
- LBF clear reinsertion bbox overlap alapján elutasíthat exact szerint valid candidate-et.
```

Ez ellentmond a Q11 fő elvének:

```text
jagua_polygon_exact esetén bbox false-positive nem irányíthatja el rosszul a searchöt
exact Unsupported nem válhat NoCollision-né vagy silent bbox fallbackké
```

## Cél

A Q11 backend-aware útvonalat konzisztenssé kell tenni:

```text
1. minden PhaseOptimizer / phase / output score, amely az adott backend policy mellett döntési vagy diagnosztikai érték, score_with_backend(...) útvonalat használjon;
2. separator candidate evaluation exact backend esetén ne bbox-only loss alapján válasszon;
3. BppPhase -> SheetEliminationEngine is kapja meg a CollisionBackendKind-et;
4. SheetEliminationEngine fallback és commit gate backend-aware legyen;
5. bbox default maradjon bit-kompatibilis vagy viselkedés-kompatibilis;
6. exact backend Unsupported továbbra is invalid/hard penalty legyen, soha ne fallback bboxra.
```

## Scope

### Engedélyezett production fájlok

```text
rust/vrs_solver/src/adapter.rs
rust/vrs_solver/src/optimizer/phase.rs
rust/vrs_solver/src/optimizer/explore.rs
rust/vrs_solver/src/optimizer/compress.rs
rust/vrs_solver/src/optimizer/bpp_phase.rs
rust/vrs_solver/src/optimizer/separator.rs
rust/vrs_solver/src/optimizer/sheet_elimination.rs
rust/vrs_solver/src/optimizer/score.rs                 # csak ha helper kell
rust/vrs_solver/src/optimizer/repair.rs                # csak ha helper kell
```

### Engedélyezett artefaktok

```text
canvases/egyedi_solver/sgh_q11r_backend_aware_score_consistency_candidate_fix.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q11r_backend_aware_score_consistency_candidate_fix.yaml
codex/prompts/egyedi_solver/sgh_q11r_backend_aware_score_consistency_candidate_fix/run.md
codex/codex_checklist/egyedi_solver/sgh_q11r_backend_aware_score_consistency_candidate_fix.md
codex/reports/egyedi_solver/sgh_q11r_backend_aware_score_consistency_candidate_fix.md
codex/reports/egyedi_solver/sgh_q11r_backend_aware_score_consistency_candidate_fix.verify.log
docs/egyedi_solver/sgh_q11r_backend_aware_score_consistency_contract.md
```

### Tiltott scope

```text
CDE teljes implementáció
exact backend default bekapcsolása
hole/cavity semantics
DXF/preflight refaktor
új full polygon penetration-depth loss algoritmus
legacy_multisheet default lecserélése
breaking JSON output change
```

## Kötelező pre-audit

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

Futtasd és tedd a reportba:

```bash
rg -n "score\(|score_with_backend|find_violations\(|validate_for_commit|VrsSeparatorConfig|SheetEliminationEngine|new_with_rotation_context|new_with_backend" rust/vrs_solver/src/optimizer rust/vrs_solver/src/adapter.rs
```

A reportban külön írd le:

```text
- pontosan mely Q11 utáni bbox-only döntési / scoring pontokat javítottad;
- mely bbox-only pontok maradtak csak tesztekben vagy legacy/default útvonalon;
- exact backend esetén hol van invalid/hard penalty és hol explicit candidate reject;
- miért nem silent downgrade.
```

## Kötelező implementáció

### 1. PhaseOptimizer score consistency

`PhaseOptimizer::run()` ne használjon bbox-only `score()`-t, ha a config backend nem Bbox.

Kötelező:

```rust
self.score_model.score_with_backend(
  &layout.placements,
  &layout.unplaced,
  parts,
  sheets,
  &self.config.collision_backend,
)
```

Használandó:

```text
initial_score
final_score / result.score
PhaseResult.best_score
PhaseDiagnostics.initial_score / best_score
```

Bbox esetén a viselkedés maradjon azonos.

### 2. ExplorationPhase és CompressionPhase score consistency

`ExplorationPhase::run()` és `CompressionPhase::run()` initial/incumbent score-ja is backend-aware legyen.

Kötelező:

```text
initial_score = score_with_backend(..., config.collision_backend)
incumbent_score ebből induljon
minden későbbi try/sep score ugyanezt a backendet használja
```

Ne legyen olyan exact backend útvonal, ahol a baseline bbox penaltyhez hasonlítunk exact try_score-t.

### 3. Adapter score_breakdown backend consistency

A Phase1 output `score_breakdown` számítása backend-aware legyen:

```text
bbox / missing collision_backend -> régi output változatlan
jagua_polygon_exact -> score_with_backend(..., JaguaPolygonExact)
cde -> explicit unsupported/hard-penalty semantics a már meglévő Q10 policy szerint; ne silent bbox score legyen
```

Ha a final output exact commit gate-en átment, akkor az output score_breakdown ne mutasson bbox false-positive overlap penaltyt.

### 4. Separator candidate evaluation backend-aware

A `VrsSeparator::find_best_candidate_for_target()` jelenlegi bbox-only candidate rankingje nem maradhat exact backendnél.

Minimum elvárt megoldás:

```text
Bbox backend:
  jelenlegi gyors bbox behavior maradjon.

JaguaPolygonExact backend:
  candidate Placementet építs minden jelöltre;
  boundary döntés backend.placement_within_sheet(...);
  pair döntés backend.placement_overlaps(candidate, other) minden releváns másik placementtel;
  NoCollision -> 0 loss;
  Collision -> loss_model surrogate magnitude elfogadható;
  Unsupported -> BACKEND_UNSUPPORTED_* hard loss vagy candidate reject;
  ne legyen korai break kizárólag bbox overlap == 0 alapján, csak backend-evaluated 0 loss esetén.

Cde backend:
  Unsupported/hard loss, ne fogadjon el hamis candidate-et.
```

A cél nem full penetration-depth loss, hanem hogy exact backendnél a bbox false-positive ne vezesse félre a searchöt.

### 5. SheetEliminationEngine backend-aware wiring

Adj `CollisionBackendKind` mezőt a `SheetEliminationEngine`-hez.

Kötelező:

```text
SheetEliminationEngine::new(...) -> Bbox default, backward-compatible
SheetEliminationEngine::new_with_rotation_context(...) -> Bbox default
SheetEliminationEngine::new_with_backend_and_rotation_context(...)
BppPhase::run() ezt használja config.collision_backend-del
```

Javítandó belső pontok:

```text
run() commit gate: find_violations -> validate_placements_for_backend
try_separator_fallback_for_item(): VrsSeparatorConfig.collision_backend = self.collision_backend
try_separator_fallback_for_item(): validate_for_commit/find_violations -> backend-aware validation
lbf_select_clear_reinsert(): exact backend esetén ne csak bbox overlap alapján rejecteljen candidate-et
```

Elfogadható átmeneti stratégia LBF-nél:

```text
Bbox: régi placed_bboxes overlap gyors út.
Exact: candidate placement megépítése után backend-aware check az aktuális base placements ellen.
Unsupported: candidate reject vagy hard invalid, de nem bbox fallback.
```

### 6. Tesztek

Kötelező új vagy javított tesztek legalább ezekre az invariánsokra:

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

A pontos tesztnevek eltérhetnek, de az invariánsokat fedni kell.

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

## Report

Hozd létre:

```text
codex/codex_checklist/egyedi_solver/sgh_q11r_backend_aware_score_consistency_candidate_fix.md
docs/egyedi_solver/sgh_q11r_backend_aware_score_consistency_contract.md
codex/reports/egyedi_solver/sgh_q11r_backend_aware_score_consistency_candidate_fix.md
codex/reports/egyedi_solver/sgh_q11r_backend_aware_score_consistency_candidate_fix.verify.log
```

PASS esetén report első sora:

```text
PASS
```

PASS esetén report végén:

```text
SGH-Q12_STATUS: READY
```

Ettől kezdve a következő task dependency gate-je a Q11R report PASS + `SGH-Q12_STATUS: READY`, nem a régi Q11 report markere.
