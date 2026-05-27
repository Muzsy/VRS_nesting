PASS

# Report — SGH-Q14 `sgh_q14_cde_touching_semantics_parity_fix`

## Status

PASS. CDE touching semantics fixed to match VRS/Q08R policy. 323 library tests pass.

## Dependency gate

- `codex/reports/egyedi_solver/sgh_q13_cde_session_backend_search_path_wiring.md`: first line `PASS`
- `SGH-Q14_STATUS: READY`: present in Q13 report

## 1) Meta

- **Task slug:** `sgh_q14_cde_touching_semantics_parity_fix`
- **Canvas:** `canvases/egyedi_solver/sgh_q14_cde_touching_semantics_parity_fix.md`
- **Goal YAML:** `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q14_cde_touching_semantics_parity_fix.yaml`
- **Futás dátuma:** 2026-05-27
- **Branch / commit:** main
- **Fókusz terület:** CDE Touching Semantics | Collision Backend | Pair Policy | Boundary Policy

## 2) Scope

### 2.1 Cél

1. Auditálni, hogy a raw CDE/jagua primitív touchingot collisionnek veszi-e.
2. VRS-side post-policy réteget implementálni, amely CDE Collision esetén felülbírálja a touching-only eseteket NoCollision-re.
3. 13 kötelező Q14 tesztet megírni és zöldre hozni.
4. Regresszió-fix: 4 pre-existing tesztet frissíteni, amelyek a régi CDE touching=Collision viselkedésre épültek.

### 2.2 Nem-cél

- Production default CDE
- Hole/cavity semantics
- DXF/preflight refaktor
- Új optimizer stratégia
- LossModel refaktor
- CDE session performance rewrite

## 3) Audit

### A raw CDE/jagua primitív touchingot collisionnek veszi-e?

**Igen.** A `CDEngine::detect_poly_collision` a `Edge::collides_with(proper_only=false)` hívást
használja, amely `true`-t ad vissza collineáris/touching edge-ekre is. Nincs publikus API flag
a `proper_only=true` bekapcsolásához jagua-rs forkolás nélkül.

### Mely VRS-side helper/policy réteg dönt a touching vs positive collision kérdésben?

A `cde_adapter.rs`-ben implementált VRS post-policy:

**Pair case:**
- `polygons_collide(&a.world_pts, &b.world_pts)` — `segments_properly_intersect`-et használ
  (proper crossing only, collinear/touching nem számít), és `point_strictly_inside_polygon`-t
  (strict containment, boundary nem számít).

**Boundary case:**
- `polygon_within_sheet_pts(&item.world_pts, &sheet.world_pts)` — `point_inside_or_on_polygon`
  (boundary OK) + no proper crossing of sheet edges.

### Audit parancsok eredménye

```
rg -n "collides_with" rust/vrs_solver/src/optimizer/cde_adapter.rs → nem található (post-policy elfedi)
rg -n "collides_with" ~/.cargo/registry/src -g '*.rs' → Edge::collides_with(proper_only: false) in jagua-rs
rg -n "polygons_collide|polygon_within_sheet_pts" rust/vrs_solver/src/optimizer/cde_adapter.rs → 2 hit (post-policy calls)
rg -n "segments_properly_intersect|point_strictly_inside" rust/vrs_solver/src/optimizer/collision_backend.rs → 2 hit
```

## 4) Implementáció

### 4.1 `CdePreparedShape.world_pts` — új mező

```rust
pub(crate) struct CdePreparedShape {
    pub(crate) spoly: jagua_rs::geometry::primitives::SPolygon,
    pub(crate) min_x: f64,
    pub(crate) min_y: f64,
    pub(crate) max_x: f64,
    pub(crate) max_y: f64,
    pub(crate) world_pts: Vec<Point>,  // Q14: VRS post-policy touching check
}
```

`world_pts` az item polygon csúcsait tárolja world koordinátákban, a jagua-rs típusok
szivárgása nélkül. `prepare_shape_from_placement` és `prepare_shape_from_sheet` is beállítja.

### 4.2 `query_pair` post-policy

