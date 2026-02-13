# Codex checklist - exporter_out_dir_integration

- [x] Canvas DoD pontositva a `--run-dir` default pathokra es a mutual-exclusion szabalyra (`canvases/egyedi_solver/exporter_out_dir_integration.md`)
- [x] `RunContext` kiegészítve `out_dir` mezovel, `create_run_dir` letrehozza a `run_dir/out` konyvtarat (`vrs_nesting/run_artifacts/run_dir.py`)
- [x] Exporter CLI tamogatja a `--run-dir` opciot, es kezeli a ketertelmu kapcsolo-kombinaciokat (`vrs_nesting/dxf/exporter.py`)
- [x] Uj smoke script kesz: `scripts/smoke_export_run_dir_out.py`
- [x] Smoke bekotve a standard gate-be (`scripts/check.sh`)
- [x] Verify wrapper futtatva: `./scripts/verify.sh --report codex/reports/egyedi_solver/exporter_out_dir_integration.md`
- [x] Kotelezo vegso gate futtatva: `./scripts/check.sh`
