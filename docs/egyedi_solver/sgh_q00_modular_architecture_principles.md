# SGH-Q00 Modular Architecture Principles

## Cél

Ez a dokumentum rögzíti a VRS optimizer moduláris architektúrájának elveit, amelyek a jagua-rs/Sparrow parity audit (SGH-Q00) tanulságain alapulnak. Minden elv kötelező: a future SGH task-ok ezen elvek betartásával valósíthatnak meg új funkciókat.

---

## Elvek

### P01 — Rotation policy provider külön modul

**A separator, candidates és move operátorok NE tartalmazzon hardcoded `[0, 90, 180, 270]` rotációs listát.**

A rotációs politikát egy `RotationPolicy` trait írja le, amelyet minden hívó paraméterként kap meg:

```
RotationPolicy trait:
  - DiscreteRotationPolicy { allowed_rotations_deg: Vec<i64> }   ← jelenlegi VRS
  - ContinuousRotationPolicy { sample(rng) -> f32 }               ← jagua-rs RotationRange::Continuous
```

**Rationale:** A jagua-rs `RotationRange::Continuous` ág lehetővé teszi arbitrary float szögeket — a VRS kódjában hardcoded `match rot { 0 | 90 | 180 | 270 => ... }` ágak ezt örökre kizárják. Az SGH-Q00 audit F01 MISSING statuszt állapított meg.

**Ellenőrzési feltétel:** `normalize_allowed_rotations`, `dims_for_rotation`, `separator.rs` kandidátciklus NE tartalmazzon hardcoded `match rot.rem_euclid(360) { 0 | 90 | 180 | 270 => ... }` feltételezést — ezek a `RotationPolicy` mögé kerülnek.

---

### P02 — Geometry / collision backend külön modul

**A separator, initializer és move operátorok NE tartalmazzon hardcoded AABB-alapú ütközésvizsgálatot.**

A ütközés-vizsgálatot egy `CollisionBackend` trait írja le:

```
CollisionBackend trait:
  - BboxCollisionBackend          ← jelenlegi VRS (AABB overlap, rect_within_boundary)
  - CDECollisionBackend           ← jagua-rs CDEngine (quadtree + exact polygon)
```

**Rationale:** A jelenlegi `bbox_overlap_area` és `rect_within_boundary` rectangular items esetén PROXY (elfogadható), de irregular alakzatoknál WRONG lenne. Az SGH-Q00 audit F04 PROXY státuszt állapított meg — ezekre explicit quality-risk flag szükséges.

**Ellenőrzési feltétel:** Minden PROXY collision-ellenőrzés `// QUALITY_RISK: BboxOnlyProxy — exact for rectangular, proxy for irregular` kommenttel jelölendő a kódban.

---

### P03 — Collision severity / loss model külön modul

**A GLS szeparátor NE tartalmazzon hardcoded `BOUNDARY_LOSS_PROXY = 1.0` konstanst és hardcoded `dx * dy` area formulát.**

A loss modellt egy `LossModel` trait írja le:

```
LossModel trait:
  - BboxAreaLoss             ← jelenlegi VRS (area overlap + binary boundary)
  - PolePenetrationSmoothLoss ← jagua-rs Algorithm 3 (smooth pd_decay)
```

**Rationale:** A Sparrow smooth loss formula (Algorithm 3) jobb GLS gradienst biztosít. A bináris `BOUNDARY_LOSS_PROXY` ugrása a GLS-nek nehezíti az irányítást. Az SGH-Q00 audit F05 PROXY státuszt és F06 MISSING státuszt állapított meg.

**Ellenőrzési feltétel:** Minden loss constant (`BOUNDARY_LOSS_PROXY`, `bbox_overlap_area`) explicit `QUALITY_RISK: ...` annotációval jelölendő.

---

### P04 — Search phase orchestration külön modul

**A separator, sheet_elimination és moves NE tartalmazzon beágyazott exploration/compression loop logikát.**

A keresési fázisok orchestrációja külön struktúrában él:

```
search_phase modul:
  - ExplorationPhase { config: ExplorationConfig, separator: VrsSeparator, pool: InfeasibleSolutionPool }
  - CompressionPhase { config: CompressionConfig, separator: VrsSeparator }
  - PhaseOrchestrator { exploration: ExplorationPhase, compression: CompressionPhase }
```

