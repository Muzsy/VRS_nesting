PASS_WITH_NOTES

## 1) Meta

- **Task slug:** `p2_run_dir_dedupe_solver_adapter_nightly_perf_baseline`
- **Kapcsolodo canvas:** `canvases/egyedi_solver/p2_run_dir_dedupe_solver_adapter_nightly_perf_baseline.md`
- **Kapcsolodo goal YAML:** `codex/goals/canvases/egyedi_solver/fill_canvas_p2_run_dir_dedupe_solver_adapter_nightly_perf_baseline.yaml`
- **Futas datuma:** `2026-02-17`
- **Branch / commit:** `main`
- **Fokusz terulet:** `Runner | Architecture | CI | Perf`

## 2) Scope

### 2.1 Cel

- P2-1 run_dir allokáció deduplikáció lezárása a Sparrow runnerben.
- P2-2 közös solver adapter boundary bevezetése (`vrs_solver` + `sparrow`).
- P2-3 nightly perf baseline trendelhető artifacttal és threshold summaryval.

### 2.2 Nem-cel (explicit)

- Solver algoritmus módosítás.
- DXF import/export funkcionális redesign.
- CI required check policy módosítás.

## 3) Valtozasok osszefoglalasa (Change summary)

### 3.1 Erintett fajlok

- `vrs_nesting/runner/sparrow_runner.py`
- `vrs_nesting/runner/solver_adapter.py`
- `vrs_nesting/runner/__init__.py`
- `vrs_nesting/pipeline/run_pipeline.py`
- `vrs_nesting/sparrow/multi_sheet_wrapper.py`
- `tests/test_solver_adapter_contract.py`
- `tests/test_sparrow_runner_run_dir_dedupe.py`
- `scripts/smoke_time_budget_guard.py`
- `.github/workflows/nightly-perf-baseline.yml`
- `docs/qa/testing_guidelines.md`
- `codex/codex_checklist/egyedi_solver/p2_run_dir_dedupe_solver_adapter_nightly_perf_baseline.md`
- `codex/reports/egyedi_solver/p2_run_dir_dedupe_solver_adapter_nightly_perf_baseline.md`

### 3.2 Miert valtoztak?

- A P2 backlog pontokban jelzett duplikált run allocation és közvetlen runner-csatolás csökkenti a karbantarthatóságot.
- Az adapter réteg egységesíti a boundary-t, a nightly baseline pedig historikus perf nyomot ad artifactban.

## 4) Verifikacio (How tested)

### 4.1 Kotelezo parancs

- `./scripts/verify.sh --report codex/reports/egyedi_solver/p2_run_dir_dedupe_solver_adapter_nightly_perf_baseline.md` -> PASS

### 4.2 Opcionlis, feladatfuggo parancsok

- `python3 -m pytest -q tests/test_sparrow_runner_run_dir_dedupe.py` -> PASS
- `python3 -m pytest -q tests/test_sparrow_runner_run_dir_dedupe.py tests/test_solver_adapter_contract.py tests/test_cli_end_to_end_contract.py` -> PASS
- `python3 -m pytest -q` -> PASS
- `python3 -m mypy --config-file mypy.ini vrs_nesting` -> PASS
- `python3 scripts/smoke_time_budget_guard.py --help` -> PASS

### 4.3 Ha valami kimaradt

- Nincs.

