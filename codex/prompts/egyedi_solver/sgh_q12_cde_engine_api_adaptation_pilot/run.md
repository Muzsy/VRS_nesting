# Runner — SGH-Q12 CDEngine API adaptation pilot

Feladat: hajtsd végre a `canvases/egyedi_solver/sgh_q12_cde_engine_api_adaptation_pilot.md` canvas és a hozzá tartozó goal YAML alapján az SGH-Q12 taskot.

## Dependency gate

Kötelező:

```text
codex/reports/egyedi_solver/sgh_q11r_backend_aware_score_consistency_candidate_fix.md
```

Első sor: `PASS`, és szerepeljen:

```text
SGH-Q12_STATUS: READY
```

Ha a report törzsében régi REVISE packaging szöveg maradt, de az első sor PASS, az auto-verify blokk PASS, és a duplicate-overlap follow-up tesztek bekerültek, akkor ezt ne blokkold.

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
docs/egyedi_solver/sgh_q11_backend_aware_scoring_contract.md
docs/egyedi_solver/sgh_q11r_backend_aware_score_consistency_contract.md
canvases/egyedi_solver/sgh_q12_cde_engine_api_adaptation_pilot.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q12_cde_engine_api_adaptation_pilot.yaml
rust/vrs_solver/src/optimizer/collision_backend.rs
rust/vrs_solver/src/optimizer/geometry_preprocessing.rs
rust/vrs_solver/Cargo.toml
```

## Cél

Derítsd ki és pilotold, hogy a VRS-ben a `collision_backend: "cde"` lehet-e valódi jagua-rs CDE adapter, vagy jelenleg csak explicit Unsupported blocker maradhat.

Tilos CDE néven bbox vagy JaguaPolygonExact fallbacket használni.

## Kötelező API audit

Futtasd és reportold:

```bash
cargo tree --manifest-path rust/vrs_solver/Cargo.toml | rg "jagua|cde|collision|spolygon"
rg -n "CDEngine|CDE|CollisionDetection|collision_detection|OriginalShape|SPolygon|Surrogate|Hazard|hazard|collides_with|CollidesWith" \
  ~/.cargo/registry/src rust -g '*.rs' || true
```

A reportban legyen:

```text
Symbol/API | Path | Visibility | Usable from vrs_solver? | Notes
```

## Implementáció

Hozz létre:

```text
rust/vrs_solver/src/optimizer/cde_adapter.rs
```

vagy repo-stílusú ekvivalenst.

Minimum contract:

```text
CdeAdapterConfig
CdePreparedShape / CdeQueryInput / CdeQueryResult vagy ekvivalens
Unsupported { reason }
no jagua-rs type leakage public optimizer API-ba
```

Ha a valódi CDE API használható:

```text
CdeCollisionBackend -> CdeAdapter -> valódi CDE query
rect overlap / rotated rect / irregular outer polygon / boundary tests
```

Ha nem használható:

```text
CdeCollisionBackend marad Unsupported
reason: CDE_API_UNAVAILABLE vagy pontos lifecycle/API blocker
no bbox fallback
no JaguaPolygonExact fallback
contract + report egyértelműen PARTIAL/BLOCKED státuszt ír
```

## Kötelező tesztek

Minimum:

```text
cde_api_audit_report_contains_resolved_symbols
cde_backend_does_not_fallback_to_bbox_when_unavailable
cde_backend_does_not_fallback_to_jagua_polygon_exact_when_unavailable
cde_adapter_returns_unsupported_with_clear_reason_if_api_unavailable
cde_backend_rect_overlap_query_works_or_is_blocked_explicitly
cde_backend_rotated_rect_query_works_or_is_blocked_explicitly
cde_backend_irregular_polygon_query_works_or_is_blocked_explicitly
cde_backend_invalid_geometry_is_unsupported_not_no_collision
```

## Verify

Futtasd:

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::cde_adapter
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::collision_backend
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::geometry_preprocessing
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q12_cde_engine_api_adaptation_pilot.md
```

Ha bármi fail: report első sora `REVISE` vagy `BLOCKED`.

## Report

Hozd létre/frissítsd:

```text
codex/codex_checklist/egyedi_solver/sgh_q12_cde_engine_api_adaptation_pilot.md
docs/egyedi_solver/sgh_q12_cde_engine_adapter_contract.md
codex/reports/egyedi_solver/sgh_q12_cde_engine_api_adaptation_pilot.md
codex/reports/egyedi_solver/sgh_q12_cde_engine_api_adaptation_pilot.verify.log
```

PASS csak akkor lehet, ha nincs hamis CDE állítás és nincs silent fallback.

A report végén csak akkor legyen:

```text
SGH-Q13_STATUS: READY
```

ha Q12 saját acceptance gate-je teljesült és a következő lépés egyértelmű.
