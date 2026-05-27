# SGH-Q16 — CDE final commit gate consistency fix

## Státusz

Next mandatory task after SGH-Q15. Q18 diagnostics nem válthatja ki ezt a javítást: amíg a CDE végső commit gate nem működik, addig bármely CDE runtime mérés csak egy félig bekötött production pathot mérne.

## Előfeltétel

Kötelező:

```text
codex/reports/egyedi_solver/sgh_q15_cavity_prepack_v2_solver_hole_free_contract.md
```

Első sor: `PASS`, és a report végén legyen:

```text
SGH-Q16_STATUS: READY
```

Ha nincs, állj meg `BLOCKED` reporttal, production kódmódosítás nélkül.

## Miért kell?

A jelenlegi repo állapotban a CDE backend már nem csak fantom:

```text
rust/vrs_solver/src/optimizer/cde_adapter.rs
rust/vrs_solver/src/optimizer/collision_backend.rs
rust/vrs_solver/src/optimizer/repair.rs
rust/vrs_solver/src/optimizer/score.rs
rust/vrs_solver/src/optimizer/separator.rs
rust/vrs_solver/src/optimizer/phase.rs
```

A CDE útvonal több helyen valós query backendként létezik. Viszont a final acceptance gate még ellentmond ennek:

```rust
WorkingLayout::validate_and_commit_with_backend(..., CollisionBackendKind::Cde)
  -> Err(UnsupportedBackend { reason: "CDE_BACKEND_UNSUPPORTED", ... })
```

Ez production blocker. A solver nem lehet CDE-ready, ha a final `WorkingLayout` commit gate CDE esetén mindig unsupported.

## Cél

Q16 célja:

```text
CDE final commit gate consistency
```

Konkrétan:

1. `WorkingLayout::validate_and_commit_with_backend(CollisionBackendKind::Cde)` a valós `CdeCollisionBackend`-et használja.
2. Valid CDE layout esetén a commit sikeres legyen.
3. A commit eredmény tartalmazza:

```text
backend_diagnostics.backend_name == "cde_adapter"
unsupported_queries == 0
bbox_fallback_queries == 0
```

4. Unsupported CDE query esetén explicit `WorkingCommitError::UnsupportedBackend` legyen.
5. Collision/boundary violation esetén `WorkingCommitError::Violations` legyen.
6. Sehol ne legyen silent bbox fallback CDE final commit alatt.
7. A legacy/default bbox útvonal változatlan maradjon.
8. `JaguaPolygonExact` viselkedés ne regresszáljon.
9. Stale dokumentáció és teszt, amely szerint CDE final commit mindig unsupported, frissüljön.

## Nem cél

Ne csináld most:

```text
CDE session/cache performance rewrite
Q18A/Q18B runtime observability teljesítése
CDE default backend bekapcsolása
hole-aware CDE collision a main solverben
cavity_prepack_v2 módosítása
DXF/preflight refaktor
smooth collision severity újraírás
shape-based loss/penalty újraírás
continuous rotation refinement
move_items_multi / multi-worker stratégia
benchmark gate / LV8 acceptance suite
```

Q16 csak a final commit gate inkonzisztenciát javítja.

## Fontos architekturális korlát

A Q15 contract változatlan:

```text
MAIN_SOLVER_MUST_BE_HOLE_FREE
```

CDE itt outer-only part/sheet validation backend. Q16 nem jelent hole-aware main solver támogatást. Ha hole-os part jutna a Phase1 fő solverbe, az továbbra is unsupported/pipeline-level blokk maradjon a meglévő policy szerint.

## Repo evidence, amit ellenőrizni kell

Keresd és olvasd:

```text
rust/vrs_solver/src/io.rs
rust/vrs_solver/src/adapter.rs
rust/vrs_solver/src/optimizer/working.rs
rust/vrs_solver/src/optimizer/repair.rs
rust/vrs_solver/src/optimizer/collision_backend.rs
rust/vrs_solver/src/optimizer/cde_adapter.rs
rust/vrs_solver/src/optimizer/score.rs
rust/vrs_solver/src/optimizer/separator.rs
rust/vrs_solver/src/optimizer/phase.rs
codex/reports/egyedi_solver/sgh_q15_cavity_prepack_v2_solver_hole_free_contract.md
```

Kötelező audit parancs:

```bash
rg -n "validate_and_commit_with_backend|CDE_BACKEND_UNSUPPORTED|CollisionBackendKind::Cde|CdeCollisionBackend|validate_placements_with_backend_checked|validate_placements_for_backend|backend_used|bbox_fallback_queries|unsupported_queries" rust/vrs_solver/src codex docs canvases
```

