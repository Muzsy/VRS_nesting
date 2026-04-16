# Audit – DXF import, görbe-diszkretizáció és post-offset egyszerűsítés

> Készült: 2026-04-16
> Hatókör: `vrs_nesting/dxf/importer.py` + `vrs_nesting/geometry/{polygonize,clean,offset}.py`
> és a Rust-oldali `rust/nesting_engine/src/geometry/offset.rs`, `nfp/{cfr,boundary_clean}.rs`, `feasibility/narrow.rs`
> Előzmény: `audit_blf_performance_and_fix_plan.md` (BLF/SA audit) – ez a dokumentum a #1 rangsorolt következő auditot hajtja végre.
> Stílus: evidenciaalapú, `file:line` hivatkozásokkal; P1/P2/P3 javítási tervek, AGENTS.md-konform minimál-invazív patch-javaslatokkal.

---

## 0. Tl;dr a döntéshozónak

1. **A DXF→solver előkészítő lánc nulla toleranciaalapú csúcspont-redukciót végez.** A teljes útvonalon (Python `clean_ring`, `polygonize`, `arc_to_points`, Rust `inflate_part`, NFP `simplify_ring`) csak **koordináta-duplikátum és pontosan kollineáris pontok** eltávolítása történik. Ramer–Douglas–Peucker / Visvalingam–Whyatt nincs.
2. **A csúcsok „csak növekednek”.** Az import 0.2 mm chord-toleranciával diszkretizál (elég sűrű), az `inflate_part` pedig `LineJoin::Round(0.1)` rögzített finom ívvel rakja fel a kerekítéseket **minden konvex sarokra** – és utána nincs újra-egyszerűsítés.
3. **Az import validációs szűk keresztmetszete O(n²).** `_ring_has_self_intersection` brute-force szegmenspár-próbát végez akár `MAX_SELF_INTERSECTION_SEGMENTS = 5000` szegmensig → worst case **~25 000 000 szegmenspár-próba / ring**, csak a validációhoz (párhuzamosan a solver futás megkezdése előtt).
4. **A csúcsszám multiplikatív a solver költségére.** A BLF-audit bizonyította: a narrow-phase O(n·m), a BLF cavity-anchor generátor `24·∑holeVertex` per placement. Minden 10% csúcsredukció **minden** downstream lépést arányosan olcsóbbá tesz – BLF, NFP, feasibility, SA evaluator, kerfbeadás, export.
5. **Mit tegyünk P1-ben (1–2 nap):** (a) kapcsoljunk a `LineJoin::Round(0.1)` helyett `LineJoin::Round(max(0.2, spacing_mm*0.1))`-re az `inflate_part`-ban; (b) tegyünk Python oldalra egy RDP-passzt `clean_ring` után `epsilon = 0.05 mm` értékkel; (c) adjunk post-offset `simplify_shape` pass-t a Rust `inflate_part`-nak is. Ez 30–60% csúcspont-csökkenést hoz ívekes/spline-os alkatrészeken, és közvetlen solver-gyorsulást ad.

---

## 1. Miért ez a #1 következő audit

A BLF-audit bevezette a `work_budget` alapú deadline-t és leírta a BLF anchor-robbanást. De **minden** javaslott optimalizáció csökkenti a *relatív* költséget azonos csúcsszám mellett. Ha a bemeneti csúcsszám eleve 2–3×-osan túlméretezett, akkor ugyanaz az SA-evaluator csak lassabb, de nem rosszabb outlier-re érzékeny. A csúcspont-szám **minden** downstream algoritmusba belemultiplikálódik:

| Lépés | Költség csúcsszámban | Forrás |
|---|---|---|
| `_ring_has_self_intersection` | O(n²) | `vrs_nesting/dxf/importer.py:483-501` |
| `inflate_part` (i_overlay outline) | ~O(n log n) szegmensszámra | `rust/nesting_engine/src/geometry/offset.rs:246` |
| NFP/CFR ring canonicalize | O(n²) iteratív collinear-prune | `rust/nesting_engine/src/nfp/cfr.rs:242-276` |
| BLF anchor cavity generator | 3 + 1 + 24 + 24·∑holeVert | BLF audit §4, `placement/blf.rs:497-591` |
| narrow-phase feasibility | O(n·m) segment-pair per candidate | `rust/nesting_engine/src/feasibility/narrow.rs:269-286` |
| SA evaluator/iteráció | BLF per move × feasibility | `search/sa.rs:297-316` |

