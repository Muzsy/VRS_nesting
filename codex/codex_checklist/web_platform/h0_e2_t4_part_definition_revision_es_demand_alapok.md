# Codex checklist - h0_e2_t4_part_definition_revision_es_demand_alapok

- [x] Canvas + goal YAML + run prompt artefaktok elerhetoek
- [x] Letrejott a bazis migracio: `supabase/migrations/20260310233000_h0_e2_t4_part_definition_revision_es_demand_alapok.sql`
- [x] A migracio letrehozza az `app.part_definitions`, `app.part_revisions`, `app.project_part_requirements` tablakat
- [x] A demand tabla a `part_revisions` vilagra ul, nem kozvetlenul a definitionre
- [x] PK/FK kapcsolatok es minimalis indexek letrejottek
- [x] A task nem hoz letre geometry/file/sheet/run/remnant/export domain tablakat
- [x] A task nem vezet be RLS policyt
- [x] Architecture + H0 roadmap minimal docs szinkron megtortent
- [x] `./scripts/verify.sh --report codex/reports/web_platform/h0_e2_t4_part_definition_revision_es_demand_alapok.md` PASS
- [x] Report DoD -> Evidence matrix kitoltve
