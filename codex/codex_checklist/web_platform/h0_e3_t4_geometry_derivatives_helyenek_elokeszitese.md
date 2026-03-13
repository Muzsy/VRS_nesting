# Codex checklist - h0_e3_t4_geometry_derivatives_helyenek_elokeszitese

- [x] Canvas + goal YAML + run prompt artefaktok elerhetoek
- [x] Letrejott a bazis migracio: `supabase/migrations/20260312007000_h0_e3_t4_geometry_derivatives_helyenek_elokeszitese.sql`
- [x] A migracio letrehozza az `app.geometry_derivatives` tablat
- [x] A derivative rekord visszavezetheto source `app.geometry_revisions` rekordra
- [x] A tabla hasznalja az `app.geometry_derivative_kind` enumot
- [x] A payload + version + hash mezok biztositottak
- [x] A `(geometry_revision_id, derivative_kind)` uniqueness vedelme letrejott
- [x] A migracio nem hoz letre binding/run/export tablakat
- [x] A task nem vezet be RLS policyt
- [x] Architecture + H0 roadmap minimal docs szinkron megtortent
- [x] `./scripts/verify.sh --report codex/reports/web_platform/h0_e3_t4_geometry_derivatives_helyenek_elokeszitese.md` PASS
- [x] Report DoD -> Evidence matrix kitoltve
