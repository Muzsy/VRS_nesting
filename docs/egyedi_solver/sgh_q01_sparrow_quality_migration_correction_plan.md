# SGH-Q01 — Sparrow Quality Migration Correction Plan

## Cél

Az SGH-Q00 parity audit 18 feature-t vizsgált meg és 7 MISSING, 6 PROXY, 4 PARTIAL és 1 FULL státuszt állapított meg. Ez a dokumentum a korrekciós tervet rögzíti: mi marad, mi áll le, mi cserélendő, és milyen sorrendben.

Ez **audit + tervezési** dokumentum — production kód nem változik.

---

## Kötelező döntések (nem alkuképesek)

```
SGH-06 is paused.
SGH-01..SGH-05 are structural scaffolds, not quality parity.
No future simplified proxy is acceptable without explicit quality-risk flag and benchmark gate.
Every MISSING / PROXY / PARTIAL feature from SGH-Q00 gets a migration path.
```

### SGH-06 szüneteltetésének oka

Az SGH-Q00 audit megállapította, hogy az SGH-05 move operátorok (transfer, swap, reinsert) megvannak, de a keresési loop orchestration (exploration/compression phase, infeasible pool, disruption) teljes egészében hiányzik. Az SGH-06 eredeti scope-ja (`solution pool / perturbation / local search loop`) helyes irányba mutat, de a végrehajtás sorrendje és a quality gateek nincsenek definiálva az SGH-Q00 audit eredményei fényében.

**SGH-06 csak az alábbiak teljesülése után indulhat:**
1. SGH-Q02: GLS parity + weight-preserving rollback (F07, F08)
2. SGH-Q03: multi-worker move_items_multi (F09)
3. SGH-Q04: exploration/compression orchestration (F11, F12, F13, F14)

### SGH-01..SGH-05 értékelése

| Task | Mit épített | Minőségi parity státusz | Megtartható? |
|---|---|---|---|
| SGH-01 | `WorkingLayout`, commit gate, `find_violations` | Strukturális alap — helyes | KEEP |
| SGH-02 | `VrsSeparator`, `VrsCollisionTracker`, GLS struktúra | PARTIAL (additive GLS, single-threaded, binary boundary loss) | KEEP + EXTEND |
| SGH-03 | `initializer.rs` LBF + separator fallback | PROXY (deterministic only) | KEEP (Phase 1 baseline) |
| SGH-04 | `sheet_elimination.rs` | PARTIAL (bp_explore loop hiányzik) | KEEP + EXTEND |
| SGH-05 | `moves.rs` MoveExecutor | PARTIAL (disruption orchestration hiányzik) | KEEP + EXTEND |

---

## Keep / Stop / Replace döntési tábla

| Elem | Döntés | Indoklás |
|---|---|---|
| `WorkingLayout` + commit gate | **KEEP** | Helyes absztrakció, F: SGH-01 |
| `VrsCollisionTracker` (AABB loss, binary boundary) | **KEEP + QUALITY_RISK annotáció** | PROXY-ként elfogadható rect Phase 1-ben, de jelölni kell |
| `VrsSeparator` (single-threaded, additive GLS) | **KEEP + EXTEND** | Alap jó; GLS formula és multi-worker hiányzik (F07, F09) |
| `initializer.rs` LBF deterministic | **KEEP** | Rectangular Phase 1 baseline; stochasztikus search külön rétegben |
| `sheet_elimination.rs` | **KEEP + EXTEND** | SGH-04 operátorok megvannak; phase loop hiányzik |
| `moves.rs` MoveExecutor (SGH-05) | **KEEP + EXTEND** | Primitívek OK; disruption loop hiányzik |
| `score.rs` ScoreModel | **KEEP** | Helyes, `cost_per_use` megvan (JG-19) |
| `stopping.rs` StoppingPolicy | **KEEP + EXTEND** | Nincs per-phase time split |
| Hardcoded `[0, 90, 180, 270]` lista item.rs-ben | **ANNOTATE, later REPLACE** | DiscreteRotationPolicy-ra kell refaktorálni Phase 2 előtt |
| AABB `bbox_overlap_area` + `BOUNDARY_LOSS_PROXY = 1.0` | **ANNOTATE now, REPLACE in F-tasks** | Rect esetén PROXY-ok; jelölni kell P06 szerint |
| SGH-06 (eredeti scope) | **PAUSE** | Nincs quality gate; orchestration előfeltételek hiányoznak |

---

## Proxy annotáció kötelezettség (SGH-Q01 scope)

Az SGH-Q00 modular architecture principles P06 elvének megfelelően a következő kódhelyek annotációt kapnak (nem production logika változás — ez SGH-Q01 production scope-ja):

