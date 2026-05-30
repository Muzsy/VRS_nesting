PASS

# Report — SGH-Q22 Real SparrowState + Separation Kernel with Measurement

SGH-Q22_STATUS: READY_FOR_AUDIT
SPARROW_EXPERIMENTAL_STATUS: TESTABLE
SGH-Q23_STATUS: HOLD
Q19_STATUS: HOLD
Q18B_RECOMMENDATION: NOT_REQUIRED_NOW

---

## 1) Meta

* **Task slug:** `sgh_q22_sparrow_state_separation_kernel`
* **Kapcsolódó canvas:** `canvases/egyedi_solver/sgh_q22_sparrow_state_separation_kernel.md`
* **Kapcsolódó goal YAML:** `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q22_sparrow_state_separation_kernel.yaml`
* **Futás dátuma:** 2026-05-30
* **Branch / commit:** main / 74d8c05 (uncommitted changes on top)
* **Fókusz terület:** Solver mode | Mixed

---

## 2) Dependency gate

```text
codex/reports/egyedi_solver/sgh_q20r_r1_topk_report_consistency_fix.md      → SGH-Q20R_R1_STATUS: READY_FOR_AUDIT
codex/reports/egyedi_solver/sgh_q21r1_collision_severity_full_sparrow_alignment.md → SGH-Q21R1_STATUS: READY_FOR_AUDIT, SGH-Q22_STATUS: READY
```

Gate **PASS** — Q21R1-ből: oracle-probe severity + bracket+binary refinement + full query accounting; Q20R-R1-ből: top-k coord descent. Ezekre építünk.

---

## 3) Mit valósít meg Q22

Az első tesztelhető, mért **jagua_rs/Sparrow-stílusú solver mode**, nem PhaseOptimizer relabeling:

1. **Explicit `sparrow_experimental` pipeline** — `OptimizerPipelineKind::SparrowExperimental`, JSON: `"sparrow_experimental"`, dedicated adapter routing.
2. **`optimizer/sparrow.rs` modul** — `SparrowConfig`, `SparrowDiagnostics`, `SparrowState`, `CollisionGraphSnapshot`, `SparrowSeparationKernel`, `SparrowResult`.
3. **Intentional infeasible seed** — `build_sparrow_seed_layout()` minden fittable instancet beletesz az adott első sheet (0,0) pozíciójába, **overlapek megengedettek**. PART_NEVER_FITS_STOCK csak akkor, ha tényleg sehova nem fér.
4. **Deterministic CollisionGraphSnapshot** — pair / boundary counts, raw + weighted loss, worst item / pair / boundary index, max weights, top-K listák (sorted by weighted_loss DESC, instance_id ASC tie-break).
5. **Separation loop** — minden iterációban:
   - graph snapshot → `worst_item_index`
   - `search_position_for_target` relocate
   - tentative apply via `tracker.update_placement`
   - if `new_weighted_loss < prev_weighted_loss`: commit, else rollback `restore_but_keep_weights` (GLS megmarad)
   - minden `gls_update_period = 5` iteráción `update_weights` (Sparrow GLS guidance)
   - state refresh: új graph snapshot + best feasible/infeasible incumbent
6. **Final backend gate** — sikeres output csak `validate_and_commit_with_backend(...)` után, különben honest `unsupported` (`SPARROW_NO_FEASIBLE_LAYOUT`).
7. **No silent bbox fallback** alatt CDE/Jagua: `bbox_fallback_queries == 0` (test + smoke + bench).
8. **LBF fallback disabled by default** Sparrow alatt (`SparrowConfig.allow_lbf_fallback = false`).

---

## 4) Érintett fájlok

**Új:**

* `rust/vrs_solver/src/optimizer/sparrow.rs` — kernel (~700 LOC), 9 unit teszt
* `scripts/smoke_sgh_q22_sparrow_kernel.py` — 5 fixture + determinism + CDE no-fallback (14 check)
* `scripts/bench_sgh_q22_sparrow_kernel.py --quick` — matrix benchmark, JSON+MD output
* `codex/reports/egyedi_solver/sgh_q22_sparrow_state_separation_kernel.md` — ez a report
* `codex/reports/egyedi_solver/sgh_q22_sparrow_state_separation_kernel.verify.log` — verify.sh log
* `codex/reports/egyedi_solver/sgh_q22_sparrow_state_separation_kernel_measurements.json/.md` — bench output

**Módosított:**

* `rust/vrs_solver/src/io.rs` — `OptimizerPipelineKind::SparrowExperimental`, 26 új `Option<T>` mező `OptimizerDiagnosticsOutput`-ban (`#[serde(skip_serializing_if = "Option::is_none")]`)
* `rust/vrs_solver/src/optimizer/mod.rs` — `pub mod sparrow;`
* `rust/vrs_solver/src/adapter.rs` — új match arm a `pipeline` switchben Sparrow-ra; 4 új adapter integration teszt

