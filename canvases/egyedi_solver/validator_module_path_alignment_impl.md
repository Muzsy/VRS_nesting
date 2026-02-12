# Validator modul utvonal-egysegesites (P1-VAL-01)

## 🎯 Funkcio
Ez a task a P1-VAL-01 kovetelmenyt zarja: a validator kodot dedikalt modulutvonalra emeli (`vrs_nesting/validate/solution_validator.py`), mikozben a script entrypoint (`scripts/validate_nesting_solution.py`) megmarad kompatibilis wrappernek.
A cel, hogy a dokumentacio es a tenyleges kodhely ne legyen ellentmondasos.

## 🧠 Fejlesztesi reszletek
### Scope
- Benne van:
  - `vrs_nesting/validate/solution_validator.py` letrehozasa.
  - `scripts/validate_nesting_solution.py` wrapperre egyszerusitese.
  - Relevans canvas/report hivatkozasok frissitese a modulutvonal-egysegesiteshez.
- Nincs benne:
  - Validator logika erdemi atirasa.
  - Uj validacios szabaly bevezetese.

### Erintett fajlok
- `vrs_nesting/validate/__init__.py`
- `vrs_nesting/validate/solution_validator.py`
- `scripts/validate_nesting_solution.py`
- `canvases/egyedi_solver/rotation_policy_and_instance_regression.md`
- `codex/reports/egyedi_solver/rotation_policy_and_instance_regression.md`
- `codex/reports/egyedi_solver_p1_audit.md`
- `codex/codex_checklist/egyedi_solver/validator_module_path_alignment_impl.md`
- `codex/reports/egyedi_solver/validator_module_path_alignment_impl.md`

### DoD
- [ ] Letrejon a `vrs_nesting/validate/solution_validator.py` modul, benne a validator API + CLI main.
- [ ] A `scripts/validate_nesting_solution.py` script wrapperkent a modulra hivatkozik.
- [ ] A relevans canvas/report hivatkozasokban nincs mar `NINCS: vrs_nesting/validate/solution_validator.py` ellentmondas.
- [ ] A standard gate valtozatlanul zold.

### Kockazat + mitigacio + rollback
- Kockazat: belso import utvonal torese miatt validator CLI meghibasodhat.
- Mitigacio: script wrapper megtartasa, py_compile + verify gate futtatas.
- Rollback: wrapper visszaallithato eredeti scriptre, modulpath valtozas izolalt.

## 🧪 Tesztallapot
- Kotelezo gate: `./scripts/verify.sh --report codex/reports/egyedi_solver/validator_module_path_alignment_impl.md`
- Kapcsolodo futasok:
  - `python3 scripts/validate_nesting_solution.py --help`
  - `python3 -m vrs_nesting.validate.solution_validator --help`

## 🌍 Lokalizacio
N/A

## 📎 Kapcsolodasok
- `tmp/egyedi_solver/tablas_optimalizacios_algoritmus_jagua_rs_integracio_reszletes_rendszerleiras.md` (validator modulpath)
- `codex/reports/egyedi_solver_p1_audit.md` (P1-VAL-01 finding)
- `canvases/egyedi_solver/rotation_policy_and_instance_regression.md`
