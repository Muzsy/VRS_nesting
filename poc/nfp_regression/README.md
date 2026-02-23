# NFP Regression Fixtures

Ez a könyvtár a konvex NFP regressziós fixture-öket tartalmazza.

## Fixture formátum

Minden `.json` fájl mezői:

- `description`: rövid leírás
- `polygon_a`: `[[x, y], ...]` egész koordináták
- `polygon_b`: `[[x, y], ...]` egész koordináták
- `rotation_deg_b`: B alakzat rotációja fokban (F2-1-ben diszkrét, itt referencia 0)
- `expected_nfp`: elvárt NFP kontúr
- `expected_vertex_count`: elvárt csúcsszám

## Megjegyzés

A fixture koordináták integer rácson vannak megadva. Az NFP összehasonlítás
tesztoldalon kanonizált kontúrral történik (CCW + determinisztikus kezdőpont).