A reportban explicit válaszold meg:

```text
- Hol volt még CDE scaffoldként kezelve?
- Hol használ már valós CdeCollisionBackend-et a repo?
- A final commit gate miért volt inkonzisztens?
- A javítás után melyik útvonal bizonyítja, hogy final commit CDE-vel történt?
```

## Engedélyezett production fájlok

Elsődleges:

```text
rust/vrs_solver/src/optimizer/working.rs
rust/vrs_solver/src/io.rs
rust/vrs_solver/src/adapter.rs
```

Szükség esetén, de csak célzottan:

```text
rust/vrs_solver/src/optimizer/repair.rs
rust/vrs_solver/src/optimizer/collision_backend.rs
rust/vrs_solver/src/optimizer/cde_adapter.rs
rust/vrs_solver/src/optimizer/score.rs
rust/vrs_solver/src/optimizer/separator.rs
rust/vrs_solver/src/optimizer/phase.rs
```

Tesztek:

```text
rust/vrs_solver/src/optimizer/working.rs
rust/vrs_solver/src/adapter.rs
rust/vrs_solver/src/optimizer/cde_adapter.rs
rust/vrs_solver/src/optimizer/collision_backend.rs
```

Dokumentáció/report:

```text
canvases/egyedi_solver/sgh_q16_cde_final_commit_gate_consistency_fix.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q16_cde_final_commit_gate_consistency_fix.yaml
codex/prompts/egyedi_solver/sgh_q16_cde_final_commit_gate_consistency_fix/run.md
codex/codex_checklist/egyedi_solver/sgh_q16_cde_final_commit_gate_consistency_fix.md
docs/egyedi_solver/sgh_q16_cde_final_commit_gate_consistency_fix.md
codex/reports/egyedi_solver/sgh_q16_cde_final_commit_gate_consistency_fix.md
codex/reports/egyedi_solver/sgh_q16_cde_final_commit_gate_consistency_fix.verify.log
```

## Kötelező implementáció

### 1. WorkingLayout CDE branch javítása

`rust/vrs_solver/src/optimizer/working.rs`:

A CDE branch ne ezt csinálja:

```rust
CollisionBackendKind::Cde => Err(WorkingCommitError::UnsupportedBackend {
    reason: "CDE_BACKEND_UNSUPPORTED".to_string(),
    unsupported_queries: placement_count,
})
```

Hanem ugyanazt a checked backend pattern-t kövesse, mint `JaguaPolygonExact`, csak `CdeCollisionBackend`-del:

```text
validate_placements_with_backend_checked(
  &self.placements,
  parts,
  sheets,
  &CdeCollisionBackend,
)
```

Policy:

```text
unsupported_queries > 0 -> UnsupportedBackend { reason: "CDE_BACKEND_UNSUPPORTED_QUERY", unsupported_queries }
violations non-empty -> WorkingCommitError::Violations(...)
valid -> BackendCommitResult { placements, unplaced, diagnostics }
```

A `backend_diagnostics.backend_name` a backend `name()` értéke legyen, jelenleg várhatóan:

```text
cde_adapter
```

### 2. Közös helper megengedett

Ha a `JaguaPolygonExact` és `Cde` branch duplikálna sok kódot, megengedett egy privát helper bevezetése `working.rs`-ben:

```rust
fn validate_checked_backend_commit(
    self,
    parts: &[Part],
    sheets: &[SheetShape],
    backend: &dyn CollisionBackend,
    unsupported_reason: &str,
) -> Result<BackendCommitResult, WorkingCommitError>
```

De ne refaktoráld túl a modult. A feladat célja a CDE commit gate fix, nem általános optimizer áttervezés.

### 3. Stale kommentek frissítése

Frissítsd legalább:

```text
rust/vrs_solver/src/io.rs
- "Explicit cde: always Unsupported (scaffold only)."

rust/vrs_solver/src/optimizer/working.rs
- "Cde: always returns UnsupportedBackend"

rust/vrs_solver/src/optimizer/collision_backend.rs
- ha még scaffold/BLOCKED komment maradt, pontosítsd: per-call pilot implementation, final commit supported, session/cache later.
```

A dokumentáció legyen őszinte:

```text
CDE final commit supported
CDE per-call adapter/session performance not solved here
CDE remains opt-in
CDE remains outer-only in main solver
```

### 4. Adapter output viselkedés

Explicit CDE backend + valid simple layout esetén a solver output ne legyen `unsupported` pusztán azért, mert CDE backend lett választva.