### 4.4 Automatikus blokk

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-02-17T21:36:56+01:00 → 2026-02-17T21:38:35+01:00 (99s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/p2_run_dir_dedupe_solver_adapter_nightly_perf_baseline.verify.log`
- git: `main@6c131a7`
- módosított fájlok (git status): 18

**git diff --stat**

```text
 docs/qa/testing_guidelines.md              |  5 +++
 scripts/check.sh                           | 50 +++++++++++++++++++++++++-----
 scripts/smoke_time_budget_guard.py         | 44 ++++++++++++++++++++++++--
 vrs_nesting/config/runtime.py              | 21 +++++++++++++
 vrs_nesting/pipeline/run_pipeline.py       | 10 +++---
 vrs_nesting/runner/__init__.py             | 22 ++++++++++++-
 vrs_nesting/runner/sparrow_runner.py       | 30 ++++++------------
 vrs_nesting/runner/vrs_solver_runner.py    | 11 +++----
 vrs_nesting/sparrow/multi_sheet_wrapper.py | 14 +++++----
 9 files changed, 157 insertions(+), 50 deletions(-)
```

**git status --porcelain (preview)**

```text
 M docs/qa/testing_guidelines.md
 M scripts/check.sh
 M scripts/smoke_time_budget_guard.py
 M vrs_nesting/config/runtime.py
 M vrs_nesting/pipeline/run_pipeline.py
 M vrs_nesting/runner/__init__.py
 M vrs_nesting/runner/sparrow_runner.py
 M vrs_nesting/runner/vrs_solver_runner.py
 M vrs_nesting/sparrow/multi_sheet_wrapper.py
?? .github/workflows/nightly-perf-baseline.yml
?? canvases/egyedi_solver/p2_run_dir_dedupe_solver_adapter_nightly_perf_baseline.md
?? codex/codex_checklist/egyedi_solver/p2_run_dir_dedupe_solver_adapter_nightly_perf_baseline.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_p2_run_dir_dedupe_solver_adapter_nightly_perf_baseline.yaml
?? codex/reports/egyedi_solver/p2_run_dir_dedupe_solver_adapter_nightly_perf_baseline.md
?? codex/reports/egyedi_solver/p2_run_dir_dedupe_solver_adapter_nightly_perf_baseline.verify.log
?? tests/test_solver_adapter_contract.py
?? tests/test_sparrow_runner_run_dir_dedupe.py
?? vrs_nesting/runner/solver_adapter.py
```

<!-- AUTO_VERIFY_END -->

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo teszt/ellenorzes |
| --- | ---: | --- | --- | --- |
| Sparrow runner `create_run_dir`-t hasznal deduplikalt allokációval | PASS | `vrs_nesting/runner/sparrow_runner.py:19`, `vrs_nesting/runner/sparrow_runner.py:262` | A saját `_new_run_dir` eltűnt; `run_sparrow` a közös allocatoron keresztül allokál. | `python3 -m pytest -q tests/test_sparrow_runner_run_dir_dedupe.py`, `./scripts/verify.sh --report ...` |
| Közös solver adapter boundary készen van és használt a call site-okban | PASS | `vrs_nesting/runner/solver_adapter.py:19`, `vrs_nesting/pipeline/run_pipeline.py:14`, `vrs_nesting/pipeline/run_pipeline.py:86`, `vrs_nesting/sparrow/multi_sheet_wrapper.py:10`, `vrs_nesting/sparrow/multi_sheet_wrapper.py:342` | Egységes `run_in_dir` contract és egységes adapter error réteg bevezetve, call site-ok átállítva. | `python3 -m pytest -q tests/test_solver_adapter_contract.py`, `./scripts/verify.sh --report ...` |
| Adapter contract tesztek + deduplikáció regressziós teszt elérhető | PASS | `tests/test_solver_adapter_contract.py:79`, `tests/test_solver_adapter_contract.py:112`, `tests/test_sparrow_runner_run_dir_dedupe.py:42` | Fake backendekkel validált adapter contract + külön deduplikációs regressziós teszt. | `python3 -m pytest -q tests/test_sparrow_runner_run_dir_dedupe.py tests/test_solver_adapter_contract.py tests/test_cli_end_to_end_contract.py` |
| Nightly perf baseline workflow artifact + threshold summary megvan | PASS | `.github/workflows/nightly-perf-baseline.yml:35`, `.github/workflows/nightly-perf-baseline.yml:43`, `.github/workflows/nightly-perf-baseline.yml:78` | Ütemezett nightly workflow baseline futtatással, summary warning/notice lépéssel és artifact uploaddal. | Workflow definíció review + `./scripts/verify.sh --report ...` |
| Perf guard baseline JSON és threshold paraméter támogatott | PASS | `scripts/smoke_time_budget_guard.py:90`, `scripts/smoke_time_budget_guard.py:136`, `scripts/smoke_time_budget_guard.py:169` | A script paraméterezhető thresholdot és opcionális baseline JSON exportot ad. | `python3 scripts/smoke_time_budget_guard.py --help`, `./scripts/verify.sh --report ...` |
| Verify PASS + report/log frissítés | PASS | `codex/reports/egyedi_solver/p2_run_dir_dedupe_solver_adapter_nightly_perf_baseline.verify.log`, `codex/reports/egyedi_solver/p2_run_dir_dedupe_solver_adapter_nightly_perf_baseline.md` | A kötelező gate PASS, AUTO_VERIFY blokk frissült. | `./scripts/verify.sh --report codex/reports/egyedi_solver/p2_run_dir_dedupe_solver_adapter_nightly_perf_baseline.md` |

## 8) Advisory notes (nem blokkolo)

- A verify stat jelenleg tartalmazza a már korábban megkezdett P1 centralizációs módosításokat is (`scripts/check.sh`, `vrs_nesting/config/runtime.py`, `vrs_nesting/runner/vrs_solver_runner.py`), mert a worktree nem volt tiszta.
- A nightly perf baseline küszöb most konzervatív (5.0s), később történeti adatok alapján finomítható.
