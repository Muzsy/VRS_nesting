# Codex checklist - cavity_v2_t03_prepack_guard_hole_free

- [x] AGENTS.md + T03 canvas/YAML/prompt beolvasva
- [x] `worker/cavity_prepack.py` atnezve es bovitve
- [x] `worker/main.py` prepack bekotesi pont azonositva es frissitve
- [x] `tests/worker/test_cavity_prepack.py` guard tesztekkel bovitve
- [x] `CavityPrepackGuardError` letezik es exportalva van
- [x] `validate_prepack_solver_input_hole_free` letezik es exportalva van
- [x] `CAVITY_PREPACK_TOP_LEVEL_HOLES_REMAIN` szerepel az exception uzenetben
- [x] Violalo part ID-k benne vannak az exception uzenetben
- [x] Guard csak `part_in_part == "prepack"` esetben fut
- [x] `python3 -m pytest -q tests/worker/test_cavity_prepack.py` PASS
- [x] `python3 -m pytest -q tests/worker/test_cavity_prepack.py -k "guard"` PASS
- [x] Report DoD -> Evidence matrix kitoltve
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/cavity_v2_t03_prepack_guard_hole_free.md` PASS
