# Geometry Preparation Contract v1

Task context: Engine v2 NFP RC T02.
Scope: exact / canonical / solver geometry reteg-hatarok egyertelmu definialasa a T03-T10 feladatokhoz.

## 1. Exact geometry

Definicio:
- Az exact geometry az eredeti gyartasi geometriat reprezentalja, ahogy az input pipeline-ba erkezik, es amelyhez a vegso gyartasi ervenyesseg kotodik.

Kodkapcsolat:
- `PartGeometry` a part geometriat `Polygon64`-ben tarolja (`rust/nesting_engine/src/geometry/types.rs`).
- A `run_inflate_pipeline` a requestbol determinisztikusan epit nominal geometriat (`rust/nesting_engine/src/geometry/pipeline.rs`).

Szabalyok:
- Exact geometry nem cserelheto solver-gyorsito reprezentaciora gyartasi donteseknel.
- A vegso validacios dontes exact geometry alapjan tortenik.

## 2. Canonical clean geometry

Definicio:
- A canonical clean geometry topologiailag egyszerusitett, determinisztikus, de meg ervenyes sokszog-hatarvonal.

Kodkapcsolat:
- `clean_polygon_boundary` eltavolitja a zaro duplikatumot, egymas melletti duplikalt pontokat, zero-length eleket, kollinearis koztes pontokat, majd CCW iranyra es lexikografikus kezdo pontra normalizal (`rust/nesting_engine/src/nfp/boundary_clean.rs`).
- Onmetszes eseten `NfpError::NotSimpleOutput` hibaval ter vissza.

Szabalyok:
- Canonical clean csak olyan tisztitast vegezhet, ami nem teszi onmetszove/ervenytelenne a poligont.
- A canonical clean celja a determinisztikus NFP-bemenet stabilizalasa.

## 3. Solver/NFP geometry

Definicio:
- A solver geometry az NFP/szamitasi retegek bemeneti formatuma, nem gyartasi igazsagforras.

Kodkapcsolat:
- Az NFP retegek `Polygon64`/`Point64` integer geometriaval dolgoznak (`rust/nesting_engine/src/geometry/types.rs`, `rust/nesting_engine/src/nfp/mod.rs`).
- `NfpError` explicit hibamodelt ad (`EmptyPolygon`, `NotConvex`, `NotSimpleOutput`, orbit/decomposition hibak).

Kritikus szabaly:
- Solver geometry != gyártási geometry. A solver geometrybol szarmazo elfogadas csak koztes eredmeny; vegso check exact geometriaval kotelezo.

## 4. Integer robust layer

Definicio:
- Az integer robust layer implementacioja a `Point64 { x: i64, y: i64 }` tipusrendszer.

Tenyleges kodbeli allitasok:
- `SCALE = 1_000_000` (`rust/nesting_engine/src/geometry/scale.rs`), azaz 1 mm = 1_000_000 belso egyseg.
- `mm_to_i64` kerekitett atvaltast vegez, `i64_to_mm` visszaalakitas determinisztikus.
- Orientacios/terulet jellegu muveletek i128 arithmetic-kal vedik az overflowt (`cross_product_i128`, `signed_area2_i128` a `types.rs`-ben).

Kovetkezmeny:
- A robust geometriai donteseket integer tartomanyban kell meghozni, nem floating-point becslessel.

## 5. GEOM_EPS_MM toleranciak

Tenyleges ertek:
- `GEOM_EPS_MM = 1e-9` (`rust/nesting_engine/src/geometry/float_policy.rs`).
- `AREA_EPS_MM2 = 1e-12` (`rust/nesting_engine/src/geometry/float_policy.rs`).

Hasznalat:
- `is_near_zero`, `eq_eps`, `cmp_eps` fuggvenyekben epsilon-kezelt float osszehasonlitasra.
- `cmp_eps` NaN eseten determinisztikus `total_cmp` rendezest alkalmaz.

Korlatozas:
- GEOM_EPS_MM float-domain tolerancia; integer robust dontesnel a `Point64` skalazott egesz modell az iranyado.

## 6. Simplification safety szabalyok

Minimum safety-elv:
- Tilos olyan simplify/cleanup lepest bevezetni, amely topologiai hibat (pl. onmetszes) okoz.
- Tilos ugy modositas, amely kovetkezmenyekent az NFP output `NotSimpleOutput`-ra fut, mikozben az input korabban tiszta volt.
- `ring_has_self_intersection` es `clean_polygon_boundary` ellenorzes kotelezo vedovonal a boundary tisztitasnal.
- A boundary tisztitasnak determinisztikusnak kell maradnia (CCW normalizalas + lexikografikus kezdo pont).

Megjegyzes:
- A kesobbi T03-T07 simplify strategiak csak ugy fogadhatok el, ha a canonical tisztitas invariansai nem serulnek.

## 7. Final validation elve

Kotelezo elv:
- A placement, overlap, boundary ervenyesseg vegso ellenorzese exact geometry ellen tortenjen.
- A solver geometry eredmenye onmagaban nem eleg gyartasi elfogadashoz.
- Ha solver es exact viselkedes konfliktusba kerul, exact geometry az elsosegi forras.

Operativ kovetkezmeny T03-T10-re:
- Minden uj NFP/cleanup/modositas only-if elfogadhato, ha vegul exact geometry alapu validacio mellett is helyes eredmenyt ad.
