PASS

# Report — SGH-Q18A-R1 `sgh_q18a_r1_phase_timing_report_consistency_fix`

## Dependency gate

```
codex/reports/egyedi_solver/sgh_q18a_cde_correctness_runtime_observability.md
```

First line: `PASS` ✓  
Contains `SGH-Q18A_STATUS: READY_FOR_AUDIT` ✓  

Dependency gate: **PASS**

## False claim identified

Q18A closed with these checklist items checked:

```
[x] PhaseOptimizer exploration runtime measurable in report or explicit diagnostics mode
[x] PhaseOptimizer compression runtime measurable in report or explicit diagnostics mode
[x] PhaseOptimizer BPP runtime measurable in report or explicit diagnostics mode
```

Audit of `phase.rs` and `adapter.rs` at Q18A close confirmed these fields did NOT exist:
- `PhaseResult` had no `exploration_ms`/`compression_ms`/`bpp_ms` fields
- `OptimizerDiagnosticsOutput` had no `phase_optimizer_*_ms` fields
- `PhaseOptimizer::run` had no wall-clock instrumentation for per-phase timing

Only `final_commit_validation_ms` (for `CDE` + final commit, gated by `VRS_CDE_OBSERVABILITY_TIMING=1`)
was actually implemented. The Q18A smoke script had 32 assertions, none covering per-phase timing.

## What R1 implements

### `rust/vrs_solver/src/optimizer/phase.rs`

- Added private helpers `phase_timing_enabled()`, `phase_t_start(enabled)`, `phase_t_ms(start)`
- Extended `PhaseResult` with:
  ```rust
  pub exploration_ms: Option<f64>,
  pub compression_ms: Option<f64>,
  pub bpp_ms: Option<f64>,
  ```
- `PhaseOptimizer::run` now instruments each phase with `Instant` guarded by `phase_timing_enabled()`
- 3 new tests: absent by default, helpers disabled, helpers enabled

### `rust/vrs_solver/src/io.rs`

Extended `OptimizerDiagnosticsOutput` with 4 new `Option<f64>` fields (backward-compatible):

```rust
pub phase_optimizer_exploration_ms: Option<f64>,
pub phase_optimizer_compression_ms: Option<f64>,
pub phase_optimizer_bpp_ms: Option<f64>,
pub phase_optimizer_final_commit_ms: Option<f64>,
```

All `#[serde(skip_serializing_if = "Option::is_none")]` — absent from default JSON.

### `rust/vrs_solver/src/adapter.rs`

- Moved `diagnostics` construction into the `Ok(commit)` arm (after commit timing measurement)
- Wired `result.exploration_ms`, `result.compression_ms`, `result.bpp_ms` from `PhaseResult`
- Wired `final_commit_ms` from the commit-timing measurement
- 3 new tests covering default-absent timing and determinism

### `scripts/smoke_sgh_q18a_cde_observability.py`

- Added `env.pop("VRS_CDE_OBSERVABILITY_TIMING", None)` in `run_solver` when `timing=False`
  (prevents parent env from leaking into non-timing fixtures when script is run with the env flag)
- Added fixture 7: asserts all 5 timing fields absent in default JSON (phase_optimizer + CDE, no env)
- Added fixture 8: asserts all 4 phase_optimizer timing fields present and non-negative (env=1)
- Added fixture 9: asserts `final_commit_validation_ms` present for legacy_multisheet + CDE + env,
  and `optimizer_diagnostics` absent (legacy path emits no per-phase timing)

### `codex/codex_checklist/egyedi_solver/sgh_q18a_cde_correctness_runtime_observability.md`

Unchecked the three false timing items; added correction note referencing R1.

### `codex/reports/egyedi_solver/sgh_q18a_cde_correctness_runtime_observability.md`

Updated "Runtime/per-phase evidence" section to document the gap and note R1 correction.

## Modified files (R1)

| File | Change |
|---|---|
| `rust/vrs_solver/src/optimizer/phase.rs` | Timing helpers + `PhaseResult` fields + per-phase measurement + 3 tests |
| `rust/vrs_solver/src/io.rs` | 4 new `Option<f64>` fields in `OptimizerDiagnosticsOutput` |
| `rust/vrs_solver/src/adapter.rs` | Wired phase timing into diagnostics construction + 3 tests |
| `scripts/smoke_sgh_q18a_cde_observability.py` | env isolation fix + fixtures 7/8/9 |
| `codex/codex_checklist/egyedi_solver/sgh_q18a_cde_correctness_runtime_observability.md` | False items unchecked + R1 note |
| `codex/reports/egyedi_solver/sgh_q18a_cde_correctness_runtime_observability.md` | Runtime section updated |

## Timing evidence (VRS_CDE_OBSERVABILITY_TIMING=1)

From smoke fixture 8 (phase_optimizer + CDE, 2-part, 10s):

```
phase_optimizer_exploration_ms  = 331.77 ms
phase_optimizer_compression_ms  = 213.16 ms
phase_optimizer_bpp_ms          = 5.94 ms
phase_optimizer_final_commit_ms = 5.86 ms
```

Timing breakdown: exploration and compression dominate, BPP and final commit negligible.
This matches expectations: exploration runs scoring in a loop; final commit is one-shot.

