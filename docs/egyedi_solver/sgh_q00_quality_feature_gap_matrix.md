# SGH-Q00 Quality Feature Gap Matrix

Minden sorhoz: Feature, forrás bizonyíték, VRS jelenlegi ekvivalens, parity státusz, quality risk, szükséges migráció, szükséges tesztek, szükséges benchmark, modularitási követelmény.

---

## F01 — RotationRange / continuous/discrete rotation

| Mező | Tartalom |
|---|---|
| **Feature** | Kontinuus és diskrét rotáció együttes támogatása |
| **Sparrow/jagua-rs source evidence** | `jagua-rs/src/geometry/geo_enums.rs`: `RotationRange { None, Continuous, Discrete(Vec<f32>) }`. `Item.allowed_rotation: RotationRange`. `search.rs:81`: `let wiggle = item.allowed_rotation == RotationRange::Continuous` |
| **VRS current equivalent** | `item.rs`: `allowed_rotations_deg: Vec<i64>`, `normalize_allowed_rotations` csak 0/90/180/270-et fogad el; `Placement.rotation_deg: i64` |
| **Parity status** | **MISSING** |
| **Quality risk** | Kritikus irregular Phase 2-höz; rectangular-only esetén elfogadható. Jelenlegi VRS minden rotációs input-ot legfeljebb 4 értékre szűkít le — más értéket error-ral visszautasít |
| **Required migration strategy** | `RotationPolicy` trait: `DiscreteRotationPolicy` (jelenlegi), `ContinuousRotationPolicy` (jagua-rs RotationRange::Continuous). Separator, candidates, moves NE tartalmazzon hardcoded `0/90/180/270` feltételezést |
| **Required tests** | `normalize_allowed_rotations` visszautasítja a nem-rács szögeket → explicit error; `ContinuousRotationPolicy::sample(rng)` → f32 angle; test hogy a policy interface determinisztikus-e |
| **Required benchmark** | Diskrét 4-szög vs. kontinuus rotáció density összehasonlítás ugyanazon irregular inputon |
| **Modularity requirement** | `rotation_policy` külön modul; separator, candidates, moves ne tartalmazzon hardcoded `[0, 90, 180, 270]` listát |

---

## F02 — Continuous sampling + local rotation wiggle/refinement

| Mező | Tartalom |
|---|---|
| **Feature** | Stochasztikus uniform mintavétel + két lépéses koordinátacsökkentés (pre-refine + final refine) kontinuus (x,y,r) térben |
| **Sparrow/jagua-rs source evidence** | `src/sample/search.rs:20`: `search_placement` (Algorithm 6): focussed BBox sampler + container-wide sampler; `coord_descent` két fázisban. `src/sample/coord_descent.rs`: `CDConfig { t_step_init, t_step_limit, r_step_init, r_step_limit }`. `src/consts.rs`: `PRE_REFINE_CD_R_STEPS`, `SND_REFINE_CD_R_STEPS` |
| **VRS current equivalent** | `candidates.rs`: `generate_candidates_with_sheets` — diskrét LBF pozíció-lista; `initializer.rs`: `lbf_select_clear_candidate` — determinisztikus LBF keresés; nincs coord descent |
| **Parity status** | **MISSING** |
| **Quality risk** | Magas. A Sparrow minőségének fő forrása az algoritmikus mintavétel. Stochasztikus keresés nélkül a VRS csak determinisztikus LBF grid-et vizsgál — ez nem ekvivalens |
| **Required migration strategy** | `SampleSearchEngine` trait: `LbfDeterministicSearch` (jelenlegi) és `StochasticCoordDescentSearch` (jagua-rs alapú). A koordinátacsökkentő lépések igénylik a continous rotation + smooth loss (F01, F05) meglétét |
| **Required tests** | Stochasztikus keresés azonos seed mellett determinisztikus; coord descent csökkenti a weighted loss-t; focussed sampler a jelenlegi placement köré mintáz |
| **Required benchmark** | LBF-only vs. stochastic + coord descent: density és iteration count összehasonlítás 50-item+ irregular inputon |
| **Modularity requirement** | `search_phase` orchestration külön modul; NE legyen hardcoded a separator belső hurkában |

---

