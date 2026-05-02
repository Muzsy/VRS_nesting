# Codex checklist - cavity_v2_t09_report_observability

- [x] AGENTS.md + T09 canvas/YAML/prompt beolvasva
- [x] `worker/result_normalizer.py` `metrics_jsonb.cavity_plan` v2 mezoi bovitve
- [x] V1 `cavity_plan` metrics formatum valtozatlan (csak `enabled`, `version`, `virtual_parent_count`)
- [x] `_count_diagnostics_by_code()` helper hasznalva a v2 `diagnostics_by_code` kitolteshez
- [x] `frontend/src/lib/types.ts` `cavity_prepack_summary` tipus bovitve (`max_cavity_depth`, `quantity_delta_summary`, `diagnostics_by_code`)
- [x] `frontend/src/pages/NewRunPage.tsx` cavity summary panel guard moge teve: `result?.metrics_jsonb?.cavity_plan?.enabled`
- [x] `tests/worker/test_result_normalizer_cavity_plan.py` uj tesztek: `test_v2_metrics_contain_cavity_plan_summary`, `test_v1_metrics_unchanged`
- [x] `python3 -m pytest -q tests/worker/test_result_normalizer_cavity_plan.py` PASS
- [x] `cd frontend && npx tsc --noEmit` PASS
- [x] Report DoD -> Evidence matrix kitoltve
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/cavity_v2_t09_report_observability.md` PASS
