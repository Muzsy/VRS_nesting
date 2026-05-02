# Codex checklist - cavity_v2_t10_lv8_benchmark

- [x] AGENTS.md + T10 canvas/YAML/prompt beolvasva
- [x] Fixture keresesi parancsok futtatva
- [x] LV8 fixture azonosítva: `tmp/ne2_input_lv8jav.json`
- [x] `scripts/benchmark_cavity_v2_lv8.py` letrehozva
- [x] Script tartalmazza a kotelezo metrikakat (`holes before/after`, `guard_passed`, `virtual_parent_count`, `usable_cavity_count`, `holed_child_proxy_count`, `quantity_delta_parts`, `quantity_mismatch_count`, `engine_cli_args`, `nfp_fallback_occurred`, `validation_issues`, `overlap_count`, `bounds_violation_count`)
- [x] Minimum kriterium ellenorzes implementalva (`holes_after==0`, `qty_mismatch==0`, `guard_passed==True`)
- [x] Script csak `tmp/benchmark_results/` ala ir artefaktumot
- [x] `python3 scripts/benchmark_cavity_v2_lv8.py` futott (exit code 0)
- [x] JSON artefaktum mentve: `tmp/benchmark_results/cavity_v2_lv8_20260502T220627Z.json`
- [x] `python3 scripts/benchmark_cavity_v2_lv8.py --help` PASS
- [x] `python3 -c "import ast; ast.parse(...)"` PASS
- [x] Report DoD -> Evidence matrix kitoltve
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/cavity_v2_t10_lv8_benchmark.md` PASS
