# Codex checklist - jagua_rs_feasibility_integration

## Kotelezo (felderites)

- [x] Elolvastam: `AGENTS.md`
- [x] Elolvastam: `docs/codex/overview.md`
- [x] Elolvastam: `docs/codex/yaml_schema.md`
- [x] Elolvastam: `docs/codex/report_standard.md`
- [x] Elolvastam: `canvases/egyedi_solver/jagua_rs_feasibility_integration.md`
- [x] Elolvastam: `codex/goals/canvases/egyedi_solver/fill_canvas_jagua_rs_feasibility_integration.yaml`

## Kotelezo (implementacio)

- [x] Frissult: `rust/vrs_solver/Cargo.toml` (`jagua-rs = 0.6.4`)
- [x] Frissult: `rust/vrs_solver/Cargo.lock` (uj dependency graph)
- [x] Frissult: `rust/vrs_solver/src/main.rs` (`jagua-rs` primitive + `CollidesWith` usage)
- [x] Feasibility check contain/hole-edge ellenorzes jagua geometriaval fut

## Minosegkapu

- [x] Lefutott: `./scripts/verify.sh --report codex/reports/egyedi_solver/jagua_rs_feasibility_integration.md`
- [x] Letrejott/frissult: `codex/reports/egyedi_solver/jagua_rs_feasibility_integration.verify.log`
- [x] Report AUTO_VERIFY blokk frissult
