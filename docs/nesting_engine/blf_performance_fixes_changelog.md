# BLF Performance Fixes — Changelog és Referencia

> Hatókör: `rust/nesting_engine/src/placement/blf.rs`, `src/search/sa.rs`,
> `src/geometry/offset.rs`, `vrs_nesting/geometry/clean.py`,
> `vrs_nesting/geometry/polygonize.py`, `vrs_nesting/dxf/importer.py`
>
> Készült: 2026-04-18
> Állapot: A-blokk + C1 commitolva, B1+B3 implementálva

---

## 1. Összefoglaló

Az `audit_blf_performance_and_fix_plan.md` alapján végrehajtott javítások
három ütemben:

| Blokk | Leírás | Commit | Állapot |
|-------|--------|--------|---------|
| A1 | Offset post-simplify | fcfad11 | ✔ Kész |
| A2 | SA safety margin | fcfad11 | ✔ Kész |
| A3 | Self-intersection limit csökkentés | fcfad11 | ✔ Kész |
| A4 | BLF telemetria mezők | user commit | ✔ Kész |
| C1 | RDP polygon simplification | 1491e52 | ✔ Kész |
| B1 | Per-instance candidate cap | — | ✔ Implementálva |
| B3 | Cavity bbox-fit skip + anchor cap | — | ✔ Implementálva |

---

## 2. A-blokk: Alacsony kockázatú infrastruktúra

### A1 — Offset post-simplify (`offset.rs`)

**Fájl:** `rust/nesting_engine/src/geometry/offset.rs`

**Probléma:** Az `i_overlay` offset művelet felesleges köztes vertex-eket
hagyhat a kontúron (mikroszegmensek, kollineáris élek), ami a downstream
BLF narrow-phase `ring_intersects_ring_or_touch` O(n·m) szegmenspár-
ellenőrzését drágítja.

**Megoldás:**
- Post-offset `SimplifyShape::simplify_shape(FillRule::NonZero)` hívás.
- `LineJoin::Round` tolerance spacing-arányos:
  `clamp(|delta| * 0.1, 0.2, 1.0)`.

**Hatás:** Csökkenti az inflated polygon vertex-számot, ami minden
downstream feasibility-check-et gyorsít.

### A2 — SA safety margin (`sa.rs`)

**Fájl:** `rust/nesting_engine/src/search/sa.rs`

**Probléma:** Az SA `clamp_sa_iters_by_time_limit_and_eval_budget` képlete
lehetővé tette, hogy `sa_eval_budget_sec × max_iters` pontosan kitöltse
a `time_limit_sec`-et, nem hagyva tartalékot az output-szerializálásra.

**Megoldás:**
- `sa_safety_margin_frac()` helper:
  `NESTING_ENGINE_SA_SAFETY_MARGIN_FRAC` env var (default: 0.0).
- A clamp képlet módosítása:
  ```
  reserve_sec = (time_limit_sec * safety_margin).ceil()
  usable_time_sec = time_limit_sec - reserve_sec
  max_evals = usable_time_sec / eval_budget_sec
  ```

**Env var:** `NESTING_ENGINE_SA_SAFETY_MARGIN_FRAC`
- Tartomány: `[0.0, 0.5)` (érvényes finite float)
- Default: `0.0` (nincs tartalék — backward-kompatibilis)
- Ajánlott: `0.05` (5% tartalék)

### A3 — Self-intersection segment limit (`importer.py`)

**Fájl:** `vrs_nesting/dxf/importer.py`

**Probléma:** A `MAX_SELF_INTERSECTION_SEGMENTS = 5000` túl magas volt,
a self-intersection-check O(n²) idejű.

**Megoldás:** `MAX_SELF_INTERSECTION_SEGMENTS = 2000`.

### A4 — BLF telemetria mezők (`blf.rs`)

**Fájl:** `rust/nesting_engine/src/placement/blf.rs`

**Leírás:** 3 új `u64` mező a `BlfProfileV1` struct-ban, előkészítve a
B1/B3 telemetria bekötéséhez:

```rust
pub instance_cap_hits: u64,
pub cavity_anchor_cap_applied: u64,
pub cavity_hole_bbox_fit_skipped: u64,
```

Ezek a `NESTING_ENGINE_BLF_PROFILE=1` env var mellett a stderr JSON-ban
jelennek meg (`BLF_PROFILE_V1 {...}`).

---

## 3. C1-blokk: RDP polygon-egyszerűsítés (Python)

### C1 — Ramer-Douglas-Peucker polygon simplification

**Fájlok:**
- `vrs_nesting/geometry/clean.py` — core implementáció
- `vrs_nesting/geometry/polygonize.py` — bekötés a polygonize pipeline-ba
- `vrs_nesting/dxf/importer.py` — bekötés a DXF import pipeline-ba
- `tests/test_geometry_clean.py` — 13 új teszt

