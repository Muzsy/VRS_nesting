# Codex checklist - h0_e3_t2_geometry_revision_modell

- [x] Canvas + goal YAML + run prompt artefaktok elerhetoek
- [x] Letrejott a bazis migracio: `supabase/migrations/20260312003000_h0_e3_t2_geometry_revision_modell.sql`
- [x] A migracio letrehozza az `app.geometry_revisions` tablat
- [x] A geometry revision rekord visszavezetheto source `app.file_objects` rekordra
- [x] A canonical format version tarolasa es a JSON-alapu canonical geometry hely biztositott
- [x] PK/FK kapcsolatok, revision-integritas es alap indexek letrejottek
- [x] A migracio nem hoz letre validation/review/derivative/run/export tablakat
- [x] A task nem vezet be RLS policyt
- [x] Architecture + H0 roadmap minimal docs szinkron megtortent
- [x] `./scripts/verify.sh --report codex/reports/web_platform/h0_e3_t2_geometry_revision_modell.md` PASS
- [x] Report DoD -> Evidence matrix kitoltve
