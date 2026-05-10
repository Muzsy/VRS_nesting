# T06l-a — Diagnostics cleanup + can_place profiling

## 1. Status

**PASS_WITH_KNOWN_PREEXISTING_FAILURE**

- Default hot-path log spam eliminated. ✓
- `can_place` profiling wired and aggregated. ✓
- Default placement behavior unchanged (byte-identical stdout). ✓
- One pre-existing test failure unrelated to this task (`nfp::cfr::tests::cfr_sort_key_precompute_hash_called_once_per_component`) — verified failing on unmodified `main` (`git stash` baseline) with the identical error.

---

## 2. Executive verdict

- **Default hot-path log spam:** **gone**. Smoke fixture (`f3_4_compaction_slide_fixture_v2.json`, `--placer nfp --search none`): default stderr = 0 lines vs. before T06l-a where the same call would emit per-NFP-compute and per-CFR-call lines.
- **`can_place` profiling:** **works**. Under `NESTING_ENGINE_CAN_PLACE_PROFILE=1`, the placer routes each `can_place` call through `can_place_profiled` and the resulting `CanPlaceProfile` is aggregated into `NfpPlacerStatsV1`; the JSON `NEST_NFP_STATS_V1` line surfaces 14 new `can_place_profile_*` fields.
- **Default behavior:** **unchanged**. With profile flag off, all new fields default to `0` / `false`; stdout placements are byte-identical between default-flagged and profile-flagged runs of the same fixture; pre-existing `nfp_compute_calls`, `cfr_union_calls`, `cfr_diff_calls`, `candidates_*` counts are identical between flag combinations.
- **Measurement available:** boundary, broad-phase (RTree query + AABB filter), and narrow-phase (exact polygon intersection) nanosecond totals, plus per-stage reject counts and overlap-candidate-pair counters.

---

## 3. Context and source reports reviewed

Read for context (already established baseline):

- `codex/reports/nesting_engine/engine_v2_nfp_rc_t06_next_claude_algorithmic_speedup_audit.md` — 13-option ranked speedup audit; T06l (= this task) is recommendation **A** (eprintln gating + can_place profiling).
- `codex/reports/nesting_engine/engine_v2_nfp_rc_t06i_prepacked_cgal_nfp_benchmark.md` — direct CGAL hot-path baseline (276/276, 49.4% util, 32.5s NFP compute over 842 calls).
- (Implicit) T06d / T06j / T06k feature flags audited — `NESTING_ENGINE_CANDIDATE_DRIVEN`, `NESTING_ENGINE_HYBRID_CFR`, `NESTING_ENGINE_ACTIVE_SET_CANDIDATES`, etc., all left untouched and in their existing default-off state.

---

## 4. Code audit

### 4.1 Hot-path print audit (before T06l-a)

| Location | Print | When fired | Gating before T06l-a |
|---|---|---|---|
| `nfp_placer.rs:1077` | `[NFP DIAG] compute_nfp_lib START …` | every NFP cache miss | **none — unconditional** |
| `nfp_placer.rs:1089` | `[NFP DIAG] compute_nfp_lib END …` | every NFP cache miss | **none — unconditional** |
| `nfp_placer.rs:1181` | `[CFR DIAG] START …` | every CFR call (default path) | **none — unconditional** |
| `nfp_placer.rs:1193` | `[CFR DIAG] END …` | every CFR call (default path) | **none — unconditional** |
| `nfp_placer.rs:1585` | `[NFP DIAG] provider=… result_pts=…` | every successful provider compute | **none — unconditional** |
| `nfp/provider.rs:218` | `[NFP DIAG] provider=… cache_key_kernel=… result_pts=…` | every `compute_nfp_lib_with_provider` success | **none — unconditional** |
| `nfp/provider.rs:229` | `[NFP DIAG] provider=… FAILED=…` | every provider failure | **none — unconditional** |
| `nfp/cfr.rs::emit_cfr_diag` | `CFR_DIAG …` | once per `compute_cfr_with_stats` call (already gated) | already gated by `NESTING_ENGINE_CFR_DIAG=1` or threshold inside `cfr.rs` |
| `nfp_placer.rs::emit_summary` | `NFP_RUNTIME_DIAG_V1 …` | once at end of `nfp_place` | already gated by `NESTING_ENGINE_NFP_RUNTIME_DIAG=1` |
| `nfp_placer.rs:586,809,843,899` | `[ACTIVE_SET] …` | hot path *but* only when `NESTING_ENGINE_ACTIVE_SET_CANDIDATES=1` | already gated by `NESTING_ENGINE_ACTIVE_SET_DIAG=1` |
| `nfp_placer.rs::candidate_diag` lines | `[CANDIDATE_DIAG] …` | hot path *but* only when candidate-driven on | already gated by `NESTING_ENGINE_CANDIDATE_DIAG=1` |
| `nfp_placer.rs::is_hybrid_cfr_diag_enabled` line | `[HYBRID_CFR] …` | hot path *but* only when hybrid CFR on | already gated by `NESTING_ENGINE_HYBRID_CFR_DIAG=1` |
| `nfp_placer.rs::resolve_nfp_kernel*` warning | unknown-kernel warning | once at startup if env is malformed | not gated; left as-is (cold, one-shot, surface mis-config) |

