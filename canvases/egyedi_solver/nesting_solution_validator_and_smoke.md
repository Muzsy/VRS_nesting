# Tablas validacio + smoke gate

## 🎯 Funkcio
Ez a task egy uj tablas solution validatort es hozza tartozo smoke gate-et definial, hogy a jovobeli solver kimenetekre legyen stabil minosegkapu lokalisan es CI-ben.

## 🧠 Fejlesztesi reszletek
### Scope
- Benne van:
  - `validate_nesting_solution.py` validator script letrehozasa.
  - Uj smoke workflow integracio lokalis es CI futashoz.
  - Failure artifact mentes es report evidencia kovetelmenyek.
- Nincs benne:
  - Solver placement algoritmus fejlesztes.
  - DXF import komplex tisztitas.
  - UI riport felulet.

### Erintett fajlok
- `scripts/validate_nesting_solution.py`
- `.github/workflows/nesttool-smoketest.yml`
- `scripts/check.sh`
- `codex/codex_checklist/egyedi_solver/nesting_solution_validator_and_smoke.md`
- `codex/reports/egyedi_solver/nesting_solution_validator_and_smoke.md`

### DoD
- [ ] Validator ellenorzi: in-bounds, hole szabaly, no-overlap, rotation policy.
- [ ] Uj smoke gate futtathato lokalisan es CI-ben.
- [ ] Failure eseten artifact mentese dokumentalt.
- [ ] Verify report PASS es evidencia matrix kitoltve.

### Kockazat + mitigacio + rollback
- Kockazat: CI instabilitas toolchain/fuggoseg miatt.
- Mitigacio: pinned toolchain, reprodukalhato fixture bemenet.
- Rollback: uj smoke workflow kulon fajlban, regi gate valtozatlanul marad.

## 🧪 Tesztallapot
- Kotelezo gate: `./scripts/verify.sh --report codex/reports/egyedi_solver/nesting_solution_validator_and_smoke.md`
- Task-specifikus ellenorzes a vegrehajto runban:
  - Pozitiv/negativ validator fixture futtatas.
  - CI workflow dry-run vagy PR validacio.

## 🌍 Lokalizacio
Nem relevans.

## 📎 Kapcsolodasok
- `codex/reports/egyedi_solver_backlog.md`
- `tmp/egyedi_solver/uj_tablas_solver_fix_w_h_alakos_stock_komplett_dokumentacio.md`
- `docs/qa/testing_guidelines.md`
- `scripts/check.sh`
- `scripts/verify.sh`
- `.github/workflows/sparrow-smoketest.yml`
