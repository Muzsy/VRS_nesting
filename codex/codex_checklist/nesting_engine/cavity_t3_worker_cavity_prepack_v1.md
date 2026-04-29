# Codex checklist - cavity_t3_worker_cavity_prepack_v1

- [x] AGENTS.md + Codex szabalyok + T3 canvas/YAML/prompt atnezve
- [x] Uj pure worker modul keszult: `worker/cavity_prepack.py`
- [x] Public API implementalva: `build_cavity_prepacked_engine_input(...)`
- [x] Modul DB/API/file write mentes
- [x] Disabled mode visszafele kompatibilis (`enabled=false`)
- [x] Virtual parent partok `quantity=1` es `holes_points_mm=[]`
- [x] Child quantity reservation + `quantity_delta` + `instance_bases` implementalva
- [x] Child holes v1 unsupported diagnostic jelen van
- [x] Determinisztikus candidate sorrend + tie-breaker implementalva
- [x] Nincs OTSZOG/NEGYZET/MACSKANYELV hardcode
- [x] Unit teszt csomag keszult: `tests/worker/test_cavity_prepack.py`
- [x] Task-specifikus smoke keszult: `scripts/smoke_cavity_t3_worker_cavity_prepack_v1.py`
- [x] `python3 -m pytest -q tests/worker/test_cavity_prepack.py` PASS
- [x] `python3 scripts/smoke_cavity_t3_worker_cavity_prepack_v1.py` PASS
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/cavity_t3_worker_cavity_prepack_v1.md` PASS