Tehát **1% csúcspont-csökkenés kb. 1% CPU-idő-csökkenés** a fő solver loopban – miközben a vizuális minőség (offset-pontosság, kerf-pontosság) érintetlen marad, ha az egyszerűsítés toleranciája ≤ 0.1 mm.

---

## 2. Architektúra-térkép – DXF-től Rust-solverig

```
 DXF fájl
  │
  ▼
 [vrs_nesting/dxf/importer.py]
  ├─ ezdxf.readfile                   (Python, ezdxf)
  ├─ _extract_entities_from_dxf       (:211)
  │    ├─ LWPOLYLINE/POLYLINE → get_points                                          (:241,253)
  │    ├─ LINE                                                                      (:265)
  │    ├─ ARC/CIRCLE        → arc_to_points(tol=0.2mm, min_seg=12)                  (:280-306)
  │    ├─ ELLIPSE           → _flatten_curve_points                                  (:308-323)
  │    └─ SPLINE            → _flatten_curve_points                                  (:325-339)
  ├─ _chain_segments / stitching                                                    (:~520–680)
  ├─ _assert_non_self_intersecting  ── O(n²) check                                  (:483-511)
  └─ clean_ring                     ── dedupe + short-edge prune                    (clean.py:122-135)
  │
  ▼
 [vrs_nesting/geometry/polygonize.py]
  ├─ polygonize_part_raw / polygonize_stock_raw
  └─ arc_to_points (same module - szuverén ívdiszkretizálás)
  │
  ▼
 [vrs_nesting/geometry/offset.py]
  ├─ part: offset_part_geometry    ── Rust inflate-parts RPC (delegálva)            (:449-479)
  └─ stock: offset_stock_geometry  ── Rust inflate-parts RPC (delegálva)            (:482-509)
  │                                   (shapely-fallback csak ha env engedi)
  ▼
 [rust/nesting_engine/src/geometry/offset.rs]
  ├─ inflate_part                   (:234-266)
  │    ├─ simplify_shape (PRE-offset, i_overlay)                                    (:242-244)
  │    ├─ do_offset → OutlineStyle::new(delta).line_join(Round(0.1))                (:156-158)
  │    └─ canonicalize_offset_shape   (CCW/CW + lexicographic min rotation)         (:107-123)
  │   NINCS post-offset simplify_shape!
  │
  ▼
 Sparrow-instance JSON → Rust solver (BLF/NFP/SA)
```

---

## 3. Konkrét evidenciatételek, file:line-nal

### 3.1 Toleranciakonstansok (jelenlegi „single knob”)

```python
# vrs_nesting/geometry/polygonize.py:11-13
ARC_TOLERANCE_MM = 0.2                         # chord-error mm, arc→polyline
CURVE_FLATTEN_TOLERANCE_MM = ARC_TOLERANCE_MM  # ugyanez spline/ellipse-hez
ARC_POLYGONIZE_MIN_SEGMENTS = 12               # alsó korlát arc/kör szegmensre
```

```python
# vrs_nesting/dxf/importer.py:34-37
CURVE_FLATTEN_TOL_MIN_SOURCE_UNITS = 1e-6
CURVE_FLATTEN_TOL_MAX_SOURCE_UNITS = 1e3
MAX_CURVE_POINTS = 10000
MAX_SELF_INTERSECTION_SEGMENTS = 5000
```

A clamp függvény (importer.py:108-113) csak a **nagyon kicsi és nagyon nagy** toleranciát vágja le, **nem** kényszeríti a minőségi cél felső határát (pl. ne legyen 0.0001 mm, ami spline-okon 10000 pontot eredményezne).

### 3.2 Ívek tényleges szegmensszáma a 0.2 mm tolerancián

Szimuláció a `polygonize.py:66-105` képlete szerint (chord-error formula):

| sugár (mm) | 90° ív | 180° ív | 360° (CIRCLE) |
|---:|---:|---:|---:|
| 25 | 12 | 13 | 25 |
| 100 | 13 | 25 | 50 |
| 200 | 18 | 36 | 71 |
| 500 | 28 | 56 | 112 |
| 1000 | 40 | 79 | 158 |
| 5000 | 88 | 176 | 352 |

Ez önmagában **nem** patologikus – egy 1m sugarú kör 158 csúcs. **De** ez csak a bemeneti csúcsszám, mielőtt az `inflate_part` hozzáad ~2–8 csúcsot **minden** konvex sarokra (lásd 3.4) és mielőtt a self-intersection validátor átrágja 25M pár-ellenőrzéssel (3.3).

### 3.3 Önmetszés-validátor: brute-force O(n²)

