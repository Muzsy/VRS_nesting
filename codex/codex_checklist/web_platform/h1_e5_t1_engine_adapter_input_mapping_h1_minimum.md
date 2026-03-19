# Codex checklist - h1_e5_t1_engine_adapter_input_mapping_h1_minimum

- [x] Canvas + goal YAML + run prompt artefaktok elerhetoek
- [x] Keszult explicit `worker/engine_adapter_input.py` helper modul
- [x] A helper canonical run snapshotbol epiti a solver inputot
- [x] A solver input a `docs/solver_io_contract.md` szerinti `solver_input.json` v1 contractot koveti
- [x] A part geometry a `nesting_canonical` derivative truth-bol jon (`outer_ring/hole_rings/bbox`)
- [x] A stocks a snapshot `sheets_manifest_jsonb` alapjan keszulnek
- [x] A rotation policy mapping explicit, determinisztikus es nem-tamogatott policy eseten hibazik
- [x] A snapshot builder minimalisan bovult a snapshot-only mappinghez szukseges geometry payloaddal
- [x] Keszult task-specifikus smoke script: `scripts/smoke_h1_e5_t1_engine_adapter_input_mapping_h1_minimum.py`
- [x] `python3 -m py_compile worker/engine_adapter_input.py worker/main.py api/services/run_snapshot_builder.py api/services/run_creation.py scripts/smoke_h1_e5_t1_engine_adapter_input_mapping_h1_minimum.py` PASS
- [x] `python3 scripts/smoke_h1_e5_t1_engine_adapter_input_mapping_h1_minimum.py` PASS
- [x] `./scripts/verify.sh --report codex/reports/web_platform/h1_e5_t1_engine_adapter_input_mapping_h1_minimum.md` PASS
- [x] Report DoD -> Evidence matrix kitoltve