Elvárt:

```text
status == "ok" vagy a meglévő valid status semantics szerint sikeres/partial
unsupported_reason == None
collision_backend_diagnostics.backend_used == "cde_adapter"
collision_backend_diagnostics.unsupported_queries == 0
collision_backend_diagnostics.bbox_fallback_queries == 0
```

Ha a layout valós CDE collisiont vagy boundary violationt tartalmaz, továbbra is fail/unsupported legyen commit violation reasonnel.

### 5. Unsupported geometry policy

Malformed/degenerate exact geometry esetén CDE ne fallbackeljen bboxra.

Elvárt:

```text
status == "unsupported"
unsupported_reason == "CDE_BACKEND_UNSUPPORTED_QUERY" vagy célzottabb, stabil CDE unsupported reason
placements == []
collision_backend_diagnostics ne hazudja azt, hogy bbox futott
```

A reason lehet stabilizáltabb, de ne legyen többé a blanket `CDE_BACKEND_UNSUPPORTED`, kivéve ha tényleg API/runtime-level CDE nincs elérhető.

## Kötelező tesztek

Minimum Rust tesztek:

```text
working_cde_valid_layout_commits_successfully
working_cde_valid_layout_reports_cde_adapter_backend
working_cde_positive_overlap_rejects_with_violation
working_cde_boundary_violation_rejects_with_violation
working_cde_unsupported_geometry_rejects_without_bbox_fallback
adapter_cde_backend_valid_simple_case_is_not_unsupported
adapter_cde_backend_valid_simple_case_reports_cde_diagnostics
adapter_cde_backend_invalid_geometry_returns_unsupported_not_bbox_fallback
adapter_cde_backend_does_not_return_legacy_cde_backend_unsupported_for_valid_case
bbox_default_commit_behavior_unchanged
jagua_polygon_exact_commit_behavior_unchanged
```

A meglévő tesztet, amely blanket unsupportedot vár CDE esetén, frissíteni kell:

```text
cde_backend_returns_unsupported_not_bbox_fallback
```

Ez Q16 után csak malformed/unsupported geometry esetén várhat unsupportedot, valid simple geometry esetén nem.

## Kötelező verify

Futtasd és reportold:

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::working
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::collision_backend
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::cde_adapter
cargo test --manifest-path rust/vrs_solver/Cargo.toml adapter
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q16_cde_final_commit_gate_consistency_fix.md
```

Ha van repo-standard teljes verify script, azt is futtasd.

## Acceptance gate

PASS csak akkor lehet, ha mind igaz:

```text
1. Q15 dependency PASS + SGH-Q16_STATUS: READY megvan.
2. CDE final commit valid layoutnál sikeres.
3. CDE final commit collision/boundary violationnél rejectel.
4. CDE final commit unsupported geometrynél UnsupportedBackend-et ad.
5. CDE final commit alatt bbox_fallback_queries == 0.
6. Solver output valid explicit CDE case-ben nem blanket unsupported.
7. `CDE_BACKEND_UNSUPPORTED` már nem valid simple case eredménye.
8. Bbox default behavior unchanged.
9. JaguaPolygonExact behavior unchanged.
10. Rust célzott tesztek és `cargo test --lib` zöld.
11. Report első sora `PASS`, végén `SGH-Q18_STATUS: READY`.
```

Ha bármelyik nem teljesül:

```text
első sor: REVISE vagy BLOCKED
nincs SGH-Q18_STATUS: READY
```

## Report kötelező tartalom

A report tartalmazza:

```text
- első sor: PASS / REVISE / BLOCKED
- dependency gate eredménye
- pre-audit találatok
- pontos módosított fájlok
- CDE branch előtte/utána összefoglaló
- valid CDE final commit bizonyíték
- unsupported geometry bizonyíték
- bbox_fallback_queries == 0 bizonyíték
- legacy bbox és JaguaPolygonExact non-regression bizonyíték
- lefuttatott tesztek pontos parancs + eredmény
- fennmaradó kockázat: CDE per-call/session performance nincs megoldva, Q18A következik
- záró marker: SGH-Q18_STATUS: READY csak PASS esetén
```

## Következő task

PASS után ne Q19 jöjjön, hanem:

```text
SGH-Q18A — CDE correctness/runtime observability
```

Q18A fókusz:

```text
backend_used mezők
CDE query/call count
unsupported count
fallback count
validation failure okok
per-phase runtime
final commit backend bizonyítása
```

Q18B session/cache csak akkor következzen, ha Q18A mérései szerint a per-call adapter érdemi bottleneck.