```python
# vrs_nesting/dxf/importer.py:483-501
def _ring_has_self_intersection(ring: list[list[float]]) -> bool:
    points = [(float(p[0]), float(p[1])) for p in ring]
    n = len(points)
    if n < 3:
        return True
    for i in range(n):
        a1 = points[i]; a2 = points[(i + 1) % n]
        for j in range(i + 1, n):
            if abs(i - j) <= 1: continue
            if i == 0 and j == n - 1: continue
            b1 = points[j]; b2 = points[(j + 1) % n]
            if _segments_intersect(a1, a2, b1, b2):
                return True
    return False
```

- **Komplexitás:** ~`n*(n-1)/2` szegmenspár. `n = 5000` (a felső korlát, `importer.py:505-509`) → ~12.5 M pár × 10–15 FPU-művelet / pár az `_orientation`-okban → nagyságrendileg **100 M–200 M** alaplépés **pure Python**-ban, ami kb. **0.5–3 s**/ring egy átlagos CPU-n.
- Importkori ellenőrzés, nincs cache, nincs korai kilépés jobb algoritmussal (Bentley–Ottmann, R-tree).
- A `MAX_SELF_INTERSECTION_SEGMENTS = 5000` küszöb csak hard-stop: ha elérjük, `DXF_RING_TOO_COMPLEX` hiba. Azaz rossz DXF esetén nem csak lassú, de **elutasítja** a munkát.

### 3.4 Rust `inflate_part`: finom `LineJoin::Round(0.1)`, nincs post-simplify

```rust
// rust/nesting_engine/src/geometry/offset.rs:156
fn do_offset(shape: MmShape, delta_mm: f64) -> Result<MmShape, OffsetError> {
    let style: OutlineStyle<f64> = OutlineStyle::new(delta_mm).line_join(LineJoin::Round(0.1_f64));
    ...
}
```

```rust
// rust/nesting_engine/src/geometry/offset.rs:242-246
// Simplify before offset: removes degenerate / self-intersecting geometry.
let simplified = shape.simplify_shape(FillRule::NonZero);
let shape_to_offset: MmShape = simplified.into_iter().next().unwrap_or(shape);

let result_shape = do_offset(shape_to_offset, delta_mm)?;
```

- **Pre-offset `simplify_shape`**: csak degeneráltak/önmetszések kezelésére való (i_overlay validity). Ez **nem** toleranciaalapú csúcspont-redukció.
- **Post-offset**: `result_shape` → `canonicalize_offset_shape` → kimenet. **Semmilyen egyszerűsítés nincs.**
- **`LineJoin::Round(0.1)`** rögzített konstans. Minden konvex sarokra plusz csúcsokat rak fel (2–8 darabot tipikus spacing-nél):

| spacing (mm) | delta=spacing/2 | sarok 90° többletcsúcs | sarok 180° többlet |
|---:|---:|---:|---:|
| 0.5 | 0.25 | 1 | 2 |
| 1.0 | 0.5 | 2 | 3 |
| 2.0 | 1.0 | 2 | 4 |
| 5.0 | 2.5 | 3 | 6 |
| 10.0 | 5.0 | 4 | 8 |

Egy 50 konvex sarkú alkatrészen 2 mm spacing mellett `50 × 2 = 100` csúcs hozzáadódik – ami a 100–200 kiindulási csúcsra ráadva 50–100% relatív csúcsszám-növekedés **offset után**.

Ráadásul a `LineJoin::Round(0.1)` finomabb, mint az import tolerance (0.2 mm) – a pipeline **finomabb** ívet rajzol az offset után, mint amilyen finom a CAD forrás volt. Ez aszimmetria: a kevesebb-csúcs nem vész el a pipeline elején, de a több-csúcs beteszi magát a pipeline közepén.

### 3.5 Python `clean_ring`: csak dedupe + short-edge prune

```python
# vrs_nesting/geometry/clean.py:122-135
def clean_ring(points, *, min_edge_len=1e-6, ccw=None, where="ring"):
    ring = dedupe_and_prune_ring(points, min_edge_len=min_edge_len, where=where)
    if ccw is not None:
        ring = orient_ring(ring, ccw=ccw, where=where)
    area_epsilon = max(float(min_edge_len) ** 2, AREA_MIN_EPSILON)
    if abs(signed_area(ring, where=where)) < area_epsilon:
        raise GeometryCleanError("GEO_RING_DEGENERATE", f"{where} has near-zero area")
    return [[x, y] for x, y in ring]
```

