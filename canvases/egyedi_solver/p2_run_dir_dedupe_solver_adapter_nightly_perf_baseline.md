# canvases/egyedi_solver/p2_run_dir_dedupe_solver_adapter_nightly_perf_baseline.md
# P2: run_dir deduplikáció + solver adapter boundary + nightly perf baseline

## 🎯 Funkció

A cél a backlog P2 tételek végrehajtása minimálisan invazív módon:

1. Run directory allokáció deduplikáció: a Sparrow runner saját allokáció helyett a közös `create_run_dir` útvonalat használja.
2. Solver plugin boundary: legyen közös adapter interfész a `vrs_solver` és `sparrow` runner-hívásokra.
3. Nightly perf baseline: legyen ütemezett nightly workflow baseline artifacttal és threshold jelzéssel.

## 🧠 Fejlesztési részletek

### Jelenlegi állapot

- `vrs_nesting/runner/sparrow_runner.py` saját run dir allokátort tart (`_new_run_dir`), miközben már létezik közös `vrs_nesting/run_artifacts/run_dir.py:create_run_dir`.
- A `vrs_nesting/pipeline/run_pipeline.py` és a `vrs_nesting/sparrow/multi_sheet_wrapper.py` közvetlenül runner függvényeket hív, nincs közös plugin boundary.
- Van `scripts/smoke_time_budget_guard.py`, de nincs külön nightly baseline workflow és baseline JSON artifact trendhez.

### Célmegoldás

- `sparrow_runner.run_sparrow` átáll `create_run_dir` használatára (backward-compatible meta mezőkkel).
- Új közös adapter modul a runner rétegben (`vrs_nesting/runner/solver_adapter.py`) egységes `run_in_dir` contracttal.
- `run_pipeline` és `multi_sheet_wrapper` átáll adapter használatra.
- Új/extra tesztek:
  - adapter contract tesztek fake solver/fake sparrow binárissal,
  - deduplikált run_dir allokáció viselkedés tesztje Sparrow runnerre.
- `smoke_time_budget_guard.py` bővül baseline JSON exporttal és paraméterezhető thresholddal.
- Új nightly workflow artifact feltöltéssel és threshold summary figyelmeztetéssel.

### DoD

- [ ] Sparrow runner már nem saját run_dir allokátort használ, hanem `create_run_dir`-t.
- [ ] Közös solver adapter boundary elkészül (`runner/solver_adapter.py`) és mindkét érintett path ezt használja.
- [ ] Van contract teszt az adapter rétegre (fake binaries), és deduplikációs regressziós teszt.
- [ ] Nightly perf baseline workflow létrejön artifact publikálással és threshold jelzéssel.
- [ ] `scripts/smoke_time_budget_guard.py` tud baseline JSON-t írni, threshold paraméterezhető.
- [ ] Kötelező gate PASS: `./scripts/verify.sh --report codex/reports/egyedi_solver/p2_run_dir_dedupe_solver_adapter_nightly_perf_baseline.md`

### Kockázat + mitigáció + rollback

- Kockázat: adapter bevezetés regressziót okoz futtatási útvonalakon.
  - Mitigáció: fake bináris contract tesztek + teljes gate futtatás.
- Kockázat: perf baseline workflow flaky környezetfüggő runtime miatt.
  - Mitigáció: threshold paraméterezés + baseline artifact + warning summary; kezdetben konzervatív limit.
- Rollback: adapter modul és call site használat visszaállítása közvetlen runner hívásokra; nightly workflow ideiglenes kikapcsolása.

## 🧪 Tesztállapot

- Kötelező: `./scripts/verify.sh --report codex/reports/egyedi_solver/p2_run_dir_dedupe_solver_adapter_nightly_perf_baseline.md`
- Opcionális célzott:
  - `python3 -m pytest -q tests/test_solver_adapter_contract.py tests/test_sparrow_runner_run_dir_dedupe.py`

## 🌍 Lokalizáció

Nem releváns.

## 📎 Kapcsolódások

- `vrs_nesting/run_artifacts/run_dir.py`
- `vrs_nesting/runner/sparrow_runner.py`
- `vrs_nesting/runner/solver_adapter.py`
- `vrs_nesting/pipeline/run_pipeline.py`
- `vrs_nesting/sparrow/multi_sheet_wrapper.py`
- `tests/test_solver_adapter_contract.py`
- `tests/test_sparrow_runner_run_dir_dedupe.py`
- `scripts/smoke_time_budget_guard.py`
- `.github/workflows/nightly-perf-baseline.yml`
- `docs/qa/testing_guidelines.md`
