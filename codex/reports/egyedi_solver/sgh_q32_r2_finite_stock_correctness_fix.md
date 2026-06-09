# SGH-Q32-R2 Finite-Stock Multisheet Correctness Fix (R2) — Codex Report

## Status

**PASS**

---

## 1. Meta

- **Task slug:** `sgh_q32_r2_finite_stock_correctness_fix`
- **Date:** 2026-06-09
- **Branch / commit:** `main / pending`
- **Base:** SGH-Q32-R1 (`main@17ac96f`)
- **Focus:** Correctness | Time-Limit Enforcement (wall_s) | score_breakdown Reporting | Smoke Fix

---

## 2. Scope

### 2.1 Issues Fixed (per Q32-R2 audit)

1. **Smoke FAIL**: `Q32_CASE03_STATUS:` marker corrupted as `Q32_CASE03_STAQ32_CASE01_PLACED:` in the Q32 codex report.
2. **Wall time overrun**: `sparrow_ms_runtime_ms=1193911ms` within gate but `wall_s=1214.19s > time_limit+5s=1205s`.
3. **score_breakdown.usable_area_utilization misleading**: `1.0` (bbox-based, capped) vs true polygon utilization of 74.1%.
4. **Runner gate missing**: `wall_s ≤ time_limit+5s` not enforced.

### 2.2 Non-goals

- No changes to Sparrow search strategy, GLS weights, worker logic, or compression.
- No changes to CDE core or base-shape cache.
- No changes to existing integration test fixtures.
- Gate relaxation not permitted.

---

## 3. Root Cause Analysis

### 3.1 Corrupted Q32 report marker

Line 211 of `sgh_q32_finite_stock_sparrow_multisheet_manager.md` had two markers merged:
`Q32_CASE03_STAQ32_CASE01_PLACED: 276` instead of:
```
Q32_CASE03_STATUS: PASS
Q32_CASE01_PLACED: 276
```
The smoke script searched for `Q32_CASE03_STATUS:` as a substring — not found → FAIL.

### 3.2 Wall time overrun

`sparrow_ms_runtime_ms` starts AFTER JSON input deserialization and adapter setup. For LV8-dense (276 parts, complex polygons), JSON parse + adapter prep + output serialization adds ~20s overhead outside the Sparrow timer. With GUARD=65s: `sparrow_ms_runtime ≈ 1194s`, `wall_s ≈ 1194 + 20 = 1214s > 1205s gate`.

Fix: increase `FULL_POOL_GUARD_S: 65.0 → 90.0`. Derivation: `GUARD ≥ iter_overrun(27) + OH_sparrow(39) + IO_overhead(20) - gate_tolerance(5) = 81s` → using 90s for 9s margin.

Expected: `sparrow_ms_runtime ≈ 1169s`, `wall_s ≈ 1169 + 20 = 1189s ≤ 1205s ✓`.

### 3.3 score_breakdown.usable_area_utilization misleading

`phase1_score_breakdown_for_backend` uses bbox area as the optimizer's internal "placed area reward." For LV8 parts (bbox overestimates polygon by 2.277×), `placed_area_contribution = -15,187,542` and `usable_area_utilization = bbox_area / sheet_area = 1.688 → capped to 1.0`. This is correct for the optimizer objective but misleading as a user-facing utilization metric.

Fix: in `adapter.rs`, after computing Phase1 score_breakdown, if the pipeline is `SparrowCdeMultisheet`, override `usable_area_utilization` with `sparrow_ms_placed_part_area / sparrow_ms_used_sheet_area` (polygon-based, consistent with `sparrow_ms_utilization_pct`).

---

## 4. Change Summary

### 4.1 Modified Files

**`codex/reports/egyedi_solver/sgh_q32_finite_stock_sparrow_multisheet_manager.md`**
- Fixed corrupted marker on line 211: `Q32_CASE03_STAQ32_CASE01_PLACED: 276` → two separate lines.

**`rust/vrs_solver/src/optimizer/sparrow/multisheet.rs`**
- `FULL_POOL_GUARD_S`: `65.0 → 90.0` to account for I/O overhead outside Sparrow timer.

**`rust/vrs_solver/src/adapter.rs`**
- For `SparrowCdeMultisheet` pipeline: override `score_breakdown.usable_area_utilization` with polygon-based value from multisheet diagnostics.

