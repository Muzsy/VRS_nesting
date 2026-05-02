# Codex checklist - cavity_v2_t06_recursive_cavity_fill

- [x] AGENTS.md + T06 canvas/YAML/prompt beolvasva
- [x] `_CavityRecord` dataclass bevezetve
- [x] `_build_usable_cavity_records()` implementalva
- [x] `_rank_cavity_child_candidates()` implementalva
- [x] `_fill_cavity_recursive()` implementalva (max depth + cycle vedelem)
- [x] `build_cavity_prepacked_engine_input_v2()` implementalva
- [x] `build_cavity_prepacked_engine_input_v2` exportalva (`__all__`)
- [x] V2 tesztek hozzaadva (`matrjoska`, `cycle`, `quantity`, `disabled`, `max_depth`)
- [x] `python3 -c "from worker.cavity_prepack import build_cavity_prepacked_engine_input_v2; print('v2 entrypoint OK')"` PASS
- [x] `python3 -m pytest -q tests/worker/test_cavity_prepack.py -k "v2"` PASS
- [x] `python3 -m pytest -q tests/worker/test_cavity_prepack.py` PASS
- [x] Report DoD -> Evidence matrix kitoltve
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/cavity_v2_t06_recursive_cavity_fill.md` PASS
