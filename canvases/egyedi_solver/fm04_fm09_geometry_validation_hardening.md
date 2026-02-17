# canvases/egyedi_solver/fm04_fm09_geometry_validation_hardening.md

# FM04-FM09 geometry and validator hardening

## 🎯 Funkcio
A feladat a DXF correctness audit kovetkezo hianyossagainak javitasa:
- FM-04: chaining algoritmus ketiranyu bovitese
- FM-05: self-intersection detektalas importnal
- FM-06: valos geometriai overlap validacio (nem bbox-only)
- FM-07: spacing/margin invariansok ellenorzese validatorban
- FM-08: `source_base_offset_mm` szamitasa prepared geometriabol
- FM-09: closed SPLINE kezeles robusztusabba tetele

## 🧠 Fejlesztesi reszletek

### Scope
- Benne van:
  - `vrs_nesting/dxf/importer.py` bovites FM04/FM05/FM09 szerint.
  - `vrs_nesting/nesting/instances.py` validator erosites FM06/FM07 szerint.
  - `vrs_nesting/sparrow/input_generator.py` FM08 javitas.
  - Unit tesztek bovitese/import regressziok + validator spacing/margin + input_generator offset.
  - Codex checklist + report kitoltese, verify gate futtatasa.
- Nincs benne:
  - FM10+ audit pontok javitasa.
  - Exporter viselkedes valtoztatasa.

### Erintett fajlok
- `vrs_nesting/dxf/importer.py`
- `vrs_nesting/nesting/instances.py`
- `vrs_nesting/sparrow/input_generator.py`
- `tests/test_dxf_importer_json_fixture.py`
- `tests/test_output_status_validation.py`
- `tests/test_sparrow_input_generator.py`
- `canvases/egyedi_solver/fm04_fm09_geometry_validation_hardening.md`
- `codex/goals/canvases/egyedi_solver/fill_canvas_fm04_fm09_geometry_validation_hardening.yaml`
- `codex/codex_checklist/egyedi_solver/fm04_fm09_geometry_validation_hardening.md`
- `codex/reports/egyedi_solver/fm04_fm09_geometry_validation_hardening.md`

### DoD
- [ ] FM-04: chaining tud prepend+append iranyban is epiteni (nem csak chain end felol).
- [ ] FM-05: import self-intersecting outer/inner konturra deterministic hibaval leall.
- [ ] FM-09: `SPLINE closed=true` esetben endpoint drift miatt nem lesz fals open-path hiba.
- [ ] FM-06: multi-sheet validator valos polygon overlapet ellenoriz, nem csak bbox-ot.
- [ ] FM-07: multi-sheet validator enforce-olja `spacing_mm` es `margin_mm` invariansokat.
- [ ] FM-08: `source_base_offset_mm` prepared geometriabol szamolodik.
- [ ] Unit tesztek lefedik az uj viselkedest.
- [ ] `./scripts/verify.sh --report codex/reports/egyedi_solver/fm04_fm09_geometry_validation_hardening.md` PASS.

### Kockazat + mitigacio + rollback
- Kockazat: validator szigoritas regressziot hozhat korabban elfogadott, de geometriailag hibas kimenetre.
- Mitigacio: pontos hiba-uzenetek + targeted tesztek spacing/margin/overlap esetekre.
- Kockazat: chaining valtozas nyitott kontur detekciot erintheti.
- Mitigacio: meglvo tesztek + uj chaining/spline regresszio tesztek.
- Rollback: egy commitban visszavonhato, mivel valtozas csak importer/validator/input_generator + tesztek teruletet erinti.

## 🧪 Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/egyedi_solver/fm04_fm09_geometry_validation_hardening.md`
- Feladat-specifikus:
  - `python3 -m pytest -q tests/test_dxf_importer_json_fixture.py`
  - `python3 -m pytest -q tests/test_output_status_validation.py`
  - `python3 -m pytest -q tests/test_sparrow_input_generator.py`

## 🌍 Lokalizacio
N/A

## 📎 Kapcsolodasok
- `tmp/DXF_correctness_audit_2026_02_17/VRS_nesting_DXF_Correctness_Audit.md`
- `vrs_nesting/dxf/importer.py`
- `vrs_nesting/nesting/instances.py`
- `vrs_nesting/sparrow/input_generator.py`
