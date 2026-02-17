PASS

## 1) Meta
- Task slug: `fm04_fm09_geometry_validation_hardening`
- Kapcsolodo canvas: `canvases/egyedi_solver/fm04_fm09_geometry_validation_hardening.md`
- Kapcsolodo goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_fm04_fm09_geometry_validation_hardening.yaml`
- Fokusz terulet: `DXF Import | Geometry Validation | Sparrow Input`

## 2) Scope

### 2.1 Cel
- FM04/FM05/FM09 javitas az importerben.
- FM06/FM07 javitas a multi-sheet validatorban.
- FM08 javitas a sparrow input generatorban.
- Unit teszt lefedes bovitese az uj viselkedesekre.

### 2.2 Nem-cel
- FM10+ audit pontok javitasa.
- DXF exporter logika modositas.

## 3) Valtozasok osszefoglalasa

### 3.1 Erintett fajlok
- `canvases/egyedi_solver/fm04_fm09_geometry_validation_hardening.md`
- `codex/goals/canvases/egyedi_solver/fill_canvas_fm04_fm09_geometry_validation_hardening.yaml`
- `vrs_nesting/dxf/importer.py`
- `vrs_nesting/nesting/instances.py`
- `vrs_nesting/sparrow/input_generator.py`
- `tests/test_dxf_importer_json_fixture.py`
- `tests/test_output_status_validation.py`
- `tests/test_sparrow_input_generator.py`
- `codex/codex_checklist/egyedi_solver/fm04_fm09_geometry_validation_hardening.md`
- `codex/reports/egyedi_solver/fm04_fm09_geometry_validation_hardening.md`

### 3.2 Miert valtoztak?
- A DXF correctness auditban nyitott FM04-FM09 hianyossagokat celzottan javitani kell a gyartasi korrektseg erositesere.

## 4) Verifikacio (How tested)

### 4.1 Kotelezo parancs
- `./scripts/verify.sh --report codex/reports/egyedi_solver/fm04_fm09_geometry_validation_hardening.md` -> PASS

### 4.2 Opcionals
- `python3 -m pytest -q tests/test_dxf_importer_json_fixture.py` -> PASS
- `python3 -m pytest -q tests/test_output_status_validation.py` -> PASS
- `python3 -m pytest -q tests/test_sparrow_input_generator.py` -> PASS

### 4.3 Ha valami kimaradt
- N/A

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo teszt/ellenorzes |
| --- | --- | --- | --- | --- |
| FM-04 ketiranyu chaining | PASS | `vrs_nesting/dxf/importer.py:473`, `vrs_nesting/dxf/importer.py:513`, `tests/test_dxf_importer_json_fixture.py:85` | A chaining mar a chain elejet is tudja boviteni (`_prepend_path`), igy olyan eseteket is osszefuz, ahol csak start-oldali illesztes van. | `python3 -m pytest -q tests/test_dxf_importer_json_fixture.py` |
| FM-05 self-intersection check | PASS | `vrs_nesting/dxf/importer.py:428`, `vrs_nesting/dxf/importer.py:449`, `vrs_nesting/dxf/importer.py:595`, `tests/test_dxf_importer_json_fixture.py:101` | Az importer topologiai onmetszes ellenorzest futtat minden normalizalt ringen, es deterministic `DXF_INVALID_RING` hibaval all meg. | `python3 -m pytest -q tests/test_dxf_importer_json_fixture.py` |
| FM-09 closed spline drift robustness | PASS | `vrs_nesting/dxf/importer.py:611`, `vrs_nesting/dxf/importer.py:616`, `tests/test_dxf_importer_json_fixture.py:122` | `closed=true` SPLINE/ELLIPSE eseten endpoint drift mellett is explicit konturzarat kap a ring (nem esik at open-path agra). | `python3 -m pytest -q tests/test_dxf_importer_json_fixture.py` |
| FM-06 polygon overlap validator | PASS | `vrs_nesting/nesting/instances.py:311`, `vrs_nesting/nesting/instances.py:323`, `tests/test_output_status_validation.py:52` | A validator placementenkent valos polygont epit/forgat, es interszekcio area alapjan vizsgal overlapet bbox-helyett. | `python3 -m pytest -q tests/test_output_status_validation.py` |
| FM-07 spacing/margin validator checks | PASS | `vrs_nesting/nesting/instances.py:261`, `vrs_nesting/nesting/instances.py:317`, `vrs_nesting/nesting/instances.py:325`, `tests/test_output_status_validation.py:92`, `tests/test_output_status_validation.py:119` | A validator olvassa `spacing_mm`/`margin_mm` mezoket, spacing tavolsagot es margin buffer-feltetelt enforce-ol placement ellenorzeskor. | `python3 -m pytest -q tests/test_output_status_validation.py` |
| FM-08 source_base_offset prepared geometriabol | PASS | `vrs_nesting/sparrow/input_generator.py:56`, `vrs_nesting/sparrow/input_generator.py:134`, `vrs_nesting/sparrow/input_generator.py:158`, `tests/test_sparrow_input_generator.py:18`, `tests/test_sparrow_input_generator.py:65` | A `source_base_offset_mm` mar prepared outer pontokbol szamolodik, es a solver input explicit tartalmazza spacing/margin + prepared geometriat a validatornak. | `python3 -m pytest -q tests/test_sparrow_input_generator.py` |
| Verify gate PASS | PASS | `codex/reports/egyedi_solver/fm04_fm09_geometry_validation_hardening.verify.log` | A kotelezo verify wrapper teljes check.sh futasa zolden lefutott. | `./scripts/verify.sh --report codex/reports/egyedi_solver/fm04_fm09_geometry_validation_hardening.md` |

## 8) Advisory notes
- A validator most shapely-re tamaszkodik geometriavalidaciora; a repoban ez mar baseline dependency, de runtime hiany eseten explicit hibaval lep ki.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-02-17T23:06:28+01:00 → 2026-02-17T23:08:13+01:00 (105s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/fm04_fm09_geometry_validation_hardening.verify.log`
- git: `fix/repo-gate-sparrow-fallback@9ac3287`
- módosított fájlok (git status): 11

**git diff --stat**

```text
 tests/test_dxf_importer_json_fixture.py |  57 +++++++-
 tests/test_output_status_validation.py  |  88 +++++++++++
 vrs_nesting/dxf/importer.py             | 106 +++++++++++++-
 vrs_nesting/nesting/instances.py        | 249 ++++++++++++++++----------------
 vrs_nesting/sparrow/input_generator.py  |   8 +-
 5 files changed, 376 insertions(+), 132 deletions(-)
```

**git status --porcelain (preview)**

```text
 M tests/test_dxf_importer_json_fixture.py
 M tests/test_output_status_validation.py
 M vrs_nesting/dxf/importer.py
 M vrs_nesting/nesting/instances.py
 M vrs_nesting/sparrow/input_generator.py
?? canvases/egyedi_solver/fm04_fm09_geometry_validation_hardening.md
?? codex/codex_checklist/egyedi_solver/fm04_fm09_geometry_validation_hardening.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_fm04_fm09_geometry_validation_hardening.yaml
?? codex/reports/egyedi_solver/fm04_fm09_geometry_validation_hardening.md
?? codex/reports/egyedi_solver/fm04_fm09_geometry_validation_hardening.verify.log
?? tests/test_sparrow_input_generator.py
```

<!-- AUTO_VERIFY_END -->
