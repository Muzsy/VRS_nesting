# T06 Checklist — lv8_density_t06_phase0_shadow_run_baseline_report

- [x] Kötelező források beolvasva (`AGENTS.md`, codex/qa docs, T06 canvas, T06 YAML, master/index).
- [x] T01–T05 reportok léteznek és mind PASS/PASS_WITH_NOTES.
- [x] `get_phase0_shadow_profile_pairs()` ellenőrizve:
      `quality_default -> quality_default_no_sa_shadow`,
      `quality_aggressive -> quality_aggressive_no_sa_shadow`.
- [x] Fixture availability ellenőrizve:
      `tests/fixtures/nesting_engine/ne2_input_lv8jav.json`,
      `tmp/lv8_singlesheet_etalon_20260514/inputs/lv8_sheet1_179.json`,
      `poc/nesting_engine/f2_4_sa_quality_fixture_v2.json`,
      contract-freeze anchorok.
- [x] `scripts/experiments/lv8_phase0_shadow_run_matrix.py` létrehozva.
- [x] `tests/test_lv8_phase0_shadow_run_matrix.py` létrehozva.
- [x] Célzott ellenőrzések zöldek:
      `py_compile` (3 script) + `pytest tests/test_lv8_phase0_shadow_run_matrix.py -q` (5 passed).
- [x] Matrix artefaktok elkészültek:
      `runs.jsonl`, `phase0_shadow_matrix.json`, `phase0_shadow_matrix.md`,
      `hard_cut_decision.json`, `fixture_profile_inventory.json`.
- [x] Contract-freeze smoke row jelen van (`regression_gate=PASS`,
      `shadow_profile_applicability=not_applicable`).
- [x] Hard-cut decision rögzítve: `DEFER_HARD_CUT`.
- [x] T06 report + checkpoint alias report létrehozva.
- [x] `./scripts/verify.sh --report ...` futtatás eredménye visszaírva a reportba.
