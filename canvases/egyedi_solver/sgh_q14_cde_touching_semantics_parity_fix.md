# SGH-Q14 — CDE touching semantics parity fix

## Státusz

Implementation / repair task SGH-Q13 után.

## Előfeltétel

Kötelező:

```text
codex/reports/egyedi_solver/sgh_q13_cde_session_backend_search_path_wiring.md
```

Első sor: `PASS`, és legyen benne:

```text
SGH-Q14_STATUS: READY
```

Ha nincs meg, állj meg `BLOCKED` reporttal, production kódmódosítás nélkül.

## Miért kell?

SGH-Q13 után a CDE backend már ténylegesen részt vesz a separator/search útvonalban:

```text
compute_backend_decisions(Cde) -> CDE döntések
candidate_backend_loss(Cde) -> nem automatikus f64::MAX
```

A Q13 report/contract viszont nyitva hagyta a CDE touching policy problémát:

```text
CDE uses Edge::collides_with(proper_only=false)
```

Ez potenciálisan túl szigorú, mert a gyártási nestingben az alábbiak nem számítanak ütközésnek:

```text
két alkatrész közös élen érintkezik -> NoCollision
két alkatrész közös pontban érintkezik -> NoCollision
alkatrész pontosan a sheet boundaryn belül érinti a sheet szélét -> NoCollision
```

Ütközésnek csak a valódi pozitív területű overlap, valódi crossing vagy sheeten kívülre lógás számítson.

## Cél

A Q14 célja: a CDE backend touching semantics legyen parityben a Q08R exact policyval és a bbox default policyval.

Kötelező viselkedés:

```text
CDE item-item:
- shared edge touch -> NoCollision
- shared corner touch -> NoCollision
- positive-area overlap -> Collision
- true crossing -> Collision

CDE item-sheet boundary:
- item edge exactly on sheet boundary, fully inside -> NoCollision
- item corner on sheet boundary, fully inside -> NoCollision
- true outside / crossing boundary -> Collision
```

A Q14 nem új CDE session/lifecycle task. Nem cél a CDE teljesítmény optimalizálása, nem cél hole/cavity semantics, és nem cél CDE defaulttá tétele.

## Scope

### Engedélyezett production fájlok

```text
rust/vrs_solver/src/optimizer/cde_adapter.rs
rust/vrs_solver/src/optimizer/collision_backend.rs
rust/vrs_solver/src/optimizer/cde_session.rs          # csak ha diagnostics/capability érintett
rust/vrs_solver/src/geometry.rs                       # csak segment/touch helper esetén
rust/vrs_solver/src/optimizer/repair.rs               # csak backend-aware validation helperhez, ha szükséges
```

### Engedélyezett artefaktok

```text
canvases/egyedi_solver/sgh_q14_cde_touching_semantics_parity_fix.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q14_cde_touching_semantics_parity_fix.yaml
codex/prompts/egyedi_solver/sgh_q14_cde_touching_semantics_parity_fix/run.md
codex/codex_checklist/egyedi_solver/sgh_q14_cde_touching_semantics_parity_fix.md
codex/reports/egyedi_solver/sgh_q14_cde_touching_semantics_parity_fix.md
codex/reports/egyedi_solver/sgh_q14_cde_touching_semantics_parity_fix.verify.log
docs/egyedi_solver/sgh_q14_cde_touching_semantics_contract.md
```

### Tiltott scope

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

## Kötelező pre-audit

Olvasd el:

```text
AGENTS.md
docs/codex/overview.md
docs/codex/yaml_schema.md
docs/codex/report_standard.md
docs/qa/testing_guidelines.md
docs/egyedi_solver/sgh_q08_collision_backend_contract.md
docs/egyedi_solver/sgh_q13_cde_session_backend_contract.md
codex/reports/egyedi_solver/sgh_q13_cde_session_backend_search_path_wiring.md
rust/vrs_solver/src/optimizer/cde_adapter.rs
rust/vrs_solver/src/optimizer/collision_backend.rs
rust/vrs_solver/src/optimizer/repair.rs
```

