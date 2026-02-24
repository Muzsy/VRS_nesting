# NFP Regression Fixtures

Ez a könyvtár konvex (F2-1) es konkav (F2-2) NFP regresszios fixture-okat tartalmaz.

## Fixture formátum

Minden `.json` fájl alap mezo-i:

- `description`: rövid leírás
- `fixture_type`: `convex` vagy `concave`
- `polygon_a`: `[[x, y], ...]` egész koordináták
- `polygon_b`: `[[x, y], ...]` egész koordináták
- `rotation_deg_b`: B alakzat rotációja fokban (jelen regresszioban 0)
- `expected_nfp`: elvárt NFP kontúr
- `expected_vertex_count`: elvárt csúcsszám

Opcionális mezo:

- `expect_exact_fallback`: `true` eseten az orbitalis exact mod fallbackje is validalt.

## Konkav fixture-ek (F2-2)

Konkav fixture-eknel az elvart eredmeny a stabil alaputvonalra vonatkozik:

1. konkav -> konvex dekompozicio
2. resz-NFP-k (konvex Minkowski)
3. union
4. boundary clean (CCW + lexikografikus start, onmetszesmentes)

Az osszehasonlitas tesztoldalon canonical ring alapjan tortenik.

## Megjegyzés

A fixture koordináták integer rácson vannak megadva. Az NFP összehasonlítás
tesztoldalon kanonizált kontúrral történik (CCW + determinisztikus kezdőpont).