**Probléma:** A DXF-ből importált körív- és ellipszis-diszkretizációk
sok vertex-et hoznak (61–78 / kontúr), ami a downstream solver
narrow-phase-ét drágítja.

**Megoldás:**
- Iteratív (stack-alapú) RDP implementáció zárt ring-ekre.
- Farthest-vertex anchor split: a zárt ring legtávolabbi pontját
  kereső heurisztika biztosítja, hogy a simplification ne „nyitott
  polyline"-ként kezelje a kontúrt.
- Degenerate fallback: ha az RDP < 3 pontra csökkentene, az eredeti
  ring marad.
- Env-gated opt-in minta: a tolerancia env var-ból jön.

**Env var:** `NESTING_ENGINE_RDP_SIMPLIFY_TOL_MM`
- Tartomány: `(0.0, 1.0]` (érvényes pozitív float, max 1.0 mm)
- Default: nincs beállítva → RDP kikapcsolva
- Ajánlott: `0.2` (200 µm tolerancia — elegendő CNC pontossághoz)
- Hatás: kör 61→~20 vertex, ív 78→~25 vertex (~60-70% csökkenés)

**Integráció:**
- `clean_ring()` kap egy `simplify_tol_mm` opcionális paramétert.
- `polygonize_part_raw()` és `polygonize_stock_raw()` olvasnak env-ből.
- `_chain_segments_to_rings()` és `_collect_layer_rings()` az
  importer-ben szintén env-ből olvasnak.
- Az RDP a `clean_ring` utolsó lépéseként fut, a CCW/CW enforcement és
  a min-edge-length szűrés után.

**Determinizmus:** Biztosított. Az RDP iteratív implementáció fix
bejárási sorrenddel dolgozik. A `simplify_ring_rdp` kimenete
determinisztikus ugyanarra a bemenetre.

---

## 4. B-blokk: BLF cap-ek

### B1 — Per-instance candidate cap

**Fájl:** `rust/nesting_engine/src/placement/blf.rs`

**Probléma:** Audit 2.2 — a BLF rács-söprés korlátlan mennyiségű jelöltet
próbálgat egyetlen instance-re, akár >156 000-et siker nélkül.

**Megoldás:** Env-gated per-instance candidate limit, ami a cavity ÉS grid
fázisban egyaránt számol. Az instance-szintű számláló minden új instance
elején nullázódik. Cap elérésekor:
- Az instance `INSTANCE_CANDIDATE_CAP` unplaced reason-t kap.
- A következő instance-re ugrik (nem áll le teljesen).

**Env var:** `NESTING_ENGINE_BLF_INSTANCE_CANDIDATE_CAP`
- Típus: `u64`
- Default: `0` (korlátlan — backward-kompatibilis)
- Ajánlott: `10000` SA search-höz (quality-loss nélküli sweet spot az
  500-partos benchmark-on)

**Interakció a StopPolicy-val:** A `stop.consume(1)` ellenőrzés
megmarad a cap-ellenőrzés ELŐTT. A StopPolicy (wall-clock/work-budget)
elsőbbséget élvez.

**Telemetria:** `BlfProfileV1.instance_cap_hits` — hány instance-t
vágott le a cap.

**Unplaced reason:** `INSTANCE_CANDIDATE_CAP`

### B3a — Cavity hole bbox-fit skip

**Fájl:** `rust/nesting_engine/src/placement/blf.rs` —
`collect_cavity_candidates()`

**Probléma:** Audit 2.4 — a cavity anchor generátor minden lyukra
generál `3 + 1 + 24 + 24 × vertexCount` anchor pontot, akkor is, ha
a lyuk nyilvánvalóan kisebb, mint az elhelyezendő alkatrész.

**Megoldás:** Mielőtt a lyukra anchor pontokat generálnánk, összehasonlítjuk
a lyuk AABB méreteit az alkatrész rotált AABB méreteivel:
```
hole_w < part_w || hole_h < part_h → skip
```

**Mindig aktív** — nincs env var (pure optimization, nem változtat
eredményt, csak felesleges munkát spórol meg).

**Telemetria:** `BlfProfileV1.cavity_hole_bbox_fit_skipped`

### B3b — Cavity anchor cap

**Fájl:** `rust/nesting_engine/src/placement/blf.rs` —
`collect_cavity_candidates()`

**Probléma:** Nagy vertex-számú lyukak (61+ vertex) robbanásszerű
anchor-mennyiséget generálhatnak (>1400/lyuk/rotáció).

**Megoldás:** A `collect_cavity_candidates` visszaadott listájának
mérete env-vel korlátozható. A cap elérése után `break 'outer`
— determinisztikus sorrendben a legígéretesebb (lower-left, center,
first-vertex) anchor-ok maradnak.

