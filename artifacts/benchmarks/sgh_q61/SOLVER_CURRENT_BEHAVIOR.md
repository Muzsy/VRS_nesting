# VRS_nesting — a solver jelenlegi működése (Q56–Q60 + Q61 állapot)

> Állapot: 2026-06-23. Ez a dokumentum a `rust/vrs_solver` Sparrow/CDE kritikus-admission útjának
> tényleges működését írja le a Q56–Q60 preprocessing rétegek és a Q61 production-wiring után.
> Forrás: a `rust/vrs_solver/src/optimizer/sparrow/` modulok és `rust/vrs_solver/src/io.rs`.
> Minden függvény-/modulnév a valós kódból származik; a sorszámok a kód mozgásával eltérhetnek, ezért
> a hivatkozás elsősorban függvénynév szerinti.

---

## 0. TL;DR

- A placementet a **konstruktív, kritikus-aware sheet builder** (`build_critical_aware_seed`) vezeti, ha
  `VRS_SHEET_BUILDER=1`; különben a régi LBF-seed fut. A **CDE (jagua) marad a collision/boundary
  igazság** — minden jelölt a végén CDE-validált.
- A Q56–Q60 modulok **döntéstámogató / jelölt-generáló rétegek**, NEM második collision-solver. A
  „elfér-e" kérdést a CDE + a **co-movable separation** (`try_seeded_critical_separation` →
  `simultaneous_critical_repack`) dönti el.
- A Q61 a Q56–Q60 modulokat **ténylegesen bekötötte** a valós `try_admit_critical` /
  `build_critical_aware_seed` útba, **gate-ek mögött**, additív consumption-diagnosztikával.
- **Mért, őszinte viselkedés:** spacing 0-n a valós builder-út **3 nagy LV8-at egy táblára** placel
  (geometriailag feasibilis); valós spacingen (8) a skeleton+modul út **max 2 kritikus/tábla** → ez egy
  **algoritmikus rés** (RNG/idő-fragilis 3-way interlock), nem geometriai lehetetlenség.
- **Gate-OFF default → byte-azonos** a korábbi viselkedéssel (determinizmus-gate 10/10 byte-azonos).

---

## 1. Belépési pont és pipeline-routing

- `vrs_solver::adapter::solve(SolverInput) -> SolverOutput`.
- `SolverInput.optimizer_pipeline == sparrow_cde_multisheet` + `collision_backend == cde` esetén a
  Sparrow CDE multisheet út fut.
- A sheetek margin-kezelése az adapter szintjén történik: a tábla a placement előtt
  `inset = margin − spacing/2`-vel elő van zsugorítva (Q55B-ben rögzített modell). A fő solver
  belsejében `spacing_mm` a part-geometriába van „beépítve" a spacing-expanded kontúron keresztül.
- A kimenet: `SolverOutput { status, placements[], unplaced[], metrics, optimizer_diagnostics, ... }`.
  - `status == "ok"`: full feasibilis (minden placed, 0 collision, 0 boundary).
  - `status == "partial"`: a placed partok érvényesek (0 collision/boundary), de van unplaced.
  - A solver **sosem** ad ki átfedő/határsértő placementet.

---

## 2. Per-part geometria és preprocessing (egyszer, part-típusonként)

A `SparrowProblem::from_solver_input(...)` (model.rs) part-típusonként **egyszer** számolja és Rc-vel
megosztja az instance-ek között:

| Adat | Mező / forrás | Szerep |
|---|---|---|
| Eredeti kontúr | `SPInstance.base_shape: Rc<CdeBaseShape>` | boundary/output igazság |
| Spacing-expanded kontúr | `SPInstance.spacing_collision_base_shape` | part-part collision/search geometria (spacing fél-offset kifelé). Ha `spacing_mm==0`, ugyanaz az Rc, mint a base. |
| Q47 profil | `SPInstance.shape_profile: Rc<PartShapeProfile>` | `criticality_tier()`, `is_critical()`, `priority_score`, area/aspect/fill, `is_large_anchor`, `is_high_interlock_potential` |
| Q53A kontúrfeature-ök | `shape_profile.contour_features` (`ContourFeatureSet`) | dominant edges, extreme points, concave/protrusion, `sheet_edge_alignment_angles` |
| **Q56A OrientationCatalog** | `SPInstance.orientation_catalog: Rc<OrientationCatalog>` | előre számolt rotációs jelöltek (sheet vertical/horizontal alignment, **min-width/min-height**, dominant edge, 180° flip), **spacing-expanded true-extrema** mintákkal, determinisztikus deduppal |
| **Q56B PartAnalysis** | `SPInstance.part_analysis: Rc<PartAnalysis>` | soft shape tag-ek, `fit_difficulty`, family key, interlock/anchor/filler score-ok; újrahasználja a profilt + OrientationCatalog-ot |

