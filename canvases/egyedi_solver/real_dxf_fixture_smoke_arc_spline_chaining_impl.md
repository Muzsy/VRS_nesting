# canvases/egyedi_solver/real_dxf_fixture_smoke_arc_spline_chaining_impl.md

# Valodi DXF fixture + smoke (ARC/SPLINE + chaining) implementacio

## 🎯 Funkcio
A cel, hogy a repo standard gate-je (scripts/check.sh) **tenyleges DXF fajlokon** jarassa meg a DXF import kritikus agait:
- ARC entitasok kezelese
- SPLINE entitasok kezelese
- chaining: szegmensekbol (LINE/ARC/SPLINE) zart kontur osszefuzese

Ez regressziofogast ad a "valos DXF nesting" pipeline-hoz, mert jelenleg a smoke-ok JSON fixture-rel futnak, nem igazi .dxf-en.

## 🧠 Fejlesztesi reszletek

### Scope
- Benne van:
  - Valodi `.dxf` fixture keszlet letrehozasa a repo alatt: `samples/dxf_demo/*.dxf`
  - Dedikalt smoke script, ami:
    - importal valodi DXF-et (`import_part_raw`)
    - ellenorzi, hogy az import tenylegesen latott `ARC` es `SPLINE` entitast a source_entities-ben
    - ellenorzi a chaining eredmenyet (zart outer, es hole)
    - negativ fixture-re stabil hibakodot var (`DXF_OPEN_OUTER_PATH`)
  - A mar meglevo `scripts/smoke_real_dxf_sparrow_pipeline.py` frissitese, hogy **valodi .dxf fixture**-t hasznaljon (ne JSON-t).
  - Gate-be kotes: `scripts/check.sh` futtassa az uj smoke-ot es a frissitett real_dxf pipeline smoke-ot.
  - `samples/dxf_demo/README.md` frissitese: konvencio + mire valo a keszlet + dependency megjegyzes.

- Nincs benne:
  - Exporter "eredeti geometriaval" javitasa (kulon P0-2 task).
  - Komplett termelesi DXF tesztcsomag (csak minimal regressziofixture).

### Erintett fajlok
- Uj/Frissul:
  - `samples/dxf_demo/README.md`
  - `samples/dxf_demo/stock_rect_1000x2000.dxf`
  - `samples/dxf_demo/part_arc_spline_chaining_ok.dxf`
  - `samples/dxf_demo/part_chain_open_fail.dxf`
  - `scripts/smoke_real_dxf_fixtures.py` (UJ)
  - `scripts/smoke_real_dxf_sparrow_pipeline.py` (DXF fixture-re allitva)
  - `scripts/check.sh` (uj smoke behuzasa)
- Codex artefaktok:
  - `codex/codex_checklist/egyedi_solver/real_dxf_fixture_smoke_arc_spline_chaining_impl.md`
  - `codex/reports/egyedi_solver/real_dxf_fixture_smoke_arc_spline_chaining_impl.md`

### Fixture definicio (minimal, de celzott)
- `stock_rect_1000x2000.dxf`
  - Layer: `CUT_OUTER`
  - 1000x2000 mm teglalap, zart LWPOLYLINE
- `part_arc_spline_chaining_ok.dxf`
  - Outer: `CUT_OUTER` - **LINE + ARC** szegmensek (nem zart polyline!), hogy a chainingnek dolgoznia kelljen
  - Hole: `CUT_INNER` - **SPLINE**, zart (closed)
  - Ezzel 1 file-on belul lefedjuk: ARC + SPLINE + chaining
- `part_chain_open_fail.dxf`
  - Outer: `CUT_OUTER` - chaininghez szant szegmensekbol 1 hianyzik -> elvart hiba: `DXF_OPEN_OUTER_PATH`

### DoD
- [ ] `samples/dxf_demo/` alatt letezik legalabb 2 pozitiv + 1 negativ valodi `.dxf` fixture (fentiek szerint).
- [ ] Uj smoke script: `scripts/smoke_real_dxf_fixtures.py`
  - [ ] pozitiv fixture import PASS, outer zart, hole szam PASS
  - [ ] `source_entities` tartalmaz `ARC` es `SPLINE` tipust
  - [ ] negativ fixture stabilan `DXF_OPEN_OUTER_PATH` kodot ad
- [ ] A pozitiv fixture konkretan `part_arc_spline_chaining_ok.dxf`, a negativ fixture `part_chain_open_fail.dxf`.
- [ ] `scripts/smoke_real_dxf_sparrow_pipeline.py` mar nem JSON fixture-t hasznal, hanem a valodi `.dxf` part+stock fixture-t.
- [ ] `scripts/check.sh` futtatja:
  - `python3 scripts/smoke_real_dxf_fixtures.py`
  - `python3 scripts/smoke_real_dxf_sparrow_pipeline.py`
- [ ] Verify PASS:
  - `./scripts/verify.sh --report codex/reports/egyedi_solver/real_dxf_fixture_smoke_arc_spline_chaining_impl.md`
- [ ] A reportban DoD -> Evidence matrix ki van toltve valos file+line hivatkozasokkal.

### Kockazat + mitigacio + rollback
- Kockazat: a valodi DXF importhoz kellhet `ezdxf` a kornyezetben.
- Mitigacio: smoke elejen explicit ellenorzes + ertelmes hiba-uzenet (install tipp), es CI-ben `python3-ezdxf` telepitheto.
- Rollback: a ket uj smoke hivas kiveheto a `scripts/check.sh`-bol; a fixturek a `samples/` alatt izolaltak.

## 🧪 Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/egyedi_solver/real_dxf_fixture_smoke_arc_spline_chaining_impl.md`
- Relevans futasok:
  - `./scripts/check.sh`
  - `python3 scripts/smoke_real_dxf_fixtures.py`
  - `python3 scripts/smoke_real_dxf_sparrow_pipeline.py`

## 🌍 Lokalizacio
N/A

## 📎 Kapcsolodasok
- `vrs_nesting/dxf/importer.py` (ARC/SPLINE + chaining implementacio)
- `scripts/smoke_dxf_import_convention.py` (JSON fixture konvencio smoke, marad)
- `codex/reports/egyedi_solver/real_dxf_nesting_sparrow_pipeline.md` (a jelenlegi smoke meg DXF helyett JSON-t hasznal -> ezt javitjuk)
- `docs/dxf_nesting_app_2_dxf_import_konturok_kinyerese_konvencioval_reszletes.md`
- `docs/dxf_nesting_app_3_ivek_spline_ok_poligonizalasa_geometria_clean_reszletes.md`
