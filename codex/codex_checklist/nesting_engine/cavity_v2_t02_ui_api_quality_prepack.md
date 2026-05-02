# Codex checklist - cavity_v2_t02_ui_api_quality_prepack

- [x] AGENTS.md + T02 canvas/YAML/prompt beolvasva
- [x] `vrs_nesting/config/nesting_quality_profiles.py` registry ellenorizve (`quality_cavity_prepack` letezik)
- [x] `frontend/src/lib/types.ts` frissitve (`QualityProfileName` union + `cavity_prepack_summary` bovites)
- [x] `frontend/src/pages/NewRunPage.tsx` frissitve (uj quality option)
- [x] `QualityProfileName` tartalmazza a `"quality_cavity_prepack"` literalt
- [x] `cavity_prepack_summary` tipus frissitve
- [x] NewRunPage quality select tartalmazza a `quality_cavity_prepack` opciot
- [x] `quality_default` es `quality_aggressive` optionok erintetlenek maradtak
- [x] `cd frontend && npx tsc --noEmit` PASS
- [x] Report DoD -> Evidence matrix kitoltve
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/cavity_v2_t02_ui_api_quality_prepack.md` PASS
