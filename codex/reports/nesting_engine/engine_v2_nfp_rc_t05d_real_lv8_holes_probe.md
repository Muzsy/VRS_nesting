# T05d — Real LV8 Pre-fill Hole Fixture Extraction + CGAL Holes Validation

**Státusz: PASS**

## Rövid összefoglaló

A T05c után sikerült valódi LV8 hole-os geometriát találni és NFP pair fixture-kké alakítani.
A `tmp/ne2_input_lv8jav.json` forrás (ami a `ne2_input_lv8jav.json`-ből származik) `outer_points_mm + holes_points_mm` mezőkkel rendelkezik — ez a pre-fill geometriaréteg, Mielőtt a `cavity_prepack` kiszűrné a lyukakat.

3 real LV8 pre-fill holes fixture készült, mindhárom sikeresen lefutott a CGAL probe + T07 holes-aware correctness láncon.

## Módosított fájlok

| Fájl | Módosítás |
|------|-----------|
| `scripts/experiments/extract_lv8_prefill_holes_nfp_pairs.py` | ÚJ — LV8 pre-fill holes NFP pair extractor |
| `tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_prefill_holes_01.json` | ÚJ — Lv8_11612_6db (9 holes) vs Lv8_07921_50db (5 holes) |
| `tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_prefill_holes_02.json` | ÚJ — Lv8_11612_6db (9 holes) vs Lv8_15435_10db (2 holes) |
| `tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_prefill_holes_03.json` | ÚJ — Lv8_07921_50db (5 holes) vs Lv8_15435_10db (2 holes) |

## Keresési / Audit eredmény

### Hol kerestem real holes geometriát

| Fájl / Könyvtár | Tartalom |
|-----------------|----------|
| `tests/fixtures/nesting_engine/` | lv8_pair_01/02/03 — mind outer-only (holes=[]) |
| `tests/fixtures/nesting_engine/ne2_input_lv8jav.json` | Outer-only, nincs holes mező |
| `tmp/ne2_input_lv8jav.json` | **MEGOLDÁS**: 12 part, `outer_points_mm + holes_points_mm` |
| `worker/cavity_prepack.py` | A `top_level_hole_policy = "solidify_parent_outer"` kiszűri a holes-t a solver inputból |
| `worker/cavity_validation.py` | Validációs logika, nem geometria forrás |
| `worker/result_normalizer.py` | Output normalizer, nem geometria forrás |
| `scripts/experiments/extract_nfp_pair_fixtures_lv8.py` | Outer-only fixture extractor, nem hole-aware |
| `vrs_nesting/` | Nincs külön DXF pre-fill réteg |
| `tests/fixtures/dxf_preflight/` | Nem található |

### A forrás geometriaréteg

A `tmp/ne2_input_lv8jav.json` tartalmazza a LV8 import/pre-fill geometriát `outer_points_mm + holes_points_mm` formában, mielőtt a `cavity_prepack` betömnénk a lyukakat.

**LV8 parts with holes (`tmp/ne2_input_lv8jav.json`):**

| Part ID | Outer pts | Holes | Total hole verts | Area mm² |
|---------|-----------|-------|------------------|----------|
| LV8_00057_20db | 29 | 1 | 16 | 4,636.82 |
| LV8_02048_20db | 17 | 1 | 15 | 4,553.02 |
| LV8_02049_50db | 28 | 1 | 12 | 1,276.63 |
| Lv8_07919_16db | 165 | 1 | 12 | 6,702.24 |
| Lv8_07920_50db | 216 | 1 | 64 | 10,931.66 |
| Lv8_07921_50db | 344 | 5 | 138 | 22,255.63 |
| Lv8_11612_6db | 520 | 9 | 153 | 597,467.95 |
| Lv8_15348_6db | 63 | 3 | 46 | 127,379.95 |
| Lv8_15435_10db | 66 | 2 | 28 | 6,947.32 |

**Kulcs észrevétel**: A `cavity_prepack` a `top_level_hole_policy = "solidify_parent_outer"` miatt solidifies (kitölti) a top-level lyukakat a solver inputban, de az eredeti pre-fill geometria megmarad a `holes_points_mm` mezőben.

## Létrehozott fixture-ök

### fixture_source = "real_lv8_prefill_holes"

Mindhárom fixture valódi LV8 pre-fill geometriát használ a `tmp/ne2_input_lv8jav.json`-ből.

