# Codex checklist - export_original_geometry_block_insert_impl

## Kotelezo (felderites)

- [x] Elolvastam: `AGENTS.md`
- [x] Elolvastam: `canvases/egyedi_solver/export_original_geometry_block_insert_impl.md`
- [x] Elolvastam: `codex/goals/canvases/egyedi_solver/fill_canvas_export_original_geometry_block_insert_impl.yaml`
- [x] Felmerve: DXF exporter + dxf pipeline mapping artefaktumok

## Kotelezo (implementacio)

- [x] Frissult: `canvases/egyedi_solver/export_original_geometry_block_insert_impl.md` (felderitesi pontositas)
- [x] Frissult: `vrs_nesting/sparrow/input_generator.py` (source mapping mezok)
- [x] Frissult: `vrs_nesting/sparrow/multi_sheet_wrapper.py` (`source_geometry_map.json` + `geometry_mode: source`)
- [x] Frissult: `vrs_nesting/dxf/exporter.py` (`--geometry-mode approx|source`, source BLOCK/INSERT export)
- [x] Uj: `scripts/smoke_export_original_geometry_block_insert.py`
- [x] Frissult: `scripts/check.sh` (uj smoke bekotve)

## Minosegkapu

- [x] Lefutott: `./scripts/verify.sh --report codex/reports/egyedi_solver/export_original_geometry_block_insert_impl.md`
- [x] Letrejott/frissult: `codex/reports/egyedi_solver/export_original_geometry_block_insert_impl.verify.log`
- [x] Lefutott kulon: `./scripts/check.sh`
