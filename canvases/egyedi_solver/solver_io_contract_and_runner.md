# Solver IO contract + runner integracios reteg

## 🎯 Funkcio
Ez a task a tablas solver input/output szerzodeset es a futtato runner reteget formalizalja, hogy a solver cserelheto es auditably futtathato legyen.

## 🧠 Fejlesztesi reszletek
### Scope
- Benne van:
  - `solver_input.json` es `solver_output.json` schema dokumentacio.
  - Python runner modul a solver processz futtatasara es logolasara.
  - Input hash, seed, exit status, artifact path metadata rogzitese.
- Nincs benne:
  - Solver heuristikak implementalasa.
  - DXF parser/export funkcio.
  - CI benchmark pipeline.

### Erintett fajlok
- `NINCS: docs/solver_io_contract.md`
- `NINCS: vrs_nesting/runner/vrs_solver_runner.py`
- `codex/codex_checklist/egyedi_solver/solver_io_contract_and_runner.md`
- `codex/reports/egyedi_solver/solver_io_contract_and_runner.md`
- Referencia: `vrs_nesting/runner/sparrow_runner.py`

### DoD
- [ ] Dokumentalt es verziozott solver IO schema elerheto.
- [ ] Runner feloldja a solver binarist (env/explicit/PATH) es futtat.
- [ ] Non-zero exit es parse hiba esetben diagnosztika mentodik.
- [ ] Input hash + seed + cmd metadata reportalva.
- [ ] Task report/checklist verify kapuval zar.

### Kockazat + mitigacio + rollback
- Kockazat: korai contract churn kompatibilitasi toressel.
- Mitigacio: contract verzio mezok, backward compatibility tabla a doksiban.
- Rollback: runner modul feature branchen tarthato, fallback a meglvo Sparrow runnerre.

## 🧪 Tesztallapot
- Kotelezo gate: `./scripts/verify.sh --report codex/reports/egyedi_solver/solver_io_contract_and_runner.md`
- Task-specifikus ellenorzes a vegrehajto runban:
  - Sikeres es hibas solver processz szimulacio.
  - IO schema peldak validator ellenorzese.

## 🌍 Lokalizacio
Nem relevans.

## 📎 Kapcsolodasok
- `codex/reports/egyedi_solver_backlog.md`
- `tmp/egyedi_solver/tablas_optimalizacios_algoritmus_jagua_rs_integracio_reszletes_rendszerleiras.md`
- `tmp/egyedi_solver/uj_tablas_solver_fix_w_h_alakos_stock_komplett_dokumentacio.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `vrs_nesting/runner/sparrow_runner.py`
- `scripts/run_sparrow_smoketest.sh`
