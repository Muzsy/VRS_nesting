# dxf_demo fixtures

Valodi DXF regressziofixture-k a DXF import es real_dxf pipeline smoke-okhoz.

## Fajlok
- `stock_rect_1000x2000.dxf`
  - Layer: `CUT_OUTER`
  - Zart LWPOLYLINE teglalap (1000 x 2000 mm)
- `part_arc_spline_chaining_ok.dxf`
  - `CUT_OUTER`: LINE + ARC + LINE + LINE szegmensek (nem egy zart polyline, chaining kell)
  - `CUT_INNER`: SPLINE hole
  - Elvart: import PASS, hole detektalas, source_entities-ben `ARC` es `SPLINE`
- `part_chain_open_fail.dxf`
  - `CUT_OUTER`: hianyos chaining (zaro szegmens hianyzik)
  - Elvart: `DXF_OPEN_OUTER_PATH`

## Hasznalat
- Gyors import regresszio smoke:
  - `python3 scripts/smoke_real_dxf_fixtures.py`
- End-to-end real DXF + Sparrow smoke:
  - `python3 scripts/smoke_real_dxf_sparrow_pipeline.py`

## Fuggoseg
A valodi `.dxf` importhoz az `ezdxf` Python csomag szukseges.
Ha hianyzik, az uj smoke script ertelmes hiba-uzenetet ad telepitesi tippel.