**Findings:** seven unconditional hot-path prints needed gating; the rest were already gated or are cold/start-up paths.

### 4.2 `can_place_profiled` audit

`can_place_profiled` is exported from `feasibility::narrow` and re-exported from `feasibility::mod`. It mirrors the structural logic of `can_place` exactly — same five-step decision (ring validity → AABB containment → strict containment / boundary intersection → broad-phase RTree query + AABB overlap filter → narrow-phase polygon intersection-or-touch) — and additionally records:

- `poly_within_ns` — boundary / containment time (`poly_strictly_within`).
- `overlap_query_ns` — RTree broad-phase + AABB filter time.
- `overlap_candidates` — count of broad-phase survivors.
- `narrow_phase_ns` — exact polygon intersection check time.
- `narrow_phase_pairs` — number of placed parts examined in narrow phase.
- `rejected_by_aabb / within / narrow` — early-exit reason flags.
- `segment_pair_checks` — informational rough-cut, recomputed inside the per-pair loop (recorded for diagnostics; not consumed by aggregation).

**Why it was not on the live path:** it returns a `(bool, CanPlaceProfile)` tuple, and the live placer call sites used the simpler `bool`-returning `can_place(...)`. Both functions share branch-by-branch identical conditions, so swapping in `can_place_profiled` returns the same boolean (verified by the new equivalence test).

### 4.3 Stats / output audit

`NfpPlacerStatsV1` is the public stats struct already serialized as the `NEST_NFP_STATS_V1 <json>` line behind `NESTING_ENGINE_EMIT_NFP_STATS=1` (read in `main.rs::should_emit_nfp_stats`). New fields added; pre-existing fields untouched.

---

## 5. Implementation summary

### 5.1 Modified files

| File | Change |
|---|---|
| `rust/nesting_engine/src/placement/nfp_placer.rs` | added 3 env helpers, dispatcher + aggregator helpers, 14 `can_place_profile_*` stats fields with `Default` + `merge_from`, gated 5 hot-path eprintlns, replaced 5 `can_place(...)` call sites with `can_place_dispatch(...)`. |
| `rust/nesting_engine/src/nfp/provider.rs` | gated success + failure eprintlns in `compute_nfp_lib_with_provider` behind `NESTING_ENGINE_NFP_RUNTIME_DIAG=1`. |
| `rust/nesting_engine/src/feasibility/narrow.rs` | added `can_place_and_profiled_return_equal_booleans_across_control_cases` test asserting boolean equivalence across the 5 control cases. |

### 5.2 Env flags

| Flag | Effect | Default |
|---|---|---|
| `NESTING_ENGINE_NFP_RUNTIME_DIAG=1` | enables per-call NFP `[NFP DIAG]` lines (placer + provider) and the end-of-placement `NFP_RUNTIME_DIAG_V1` summary. | off |
| `NESTING_ENGINE_CFR_DIAG=1` | enables per-call CFR `[CFR DIAG]` lines in `nfp_placer.rs`. (The `cfr.rs::emit_cfr_diag` line was already gated by the same flag.) | off |
| `NESTING_ENGINE_CAN_PLACE_PROFILE=1` | routes each `can_place(...)` call through `can_place_profiled(...)` and aggregates the `CanPlaceProfile` into `NfpPlacerStatsV1`. | off |
| (existing, unchanged) | `NESTING_ENGINE_EMIT_NFP_STATS`, `NESTING_ENGINE_CANDIDATE_DRIVEN`, `…_DIAG`, `…_HYBRID_CFR`, `…_ACTIVE_SET_CANDIDATES`, `…_ACTIVE_SET_DIAG`, etc. | unchanged |

### 5.3 New stat fields

```
can_place_profile_enabled: bool
can_place_profile_calls: u64
can_place_profile_accept_count: u64
can_place_profile_reject_count: u64
can_place_profile_total_ns: u64           // outer wall-clock across the dispatcher
can_place_profile_boundary_ns_total: u64  // poly_strictly_within
can_place_profile_broad_phase_ns_total: u64  // RTree query + AABB overlap filter
can_place_profile_narrow_phase_ns_total: u64 // exact polygons_intersect_or_touch
can_place_profile_overlap_query_count_total: u64    // calls that reached broad phase
can_place_profile_overlap_candidate_count_total: u64 // sum of broad-phase survivors
can_place_profile_narrow_phase_pair_count_total: u64 // sum of narrow-phase iterations
can_place_profile_rejected_by_aabb_count: u64
can_place_profile_rejected_by_within_count: u64
can_place_profile_rejected_by_narrow_count: u64
```

