# Codex checklist - h0_e5_t3_artifact_es_projection_modellek

- [x] Canvas + goal YAML + run prompt artefaktok elerhetoek
- [x] Letrejott a bazis migracio: `supabase/migrations/20260314110000_h0_e5_t3_artifact_es_projection_modellek.sql`
- [x] A migracio letrehozza az `app.run_artifacts` tablat
- [x] A migracio letrehozza az `app.run_layout_sheets` tablat
- [x] A migracio letrehozza az `app.run_layout_placements` tablat
- [x] A migracio letrehozza az `app.run_layout_unplaced` tablat
- [x] A migracio letrehozza az `app.run_metrics` tablat
- [x] Az artifact tabla hasznalja az `app.artifact_kind` enumot
- [x] Az artifact es projection reteg fizikailag kulon marad
- [x] A task szandekosan nem hoz letre kulon `app.run_results` tablat
- [x] A task nem vezet be storage bucket policyt vagy RLS policyt
- [x] Minimal docs szinkron megtortent a T3 source-of-truth iranyhoz
- [x] A stale `public.run_layout_*`, `public.run_metrics` es `run_results` maradvanyok javitva
- [x] `./scripts/verify.sh --report codex/reports/web_platform/h0_e5_t3_artifact_es_projection_modellek.md` PASS
- [x] Report DoD -> Evidence matrix kitoltve
