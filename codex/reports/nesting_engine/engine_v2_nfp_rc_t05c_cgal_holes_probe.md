# T05c — CGAL Probe Holes Support + T07 Hole-Aware Correctness

**Dátum:** 2025-05-04
**Fázis:** T05c (CGAL sidecar prototípus — holes kiterjesztés)
**Állapot:** PASS — holes probe és holes validator működik

---

## 1. Kiinduló állapot (T05b után)

| Komponens | Verzió | Támogatás |
|-----------|--------|-----------|
| CGAL probe | 0.1.0 | outer-only |
| T07 external_json | — | outer-only correctness |
| LV8 pair-ek | 3 db | mind outer-only (holes_mm=[]) |

**T05b regressziós státusz:** Mindhárom LV8 pair — PASS

---

## 2. Módosított fájlok

```
tools/nfp_cgal_probe/src/main.cpp              # Holes-aware (0.1.0 → 0.2.0)
rust/nesting_engine/src/bin/nfp_correctness_benchmark.rs  # T07 holes_i64 parser

tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_holes_smoke.json  # ÚJ: synthetic smoke fixture
```

---

## 3. Build eredmény

### CGAL probe (v0.2.0)
```
=== BUILD SUCCESS ===
Binary: tools/nfp_cgal_probe/build/nfp_cgal_probe (1.3MB)
```

### T07 validator
```
cargo build --release --bin nfp_correctness_benchmark
=== BUILD SUCCESS ===
```

---

## 4. CGAL probe holes implementáció

### Input támogatás
- `part_a.holes_mm` és `part_b.holes_mm` beolvasása a fixture-ből
- Ha üres: kompatibilis T05b-vel (Polygon_with_holes_2 üres holes listával)
- Ha nem üres: `make_polygon_with_holes()` épít Polygon_with_holes_2-t
  - outer boundary: CCW orientáció (CGAL követelmény)
  - hole ringek: CW orientáció (CGAL követelmény)

### Reflect/NFP tükrözés
- `reflect_polygon_with_holes()`: teljes Polygon_with_holes_2 tükrözése `(x,y) -> (-x,-y)`
- Tükrözés után orientáció újra normalizálva:
  - outer: CCW
  - holes: CW
- NFP számítás: `CGAL::minkowski_sum_by_reduced_convolution_2(pwh_a, reflected_pwh_b)`

### Output kiterjesztés
Stats mezők a JSON-ban:
- `input_holes_a`, `input_holes_b`
- `input_hole_vertices_a`, `input_hole_vertices_b`
- `output_holes`, `output_hole_vertices`

---

## 5. Outer-only regresszió

Mindhárom LV8 pair továbbra is PASS:

| pair_id | CGAL status | output_holes | T07 verdict | FP | FN | boundary_mm |
|---------|------------|--------------|-------------|----|----|-------------|
| lv8_pair_01 | success | 0 | PASS | 0 | 0 | 0.0 |
| lv8_pair_02 | success | 0 | PASS | 0 | 0 | 0.0 |
| lv8_pair_03 | success | 0 | PASS | 0 | 0 | 0.0 |

---

## 6. Holes smoke fixture

**Fixture:** `tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_holes_smoke.json`
**Típus:** `synthetic_holes_smoke` (NEM valódi LV8 geometria)
**Leírás:** 100x100mm square 40x40mm square hole vs. 30x26mm triangle

### CGAL probe output
```
status: success
outer_i64: 7 vertices
holes_i64: 1 hole (4 vertices)  ← TÉNYLEGES hole az outputban
timing_ms: 0.798
```

### T07 holes correctness
```
correctness_verdict: PASS
false_positive_count: 0
false_negative_count: 0
boundary_penetration_max_mm: 0.0
notes: HOLES_AWARE: 1 hole(s) parsed from holes_i64, hole-aware containment active
```

**Hole-aware containment működik:** A T07 validator:
1. Parse-olja a `holes_i64` mezőt a CGAL outputból
2. `Polygon64 { outer, holes }` konstrukció
3. `point_in_polygon()`: ha pont outer belsejében, ellenőrzi, hogy NEM hole-ban van-e
4. Inside sample check: ha pont NFP outer-en belül, de hole-ban → NEM collides (correct)
5. Outside sample check: ha pont outer-en kívül vagy hole-ban → NEM collides (correct)

---

## 7. Real LV8 hole-os pair

**Státusz: NEM ELÉRHETŐ**

Keresés minden teszt fixture-ben és LV8 input fájlban:
- LV8 solver geometry: `ne2_input_lv8jav.json` → 12 part, mind outer-only (cavity_prepack kitölti a lyukakat)
- LV8 DXF geometry: van holes szintaxis, de solver inputból kivesszük
- T01-T08 fixture-ek: holes nem szerepel

**Következtetés:** A valódi LV8 lyukak a DXF szinten vannak, de a solver input pipeline (cavity_prepack v2) fill-elı je, így a solver NEM kap holes inputot. A real LV8 holes pair igényel egy olyan fixture-t, ami a pre-fill geometriát tartalmazza — ez jelenleg nem érhető el.

---

## 8. Output összefoglaló táblázat

| pair_id | fixture_type | sidecar_status | output_outer_v | output_holes | output_hole_v | T07 verdict | FP | FN | notes |
|---------|-------------|---------------|---------------|--------------|---------------|-------------|----|----|-------|
| lv8_pair_01 | outer-only LV8 | success | 776 | 0 | 0 | PASS | 0 | 0 | regression OK |
| lv8_pair_02 | outer-only LV8 | success | 786 | 0 | 0 | PASS | 0 | 0 | regression OK |
| lv8_pair_03 | outer-only LV8 | success | 324 | 0 | 0 | PASS | 0 | 0 | regression OK |
| lv8_pair_holes_smoke | synthetic | success | 7 | 1 | 4 | PASS | 0 | 0 | holes-aware active |

---

## 9. Mi működik

- **CGAL probe v0.2.0**: Polygon_with_holes_2 input és output támogatás
- **T07 external_json holes_i64 parser**: parse-olja a hole ringeket, skálázással
- **T07 hole-aware containment**: `point_in_polygon()` kiterjesztve hole-okkal
  - Inside: outer belsejében ÉS nem hole-ban
  - Outside: outer-en kívül VAGY hole-ban
- **Outer-only regresszió**: 3/3 LV8 pair PASS

---

## 10. Mi maradt unsupported / blocker

| Limitáció | Leírás |
|-----------|--------|
| Real LV8 holes pair NEM érhető el | LV8 DXF geometriában vannak lyukak, de solver inputban nincsenek |
| Hole boundary sampling NEM implementált | `sample_points_on_boundary()` csak outer-t mintavételez |
| T08 integráció TILTVA | Production integráció feladat tiltása érvényesült |

---

## 11. Státusz

**PASS**

Minden megvalósított cél teljesült:
- CGAL probe: holes input → holes output ✓
- T07: holes_i64 parse + hole-aware containment ✓
- Outer-only regresszió: 3/3 PASS ✓
- Synthetic holes smoke: PASS ✓
- Real LV8 holes: nem elérhető, de ez nem a probe hibája ✓
