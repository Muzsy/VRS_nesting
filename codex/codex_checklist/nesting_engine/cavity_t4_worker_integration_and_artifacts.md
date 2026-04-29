# Codex checklist - cavity_t4_worker_integration_and_artifacts

- [x] AGENTS.md + Codex szabalyok + T4 canvas/YAML/prompt atnezve
- [x] T3 prepack modul worker futasi utvonalba bekotve (`nesting_engine_v2` branch)
- [x] Prepack policy eseten futtatott solver payload hash a prepackelt inputbol szamolodik
- [x] `solver_input_snapshot.json` prepack modban a tenyleges futtatott payload
- [x] `cavity_plan.json` input sidecar iras + upload implementalva
- [x] `cavity_plan` artifact regisztracio implementalva
- [x] Engine meta payload cavity prepack audit summaryt tartalmaz
- [x] Prepack summary log mezok implementalva (enabled/virtual/internal/qty/holes removed)
- [x] Non-prepack futas visszafele kompatibilis maradt
- [x] Solver input artifact regisztracio kompatibilis fallbackkel fake clientes smoke-okhoz
- [x] T4 smoke keszult: `scripts/smoke_cavity_t4_worker_integration_and_artifacts.py`
- [x] `python3 scripts/smoke_cavity_t4_worker_integration_and_artifacts.py` PASS
- [x] `python3 scripts/smoke_h1_e5_t1_engine_adapter_input_mapping_h1_minimum.py` PASS
- [x] `python3 scripts/smoke_h1_e5_t2_solver_process_futtatas_h1_minimum.py` PASS
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/cavity_t4_worker_integration_and_artifacts.md` PASS
