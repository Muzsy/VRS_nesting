# Codex checklist - h0_e2_t3_technology_domain_alapok

- [x] Canvas + goal YAML + run prompt artefaktok elerhetoek
- [x] Letrejott a bazis migracio: `supabase/migrations/20260310230000_h0_e2_t3_technology_domain_alapok.sql`
- [x] A migracio letrehoz reusable technology preset tablavilagot (`app.technology_presets`)
- [x] A migracio letrehoz projekt-szintu technology setup tablavilagot (`app.project_technology_setups`)
- [x] A setup tabla megfelelo FK-val kapcsolodik az `app.projects` tablaho
- [x] Alap FK/index struktura a technology domainben letrejott
- [x] A task nem hoz letre part/file/revision/run/remnant/export domain tablakat
- [x] A task nem vezet be RLS policyt
- [x] Architecture + H0 roadmap minimal docs szinkron megtortent
- [x] `./scripts/verify.sh --report codex/reports/web_platform/h0_e2_t3_technology_domain_alapok.md` PASS
- [x] Report DoD -> Evidence matrix kitoltve