## F03 — Transformation model

| Mező | Tartalom |
|---|---|
| **Feature** | Teljes merev test transzformáció: 3×3 mátrix, compose/decompose, inverse, chain |
| **Sparrow/jagua-rs source evidence** | `jagua-rs/src/geometry/transformation.rs`: `Transformation { matrix: [[NotNan<f32>; 3]; 3] }`, `rotate`, `translate`, `rotate_translate`, `inverse`, `decompose`. `d_transformation.rs`: `DTransformation { rotation: NotNan<f32>, translation: (NotNan<f32>, NotNan<f32>) }` |
| **VRS current equivalent** | `io.rs`: `Placement { x: f64, y: f64, rotation_deg: i64 }` — nem mátrix, nem invertálható, nem chainelhető |
| **Parity status** | **PROXY** |
| **Quality risk** | Alacsony rectangular Phase 1-ben (AABB elegendő). Magas irregular Phase 2-ben: inverse transform szükséges a disruption cascade-hez (`explore.rs:192`: `dt1_old.compose().inverse().transform(&converting_transformation)`) |
| **Required migration strategy** | `PlacementTransform` trait: `RectPlacementTransform` (jelenlegi anchor+deg) és `FullRigidTransform` (jagua-rs DTransformation). A disruption cascade F13-ban igényli az inverse-t |
| **Required tests** | `compose().inverse().transform(compose())` = identity; `DTransformation(r,t).compose().decompose()` visszaadja az eredetit |
| **Required benchmark** | N/A Phase 1 rectangular-nál |
| **Modularity requirement** | `geometry_backend` külön modul; VRS separator NE tartalmazzon hardcoded `anchor+deg` feltételezést |

---

## F04 — jagua-rs CDE / exact shape collision usage

| Mező | Tartalom |
|---|---|
| **Feature** | Quadtree alapú pontos poligon–poligon ütközésvizsgálat, surrogate fast-fail, hazard registry |
| **Sparrow/jagua-rs source evidence** | `cd_engine.rs`: `CDEngine { quadtree: QTNode, hazards_map: SlotMap<HazKey, Hazard>, config: CDEConfig }`. `detect_poly_collision`: edge intersection + containment. `detect_surrogate_collision`: pole + pier fast-fail. `CDEConfig { quadtree_depth, cd_threshold, item_surrogate_config }` |
| **VRS current equivalent** | `separator.rs`: `bbox_overlap_area` — AABB overlap only; `boundary.rs`: `rect_within_boundary` — AABB check |
| **Parity status** | **PROXY** |
| **Quality risk** | Alacsony rectangular-only esetén (AABB = exact for axis-aligned rectangles). Magas irregular esetén: PROXY nincs jelölve quality-risk flaggel |
| **Required migration strategy** | `CollisionBackend` trait: `BboxCollisionBackend` (jelenlegi, PROXY) és `CDECollisionBackend` (jagua-rs CDEngine). A proxy explicit `QUALITY_RISK: BboxOnlyProxy` flaggel dokumentálandó |
| **Required tests** | BboxCollisionBackend: AABB overlap egyező a kézi számítással; CDECollisionBackend: L-alakú polygon collision-mentes placement nem false-positive |
| **Required benchmark** | AABB vs. CDE: overlap detection accuracy irregular 100-item inputon |
| **Modularity requirement** | `collision_backend` külön modul |

---

## F05 — Collision severity / penetration / smooth loss

