# SGH-Q25-R1 Semantic upstream Sparrow core parity fix, compression excluded

## Why this task exists

Q25 was a useful structural reset: the old monolithic `rust/vrs_solver/src/optimizer/sparrow/mod.rs` was split into upstream-mapped modules, and production `sparrow_cde` stayed on the native `SparrowProblem -> SparrowOptimizer -> SparrowSolution` route.

However, the Q25 audit found that this is still not a complete jagua_rs/Sparrow core port. Several files have upstream names but not upstream behavior:

- `eval/specialized_cde_pipeline.rs` is a stub/no-op collector.
- `eval/sep_evaluator.rs` still ranks candidates with bbox/extent-like penetration via `hazard_extent_depth`.
- `lbf.rs` still has `fixed_sheet_recovery_candidate` and AABB-overlap penalty fallback.
- `quantify/*` still uses a local CDE-resolution-distance model instead of the upstream `overlap_area_proxy + shape penalty` quantification.
- `worker.rs` / `separator.rs` are closer, but must strictly follow weighted-loss semantics and not pair-count-first shortcuts.
- `explore.rs` still lacks a faithful fixed-sheet equivalent of upstream contained-item relocation during disruption.

This task fixes those semantic gaps. It must not become another benchmark-tuning task.

## Source of truth

Use the local upstream clone:

```text
.cache/sparrow
```

Record the exact commit:

```bash
git -C .cache/sparrow rev-parse HEAD
```

Read these upstream files before coding:

```text
.cache/sparrow/src/eval/specialized_jaguars_pipeline.rs
.cache/sparrow/src/eval/sep_evaluator.rs
.cache/sparrow/src/eval/lbf_evaluator.rs
.cache/sparrow/src/eval/sample_eval.rs
.cache/sparrow/src/quantify/mod.rs
.cache/sparrow/src/quantify/tracker.rs
.cache/sparrow/src/quantify/pair_matrix.rs
.cache/sparrow/src/quantify/overlap_proxy.rs
.cache/sparrow/src/sample/search.rs
.cache/sparrow/src/sample/coord_descent.rs
.cache/sparrow/src/sample/best_samples.rs
.cache/sparrow/src/sample/uniform_sampler.rs
.cache/sparrow/src/optimizer/lbf.rs
.cache/sparrow/src/optimizer/worker.rs
.cache/sparrow/src/optimizer/separator.rs
.cache/sparrow/src/optimizer/explore.rs
```

Do not proceed by memory. Do not infer upstream behavior from the current VRS code.

## Scope

Keep the Q25 module structure:

```text
rust/vrs_solver/src/optimizer/sparrow/
  mod.rs
  model.rs
  optimizer.rs
  lbf.rs
  worker.rs
  separator.rs
  explore.rs
  fixed_sheet.rs
  diagnostics.rs
  sample/
  eval/
  quantify/
```

Do not collapse the modules back into a monolith.

Compression is still out of scope. Do not implement, optimize, or enable compression in this task.

## Required semantic fixes

### 1. `eval/specialized_cde_pipeline.rs` must stop being a stub

Current failure pattern:

```rust
pub(crate) struct SpecializedCdeHazardCollector;
impl SpecializedCdeHazardCollector {
    pub(crate) fn reload(&mut self, _loss_bound: f64) {}
}
```

This is not a port.

Required:

- Implement a real VRS/jagua-compatible counterpart of upstream `SpecializedHazardCollector`.
- It must hold state: current target, tracker reference/weights, accumulated weighted loss, collected pair/container hazards, loss bound, early-termination flag/counter.
- `reload(loss_bound)` must actually reset collector state and store the bound.
- The collector must expose meaningful methods equivalent to:
  - `is_empty`,
  - `loss`,
  - `early_terminate`,
  - hazard/pair/container accumulation.
- `collect_poly_collisions_in_detector_custom(...)` must perform real collection using the local CDE/session, not just return an empty collector.

Fixed-sheet adaptation is allowed only for the container/sheet representation, not for skipping the collector.

### 2. `SeparationEvaluator` must use collector + upper-bound semantics

Required:

- Candidate evaluation must follow the upstream pattern:
  1. convert candidate transform;
  2. prepare moving shape;
  3. reload hazard collector with upper bound;
  4. query CDE / collect hazards;
  5. early-terminate dominated samples;
  6. return `Clear`, `Collision { loss }`, or invalid based on collector state.
- It must use tracker GLS weights through the collector.
- Remove bbox/extent ranking such as `hazard_extent_depth`, `aabb_penetration`, `ox.min(oy)`, or `ix * iy` as candidate collision-loss scoring.
- AABB may remain only for safe fit-to-sheet broad-phase clipping, never as separation loss/ranking.

### 3. Quantification must match upstream or be explicitly non-default experimental

The default production loss model must be the upstream Sparrow model:

- pair loss: `overlap_area_proxy(...) + epsilon^2`, square root, shape penalty;
- container loss: outside/intersection-area logic and shape penalty;
- tracker stores pair/container loss and GLS weights based on this quantification.

