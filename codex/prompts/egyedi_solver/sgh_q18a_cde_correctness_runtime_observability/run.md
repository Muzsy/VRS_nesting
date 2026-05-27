# Runner — SGH-Q18A CDE correctness/runtime observability

Feladat: hajtsd végre a `canvases/egyedi_solver/sgh_q18a_cde_correctness_runtime_observability.md` canvas és a hozzá tartozó goal YAML alapján az SGH-Q18A taskot.

## Dependency gate

Kötelező:

```text
codex/reports/egyedi_solver/sgh_q16_cde_final_commit_gate_consistency_fix.md
```

Első sor: `PASS`, és legyen benne:

```text
SGH-Q18_STATUS: READY
```

Ha nincs, állj meg `BLOCKED` reporttal, production módosítás nélkül.

## Lényeg

Q18A nem CDE cache/session rewrite és nem solver-minőség javítás. Q18A observability task: mérhetővé és bizonyíthatóvá kell tenni, hogy explicit CDE backend esetén a CDE hol, hányszor, milyen eredménnyel és milyen költséggel fut.

Q18B-ről ne dönts előre. A report végén evidencia alapján adj döntést.

## Kötelező bemenetek

Olvasd el:

```text
AGENTS.md
docs/codex/overview.md
docs/codex/yaml_schema.md
docs/codex/report_standard.md
docs/qa/testing_guidelines.md
codex/reports/egyedi_solver/sgh_q16_cde_final_commit_gate_consistency_fix.md
canvases/egyedi_solver/sgh_q18a_cde_correctness_runtime_observability.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q18a_cde_correctness_runtime_observability.yaml
rust/vrs_solver/src/io.rs
rust/vrs_solver/src/adapter.rs
rust/vrs_solver/src/optimizer/working.rs
rust/vrs_solver/src/optimizer/repair.rs
rust/vrs_solver/src/optimizer/collision_backend.rs
rust/vrs_solver/src/optimizer/cde_adapter.rs
rust/vrs_solver/src/optimizer/score.rs
rust/vrs_solver/src/optimizer/separator.rs
rust/vrs_solver/src/optimizer/phase.rs
rust/vrs_solver/src/optimizer/explore.rs
rust/vrs_solver/src/optimizer/compress.rs
rust/vrs_solver/src/optimizer/bpp_phase.rs
```

## Kötelező audit

Futtasd és reportold:

```bash
rg -n "CdeCollisionBackend|CdeAdapter::with_defaults|CDEngine::new|validate_and_commit_with_backend|validate_placements_with_backend_checked|score_with_backend|collision_backend_diagnostics|OptimizerDiagnosticsOutput|PhaseDiagnostics" rust/vrs_solver/src
```

Válaszold meg a reportban:

```text
- Hol épül CDEngine jelenleg?
- Melyik útvonalakon hívódik CDE scoring/separator/validation alatt?
- Hol van final commit CDE bizonyíték Q16 után?
- Milyen diagnosztika hiányzik még a Q18B döntéshez?
```

## Implementációs követelmények

### 1. CDE számlálók

Adj solve-scoped vagy thread-local CDE observability számlálókat legalább ezekre:

```text
cde_pair_queries
cde_boundary_queries
cde_total_queries
cde_engine_builds
cde_collision_results
cde_no_collision_results
cde_unsupported_results
cde_prepare_failures
cde_cross_sheet_skipped_queries vagy hasonló, ha releváns
```

A számlálók fedjék le legalább:

```text
CdeCollisionBackend::placement_overlaps
CdeCollisionBackend::placement_within_sheet
```

Kerüld a sima process-global mutable state-et, mert párhuzamos cargo test alatt flaky lehet. Thread-local vagy explicit solve-scoped megoldás előnyben.

### 2. Output diagnosztika

A meglévő mezők maradjanak:

```text
backend_used
unsupported_queries
bbox_fallback_queries
```

Bővítsd backward-compatible módon, például:

```text
final_commit_backend_used
final_commit_unsupported_queries
final_commit_bbox_fallback_queries
cde_pair_queries
cde_boundary_queries
cde_total_queries
cde_engine_builds
cde_collision_results
cde_no_collision_results
cde_unsupported_results
cde_prepare_failures
cde_observability_scope
```

A pontos név eltérhet, de a reportban dokumentáld.

Explicit CDE backend unsupported output esetén is törekedj arra, hogy a diagnosztika ne vesszen el. Ha ehhez helper kell, például `_unsupported_output_with_collision_backend_diagnostics`, vezess be tisztán és teszteld.

### 3. Runtime/timing

A wall-clock timing nem determinisztikus. Ezért:

```text
- determinisztikus query countok mehetnek normál JSON-ba;
- wall-clock timing csak explicit diagnostics/env módban kerüljön JSON-ba, vagy csak smoke/report logba;
- meglévő determinism tesztek nem regresszálhatnak.
```

Mérendő minimum reportban vagy explicit diagnostics módban:

```text
final_commit_validation_runtime
phase_optimizer_exploration_runtime
phase_optimizer_compression_runtime
phase_optimizer_bpp_runtime
phase_optimizer_final_commit_runtime
legacy_multisheet_cde_final_commit_runtime
```

Elfogadható env flag példa:

```text
VRS_CDE_OBSERVABILITY_TIMING=1
```

### 4. Smoke script

Készíts:

```text
scripts/smoke_sgh_q18a_cde_observability.py
```

A script legalább négy fixture-t futtasson:

```text
1. valid simple rect + collision_backend=cde + legacy_multisheet
2. valid simple rect + collision_backend=cde + optimizer_pipeline=phase_optimizer
3. malformed outer_points + collision_backend=cde -> unsupported
4. bbox false-positive notch fixture + collision_backend=cde
```

Asserteld:

```text
backend_used == "cde_adapter"
final commit backend proof jelen van
bbox_fallback_queries == 0
cde_total_queries > 0 valid CDE esetben
cde_engine_builds > 0 valid CDE esetben
unsupported reason == "CDE_BACKEND_UNSUPPORTED_QUERY" malformed esetben
bbox/default path nem kap CDE runtime számlálókat
```

Timingot csak jelenlétre / pozitív vagy nem negatív formára ellenőrizz explicit diagnostics módban, exact értékre ne.

## Tesztek

Minimum célzott coverage:

```text
cde_observability_counts_pair_and_boundary_queries
cde_observability_reports_engine_builds
cde_observability_reports_no_bbox_fallback
adapter_cde_valid_output_contains_observability_diagnostics
adapter_cde_unsupported_output_preserves_observability_or_documents_blocker
bbox_backend_does_not_emit_cde_observability
cde_observability_does_not_break_existing_q16_tests
```

Futtasd legalább:

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::cde_adapter
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::collision_backend
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::working
cargo test --manifest-path rust/vrs_solver/Cargo.toml adapter
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
python3 scripts/smoke_sgh_q18a_cde_observability.py
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q18a_cde_correctness_runtime_observability.md
```

Ha bármelyik környezeti okból nem fut, a report nem lehet hamis PASS. Dokumentáld pontosan a blokkert.

## Report

A report első sora csak `PASS`, `REVISE` vagy `BLOCKED` lehet.

PASS report tartalmazza:

```text
- dependency gate eredmény;
- pre-audit command összefoglaló;
- módosított fájlok;
- új diagnosztikai mezők listája;
- valid CDE final commit backend proof;
- CDE query/call count evidence;
- unsupported/fallback evidence;
- runtime/per-phase evidence;
- smoke script output summary;
- cargo és verify eredmények;
- Q18B döntési táblázat.
```

PASS report végén legyen:

```text
SGH-Q18A_STATUS: READY_FOR_AUDIT
Q18B_RECOMMENDATION: REQUIRED|NOT_REQUIRED_NOW|INCONCLUSIVE_NEEDS_BIGGER_FIXTURE
```
