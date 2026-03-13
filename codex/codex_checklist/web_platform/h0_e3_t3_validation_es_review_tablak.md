# Codex checklist - h0_e3_t3_validation_es_review_tablak

- [x] Canvas + goal YAML + run prompt artefaktok elerhetoek
- [x] Letrejott a bazis migracio: `supabase/migrations/20260312005000_h0_e3_t3_validation_es_review_tablak.sql`
- [x] A migracio letrehozza az `app.geometry_validation_reports` tablat
- [x] A migracio letrehozza az `app.geometry_review_actions` tablat
- [x] A validation report geometry lineage explicit FK-val vedett
- [x] A review action same-geometry validation report-hivatkozasat kompozit FK vedi
- [x] PK/FK kapcsolatok, audit-integritas es alap indexek letrejottek
- [x] A migracio nem hoz letre derivative/binding/run/export tablakat
- [x] A task nem vezet be RLS policyt
- [x] Architecture + H0 roadmap minimal docs szinkron megtortent
- [x] `./scripts/verify.sh --report codex/reports/web_platform/h0_e3_t3_validation_es_review_tablak.md` PASS
- [x] Report DoD -> Evidence matrix kitoltve
