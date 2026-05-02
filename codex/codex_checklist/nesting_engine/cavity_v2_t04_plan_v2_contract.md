# Codex checklist - cavity_v2_t04_plan_v2_contract

- [x] AGENTS.md + T04 canvas/YAML/prompt beolvasva
- [x] `_PLAN_VERSION_V2 = "cavity_plan_v2"` bevezetve a `worker/cavity_prepack.py`-ban
- [x] `_PlacementTreeNode` dataclass bevezetve
- [x] `_empty_plan_v2()` helper bevezetve helyes v2 schema-val
- [x] `_load_enabled_cavity_plan()` elfogadja a `cavity_plan_v2` verziostringet
- [x] `docs/nesting_engine/cavity_prepack_contract_v2.md` letrehozva (placement_trees peldaval)
- [x] `python3 -m pytest -q tests/worker/test_cavity_prepack.py` PASS
- [x] `python3 -m pytest -q tests/worker/test_result_normalizer_cavity_plan.py` PASS
- [x] Report DoD -> Evidence matrix kitoltve
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/cavity_v2_t04_plan_v2_contract.md` PASS
