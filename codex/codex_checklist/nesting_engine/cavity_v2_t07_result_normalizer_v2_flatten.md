# Codex checklist - cavity_v2_t07_result_normalizer_v2_flatten

- [x] AGENTS.md + T07 canvas/YAML/prompt beolvasva
- [x] `_compose_cavity_transform()` implementalva
- [x] `_count_diagnostics_by_code()` implementalva
- [x] `_flatten_cavity_plan_v2_tree()` implementalva (rekurziv)
- [x] `_normalize_solver_output_projection_v2()` v2 `placement_trees` ag implementalva
- [x] V2 quantity mismatch hard-fail (`CAVITY_QUANTITY_MISMATCH`) implementalva
- [x] V2 metadata `cavity_tree_depth` kitoltes implementalva
- [x] V2 tesztek hozzaadva (single-level, matrjoska, rotated, mismatch)
- [x] `python3 -c "from worker.result_normalizer import placement_transform_point; print('normalizer OK')"` PASS
- [x] `python3 -m pytest -q tests/worker/test_result_normalizer_cavity_plan.py -k "v2"` PASS
- [x] `python3 -m pytest -q tests/worker/test_result_normalizer_cavity_plan.py` PASS
- [x] Report DoD -> Evidence matrix kitoltve
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/cavity_v2_t07_result_normalizer_v2_flatten.md` PASS
