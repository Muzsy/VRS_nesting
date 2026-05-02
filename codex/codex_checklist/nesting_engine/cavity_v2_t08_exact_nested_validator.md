# Codex checklist - cavity_v2_t08_exact_nested_validator

- [x] AGENTS.md + T08 canvas/YAML/prompt beolvasva
- [x] `worker/cavity_validation.py` letrehozva
- [x] `tests/worker/test_cavity_validation.py` letrehozva
- [x] `CavityValidationError`, `ValidationIssue`, `validate_cavity_plan_v2` exportalva `__all__`-ban
- [x] `validate_child_within_cavity()` implementalva (`covers()` alapu)
- [x] `validate_no_child_child_overlap()` implementalva (Shapely overlap area check)
- [x] Hibakodok tesztelve: `CAVITY_CHILD_OUTSIDE_PARENT_CAVITY`, `CAVITY_CHILD_CHILD_OVERLAP`, `CAVITY_QUANTITY_MISMATCH`
- [x] `strict=True` esetben kivetel dob (`CavityValidationError`)
- [x] `strict=False` esetben issue listat ad vissza
- [x] Shapely dependency es import ellenorizve (`shapely==2.1.2`, import OK)
- [x] Modul nem ir fajlt, nem hiv DB-t
- [x] `python3 -m pytest -q tests/worker/test_cavity_validation.py` PASS
- [x] Report DoD -> Evidence matrix kitoltve
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/cavity_v2_t08_exact_nested_validator.md` PASS
