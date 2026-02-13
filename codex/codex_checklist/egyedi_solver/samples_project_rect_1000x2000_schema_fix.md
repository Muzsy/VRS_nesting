# Codex checklist - samples_project_rect_1000x2000_schema_fix

- [x] A strict schema forras ellenorizve: `vrs_nesting/project/model.py`
- [x] A strict parse-t toro korabbi ok rogzitve a canvasban (`solver_output_example` top-level extra kulcs)
- [x] `samples/project_rect_1000x2000.json` futtathato strict minta maradt
- [x] Extra peldaadat kulon fajlba mentve: `samples/project_rect_1000x2000_with_examples.json`
- [x] Manualis smoke: `VRS_SOLVER_BIN=rust/vrs_solver/target/release/vrs_solver python3 -m vrs_nesting.cli run samples/project_rect_1000x2000.json`
- [x] Verify wrapper futtatva: `./scripts/verify.sh --report codex/reports/egyedi_solver/samples_project_rect_1000x2000_schema_fix.md`
- [x] Kotelezo vegso gate futtatva: `./scripts/check.sh`