```rust
// ELŐTTE (Q12/Q13): raw CDE döntés, touching = Collision
if !cde.detect_poly_collision(&a.spoly, &NoFilter) {
    return CdeQueryResult::NoCollision;
}
return CdeQueryResult::Collision;  // touching is!

// UTÁNA (Q14): VRS post-policy
if !cde.detect_poly_collision(&a.spoly, &NoFilter) {
    return CdeQueryResult::NoCollision;
}
match polygons_collide(&a.world_pts, &b.world_pts) {
    Ok(true)  => CdeQueryResult::Collision,
    Ok(false) => CdeQueryResult::NoCollision,  // csak touching
    Err(r)    => CdeQueryResult::Unsupported { reason: r },
}
```

### 4.3 `query_boundary` post-policy

```rust
// ELŐTTE: raw CDE döntés, boundary touch = Collision
if !cde.detect_poly_collision(&item.spoly, &NoFilter) {
    return CdeQueryResult::NoCollision;
}
return CdeQueryResult::Collision;

// UTÁNA (Q14): VRS post-policy
if !cde.detect_poly_collision(&item.spoly, &NoFilter) {
    return CdeQueryResult::NoCollision;
}
match polygon_within_sheet_pts(&item.world_pts, &sheet.world_pts) {
    Ok(true)  => CdeQueryResult::NoCollision,  // belül vagy boundary touch
    Ok(false) => CdeQueryResult::Collision,    // valóban kívül
    Err(r)    => CdeQueryResult::Unsupported { reason: r },
}
```

### 4.4 `polygon_within_sheet_pts` — új helper (`collision_backend.rs`)

```rust
pub(crate) fn polygon_within_sheet_pts(item_pts: &[Point], sheet_pts: &[Point]) -> Result<bool, &'static str> {
    // 1) minden item csúcs belül van-e vagy a sheet peremén?
    for &pt in item_pts {
        if !point_inside_or_on_polygon(pt, sheet_pts) {
            return Ok(false);  // kívül
        }
    }
    // 2) van-e proper crossing (item edge átmetszi a sheet peremét)?
    for i in 0..item_pts.len() {
        let a1 = item_pts[i];
        let a2 = item_pts[(i + 1) % item_pts.len()];
        for j in 0..sheet_pts.len() {
            let b1 = sheet_pts[j];
            let b2 = sheet_pts[(j + 1) % sheet_pts.len()];
            if segments_properly_intersect(a1, a2, b1, b2) {
                return Ok(false);  // valóban crossing
            }
        }
    }
    Ok(true)  // belül van, perem touch megengedett
}
```

### 4.5 Módosított fájlok

```
rust/vrs_solver/src/optimizer/cde_adapter.rs       — world_pts mező; post-policy query_pair/boundary; 11 Q14 teszt
rust/vrs_solver/src/optimizer/collision_backend.rs  — polygons_collide pub(crate); polygon_within_sheet_pts új
rust/vrs_solver/src/optimizer/separator.rs         — 2 Q14 teszt (candidate loss touching/overlap)
rust/vrs_solver/src/optimizer/moves.rs             — 1 regresszió-fix (teszt átnevezés + assertation enyhítés)
rust/vrs_solver/src/optimizer/sheet_elimination.rs — 1 regresszió-fix (assertion invertálás + negatív eset)
```

## 5) Tesztek

### Q14 kötelező tesztek (13/13 passing)

```
test optimizer::cde_adapter::tests::cde_touching_rect_edges_are_no_collision ... ok
test optimizer::cde_adapter::tests::cde_touching_rect_corners_are_no_collision ... ok
test optimizer::cde_adapter::tests::cde_positive_rect_overlap_is_collision ... ok
test optimizer::cde_adapter::tests::cde_touching_irregular_polygon_edges_are_no_collision ... ok
test optimizer::cde_adapter::tests::cde_positive_irregular_overlap_is_collision ... ok
test optimizer::cde_adapter::tests::cde_item_touching_sheet_boundary_inside_is_no_collision ... ok
test optimizer::cde_adapter::tests::cde_item_corner_touching_sheet_boundary_inside_is_no_collision ... ok
test optimizer::cde_adapter::tests::cde_item_crossing_sheet_boundary_is_collision ... ok
test optimizer::separator::tests::cde_separator_candidate_loss_touching_layout_is_zero ... ok
test optimizer::separator::tests::cde_separator_candidate_loss_positive_overlap_is_positive ... ok
test optimizer::cde_adapter::tests::bbox_default_touching_semantics_unchanged ... ok
test optimizer::cde_adapter::tests::jagua_polygon_exact_touching_semantics_unchanged ... ok
test optimizer::cde_adapter::tests::no_silent_bbox_fallback_for_cde_touching_policy ... ok
```