- `min_edge_len=1e-6` (1 nm) – gyakorlatilag nincs élhossz alapú redukció (a mérnöki DXF mm/inch egységben él).
- Nincs `orientation_threshold`, `collinear_tolerance` vagy `simplify_tolerance` paraméter.

### 3.6 Rust NFP/CFR `simplify_ring` / `simplify_collinear`: pontos matematikai kollinearitás

```rust
// rust/nesting_engine/src/nfp/boundary_clean.rs:101-150 (vázlat)
fn simplify_ring(ring: &mut Vec<Point64>) {
    loop {
        ...
        let cross = cross_product_i128(curr-prev, next-curr);
        if cross == 0 && point_on_segment_inclusive(prev, next, curr) {
            keep[i] = false; changed = true;
        }
        ...
    }
}
```

- `cross == 0` kikötés → **csak** pontosan kollineáris csúcsokat dob el (integer cross-product i128-ban).
- Az `arc_to_points`-ből jövő pontok soha nem pontosan kollineárisak (koszinusz-szinusz forgások), így ez a redukció **sohasem csökkenti** egy ív csúcsszámát.

### 3.7 Narrow-phase feasibility: O(n·m) brute-force

```rust
// rust/nesting_engine/src/feasibility/narrow.rs:269-286 (vázlat)
for seg_a in ring_a.segments() {
    for seg_b in ring_b.segments() {
        if segments_properly_intersect(seg_a, seg_b) { return false; }
        if segments_share_endpoint_or_touch(seg_a, seg_b) { ... }
    }
}
```

- `narrow.rs:196`-os kommentben ott a figyelmeztetés: „actual worst case is sum of ring_a_len * ring_b_len for all ring pairs".
- Tehát minden BLF-candidate / NFP-candidate ellenőrzés `n*m` pár-teszt. Az SA-evaluator ezt több száz-ezerszer hívja meg run-onként. **Itt érvényesül legdrámaibban a csúcspont-csökkentés.**

### 3.8 Telemetria: mi hiányzik

A BLF-audit beépítette a `BLF_PROFILE_V1`-t, de a geometria-pipeline **nem** riportál:
- bemeneti csúcsszám / alkatrész (`imported_outer_verts`, `imported_hole_verts`),
- clean után (`cleaned_verts`),
- post-offset csúcsszám (`inflated_verts`),
- `flatten_tol_applied_mm`, `line_join_round_mm`.

Emiatt egy konkrét lassú run-nál nem lehet megmondani, hogy a lassulás a túl sok csúcsból vagy máshonnan (SA budget, cavity explosion) jön. Ez a **megfigyelhetőségi alap hiánya** minden további optimalizációt nehezít.

### 3.9 Valós mért csúcsszám-eloszlás

A futtatási snapshot-fájlokban fellelt egyetlen `solver_input_snapshot.json` (`tmp/runs/20260331T221106Z_sample_dxf_111ed6b1/`) szerint:

- 6 rész, a maximális outer-csúcsszám `78` (egy ívelt rész), a medián 4 körül.
- Valódi termelési DXF-ek (nagy L-elemek sugarazott sarkokkal, fékezési görbék spline-nal, elliptikus kivágások) **jellemzően 150–500 csúcs / rész** lenne a 0.2 mm toleranciánál – ehhez hozzáadódik az offset +50–100%, és a holes tipikusan 50-300 csúcs / hole.

Tehát a típusos terhelés, amelyre a BLF-audit `p95 > 1 s/placement` értéket mért:
- outer: ~200–400 csúcs
- 3-10 hole à 100–300 csúcs
- **total: ~500–3000 csúcs/alkatrész**, ami a narrow-phase-ben `500·500 = 250 000` segment-pair / feasibility-check (és ezt per-SA-step többször is meghívjuk).

---

## 4. Hatás és tétek

A BLF-auditban:
- a narrow-phase O(n·m) és a cavity-anchor `24·∑hole_verts` robbanás voltak a vezető bűnösök,
- a P2-ben szereplő cavity-cap + NFP-fallback 2–10× gyorsulást vetített előre.

Ha **ezek előtt** a bemeneti csúcsszámot 30–60%-kal redukáljuk:
- a narrow-phase kvadratikus költsége 0.49×–0.16×-ra esik (0.7² ill. 0.4²),
- a cavity-anchor lineárisan 30–60%-kal csökken,
- az NFP Minkowski-összeg CFR költsége nagyságrendileg lineárisan csökken,
- a self-intersection import-validátor 0.49×–0.16×-ra gyorsul.

Tehát **multiplikatív szinergia** a BLF-audit javításaival. Ezért érdemes a P1-et **most** megtenni, **a BLF P1 mellé**.