From smoke fixture 9 (legacy_multisheet + CDE, 2-part, 10s):

```
final_commit_validation_ms = 7.31 ms
optimizer_diagnostics = null (correct: no phase timing in legacy path)
```

From smoke fixture 7 (default, no env):

```
All timing fields absent ✓
```

## Default JSON invariant

No timing fields appear in default `SolverOutput` JSON. The `skip_serializing_if = "Option::is_none"`
guarantee and the `Option::None` default are both unit-tested and smoke-tested.

## Cargo test results

```
cargo test ... optimizer::phase   → all passed (includes 3 new R1 tests)
cargo test ... adapter            → all passed (includes 3 new R1 tests)
cargo test ... --lib              → 356 passed, 0 failed
```

Test name→requirement mapping (R1 additions):

| Test | Requirement |
|---|---|
| `phase_optimizer_timing_fields_absent_by_default` (phase.rs) | Per-phase timing not in default JSON |
| `phase_timing_helpers_absent_when_disabled` | `phase_t_ms` returns None when timing disabled |
| `phase_timing_helpers_present_when_enabled` | `phase_t_ms` returns Some when timing enabled |
| `phase_optimizer_timing_fields_absent_by_default` (adapter.rs) | Adapter output has no timing fields by default |
| `cde_timing_field_absent_by_default_in_cde_output` | CDE path also has no timing by default |
| `determinism_not_broken_by_default_output` | Default output is deterministic |

## Smoke script results

```
python3 scripts/smoke_sgh_q18a_cde_observability.py
→ Results: 49 passed, 0 failed / SMOKE: PASS

VRS_CDE_OBSERVABILITY_TIMING=1 python3 scripts/smoke_sgh_q18a_cde_observability.py
→ Results: 49 passed, 0 failed / SMOKE: PASS
```

Total: 98 assertions, all passing.

## Q18B recommendation re-evaluation

With real per-phase timing data available:

| Phase | Time (2-part, 10s run) | Proportion |
|---|---|---|
| Exploration | ~332 ms | 60% |
| Compression | ~213 ms | 39% |
| BPP | ~6 ms | 1% |
| Final commit | ~6 ms | 1% |

The exploration and compression phases dominate. Each CDEngine builds one engine per query.
At 288 engine builds for a 2-part run, a 276-part run would likely produce orders of magnitude
more engine builds. However:

- We do not have a larger fixture to quantify the actual per-build overhead at LV8 scale
- Session/cache complexity is non-trivial (Q18B scope)
- The current architecture is clean and passes all correctness gates

**Recommendation: `INCONCLUSIVE_NEEDS_BIGGER_FIXTURE`** — identical conclusion as Q18A.
The per-phase breakdown confirms exploration dominates, but a single 2-part fixture is
insufficient to justify the session rewrite investment. Run a 276-part LV8 fixture with
`VRS_CDE_OBSERVABILITY_TIMING=1` before deciding on Q18B.

SGH-Q18A_R1_STATUS: READY_FOR_AUDIT
SGH-Q20_STATUS: READY
Q18B_RECOMMENDATION: INCONCLUSIVE_NEEDS_BIGGER_FIXTURE

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-05-28T00:38:57+02:00 → 2026-05-28T00:41:56+02:00 (179s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/sgh_q18a_r1_phase_timing_report_consistency_fix.verify.log`
- git: `main@7058f96`
- módosított fájlok (git status): 12

**git diff --stat**

```text
 ...h_q18a_cde_correctness_runtime_observability.md |  8 +-
 ...h_q18a_cde_correctness_runtime_observability.md |  8 +-
 rust/vrs_solver/src/adapter.rs                     | 84 +++++++++++++++++---
 rust/vrs_solver/src/io.rs                          |  9 +++
 rust/vrs_solver/src/optimizer/phase.rs             | 71 +++++++++++++++++
 scripts/smoke_sgh_q18a_cde_observability.py        | 90 ++++++++++++++++++++++
 6 files changed, 256 insertions(+), 14 deletions(-)
```

**git status --porcelain (preview)**

```text
 M codex/codex_checklist/egyedi_solver/sgh_q18a_cde_correctness_runtime_observability.md
 M codex/reports/egyedi_solver/sgh_q18a_cde_correctness_runtime_observability.md
 M rust/vrs_solver/src/adapter.rs
 M rust/vrs_solver/src/io.rs
 M rust/vrs_solver/src/optimizer/phase.rs
 M scripts/smoke_sgh_q18a_cde_observability.py
?? canvases/egyedi_solver/sgh_q18a_r1_phase_timing_report_consistency_fix.md
?? codex/codex_checklist/egyedi_solver/sgh_q18a_r1_phase_timing_report_consistency_fix.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q18a_r1_phase_timing_report_consistency_fix.yaml
?? codex/prompts/egyedi_solver/sgh_q18a_r1_phase_timing_report_consistency_fix/
?? codex/reports/egyedi_solver/sgh_q18a_r1_phase_timing_report_consistency_fix.md
?? codex/reports/egyedi_solver/sgh_q18a_r1_phase_timing_report_consistency_fix.verify.log
```

<!-- AUTO_VERIFY_END -->
