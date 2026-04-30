# Codex checklist - cavity_t6_svg_dxf_export_validation

- [x] AGENTS.md + Codex szabalyok + T6 canvas/YAML/prompt atnezve
- [x] T5 utani projection->export futasi utvonal atnezve (`worker/sheet_svg_artifacts.py`, `worker/sheet_dxf_artifacts.py`)
- [x] Composite cavity smoke keszult: `scripts/smoke_cavity_t6_svg_dxf_export_validation.py`
- [x] Smoke bizonyitja: parent + internal child geometry SVG-ben megjelenik
- [x] Smoke bizonyitja: parent hole SVG-ben megmarad
- [x] Smoke bizonyitja: parent + child outer + parent hole DXF-ben megjelenik
- [x] Smoke bizonyitja: virtual ID nem szivarog sem projectionbe, sem artifactba
- [x] Exporter kodmodositas NEM kellett (minimal-fix step skip evidence alapon)
- [x] `python3 scripts/smoke_cavity_t6_svg_dxf_export_validation.py` PASS
- [x] `python3 scripts/smoke_h1_e6_t2_sheet_svg_generator_h1_minimum.py` PASS
- [x] `python3 scripts/smoke_h1_e6_t3_sheet_dxf_export_artifact_generator_h1_minimum.py` PASS
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/cavity_t6_svg_dxf_export_validation.md` PASS
