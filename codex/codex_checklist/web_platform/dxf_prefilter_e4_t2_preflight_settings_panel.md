# Codex checklist - dxf_prefilter_e4_t2_preflight_settings_panel

- [x] Canvas + goal YAML + run prompt artefaktok elérhetőek
- [x] Frontend intake settings panel elkészült explicit draft shape-pel és reset művelettel
- [x] Frontend API/types boundary bővítve optional `rules_profile_snapshot_jsonb` támogatással
- [x] `complete_upload` route optional snapshot bridge elkészült
- [x] Runtime `rules_profile` plumbing elkészült (nincs `rules_profile=None` hardcode)
- [x] Runtime unit teszt frissítve rules_profile plumbing coverage-re
- [x] Készült route-level deterministic teszt a complete_upload snapshot továbbítására
- [x] Készült deterministic smoke a settings panel + plumbing szerződésre
- [x] Célzott ellenőrzések lefutottak (`py_compile`, `pytest`, smoke, `npm --prefix frontend run build`)
- [x] `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e4_t2_preflight_settings_panel.md` lefutott és report AUTO_VERIFY frissült