| Fájl | Kódhely | Annotáció |
|---|---|---|
| `optimizer/separator.rs` | `BOUNDARY_LOSS_PROXY = 1.0` | `// QUALITY_RISK: BinaryBoundaryLoss — no smooth gradient; see F05, SGH-Q00` |
| `optimizer/separator.rs` | `bbox_overlap_area` | `// QUALITY_RISK: BboxOnlyProxy — exact for rectangular, proxy for irregular; see F04, SGH-Q00` |
| `optimizer/separator.rs` | `update_weights` | `// QUALITY_RISK: AdditiveGlsProxy — differs from Sparrow Algorithm 8 multiplicative; see F07, SGH-Q00` |
| `optimizer/boundary.rs` | `rect_within_boundary` | `// QUALITY_RISK: BboxBoundaryProxy for irregular outer shapes; see F04, SGH-Q00` |
| `item.rs` | `normalize_allowed_rotations` | `// QUALITY_RISK: DiscreteRotationOnly — 0/90/180/270 only; see F01, SGH-Q00` |
| `optimizer/candidates.rs` | `PlacedBbox::overlaps` | `// QUALITY_RISK: BboxOnlyProxy — exact for Phase 1 rectangular; see F04, SGH-Q00` |

---

## Korrekciós migráció sorrendje

### Tier 0 — Annotáció (nincs production logika változás)

**SGH-Q01** (ez a task):
- P06 proxy annotációk hozzáadása a fentiek szerint.
- Documentáció: correction plan, corrected roadmap, no-downgrade gates.

### Tier 1 — GLS minőség (önálló quality javulás, kis kockázat)

**SGH-Q02 — GLS parity + weight-preserving rollback** (F07, F08):
- Multiplicative GLS update (Sparrow Algorithm 8 max_loss normalizáció).
- `restore_but_keep_weights` implementáció a `VrsCollisionTracker`-ben.
- Dependency: SGH-Q01 PASS.

**SGH-Q03 — Multi-worker move_items_multi** (F09):
- N parallel worker (rayon), random item ordering per worker.
- `SeparatorWorker` struktúra VRS-natív implementáció.
- Dependency: SGH-Q02 PASS (GLS quality gate).

### Tier 2 — Phase orchestration (nagy quality gain, közepes kockázat)

**SGH-Q04 — Exploration/compression phase orchestration** (F11, F12, F13, F14):
- `ExplorationPhase` + `CompressionPhase` struktúrák.
- `InfeasibleSolutionPool` (loss-ascending, normal distribution selection).
- `LargeItemSwapDisruption` (CH area percentile + cascade).
- `PhaseConfig` per-phase time budget.
- Dependency: SGH-Q03 PASS.

**SGH-Q05 — BPP phase loop** (F16 completion):
- coroush `bp_explore.rs` VRS-natív port.
- Iteratív sheet elimination loop a phase orchestration keretein belül.
- Dependency: SGH-Q04 PASS.

### Tier 3 — Geometry layer (Phase 2 prerequisite, magas kockázat)

**SGH-Q06 — LossModel + smooth collision severity** (F05, F06):
- `LossModel` trait: `BboxAreaLoss` (jelenlegi PROXY) és `PolePenetrationSmoothLoss`.
- Smooth boundary loss (nem bináris).
- Dependency: SGH-Q03 PASS (multi-worker szükséges az eval speedhez).

**SGH-Q07 — RotationPolicy trait** (F01):
- `DiscreteRotationPolicy` wrapper a jelenlegi logika köré.
- Hardcoded `[0, 90, 180, 270]` lista eltávolítása a separator/candidates/moves-ból.
- Dependency: SGH-Q04 PASS (fázis-logika stabilizálódott).

**SGH-Q08 — CollisionBackend + geometry preprocessing** (F03, F04, F17):
- `CollisionBackend` trait: `BboxCollisionBackend` + `CDECollisionBackend`.
- `GeometryBackend` trait: `RectGeometryBackend` + `IrregularGeometryBackend`.
- jagua-rs CDEngine integráció.
- Dependency: SGH-Q07 PASS + Phase 2 scope decision.

---

## No-downgrade szabály

Minden jövőbeli SGH task-nak meg kell felelnie a `sgh_q01_no_downgrade_acceptance_gates.md`-ban rögzített kapuknak. Egy task csak akkor kaphat PASS státuszt, ha:

1. A task scope-jában lévő feature-ök **nem kerülnek lejjebb** parity státuszban (FULL→PARTIAL tiltott; PARTIAL→PROXY tiltott).
2. Minden bevezetett proxy explicit `// QUALITY_RISK:` annotációval és gap matrix referenciával rendelkezik.
3. Minden task tartalmaz mérési gateeket (unit teszt + benchmark where applicable).
4. `cargo test -p vrs_solver` 100%-ban zöld marad minden task végén.
5. `./scripts/verify.sh` exit 0 minden task végén.
