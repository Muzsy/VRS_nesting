# Codex checklist - h2_e1_t2_project_manufacturing_selection

- [x] Canvas + goal YAML + run prompt a megfelelo helyen van
- [x] Letrejott a minimalis migration: `supabase/migrations/20260321233000_h2_e1_t2_project_manufacturing_selection.sql`
- [x] Letrejott a service: `api/services/project_manufacturing_selection.py`
- [x] Letrejottek a route-ok: `api/routes/project_manufacturing_selection.py` es `api/main.py` bekotes
- [x] Letrejott a task-specifikus smoke: `scripts/smoke_h2_e1_t2_project_manufacturing_selection.py`
- [x] `python3 -m py_compile api/services/project_manufacturing_selection.py api/routes/project_manufacturing_selection.py api/main.py scripts/smoke_h2_e1_t2_project_manufacturing_selection.py` PASS
- [x] `python3 scripts/smoke_h2_e1_t2_project_manufacturing_selection.py` PASS
- [x] `./scripts/verify.sh --report codex/reports/web_platform/h2_e1_t2_project_manufacturing_selection.md` PASS
- [x] Report DoD -> Evidence matrix kitoltve
