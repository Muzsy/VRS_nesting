# Codex checklist - h0_e2_t5_sheet_definition_revision_es_project_input_alapok

- [x] Canvas + goal YAML + run prompt artefaktok elerhetoek
- [x] Letrejott a bazis migracio: `supabase/migrations/20260310240000_h0_e2_t5_sheet_definition_revision_es_project_input_alapok.sql`
- [x] A migracio letrehozza az `app.sheet_definitions`, `app.sheet_revisions`, `app.project_sheet_inputs` tablakat
- [x] A project input tabla a `sheet_revisions` vilagra ul, nem kozvetlenul a definitionre
- [x] A `current_revision_id` integritas kompozit FK-val vedett
- [x] PK/FK kapcsolatok es minimalis indexek letrejottek
- [x] A task nem hoz letre remnant/inventory/file/geometry/run/export domain tablakat
- [x] A task nem vezet be RLS policyt
- [x] Architecture + H0 roadmap minimal docs szinkron megtortent
- [x] `./scripts/verify.sh --report codex/reports/web_platform/h0_e2_t5_sheet_definition_revision_es_project_input_alapok.md` PASS
- [x] Report DoD -> Evidence matrix kitoltve
