# Codex checklist - h0_e2_t2_core_projekt_es_profile_tablak

- [x] Canvas + goal YAML + run prompt artefaktok elerhetoek
- [x] Letrejott a bazis migracio: `supabase/migrations/20260310223000_h0_e2_t2_profiles_projects_project_settings.sql`
- [x] A migracio letrehozza az `app.profiles`, `app.projects`, `app.project_settings` tablakat
- [x] PK/FK kapcsolatok a core ownership modell szerint vannak beallitva
- [x] Alap indexek letrejottek (`projects.owner_user_id`, `projects.lifecycle`)
- [x] A task nem hoz letre technology/file/revision/run domain tablakat
- [x] A task nem vezet be RLS policyt vagy auth auto-provisioning logikat
- [x] Architecture + H0 roadmap minimal docs szinkron megtortent
- [x] `./scripts/verify.sh --report codex/reports/web_platform/h0_e2_t2_core_projekt_es_profile_tablak.md` PASS
- [x] Report DoD -> Evidence matrix kitoltve