Kulcs geometriai elv: az orientációs/anchor-extrémák a **forgatott spacing-expanded kontúrpontokból**
jönnek (nem `part.width/height`-ból, nem bboxból). Continuous partnál a min-width orientáció valódi
**tört szög** lehet (pl. `Lv8_11612_6db` → **92.75°**), nem 0/90/180/270 snap.

---

## 3. A konstruktív sheet builder (`build_critical_aware_seed`)

`VRS_SHEET_BUILDER=1` esetén ez állítja elő a kiinduló layoutot (különben LBF-seed; a builder-seed
csak akkor használt, ha **teljes és feasibilis**, egyébként RNG-restore + fallback, idő-cappel).

A `build_criticality_queues` (fixed_sheet.rs) három sorba osztja a partokat: **critical / structural /
filler** (priority szerint). Táblánként:

1. **Kritikus admission fázis (co-movable anchorok).** Sorban próbálja behozni a kritikus partokat
   `try_admit_critical`-lal. Egy `critical_frontier` guard (skeleton ON: 4, OFF: 2) zárja a fázist,
   ha túl sok egymás utáni bukás van. A **táblánkénti kritikus szám csak nő** — egy bukott admission
   **sosem** távolítja el a már behozottakat (ez a Q58B best-partial invariáns alapja).
2. **Strukturális + filler fázis.** A maradék partok `direct_insert_on_sheet` density-insertje.

A tábla-szám **emergens**: addig nyit újat, amíg van behozandó part. A fázis lezárásának oka rögzül
(`bpp_critical_phase_close_reason`: deadline / frontier_fail_limit / critical_exhausted / ...).

---

## 4. Skeleton szerepek (`VRS_SHEET_BUILDER_SKELETON=1`)

Ha a skeleton aktív, minden kritikus jelölt admission ELŐTT **szerepet** kap a tábla aktuális
topológiájából + a part Q47 profiljából (`assign_role`, sheet_skeleton.rs):

- **`SkeletonRole::Anchor`** — a tábla még üres kritikusból; az első nagy part, táblaélhez igazítva.
- **`SkeletonRole::Interlock`** — van nyitott anchor, a jelölt beilleszthető mellé (második nagy part).
- **`SkeletonRole::BandInsert`** — az anchor/interlock pár zárt; külön él-kapcsolt szabad sávba (harmadik).

A `try_admit_critical` a szerep szerint **route-olja a jelölt-generálást** (`role_match`), és
szerep-szintű countereket vezet (`bpp_role_anchor/interlock/band_insert_generated/accepted`).

---

## 5. `try_admit_critical` — a teljes admission-folyamat (Q61 wiringgel)

Egy kritikus part egy táblára való behozatalának lépései (a sorrend a lényeg):

### (A) Feature-first direkt (nem Anchor szerep)
Egy feature-seed alapú direkt density-insert az admittált anchorokat fixen tartva. Anchor szerepnél
ez kihagyott (`anchor_skip_direct`), mert az Anchor a sheet-edge jelölteken keresztül ül le.

### (B) — SGH-Q61: Anchor → Q56C SheetEdgePlacementCatalog
`skeleton_on && role == Anchor && VRS_ANCHOR_CATALOG=1` esetén:
- `sheet_edge_placement_catalog::anchor_candidates_for_instance(inst, sheet)` a **live** instance
  spacing-expanded kontúrjából + az OrientationCatalog rotációiból **edge+corner** rect-min jelölteket
  gyárt (4 él × {corner_low, corner_high, center}), corner-first.
- Mindegyik a **ugyanazon** `try_seeded_critical_separation`-ön megy át, és **free-space score** szerint
  rangsorolódik (`best_anchor_cat`).