| Mező | Tartalom |
|---|---|
| **Feature** | Pole-pole penetration depth, smooth loss átmenet az ε küszöb körül, area-arányos súlyozás |
| **Sparrow/jagua-rs source evidence** | `quantify/overlap_proxy.rs`: `overlap_area_proxy` (Algorithm 3): `pd_decay = match pd >= epsilon { true => pd, false => epsilon²/(-pd + 2ε) }; total_overlap += pd_decay * min(r1, r2) * PI` |
| **VRS current equivalent** | `separator.rs`: `bbox_overlap_area`: `dx * dy` — area, nincs sima átmenet; `boundary_loss`: `BOUNDARY_LOSS_PROXY = 1.0` — bináris |
| **Parity status** | **PROXY** |
| **Quality risk** | Közepes. AABB area overlap hasonló mértékű, de sima loss nélkül a GLS gradiense gyengébb. Boundary binary loss → extra nehézség a GLS-nek (ugrás 0→1 nincs intepolálva) |
| **Required migration strategy** | `LossModel` trait: `BboxAreaLoss` (jelenlegi PROXY) és `PolePenetrationSmoothLoss` (jagua-rs algorithm 3). Minden PROXY modell explicit `quality_risk: HIGH/MEDIUM/LOW` mezővel |
| **Required tests** | `PolePenetrationSmoothLoss` folytonos az ε körül; `BboxAreaLoss` azonos értéket ad két identikus overlap-re; unit test: sima átmenet verifikáció |
| **Required benchmark** | Loss modell hatása a GLS konvergencia sebességére 50-item dense inputon |
| **Modularity requirement** | `collision_severity` / `loss_model` külön modul |

---

## F06 — Shape-based penalty

| Mező | Tartalom |
|---|---|
| **Feature** | Penalty a poligon alakján alapul (surrogate area, convex hull area) — nem flat per-item |
| **Sparrow/jagua-rs source evidence** | `overlap_proxy.rs`: penalty arányos `min(p1.radius, p2.radius)` — a pole sugarával, ami a shape méretével skálázódik. `explore.rs`: `item.shape_cd.surrogate().convex_hull_area` a disruption large-item szelekcióhoz |
| **VRS current equivalent** | `score.rs`: `overlap_penalty_per_pair: 1e9` — flat, shape-független; `boundary_penalty_per_item: 1e9` — flat |
| **Parity status** | **MISSING** |
| **Quality risk** | Közepes. Flat penalty inkompatibilis az area-arányos GLS gradienstétel; nagy és kis itemek azonos súllyal bírnak |
| **Required migration strategy** | `LossModel` trait integráció: shape-arányos penalty opcionálisan a `collision_backend` és `loss_model` kombináción keresztül |
| **Required tests** | Nagy item magasabb penalty-t kap mint kis item azonos penetration esetén |
| **Required benchmark** | Flat vs. shape-arányos penalty: packing quality különbség |
| **Modularity requirement** | `loss_model` modul; NE legyen hardcoded flat constant |

---

## F07 — GLS dynamic weights

| Mező | Tartalom |
|---|---|
| **Feature** | Per-pair és per-container collision weight dinamikus frissítése: decay ha nincs collision, loss-arányos növelés ha van |
| **Sparrow/jagua-rs source evidence** | `tracker.rs:113`: `update_weights()` (Algorithm 8): `multiplier = GLS_WEIGHT_DECAY` (no collision) vagy `GLS_WEIGHT_MIN_INC_RATIO + (MAX-MIN)*(loss/max_loss)` (collision); `e.weight = (e.weight * multiplier).max(1.0)` |
| **VRS current equivalent** | `separator.rs:136`: `update_weights(decay, weight_max)`: `*w = (*w + 1.0 / (1.0 + *w * decay)).min(weight_max)` — additive, nem multiplicative; nincs max_loss normalizáció |
| **Parity status** | **PARTIAL** |
| **Quality risk** | Közepes. Additive vs. multiplicative update más konvergencia viselkedést ad. Nincs max_loss normalizáció → relatív súlyok torzítottak nagyon nagy loss esetén |
| **Required migration strategy** | `WeightUpdateStrategy` trait: `AdditiveGls` (jelenlegi) és `MultiplicativeGls` (Algorithm 8). A formulas explicit összehasonlítása benchmarkon |
| **Required tests** | `MultiplicativeGls`: nincs collision → weight konvergál 1.0-hoz; max collision → weight ≥ `GLS_WEIGHT_MIN_INC_RATIO`; max_loss normalizáció unit test |
| **Required benchmark** | Additive vs. multiplicative GLS: separator iterations to convergence |
| **Modularity requirement** | `gls_weight_strategy` külön modul vagy trait a separatorban |

---

## F08 — Separator incumbent / restore / strike / best-state