**Env var:** `NESTING_ENGINE_BLF_CAVITY_ANCHOR_CAP`
- Típus: `u64`
- Default: `0` (korlátlan — backward-kompatibilis)
- Ajánlott: `200`–`500` (a lower-left + center anchor-ok mindig
  benne maradnak)

**Telemetria:** `BlfProfileV1.cavity_anchor_cap_applied`

---

## 5. Env var összefoglaló

| Env var | Modul | Default | Mire hat |
|---------|-------|---------|----------|
| `NESTING_ENGINE_BLF_PROFILE` | blf.rs | ki (`!= "1"`) | BLF telemetria stderr JSON kimenet |
| `NESTING_ENGINE_BLF_INSTANCE_CANDIDATE_CAP` | blf.rs | `0` (∞) | Per-instance max jelöltek (B1) |
| `NESTING_ENGINE_BLF_CAVITY_ANCHOR_CAP` | blf.rs | `0` (∞) | Max cavity anchor-ok per rotáció (B3b) |
| `NESTING_ENGINE_SA_SAFETY_MARGIN_FRAC` | sa.rs | `0.0` | SA idő-tartalék frakció (A2) |
| `NESTING_ENGINE_RDP_SIMPLIFY_TOL_MM` | clean.py | nincs | RDP tolerancia mm-ben (C1) |

---

## 6. Benchmark eredmények

### 6.1 B3 bbox-fit skip hatása

| Fixture | bbox_fit_skipped | Megjegyzés |
|---------|-----------------|------------|
| sample_input (10 db, lyukas) | 2 | 2 kicsi lyuk kihagyva |
| part-in-part offgrid | 0 | lyuk elég nagy |
| 500 noholes | 0 | nincs lyuk → nem releváns |

### 6.2 B1 instance cap hatása (SA, 500 parts, 30s)

| Cap | Placed | Util% | Candidates | Cap hits |
|-----|--------|-------|------------|----------|
| ∞ (baseline) | 10 | 53.3 | 729,870 | 0 |
| 10,000 | 10 | 53.3 | 719,454 | 16 |
| 50,000 | 10 | 53.3 | 729,870 | 0 |
| 3,000 | 3 | 18.3 | 769,680 | 250 |

**Megállapítás:** cap=10000 az optimális pont — azonos minőség,
kevesebb felesleges work, 16 hopeless instance gyorsan kihagyva.

### 6.3 BLF bottleneck profil (200 parts, 15s greedy)

| Metrika | Érték | Arány |
|---------|-------|-------|
| `wall_ms_in_can_place` | 12,744 ms | **84.9%** |
| `wall_ms_in_translate_polygon` | 434 ms | 2.9% |
| `wall_ms_in_grid_sweep` (egyéb) | 1,822 ms | 12.1% |

A `can_place` narrow-phase marad a domináns bottleneck → ez a
P2 blokk (D1–D7: edge-AABB prefilter, placed edge R-tree) területe.

---

## 7. Tesztek

### Rust tesztek (B1+B3)

| Teszt | Leírás |
|-------|--------|
| `collect_cavity_candidates_skips_small_holes_via_bbox_fit` | B3: kis lyuk skip |
| `collect_cavity_candidates_no_skip_when_hole_is_large_enough` | B3: nagy lyuk nem skip |
| `collect_cavity_candidates_respects_anchor_cap` | B3: anchor cap betartása |
| `blf_instance_candidate_cap_limits_placement_attempts` | B1: instance cap működése |

Teljes tesztsor: 131 teszt zöld (single-threaded, `--test-threads=1`).

### Python tesztek (C1)

13 új teszt a `tests/test_geometry_clean.py`-ban:
- RDP collinear collapse, idempotency, signed area preservation
- Degenerate fallback, zero-tol noop
- `clean_ring` with/without `simplify_tol`
- `rdp_tol_mm_from_env` validation (positive, non-finite, max, garbage, unset)

---

## 8. Hátralevő javítások

| Blokk | Leírás | Prioritás | Állapot |
|-------|--------|-----------|---------|
| B2 | `translate_polygon` AABB prefilter | P1 | Nyitott |
| B4–B5 | Worker retry-gátló + trial poll-timeout | P1 | Nyitott |
| D1 | Ring-AABB prefilter narrow-phase elé | P2 | Nyitott |
| D2 | Edge-AABB prefilter ring_intersects_ring elé | P2 | Nyitott |
| D3 | Placed edge R-tree | P2 | Nyitott |
| D4–D7 | Sweep-line, NFP/BLF hybrid, stb. | P2–P3 | Nyitott |
| E1–E3 | Per-part placer selection, hole-aware NFP | P3 | Nyitott |