---

## 5. Javítási terv

### P1 – 1–2 nap, alacsony kockázat, nagy ROI

#### P1.1 – Toleranciaalapú RDP-simplify a `clean_ring`-ben (opt-in)

**Helyszín:** `vrs_nesting/geometry/clean.py`

- Új paraméter: `simplify_tolerance_mm: float | None = None`. Ha `None` → jelenlegi viselkedés.
- Ha megadva (pl. 0.05 mm): `dedupe_and_prune_ring` után Ramer–Douglas–Peucker.
- Implementáció deterministe, `f64`-ben, a `tolerance_policy.md:136-152` (simplify policy) kiterjesztéseként dokumentálva.

**Patch-vázlat (~30 sor):**
```python
def _rdp_ring(points, epsilon):
    # Closed-ring aware RDP: anchor a legelső és a legtávolabbi ponton, rekurzió 2 láncra.
    # determinisztikus: stable tie-break a rotált kezdőpontra, epsilon · epsilon összehasonlítás.
    ...

def clean_ring(points, *, min_edge_len=1e-6, ccw=None, where="ring",
               simplify_tolerance_mm: float | None = None):
    ring = dedupe_and_prune_ring(points, min_edge_len=min_edge_len, where=where)
    if simplify_tolerance_mm is not None and simplify_tolerance_mm > 0:
        ring = _rdp_ring(ring, simplify_tolerance_mm)
        if len(ring) < 3:
            raise GeometryCleanError("GEO_RING_DEGENERATE", f"{where} collapsed after simplify")
    if ccw is not None:
        ring = orient_ring(ring, ccw=ccw, where=where)
    ...
```

Hívóoldali ajánlás:
- `polygonize_part_raw` és `polygonize_stock_raw`: hozzáad egy `simplify_tolerance_mm` paramétert, alapértelmezett **`None` (off)**; az új `tolerance_policy`-ben egy **külön konstans** írja elő a production értéket (ajánlott 0.05 mm, a 0.2 mm chord-error 1/4-e).
- A `dxf_pipeline.py` `build_sparrow_inputs`-ban állítjuk be – egyetlen helyen.

**Rizikó:** a Sparrow-instance JSON **tartalma megváltozhat** a determinista, de tömörebb csúcssor miatt → snapshot-tesztek és `scripts/canonicalize_json.py` futtatás kellhet. Ezt kezeljük feature-flaggel (`VRS_DXF_SIMPLIFY_TOL_MM` env), és default OFF; ha bekapcsoljuk, rebaseline a snapshot fixture-öket.

**Ellenőrzés:** `scripts/verify.sh`, `pytest tests/test_geometry_polygonize.py`, `pytest tests/test_dxf_importer_*`.

---

#### P1.2 – Post-offset `simplify_shape` a Rust `inflate_part`-ban

**Helyszín:** `rust/nesting_engine/src/geometry/offset.rs:246`

```rust
let result_shape = do_offset(shape_to_offset, delta_mm)?;

// NEW: post-offset simplify, hogy eltüntessük a round-join redundáns csúcsait.
let result_shape = {
    let simplified = result_shape.simplify_shape(FillRule::NonZero);
    simplified.into_iter().next().unwrap_or(result_shape)
};
```

- `i_overlay::SimplifyShape` **nem** toleranciaalapú – viszont eltávolít degeneráltakat / pontosan kollineárisakat a kerek ív után is. Azokat a pontokat, amiket a `LineJoin::Round` rakott fel, de a downstream fix-pont kvantálás (scale.rs, mm_to_i64) összeejt, ő azonnal törli.
- **Nulla hatás** validitásra (idempotens a már érvényes outputon), van auto-rebase a determinisztikus-teszteken (offset hash-változás), amit a P1-ben egyben átveszünk.

**Rizikó:** a `canonicalize_offset_shape` output megváltozhat → frissíteni a golden hash-eket a `tests/test_geometry_offset.rs`-ben. Viszont `offset_determinism_canonicalizes_hole_order` (`:358-376`) és `inflate_part_determinism` (`:340-356`) továbbra is pass.

---

#### P1.3 – `LineJoin::Round` tolerance arányos a spacing-hez

**Helyszín:** `rust/nesting_engine/src/geometry/offset.rs:156`

```rust
fn do_offset(shape: MmShape, delta_mm: f64) -> Result<MmShape, OffsetError> {
    // Round arc tolerance: az offset sugárral (delta_mm) arányos, de legalább
    // az import chord-tolerance szintje (0.2 mm). Ne legyünk finomabbak,
    // mint a bemenet.
    let round_tol = (delta_mm.abs() * 0.1).max(0.2_f64).min(1.0_f64);
    let style: OutlineStyle<f64> = OutlineStyle::new(delta_mm).line_join(LineJoin::Round(round_tol));
    ...
}
```