| Mező | Tartalom |
|---|---|
| **Feature** | Incumbent megőrzés, strikes counter, rollback weight-preservation |
| **Sparrow/jagua-rs source evidence** | `separator.rs:73`: `min_loss_sol = (self.prob.save(), self.ct.save())`; strike ha `initial_strike_loss * 0.98 <= min_loss`; `rollback(..., Some(&min_loss_sol.1))` → `restore_but_keep_weights` megtartja a súlyokat |
| **VRS current equivalent** | `separator.rs:258`: `best_layout = current.snapshot()`, strikes counter van; de `restore_item` per-item (nincs CT snapshot klón); rollback visszaállítja a bboxes-t, de weight preserve nincs külön |
| **Parity status** | **PARTIAL** |
| **Quality risk** | Közepes. Weight-resetting rollback elveszíti a tanult GLS súlyokat → a separator a következő strike után nulláról tanulja újra |
| **Required migration strategy** | `CTSnapshot` + `restore_but_keep_weights` implementáció a VRS `VrsCollisionTracker`-ben |
| **Required tests** | Rollback után GLS weights megmaradnak; `CTSnapshot` klón azonos értékeket ad |
| **Required benchmark** | N/A (quality impact valószínűleg kis/közepes) |
| **Modularity requirement** | `VrsCollisionTracker` kiegészítés a `restore_but_keep_weights` metódussal |

---

## F09 — move_items_multi / multi-worker / multi-order logic

| Mező | Tartalom |
|---|---|
| **Feature** | N párhuzamos worker, minden worker más véletlenszerű sorrendben mozgatja az itemeket, a legjobb eredményt tartja meg |
| **Sparrow/jagua-rs source evidence** | `separator.rs:146`: `move_items_multi()` (Algorithm 10): `self.workers.par_iter_mut()` (rayon), minden worker: `worker.load(&master_sol, &self.ct); worker.move_items()`. `worker.rs:40`: `SeparatorWorker.move_items()` (Algorithm 5): candidates shuffle + `search_placement` |
| **VRS current equivalent** | `separator.rs:276`: determinisztikus egyszálú: `max_by(weighted_loss)` → legrosszabb collider kiválasztása; nincs shuffle, nincs rayon |
| **Parity status** | **MISSING** |
| **Quality risk** | Magas. A Sparrow minden iterációban 3 independent keresési irányt próbál — lényegesen nagyobb keresési tér lefedettsége |
| **Required migration strategy** | `SeparatorWorker` struktúra VRS-natív reimplementációja (stochasztikus item-order); rayon `par_iter_mut` integrálás; `n_workers` configban |
| **Required tests** | N worker azonos input-on: legalább az egyik worker jobb vagy egyenlő loss-t ér el; multi-worker result ≤ single-worker result loss |
| **Required benchmark** | Single vs. 3-worker: separator convergence speed és final density |
| **Modularity requirement** | `search_phase` orchestration modul; NE legyen hardcoded single-worker |

---

## F10 — BLF/LBF role

| Mező | Tartalom |
|---|---|
| **Feature** | BLF/LBF mint konstruktív alap és separator seed-pozíció |
| **Sparrow/jagua-rs source evidence** | Sparrow LBF-t a söprésvonal kontextusban alkalmazza (strip width); `search_placement` stochasztikus mintavétele felváltja az LBF-et separator hívásokban |
| **VRS current equivalent** | `candidates.rs`: `generate_candidates_with_sheets` — teljes LBF kandidátlista; `initializer.rs`: `lbf_select_clear_candidate`; `moves.rs`: `lbf_clear_on_sheet` |
| **Parity status** | **PROXY** |
| **Quality risk** | Alacsony a rectangular construction phase-ben. LBF jó konstrukciós alap; a minőségi gap az LBF utáni optimalizálási lépéseknél van (F02, F09) |
| **Required migration strategy** | Nincs közvetlen változás szükséges — LBF a VRS natív erőssége. A gap a stochasztikus keresési réteg (F02) hiánya |
| **Required tests** | Meglévő LBF tesztek zöldek maradnak |
| **Required benchmark** | N/A |
| **Modularity requirement** | LBF modul maradhat önálló; `search_phase` réteg fölé épül |

---

## F11 — Exploration / compression phases