---

## 5) Sparrow kernel architektúra

### 5.1 SparrowState

```text
layout                        - WorkingLayout (current, may be infeasible)
tracker                       - VrsCollisionTracker (severity engine + GLS weights)
current_raw_loss              - tracker.total_loss()
current_weighted_loss         - tracker.total_weighted_loss()
best_feasible_layout          - Option<WorkingLayout>
best_infeasible_layout        - Option<WorkingLayout>
best_infeasible_raw/weighted_loss
current_graph                 - CollisionGraphSnapshot
iteration, moves_attempted/accepted, rollbacks, gls_weight_updates
seed
```

`refresh()` minden iteráció után újra felépíti a graph snapshotot, frissíti a current/best metrikákat, és ha `is_feasible()` → tárolja `best_feasible_layout`-ba.

### 5.2 CollisionGraphSnapshot

Deterministic snapshot a tracker-ből: `O(n²)` pair_loss + boundary_loss végigjárás. Sorrendben:
- minden pair (i, j), i < j esetén ha `pair_loss > 0`: pair, weight, weighted_loss
- minden item i esetén ha `boundary_loss > 0`: boundary, weight, weighted_loss
- `per_item_weighted[i]` = Σ pair_weighted incidens-re + boundary_weighted

`worst_item_index` = max `per_item_weighted` (ties → `instance_id` ASC).

### 5.3 SparrowSeparationKernel.run() lifecycle

```text
state = SparrowState::new(seed_layout, tracker)
if state.is_feasible(): return finalize()

loop iter in 0..max_iterations:
    if time_limit_s elapsed: break
    if state.is_feasible(): break
    target_idx = state.current_graph.worst_item_index

    moves_attempted++
    new_p = search_position_for_target(layout, target_idx, ...)
    if new_p is None:
        update_weights()  # avoid stuck on same target
        gls_weight_updates++
        refresh()
        continue

    snap = tracker.snapshot_loss()
    old_p = layout.placements[target_idx]
    layout.placements[target_idx] = new_p
    tracker.update_placement(target_idx, layout, parts, sheets)
    new_weighted = tracker.total_weighted_loss()
    new_raw = tracker.total_loss()

    if new_weighted < prev_weighted - eps OR (eq and new_raw < prev_raw - eps):
        moves_accepted++
        current_raw/weighted = new_raw/new_weighted
    else:
        layout.placements[target_idx] = old_p
        tracker.restore_but_keep_weights(snap)   # GLS weights survive
        rollbacks++

    if iter % gls_update_period == 0:
        tracker.update_weights(...)
        gls_weight_updates++

    state.refresh()

return finalize(state, diag)
```

### 5.4 Final commit (adapter side)

```text
sparrow_result = SparrowSeparationKernel::new(cfg).run(seed_layout, parts, sheets)
if !sparrow_result.feasible:
    return _unsupported_output("SPARROW_NO_FEASIBLE_LAYOUT", ...)
match layout.validate_and_commit_with_backend(parts, sheets, backend_kind):
    Ok(commit) => emit OptimizerDiagnosticsOutput { pipeline_used="sparrow_experimental", ... }
    Err(_) => _unsupported_output("SPARROW_COMMIT_VIOLATION_BACKEND", ...)
```

Tehát colliding layout sosem kerül ki sikeres output-ként.

---

## 6) Diagnostics output

26 új `Option<T>` mező az `OptimizerDiagnosticsOutput`-ban (CSAK sparrow_experimental-nél töltődik), `#[serde(skip_serializing_if = "Option::is_none")]`:

```text
pipeline_used = "sparrow_experimental"
sparrow_invoked, sparrow_converged
sparrow_seed_placements, sparrow_seed_unplaced
sparrow_initial_raw_loss, sparrow_initial_weighted_loss
sparrow_final_raw_loss, sparrow_final_weighted_loss
sparrow_best_infeasible_raw_loss, sparrow_best_infeasible_weighted_loss
sparrow_iterations, sparrow_moves_attempted, sparrow_moves_accepted, sparrow_rollbacks
sparrow_gls_weight_updates
sparrow_collision_graph_initial_pairs, sparrow_collision_graph_final_pairs
sparrow_boundary_violations_initial, sparrow_boundary_violations_final
sparrow_search_position_calls, sparrow_search_position_samples
sparrow_severity_pair_queries, sparrow_severity_boundary_queries, sparrow_severity_probe_queries
sparrow_lbf_fallback_used
```

A `phase_optimizer` és `legacy_multisheet` outputban ezek `None` és nem szerializálódnak → backward-compatible.

---