**`scripts/run_sgh_q32_finite_stock_multisheet_lv8.py`**
- Added `wall_s ≤ TIME_LIMIT_S + 5` gate for all 3 cases.

---

## 5. Verification

### 5.1 Mandatory commands

```
cargo build --manifest-path rust/vrs_solver/Cargo.toml --release   → PASS (11.69s)
cargo test  --manifest-path rust/vrs_solver/Cargo.toml --lib        → PASS (455 passed, 174s)
cargo test  --manifest-path rust/vrs_solver/Cargo.toml --test sparrow_finite_stock_multisheet → PASS (8 passed, 13.80s)
python3 scripts/smoke_sgh_q32_finite_stock_multisheet.py            → PASS (89/89)
python3 scripts/run_sgh_q32_finite_stock_multisheet_lv8.py          → PASS (all 3 cases; wall_s 687/701/1198s)
./scripts/check.sh                                                   → PENDING
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q32_r2_finite_stock_correctness_fix.md → PENDING
```

---

## 6. DoD → Evidence Matrix

| DoD point | Status | Evidence |
|---|---|---|
| Corrupted Q32 marker fixed | PASS | `sgh_q32_finite_stock_sparrow_multisheet_manager.md:211` |
| Smoke PASS ≥ 89/89 | PASS | 89/89 after marker fix |
| `FULL_POOL_GUARD_S` = 90s | PASS | `multisheet.rs:561` |
| `wall_s ≤ time_limit+5s` gate in runner | PASS | `run_sgh_q32_finite_stock_multisheet_lv8.py` |
| `score_breakdown.usable_area_utilization` polygon-based for multisheet | PASS | `adapter.rs:1515-1540` |
| Case 01 PASS | PASS | 276/276 ok, 2 sheets, util=74.11%, runtime=661s, wall=687s |
| Case 02 PASS | PASS | 276/276 ok, 2/3 sheets, util=74.11%, runtime=675s, wall=701s |
| Case 03 PASS (wall_s ≤ 1205s) | PASS | 272/276 partial, 3 sheets, util=50.35%, runtime=1176s, wall=1198s |
| 8 integration tests | PASS | `cargo test --test sparrow_finite_stock_multisheet` |
| 455 lib tests | PASS | `cargo test --lib` (455 passed, 174s) |

---

## 7. LV8 Benchmark Results

| Case | Status | Placed | Used Sheets | Utilization % | Runtime ms | Wall s | score_bd util | Gate |
|---|---|---|---|---|---|---|---|---|
| Case 01 (2×1500×3000) | PASS | 276/276 | 2/2 | 74.11% | 661,497 | 687.3 | 0.7411 | ≤1205s ✓ |
| Case 02 (3×1500×3000) | PASS | 276/276 | 2/3 | 74.11% | 675,207 | 701.4 | 0.7411 | ≤1205s ✓ |
| Case 03 (1×1500×3000+2×1000×2000) | PASS | 272/276 partial | 3/3 | 50.35% | 1,176,058 | 1198.2 | 0.5035 | ≤1205s ✓ |

---

<!-- Marker lines (updated after benchmark) -->

Q32R2_STATUS: PASS
Q32R2_CASE01_STATUS: PASS
Q32R2_CASE02_STATUS: PASS
Q32R2_CASE03_STATUS: PASS
Q32R2_CASE03_RUNTIME_MS: 1176058
Q32R2_CASE03_WALL_S: 1198.2
Q32R2_CASE01_SCORE_BD_UTIL: 0.7411
Q32R2_FINAL_VERDICT: PASS

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-06-09T22:07:32+02:00 → 2026-06-09T22:10:45+02:00 (193s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/sgh_q32_r2_finite_stock_correctness_fix.verify.log`
- git: `main@33de5ec`
- módosított fájlok (git status): 1

**git diff --stat**

```text
 ..._q32_r2_finite_stock_correctness_fix.verify.log | 8821 ++++++++++++++++++++
 1 file changed, 8821 insertions(+)
```

**git status --porcelain (preview)**

```text
 M codex/reports/egyedi_solver/sgh_q32_r2_finite_stock_correctness_fix.verify.log
```

<!-- AUTO_VERIFY_END -->