| Mező | Tartalom |
|---|---|
| **Feature** | Kétfázisú optimalizáció: exploration (iteratív shrink + infeasible pool) + compression (fine-tune) |
| **Sparrow/jagua-rs source evidence** | `explore.rs:21`: `exploration_phase` (Algorithm 12); `compress.rs:11`: `compression_phase` (Algorithm 13); `config.rs`: külön `ExplorationConfig.time_limit` és `CompressionConfig.time_limit` |
| **VRS current equivalent** | `sheet_elimination.rs`: egylépéses eliminálás kísérlet; nincs iteratív exploration loop, nincs compression phase, nincs phase time split |
| **Parity status** | **MISSING** |
| **Quality risk** | Magas. A kétfázisú struktúra a Sparrow fő minőségi hozzájárulása a separator után |
| **Required migration strategy** | `PhaseOrchestrator` trait: `ExplorationPhase` + `CompressionPhase` külön struktúrák; `PhaseConfig` per-phase time budget |
| **Required tests** | Exploration: minden feasible solution-t megőriz; compression: best width monoton csökken; phase termination: time limit betartva |
| **Required benchmark** | Exploration+compression vs. single-phase: density és runtime tradeoff |
| **Modularity requirement** | `search_phase orchestration` külön modul |

---

## F12 — Infeasible solution pool

| Mező | Tartalom |
|---|---|
| **Feature** | Infeasible megoldások poolja, loss-arányos szelekció normális eloszlással, disruption előtt restore |
| **Sparrow/jagua-rs source evidence** | `explore.rs:31`: `infeas_sol_pool: Vec<(SPSolution, f32)>` rendezve loss szerint; `distribution = Normal(0, stddev).sample().abs().min(0.999)` → index mapping; cleared on feasibility |
| **VRS current equivalent** | Nincs. `VrsSeparator` csak incumbent-et tart |
| **Parity status** | **MISSING** |
| **Quality risk** | Közepes-magas. Pool nélkül a disruption (F13) nem tud múlt infeasible állapotokból meríteni → kisebb escape esély local minimumoknál |
| **Required migration strategy** | `InfeasibleSolutionPool` struct: binary-search insertion by loss, normal-distribution sampling |
| **Required tests** | Pool insertion tartja a loss-ascending sorrendet; `sample(rng)` jobban választja a jobb megoldásokat |
| **Required benchmark** | Pool vs. no-pool: local minimum escape ráta |
| **Modularity requirement** | `search_phase` orchestration modulban |

---

## F13 — Perturbation / disruption / large-item swap

| Mező | Tartalom |
|---|---|
| **Feature** | Disruption: két nagy item (CH area percentile alapján) cseréje + cascade contained items |
| **Sparrow/jagua-rs source evidence** | `explore.rs:89`: `disrupt_solution()`: large items by `convex_hull_area >= ch_area_cutoff`; két item choose (random, area-diverse); swap positions; cascade: `practically_contained_items` POI containment → move with converting_transformation; `convert_sample_to_closest_feasible` rotation check |
| **VRS current equivalent** | `moves.rs`: `try_swap` API (SGH-05) — rollback-safe swap primitív, de nincs large-item selection, nincs CH area percentile, nincs POI cascade |
| **Parity status** | **PARTIAL** |
| **Quality risk** | Magas. Disruption nélkül a solver csak lokális perturbációt tud — nem tud kiszabadulni mély local minimumokból |
| **Required migration strategy** | `DisruptionStrategy` trait: `LargeItemSwapDisruption` (jagua-rs minta alapján); igényli a CH area metadata meglétét (`SPSurrogate.convex_hull_area`) és a POI containment check-et (F04) |
| **Required tests** | Large item selection: mindig a top percentile-ból kerül ki; cascade: POI-contained items mozognak; rotation feasibility check |
| **Required benchmark** | Disruption vs. no-disruption: local minimum escape rate dense inputon |
| **Modularity requirement** | `search_phase` orchestration; disrupt strategy külön pluggable |

---

## F14 — Time budget / phase split

