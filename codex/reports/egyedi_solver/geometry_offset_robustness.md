PASS_WITH_NOTES

## 1) Meta

- Task slug: `geometry_offset_robustness`
- Kapcsolodo canvas: `canvases/egyedi_solver/geometry_offset_robustness.md`
- Kapcsolodo goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_geometry_offset_robustness.yaml`
- Futas datuma: `2026-02-12`
- Fokusz terulet: `Docs | Planning`

## 2) Scope

### 2.1 Cel
- P1 scaffold a geometry offset robustussag taskhoz.
- Ellenorzesi terv + P0 regresszio-orseg rogzites.

### 2.2 Nem-cel
- Funkcionalis implementacio.
- Repo gate futtatas ebben a task-specifikus reportban.

## 3) Scaffold statusz

- Canvas + goal YAML + runner prompt letrehozva.
- Checklist letrehozva.
- Kotelezo kapu kesobbi futtatashoz rogzitve.

## 4) Kotelezo verify a kesobbi runhoz

- `./scripts/verify.sh --report codex/reports/egyedi_solver/geometry_offset_robustness.md`
- Vart log: `codex/reports/egyedi_solver/geometry_offset_robustness.verify.log`