Futtasd és dokumentáld:

```bash
rg -n "collides_with|proper_only|touch|Cde|CDE|Edge" rust/vrs_solver/src/optimizer/cde_adapter.rs rust/vrs_solver/src/optimizer/collision_backend.rs ~/.cargo/registry/src -g '*.rs' || true
rg -n "touching|shared edge|shared corner|positive overlap|NoCollision|Collision" rust/vrs_solver/src/optimizer/collision_backend.rs rust/vrs_solver/src/optimizer/cde_adapter.rs
```

A reportban külön válaszold meg:

```text
- a jagua-rs/CDE primitive touchingot collisionnek veszi-e?
- hol kell VRS-side policy réteget tenni?
- a Q08R JaguaPolygonExact policyhoz képest mi változik?
```

## Kötelező implementációs irány

### 1. Explicit segment/touch classification helper

Ha a CDE / jagua edge query touchingot collisionnek veszi, tegyél VRS-side post-classification helper-t.

Ajánlott fogalmak:

```rust
enum SegmentIntersectionKind {
    None,
    TouchPoint,
    TouchOverlap,
    ProperCrossing,
}
```

vagy repo-stílusú ekvivalens.

Elvárás:

```text
TouchPoint / TouchOverlap -> no-positive-area touch -> NoCollision
ProperCrossing -> Collision
Positive polygon overlap -> Collision
```

Ne rely-olj vakon `Edge::collides_with(proper_only=false)` eredményre, ha az touchingot is collisionként ad.

### 2. CDE pair query policy wrapper

A `CdeAdapter` / `CdeCollisionBackend` pair queryje ne közvetlenül adja vissza a nyers CDE touching döntést.

Elvárt:

```text
raw CDE collision candidate
  -> VRS touching policy verification
  -> NoCollision, ha csak edge/corner touch
  -> Collision, ha positive overlap / true crossing
```

Ha a CDE API nem teszi lehetővé a touching/overlap különbségtételt, akkor építs VRS-side polygon segment/containment helper-t a query utáni pontosításhoz. Ez a Q08R exact policy helperből újrahasznosítható.

### 3. CDE boundary query policy wrapper

Sheet boundary esetén:

```text
all vertices inside or on boundary + no true crossing outside -> NoCollision
edge lies on boundary -> NoCollision
corner on boundary -> NoCollision
any vertex outside beyond epsilon -> Collision
proper boundary crossing -> Collision
```

Ha unsupported geometry miatt nem dönthető el, maradjon `Unsupported`, ne bbox fallback.

### 4. Epsilon és tolerance contract

Legyen explicit tolerance:

```text
GEOM_EPS vagy repo existing EPS
```

Dokumentáld:

```text
- milyen távolságon belül számít touch-nak
- positive overlap teszt hogyan különül el touchingból
- CDE raw result hogyan kombinálódik VRS post-policyval
```

### 5. Diagnostics

Ha már van CDE diagnostics, bővítsd vagy reportold:

```text
cde_raw_collision_count
cde_touch_filtered_count
cde_positive_collision_count
cde_boundary_touch_count
cde_unsupported_count
```

Ha kódban túl széles lenne a diagnostics bővítés, legalább a reportban legyen teszt/finding matrix.

## Kötelező tesztek

Adj célzott Rust teszteket, minimum ezekkel vagy ekvivalens nevekkel:

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

A tesztek legalább a publikus backend API-n keresztül bizonyítsák a viselkedést:

```text
CdeCollisionBackend::placement_overlaps
CdeCollisionBackend::placement_within_sheet
VrsSeparator / candidate backend loss, ahol releváns
```

## Acceptance gate

Futtasd legalább:

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

A report tartalmazza:

```text
- dependency gate evidence
- raw CDE touching semantics audit
- exact policy target: bbox/Q08R parity
- changed files/functions matrix
- tests added/fixed
- touching vs positive collision matrix
- diagnostics / counters, ha vannak
- remaining limitations
- verify summary
```

PASS esetén:

```text
első sor: PASS
report vége: SGH-Q15_STATUS: READY
```
