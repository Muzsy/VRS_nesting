# SGH-Q01 Corrected Task Roadmap

Minden task tartalmaz: objective, source feature, current VRS gap, dependency, allowed production files, required tests, required benchmark/acceptance gate, PASS marker.

Az SGH-Q00 gap matrix (F01–F18) referenciái minden tasknál jelölve vannak.

---

## Tier 0 — Annotáció (SGH-Q01)

### SGH-Q01 — Proxy annotáció + correction plan

| Mező | Tartalom |
|---|---|
| **Objective** | P06 QUALITY_RISK annotációk a 6 jelöletlen PROXY kódhelyhez; correction plan + roadmap + no-downgrade gates dokumentáció |
| **Source Sparrow/jagua-rs feature** | N/A — dokumentációs task; az annotáció a P06 elvet érvényesíti |
| **Current VRS gap** | 6 PROXY nincs annotálva (F01, F04, F05, F07); olvasó nem tudja megkülönböztetni a szándékos proxyt a hiányosságtól |
| **Dependency** | SGH-Q00 PASS + `SGH-Q01_STATUS: READY` |
| **Allowed production files** | `separator.rs`, `boundary.rs`, `item.rs`, `candidates.rs` — csak komment-szintű annotáció, logika nem változik |
| **Required tests** | `cargo test -p vrs_solver` 140/140 zöld (változatlan) |
| **Required benchmark/acceptance gate** | Nincs (annotáció nem érinti a viselkedést) |
| **PASS marker** | `SGH-Q02_STATUS: READY` a report végén |

---

## Tier 1 — GLS minőség

### SGH-Q02 — GLS parity + weight-preserving rollback

| Mező | Tartalom |
|---|---|
| **Objective** | `VrsCollisionTracker.update_weights()` cseréje Sparrow Algorithm 8 multiplicative formulára; `restore_but_keep_weights()` implementálása |
| **Source Sparrow/jagua-rs feature** | `sparrow/quantify/tracker.rs:113` — `update_weights()` (Algorithm 8): `multiplier = GLS_WEIGHT_DECAY` (no collision) vagy `GLS_WEIGHT_MIN_INC_RATIO + (MAX-MIN)*(loss/max_loss)` (collision); `restore_but_keep_weights()`: loss restore, weight megtartás |
| **Current VRS gap** | F07 PARTIAL: additive GLS, nincs max_loss normalizáció; F08 PARTIAL: rollback elveszti GLS súlyokat |
| **Dependency** | SGH-Q01 PASS |
| **Allowed production files** | `rust/vrs_solver/src/optimizer/separator.rs` |
| **Required tests** | `MultiplicativeGls`: nincs collision → weight konvergál 1.0-hoz; collision → weight ≥ min_ratio; `restore_but_keep_weights`: loss override de weight megmarad; determinism teszt (azonos input → azonos output) |
| **Required benchmark/acceptance gate** | Separator convergence teszt: overlapping fixture → `best_loss == 0.0` ugyanolyan itemszámnál; weight decay smoke: N iteration után jelöletlen pair weight < 1.5 |
| **PASS marker** | `SGH-Q03_STATUS: READY` |

---

### SGH-Q03 — Multi-worker move_items_multi

| Mező | Tartalom |
|---|---|
| **Objective** | N párhuzamos `SeparatorWorker` implementáció rayon `par_iter_mut` alapon; minden worker más véletlenszerű item-sorrenddel; legjobb weighted loss kiválasztása |
| **Source Sparrow/jagua-rs feature** | `sparrow/optimizer/separator.rs:146` — `move_items_multi()` (Algorithm 10): `self.workers.par_iter_mut().map(|worker| { worker.load(&master_sol, &ct); worker.move_items() }).sum()`; `worker.rs:40` — `move_items()` (Algorithm 5): colliding items shuffle + `search_placement` |
| **Current VRS gap** | F09 MISSING: single-threaded, deterministic worst-collider selection; nincs shuffle, nincs rayon |
| **Dependency** | SGH-Q02 PASS |
| **Allowed production files** | `rust/vrs_solver/src/optimizer/separator.rs`, `Cargo.toml` (rayon dependency ha nincs) |
| **Required tests** | `N=3` workers azonos input-on: legalább egy worker ≤ single-worker loss; seed alapú determinizmus: azonos seed → azonos output; worker count 1 → backward-compat (single-threaded ág) |
| **Required benchmark/acceptance gate** | 3-worker vs. 1-worker: dense 20+ item fixture → 3-worker same or fewer iterations to convergence |
| **PASS marker** | `SGH-Q04_STATUS: READY` |

---

## Tier 2 — Phase orchestration

### SGH-Q04 — Exploration/compression phase orchestration

