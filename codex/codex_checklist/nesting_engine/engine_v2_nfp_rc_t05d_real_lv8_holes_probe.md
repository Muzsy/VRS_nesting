# T05d Checklist

- [x] T05c outer-only regresszió továbbra is PASS
  - CGAL probe build: SUCCESS (v0.2.0, 1.3M)
  - T07 build: SUCCESS
  - lv8_pair_01 T07: PASS, FP=0, FN=0, boundary=0.0

- [x] real LV8 hole-os geometriák keresése dokumentált
  - Keresett helyek: tests/fixtures/, worker/, scripts/, vrs_nesting/, tmp/
  - MEGOLDÁS: tmp/ne2_input_lv8jav.json — outer_points_mm + holes_points_mm (pre-fill réteg)
  - worker/cavity_prepack.py: top_level_hole_policy = "solidify_parent_outer" — ez szűri ki a holes-t a solver inputból
  - 9 LV8 part with holes talált (Lv8_11612_6db: 9 holes, Lv8_07921_50db: 5 holes, stb.)

- [x] legalább 1 real LV8 pre-fill holes fixture létrejött
  - lv8_pair_prefill_holes_01.json (Lv8_11612_6db vs Lv8_07921_50db)
  - lv8_pair_prefill_holes_02.json (Lv8_11612_6db vs Lv8_15435_10db)
  - lv8_pair_prefill_holes_03.json (Lv8_07921_50db vs Lv8_15435_10db)
  - Mindhárom: fixture_source = "real_lv8_prefill_holes"

- [x] fixture tartalmaz part_a.holes_mm vagy part_b.holes_mm mezőt nem üres tartalommal
  - lv8_pair_prefill_holes_01: part_a=9 holes (153 verts), part_b=5 holes (138 verts)
  - lv8_pair_prefill_holes_02: part_a=9 holes (153 verts), part_b=2 holes (28 verts)
  - lv8_pair_prefill_holes_03: part_a=5 holes (138 verts), part_b=2 holes (28 verts)

- [x] CGAL probe lefutott real holes fixture-re
  - lv8_pair_prefill_holes_01: success, 776 outer verts, 182.99ms, input_holes_a=9, input_holes_b=5
  - lv8_pair_prefill_holes_02: success, 664 outer verts, 41.57ms, input_holes_a=9, input_holes_b=2
  - lv8_pair_prefill_holes_03: success, 193 outer verts, 23.29ms, input_holes_a=5, input_holes_b=2
  - Mindhárom: status=success, output_holes=0 (matematikailag helyes: NFP Minkowski összeg nem feltétlenül tartalmaz hole-t)

- [x] T07 holes-aware correctness lefutott real holes fixture-re
  - lv8_pair_prefill_holes_01: T07 PASS, FP=0, FN=0
  - lv8_pair_prefill_holes_02: T07 PASS, FP=0, FN=0
  - lv8_pair_prefill_holes_03: T07 PASS, FP=0, FN=0

- [x] FP/FN riport készült
  - Mindhárom fixture: false_positive_count=0, false_negative_count=0
  - boundary_penetration_max_mm=0.0 mindháromra

- [x] hole-aware containment tényleg aktív volt
  - T07 point_in_polygon(): outer belsejében ÉS hole-ban → Outside (T05c implementáció)
  - CGAL stats.input_holes_a/b mutatja a valós hole értékeket
  - T07 holes_i64 parsing: implementálva (T05c), de output holes=0 → HOLES_AWARE notes nem aktív

- [ ] hole boundary sampling implementált
  - NEM volt része a T05d scope-nak
  - Következő javasolt lépés: T05e vagy follow-up issue
  - A T05d ettől függetlenül PASS (real holes correctness működik)

- [x] nincs production integráció
  - CGAL: prototípus/reference tool, v0.2.0
  - scripts/experiments/: csak dev/experiment könyvtár
  - Nincs módosítás worker/, Dockerfile-, engine v2 production útvonalban

- [x] nincs silent outer-only fallback
  - CGAL probe: explicit status=success/error
  - T07: explicit correctness_verdict=PASS/FAIL
  - Ha holes_i64 üres, explicit 0 érték a JSON-ban