## 7) Tests

### 7.1 Unit tests (`optimizer::sparrow`, 9 db)

| Teszt | Verifikál |
|---|---|
| `sparrow_seed_layout_includes_all_fit_instances` | seed = minden fittable, never-fit = PART_NEVER_FITS_STOCK |
| `sparrow_state_allows_infeasible_intermediate_layout` | overlapping seed → `current_raw_loss > 0` és `!is_feasible()` |
| `collision_graph_snapshot_counts_pair_and_boundary_violations` | 2 overlapping rect → `colliding_pairs_count == 1` |
| `sparrow_selects_worst_weighted_collider_deterministically` | 2 egymás utáni snapshot ugyanazt a `worst_item_index`-et adja |
| `sparrow_move_commit_improves_loss_or_rolls_back` | `moves_accepted + rollbacks == moves_attempted`, `final_raw_loss ≤ initial_raw_loss` |
| `sparrow_rollback_preserves_gls_weights` | `pair_weight` változatlan rollback előtt és után |
| `sparrow_kernel_resolves_two_rect_overlap` | converges to feasible (pairs=0, boundaries=0) |
| `sparrow_kernel_boundary_recovery` | boundary violation pulled inside |
| `sparrow_kernel_same_seed_is_deterministic` | két futás ugyanazt a placement listát adja |

### 7.2 Adapter integration tests (4 db)

| Teszt | Verifikál |
|---|---|
| `sparrow_pipeline_routes_from_adapter` | `pipeline_used == "sparrow_experimental"`, `sparrow_invoked = Some(true)` |
| `sparrow_pipeline_final_commit_uses_selected_backend` | JaguaPolygonExact → `backend_used` tartalmaz "jagua" vagy "exact" |
| `sparrow_pipeline_cde_has_no_bbox_fallback` | CDE → `bbox_fallback_queries == 0` |
| `sparrow_pipeline_same_seed_is_deterministic` | adapter-szinten determinism |

### 7.3 Cargo eredmények

```text
cargo test optimizer::sparrow                    → 9 passed
cargo test optimizer::separator                  → 47 passed
cargo test optimizer::search_position            → 14 passed
cargo test optimizer::collision_severity         → 13 passed
cargo test adapter (csak sparrow_pipeline_*)     → 4 passed
cargo test --lib                                 → 417 passed, 0 failed
```

### 7.4 Smoke (`scripts/smoke_sgh_q22_sparrow_kernel.py`) — **14/14 PASS**

| Fixture | Init pairs | Final pairs | Iters | Moves acc/att | Feasible |
|---|---:|---:|---:|---:|:---:|
| overlap_two_rects | 1 | 0 | 2 | 1/1 | ✓ |
| boundary_recovery | 0 | 0 | 0 | 0/0 | ✓ |
| three_item_collision_chain | 3 | 0 | 3 | 2/2 | ✓ |
| continuous_rotation_rescue | 1 | 0 | 2 | 1/1 | ✓ |
| medium_10_to_20_items | **66** | **0** | 12 | 11/11 | ✓ |

A `medium_10_to_20_items` fixture 12 part × 200×200 sheet × 2: initial state 66 pair collision (mind a (12 choose 2)), 11 separation move alatt mind 0-ra resolved. **0 rollback** mind az 5 fixture-ön → az adaptive search_position + oracle severity nagyon hatékony.

### 7.5 Bench (`scripts/bench_sgh_q22_sparrow_kernel.py --quick`)

Matrix: 2 fixtures × 2 pipelines × 2 backends × 3 seeds = 24 run. Output:
- `codex/reports/egyedi_solver/sgh_q22_sparrow_state_separation_kernel_measurements.json`
- `codex/reports/egyedi_solver/sgh_q22_sparrow_state_separation_kernel_measurements.md`

**Honest results:**

| Pipeline × Backend | medium (12 parts) | synthetic (30 parts) |
|---|---|---|
| phase_optimizer + bbox | ok 3-4 ms, all placed | ok ~20 ms, all placed |
| phase_optimizer + cde | **timeout 30s** (existing PhaseOptimizer + CDE issue, independent of Q22) | timeout 30s |
| **sparrow_experimental + bbox** | **ok 2-3 ms, 100% feasible (66 pairs → 0, 11 moves)** | **ok 8-10 ms, 100% feasible (435 pairs → 0, 29 moves)** |
| sparrow_experimental + cde | `unsupported` ~20 s (CDE + multi-direction probe too expensive per iter; see Limitations) | timeout 30s |

Sparrow + bbox: **6 / 6 convergent, 0 % loss after final** (100% reduction from initial overlap loss). 30-item synthetic fixture: 435 initial pair collisions → 0 final in 29 moves. Sparrow is the *only* pipeline that handles both fixtures in <10 ms with full feasibility on bbox.

