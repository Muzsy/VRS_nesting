# canvases/nesting_engine/arc_spline_polygonization_policy.md

## 🎯 Funkció

F3-1 cél: az importerben használt **ARC / SPLINE / ELLIPSE poligonizálási policy** véglegesítése,
repo-szintű source-of-truth konstansokkal, dokumentált toleranciával és regressziós fixture-kel.

A feladat lényege nem új geometriai motor írása, hanem a már meglévő Python DXF import/polygonize útvonal
**egységesítése, keményítése és bizonyíthatóvá tétele**.

Kimeneti elv:
- a görbealapú DXF entitások determinisztikusan ugyanarra a polygonizált reprezentációra fussanak,
- az `arc_tolerance_mm = 0.2` policy dokumentáltan és ténylegesen legyen alkalmazva,
- az arc-heavy / spline-heavy edge-case-ekre legyen repo-ban élő regressziós bizonyíték,
- a pozitív fixture-ök polygonizálása után **0 self-intersection** maradjon.

### Nem cél
- Nem része a feladatnak a Rust oldali NFP / placement / SA módosítása.
- Nem része a feladatnak új user-facing config mező vagy CLI paraméter bevezetése.
- Nem része a feladatnak a part-in-part vagy remnant scoring logika.
- Nem cél a nominal/export contract újratervezése; az importerből kijövő nominal pontlista marad az export truth layer.

## 🧠 Fejlesztési részletek

### Kiinduló repo-helyzet
A jelenlegi repóban az ARC/SPLINE/ELLIPSE kezelés több helyen, részben implicit policy-val él:
- `vrs_nesting/geometry/polygonize.py`
  - `arc_to_points(..., max_chord_error_mm=0.2, min_segments=12)`
- `vrs_nesting/dxf/importer.py`
  - `ARC_CHORD_ERROR_MM = 0.2`
  - `curve_entity.flattening(flatten_tol)` útvonal SPLINE/ELLIPSE esetén
  - `CHAIN_ENDPOINT_EPSILON_MM = 0.2`
- `tests/test_dxf_importer_json_fixture.py`
  - van spline endpoint drift regresszió, de nincs még explicit arc-heavy policy teszt
- `scripts/smoke_real_dxf_fixtures.py`
  - jelenleg a meglévő `part_arc_spline_chaining_ok.dxf` fixture-t ellenőrzi,
    de nincs külön arc-heavy regressziós készlet

### Repo-kompatibilis policy döntés
A backlog jelenleg `poc/dxf_fixtures/arc_heavy/` útvonalat említ, de a repó valós DXF fixture-ei ma
következetesen a `samples/dxf_demo/` alatt élnek, és a smoke script is ezt használja.

Ezért ennél a tasknál a **repo-native canonical path**:
- valós DXF fixture-ek: `samples/dxf_demo/*.dxf`
- importer/polygonize regressziós tesztek: `tests/`
- gate-be húzott smoke: `scripts/smoke_real_dxf_fixtures.py`

Következmény:
- az F3-1 backlog/doksi szövegét ehhez kell szinkronizálni,
- nem vezetünk be párhuzamos, új fixture-hierarchiát csak ezért a feladatért.

### 1) Source-of-truth polygonization policy
A policy legyen explicit és egyhelyen karbantartható.

Elvárt eredmény:
- a kódban legyen **egyértelmű, névvel jelölt** curve flatten/polygonize policy,
- dokumentált mapping legyen a projekt-szintű `arc_tolerance_mm` fogalom és a kódbeli konstans között,
- világosan legyen különválasztva:
  - curve flatten tolerance (`arc_tolerance_mm = 0.2`)
  - chain endpoint epsilon (`CHAIN_ENDPOINT_EPSILON_MM = 0.2`)

Fontos: attól, hogy a két szám jelenleg azonos, **nem ugyanazt a fogalmat jelentik**.

### 2) Érintett kódútvonalak
A task scope-ja a meglévő Python import/polygonize útvonal lezárása:
- `vrs_nesting/geometry/polygonize.py`
  - `arc_to_points()` policy-konstansok és determinisztikus viselkedés
- `vrs_nesting/dxf/importer.py`
  - ARC polygonizálás ugyanebből a policy-ből éljen
  - SPLINE / ELLIPSE flattening ugyanennek a policy-nak megfelelő tolerance-t használja
  - maradjon stabil a `DxfImportError` kódolás

Nem elfogadható, ha az ARC, a SPLINE és az ELLIPSE külön, véletlenszerűen driftelő tolerancia-értékekkel fut.

### 3) Regressziós tesztcsomag
Minimum új vagy bővített bizonyítékok:
- `tests/test_geometry_polygonize.py` (új)
  - `arc_to_points()` chord-error policy regresszió
  - minimum szegmensszám / zártság / determinisztikus pontsor ellenőrzés
- `tests/test_dxf_importer_json_fixture.py`
  - a meglévő spline drift regresszió megtartása és szükség szerinti bővítése
- `tests/test_dxf_importer_error_handling.py`
  - ideiglenes DXF-ből generált edge-case-ek (pl. arc-heavy + self-intersection fail)

### 4) Real DXF fixture bővítés
A jelenlegi `samples/dxf_demo/part_arc_spline_chaining_ok.dxf` hasznos, de kevés az F3-1 DoD lezárásához.