| Mező | Tartalom |
|---|---|
| **Objective** | `ExplorationPhase` + `CompressionPhase` struktúrák; `InfeasibleSolutionPool`; `LargeItemSwapDisruption`; `PhaseConfig` per-phase time budget |
| **Source Sparrow/jagua-rs feature** | `sparrow/optimizer/explore.rs:21` — `exploration_phase()` (Algorithm 12): iteratív shrink + infeasible pool + disruption. `sparrow/optimizer/compress.rs:11` — `compression_phase()` (Algorithm 13): legjobb feasible-tól indul, shrink decay. `sparrow/config.rs`: `ExplorationConfig.time_limit`, `CompressionConfig.time_limit` |
| **Current VRS gap** | F11 MISSING: nincs exploration/compression orchestration; F12 MISSING: nincs infeasible pool; F13 PARTIAL: swap primitív megvan (SGH-05), de disruption loop nincs; F14 MISSING: nincs per-phase time budget |
| **Dependency** | SGH-Q03 PASS |
| **Allowed production files** | `rust/vrs_solver/src/optimizer/` — új fájlok: `explore.rs`, `compress.rs`, `phase.rs`; meglévő: `moves.rs` (disruption integrálás) |
| **Required tests** | Exploration: feasible solutions megőrződnek; infeasible pool loss-ascending sorrendben tárol; compression: best width monoton csökken; disruption: large item selection top-percentile-ból; phase time limit: time budget betartva |
| **Required benchmark/acceptance gate** | Exploration + compression vs. no-phase: density összehasonlítás 30+ item fixture-n; disruption: local minimum escape rate mérés (10 futás, stuck vs. escaped arány) |
| **PASS marker** | `SGH-Q05_STATUS: READY` |

---

### SGH-Q05 — BPP phase loop (sheet elimination iteratív)

| Mező | Tartalom |
|---|---|
| **Objective** | coroush `bp_explore.rs` iteratív sheet eliminálási loop VRS-natív implementálása a phase orchestration keretein belül |
| **Source Sparrow/jagua-rs feature** | coroush/sparrow `bp_explore.rs` (commit `5df9ce15`): iteratív sheet tryout → separator → accept/rollback loop |
| **Current VRS gap** | F16 PARTIAL: SGH-04 operátorok (sheet_elimination.rs) megvannak, de az iteratív loop hiányzik |
| **Dependency** | SGH-Q04 PASS |
| **Allowed production files** | `rust/vrs_solver/src/optimizer/sheet_elimination.rs`, új: `optimizer/bpp_phase.rs` |
| **Required tests** | Iteratív loop: minden eliminálási kísérlet rollback-safe; sheet count monoton csökkentési irány; find_violations-mentes output minden sikeres eliminálás után |
| **Required benchmark/acceptance gate** | Multi-sheet BPP fixture: sheet count reduction vs. SGH-04 baseline mérés |
| **PASS marker** | `SGH-Q06_STATUS: READY` |

---

## Tier 3 — Geometry layer

### SGH-Q06 — LossModel + smooth collision severity

| Mező | Tartalom |
|---|---|
| **Objective** | `LossModel` trait bevezetése; `BboxAreaLoss` (jelenlegi, PROXY-ként marad) és `PolePenetrationSmoothLoss` (Sparrow Algorithm 3); smooth boundary loss (nem bináris) |
| **Source Sparrow/jagua-rs feature** | `sparrow/quantify/overlap_proxy.rs` — Algorithm 3: `pd_decay = match pd >= epsilon { true => pd, false => epsilon²/(-pd + 2ε) }; total += pd_decay * min(r1,r2) * PI`; `CollisionTracker`: per-pair loss + weight struktúra |
| **Current VRS gap** | F05 PROXY: `bbox_overlap_area = dx*dy` (nincs smooth decay); F06 MISSING: shape-proportional penalty hiányzik; boundary loss bináris (0/1) |
| **Dependency** | SGH-Q05 PASS; surrogate/pole generáció előfeltétele a smooth loss-nak (F17 prerequisite) |
| **Allowed production files** | `rust/vrs_solver/src/optimizer/separator.rs`, új: `optimizer/loss_model.rs` |
| **Required tests** | `PolePenetrationSmoothLoss` folytonos az ε körül; nincs loss ugrás az ε határon; `BboxAreaLoss` backward-compat megmarad |
| **Required benchmark/acceptance gate** | BboxAreaLoss vs. PolePenetrationSmoothLoss: GLS convergence iterations összehasonlítás azonos fixture-n |
| **PASS marker** | `SGH-Q07_STATUS: READY` |

---

### SGH-Q07 — RotationPolicy trait

