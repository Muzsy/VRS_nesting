# Codex Checklist - trial_run_tool_new_project_technology_setup_fix

**Task slug:** `trial_run_tool_new_project_technology_setup_fix`
**Canvas:** `canvases/trial_run_tool_fix/trial_run_tool_new_project_technology_setup_fix.md`
**Goal YAML:** `codex/goals/canvases/trial_run_tool_fix/fill_canvas_trial_run_tool_new_project_technology_setup_fix.yaml`

---

## Felderites

- [x] `AGENTS.md` elolvasva
- [x] `docs/codex/overview.md` elolvasva
- [x] `docs/codex/yaml_schema.md` elolvasva
- [x] `docs/codex/report_standard.md` elolvasva
- [x] `docs/qa/testing_guidelines.md` elolvasva
- [x] `canvases/trial_run_tool/trial_run_tool_cli_core.md` es `canvases/trial_run_tool/trial_run_tool_tkinter_gui.md` atnezve
- [x] `scripts/trial_run_tool_core.py`, `scripts/run_trial_run_tool.py`, `scripts/trial_run_tool_gui.py` atnezve
- [x] `scripts/smoke_trial_run_tool_cli_core.py`, `scripts/smoke_trial_run_tool_tkinter_gui.py` atnezve
- [x] `api/services/run_snapshot_builder.py` technology setup prerequisite ellenorizve
- [x] `supabase/migrations/20260310230000_h0_e2_t3_technology_domain_alapok.sql` schema mezok ellenorizve

## Implementacio

- [x] Uj projekt modban a core approved+default `project_technology_setups` seedelest vegez
- [x] A technology setup mezok expliciten kezeltek, migration schema-val osszhangban
- [x] Korai, ertheto hiba uj projekt modban, ha hianyzik `SUPABASE_URL` vagy `SUPABASE_ANON_KEY`
- [x] `project_technology_setup.json` evidence fajl es `technology_setup_input.json` input snapshot letrejon
- [x] A summary jelzi, seedelt-e setupot, milyen azonositoval es kulcsmezokkel
- [x] CLI parameterkeszlet technology setup opciokkal bovitve
- [x] GUI uj projekt modban technology setup mezoket kezel es prerequisite-eket validal
- [x] Existing project modban nincs felesleges setup-seed kenyszer
- [x] Core smoke biztosítja, hogy setup nelkul uj projekt modban nincs `POST /runs`
- [x] GUI smoke validalja az uj setup workflow-t es a new/existing mod kulonbseget

## Ellenorzes

- [x] `python3 -B -m py_compile scripts/trial_run_tool_core.py scripts/run_trial_run_tool.py scripts/trial_run_tool_gui.py scripts/smoke_trial_run_tool_cli_core.py scripts/smoke_trial_run_tool_tkinter_gui.py` PASS
- [x] `python3 -B scripts/smoke_trial_run_tool_cli_core.py` PASS
- [x] `python3 -B scripts/smoke_trial_run_tool_tkinter_gui.py` PASS

## Gate

- [x] `./scripts/verify.sh --report codex/reports/trial_run_tool_fix/trial_run_tool_new_project_technology_setup_fix.md` PASS