- **Non-regressing fallback:** a végső commitnál a meglévő Q55B sheet-edge feature-seed
  (`best_skeleton`) **elsőbbséget kap**; a katalógus csak akkor commitol, ha a meglévő út nem ad
  eredményt (`prefer_catalog = best_skeleton.is_none()`). Így a katalógus **nem rontja** a bizonyított
  co-movable interlock seedinget.
- Diagnosztika: `bpp_q61_anchor_catalog_consulted/candidates_generated/accepted`,
  `accepted_anchor_source`, `accepted_anchor_secondary_policy`.

### (C) Feature-first co-movable (a fő admission-motor)
`generate_feature_candidate_seeds_for_sheet(inst, rot, sheet, neighbours, ...)` kontúrfeature-alapú
seedeket gyárt; `role_match` szűri (Anchor → `sheet_edge`; Interlock → nem `sheet_edge`).

#### (C1) — SGH-Q61: BandInsert → Q59 true-extreme slot-edge
`skeleton_on && role == BandInsert` esetén megkeresi a legnagyobb él-kapcsolt szabad slotot
(`largest_edge_connected_free_slot`). Ha van slot:
- `VRS_BAND_INSERT_TRUE_EXTREME=1` esetén a `band_insert_slot_edge::slot_edge_seeds_for_instance`
  true-extreme, continuous (akár fractional) slot-edge jelölteket próbál **a bbox-`band_insert_seeds`
  ELŐTT**; ezeket `try_seeded_critical_separation` validálja.
- Ha egyik sem fogadódik el → `bpp_q61_fallback_to_bbox_band_insert=true`, és a régi bbox-út fut.
- Diagnosztika: `bpp_q61_band_insert_true_extreme_consulted/slot_edge_candidates_generated/accepted`.

#### (C2) — SGH-Q61: Interlock → Q57A/B pair index
`skeleton_on && role == Interlock && VRS_INTERLOCK_PAIR=1` esetén, a generic neighbour-feature seedek
**ELŐTT**:
- Megkeresi a táblán már elhelyezett anchor world-bbox-át.
- `quantify::pair_matrix::interlock_seeds_against_anchor(anchor_bbox, inst)` pár-kompatibilis relatív
  placementeket gyárt (side-by-side jobbra/fölé + **átfedő flip-interlock** a jelölt OrientationCatalog
  rotációival és 180° flipjeivel). Az átfedő seed szándékos: a separation oldja fel interlockká.
- Mindegyik `try_seeded_critical_separation`-ön megy át. Ha elfogadódik → accepted + return.
- Ha egyik sem → **explicit** `bpp_q61_pair_rejection_summary` (boundary|collision|candidate_not_clear|
  refinement_failed) + `bpp_q61_interlock_fallback_to_neighbour=true`, majd a neighbour-feature út fut.
  **Nincs néma fallback.**
- Diagnosztika: `bpp_q61_pair_index_consulted/pair_candidates_generated/accepted`.

#### (C3) Free-space-megőrző rangsor
A feasibilis feature-seedek közül a skeleton úton a **legnagyobb él-kapcsolt szabad bandet** hagyó
(`sheet_freespace_score`, `largest_edge_connected_free_area`) nyer (bounded számú jelölt rangsorolva),
hogy a KÖVETKEZŐ kritikusnak maradjon hely. A commitnál a `best_anchor_cat` (Q56C) vs `best_skeleton`
(meglévő) közül a magasabb free-space-ű nyer (a katalógus csak ≥/fallback esetén).

### (D) Explicit fallback
Ha minden feature-first út bukik: bbox/uniform direkt insert, majd centroid-seeded co-movable.

---

## 6. Az interlock-motor: `try_seeded_critical_separation` + `simultaneous_critical_repack`

Ez a **valódi** „elfér-e tightan" motor:
- Egy (akár **átfedő**) seedből indul, hozzáadja a jelöltet a layouthoz.
- Az **összes admittált kritikust EGYÜTT mozgatja** (co-movable), density-biased / overlap-toleráns
  separationnel, **continuous rotációval**.
