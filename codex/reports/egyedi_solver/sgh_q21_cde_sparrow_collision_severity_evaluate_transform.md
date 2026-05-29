PASS

# Report — SGH-Q21 CDE/Sparrow Collision Severity + evaluate_transform

SGH-Q21_STATUS: COMPLETE

---

## 1) Meta

* **Task slug:** `sgh_q21_cde_sparrow_collision_severity_evaluate_transform`
* **Kapcsolódó canvas:** `canvases/egyedi_solver/sgh_q20r_sparrow_search_position_coord_descent.md`
* **Futás dátuma:** 2026-05-29
* **Branch / commit:** main / 4e09b3d (uncommitted changes on top)
* **Fókusz terület:** Geometry | Mixed

---

## 2) Scope

### 2.1 Cél

1. Replace bbox/proxy collision severity in optimizer scoring paths with backend-confirmed oracle-probe severity under CDE/JaguaPolygonExact backends.
2. Create central `collision_severity.rs` module with `evaluate_transform_loss()`, `compute_probe_pair_severity()`, `compute_probe_boundary_severity()`.
3. Refactor `search_position.rs` to delegate to the central severity engine (remove local `eval_with_backend_trait` / `eval_candidate_loss`).
4. Wire oracle-probe severity into `VrsCollisionTracker.pair_loss()` and `boundary_loss()` in `separator.rs`.
5. Propagate severity diagnostics through `VrsSeparatorDiagnostics` → `PhaseDiagnostics` → `OptimizerDiagnosticsOutput` → `adapter.rs`.
6. Create `scripts/smoke_sgh_q21_collision_severity.py` (5 fixtures, all pass).

### 2.2 Nem-cél (explicit)

1. Q19 LV8 benchmark gate — not implemented here.
2. Q18B CDE session/cache rewrite — not required.
3. Q22 shrink-loop redesign — out of scope.
4. Hole-aware collision in main solver (Q15 constraint: outer-only).

---

## 3) Változások összefoglalója

### 3.1 Érintett fájlok

**New:**
* `rust/vrs_solver/src/optimizer/collision_severity.rs` — central severity engine (oracle-probe, config, stats, 7 unit tests)
* `scripts/smoke_sgh_q21_collision_severity.py` — 5-fixture end-to-end smoke (42 checks, all pass)

**Modified:**
* `rust/vrs_solver/src/optimizer/mod.rs` — `pub mod collision_severity;`
* `rust/vrs_solver/src/optimizer/search_position.rs` — removed local bbox-proxy eval functions; `eval_at_point` delegates to `collision_severity::evaluate_transform_loss`; new `severity_cfg` / `severity_stats` fields; 2 Q21 unit tests
* `rust/vrs_solver/src/optimizer/separator.rs` — `VrsCollisionTracker` extended with `pair_probe_severity`, `boundary_probe_severity`, `severity_cfg`, `severity_stats`; oracle probes in `compute_backend_decisions` and `update_backend_decisions_for_item`; `pair_loss()` / `boundary_loss()` use probe severity; `VrsSeparatorDiagnostics.severity_stats`; 2 Q21 unit tests
* `rust/vrs_solver/src/optimizer/phase.rs` — 8 `collision_severity_*` fields in `PhaseDiagnostics` + accumulation in main `run()` struct literal
* `rust/vrs_solver/src/optimizer/explore.rs` — accumulate severity stats from `sep_diag.severity_stats`
* `rust/vrs_solver/src/optimizer/compress.rs` — accumulate severity stats from `sep_diag.severity_stats`
* `rust/vrs_solver/src/io.rs` — 9 `collision_severity_*` fields in `OptimizerDiagnosticsOutput`
* `rust/vrs_solver/src/adapter.rs` — wire severity fields from `diag_ref` to `OptimizerDiagnosticsOutput`

---

## 4) Tesztek

### 4.1 Unit tesztek

| Teszt filter | Eredmény |
|---|---|
| `optimizer::collision_severity` | **7 passed** |
| `optimizer::search_position` | **13 passed** |
| `optimizer::separator` | **44 passed** |
| `adapter` | **55 passed** |
| `--lib` (teljes) | **394 passed, 0 failed** |

### 4.2 Smoke tesztek

| Script | Eredmény |
|---|---|
| `smoke_sgh_q20r_sparrow_search_position.py` | **37 passed, 0 failed — SMOKE: PASS** |
| `smoke_sgh_q21_collision_severity.py` | **42 passed, 0 failed — SMOKE: PASS** |

---

## 5) Severity engine design

### Oracle-probe strategy

When the backend confirms a collision (`CollisionDecision::Collision`), the engine probes in +x/−x/+y/−y directions with a doubling step until the backend reports `NoCollision`. The minimum resolution distance is used as the severity signal — this is monotonically related to overlap depth.

