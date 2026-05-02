# Codex checklist - cavity_v2_t05_holed_child_outer_proxy

- [x] AGENTS.md + T05 canvas/YAML/prompt beolvasva
- [x] `_candidate_children()`-ben a holed child `continue` eltavolitva
- [x] Diagnostic kod cserelve: `child_has_holes_outer_proxy_used` (+ `hole_count`)
- [x] `_rotation_shapes()` outer-only proxy megjegyzes frissitve
- [x] `test_holed_child_enters_candidate_list` letrehozva
- [x] `test_holed_child_diagnostic_is_outer_proxy_used` letrehozva
- [x] `test_v1_solid_child_behavior_unchanged` letrehozva
- [x] `python3 -m pytest -q tests/worker/test_cavity_prepack.py` PASS
- [x] `python3 -m pytest -q tests/worker/test_cavity_prepack.py -k "holed_child"` PASS
- [x] Report DoD -> Evidence matrix kitoltve
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/cavity_v2_t05_holed_child_outer_proxy.md` PASS
