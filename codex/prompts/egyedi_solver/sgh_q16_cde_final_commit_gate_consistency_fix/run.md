# Runner — SGH-Q16 CDE final commit gate consistency fix

Feladat: hajtsd végre a `canvases/egyedi_solver/sgh_q16_cde_final_commit_gate_consistency_fix.md` canvas és a hozzá tartozó goal YAML alapján az SGH-Q16 taskot.

## Dependency gate

Kötelező:

```text
codex/reports/egyedi_solver/sgh_q15_cavity_prepack_v2_solver_hole_free_contract.md
```

Első sor: `PASS`, és legyen benne:

```text
SGH-Q16_STATUS: READY
```

Ha nincs, állj meg `BLOCKED` reporttal, production módosítás nélkül.

## Fontos

Q18 diagnostics nem válthatja ki Q16-ot. Előbb a CDE final commit gate legyen konzisztens, utána lehet runtime/call-count observabilityt mérni.

Q16 nem CDE session/cache performance task. Q16 nem hole-aware CDE main solver task. A Q15 `MAIN_SOLVER_MUST_BE_HOLE_FREE` szerződés változatlan.

## Kötelező bemenetek

Olvasd el:

```text
AGENTS.md
docs/codex/overview.md
docs/codex/yaml_schema.md
docs/codex/report_standard.md
docs/qa/testing_guidelines.md
codex/reports/egyedi_solver/sgh_q15_cavity_prepack_v2_solver_hole_free_contract.md
canvases/egyedi_solver/sgh_q16_cde_final_commit_gate_consistency_fix.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q16_cde_final_commit_gate_consistency_fix.yaml
rust/vrs_solver/src/io.rs
rust/vrs_solver/src/adapter.rs
rust/vrs_solver/src/optimizer/working.rs
rust/vrs_solver/src/optimizer/repair.rs
rust/vrs_solver/src/optimizer/collision_backend.rs
rust/vrs_solver/src/optimizer/cde_adapter.rs
rust/vrs_solver/src/optimizer/score.rs
rust/vrs_solver/src/optimizer/separator.rs
rust/vrs_solver/src/optimizer/phase.rs
```

## Kötelező audit

Futtasd és reportold:

```bash
rg -n "validate_and_commit_with_backend|CDE_BACKEND_UNSUPPORTED|CollisionBackendKind::Cde|CdeCollisionBackend|validate_placements_with_backend_checked|validate_placements_for_backend|backend_used|bbox_fallback_queries|unsupported_queries" rust/vrs_solver/src codex docs canvases
```

Válaszold meg a reportban:

```text
- Hol volt még CDE scaffoldként kezelve?
- Hol használ már valós CdeCollisionBackend-et a repo?
- A final commit gate miért volt inkonzisztens?
- A javítás után melyik teszt/output bizonyítja, hogy final commit CDE-vel történt?
```

## Implementációs cél

### WorkingLayout CDE branch

`rust/vrs_solver/src/optimizer/working.rs`:

A `CollisionBackendKind::Cde` branch ne blanket `CDE_BACKEND_UNSUPPORTED` hibát dobjon. Használja a valós `CdeCollisionBackend`-et a checked backend commit pathon:

```text
validate_placements_with_backend_checked(..., &CdeCollisionBackend)
```

Elvárt policy:

```text
unsupported_queries > 0 -> WorkingCommitError::UnsupportedBackend { reason: "CDE_BACKEND_UNSUPPORTED_QUERY", unsupported_queries }
violations non-empty -> WorkingCommitError::Violations(...)
valid -> BackendCommitResult { placements, unplaced, backend_diagnostics }
```

### Diagnostics

Valid explicit CDE case elvárt diagnosztika:

```text
backend_used == "cde_adapter"
unsupported_queries == 0
bbox_fallback_queries == 0
```

### No fallback

CDE final commit alatt tilos:

```text
bbox fallback
JaguaPolygonExact fallback
Unsupported -> NoCollision masquerade
valid simple geometry -> CDE_BACKEND_UNSUPPORTED
```

### Stale kommentek

Frissítsd:

```text
rust/vrs_solver/src/io.rs
rust/vrs_solver/src/optimizer/working.rs
rust/vrs_solver/src/optimizer/collision_backend.rs
```

A dokumentáció legyen pontos:

```text
CDE final commit supported
CDE per-call adapter/session performance not solved here
CDE remains opt-in
CDE remains outer-only in the main solver
```

## Nem cél

Ne csináld most:

```text
Q18A/Q18B observability teljesítése
CDE session/cache rewrite
CDE default bekapcsolása
hole-aware main solver collision
cavity_prepack_v2 módosítás
DXF/preflight refaktor
continuous rotation refinement
shape penalty / smooth loss újraírás
LV8 benchmark gate
```

## Kötelező tesztek

Minimum:

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

Frissítsd a régi blanket unsupported tesztet:

```text
cde_backend_returns_unsupported_not_bbox_fallback
```

Valid simple CDE case-ben többé nem várhat `CDE_BACKEND_UNSUPPORTED` eredményt.

## Verify

Futtasd:

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::working
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::collision_backend
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::cde_adapter
cargo test --manifest-path rust/vrs_solver/Cargo.toml adapter
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q16_cde_final_commit_gate_consistency_fix.md
```

Ha bármelyik fail, report első sora `REVISE` vagy `BLOCKED`, és nincs `SGH-Q18_STATUS: READY`.

## Output

Hozd létre/frissítsd:

```text
canvases/egyedi_solver/sgh_q16_cde_final_commit_gate_consistency_fix.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q16_cde_final_commit_gate_consistency_fix.yaml
codex/prompts/egyedi_solver/sgh_q16_cde_final_commit_gate_consistency_fix/run.md
codex/codex_checklist/egyedi_solver/sgh_q16_cde_final_commit_gate_consistency_fix.md
docs/egyedi_solver/sgh_q16_cde_final_commit_gate_consistency_fix.md
codex/reports/egyedi_solver/sgh_q16_cde_final_commit_gate_consistency_fix.md
codex/reports/egyedi_solver/sgh_q16_cde_final_commit_gate_consistency_fix.verify.log
```

PASS esetén:

```text
első sor: PASS
vége: SGH-Q18_STATUS: READY
```

## Következő lépés PASS után

```text
SGH-Q18A — CDE correctness/runtime observability
```

Q18A csak Q16 PASS után hasznos, mert akkor már a final commit backend is valós CDE útvonalon fut.
