# Codex checklist - h3_quality_t3_snapshot_to_nesting_engine_v2_adapter

- [x] Canvas + goal YAML + run prompt artefaktok elerhetoek
- [x] Keszult explicit snapshot -> `nesting_engine_v2` input builder (`build_nesting_engine_input_from_snapshot`)
- [x] Keszult v2 canonical hash helper (`nesting_engine_input_sha256`)
- [x] A v1 builder ut (`build_solver_input_from_snapshot`) erintetlenul megmaradt
- [x] A v2 rotacio policy explicit veges halmazt kepez (`rotation_step_deg`) es `allow_free_rotation=true` fail-fast
- [x] A sheet mapping single-sheet-family fail-fast szaballyal mukodik (elteto sheet tippeknel hiba)
- [x] Keszult task-specifikus smoke script: `scripts/smoke_h3_quality_t3_snapshot_to_nesting_engine_v2_adapter.py`
- [x] `python3 -m py_compile worker/engine_adapter_input.py scripts/smoke_h3_quality_t3_snapshot_to_nesting_engine_v2_adapter.py` PASS
- [x] `python3 scripts/smoke_h3_quality_t3_snapshot_to_nesting_engine_v2_adapter.py` PASS
- [x] `./scripts/verify.sh --report codex/reports/web_platform/h3_quality_t3_snapshot_to_nesting_engine_v2_adapter.md` PASS
- [x] Report DoD -> Evidence matrix kitoltve