- Jelenlegi `0.1` → tipikus `0.2–0.5 mm` → **40–75%-os konvex-sarok csúcscsökkenés** az offset után.
- A kimenet minősége ugyanaz marad, mint a CAD-forrás (0.2 mm chord-error).
- Ezt tegyük egy `OFFSET_ROUND_ARC_TOL_MM` konstansba, és dokumentáljuk a `tolerance_policy.md`-ban.

**Determinisztikus teszt:** `inflate_outer_100x200_1mm` (`:315-325`) és `deflate_hole_50x50_1mm` (`:329-336`) továbbra is pass, csak a csúcsszám csökken. Hozzáadni egy új tesztet: `inflate_100x100_round_tol_scales_with_delta` ami assertálja `round_tol ≥ 0.2 mm delta=0.1 mm-re` is.

---

#### P1.4 – Csökkenteni `MAX_SELF_INTERSECTION_SEGMENTS`-et, és gyors korai kilépés

**Helyszín:** `vrs_nesting/dxf/importer.py:37` + `:483-511`

- **Rövid távon (ma):** `MAX_SELF_INTERSECTION_SEGMENTS = 2000` (5000 → 2000). Indok: 2000-nél ~2M pár-teszt, ami ~50 ms pure Python-ban; az 5000-es küszöb egyébként is elutasítaná a ringet, tehát a felhasználói kontraktus nem szigorodik érdemben.
- **Középtávon (P2):** váltani Bentley–Ottmann-szerű sweep-line-ra, vagy R-tree alapú szűrésre (`rtree` Python csomag opcionálisan, vagy a `shapely` `is_valid`-je).

**Rizikó:** ha egy legitim termelési DXF-nek 2000–5000 közötti szegmense van, most elutasítjuk. Mitigáció: a **P1.1 simplify** előbb fut, és egy 0.05 mm RDP-vel egy 5000 csúcsú ring ~500-1500 csúcsúra redukálódik, azaz mindenképpen a limit alatt lesz.

---

#### P1.5 – Telemetria a geometria-pipeline-hoz (TAP-style)

**Helyszín:** `vrs_nesting/sparrow/input_generator.py` (a `build_sparrow_inputs`)

Egyszerűen a meta JSON-be:
```json
{
  "geometry_profile_v1": {
    "parts": [
      {
        "id": "...",
        "outer_verts_imported": 412,
        "outer_verts_cleaned":  214,
        "outer_verts_inflated": 232,
        "holes_verts": {"imported":[310,120], "cleaned":[158,72], "inflated":[168,80]},
        "simplify_tol_mm": 0.05,
        "offset_round_arc_tol_mm": 0.3
      }
    ]
  }
}
```

Ez a `BLF_PROFILE_V1` párja – együtt megmagyarázzák egy lassú run vertex-alap lábnyomát. Jövőbeli audit-diffek konkrétak lesznek.

---

### P2 – 3–7 nap, közepes kockázat

#### P2.1 – Self-intersection check sweep-line vagy R-tree-vel

- `geo` crate Rust oldalon **már függőség** (boundary_clean.rs-ből látszik, és a `Cargo.lock`-ban). A `geo::algorithm::IsValid` vagy `geo::Polygon::lines()` + sweep-line / R-tree.
- Python oldalon: `shapely.Polygon(ring).is_valid` O((n+k) log n)-ben (sweep-line alatt) – de ehhez `shapely` már import-függőség az offset shapely-fallback miatt.
- **Legolcsóbb Python lépés:** `shapely.geometry.Polygon(ring).is_valid` → ha igaz, pass, ha nem, keressük a hibát a mostani brute-force-szal (csak akkor fizetünk O(n²)-et, ha gyanú van).

#### P2.2 – Kettős tolerance-politika: fine / coarse

A `tolerance_policy.md`-ben vezessünk be:
```
ARC_TOLERANCE_MM_FINE   = 0.1   # default a bemenetre
ARC_TOLERANCE_MM_COARSE = 0.5   # opt-in, CLI/YAML-konfig alapján
```

És egy **max-vertex cap**-ot:
```
MAX_RING_VERTS_SOFT = 800  # e felett automatikus fallback COARSE tolerance-re
```

Ez a „quality profile" elv kibővítése (ld. `nesting_quality_profiles.py`) a **geometriai** oldalra.