| Mező | Tartalom |
|---|---|
| **Feature** | Per-phase konfigurálható time budget; exploration és compression külön |
| **Sparrow/jagua-rs source evidence** | `config.rs`: `ExplorationConfig { time_limit: Duration::from_secs(9*60) }`, `CompressionConfig { time_limit: Duration::from_secs(60) }` |
| **VRS current equivalent** | `stopping.rs`: `StoppingCondition` struct létezik; de nincs per-phase time split |
| **Parity status** | **MISSING** |
| **Quality risk** | Alacsony-közepes. Helytelen time split → compression underbudgeted → final density suboptimal |
| **Required migration strategy** | `PhaseConfig { exploration_time: Duration, compression_time: Duration }` a `PhaseOrchestrator`-ban |
| **Required tests** | Exploration time limit betartva (wall time check); compression time limit betartva |
| **Required benchmark** | N/A |
| **Modularity requirement** | `search_phase orchestration` modul |

---

## F15 — Seed determinism

| Mező | Tartalom |
|---|---|
| **Feature** | Reprodukálható futás RNG seeddel |
| **Sparrow/jagua-rs source evidence** | `config.rs:9`: `rng_seed: Option<usize>`; workers: `Xoshiro256PlusPlus::seed_from_u64(rng.random())` |
| **VRS current equivalent** | `VrsSeparator`: nincs RNG, teljesen determinisztikus. `MoveExecutor`: szintén nincs RNG |
| **Parity status** | **FULL (restricted)** |
| **Quality risk** | Nincs (jelenlegi determinisztikus rendszerben). Ha F02/F09 stochasztikus keresést bevezet, `rng_seed` szükséges |
| **Required migration strategy** | Ha stochasztikus keresés bevezetésre kerül: `SolverConfig { rng_seed: Option<u64> }` |
| **Required tests** | Azonos seed → bit-identikus output (ha RNG bevezetésre kerül) |
| **Required benchmark** | N/A |
| **Modularity requirement** | `SolverConfig` toplevel |

---

## F16 — BPP / bin reduction logic (coroush fork)

| Mező | Tartalom |
|---|---|
| **Feature** | BPP sheet-to-sheet transfer/swap/reinsert operátorok + sheet eliminálás |
| **Sparrow/jagua-rs source evidence** | coroush/sparrow `bp_moves.rs` (commit `5df9ce15`): `try_transfer`, `try_swap`, `try_reinsert`; `bp_explore.rs`: sheet elimination loop. coroush/sparrow-grasshopper: C# wrapper (`0c9a1362`) |
| **VRS current equivalent** | SGH-05 (`moves.rs`): `try_transfer`, `try_swap`, `try_reinsert`, `resolve_by_transfers` VRS-natív implementáció; SGH-04 (`sheet_elimination.rs`): sheet eliminálás |
| **Parity status** | **PARTIAL** |
| **Quality risk** | Közepes. Az operátorok megvannak, de a coroush `bp_explore.rs` iteratív eliminálási loop-ja MISSING (SGH-06+ területe) |
| **Required migration strategy** | `BinPackingPhase` orchestration (bp_explore.rs VRS-natív port) SGH-06-ban |
| **Required tests** | SGH-05 tesztek (140/140 zöld) — teljesítve |
| **Required benchmark** | Multi-sheet BPP: sheet count reduction vs. coroush referencia |
| **Modularity requirement** | `sheet_phase orchestration` külön modul |

---

## F17 — Geometry caching / preprocessing / simplification

| Mező | Tartalom |
|---|---|
| **Feature** | Shape preprocessing pipeline: simplification, offset (spacing), narrow concavity close; surrogate generation (poles + piers); Arc-cached immutable shapes |
| **Sparrow/jagua-rs source evidence** | `jagua-rs/src/geometry/original_shape.rs`: pipeline: offset → simplify_shape → close_narrow_concavities → simplify. `Item { shape_orig: Arc<OriginalShape>, shape_cd: Arc<SPolygon> }`. `SPSurrogateConfig { n_pole_limits, n_ff_poles, n_ff_piers }`. `SparrowConfig { poly_simpl_tolerance, min_item_separation, narrow_concavity_cutoff_ratio }` |
| **VRS current equivalent** | `item.rs`: `Part { outer_points: Option<JsonValue>, holes_points: Option<JsonValue> }` — beolvasva, de nem feldolgozva; nincs preprocessing, nincs surrogate |
| **Parity status** | **MISSING** |
| **Quality risk** | Magas irregular Phase 2-höz; nincs hatás rectangular Phase 1-en |
| **Required migration strategy** | `GeometryBackend` trait; `RectGeometryBackend` (jelenlegi AABB) és `IrregularGeometryBackend` (jagua-rs pipeline). A preprocessing: az `outer_points` / `holes_points` JsonValue-okból `SPolygon` konverzió |
| **Required tests** | Simplification megőrzi az eredeti shape-et a tolerance-en belül; offset monoton inflál; surrogate poles ≤ shape boundary |
| **Required benchmark** | Preprocessing time vs. CDE collision speedup |
| **Modularity requirement** | `geometry_backend` külön modul; `collision_backend` erre épül |