If the previous CDE-resolution-distance probe is retained at all, it must be behind an explicit experimental flag and must not be the default production path. The report must not call it “exact upstream-style”.

### 4. `LBFBuilder` must remove fixed-sheet recovery/proxy fallback

Current failure pattern:

```rust
fixed_sheet_recovery_candidate(...)
candidate_penalty += 1.0 + (ix * iy).sqrt()
```

Required:

- LBF placement must go through `search_placement + LBFEvaluator` semantics.
- If no clear placement exists on fixed sheets, return unresolved/partial with diagnostics; do not invent AABB-overlap recovery placement.
- Fixed-sheet adaptation may iterate the available sheets and rotations, but may not use shelf/anchor/proxy fallback as a production success path.

### 5. Worker/separator must be strict weighted-loss semantics

Required:

- Worker move acceptance must be based on the moved item’s weighted loss not increasing, matching upstream intent.
- Separator best-worker load-back must choose minimum total weighted loss, not pair-count-first or raw-loss-first.
- Strike/no-improvement loop must be based on upstream loss semantics.
- Sequential workers are acceptable only if parallelism is documented as an implementation limitation; the semantics must still match the upstream worker competition.

### 6. Exploration disruption must include contained-item relocation equivalent

Required:

- Keep fixed-sheet adaptation, but implement the meaningful equivalent of upstream `practically_contained_items` relocation:
  - after large-item swap/relocation, detect items practically contained/covered by moved large items using CDE/geometric containment;
  - transform those contained items into the newly opened space;
  - clamp/convert to closest feasible fixed-sheet placement;
  - update tracker consistently.
- Do not count a mere large-item swap + random kick as full exploration parity.

### 7. Smoke/tests must catch semantic regressions

Update or add smoke checks so Q25-R1 cannot pass with:

- no-op collector,
- empty `reload`,
- bbox/extent separation ranking,
- `fixed_sheet_recovery_candidate`,
- `candidate_penalty` with `ix * iy`,
- default resolution-distance loss while claiming upstream parity,
- pair-count-first worker selection,
- fake dense guard/partial,
- compression usage.

## Runtime gates

Runtime is not the main goal, but the implementation must still build and preserve basic behavior:

```bash
cargo build --manifest-path rust/vrs_solver/Cargo.toml --release
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
python3 scripts/smoke_sgh_q25_r1_semantic_sparrow_core_parity_fix.py
./scripts/check.sh
```

Expected runtime behavior:

- medium CDE regression remains passing;
- LV8 12 type × 1 remains passing;
- LV8 first-sheet 191 real run is not guarded/faked;
- 191 may remain partial, but report exact raw loss, weighted loss, final pairs, validated placements, search calls, collector early terminations, and unresolved list.

## Report requirements

Write:

```text
codex/reports/egyedi_solver/sgh_q25_r1_semantic_sparrow_core_parity_fix.md
```

The report must include:

1. upstream commit hash;
2. changed files;
3. semantic-port table with these columns:

```text
Upstream file | Required behavior | Local file | Local implementation | Status | Fixed-sheet deviation | Evidence
```

Allowed statuses:

```text
PORTED
ADAPTED_FIXED_SHEET
DEFERRED_COMPRESSION_ONLY
NOT_APPLICABLE_IO_ONLY
REVISE
```

Rules:

- `PORTED` means the behavior is implemented, not just the type/function name exists.
- `ADAPTED_FIXED_SHEET` requires a concrete fixed-sheet reason.
- Non-compression `REVISE` means final task status must be `REVISE`, not `PASS`.
- Do not use “Sparrow-like”, “equivalent”, “similar”, “future work”, “partial but acceptable”, or “progress improved” to justify a PASS.

## PASS criteria

Q25-R1 can be `PASS` only if:

- `specialized_cde_pipeline.rs` is not a stub;
- `SeparationEvaluator` does not use bbox/extent penetration as separation loss/ranking;
- default quantification matches upstream Sparrow quantification semantics or the report honestly marks a non-default experimental alternative;
- LBF has no AABB/proxy recovery success path;
- worker/separator selects by weighted loss semantics;
- exploration contains contained-item relocation equivalent;
- production `sparrow_cde` stays native and compression-free;
- build/tests/smoke pass;
- report is honest and does not overstate parity.

## Automatic REVISE

Mark `SGH-Q25-R1_STATUS: REVISE` if any of these remain:

```text
SpecializedCdeHazardCollector is empty or reload is no-op
collect_poly_collisions_in_detector_custom returns empty/default collector only
hazard_extent_depth / aabb_penetration / ox.min(oy) / ix*iy used for separation loss
fixed_sheet_recovery_candidate or shelf/anchor fallback remains production LBF path
resolution-distance primary quantification is called exact upstream parity
worker candidate selection is pair-count-first
exploration disruption has no contained-item relocation equivalent
compression is implemented/enabled/hardened
```
