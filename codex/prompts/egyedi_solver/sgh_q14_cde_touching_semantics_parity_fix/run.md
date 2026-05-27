# Runner — SGH-Q14 CDE touching semantics parity fix

Feladat: hajtsd végre a `canvases/egyedi_solver/sgh_q14_cde_touching_semantics_parity_fix.md` canvas és a hozzá tartozó goal YAML alapján az SGH-Q14 taskot.

## Dependency gate

Kötelező:

```text
codex/reports/egyedi_solver/sgh_q13_cde_session_backend_search_path_wiring.md
```

Első sor: `PASS`, és legyen benne:

```text
SGH-Q14_STATUS: READY
```

Ha nincs, állj meg `BLOCKED` reporttal, production kódmódosítás nélkül.

## Alapprobléma

Q13 után a CDE backend már search-pathban is használható, de a raw CDE/jagua edge collision touchingot is collisionnek vehet.

A VRS/Q08R policy szerint:

```text
shared edge touch -> NoCollision
shared corner touch -> NoCollision
boundary touch while fully inside -> NoCollision
positive-area overlap -> Collision
proper crossing / outside -> Collision
```

Q14 célja ezt paritybe hozni CDE opt-in mellett is.

## Kötelező audit

Futtasd és reportold:

```bash
rg -n "collides_with|proper_only|touch|Cde|CDE|Edge" rust/vrs_solver/src/optimizer/cde_adapter.rs rust/vrs_solver/src/optimizer/collision_backend.rs ~/.cargo/registry/src -g '*.rs' || true
rg -n "touching|shared edge|shared corner|positive overlap|NoCollision|Collision" rust/vrs_solver/src/optimizer/collision_backend.rs rust/vrs_solver/src/optimizer/cde_adapter.rs
```

A reportban válaszold meg:

```text
- a raw CDE/jagua primitive touchingot collisionnek veszi-e?
- mely VRS-side helper/policy réteg dönt a touching vs positive collision kérdésben?
```

## Implementációs cél

### Pair policy

```text
CDE pair raw decision
  -> VRS touching classification
  -> NoCollision, ha csak shared edge/corner touch
  -> Collision, ha positive overlap / proper crossing
  -> Unsupported, ha geometry unsupported
```

### Boundary policy

```text
fully inside + edge/corner on boundary -> NoCollision
true outside / boundary crossing -> Collision
unsupported geometry -> Unsupported
```

### Separator candidate loss

```text
touching layout -> 0 backend loss
positive overlap -> positive backend loss/collision penalty
unsupported -> sentinel/Unsupported
```

Bbox default és JaguaPolygonExact viselkedés ne regresszáljon.

## Nem cél

Ne csináld most:

```text
CDE default production bekapcsolása
hole/cavity semantics
DXF/preflight refaktor
új optimizer stratégia
LossModel refaktor
RotationPolicy refaktor
BPP/PhaseOptimizer refaktor
CDE session performance rewrite
```

## Kötelező tesztek

Minimum:

```text
cde_touching_rect_edges_are_no_collision
cde_touching_rect_corners_are_no_collision
cde_positive_rect_overlap_is_collision
cde_touching_irregular_polygon_edges_are_no_collision
cde_positive_irregular_overlap_is_collision
cde_item_touching_sheet_boundary_inside_is_no_collision
cde_item_corner_touching_sheet_boundary_inside_is_no_collision
cde_item_crossing_sheet_boundary_is_collision
cde_separator_candidate_loss_touching_layout_is_zero
cde_separator_candidate_loss_positive_overlap_is_positive
bbox_default_touching_semantics_unchanged
jagua_polygon_exact_touching_semantics_unchanged
no_silent_bbox_fallback_for_cde_touching_policy
```

## Verify

Futtasd:

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::cde_adapter
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::collision_backend
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::separator
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::repair
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q14_cde_touching_semantics_parity_fix.md
```

Ha bármelyik fail, report első sora `REVISE` vagy `BLOCKED`, és nincs `SGH-Q15_STATUS: READY`.

## Report

Hozd létre/frissítsd:

```text
docs/egyedi_solver/sgh_q14_cde_touching_semantics_contract.md
codex/codex_checklist/egyedi_solver/sgh_q14_cde_touching_semantics_parity_fix.md
codex/reports/egyedi_solver/sgh_q14_cde_touching_semantics_parity_fix.md
codex/reports/egyedi_solver/sgh_q14_cde_touching_semantics_parity_fix.verify.log
```

PASS esetén:

```text
első sor: PASS
report vége: SGH-Q15_STATUS: READY
```
