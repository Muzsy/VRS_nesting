REVISE

# SGH-Q24R4 native Sparrow model cutover

SGH-Q24R4_STATUS: REVISE (native model cutover NOT completed; Q24R3 runtime intact)
STATIC_CUTOVER_GATE: FAIL (sparrow.rs still uses WorkingLayout/VrsCollisionTracker; run_sparrow_pipeline builds WorkingLayout)
RUNTIME_MEDIUM_CDE_GATE: PASS (ok, 12/12, converged, pairs 0, boundary 0 — Q24R3 behavior preserved)
ENABLING_NATIVE_PRIMITIVE: cde_adapter::prepare_shape_native added (green, integrated)
CUTOVER_MAP: docs/egyedi_solver/sgh_q24r4_native_sparrow_model_cutover_map.md
BUILD_STATUS: green (committed Q24R3 PASS baseline preserved; no broken/half-migrated core)
Q19_STATUS: HOLD

> Honest `REVISE`. Q24R4 requires a **complete from-scratch rewrite of the
> production solver core** — replacing `WorkingLayout` + `crate::io::Placement`
> (internal) + `VrsCollisionTracker` with native `SparrowProblem` / `SPInstance` /
> `SparrowLayout` / `SparrowSolution` / `SparrowCollisionTracker` / `SparrowOptimizer`,
> a native CDE-backed tracker, a native search (the existing
> `search_position_for_target` is `&WorkingLayout`-typed and cannot be reused),
> native final CDE validation, an adapter cutover of `run_sparrow_pipeline`, and a
> port of the entire Sparrow test suite — while keeping 434 tests green AND the
> medium CDE 12/12 gate converging. That is a genuine multi-session effort. I did
> **not** complete it as a one-shot, because a half-migrated core would break the
> verified-green Q24R3 PASS baseline, and I will not fake a Sparrow-named wrapper
> over the old core (explicitly rejected by the task). I report this honestly
> rather than claim an unverified PASS.

## What WAS done this run
1. **Mandatory reference reading** — `.cache/sparrow` present; read
   `optimizer/{mod,separator,worker,explore}.rs`, `sample/search.rs`,
   `quantify/tracker.rs` (compress.rs skim only). Current VRS core read:
   `optimizer/sparrow.rs`, `working.rs`, `search_position.rs`, `collision_severity.rs`,
   `cde_adapter.rs`, `adapter.rs`, `io.rs`.
2. **Model cutover map** — `docs/egyedi_solver/sgh_q24r4_native_sparrow_model_cutover_map.md`:
   function-by-function old-core → native replacement, reusable low-level primitives,
   static-gate shape, compression-out-of-scope.
3. **Enabling native primitive** — `cde_adapter::prepare_shape_native(part, x, y, rot)`
   (builds a CDE shape from native transform fields, no `crate::io::Placement`),
   integrated (the old `prepare_shape_from_placement` now delegates to it). This is
   the foundation the native `SparrowCollisionTracker`/search need to do CDE truth
   without the old core. Build stays green.

## What was NOT done (the cutover itself) — remaining work
- Native types: `SparrowProblem`/`SPInstance`/`SparrowLayout`/`SparrowPlacement`/
  `SparrowSolution`/`SparrowCollisionTracker`/`SparrowOptimizer` (single-file
  `sparrow.rs` rewrite is sufficient for the static gate, which scans the file when
  no `sparrow/` dir exists).
- Native CDE tracker (owns pair/boundary records + GLS; uses `prepare_shape_native`
  + `CdeCandidateSession` + `CdeAdapter::query_*`; no `VrsCollisionTracker`).
- Native search over `SparrowLayout` (sampling + coord descent + CDE eval), since
  `search_position_for_target` is `&WorkingLayout`-typed.
- `run_sparrow_pipeline` cutover: `SparrowProblem::from_solver_input(...)` →
  `SparrowOptimizer::solve(...)` → native final CDE validation → projection to
  `crate::io::Placement`; remove `WorkingLayout::new` from the production branch.
- Port the Sparrow + adapter test suite onto native types; keep medium CDE 12/12.

## Evidence (current state — honest)
- `cargo build --manifest-path rust/vrs_solver/Cargo.toml --release` → ok (green).
- `python3 scripts/smoke_sgh_q24r4_native_sparrow_model_cutover.py` →
  **static native-model gate FAILS** (WorkingLayout/VrsCollisionTracker present in
  `sparrow.rs`; native tokens absent; `run_sparrow_pipeline` uses `WorkingLayout::new`)
  while the **runtime medium CDE gate PASSES** (status ok, 12/12, converged, final
  collision pairs 0, final boundary violations 0, CDE forced, compression 0). This
  truthfully shows the cutover is not yet implemented and Q24R3 runtime is intact.
- Compression stayed disabled/out of scope (Q24R3 `enable_compression=false`).

## Why REVISE and not a one-shot PASS
The task is binary (native model OR reject) and forbids wrappers. A genuine cutover
is large and convergence-sensitive (the native tracker/search must keep medium CDE
12/12 converging). Completing AND verifying it in one session risks a broken core;
the responsible path is to land the design + enabling primitive green and report the
remaining rewrite precisely. Next session: implement the native single-file
`sparrow.rs` per the cutover map and the added `prepare_shape_native` primitive.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-05-31T11:02:31+02:00 → 2026-05-31T11:05:25+02:00 (174s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/sgh_q24r4_native_sparrow_model_cutover.verify.log`
- git: `main@12a9245`
- módosított fájlok (git status): 10

**git diff --stat**

```text
 rust/vrs_solver/src/optimizer/cde_adapter.rs | 18 ++++++++++++++----
 1 file changed, 14 insertions(+), 4 deletions(-)
```

**git status --porcelain (preview)**

```text
 M rust/vrs_solver/src/optimizer/cde_adapter.rs
?? README_SGH_Q24R4_NATIVE_SPARROW_MODEL_CUTOVER_PACKAGE.md
?? canvases/egyedi_solver/sgh_q24r4_native_sparrow_model_cutover.md
?? codex/codex_checklist/egyedi_solver/sgh_q24r4_native_sparrow_model_cutover.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q24r4_native_sparrow_model_cutover.yaml
?? codex/prompts/egyedi_solver/sgh_q24r4_native_sparrow_model_cutover/
?? codex/reports/egyedi_solver/sgh_q24r4_native_sparrow_model_cutover.md
?? codex/reports/egyedi_solver/sgh_q24r4_native_sparrow_model_cutover.verify.log
?? docs/egyedi_solver/sgh_q24r4_native_sparrow_model_cutover_map.md
?? scripts/smoke_sgh_q24r4_native_sparrow_model_cutover.py
```

<!-- AUTO_VERIFY_END -->