* Initial step = `probe_initial_step_factor * sheet_diagonal` (default: 5%)
* Max steps per direction: 5
* `.max(1.0)` ensures minimum loss of 1.0 for confirmed collisions

### Backend-specific behavior

| Backend | Behavior |
|---|---|
| `Bbox` | Early-exit via `eval_bbox_loss` — no oracle calls, no stats tracked |
| `JaguaPolygonExact` | Oracle-probe severity — `bbox_proxy_uses == 0` |
| `CDE` | Oracle-probe severity — `bbox_proxy_uses == 0`, `bbox_fallback_queries == 0` |

### Key diagnostic fields (all in `optimizer_diagnostics`)

| Field | Meaning |
|---|---|
| `collision_severity_backend` | Rust Debug name of backend (`"Bbox"`, `"JaguaPolygonExact"`, `"Cde"`) |
| `collision_severity_enabled` | `true` when any separator ran |
| `collision_severity_boundary_queries` | Boundary checks via oracle (from `eval_at_point`) |
| `collision_severity_pair_queries` | Pair checks via oracle (from `eval_at_point`) |
| `collision_severity_probe_queries` | Oracle probe steps fired |
| `collision_severity_backend_confirmed_collisions` | Collisions confirmed by oracle |
| `collision_severity_backend_confirmed_no_collisions` | No-collisions confirmed (bbox false-positive elim.) |
| `collision_severity_unsupported_queries` | Unsupported geometry queries |
| `collision_severity_bbox_proxy_uses` | Times bbox proxy was used (probe disabled path only) |

---

## 6) Checklist

- [x] `collision_severity.rs` created with oracle-probe + config + stats
- [x] `search_position.rs` — removed local eval functions, delegates to central module
- [x] `separator.rs` — `VrsCollisionTracker` uses oracle-probe severity in `pair_loss()` / `boundary_loss()`
- [x] `phase.rs` — 8 `collision_severity_*` fields in `PhaseDiagnostics`
- [x] `explore.rs` + `compress.rs` — accumulate severity stats
- [x] `io.rs` — 9 fields in `OptimizerDiagnosticsOutput`
- [x] `adapter.rs` — wired
- [x] All 394 lib tests pass
- [x] Smoke Q20R: 37/37 PASS
- [x] Smoke Q21: 42/42 PASS

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-05-29T20:07:24+02:00 → 2026-05-29T20:10:26+02:00 (182s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/sgh_q21_cde_sparrow_collision_severity_evaluate_transform.verify.log`
- git: `main@4e09b3d`
- módosított fájlok (git status): 16

**git diff --stat**

```text
 rust/vrs_solver/src/adapter.rs                   |  10 +
 rust/vrs_solver/src/io.rs                        |  10 +
 rust/vrs_solver/src/optimizer/compress.rs        |   9 +
 rust/vrs_solver/src/optimizer/explore.rs         |   9 +
 rust/vrs_solver/src/optimizer/mod.rs             |   1 +
 rust/vrs_solver/src/optimizer/phase.rs           |  38 ++++
 rust/vrs_solver/src/optimizer/search_position.rs | 195 +++++++++---------
 rust/vrs_solver/src/optimizer/separator.rs       | 240 ++++++++++++++++++++---
 8 files changed, 382 insertions(+), 130 deletions(-)
```

**git status --porcelain (preview)**

```text
 M rust/vrs_solver/src/adapter.rs
 M rust/vrs_solver/src/io.rs
 M rust/vrs_solver/src/optimizer/compress.rs
 M rust/vrs_solver/src/optimizer/explore.rs
 M rust/vrs_solver/src/optimizer/mod.rs
 M rust/vrs_solver/src/optimizer/phase.rs
 M rust/vrs_solver/src/optimizer/search_position.rs
 M rust/vrs_solver/src/optimizer/separator.rs
?? canvases/egyedi_solver/sgh_q21_cde_sparrow_collision_severity_evaluate_transform.md
?? codex/codex_checklist/egyedi_solver/sgh_q21_cde_sparrow_collision_severity_evaluate_transform.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q21_cde_sparrow_collision_severity_evaluate_transform.yaml
?? codex/prompts/egyedi_solver/sgh_q21_cde_sparrow_collision_severity_evaluate_transform/
?? codex/reports/egyedi_solver/sgh_q21_cde_sparrow_collision_severity_evaluate_transform.md
?? codex/reports/egyedi_solver/sgh_q21_cde_sparrow_collision_severity_evaluate_transform.verify.log
?? rust/vrs_solver/src/optimizer/collision_severity.rs
?? scripts/smoke_sgh_q21_collision_severity.py
```

<!-- AUTO_VERIFY_END -->