### Összes lib teszt

```
test result: ok. 323 passed; 0 failed; 0 ignored
```

### Regresszió-fix tesztek

```
test optimizer::moves::tests::move_executor_backend_aware_commit_gate_accepts_valid_cde_placement ... ok
test optimizer::sheet_elimination::tests::cde_internal_paths_reject_or_hard_penalty_no_silent_success ... ok
```

## 6) Policy döntések összefoglalója

### PASS feltételek teljesítése

| Feltétel | Teljesítve |
|---|---|
| Raw CDE touching semantics dokumentálva | Igen — proper_only=false confirmed |
| Pair touching → NoCollision | Igen — polygons_collide post-policy |
| Pair positive overlap → Collision | Igen — polygons_collide returns true |
| Boundary touch inside → NoCollision | Igen — polygon_within_sheet_pts returns true |
| Boundary crossing / outside → Collision | Igen — polygon_within_sheet_pts returns false |
| Bbox arm változatlan | Igen — Bbox arm érintetlen |
| JaguaPolygonExact arm változatlan | Igen — Exact arm érintetlen |
| cargo test --lib zöld | Igen — 323 passed, 0 failed |
| verify.sh zöld | Igen — see verify.log |

### Nem elfogadható esetek: mind megoldva

- ~~CDE touching edge → Collision~~ — Q14 post-policy javítja
- ~~CDE boundary touch inside → Collision~~ — Q14 polygon_within_sheet_pts javítja
- ~~silent fallback bboxra CDE query hiba esetén~~ — nincs (Unsupported propagálva)
- ~~Bbox/JaguaPolygonExact regresszió~~ — nincs (armok érintetlenek)

## 7) Nem-blokkoló megjegyzések

1. **Per-call CDEngine overhead**: a post-policy `polygons_collide` / `polygon_within_sheet_pts`
   hívások O(n*m) complexitásúak. Production batch-validationhoz QueryBatch optimalizálható.
2. **Hole/cavity semantics**: Q14 csak outer polygon touching-t fed le. Hole-on belüli
   touching eseteket külön task (Q15+) kezeli.
3. **world_pts allocation**: minden `prepare_shape_from_placement` hívás Vec-et allokál.
   Teljesítmény-kritikus path esetén arena allokátor vizsgálható.

SGH-Q15_STATUS: READY

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-05-27T19:16:44+02:00 → 2026-05-27T19:19:47+02:00 (183s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/sgh_q14_cde_touching_semantics_parity_fix.verify.log`
- git: `main@468d22b`
- módosított fájlok (git status): 12

**git diff --stat**

```text
 rust/vrs_solver/src/optimizer/cde_adapter.rs       | 248 ++++++++++++++++++---
 rust/vrs_solver/src/optimizer/collision_backend.rs |  33 ++-
 rust/vrs_solver/src/optimizer/moves.rs             |  21 +-
 rust/vrs_solver/src/optimizer/separator.rs         |  67 ++++++
 rust/vrs_solver/src/optimizer/sheet_elimination.rs |  21 +-
 5 files changed, 346 insertions(+), 44 deletions(-)
```

**git status --porcelain (preview)**

```text
 M rust/vrs_solver/src/optimizer/cde_adapter.rs
 M rust/vrs_solver/src/optimizer/collision_backend.rs
 M rust/vrs_solver/src/optimizer/moves.rs
 M rust/vrs_solver/src/optimizer/separator.rs
 M rust/vrs_solver/src/optimizer/sheet_elimination.rs
?? canvases/egyedi_solver/sgh_q14_cde_touching_semantics_parity_fix.md
?? codex/codex_checklist/egyedi_solver/sgh_q14_cde_touching_semantics_parity_fix.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q14_cde_touching_semantics_parity_fix.yaml
?? codex/prompts/egyedi_solver/sgh_q14_cde_touching_semantics_parity_fix/
?? codex/reports/egyedi_solver/sgh_q14_cde_touching_semantics_parity_fix.md
?? codex/reports/egyedi_solver/sgh_q14_cde_touching_semantics_parity_fix.verify.log
?? docs/egyedi_solver/sgh_q14_cde_touching_semantics_contract.md
```

<!-- AUTO_VERIFY_END -->
