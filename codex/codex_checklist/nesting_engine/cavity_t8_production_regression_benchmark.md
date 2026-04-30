# Codex checklist - cavity_t8_production_regression_benchmark

- [x] AGENTS.md + T8 canvas/YAML/prompt atnezve
- [x] T0-T7 kapcsolodo reportok atnezve (fokusz: T0 production replay blokk)
- [x] Production artifact URL blokk evidence ujraellenorizve (`downloaded_artifact_urls.json` 400 `artifact url failed`)
- [x] T8 smoke script keszult: `scripts/smoke_cavity_t8_production_regression_benchmark.py`
- [x] Legacy vs prepack engine replay evidence generalva: `tmp/cavity_t8_smoke_evidence.json`
- [x] Synthetic fallback benchmarkben legacy fallback `effective_placer=blf` bizonyitott
- [x] Synthetic fallback benchmarkben prepack `effective_placer=nfp` es fallback warning hianya bizonyitott
- [x] H3 benchmark harness profile matrix plan-only ellenorzes lefutott (`quality_default`, `quality_cavity_prepack`)
- [x] Rollout decision doksi frissitve: `docs/nesting_quality/cavity_prepack_rollout_decision.md`
- [x] `quality_default` ebben a taskban nem lett atallitva
- [x] `python3 scripts/smoke_cavity_t8_production_regression_benchmark.py` PASS
- [x] `python3 scripts/run_h3_quality_benchmark.py --plan-only --quality-profile quality_default --quality-profile quality_cavity_prepack --output tmp/cavity_t8_h3_plan_only.json` PASS
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/cavity_t8_production_regression_benchmark.md` PASS
