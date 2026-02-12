# Geometriai polygonize + clean + offset pipeline implementacio

## 🎯 Funkcio
Ez a task a P1-GEO-01 es P1-GEO-02 kovetelmenyek kodszintu teljesiteset adja: letrehozza a hianyzo geometriai preprocess modulokat (`polygonize.py`, `clean.py`, `offset.py`) es a gate-ben futtathato robustussagi smoke ellenorzest.
A cel egy minimalis, de valos API, ami a DXF importbol jovo ring geometriakat tisztitja, normalizalja, majd spacing/margin offsettel elokesziti.

## 🧠 Fejlesztesi reszletek
### Scope
- Benne van:
  - `vrs_nesting/geometry/polygonize.py` letrehozasa a PartRaw/StockRaw-szeru ring normalizalo pipeline-hoz.
  - `vrs_nesting/geometry/clean.py` letrehozasa (dedupe, rovid elek szurese, zartsag/orientacio normalizalas).
  - `vrs_nesting/geometry/offset.py` letrehozasa (part outset + stock inset + hole kezeles).
  - Geometriai smoke script + fixturek, gate-be kotve.
- Nincs benne:
  - DXF iv/spline valos mintavetelezes implementacio (ezdxf flattening teljes kiepitese).
  - Solver heurisztika modositasa.
  - Export pipeline valtoztatas.

### Erintett fajlok
- `vrs_nesting/geometry/__init__.py`
- `vrs_nesting/geometry/clean.py`
- `vrs_nesting/geometry/polygonize.py`
- `vrs_nesting/geometry/offset.py`
- `scripts/smoke_geometry_pipeline.py`
- `samples/geometry/part_raw_dirty.json`
- `samples/geometry/stock_raw_shape.json`
- `scripts/check.sh`
- `codex/codex_checklist/egyedi_solver/geometry_offset_robustness_impl.md`
- `codex/reports/egyedi_solver/geometry_offset_robustness_impl.md`

### DoD
- [ ] Letrejon a `vrs_nesting/geometry/polygonize.py` es `vrs_nesting/geometry/clean.py` a ring clean/normalizalo API-val.
- [ ] Letrejon a `vrs_nesting/geometry/offset.py` ami part outsetet es stock insetet ad spacing/margin szabaly szerint.
- [ ] A geometriai smoke script fut es ellenorzi a pipeline alap invariansait (valid geometriak, orientacio, nem-ures offset eredmeny).
- [ ] A standard gate (`scripts/check.sh`) futtatja a geometriai smoke ellenorzest is.
- [ ] A report DoD -> Evidence matrix minden ponthoz konkret kodbizonyitekot tartalmaz.

### Kockazat + mitigacio + rollback
- Kockazat: offset degeneracio miatt egyes geometriak osszeomolhatnak (vekony fal, onmetszes).
- Mitigacio: fail-fast validacio, determinisztikus hibakodok, minimalis smoke fixturek.
- Rollback: geometry smoke hivas kiveheto a `scripts/check.sh`-bol; modulok izolaltak maradnak.

## 🧪 Tesztallapot
- Kotelezo gate: `./scripts/verify.sh --report codex/reports/egyedi_solver/geometry_offset_robustness_impl.md`
- Relevans futasok:
  - `python3 scripts/smoke_geometry_pipeline.py`
  - `./scripts/check.sh`

## 🌍 Lokalizacio
N/A

## 📎 Kapcsolodasok
- `tmp/egyedi_solver/mvp_terv_tablas_nesting_fix_w_h_alakos_tabla_alap_a_meglevo_vrs_nesting_repora_epitve.md` (4.3, 4.4)
- `tmp/egyedi_solver/tablas_optimalizacios_algoritmus_jagua_rs_integracio_reszletes_rendszerleiras.md` (geometry modulok)
- `tmp/egyedi_solver/uj_tablas_solver_fix_w_h_alakos_stock_komplett_dokumentacio.md` (offset + sanity)
- `docs/dxf_nesting_app_3_ivek_spline_ok_poligonizalasa_geometria_clean_reszletes.md`
- `docs/dxf_nesting_app_4_spacing_margin_implementacio_offsettel_reszletes.md`
- `codex/reports/egyedi_solver_p1_audit.md` (P1-GEO-01, P1-GEO-02)