**Rationale:** A Sparrow kétfázisú architektúrája (Algorithm 12 + 13) a legjelentősebb quality gap az SGH-Q00 auditban (F11 MISSING, F12 MISSING, F13 PARTIAL, F14 MISSING). Egyetlen monolít separator-hurokba ezek nem integrálhatók értelmesen.

**Ellenőrzési feltétel:** `separator.rs` nem tartalmaz `Vec<SPSolution>` infeasible pool-t vagy exploration shrink loop-t. Ezek a `search_phase` modulban élnek.

---

### P05 — Separator / move / sheet-elimination NE tartalmazzon hardcoded lebutított rotation/collision feltételezést

Ez P01, P02, P03 együtteseinek összefoglaló elve:

- Ha egy `match rot { 0 | 90 | ... }` feltételezés fennáll, az explicit quality flag nélkül **TILOS**.
- Ha egy `bbox_overlap_area` PROXY-t alkalmazunk, az explicit `// QUALITY_RISK: BboxOnlyProxy` nélkül **TILOS**.
- Ha egy bináris boundary loss van, az explicit `// QUALITY_RISK: BinaryBoundaryLoss` nélkül **TILOS**.

**Rationale:** A SGH-Q00 audit megállapította, hogy a VRS jelenlegi 6 PROXY funkciói nincsenek jelölve — a jövőbeli kód-olvasó nem tudja eldönteni, hogy a leegyszerűsítés szándékos vagy hiányosság.

---

### P06 — Minden proxy csak explicit, mérhető quality-risk flaggel létezhet

**Minden PROXY implementáció kötelező annotációi:**

```rust
// QUALITY_RISK: BboxOnlyProxy
// Exact for axis-aligned rectangular items.
// For irregular shapes: use CDECollisionBackend instead.
// Parity: PROXY (F04, SGH-Q00)
```

A flag tartalmazza:
1. A proxy nevét (pl. `BboxOnlyProxy`)
2. Mikor pontos (pl. rectangular items)
3. Mikor NEM pontos (pl. irregular)
4. Az SGH-Q00 gap matrix reference (pl. `F04`)

**Rationale:** A SGH-Q00 audit célja az volt, hogy kódszintű bizonyítékkal állapítsa meg a quality gap-eket. A jövőbeli fejlesztők csak akkor tudják az architektúrát javítani, ha a proxy jelölések egyértelműek.

---

## Összefoglalás

| Elv | Mit tilt | Mit vár el |
|---|---|---|
| P01 | Hardcoded `[0, 90, 180, 270]` lista | `RotationPolicy` trait |
| P02 | Hardcoded AABB collision | `CollisionBackend` trait |
| P03 | Hardcoded `BOUNDARY_LOSS_PROXY = 1.0` és `dx*dy` | `LossModel` trait |
| P04 | Beágyazott exploration/compression loop | `search_phase` orchestration modul |
| P05 | Mindenféle hardcoded lebutítás jelölés nélkül | Explicit quality flag minden proxynál |
| P06 | Jelöletlen PROXY implementáció | `// QUALITY_RISK:` annotáció minden PROXY kódban |

---

## Jelen állapot vs. elvek

A jelenlegi VRS kód a P01–P06 elvek közül egyiket sem sérti kritikus módon a rectangular Phase 1 keretei közt — a PROXY-k elfogadhatóak addig, amíg explicit jelöltek. A SGH-Q00 audit után az alábbi fájlokba szükséges a `QUALITY_RISK` annotáció hozzáadása (nem production kód változtatás, dokumentációs kiegészítés):

- `rust/vrs_solver/src/optimizer/separator.rs`: `BOUNDARY_LOSS_PROXY`, `bbox_overlap_area`
- `rust/vrs_solver/src/optimizer/boundary.rs`: `rect_within_boundary`
- `rust/vrs_solver/src/item.rs`: `normalize_allowed_rotations`

Ezek az annotációk a SGH-Q01+ feladatok scope-jába tartoznak — az SGH-Q00 nem módosít production kódot.
