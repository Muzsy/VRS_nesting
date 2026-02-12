# Determinizmus/idokeret timeout-perf guard implementacio

## 🎯 Funkcio
Ez a task a P1-DET-02 hianyzo bizonyitekpontjat zarja: bevezet egy explicit, reprodukalhato timeout/perf guard smoke tesztet, ami a runner idokeret-kikenszeriteset tenylegesen ellenorzi.
A cel, hogy ne csak parameter-atadas bizonyitek legyen, hanem valodi timeout ag is legyen tesztelve.

## 🧠 Fejlesztesi reszletek
### Scope
- Benne van:
  - `vrs_nesting/runner/vrs_solver_runner.py` timeout kikenszerites bovitese.
  - Reprodukalhato timeout/perf guard smoke script (`scripts/smoke_time_budget_guard.py`) letrehozasa.
  - Gate (`scripts/check.sh`) bovitese az uj smoke lepes futtatasaval.
  - `determinism_and_time_budget` report/checklist frissitese explicit timeout bizonyitekkal.
- Nincs benne:
  - Solver heurisztika vagy keresesi algoritmus modositasa.
  - Uj benchmark infrastruktura bevezetese.

### Erintett fajlok
- `vrs_nesting/runner/vrs_solver_runner.py`
- `scripts/smoke_time_budget_guard.py`
- `samples/time_budget/timeout_guard_input.json`
- `scripts/check.sh`
- `.github/workflows/nesttool-smoketest.yml`
- `codex/reports/egyedi_solver/determinism_and_time_budget.md`
- `codex/codex_checklist/egyedi_solver/determinism_and_time_budget.md`
- `codex/codex_checklist/egyedi_solver/time_budget_timeout_perf_guard_impl.md`
- `codex/reports/egyedi_solver/time_budget_timeout_perf_guard_impl.md`

### DoD
- [ ] A runner timeoutot enforce-ol (`time_limit_s` alapjan) es determinisztikus hibaval lep ki timeoutnal.
- [ ] Van reprodukalhato timeout guard smoke teszt (fake slow solverrel), ami pirosra futna timeout enforce nelkul.
- [ ] A standard gate futtatja az uj timeout/perf guard smoke tesztet.
- [ ] A `determinism_and_time_budget` report/checklist explicit P1-DET-02 timeout bizonyitekkal frissul.
- [ ] A task report DoD -> Evidence matrix kitoltve, verify PASS.

### Kockazat + mitigacio + rollback
- Kockazat: tul szigoru timeout threshold fals hibakat okozhat.
- Mitigacio: runner timeouthoz kis grace ido, smoke teszt izolalt fake solverrel.
- Rollback: timeout guard smoke lepes ideiglenesen kiveheto `check.sh`-bol, runner timeout blokk izolaltan visszafordithato.

## 🧪 Tesztallapot
- Kotelezo gate: `./scripts/verify.sh --report codex/reports/egyedi_solver/time_budget_timeout_perf_guard_impl.md`
- Relevans futasok:
  - `python3 scripts/smoke_time_budget_guard.py`
  - `./scripts/verify.sh --report codex/reports/egyedi_solver/determinism_and_time_budget.md`

## 🌍 Lokalizacio
N/A

## 📎 Kapcsolodasok
- `codex/reports/egyedi_solver/determinism_and_time_budget.md`
- `tmp/egyedi_solver/mvp_terv_tablas_nesting_fix_w_h_alakos_tabla_alap_a_meglevo_vrs_nesting_repora_epitve.md` (time_limit)
- `tmp/egyedi_solver/dxf_nesting_app_7_multi_sheet_wrapper_reszletes.md` (determinism/time-budget)
- `vrs_nesting/runner/vrs_solver_runner.py`
- `scripts/check.sh`