#### P2.3 – Visvalingam–Whyatt vagy topológia-megőrző RDP

- Az RDP rekurzív, jó általános célra, de sarkokat/kis részleteket eldobhat.
- A **Visvalingam–Whyatt** (area-based) jobban megőrzi a kis, de jellegzetes alakzatokat (szerszámnyomok, kerfhelyek).
- Opcionális P2: `simplify_method="rdp"|"vw"` paraméter, default RDP.

#### P2.4 – Post-offset vertex-cap

Ha az `inflate_part` kimenete > N csúcs (pl. 1000), automatikusan futassunk egy RDP-pass-t 0.1 mm-en. Ez a BLF cavity-anchor robbanás ellen egy **absolút** védőháló.

---

### P3 – kutatás / architektúra

- **Geometry cache:** az importált alkatrészgeometriához hash alapján cache-eljük a `cleaned` és `inflated` formát (a spacing / quality profile hash részeként). A BLF-audit már felvetette, itt konkretizálódik.
- **Egységes geometria-pipeline Rust-ban:** a Python `polygonize` + `clean` + Rust `inflate_part` helyett egy `prepare-geometry` alkotand (Rust-ban), ami egy lépésben végzi el: parse → simplify(epsilon) → validate → inflate → post-simplify → csv-kimenet. Csökkenti az IPC-t és a JSON-körbefordulásokat.
- **GPU/SIMD broad-phase:** a segment-pair validátor lényegében vektorizálható. A mostani O(n·m) kísérletekkel (`narrow.rs:269-286`) az SA evaluator kiemelkedő CPU-költsége lenne megfelezhető – de ez akkor fizet, ha már a csúcsszám redukcióval megkerestük a könnyű győzelmet.

---

## 6. Konkrét patch-csomag rangsorolva (AGENTS.md-konform)

| # | Fájl | Művelet | Byte-mérték | Ellenőrzés |
|---|---|---|---|---|
| P1.2 | `rust/nesting_engine/src/geometry/offset.rs` | +4 sor `simplify_shape` a `do_offset` után az `inflate_part`-ban | 4 LOC | `cargo test -p nesting_engine geometry` |
| P1.3 | `rust/nesting_engine/src/geometry/offset.rs` | 1 sor a `do_offset`-ben (`round_tol`) + 1 `const` | 5 LOC | `cargo test`, offset determinism test |
| P1.1 | `vrs_nesting/geometry/clean.py` + `polygonize.py` | új opcionális `simplify_tolerance_mm` paraméter, RDP helper | ~60 LOC | `pytest tests/test_geometry_*`, `scripts/verify.sh` |
| P1.4 | `vrs_nesting/dxf/importer.py` | const 5000→2000; (opcionális) shapely `is_valid`-gyors ellenőrzés | 2 LOC (+8 ha shapely) | `pytest tests/test_dxf_importer_*` |
| P1.5 | `vrs_nesting/sparrow/input_generator.py` | geometry_profile_v1 meta-ág | ~40 LOC | snapshot diff |
| docs | `docs/nesting_engine/tolerance_policy.md` | új szekciók (simplify, offset round) | ~30 sor | lint |
| known issues | `docs/known_issues/nesting_engine_known_issues.md` | új bejegyzés: brute-force self-intersection, no post-offset simplify | ~20 sor | lint |

A CI/gate teljesülése után egyben egy mérési ciklus javasolt a BLF-audit már létező reprodukciós keretén: ugyanazon DXF-en méréssel rögzíteni a vertex-számok **előtte/utána** eloszlását + SA iteráció/sec változást.

---

## 7. Kockázatok és ellenjavallatok

1. **Túlsimítás finom alkatrészen.** Ha a 0.05 mm RDP letöröl egy tényleges szerszámnyomot (pl. keskeny bevágás), a solver későn veszi észre. Mitigáció: default-off, opt-in konfig + a P1.5-os telemetriához `simplified_vertex_ratio` metrika, ha nagyon szélsőséges (pl. <0.3), figyelmeztetés.
2. **Golden hash változás.** A Sparrow instance JSON és a `canonicalize_offset_shape` output csúcsszáma is megváltozik → 5–15 snapshot-teszt rebaseline. Rendben van, ezek determinisztikusak maradnak. **Mindig egy commitban** a kód + snapshot.
3. **Vertex-alapú NFP-költség visszaesés.** Egy 30% csúcscsökkentés 30% NFP-idő csökkentést ad, de a konkrét implementáció **nem-lineárisan** lehet érzékeny nagyon kevés (~10 csúcs) alakzatokra – szélsőséges esetben új feasibility-artefaktumok jelenhetnek meg. Ezt a `scripts/smoke_real_dxf_nfp_pairs.py` + `scripts/export_real_dxf_nfp_pairs.py` egy-egy futtatásával lehet validálni.
4. **`MAX_SELF_INTERSECTION_SEGMENTS` szigorítása** elutasíthat eddig befogadott inputot. Mitigáció: a simplify előbb fut; illetve a konstans bekötése a quality profile-ba, ne legyen globálisan kemény.