---

## F18 — Irregular container / remnant support

| Mező | Tartalom |
|---|---|
| **Feature** | Tetszőleges poligon konténer; remnant (maradék lemez) mint alacsonyabb cost_per_use sheet |
| **Sparrow/jagua-rs source evidence** | `jagua-rs/src/probs/spp`: SPP container = strip, boundary lehet szabálytalan poligon. `CDEngine` bármilyen polygon boundary-t kezel. `Item.min_quality: Option<usize>` — quality zóna |
| **VRS current equivalent** | `sheet.rs`: `Stock { outer_points: Option<JsonValue>, cost_per_use: Option<f64> }`. `SheetShape { outer_points, cost_per_use }`. `score.rs`: `sheet_cost_total` már `cost_per_use`-alapú (JG-19). Boundary check: `rect_within_boundary` — csak AABB |
| **Parity status** | **PROXY** |
| **Quality risk** | Alacsony rectangular remnant esetén (AABB boundary = exact). Magas irregular remnant esetén: `rect_within_boundary` nem kezeli az `outer_points` által meghatározott kontúrt |
| **Required migration strategy** | Irregular boundary check a `CollisionBackend` trait révén; `outer_points` JsonValue → `SPolygon` konverzió a `GeometryBackend`-ben |
| **Required tests** | `cost_per_use`-alapú remnant preference: tesztek a score.rs-ben zöldek (SGH-JG19 eleve megvan) |
| **Required benchmark** | Remnant vs. regular sheet density trade-off |
| **Modularity requirement** | `geometry_backend` modul kezeli a `outer_points` → `SPolygon` konverziót |

---

## Gap Matrix Summary

| # | Feature | Parity | Quality Risk |
|---|---|---|---|
| F01 | RotationRange / continuous rotation | MISSING | HIGH (Phase 2) |
| F02 | Continuous sampling + wiggle | MISSING | HIGH |
| F03 | Transformation model | PROXY | LOW (Phase 1) / HIGH (Phase 2) |
| F04 | CDE / exact shape collision | PROXY | LOW (Phase 1) / HIGH (Phase 2) |
| F05 | Collision severity / smooth loss | PROXY | MEDIUM |
| F06 | Shape-based penalty | MISSING | MEDIUM |
| F07 | GLS dynamic weights | PARTIAL | MEDIUM |
| F08 | Separator incumbent / restore | PARTIAL | MEDIUM |
| F09 | move_items_multi / multi-worker | MISSING | HIGH |
| F10 | BLF/LBF role | PROXY | LOW |
| F11 | Exploration / compression phases | MISSING | HIGH |
| F12 | Infeasible solution pool | MISSING | MEDIUM |
| F13 | Perturbation / disruption | PARTIAL | HIGH |
| F14 | Time budget / phase split | MISSING | LOW-MEDIUM |
| F15 | Seed determinism | FULL (restricted) | NONE |
| F16 | BPP / bin reduction | PARTIAL | MEDIUM |
| F17 | Geometry caching / preprocessing | MISSING | HIGH (Phase 2) |
| F18 | Irregular container / remnant | PROXY | LOW (rect) / HIGH (irreg) |

**FULL:** 1 | **PARTIAL:** 4 | **PROXY:** 6 | **MISSING:** 7 | **WRONG:** 0

Minden PROXY egy explicit, mérhető quality-risk zászlóval kísért proxy — nem tekinthető paritynak. A MISSING funkciók a SGH-06+ implementációs sorban kerülnek megvalósításra.
