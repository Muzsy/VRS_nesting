# Codex checklist - cavity_t5_result_normalizer_expansion

- [x] AGENTS.md + Codex szabalyok + T5 canvas/YAML/prompt atnezve
- [x] `worker/result_normalizer.py` v2 agban opcionalis `cavity_plan.json` betoltes implementalva
- [x] `enabled=false` vagy hianyzo cavity plan eseten legacy v2 viselkedes megtartva
- [x] Virtual parent `part_id` -> real `parent_part_revision_id` mapping implementalva
- [x] Internal child placement abszolut transzform implementalva (parent rotation + local transform)
- [x] Top-level child placement instance offset (`top_level_instance_base`) implementalva
- [x] Unplaced child instance offset implementalva
- [x] User-facing projectionben virtual part ID nem marad (`part_revision_id`/`instance_ids`)
- [x] Unit teszt keszult: `tests/worker/test_result_normalizer_cavity_plan.py`
- [x] T5 smoke keszult: `scripts/smoke_cavity_t5_result_normalizer_expansion.py`
- [x] `python3 -m pytest -q tests/worker/test_result_normalizer_cavity_plan.py` PASS
- [x] `python3 scripts/smoke_cavity_t5_result_normalizer_expansion.py` PASS
- [x] `python3 scripts/smoke_h1_e6_t1_result_normalizer_h1_minimum.py` PASS
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/cavity_t5_result_normalizer_expansion.md` PASS
