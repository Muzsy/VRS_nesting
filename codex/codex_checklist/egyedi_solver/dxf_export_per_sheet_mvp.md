# Codex checklist - dxf_export_per_sheet_mvp

## Kotelezo (felderites)

- [x] Elolvastam: `AGENTS.md`
- [x] Elolvastam: `canvases/egyedi_solver/dxf_export_per_sheet_mvp.md`
- [x] Elolvastam: `codex/goals/canvases/egyedi_solver/fill_canvas_dxf_export_per_sheet_mvp.yaml`
- [x] Ellenoriztem a kapcsolodo futasi artifact konvenciot (`runs/<run_id>/...`)

## Kotelezo (implementacio)

- [x] Letrejott: `vrs_nesting/dxf/exporter.py`
- [x] Letrejott: `samples/project_rect_1000x2000.json`
- [x] Sheet-enkenti naming implementalva (`sheet_001.dxf`, ...)
- [x] Ures sheet export kihagyas implementalva
- [x] Export summary metrikak implementalva (`sheet_metrics`, `exported_count`)

## Minosegkapu

- [x] Lefutott: `./scripts/verify.sh --report codex/reports/egyedi_solver/dxf_export_per_sheet_mvp.md`
- [x] Letrejott/frissult: `codex/reports/egyedi_solver/dxf_export_per_sheet_mvp.verify.log`
- [x] Report AUTO_VERIFY blokk frissult