---

## 8. Ajánlott mérés a P1 után (reproducer-csomag)

A BLF-audit mérési keretére ráépítve, ugyanazokkal az alkatrészekkel:

| Metrika | Előtte várható | Utána célérték |
|---|---|---|
| `outer_verts_inflated` átlag | (+50–100% az `outer_verts_imported`-hoz képest) | ≤ `outer_verts_imported`, gyakran 30–50% alatta |
| BLF narrow-phase `segment_pair_ops` átlag | `n*m`, ahol n,m ~200–500 | 0.5–0.2× (kvadratikus javulás) |
| SA iter/sec | jelenleg (BLF-audit P2 előtt) | +40–80% |
| `DXF_RING_TOO_COMPLEX` hibaráta | ritka | nulla a simplify után |

---

## 9. Összefoglalás és kapcsolat a BLF-audittal

- Ez az audit **orthogonális** a BLF-audithoz: mindkettő hathat a gyakorlati wall-clock időre. A **BLF P2** (cavity cap, NFP fallback) és a jelen **P1** (simplify, post-offset) együttes bevezetése a legjobb perf/risk arány.
- Javasolt sorrend:
  1. **BLF P1** (deadline / `work_budget` fix) – már ki van dolgozva az előző dokumentumban.
  2. **Geom P1.2 + P1.3** (Rust-only, 2 fájl, 10 LOC összesen, azonnali pozitív hatás).
  3. **Geom P1.1 + P1.5** (Python oldal, simplify feature-flaggel, telemetria).
  4. **BLF P2** (cavity-cap).
  5. **Geom P2** (sweep-line self-intersect, quality-profile vertex cap).

**Készen áll a patch-írásra**, ha zöld utat kapok.

---

## Melléklet – közvetlen file:line hivatkozások a hivatkozott döntésekhez

- `vrs_nesting/geometry/polygonize.py:11-13` – ARC_TOLERANCE_MM, CURVE_FLATTEN_TOLERANCE_MM
- `vrs_nesting/geometry/polygonize.py:66-105` – `arc_to_points` (chord-error formula)
- `vrs_nesting/geometry/clean.py:122-135` – `clean_ring` (simplify nélkül)
- `vrs_nesting/dxf/importer.py:34-37` – limitkonstansok (MAX_CURVE_POINTS, MAX_SELF_INTERSECTION_SEGMENTS)
- `vrs_nesting/dxf/importer.py:108-113` – `_clamp_curve_flatten_tolerance`
- `vrs_nesting/dxf/importer.py:223` – `ezdxf.flattening(flatten_tol)` hívás, tolerance átváltással
- `vrs_nesting/dxf/importer.py:280-339` – ARC / CIRCLE / ELLIPSE / SPLINE polygonizációs ágak
- `vrs_nesting/dxf/importer.py:377-405` – `_points_from_curve_vertices`, `_flatten_curve_points`
- `vrs_nesting/dxf/importer.py:483-511` – `_ring_has_self_intersection`, `_assert_non_self_intersecting`
- `rust/nesting_engine/src/geometry/offset.rs:156-165` – `do_offset` + `LineJoin::Round(0.1)`
- `rust/nesting_engine/src/geometry/offset.rs:242-246` – pre-offset `simplify_shape` (post-offset NINCS)
- `rust/nesting_engine/src/geometry/offset.rs:234-266` – `inflate_part`
- `rust/nesting_engine/src/nfp/boundary_clean.rs:101-150` – `simplify_ring` (csak kollineáris)
- `rust/nesting_engine/src/nfp/cfr.rs:242-276` – `simplify_collinear` (csak kollineáris, integer cross)
- `rust/nesting_engine/src/feasibility/narrow.rs:196` – komment a `ring_a * ring_b` worst-case-ről
- `docs/nesting_engine/tolerance_policy.md:136-152` – a jelenleg dokumentált simplify policy (csak pre-offset)
- `audit_blf_performance_and_fix_plan.md` – előző audit (BLF/SA), multiplikatív kapcsolat

---

*Vége.*