Sparrow + CDE under medium fixture finishes within 20 s but emits `SPARROW_NO_FEASIBLE_LAYOUT` (honest reporting) — the multi-direction oracle probe (9 directions × bracket+binary refine) is currently too expensive on dense layouts during the separation loop. This is the same pattern as the existing PhaseOptimizer + CDE timeout (not a Q22 regression). The Q22 kernel honestly returns `unsupported` rather than emit invalid placements.

---

## 8) Known limitations (PASS-mellett megengedett)

* **Nincs LV8 acceptance gate** — Q22 fixture-jei kis/közepes méretűek; a 276-part LV8 benchmark Q19 scope. A Sparrow kernel működéséhez ez nem feltétel.
* **Nincs full multi-sheet minimization objective** — a kernel a kollíziófeloldásra fókuszál; a sheet-count-reduction explicit Q23 task (strip-shrink / Algorithm 12/13 parity).
* **Nincs Sparrow Algorithm 12/13 strip-shrink parity** — Q23 task.
* **Nincs true overlap-area metric** — a probe-based resolution-distance jó proxy, és a Q21R1 bracket+binary refinement értelmes severity signalt ad. Áttéres a teljes overlap-area metrikára Q23-ban opcionális.
* **CDE session/cache** — Q18B nem szükséges Q22 acceptance-hez. A bench megmutatja, hogy Sparrow + CDE jelenleg drága: a 12-part medium fixture-en 8352 CDE query × ~20s után `SPARROW_NO_FEASIBLE_LAYOUT`-ot ad — a multi-direction probe (9 directions × bracket+binary refine) iterációnként sok backend query-t generál a CDE backend mellett. Ugyanez a probléma a meglévő PhaseOptimizer + CDE-nél is timeout-ot okoz (independent of Q22). Q18B CDE session/cache rewrite vagy a probe cfg lecsökkentése Sparrow esetén — Q18B/Q23 scope. A Q22 kernel honest módon `unsupported`-et ad, sosem emit invalid colliding placements.

### 8.1 Nem megengedett ismert hibák (mind ellenőrizve, nincs ilyen)

- ❌ sparrow_experimental csak phase_optimizer relabel → ✅ saját kernel, saját state, saját graph
- ❌ no explicit infeasible state → ✅ SparrowState `best_infeasible_layout` + `current_raw_loss > 0` allowed
- ❌ no collision graph snapshot → ✅ `CollisionGraphSnapshot::from_tracker()` deterministic
- ❌ no separation loop → ✅ explicit `SparrowSeparationKernel::run()` 60+ LOC loop
- ❌ no measurement script → ✅ smoke + bench
- ❌ CDE uses bbox fallback silently → ✅ adapter teszt: `bbox_fallback_queries == 0`
- ❌ invalid colliding layout emitted as successful → ✅ `!feasible` → unsupported output

---

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-05-30T05:29:41+02:00 → 2026-05-30T05:32:53+02:00 (192s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/sgh_q22_sparrow_state_separation_kernel.verify.log`
- git: `main@a308494`
- módosított fájlok (git status): 15

**git diff --stat**

```text
 rust/vrs_solver/src/adapter.rs       | 248 +++++++++++++++++++++++++++++++++++
 rust/vrs_solver/src/io.rs            |  53 ++++++++
 rust/vrs_solver/src/optimizer/mod.rs |   1 +
 3 files changed, 302 insertions(+)
```

**git status --porcelain (preview)**

```text
 M rust/vrs_solver/src/adapter.rs
 M rust/vrs_solver/src/io.rs
 M rust/vrs_solver/src/optimizer/mod.rs
?? README_SGH_Q22_PACKAGE.md
?? canvases/egyedi_solver/sgh_q22_sparrow_state_separation_kernel.md
?? codex/codex_checklist/egyedi_solver/sgh_q22_sparrow_state_separation_kernel.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q22_sparrow_state_separation_kernel.yaml
?? codex/prompts/egyedi_solver/sgh_q22_sparrow_state_separation_kernel/
?? codex/reports/egyedi_solver/sgh_q22_sparrow_state_separation_kernel.md
?? codex/reports/egyedi_solver/sgh_q22_sparrow_state_separation_kernel.verify.log
?? codex/reports/egyedi_solver/sgh_q22_sparrow_state_separation_kernel_measurements.json
?? codex/reports/egyedi_solver/sgh_q22_sparrow_state_separation_kernel_measurements.md
?? rust/vrs_solver/src/optimizer/sparrow.rs
?? scripts/bench_sgh_q22_sparrow_kernel.py
?? scripts/smoke_sgh_q22_sparrow_kernel.py
```

<!-- AUTO_VERIFY_END -->
