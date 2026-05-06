# T05f Checklist — Hole Boundary Sampling Implementation

- [x] real_work_dxf_holes_pair_02 CGAL output_holes >= 1
- [x] T07 parse-olja a holes_i64 outputot
- [x] sample_points_on_boundary vagy megfelelő boundary sampling logika hole ringekre is mintáz
- [x] output JSON tartalmaz outer_boundary_samples mezőt
- [x] output JSON tartalmaz hole_boundary_samples mezőt
- [x] hole_boundary_samples > 0 real_work_dxf_holes_pair_02 esetén
- [x] outer-only regresszió továbbra is PASS
- [x] FP/FN riport nem romlott
- [x] ismert boundary/contact limitáció dokumentált
- [x] nincs production integráció
- [x] nincs T08 indítás

## Teljesítés dátuma: 2026-05-05

## Regression summary

| Fixture | Verdict | FP | FN | outer_boundary_samples | hole_boundary_samples | boundary_holes_supported |
|---------|---------|----|----|----------------------|---------------------|------------------------|
| real_work_dxf_holes_pair_02 | PASS | 0 | 0 | 398 | 2 | true |
| lv8_pair_01 | PASS | 0 | 0 | 200 | 0 | false |
| lv8_pair_holes_smoke | PASS | 0 | 0 | 197 | 3 | true |