All `u64` use `saturating_add` to avoid overflow on long runs.

### 5.4 Boolean equivalence guarantee

- The dispatcher takes a single `flag_enabled: bool`; when false it forwards directly to `can_place` (zero new work).
- When true, it calls `can_place_profiled(c, b, p)` and returns `.0` — the boolean.
- `can_place_profiled` shares branch-by-branch identical conditions with `can_place` (audited line-by-line in `narrow.rs:79–122` vs. `narrow.rs:140–231`).
- A new unit test (`can_place_and_profiled_return_equal_booleans_across_control_cases`) covers the 5 control cases mandated by the prompt: empty sheet valid, bounds violation, overlap violation, touching, multi-placed RTree query (with both clear and overlapping candidates).

---

## 6. Tests and commands

### 6.1 Build

```bash
cd rust/nesting_engine
cargo check -p nesting_engine
# Finished `dev` profile [unoptimized + debuginfo] target(s) in 3.28s — 40 warnings, 0 errors
cargo build --release -p nesting_engine
# Finished `release` profile [optimized] target(s) in 30.56s
```

### 6.2 Targeted tests

```bash
cargo test -p nesting_engine can_place
# 3 passed — including the new
#   can_place_and_profiled_return_equal_booleans_across_control_cases

cargo test -p nesting_engine nfp
# 6 passed (placement::nfp_placer::tests::*)

cargo test -p nesting_engine --bin nesting_engine narrow
# 12 passed (all feasibility::narrow::tests::*)
```

### 6.3 Full suite (with documented pre-existing failure)

```bash
cargo test -p nesting_engine
# test result: FAILED. 59 passed; 1 failed (lib)
# failing test: nfp::cfr::tests::cfr_sort_key_precompute_hash_called_once_per_component
```

**Pre-existing-failure verification:** stashed all working changes (`git stash`), re-ran `cargo test -p nesting_engine --lib` on unmodified `main` (commit `4c7d56c`), got the **same exact failure with identical assertion (`left: 9, right: 6`)**. Stash popped; failure is unrelated to T06l-a.

---

## 7. Smoke / measurement results

Smoke fixture: `poc/nesting_engine/f3_4_compaction_slide_fixture_v2.json` (small synthetic fixture; runs in <0.1s).
Command shape: `nesting_engine nest --placer nfp --search none < fixture.json`.

| Run | flags | stderr lines | placement stdout |
|---|---|---|---|
| A | (none) | **0** | baseline |
| B | `NESTING_ENGINE_NFP_RUNTIME_DIAG=1` | 3 | byte-identical to A |
| C | `NESTING_ENGINE_CFR_DIAG=1` | 8 (3× CFR DIAG START + END pairs etc.) | byte-identical to A |
| D | `NESTING_ENGINE_CAN_PLACE_PROFILE=1` + `NESTING_ENGINE_EMIT_NFP_STATS=1` | 1 (single `NEST_NFP_STATS_V1` JSON line) | byte-identical to A |
| E | `NESTING_ENGINE_EMIT_NFP_STATS=1` (profile off) | 1 (JSON, but `can_place_profile_enabled=false`, all `*_count`=0, all `*_ns_total`=0) | byte-identical to A |

### 7.1 Default vs diag flag log volume

- Default emits **0** hot-path diagnostic lines.
- With both diag flags on, NFP+CFR per-call lines reappear; 5 hot-path eprintlns are properly gated.

### 7.2 can_place profile aggregate (run D excerpt)

```
can_place_profile_enabled: true
can_place_profile_calls: 38
can_place_profile_accept_count: 3       (= 3 placements)
can_place_profile_reject_count: 35
can_place_profile_total_ns: 163_066     (~163 µs total can_place wall time)
can_place_profile_boundary_ns_total: 48_258  (poly_strictly_within)
can_place_profile_broad_phase_ns_total: 11_106  (RTree + AABB filter)
can_place_profile_narrow_phase_ns_total: 9_147   (polygons_intersect_or_touch)
can_place_profile_overlap_query_count_total: 38
can_place_profile_overlap_candidate_count_total: 6
can_place_profile_narrow_phase_pair_count_total: 6
can_place_profile_rejected_by_aabb_count: 0
can_place_profile_rejected_by_within_count: 31    (most rejects = bin-boundary / containment)
can_place_profile_rejected_by_narrow_count: 4
```

