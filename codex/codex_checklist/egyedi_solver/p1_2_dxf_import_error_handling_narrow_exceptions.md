# Codex checklist - p1_2_dxf_import_error_handling_narrow_exceptions

## Kotelezo (felderites)

- [x] Elolvastam: `AGENTS.md`
- [x] Elolvastam: `canvases/egyedi_solver/p1_2_dxf_import_error_handling_narrow_exceptions.md`
- [x] Elolvastam: `codex/goals/canvases/egyedi_solver/fill_canvas_p1_2_dxf_import_error_handling_narrow_exceptions.yaml`
- [x] Feltarva: `vrs_nesting/dxf/importer.py` osszes `except Exception` helye

## Kotelezo (implementacio)

- [x] Frissult: `vrs_nesting/dxf/importer.py` (szukitett kivetelek, `except Exception` eliminacio)
- [x] Letrejott: `tests/test_dxf_importer_error_handling.py`
- [x] Letrejott/frissult: `codex/codex_checklist/egyedi_solver/p1_2_dxf_import_error_handling_narrow_exceptions.md`
- [x] Letrejott/frissult: `codex/reports/egyedi_solver/p1_2_dxf_import_error_handling_narrow_exceptions.md`

## DoD (canvas alapjan)

- [x] `vrs_nesting/dxf/importer.py` import utvonalon nincs `except Exception`
- [x] DXF read hibak `DXF_READ_FAILED` kodra fordulnak
- [x] Invalid ring hibak `DXF_INVALID_RING` kodra fordulnak
- [x] Unit tesztek lefedik: invalid ring -> `DXF_INVALID_RING`, invalid dxf -> `DXF_READ_FAILED`
- [x] Verify PASS: `./scripts/verify.sh --report codex/reports/egyedi_solver/p1_2_dxf_import_error_handling_narrow_exceptions.md`

## Minosegkapu

- [x] Lefutott: `./scripts/verify.sh --report codex/reports/egyedi_solver/p1_2_dxf_import_error_handling_narrow_exceptions.md`
- [x] Letrejott/frissult: `codex/reports/egyedi_solver/p1_2_dxf_import_error_handling_narrow_exceptions.verify.log`
- [x] Lefutott: `./scripts/check.sh`
