# Codex checklist - h2_e3_t1_cut_rule_set_model

- [x] Canvas + goal YAML + run prompt a megfelelo helyen van
- [x] Letrejott a minimalis migration: `supabase/migrations/20260322010000_h2_e3_t1_cut_rule_set_model.sql`
- [x] Letrejott a service: `api/services/cut_rule_sets.py`
- [x] Letrejott a route: `api/routes/cut_rule_sets.py`
- [x] `api/main.py` bovitve a cut_rule_sets routerrel
- [x] Letrejott a task-specifikus smoke: `scripts/smoke_h2_e3_t1_cut_rule_set_model.py`
- [x] `python3 -m py_compile api/services/cut_rule_sets.py api/routes/cut_rule_sets.py api/main.py scripts/smoke_h2_e3_t1_cut_rule_set_model.py` PASS
- [x] `python3 scripts/smoke_h2_e3_t1_cut_rule_set_model.py` PASS (24/24 test)
- [x] `./scripts/verify.sh --report codex/reports/web_platform/h2_e3_t1_cut_rule_set_model.md` PASS
- [x] Report DoD -> Evidence matrix kitoltve
