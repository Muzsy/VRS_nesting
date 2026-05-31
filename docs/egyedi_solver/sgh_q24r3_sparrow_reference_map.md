# SGH-Q24R3 — Sparrow reference map (`.cache/sparrow` → VRS), compression out of scope

Function-by-function map from the local `.cache/sparrow` (jagua_rs/Sparrow)
optimizer to the VRS fixed-sheet `sparrow_cde` implementation. Compression
(`compress.rs`) is **explicitly out of Q24R3 scope** and gated OFF by default.

| Sparrow source (`.cache/sparrow`) | role | VRS equivalent | Q24R3 status |
|---|---|---|---|
| `src/optimizer/mod.rs::optimize` (Alg 11) | top-level orchestration: build → explore → compress | `optimizer/sparrow.rs::SparrowSeparationKernel::run` — build constructive seed → `exploration_phase` → (compression gated off) → final CDE validation | PARITY (minus compression) |
| `src/optimizer/lbf.rs::LBFBuilder::construct` | constructive initial solution | `optimizer/sparrow.rs::build_constructive_seed_layout` — area-sorted coarse row/grid spread across sheets, in-bounds, mild overlap | **NEW (Q24R3)** — replaces all-origin seed |
| `src/optimizer/explore.rs::exploration_phase` (Alg 12) | infeasible pool + biased restore + disruption | `optimizer/sparrow.rs::exploration_phase` + `disrupt_large_items` | PARITY (fixed-sheet) |
| `src/optimizer/separator.rs::Separator::separate` (Alg 9) | strike/no-improvement loop | `optimizer/sparrow.rs::SparrowSeparationKernel::separate` | PARITY |
| `src/optimizer/separator.rs::move_items_multi` (Alg 10) | worker-master pass | `optimizer/sparrow.rs::SparrowSeparationKernel::move_items_multi` | PARITY |
| `src/optimizer/worker.rs::SeparatorWorker::move_items` (Alg 5) | move every colliding item | `optimizer/sparrow.rs::SparrowSeparationKernel::worker_move_items` (uses `VrsCollisionTracker::colliding_indices`) | PARITY |
| `src/sample/search.rs::search_placement` (Alg 6) | container + focused sampling + BestSamples + 2-stage CD | `optimizer/search_position.rs::search_position_for_target` (global grid + focused + top-k + coord descent) + CDE batch separation loss | PARITY (reused; CDE-backed eval) |
| `src/quantify/tracker.rs::CollisionTracker` (Alg 1/8) | pair/container loss + GLS weights, save/restore | `optimizer/separator.rs::VrsCollisionTracker` (`colliding_indices`, `update_placement`, `update_weights`, `snapshot_loss`/`restore_but_keep_weights`) | PARITY (GLS); pair/boundary collision EXISTENCE is CDE-backed via `CdeCollisionBackend`; the decisive **search separation loss** is the CDE batch separation distance (`collision_severity::evaluate_transform_cde_batch`), not bbox area |
| `SPSolution`/`SPProblem` save/restore | coherent layout+engine snapshot | `optimizer/working.rs::WorkingLayout` (`snapshot`) + `VrsCollisionTracker` snapshot/restore; CDE candidate session reuse (`cde_adapter::CdeCandidateSession`) | FIXED_SHEET_ADAPTATION |
| `src/optimizer/compress.rs::compression_phase` (Alg 13) | strip-shrink compaction | `optimizer/sparrow.rs::compression_phase` (restore/pressure/separate/accept) | **OUT OF Q24R3 SCOPE** — gated OFF by default (`SparrowConfig::enable_compression=false`); skipped in the production lifecycle |

## CDE loss note (run.md #4)
For production `sparrow_cde`, collision/boundary **existence** is decided by the
active CDE backend (`CdeCollisionBackend` → jagua-rs `CDEngine`), and the
**decisive separation loss used by the search** is the CDE-truth separation
distance (`evaluate_transform_cde_batch` + `cde_batch_separation_loss`), never the
bbox `dx*dy` area. The `VrsCollisionTracker` GLS pair/boundary loss used for weight
guidance uses a smooth (size-scaled penetration) surrogate — documented fixed-sheet
delta; it drives GLS pressure, not the move decision. bbox is used only as
broad-phase prune inside the CDE adapter (AABB pre-check).

## Compression rationale (why out of scope)
Sparrow compression minimises the strip dimension (its objective). VRS is
fixed-sheet multisheet nesting; compaction is mainly meaningful later on the last
partially-used sheet. The Q24R3 default lifecycle is `constructive seed →
exploration/separation/search → full CDE validation` and must not depend on
compression to converge the medium CDE gate.
