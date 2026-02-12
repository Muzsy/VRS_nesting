# Codex checklist - cli_run_solver_pipeline

- [x] Canvas pontositva a valos artifact listaval, stdout/stderr szabalyokkal es `report.json` minimum mezokkel
- [x] CLI run pipeline implementalva (`project -> solver_input -> runner same run_dir -> validator -> exporter -> report.json`)
- [x] Runner kapott meglevo run_dir API-t (`run_solver_in_dir`) CLI kompatibilitas megtartasa mellett
- [x] `samples/project_rect_1000x2000.json` strict schema kompatibilis
- [x] Manualis smoke: `python3 -m vrs_nesting.cli run samples/project_rect_1000x2000.json`
- [x] Ellenorizve: egyetlen run_dir-ben jonnek letre az artefaktok
- [x] Verify wrapper futtatva: `./scripts/verify.sh --report codex/reports/egyedi_solver/cli_run_solver_pipeline.md`
- [x] Kotelezo user parancs futtatva: `./scripts/check.sh`
