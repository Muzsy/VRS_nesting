# Codex checklist - h2_e3_t2_cut_contour_rules_model

- [x] Canvas + goal YAML + run prompt a megfelelo helyen van
- [x] Letrejott a minimalis migration: `supabase/migrations/20260322013000_h2_e3_t2_cut_contour_rules_model.sql`
- [x] Letrejott a service: `api/services/cut_contour_rules.py`
- [x] Letrejott a route: `api/routes/cut_contour_rules.py`
- [x] `api/main.py` bovitve a cut_contour_rules routerrel
- [x] Letrejott a task-specifikus smoke: `scripts/smoke_h2_e3_t2_cut_contour_rules_model.py`
- [x] `python3 -m py_compile api/services/cut_contour_rules.py api/routes/cut_contour_rules.py api/main.py scripts/smoke_h2_e3_t2_cut_contour_rules_model.py` PASS
- [x] `python3 scripts/smoke_h2_e3_t2_cut_contour_rules_model.py` PASS (42/42 test)
- [x] `./scripts/verify.sh --report codex/reports/web_platform/h2_e3_t2_cut_contour_rules_model.md` PASS
- [x] Report DoD -> Evidence matrix kitoltve
