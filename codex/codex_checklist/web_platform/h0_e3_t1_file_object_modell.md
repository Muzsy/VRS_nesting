# Codex checklist - h0_e3_t1_file_object_modell

- [x] Canvas + goal YAML + run prompt artefaktok elerhetoek
- [x] Letrejott a bazis migracio: `supabase/migrations/20260312001000_h0_e3_t1_file_object_modell.sql`
- [x] A migracio letrehozza az `app.file_objects` tablat
- [x] A tabla helyesen kapcsolodik az `app.projects` es `app.profiles` tablakhhoz
- [x] A storage hivatkozas egyedisege vedett
- [x] A migracio nem hoz letre geometry/review/derivative/run/export tablakat
- [x] A task nem vezet be RLS policyt
- [x] Architecture + H0 roadmap minimal docs szinkron megtortent
- [x] `./scripts/verify.sh --report codex/reports/web_platform/h0_e3_t1_file_object_modell.md` PASS
- [x] Report DoD -> Evidence matrix kitoltve
