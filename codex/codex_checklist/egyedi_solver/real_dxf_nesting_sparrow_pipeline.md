# Codex checklist - real_dxf_nesting_sparrow_pipeline

- [x] Canvas pontositva: CLI belépési pont, `dxf_v1` schema, run artefakt lista (`canvases/egyedi_solver/real_dxf_nesting_sparrow_pipeline.md`)
- [x] Uj strict DXF schema bevezetve a modelben (`vrs_nesting/project/model.py`)
- [x] Dokumentacio frissitve (`docs/dxf_project_schema.md`, `docs/mvp_project_schema.md`)
- [x] Importer bovitve ARC/SPLINE poligonizalassal es chaininggel (`vrs_nesting/dxf/importer.py`)
- [x] Sparrow input generator letrehozva (`vrs_nesting/sparrow/input_generator.py`)
- [x] Multi-sheet wrapper letrehozva es runner integracio bovitve (`vrs_nesting/sparrow/multi_sheet_wrapper.py`, `vrs_nesting/runner/sparrow_runner.py`)
- [x] Exporter source-geometria prioritast kap (`vrs_nesting/dxf/exporter.py`)
- [x] DXF pipeline belépési pont: `cli dxf-run` + script wrapper (`vrs_nesting/cli.py`, `scripts/run_real_dxf_sparrow_pipeline.py`)
- [x] Real DXF pipeline smoke + gate bekotes (`scripts/smoke_real_dxf_sparrow_pipeline.py`, `scripts/check.sh`, `samples/dxf_demo/README.md`)
- [x] Verify wrapper futtatva: `./scripts/verify.sh --report codex/reports/egyedi_solver/real_dxf_nesting_sparrow_pipeline.md`
- [x] Kotelezo vegso gate futtatva: `./scripts/check.sh`
