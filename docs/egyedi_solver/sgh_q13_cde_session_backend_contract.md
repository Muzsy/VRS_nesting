# SGH-Q13 — CDE Session Backend Contract

## Status

**PASS** — CDE search-path wiring complete; honest `PerCallOnly` session lifecycle documented.

## Overview

SGH-Q13 fixed the three CDE sentinel stubs that made `collision_backend: "cde"` unusable in the
separator/search path. The `VrsCollisionTracker` now uses `CdeCollisionBackend` for pair and
boundary decisions under CDE mode, and `candidate_loss_for_backend` computes real loss values
instead of returning `f64::MAX`.

A new `cde_session.rs` module documents the jagua-rs 0.6.4 lifecycle capabilities honestly.

## jagua-rs 0.6.4 CDE Lifecycle Assessment

### API symbols relevant to session management

| Symbol | Path | Notes |
|---|---|---|
| `CDEngine::register_hazard` | `jagua_rs::collision_detection::CDEngine` | `pub fn` — adds a hazard to live engine |
| `CDEngine::deregister_hazard_by_entity` | same | `pub fn` — removes a hazard by entity key |
| `CDEngine::hazards_map` | same | `pub SlotMap<HazKey, Hazard>` — can look up HazKey |
| `HazardEntity::PlacedItem { pk: PItemKey }` | `jagua_rs::...::hazards::hazard` | Requires SlotMap `PItemKey` from a jagua layout |
| `HazardEntity::Hole { idx }` | same | Usable without layout state |
| `HazKeyFilter` | `jagua_rs::...::hazards::filter` | Can exclude specific HazKeys (self-hazard filter) |

### Session viability answers

**Can self-hazard be excluded in a session-owned CDEEngine query?**
`HazKeyFilter` can exclude specific `HazKey` values. However, to exclude the item being queried,
you need to either (a) use `HazardEntity::PlacedItem { pk }` with a SlotMap PItemKey from a full
jagua layout state (not available in VRS), or (b) deregister and re-register the item's hazard for
each query, which defeats the purpose. Therefore self-hazard exclusion in a live-search session
CDEngine is not cleanly implementable.

**Can `HazardEntity::PlacedItem` be used with VRS layout state?**
No. `PItemKey` is a SlotMap key from jagua-rs's own `PlacedItem` store. VRS does not maintain a
jagua-rs layout slotmap. Using `HazardEntity::Hole { idx }` is the safe alternative, but then
each query must construct or mutate the CDEngine's hazard set — which for live iterative search
means per-call rebuilds.

**What can be safely implemented now?**
- **PerCallOnly** (live search): rebuild `CDEngine` per query — honest and fully functional.
- **QueryBatch** (offline validation): build one `CDEngine` per sheet layout, run all boundary
  queries in one pass, then discard. Viable but not required to unblock search-path wiring.

## CdeSessionCapability

```rust
pub enum CdeSessionCapability {
    FullSession,                      // One CDEngine per layout, reused across all queries.
    QueryBatch,                       // One CDEngine per pass (offline validation).
    PerCallOnly { reason: &'static str }, // CDEngine rebuilt per query (live search).
}
```

`query_capability()` returns `PerCallOnly` for jagua-rs 0.6.4 — honest because:
1. No tentative-query API (no way to "try placement without committing hazard registration").
2. `HazardEntity::PlacedItem` requires a SlotMap PItemKey VRS does not own.

## CdeDiagnostics

```rust
pub struct CdeDiagnostics {
    pub cde_queries: usize,
    pub cde_engine_builds: usize,       // = cde_queries for PerCallOnly
    pub cde_unsupported_count: usize,
    pub cde_session_capability: String, // "per_call_only" | "query_batch" | "full_session"
}
```

## Separator Search-Path Wiring (Q13 Fix)

### `compute_backend_decisions(Cde)` — was all-Unsupported, now real CDE queries

```
Before Q13: all pairs → Unsupported, all boundaries → Unsupported
After  Q13: uses CdeCollisionBackend.placement_within_sheet / placement_overlaps
            → NoCollision, Collision, or Unsupported depending on actual geometry
```

### `update_placement(Cde)` — was all-Unsupported, now real CDE queries

```
Before Q13: boundary_exact_unsupported[idx] = true; all pairs → pair_exact_unsupported
After  Q13: uses CdeCollisionBackend for boundary and per-pair decisions
```

### `candidate_loss_for_backend(Cde)` — was f64::MAX, now real loss

```
Before Q13: return f64::MAX (always)
After  Q13: same logic as JaguaPolygonExact arm, using CdeCollisionBackend:
            - placement_within_sheet → NoCollision=0.0, Collision=compute_boundary_loss.max(1.0)
            - placement_overlaps → NoCollision=0.0, Collision=pair_loss.max(1.0)
            - Unsupported → return f64::MAX (only when geometry is genuinely invalid)
```

## No-Silent-Fallback Guarantees

- `collision_backend: "cde"` → CDE arm in all three separator functions; never delegates to bbox
- Invalid geometry → `Unsupported { reason }`, not `NoCollision`
- Bbox default behavior unchanged (Bbox arm untouched)
- JaguaPolygonExact behavior unchanged (JaguaPolygonExact arm untouched)

## Acceptance Outcome

**PASS** — Category B from the canvas:

> "Ha a filter/lifecycle API miatt full session nem biztonságos, akkor CdeSessionCapability::PerCallOnly
> dokumentáltan marad, de a search-path CDE wiring ténylegesen használja a per-call CdeCollisionBackendet,
> nem Unsupported sentinel."

Evidence: 10 Q13 tests pass, 310 total library tests pass, verify.sh exits 0.