| Mező | Tartalom |
|---|---|
| **Objective** | `RotationPolicy` trait; `DiscreteRotationPolicy` wrapper (jelenlegi 0/90/180/270 logika köré); hardcoded rotációs lista eltávolítása a separator/candidates/moves-ból |
| **Source Sparrow/jagua-rs feature** | `jagua-rs/geometry/geo_enums.rs`: `RotationRange { None, Continuous, Discrete(Vec<f32>) }`; `search.rs:81`: `wiggle = item.allowed_rotation == RotationRange::Continuous` |
| **Current VRS gap** | F01 MISSING: `normalize_allowed_rotations` csak 0/90/180/270; `dims_for_rotation` hardcoded match; `Placement.rotation_deg: i64` |
| **Dependency** | SGH-Q06 PASS |
| **Allowed production files** | `rust/vrs_solver/src/item.rs`, `rust/vrs_solver/src/optimizer/separator.rs`, `rust/vrs_solver/src/optimizer/candidates.rs`, `rust/vrs_solver/src/optimizer/moves.rs`, új: `item/rotation_policy.rs` |
| **Required tests** | `DiscreteRotationPolicy` backward-compat: `[0,90,180,270]` ugyanazokat adja; `ContinuousRotationPolicy::sample(rng, range)` → f32 angle in `[0, 2π)`; separator/candidates/moves nem tartalmaz hardcoded rotation match |
| **Required benchmark/acceptance gate** | Discrete 4-szög vs. continuous rotation: density összehasonlítás irregular inputon (Phase 2 readiness gate) |
| **PASS marker** | `SGH-Q08_STATUS: READY` |

---

### SGH-Q08 — CollisionBackend + geometry preprocessing

| Mező | Tartalom |
|---|---|
| **Objective** | `CollisionBackend` trait: `BboxCollisionBackend` (jelenlegi) + `CDECollisionBackend` (jagua-rs CDEngine); `GeometryBackend` trait: `RectGeometryBackend` + `IrregularGeometryBackend`; shape preprocessing pipeline (simplification, offset, narrow concavity close); surrogate generation |
| **Source Sparrow/jagua-rs feature** | `jagua-rs/collision_detection/cd_engine.rs`: CDEngine quadtree + polygon + surrogate fast-fail; `jagua-rs/geometry/original_shape.rs`: preprocessing pipeline (offset, simplify, close_narrow_concavities); `jagua-rs/entities/item.rs`: `{ shape_orig: Arc<OriginalShape>, shape_cd: Arc<SPolygon> }` |
| **Current VRS gap** | F03 PROXY: transformation model; F04 PROXY: AABB only; F17 MISSING: preprocessing pipeline; F18 PROXY: irregular boundary (outer_points nem feldolgozott) |
| **Dependency** | SGH-Q07 PASS + Phase 2 scope decision (management sign-off) |
| **Allowed production files** | Új: `geometry/collision_backend.rs`, `geometry/cde_backend.rs`, `geometry/preprocessing.rs`; módosított: `item.rs`, `sheet.rs` |
| **Required tests** | `BboxCollisionBackend` backward-compat: rectangle-on-rectangle exact; `CDECollisionBackend`: L-shaped polygon containment + non-containment; preprocessing: simplification tolerance respected; surrogate poles ≤ shape boundary |
| **Required benchmark/acceptance gate** | AABB vs. CDE: irregular 50-item fixture false positive rate; preprocessing time vs. CDE collision speedup mérés |
| **PASS marker** | `SGH-Q09_STATUS: READY` (Phase 2 gate) |

---

## Benchmark / acceptance parity gates

Minden Tier 2+ task-hoz kötelező:

| Gate neve | Mérési módszer | Elfogadási küszöb |
|---|---|---|
| `convergence_rate` | Identical fixture, iterations to best_loss==0.0 | Új verzió ≤ régi + 20% |
| `density_improvement` | Sparrow baseline vs. VRS solver: placed_area / sheet_area | VRS ≥ Sparrow × 0.95 |
| `determinism_gate` | 10 futás azonos seed → bit-identikus output | 100% egyezés |
| `no_violations_gate` | `find_violations()` minden accepted output-on | 0 violation |
| `test_suite_gate` | `cargo test -p vrs_solver` | 100% pass |
| `verify_gate` | `./scripts/verify.sh` | exit 0 |

---

## Összefoglalás: corrected task order

```
SGH-Q01 (annotáció + planning)
  → SGH-Q02 (GLS parity)
    → SGH-Q03 (multi-worker)
      → SGH-Q04 (phase orchestration)
        → SGH-Q05 (BPP phase loop)
          → SGH-Q06 (smooth loss)
            → SGH-Q07 (rotation policy)
              → SGH-Q08 (collision backend + geometry)

[PAUSED] SGH-06 (eredeti scope) → újradefiniálódik SGH-Q04 utáni orchestration részeként
```

**Eredeti SGH-06** (`solution pool / perturbation / local search loop`) tartalma az SGH-Q04-be integrálódik, nem önálló task-ként folytatódik.
