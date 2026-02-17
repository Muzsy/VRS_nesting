# canvases/egyedi_solver/dxf_import_fm01_fm03_critical_fixes.md

# DXF importer FM01-FM03 critical fixes

## 🎯 Funkcio
A cel az auditor altal jelzett harom P0 hibamod javitasa a DXF importban:
- FM-01: ELLIPSE entitas tamogatasa
- FM-02: BLOCK/INSERT felbontas import elott
- FM-03: INSUNITS alapjan mm normalizalas

A javitasnak kompatibilisnek kell maradnia a jelenlegi JSON fixture backenddel es a mar meglevo smoke/test gate-tel.

## 🧠 Fejlesztesi reszletek

### Scope
- Benne van:
  - `vrs_nesting/dxf/importer.py` bovites:
    - ELLIPSE kezeles (flattening alapuan)
    - INSERT entitas rekurziv felbontasa virtual entities-re
    - INSUNITS -> mm scale normalizalas (pontok/radius/center)
  - Unit teszt lefedes FM01-03-hoz valos `.dxf` bemenettel (`ezdxf`-fel generalva).
  - Codex checklist + report frissites, DoD evidence matrix kitoltese.
- Nincs benne:
  - FM04+ tovabbi audit pontok javitasa
  - DXF exporter modositasok
  - teljesitmeny optimalizalas (FM14)

### Erintett fajlok
- `vrs_nesting/dxf/importer.py`
- `tests/test_dxf_importer_error_handling.py`
- `canvases/egyedi_solver/dxf_import_fm01_fm03_critical_fixes.md`
- `codex/goals/canvases/egyedi_solver/fill_canvas_dxf_import_fm01_fm03_critical_fixes.yaml`
- `codex/codex_checklist/egyedi_solver/dxf_import_fm01_fm03_critical_fixes.md`
- `codex/reports/egyedi_solver/dxf_import_fm01_fm03_critical_fixes.md`

### DoD
- [ ] FM-01: `import_part_raw()` elfogad ELLIPSE outer konturt valos DXF-ben (nem `DXF_UNSUPPORTED_ENTITY_TYPE`).
- [ ] FM-02: INSERT/BLOCK geometriat az importer felbontja, es CUT_OUTER/CUT_INNER layer konturok importalhatok block referenciabol.
- [ ] FM-03: DXF `INSUNITS` alapjan az importalt geometria mm-ben jon vissza (pl. 1 inch -> 25.4 mm).
- [ ] A fenti viselkedesre unit tesztek vannak es zolden futnak.
- [ ] Repo gate PASS a verify wrapperrel:
  - `./scripts/verify.sh --report codex/reports/egyedi_solver/dxf_import_fm01_fm03_critical_fixes.md`
- [ ] Checklist + report (DoD -> Evidence) kitoltve.

### Kockazat + mitigacio + rollback
- Kockazat: INSERT virtual entity felbontasnal exotikus DXF esetekben uj unsupported tipusok megjelenhetnek.
- Mitigacio: meglvo deterministic hibaag marad (`DXF_UNSUPPORTED_ENTITY_TYPE`), csak a tamogatott geometriak mennek tovabb.
- Kockazat: INSUNITS mapping hianyos kodokra.
- Mitigacio: ismeretlen unit kodra explicit hiba (`DXF_UNSUPPORTED_UNITS`) a silent rossz skala helyett.
- Rollback: importer valtozasok visszavonhatok egy commitban; tesztek jelzik a regressziot.

## 🧪 Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/egyedi_solver/dxf_import_fm01_fm03_critical_fixes.md`
- Feladat-specifikus:
  - `python3 -m pytest -q tests/test_dxf_importer_error_handling.py`

## 🌍 Lokalizacio
N/A

## 📎 Kapcsolodasok
- `tmp/DXF_correctness_audit_2026_02_17/VRS_nesting_DXF_Correctness_Audit.md` (FM-01, FM-02, FM-03)
- `vrs_nesting/dxf/importer.py`
- `tests/test_dxf_importer_error_handling.py`
- `docs/codex/overview.md`
