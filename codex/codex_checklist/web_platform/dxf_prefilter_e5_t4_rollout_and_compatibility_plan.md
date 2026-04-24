# Codex checklist - dxf_prefilter_e5_t4_rollout_and_compatibility_plan

- [x] Canvas + goal YAML + run prompt artefaktok elerhetoek
- [x] Elkeszult a kulon rollout/compatibility dokumentum (`docs/web_platform/architecture/dxf_prefilter_rollout_and_compatibility_plan.md`)
- [x] A dokumentum explicit nevezi a canonical flag-eket: `API_DXF_PREFLIGHT_REQUIRED`, `DXF_PREFLIGHT_REQUIRED`, `VITE_DXF_PREFLIGHT_ENABLED`
- [x] A dokumentum explicit kimondja, hogy rollout OFF eseten a `complete_upload` legacy direct geometry import helperre esik vissza
- [x] A dokumentum explicit kimondja, hogy rollout OFF eseten a `replace_file` gate-elve van
- [x] A dokumentum explicit kimondja, hogy rollout OFF eseten a DXF Intake route/CTA nem latszik
- [x] Van egyertelmu ON/OFF viselkedesi matrix
- [x] Van rollout stage modell + rollback/fallback eljaras
- [x] Van rovid, futtathato support/debug checklist
- [x] Van rollout metrika terv current-source megjegyzesekkel
- [x] Van legacy sunset kriterium szekcio helper removal nelkul
- [x] Elkeszult a task-specifikus structural smoke (`scripts/smoke_dxf_prefilter_e5_t4_rollout_and_compatibility_plan.py`)
- [x] `python3 scripts/smoke_dxf_prefilter_e5_t4_rollout_and_compatibility_plan.py` lefutott
- [x] `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e5_t4_rollout_and_compatibility_plan.md` lefuttatva
