# T05e Checklist

- [x] T05d regresszió PASS
  - CGAL build: SUCCESS (v0.2.0)
  - T07 build: SUCCESS
  - smoke lv8_pair_01/02/03: 3/3 PASS
  - lv8_pair_prefill_holes_01 T07: PASS, FP=0, FN=0

- [x] real_work_dxf inventory elkészült
  - scripts/experiments/audit_real_work_dxf_holes.py
  - 12 DXF-et vizsgált
  - JSON: tmp/reports/nfp_cgal_probe/real_work_dxf_hole_inventory.json
  - MD: tmp/reports/nfp_cgal_probe/real_work_dxf_hole_inventory.md

- [x] legalább 5 hole-os DXF azonosítva VAGY hiány dokumentálva
  - HIÁNY DOKUMENTÁLVA: csak 1 hole-os DXF van (Lv8_11612_6db REV3.dxf: 2 holes, 30 verts)
  - 10 DXF outer-only
  - 1 DXF invalid geometry (szóköz a fájlnévben)
  - tmp/ne2_input_lv8jav.json 9 lyukkal rendelkező LV8_11612 NEM a nyers DXF, hanem cavity_prepack rekonstrukció

- [x] legalább 5 real_work hole pair fixture létrejött VAGY hiány dokumentálva
  - HIÁNY DOKUMENTÁLVA: csak 1 hole-os DXF → max 1 holed-complex pair (lv8_pair_01/02) + 1 complex-complex (lv8_pair_03) = 3 pair összesen
  - Ez a maximum a rendelkezésre álló DXF-ekből

- [x] minden fixture real DXF-ből származik
  - real_work_dxf_holes_pair_01: Lv8_11612_6db REV3.dxf + Lv8_07920_50db REV1.dxf
  - real_work_dxf_holes_pair_02: Lv8_11612_6db REV3.dxf + Lv8_07921_50db REV1.dxf
  - real_work_dxf_holes_pair_03: Lv8_07920_50db REV1.dxf + Lv8_07921_50db REV1.dxf

- [x] CGAL probe lefutott minden fixture-re
  - real_work_dxf_holes_pair_01: success, 132 outer verts, 11.18ms, input_holes_a=2, output_holes=0
  - real_work_dxf_holes_pair_02: success, 136 outer verts, 13.17ms, input_holes_a=2, **output_holes=1**
  - real_work_dxf_holes_pair_03: success, 328 outer verts, 70.88ms, input_holes=0, output_holes=0

- [x] T07 correctness lefutott minden success CGAL outputra
  - real_work_dxf_holes_pair_01: T07 PASS, FP=0, FN=0
  - real_work_dxf_holes_pair_02: T07 PASS, FP=0, FN=0, **HOLES_AWARE AKTÍV**
  - real_work_dxf_holes_pair_03: T07 PASS, FP=0, FN=0

- [x] FP/FN riport készült
  - mindhárom fixture: FP=0, FN=0, boundary_penetration_max_mm=0.0

- [x] output_holes állapot dokumentált
  - pair_01: 0 output holes
  - pair_02: **1 output hole (7 vertex)** — ELSŐ eset a T05b-T05e sorozatban!
  - pair_03: 0 output holes

- [x] hole boundary sampling limitáció dokumentált
  - T07 sample_points_on_boundary jelenleg csak outer-t mintavételez
  - pair_02 output_holes=1 (7 vertex) → hole boundary NEM mintavételezve
  - Következő javasolt lépés: T05f hole boundary sampling implementáció

- [x] nincs production integráció
  - scripts/experiments/: csak dev könyvtár
  - Nincs módosítás worker/, Dockerfile, engine v2 production útvonalban
  - CGAL v0.2.0 prototípus

- [x] nincs T08 indítás
  - T08 nem indítva

- [x] nincs silent outer-only fallback
  - CGAL: explicit status=success/error
  - T07: explicit correctness_verdict=PASS/FAIL
  - output_holes=0 explicit a JSON-ban