Bővítendő készlet:
- `samples/dxf_demo/part_arc_heavy_ok.dxf`
  - pozitív fixture, sok ívvel / görbével, import PASS
- `samples/dxf_demo/part_arc_heavy_self_intersect_fail.dxf`
  - negatív fixture, polygonizálás / clean után stabil `DXF_INVALID_RING`
- `samples/dxf_demo/README.md`
  - röviden írja le, melyik fixture mit fed le

A `scripts/smoke_real_dxf_fixtures.py` ellenőrizze ezt a kört is.

### 5) Dokumentációs szinkron
A task végén legalább ezek legyenek szinkronban:
- `canvases/nesting_engine/nesting_engine_backlog.md`
  - F3-1 DoD repo-native fixture pathra igazítva
- `docs/nesting_engine/tolerance_policy.md`
  - curve flatten / arc tolerance policy leírva
- `docs/nesting_engine/architecture.md`
  - a Python importer polygonization policy mint nominal truth-layer előkészítés rögzítve

### Pipálható feladatlista
- [ ] A F3-1 canvas véglegesítve van repo-native fixture-path döntéssel.
- [ ] A curve polygonization policy egyértelmű, névvel jelölt konstansokra van zárva.
- [ ] Az importer ARC és SPLINE/ELLIPSE útvonala ugyanazt a flatten/polygonize policy-t használja.
- [ ] Van közvetlen unit teszt az `arc_to_points()` tolerancia/pontszám viselkedésére.
- [ ] Van arc-heavy pozitív és negatív valós DXF fixture a `samples/dxf_demo/` alatt.
- [ ] A `scripts/smoke_real_dxf_fixtures.py` lefedi az arc-heavy fixture-öket is.
- [ ] A pozitív fixture-ökön 0 self-intersection marad a polygonizálás után.
- [ ] A tolerance/architecture/backlog dokumentáció szinkronban van a kóddal.
- [ ] `./scripts/verify.sh --report codex/reports/nesting_engine/arc_spline_polygonization_policy.md` PASS.

### Kockázatok + mitigáció
- **Kockázat:** a tolerance-policy változás megváltoztatja a polygonizált pontszámot, és ezzel downstream hash / fixture viselkedés is elmozdulhat.
  - **Mitigáció:** ne új numerikus policy-t találjunk ki, hanem a jelenlegi 0.2 mm-es repo policy-t tegyük explicit source-of-truth-vá.
- **Kockázat:** az arc-heavy negatív fixture kézi DXF-e hibás vagy túl törékeny lesz.
  - **Mitigáció:** legyen minimális, célzott és README-ben dokumentált; ahol egyszerűbb, a unit test generálhat ideiglenes DXF-et `ezdxf`-fel.
- **Kockázat:** a chain epsilon és a curve flatten tolerance fogalmilag összemosódik.
  - **Mitigáció:** külön név, külön dokumentáció, explicit megjegyzés a policy szakaszban.

### Rollback terv
- Ha a gate instabillá válik, a fallback nem az új tolerance kitalálása, hanem a policy explicitálásának minimál változata:
  - konstansok centralizálása megmarad,
  - az új fixture/smoke bővítés visszavehető,
  - a meglévő `part_arc_spline_chaining_ok.dxf` regresszió marad baseline.

## 🧪 Tesztállapot

### DoD
- [ ] `arc_tolerance_mm = 0.2` dokumentálva és ténylegesen alkalmazva van az importer curve polygonization policy-jében.
- [ ] Van repo-native arc-heavy fixture készlet a `samples/dxf_demo/` alatt, README-vel dokumentálva.
- [ ] A pozitív arc-heavy fixture-ök polygonizálása után 0 self-intersection marad.
- [ ] A negatív arc-heavy fixture stabil, determinisztikus hibakóddal bukik (`DXF_INVALID_RING` vagy dokumentált importer-hiba).
- [ ] `python3 -m pytest -q` PASS a kapcsolódó importer/polygonize tesztekkel.
- [ ] `python3 scripts/smoke_real_dxf_fixtures.py` PASS a bővített fixture-készlettel.
- [ ] `./scripts/verify.sh --report codex/reports/nesting_engine/arc_spline_polygonization_policy.md` PASS.

### Releváns futások
- `python3 -m pytest -q`
- `python3 scripts/smoke_real_dxf_fixtures.py`
- `./scripts/verify.sh --report codex/reports/nesting_engine/arc_spline_polygonization_policy.md`

## 🌍 Lokalizáció
Nem releváns.

## 📎 Kapcsolódások
- `canvases/nesting_engine/nesting_engine_backlog.md`
- `vrs_nesting/geometry/polygonize.py`
- `vrs_nesting/dxf/importer.py`
- `tests/test_dxf_importer_json_fixture.py`
- `tests/test_dxf_importer_error_handling.py`
- `scripts/smoke_real_dxf_fixtures.py`
- `samples/dxf_demo/README.md`
- `docs/nesting_engine/tolerance_policy.md`
- `docs/nesting_engine/architecture.md`
- `docs/dxf_nesting_app_3_ivek_spline_ok_poligonizalasa_geometria_clean_reszletes.md`
