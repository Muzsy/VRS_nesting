# Codex checklist - cavity_t2_runtime_profile_prepack_mode

- [x] AGENTS.md + Codex szabalyok + T2 canvas/YAML/prompt atnezve
- [x] `vrs_nesting/config/nesting_quality_profiles.py` bovitve `part_in_part=prepack` policyvel
- [x] `quality_cavity_prepack` profile felveve a quality registrybe
- [x] `quality_default` policy valtozatlanul maradt
- [x] Worker profile resolution audit mezok bovitve (requested/effective part-in-part + prepack flag)
- [x] Prepack policy eseten Rust CLI mapping `--part-in-part off`
- [x] Nincs Rust parser/choices bovites `prepack` ertekkel
- [x] Nincs geometry packer implementacio ebben a taskban
- [x] Task-specifikus smoke keszult: `scripts/smoke_cavity_t2_runtime_profile_prepack_mode.py`
- [x] `python3 scripts/smoke_cavity_t2_runtime_profile_prepack_mode.py` PASS
- [x] `python3 scripts/smoke_h3_quality_t7_quality_profiles_and_run_config_integration.py` PASS
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/cavity_t2_runtime_profile_prepack_mode.md` PASS
