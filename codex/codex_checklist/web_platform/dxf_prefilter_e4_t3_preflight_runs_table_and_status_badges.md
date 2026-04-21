# Codex checklist - dxf_prefilter_e4_t3_preflight_runs_table_and_status_badges

- [x] Canvas + goal YAML + run prompt artefaktok elérhetőek
- [x] Backend `latest_preflight_summary` projection bővítve `summary_jsonb` alapú issue/repair mezőkkel
- [x] Backend `recommended_action` mapping bekerült stabil enum-like értékekkel
- [x] `include_preflight_summary=false` viselkedés változatlan maradt
- [x] Frontend `ProjectFileLatestPreflightSummary` típus bővítve T3 mezőkkel
- [x] Frontend API normalizer bővítve optional-safe számláló/recommended_action mappinggel
- [x] `DxfIntakePage` latest runs table elkészült külön run/issue/repair/acceptance badge helper-ekkel
- [x] Route-level teszt frissítve projection mezők + latest-run kiválasztás + hiányos summary esetre
- [x] Elkészült deterministic T3 smoke (`scripts/smoke_dxf_prefilter_e4_t3_preflight_runs_table_and_status_badges.py`)
- [x] Kötelező futtatások lefutottak (`py_compile`, `pytest`, smoke, `npm --prefix frontend run build`)
- [x] `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e4_t3_preflight_runs_table_and_status_badges.md` lefutott és report AUTO_VERIFY frissült