- Ezen belül hívja a `simultaneous_critical_repack`-et (Q55D'-2, **simulated annealing**): az ÖSSZES
  part egyszerre perturbálódik, Metropolis-elfogadással, hogy a mély, egymásba-illesztett (nested,
  bbox-átfedő, kontúr-tiszta) konfiguráció elérhető legyen. Energy = pairwise spacing-collision overlap
  proxy + boundary penalty; a **CDE** dönti a végső feasibilitást.

Q61 instrumentáció: amikor a táblán már ≥1 kritikus van és újat hozunk be (a separation a korábbiakat
is mozgatja), `bpp_q61_simultaneous_critical_consulted=true`, `simultaneous_group_attempts++`,
`previous_group_parts_moved=true` (`VRS_SIMULTANEOUS_CRITICAL=1`).

---

## 7. Best-partial preservation (Q58B)

`VRS_SHEET_FEASIBILITY_HINTS=1` esetén `bpp_q61_best_partial_tracker_enabled=true`. A
`build_critical_aware_seed` loop a táblánkénti kritikus számot **csak növeli**; egy bukott admission
sosem távolítja el a már behozottakat. Ezért a **„valid 2/3 → final 1/3" regresszió konstrukció szerint
lehetetlen** a valós outputban. Diagnosztika: `bpp_q61_best_partial_max_critical_count`,
`bpp_q61_best_partial_downgrades_rejected` (nő, ha egy 3. attempt bukik, miközben ≥2 már bent van).

---

## 8. Gate-ek (kapcsolók)

| Gate (env) | Mit kapcsol | Default |
|---|---|---|
| `VRS_SHEET_BUILDER` | konstruktív kritikus-aware builder | off |
| `VRS_SHEET_BUILDER_SKELETON` | skeleton szerepek + szerep-route | off |
| `VRS_FEATURE_CANDIDATES` | kontúrfeature-seed generálás | off |
| `VRS_ANCHOR_CATALOG` | **Q56C** anchor-katalógus fogyasztása (Anchor) | off |
| `VRS_INTERLOCK_PAIR` | **Q57B** pair-seed fogyasztása (Interlock) | off |
| `VRS_BAND_INSERT_TRUE_EXTREME` | **Q59** true-extreme slot-edge (BandInsert) | off |
| `VRS_SHEET_FEASIBILITY_HINTS` | **Q58B** best-partial tracker enabled | off |
| `VRS_SIMULTANEOUS_CRITICAL` | **Q60** simultaneous instrumentáció | off |
| `VRS_PAIR_INDEX` | PairCompatibilityIndex építés (Q57A standalone) | off |

**Minden gate default OFF** → a production/determinizmus-smoke byte-azonos a Q61 előtti viselkedéssel.

---

## 9. Diagnosztika (a kimenetben)

A `SolverOutput.optimizer_diagnostics.bpp_reduction` (`BppReductionDiagnostics`, io.rs) tartalmazza a
teljes admission-képet, köztük a Q61 consumption-mezőket (mind additív, `#[serde(default)]`):

- Anchor: `bpp_q61_anchor_catalog_consulted`, `..._candidates_generated`, `..._accepted`,
  `bpp_q61_accepted_anchor_source`, `bpp_q61_accepted_anchor_secondary_policy`.
- Interlock: `bpp_q61_pair_index_consulted`, `..._candidates_generated`, `..._accepted`,
  `bpp_q61_interlock_fallback_to_neighbour`, `bpp_q61_pair_rejection_summary`.
- BandInsert: `bpp_q61_band_insert_true_extreme_consulted`, `..._slot_edge_candidates_generated`,
  `..._accepted`, `bpp_q61_fallback_to_bbox_band_insert`.
- Best-partial: `bpp_q61_best_partial_tracker_enabled`, `..._max_critical_count`,
  `..._downgrades_rejected`.
- Simultaneous: `bpp_q61_simultaneous_critical_consulted`, `..._group_attempts`,
  `bpp_q61_previous_group_parts_moved`.
- Plusz a meglévő: `bpp_max_critical_per_sheet`, `bpp_critical_admitted/deferred`,
  `bpp_role_*_generated/accepted`, `bpp_band_slot_found`, `bpp_critical_phase_close_reason`.

---

## 10. Mért, őszinte viselkedés (valós `adapter::solve`, 3 × Lv8_11612_6db, 1500×3000, continuous)

| Konfiguráció | spacing | eredmény |
|---|---|---|
| builder-only (skeleton off), stock 2 | 0 | **3/3 EGY táblára** (`by={0:3}`, status=ok) → feasibilis |
| builder-only, stock 3 | 0 | 2+1 (max 2/tábla) — **stock-/RNG-fragilis** |
| skeleton + összes modul | 0 | max **2**/tábla (modulok fogyasztva: anchor 24 + pair 32 jelölt) |
| skeleton + összes modul | 8 (valós) | max **2**/tábla, best valid partial = 2 |

**Következtetés:** a 3-part packing **geometriailag feasibilis** (a builder-út 3/3-a bizonyítja) — soha
nem „nem fér el". A skeleton+modul út a modulokat **fogyasztja**, de a co-movable/SA separation a
modul-seedekből **valós spacingen nem konvergál a tight 3-way nested interlockra**. Ez **algoritmikus
rés** (Q61 STATUS: `PARTIAL_FAIL_ALGORITHMIC_GAP`), és a 3/3 RNG-/idő-fragilis.

---

## 11. Kemény invariánsok (amik mindig állnak)

- A **CDE** a végső collision/boundary igazság; bbox/grid csak prefilter/ranking/diagnosztika.
- **Continuous rotation** megmarad (nincs 0/90/180/270 kényszer); a min-width lehet fractional.
- **Spacing/margin sosem gyengül** a pass kedvéért.
- **Nincs part-id / koordináta hardcode** a solver-logikában.
- A best-partial **sosem** degradál (valid 2/N → final 1/N lehetetlen).
- **Fallback mindig logolt** (nincs néma fallback).
- Gate-OFF → byte-azonos, determinizmus 10/10.

---

## 12. Modul-/fájltérkép

| Fájl | Tartalom |
|---|---|
| `optimizer/sparrow/bpp_reduction.rs` | `build_critical_aware_seed`, `try_admit_critical`, `try_seeded_critical_separation`, `simultaneous_critical_repack`, `band_insert_seeds`, density-insert, **Q61 wiringök** |
| `optimizer/sparrow/sheet_skeleton.rs` | `SkeletonRole`, `assign_role`, `largest_edge_connected_free_area/slot` |
| `optimizer/sparrow/model.rs` | `SPInstance` (+ `orientation_catalog`, `part_analysis`), `from_solver_input` |
| `optimizer/sparrow/orientation_catalog.rs` | **Q56A** OrientationCatalog + `anchor`-hoz rotációk |
| `optimizer/sparrow/part_analysis.rs` | **Q56B** ShapeProfileV2 |
| `optimizer/sparrow/sheet_edge_placement_catalog.rs` | **Q56C** + `anchor_candidates_for_instance`, `anchor_catalog_enabled` |
| `optimizer/sparrow/quantify/pair_matrix.rs` | **Q57A** PairCompatibilityIndex + `interlock_seeds_against_anchor` |
| `optimizer/sparrow/interlock_pair.rs` | **Q57B** pair→interlock konverzió + `interlock_pair_enabled` |
| `optimizer/sparrow/sheet_feasibility.rs` / `sheet_feasibility_bpp.rs` | **Q58A/Q58B** hints + best-partial |
| `optimizer/sparrow/band_insert_slot_edge.rs` | **Q59** + `slot_edge_seeds_for_instance`, `band_insert_true_extreme_enabled` |
| `optimizer/sparrow/critical_simultaneous.rs` | **Q60** standalone group admission (önálló; a production út a `simultaneous_critical_repack`-et használja) |
| `io.rs` | `BppReductionDiagnostics` (+ q61 mezők), `SolverOutput` |

---

## 13. A valódi következő lever

A 3/3 valós spacingen való **stabil** eléréséhez egy **determinisztikus, interlock-célzott refinement**
kell (nem RNG-fragilis SA), amely a Q56C/Q57B/Q59 modul-seedeket szándékosan a tight 3-way nested
konfigurációba viszi — a spacing/margin gyengítése nélkül. Ez folytatja a Q51 saját „density-biased
separation toward interlock" R&D irányát. A modul-réteg (jelöltek, rotációk, extrémák, pár-relatív
transzformok) készen áll erre; a hiányzó elem a **konvergens, nem-fragilis group-refinement**.
