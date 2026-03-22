# Codex checklist - h2_e3_t3_rule_matching_logic

- [x] Canvas + goal YAML + run prompt a megfelelo helyen van
- [x] Letrejott a matching service: `api/services/cut_rule_matching.py`
- [x] A matching explicit `cut_rule_set_id` inputtal dolgozik, nem resolver
- [x] A `feature_class` fallback egyertelmu es tesztelt
- [x] A `min_contour_length_mm` / `max_contour_length_mm` szures mukodik
- [x] A tie-break determinisztikus es dokumentalt
- [x] Unmatched contour eseten tiszta indok kerul visszaadasra
- [x] A task nem ir vissza truth tablaba
- [x] Letrejott a task-specifikus smoke: `scripts/smoke_h2_e3_t3_rule_matching_logic.py`
- [x] `python3 -m py_compile api/services/cut_rule_matching.py scripts/smoke_h2_e3_t3_rule_matching_logic.py` PASS
- [x] `python3 scripts/smoke_h2_e3_t3_rule_matching_logic.py` PASS (37/37 test)
- [x] `./scripts/verify.sh --report codex/reports/web_platform/h2_e3_t3_rule_matching_logic.md` PASS
- [x] Report DoD -> Evidence matrix kitoltve
