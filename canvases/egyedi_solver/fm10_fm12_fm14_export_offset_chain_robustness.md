# canvases/egyedi_solver/fm10_fm12_fm14_export_offset_chain_robustness.md

# FM10 FM11 FM12 FM14 exporter-offset-chain robustness

## 🎯 Funkcio
A feladat a DXF correctness audit P2 pontjainak javitasa:
- FM-10: explicit `mitre_limit` hasznalat offsetben
- FM-11: approx exportban ARC/SPLINE entitastipus megorzese, ha forras geometriaval rendelkezesre all
- FM-12: approx block nevutkozes elkerulese
- FM-14: chaining algoritmus teljesitmenyjavitas endpoint-index alapra

## 🧠 Fejlesztesi reszletek

### Scope
- Benne van:
  - `vrs_nesting/geometry/offset.py` explicit mitre_limit konfiguracio.
  - `vrs_nesting/dxf/exporter.py` approx mode fejlesztes source-entity aware block generalassal,
    es collision-safe block naminggel.
  - `vrs_nesting/dxf/importer.py` chaining endpoint-index alapu gyorsitasa.
  - uj/regresszios unit tesztek exporter+offset+chaining teruletre.
  - codex checklist + report + verify.
- Nincs benne:
  - P0/P1 tovabbi audit pontok modositasai.
  - source export mod semantikajanak valtoztatasa.

### Erintett fajlok
- `vrs_nesting/geometry/offset.py`
- `vrs_nesting/dxf/exporter.py`
- `vrs_nesting/dxf/importer.py`
- `tests/test_dxf_exporter_approx_mode.py`
- `tests/test_geometry_offset.py`
- `tests/test_dxf_importer_json_fixture.py`
- `canvases/egyedi_solver/fm10_fm12_fm14_export_offset_chain_robustness.md`
- `codex/goals/canvases/egyedi_solver/fill_canvas_fm10_fm12_fm14_export_offset_chain_robustness.yaml`
- `codex/codex_checklist/egyedi_solver/fm10_fm12_fm14_export_offset_chain_robustness.md`
- `codex/reports/egyedi_solver/fm10_fm12_fm14_export_offset_chain_robustness.md`

### DoD
- [ ] FM-10: offset buffer hivasok explicit `mitre_limit` parametert hasznalnak.
- [ ] FM-11: approx export mode kepes source entitykkel ARC/SPLINE-t megtartani (nem kotelezo line-only fallback).
- [ ] FM-12: approx block nevek stabilan collision-safe-ek.
- [ ] FM-14: chaining endpoint-indexes keresest hasznal, nem global linearis scan minden iteracioban.
- [ ] Unit tesztek lefedik az uj viselkedeseket.
- [ ] `./scripts/verify.sh --report codex/reports/egyedi_solver/fm10_fm12_fm14_export_offset_chain_robustness.md` PASS.

### Kockazat + mitigacio + rollback
- Kockazat: approx export entity-megorzese ezdxf fuggoseget erositi.
- Mitigacio: ha source_entities hianyzik, fallback marad line-based approx exportra.
- Kockazat: chaining algoritmus valtozas regressziot okozhat nyitott/zart kontur felismeresben.
- Mitigacio: meglevo chaining tesztek + celzott regresszio teszt fenntartasa.
- Rollback: valtozasok egy commitban visszavonhatok.

## 🧪 Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/egyedi_solver/fm10_fm12_fm14_export_offset_chain_robustness.md`
- Feladat-specifikus:
  - `python3 -m pytest -q tests/test_dxf_exporter_approx_mode.py`
  - `python3 -m pytest -q tests/test_geometry_offset.py`
  - `python3 -m pytest -q tests/test_dxf_importer_json_fixture.py`

## 🌍 Lokalizacio
N/A

## 📎 Kapcsolodasok
- `tmp/DXF_correctness_audit_2026_02_17/VRS_nesting_DXF_Correctness_Audit.md`
- `vrs_nesting/geometry/offset.py`
- `vrs_nesting/dxf/exporter.py`
- `vrs_nesting/dxf/importer.py`
