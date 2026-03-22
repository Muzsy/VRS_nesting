# Codex checklist - h2_e4_t2_manufacturing_plan_builder

- [x] Canvas + goal YAML + run prompt a megfelelo helyen van
- [x] Letrejott a migracio: `supabase/migrations/20260322023000_h2_e4_t2_manufacturing_plan_builder.sql`
- [x] `app.run_manufacturing_plans` tabla letezik a megfelelo FK-lancokkal
- [x] `app.run_manufacturing_contours` tabla letezik audit FK-lancokkal (`geometry_derivative_id`, `contour_class_id`, `matched_rule_id`)
- [x] A builder a run snapshot + run projection + manufacturing derivative + contour classification + explicit cut rule set alapjan plan-t tud epiteni
- [x] A builder nem live project manufacturing selectionbol dolgozik
- [x] A builder nem talal ki cut rule set resolver logikat (explicit `cut_rule_set_id` input)
- [x] A contour rekordok matched rule hivatkozast es alap entry/lead/cut-order infot tartalmaznak
- [x] A builder idempotens a persisted reteg szintjen
- [x] A task nem ir vissza korabbi truth tablaba
- [x] A task nem nyit preview / postprocessor / export scope-ot
- [x] Letrejott a task-specifikus smoke: `scripts/smoke_h2_e4_t2_manufacturing_plan_builder.py`
- [x] `python3 -m py_compile api/services/manufacturing_plan_builder.py scripts/smoke_h2_e4_t2_manufacturing_plan_builder.py` PASS
- [x] `python3 scripts/smoke_h2_e4_t2_manufacturing_plan_builder.py` PASS (39/39)
- [x] `./scripts/verify.sh --report codex/reports/web_platform/h2_e4_t2_manufacturing_plan_builder.md` PASS
- [x] Report DoD -> Evidence matrix kitoltve
