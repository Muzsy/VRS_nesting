# Codex checklist - h1_e4_t1_run_snapshot_builder_h1_minimum

- [x] Canvas + goal YAML + run prompt artefaktok elerhetoek
- [x] Keszult explicit `api/services/run_snapshot_builder.py` service
- [x] A service a meglevo H0/H1 tablavilagra epul (`projects`, `project_settings`, `project_technology_setups`, `project_part_requirements`, `part_*`, `project_sheet_inputs`, `sheet_*`, `geometry_derivatives`)
- [x] A builder project-level technology setupot valaszt explicit guardokkal
- [x] A builder aktiv project part requirementeket olvas es validal
- [x] A builder aktiv project sheet inputokat olvas es validal
- [x] A snapshot payload tartalmazza a H0-kompatibilis manifest blokkokat + `snapshot_hash_sha256` mezot
- [x] A builder csak `approved` part revision + explicit derivative bindinget enged tovabb
- [x] A hash kepzes determinisztikus ugyanarra az inputra
- [x] Nem keszult run route/queue/worker valtoztatas ebben a taskban
- [x] Letrejott task-specifikus smoke script: `scripts/smoke_h1_e4_t1_run_snapshot_builder_h1_minimum.py`
- [x] `python3 -m py_compile api/services/run_snapshot_builder.py scripts/smoke_h1_e4_t1_run_snapshot_builder_h1_minimum.py` PASS
- [x] `python3 scripts/smoke_h1_e4_t1_run_snapshot_builder_h1_minimum.py` PASS
- [x] `./scripts/verify.sh --report codex/reports/web_platform/h1_e4_t1_run_snapshot_builder_h1_minimum.md` PASS
- [x] Report DoD -> Evidence matrix kitoltve