For this fixture: out of 38 `can_place` calls, 31 rejected at boundary check, 4 rejected at narrow-phase, 3 accepted. Boundary cost (~48 µs) dominates broad+narrow combined (~20 µs). Sample size is small but the breakdown shape matches expectation: with few placed parts the RTree barely fires; the dominant cost is the per-vertex `point_in_polygon` of the bin-containment check.

### 7.3 Stats invariance check (D vs E)

```
field                              run D (profile on)  run E (profile off)
nfp_compute_calls                   1                   1
nfp_cache_hits / misses             2 / 1               2 / 1
cfr_calls / union_calls / diff      3 / 2 / 2           3 / 2 / 2
candidates_before_dedupe_total      144                 144
candidates_after_cap_total          144                 144
sheets_used                         1                   1
effective_placer                    nfp                 nfp
```

All pre-existing aggregate counters are bit-identical. Profile flag does not perturb the algorithm.

### 7.4 Limitations of this measurement

- Fixture is small (`f3_4_compaction_slide`, ~3 placements); per-call ns precision is good but absolute totals are tiny.
- LV8 CGAL profile run was **not** executed in this task — see Limitations §9.

---

## 8. Correctness and behavior preservation

- **Placement output:** byte-identical across runs A/B/C/D/E (verified with `diff`).
- **Stats output (other than new `can_place_profile_*` fields):** byte-identical between profile-on and profile-off (verified field-by-field in §7.3).
- **Boolean decision equivalence:** unit-tested across 5 control cases (`can_place_and_profiled_return_equal_booleans_across_control_cases`).
- **False-accept risk:** zero — `can_place_profiled` shares branch-identical conditions with `can_place`. The dispatcher only adds aggregation, never weakens the test.
- **No silent fallback** introduced; no provider policy change; no candidate ordering change; no CFR algorithm change.
- **Borrow-checker correctness:** `can_place_dispatch(... stats: &mut NfpPlacerStatsV1, profile_enabled: bool)` takes a single mutable borrow per call site; pre-existing surrounding mutations of `stats` (e.g. `stats.active_set_can_place_checks += 1`) are sequenced before the dispatcher call and release the borrow before the call. `cargo check` confirms.

---

## 9. Limitations

1. **No LV8 CGAL smoke executed in this task.** The 3 acceptance smokes listed in the prompt §9 are demonstrated on the small synthetic fixture (`f3_4_compaction_slide_fixture_v2.json`) only. A full LV8 + cgal_reference + 95s SA run was deliberately avoided to stay within the "no long benchmark matrix" rule. The behavior demonstrated here generalizes — the gating is per-eprintln and the dispatcher is structurally identical to the call it replaces — but a full LV8 timing comparison is **not** in this task.
2. **`can_place_profile_total_ns` includes dispatcher overhead.** It records the wall clock around the `can_place_profiled` call (so it captures the function entry/return cost beyond the three sub-stages). For sub-stage attribution use `boundary_ns_total + broad_phase_ns_total + narrow_phase_ns_total`; the residual is dispatcher / setup overhead.
3. **Pre-existing failing test** (`cfr_sort_key_precompute_hash_called_once_per_component`) verified failing on unmodified `main`; not addressed here.
4. **`segment_pair_checks` field of `CanPlaceProfile`** is computed but not aggregated into `NfpPlacerStatsV1` — its calculation in `narrow.rs` is currently mid-refactor (it resets and recomputes inside the loop). Left untouched in T06l-a (no logic change to `narrow.rs` outside the new test).
5. **`emit_summary` (NFP_RUNTIME_DIAG_V1) gating** was already in place and is left as-is.

---

## 10. Recommended next task

**Primary recommendation: T06l-b / T06m — Active-set candidate-first measured integration (with `can_place_profile` enabled).**

Rationale:
- The blind spot is now lit. We can quantify whether `can_place` is on the critical path for active-set runs before committing to the integration.
- Active-set is already implemented behind `NESTING_ENGINE_ACTIVE_SET_CANDIDATES=1`. The next step is a measured benchmark on the prepacked LV8 + cgal_reference path comparing default-CFR vs active-set with `NESTING_ENGINE_CAN_PLACE_PROFILE=1` so we can tell *where* the time goes.

**Alternative if T06l-b is blocked:** **T06l-c — placed-shape NFP cache key** (option B from the audit). Cache hit rate is already 99.32%, so this is a smaller win, but it is independent and low-risk.

---

## 11. Final verdict

**T06l-a is complete.** Default behavior is preserved (placement + non-profile stats byte-identical), hot-path log spam is gone by default, and `can_place` profiling is now a one-flag opt-in producing actionable boundary / broad / narrow / accept / reject breakdowns. One pre-existing test failure in `nfp::cfr::tests` is documented and verified independent of these changes. Ready for T06l-b / T06m.
