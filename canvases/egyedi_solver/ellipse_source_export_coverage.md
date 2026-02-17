# canvases/egyedi_solver/ellipse_source_export_coverage.md

# ELLIPSE source export hiany javitasa

## 🎯 Funkcio
A feladat a DXF exporter `source_entities` feldolgozasaban az ELLIPSE entitas hianyanak javitasa.
Jelenleg az ELLIPSE tipus warninggal skipelodik, ami geometria-vesztessel jarhat source exportban.

## 🧠 Fejlesztesi reszletek

### Scope
- Benne van:
  - `vrs_nesting/dxf/exporter.py` ELLIPSE tamogatas bovitese `_add_source_entities_to_block()` fuggvenyben.
  - Regresszios unit teszt, ami source mode exportban ellenorzi az ELLIPSE geometria megtartasat.
  - Codex checklist + report + verify artefaktok frissitese.
- Nincs benne:
  - DXF importer ELLIPSE flattening valtoztatasa.
  - Egyeb exporter modok (nem source entity branch) semantikajanak atalaklitasa.

### Erintett fajlok
- `vrs_nesting/dxf/exporter.py`
- `tests/test_dxf_exporter_source_mode.py`
- `canvases/egyedi_solver/ellipse_source_export_coverage.md`
- `codex/goals/canvases/egyedi_solver/fill_canvas_ellipse_source_export_coverage.yaml`
- `codex/codex_checklist/egyedi_solver/ellipse_source_export_coverage.md`
- `codex/reports/egyedi_solver/ellipse_source_export_coverage.md`

### DoD
- [ ] Source entity export nem dobja el az `ELLIPSE` tipust.
- [ ] Source mode DXF exportban az ELLIPSE forrasgeometria tenylegesen megjelenik a blokkban.
- [ ] Regresszios unit teszt lefedi az ELLIPSE source export esetet.
- [ ] `./scripts/verify.sh --report codex/reports/egyedi_solver/ellipse_source_export_coverage.md` PASS.

### Kockazat + mitigacio + rollback
- Kockazat: az ELLIPSE JSON/source payload formatok heterogenek lehetnek.
- Mitigacio: ketfoku kezeles; ha van natív ellipszis-parameter, natív entitas iras, kulonben pontsorbol LWPOLYLINE fallback.
- Rollback: valtozasok egy commitban visszavonhatok.

## 🧪 Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/egyedi_solver/ellipse_source_export_coverage.md`
- Feladat-specifikus:
  - `python3 -m pytest -q tests/test_dxf_exporter_source_mode.py`

## 🌍 Lokalizacio
N/A

## 📎 Kapcsolodasok
- `tmp/DXF_correctness_audit_2026_02_17/VRS_nesting_DXF_Correctness_Audit.md`
- `vrs_nesting/dxf/exporter.py`