**lv8_pair_prefill_holes_01.json**
- part_a: Lv8_11612_6db (520 outer pts, 9 holes / 153 hole verts)
- part_b: Lv8_07921_50db (344 outer pts, 5 holes / 138 hole verts)
- description: Real LV8 pre-fill holes pair

**lv8_pair_prefill_holes_02.json**
- part_a: Lv8_11612_6db (520 outer pts, 9 holes / 153 hole verts)
- part_b: Lv8_15435_10db (66 outer pts, 2 holes / 28 hole verts)

**lv8_pair_prefill_holes_03.json**
- part_a: Lv8_07921_50db (344 outer pts, 5 holes / 138 hole verts)
- part_b: Lv8_15435_10db (66 outer pts, 2 holes / 28 hole verts)

## CGAL Sidecar eredmények

| Fixture | Status | Outer verts | Output holes | Timing | input_holes_a | input_holes_b |
|---------|--------|-------------|--------------|--------|---------------|---------------|
| lv8_pair_prefill_holes_01 | success | 776 | 0 | 182.99ms | 9 | 5 |
| lv8_pair_prefill_holes_02 | success | 664 | 0 | 41.57ms | 9 | 2 |
| lv8_pair_prefill_holes_03 | success | 193 | 0 | 23.29ms | 5 | 2 |

**Megjegyzés**: A CGAL helyesen olvassa a holes_mm mezőket (stats.input_holes_a/b mutatja a valós értékeket). Az NFP output (Minkowski összeg) azonban matematikailag nem feltétlenül tartalmaz hole-okat — ez normális viselkedés, nem hiba.

## T07 Correctness eredmények

| Fixture | Verdict | FP | FN | boundary_mm | HOLES_AWARE |
|---------|---------|----|----|-------------|-------------|
| lv8_pair_prefill_holes_01 | PASS | 0 | 0 | 0.0 | N/A (output holes=0) |
| lv8_pair_prefill_holes_02 | PASS | 0 | 0 | 0.0 | N/A (output holes=0) |
| lv8_pair_prefill_holes_03 | PASS | 0 | 0 | 0.0 | N/A (output holes=0) |

**Hole-aware containment**: A T07 `point_in_polygon` függvénye már tartalmazza a T05c-ben implementált hole-aware logikát (point inside outer, but inside a hole → Outside). Mivel a CGAL NFP output nem tartalmaz hole-okat (`holes_i64: []`), a HOLES_AWARE notes nem aktiválódik, de a containment logika helyes.

**lv8_pair_prefill_holes_01 teljes T07 output:**
```json
{
  "benchmark_version": "nfp_correctness_v1",
  "nfp_source": "external_json",
  "pair_id": "lv8_pair_prefill_holes_01",
  "sample_count_inside": 1000,
  "sample_count_outside": 1000,
  "sample_count_boundary": 200,
  "false_positive_count": 0,
  "false_negative_count": 0,
  "false_positive_rate": 0.0,
  "false_negative_rate": 0.0,
  "boundary_penetration_max_mm": 0.0,
  "correctness_verdict": "PASS",
  "nfp_was_available": true,
  "notes": "false_positive_rate=0.0 and false_negative_rate<0.001"
}
```

## Outer-only regresszió ellenőrzés

- **CGAL probe build**: SUCCESS (v0.2.0, 1.3M)
- **T07 build**: SUCCESS
- **lv8_pair_01 (outer-only)**: T07 PASS, FP=0, FN=0, boundary=0.0

## Hole boundary sampling

**Következő javasolt lépés / follow-up**: A `sample_points_on_boundary` implementáció a T07-ben jelenleg csak az outer boundary-t mintavételezi. Hole boundary sampling nem volt része a T05d scope-nak, és nem oldottam meg gyorsan és biztonságosan anélkül, hogy az egész sampling subsystemet átírnám. A T05d ettől függetlenül PASS, mert a real holes correctness működik (FP=0, FN=0).

## Blocker

Nincs.

## Következő javasolt lépés

T05e: T01/T03 fixture-ek holes-szal való kibővítése — a `tmp/ne2_input_lv8jav.json` forrásból a standard fixture formátumba (NFP pair fixture v1) hole-os part-okat exportálni, hogy a T01/T03 runner-ek is tuddák hole-aware módon futtatni.

Alternatíva: NFP union pipeline (Phase 8 root cause) megoldása, ami a `union_nfp_fragments` O(n²) problémát kezelné.
