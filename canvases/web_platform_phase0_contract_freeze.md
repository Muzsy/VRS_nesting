# canvases/web_platform_phase0_contract_freeze.md

# Web platform Phase 0 contract freeze

## 🎯 Funkcio
A Phase 0 celja, hogy a meglvo DXF futasi contract web-platform kompatibilis legyen:
- SVG artifactok generalasa per-sheet a DXF export melle
- dxf-run report paths bovitese `out_svg_dir` kulccsal
- explicit smoke ellenorzes az SVG artifactra, repo gate-be kotve

## 🧠 Fejlesztesi reszletek

### Scope
- Benne van:
  - `vrs_nesting/dxf/exporter.py`: uj `export_per_sheet_svg()` funkcio.
  - `vrs_nesting/pipeline/dxf_pipeline.py`: SVG export meghivasa + report `paths.out_svg_dir`.
  - `docs/dxf_run_artifacts_contract.md`: SVG artifact es `out_svg_dir` contract frissites.
  - `scripts/smoke_svg_export.py`: dxf-run smoke SVG-re.
  - `scripts/check.sh`: uj smoke bekotese.
  - Codex checklist + report + verify futas.
- Nincs benne:
  - Supabase/API/frontend/worker scaffolding (Phase 1+).
  - Viewer fallback renderer (placements alapu canvas) implementacio.

### Erintett fajlok
- `canvases/web_platform_phase0_contract_freeze.md`
- `codex/goals/canvases/fill_canvas_web_platform_phase0_contract_freeze.yaml`
- `codex/codex_checklist/web_platform_phase0_contract_freeze.md`
- `codex/reports/web_platform_phase0_contract_freeze.md`
- `vrs_nesting/dxf/exporter.py`
- `vrs_nesting/pipeline/dxf_pipeline.py`
- `docs/dxf_run_artifacts_contract.md`
- `scripts/smoke_svg_export.py`
- `scripts/check.sh`

### DoD
- [ ] `vrs_nesting/dxf/exporter.py` tartalmaz uj `export_per_sheet_svg()` funkciot, ami per-sheet `out/sheet_NNN.svg` fajlokat general.
- [ ] A `dxf-run` futas sikeres esetben legeneralja az SVG artifactokat a DXF-ek melle.
- [ ] `report.json` `paths` objektuma tartalmazza az `out_svg_dir` kulcsot.
- [ ] `docs/dxf_run_artifacts_contract.md` frissitve van SVG artifact + `out_svg_dir` kovetelmennyel.
- [ ] Uj smoke script ellenorzi, hogy `out/sheet_001.svg` letezik es nem ures.
- [ ] `scripts/check.sh` futtatja az uj SVG smoke-ot.
- [ ] `./scripts/verify.sh --report codex/reports/web_platform_phase0_contract_freeze.md` PASS.

### Kockazat + mitigacio + rollback
- Kockazat: az ezdxf SVG backend edge-case geometriaknal eltoro renderelest adhat.
- Mitigacio: a smoke csak artifact letet es nem-ures outputot kapuzza; viewer fallback kulon fázis.
- Kockazat: uj smoke novelheti gate futasi idot.
- Mitigacio: minimalis 1 stock/1 part fixture hasznalat, rovid `time_limit_s`.
- Rollback: a Phase 0 modositott fajljai egyben visszavonhatok; dxf-run korabbi DXF behavior visszaall.

## 🧪 Tesztallapot
- Kotelezo gate:
  - `./scripts/verify.sh --report codex/reports/web_platform_phase0_contract_freeze.md`
- Feladat-specifikus:
  - `python3 scripts/smoke_svg_export.py`

## 🌍 Lokalizacio
N/A

## 📎 Kapcsolodasok
- `tmp/MVP_Web_ui_audit/VRS_nesting_implementacios_terv.docx`
- `tmp/MVP_Web_ui_audit/VRS_nesting_web_platform_spec.md`
- `docs/dxf_run_artifacts_contract.md`
