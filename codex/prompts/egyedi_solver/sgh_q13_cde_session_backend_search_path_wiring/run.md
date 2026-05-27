# Runner — SGH-Q13 CDE session backend + search-path wiring

Feladat: hajtsd végre a `canvases/egyedi_solver/sgh_q13_cde_session_backend_search_path_wiring.md` canvas és a hozzá tartozó goal YAML alapján az SGH-Q13 taskot.

## Dependency gate

Kötelező:

```text
codex/reports/egyedi_solver/sgh_q12_cde_engine_api_adaptation_pilot.md
```

Első sor: `PASS`, és legyen benne:

```text
SGH-Q13_STATUS: READY
```

Ha nincs, állj meg `BLOCKED` reporttal, production kódmódosítás nélkül.

## Alapprobléma

Q12 valós CDE adaptert adott, de per-call engine builddel. Emellett a search pathban még lehetnek CDE sentinel maradványok:

```text
compute_backend_decisions(Cde) -> all Unsupported
candidate_backend_loss(Cde) -> f64::MAX
```

Q13 célja, hogy a CDE opt-in ne csak final validation backend legyen, hanem a separator/search útvonalban is tényleges CDE döntést használjon, és közben őszintén dokumentálja, hogy full session-owned CDEEngine megvalósítható-e most.

## Kötelező audit

Futtasd és reportold:

```bash
rg -n "trait.*Filter|struct.*Filter|impl.*Filter|NoFilter|HazardEntity|PlacedItem|PItemKey|SlotMap|CDEngine" ~/.cargo/registry/src rust -g '*.rs' || true
rg -n "CollisionBackendKind::Cde|candidate_backend_loss|compute_backend_decisions|BACKEND_UNSUPPORTED" rust/vrs_solver/src/optimizer/separator.rs
```

A reportban válaszold meg:

```text
lehetséges-e self-hazard filter egy session-owned CDEEngine-ben?
ha nem, miért marad PerCallOnly vagy QueryBatch?
```

## Implementációs cél

1. `cde_session.rs` vagy ekvivalens lifecycle contract:

```text
CdeSessionCapability::FullSession | QueryBatch | PerCallOnly { reason }
```

Ne fake-elj sessiont, ha az API nem engedi.

2. Separator CDE wiring:

```text
compute_backend_decisions(Cde) -> CdeCollisionBackend döntések
candidate_backend_loss(Cde) -> CdeCollisionBackend döntések
```

3. Diagnostics:

```text
cde_queries
cde_engine_builds
cde_unsupported_count
cde_session_capability
```

4. No default switch:

```text
bbox default marad
cde explicit opt-in
nincs bbox fallback cde néven
```

## Nem cél

```text
production default CDE
hole/cavity semantics
DXF/preflight
Sparrow teljes port
új optimizer stratégia
```

## Kötelező tesztek

Minimum:

```text
cde_tracker_build_uses_cde_backend_not_all_unsupported
cde_separator_candidate_backend_loss_is_not_always_max
cde_separator_repairs_simple_overlap_or_reports_real_unsupported
cde_phase_optimizer_valid_rect_fixture_has_no_backend_unsupported
cde_score_with_backend_matches_validation_for_valid_rects
cde_session_capability_reports_truthful_lifecycle_status
cde_session_or_batch_matches_per_call_adapter_for_pair_matrix
bbox_default_still_matches_pre_q13_behavior
jagua_polygon_exact_path_unchanged
no_silent_bbox_fallback_for_cde_search_path
```

## Verify

Futtasd:

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::cde_adapter
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::cde_session
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::collision_backend
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::separator
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::phase
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::score
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q13_cde_session_backend_search_path_wiring.md
```

Ha bármelyik fail, report első sora `REVISE` vagy `BLOCKED`, és nincs `SGH-Q14_STATUS: READY`.

## Output

Hozd létre/frissítsd:

```text
codex/codex_checklist/egyedi_solver/sgh_q13_cde_session_backend_search_path_wiring.md
docs/egyedi_solver/sgh_q13_cde_session_backend_contract.md
codex/reports/egyedi_solver/sgh_q13_cde_session_backend_search_path_wiring.md
codex/reports/egyedi_solver/sgh_q13_cde_session_backend_search_path_wiring.verify.log
```

PASS esetén a report végén legyen:

```text
SGH-Q14_STATUS: READY
```
