# VRS Nesting Engineering Audit

## Executive Summary
- A tényleges belépési pont a `vrs_nesting` oldalon a CLI: `run` (table solver) és `dxf-run` (DXF+Sparrow) (`vrs_nesting/cli.py:245`, `vrs_nesting/cli.py:249`).
- A contractok dokumentáltak (`docs/solver_io_contract.md:13`, `docs/dxf_project_schema.md:10`, `docs/dxf_run_artifacts_contract.md:33`), és a validáció több ponton enforce-olt (`vrs_nesting/project/model.py:233`, `vrs_nesting/runner/vrs_solver_runner.py:103`).
- A lokál/CI gate erős és széles (`scripts/check.sh:24`, `scripts/check.sh:31`, `scripts/check.sh:66`, `scripts/check.sh:90`, `scripts/check.sh:181`), de nehéz és külső függőség-érzékeny (`scripts/ensure_sparrow.sh:146`).
- A “valódi gate” CI-ben a `repo-gate` workflow, mert ez futtatja a teljes `check.sh`-t (`.github/workflows/repo-gate.yml:31`).
- A tesztmix erősen smoke-domináns; pytest unit teszt csak 8 db és főleg schema/import fókuszú (`tests/test_project_model_validation.py:27`, `tests/test_dxf_importer_json_fixture.py:14`, `tests/test_run_dir.py:8`).
- `vrs_nesting/cli.py` jelenleg orchestration + reporting + export + error mapping egyben, magas couplinggal (`vrs_nesting/cli.py:75`, `vrs_nesting/cli.py:155`, `vrs_nesting/cli.py:195`).
- Kettős run-dir allokáció van (`vrs_nesting/run_artifacts/run_dir.py:26` vs `vrs_nesting/runner/sparrow_runner.py:95`) => karbantarthatósági kockázat.
- Konfiguráció szétszórt env-ekben és defaultokban (`scripts/check.sh:7`, `vrs_nesting/runner/vrs_solver_runner.py:279`, `vrs_nesting/runner/sparrow_runner.py:302`), nincs központi config modell.
- Logging van, de minimális observability: text log + stderr, nincs strukturált log/trace/correlation id (`vrs_nesting/run_artifacts/run_dir.py:52`, `vrs_nesting/runner/vrs_solver_runner.py:143`).
- “False green” lehetőség: rész-workflowk sikeresek lehetnek, miközben full gate bukna (pl. `sparrow-smoketest` nem futtat mypy-t) (`.github/workflows/sparrow-smoketest.yml:31`, `.github/workflows/repo-gate.yml:31`).
- “False red” lehetőség: fallback clone/network vagy toolchain bizonytalanság okozhat törést nem-kódhibából (`scripts/ensure_sparrow.sh:146`, `scripts/check.sh:92`).
- Dokumentációs drift: a futtatási doksi CLI-je eltér a valós CLI-tól (`docs/how_to_run.md:45` vs `vrs_nesting/cli.py:245`).

## Architecture Map (Path Evidence)
- Diagram (szöveges):
`CLI -> project.model -> (run_artifacts + runner.vrs_solver + validate + dxf.exporter)`
`CLI(dxf-run) -> project.model(dxf) -> sparrow.input_generator -> sparrow.multi_sheet_wrapper -> dxf.exporter`
- Fő modulok:
- `vrs_nesting/project/model.py`: strict schema parse (`v1`, `dxf_v1`) és determinisztikus hibakódok (`vrs_nesting/project/model.py:12`, `vrs_nesting/project/model.py:233`, `vrs_nesting/project/model.py:269`).
- `vrs_nesting/runner/vrs_solver_runner.py`: binary resolve, timeout, meta, contract validate (`vrs_nesting/runner/vrs_solver_runner.py:77`, `vrs_nesting/runner/vrs_solver_runner.py:146`, `vrs_nesting/runner/vrs_solver_runner.py:169`).
- `vrs_nesting/runner/sparrow_runner.py`: Sparrow process orchestration és artifact kezelés (`vrs_nesting/runner/sparrow_runner.py:171`, `vrs_nesting/runner/sparrow_runner.py:248`).
- `vrs_nesting/sparrow/input_generator.py`: dxf_v1 -> sparrow_instance + solver_input transzform (`vrs_nesting/sparrow/input_generator.py:76`, `vrs_nesting/sparrow/input_generator.py:129`).
- `vrs_nesting/sparrow/multi_sheet_wrapper.py`: iteratív sheet-budget, partial/unplaced okok, determinisztikus rounding (`vrs_nesting/sparrow/multi_sheet_wrapper.py:210`, `vrs_nesting/sparrow/multi_sheet_wrapper.py:289`, `vrs_nesting/sparrow/multi_sheet_wrapper.py:410`).
- `vrs_nesting/dxf/importer.py`: DXF/JSON backend, layer convention, chain/arc/spline kezelés (`vrs_nesting/dxf/importer.py:21`, `vrs_nesting/dxf/importer.py:148`, `vrs_nesting/dxf/importer.py:401`).
- `vrs_nesting/dxf/exporter.py`: per-sheet export approx/source móddal (`vrs_nesting/dxf/exporter.py:600`, `vrs_nesting/dxf/exporter.py:678`).
- Függőségi irányok:
- Jelenlegi irány többnyire “felső orchestration -> domain modulok” (`vrs_nesting/cli.py:13`-`vrs_nesting/cli.py:27`).
- Explicit “tiltott irány” szabály a repóban: `UNKNOWN` (nem találtam deklarálva külön fájlban).
- I/O contractok:
- Solver contract: `docs/solver_io_contract.md:13`, input/output futás közben `solver_input.json`/`solver_output.json`.
- DXF run artifact contract: `docs/dxf_run_artifacts_contract.md:33`, CLI report shape: `vrs_nesting/cli.py:195`.
- Entry points:
- CLI: `python -m vrs_nesting.cli run|dxf-run` (`vrs_nesting/cli.py:241`).
- Wrapper: `scripts/run_real_dxf_sparrow_pipeline.py:29`.

## QA + CI/Gate Findings
- Mi fut:
- Lokál gate: `./scripts/check.sh` (`scripts/check.sh:24`…`scripts/check.sh:185`).
- Codex wrapper: `./scripts/verify.sh --report ...` (`scripts/verify.sh:7`, `scripts/verify.sh:122`, `scripts/verify.sh:166`).
- CI:
- Full gate: `.github/workflows/repo-gate.yml` -> `./scripts/check.sh` (`.github/workflows/repo-gate.yml:31`).
- Sparrow smoke only: `.github/workflows/sparrow-smoketest.yml` (`.github/workflows/sparrow-smoketest.yml:40`).
- Solver smoke track: `.github/workflows/nesttool-smoketest.yml` (`.github/workflows/nesttool-smoketest.yml:62`).
- False green kockázat:
- Rész-workflowk nem fedik a teljes gate-et (pl. nincs mypy a `sparrow-smoketest`-ben) (`.github/workflows/sparrow-smoketest.yml:31` vs `.github/workflows/repo-gate.yml:31`).
- Status mező domain (`ok|partial`) nincs explicit enforce a Python validatorban (`docs/solver_io_contract.md:54`, `vrs_nesting/nesting/instances.py:255`).
- False red kockázat:
- Sparrow fallback clone + pin fetch hálózati érzékenység (`scripts/ensure_sparrow.sh:94`, `scripts/ensure_sparrow.sh:146`).
- Local/CI eltérés overlap-checknél auto módban (`scripts/run_sparrow_smoketest.sh:14`, `scripts/run_sparrow_smoketest.sh:113`).
- QA illeszkedés a docs/qa-hoz:
- Nagyrészt illeszkedik (`docs/qa/testing_guidelines.md:15`, `scripts/check.sh:24`).
- Dry-run checklist használat enforcement automatizmus: `UNKNOWN` (nem láttam CI/script ellenőrzést erre).

## Prioritized Backlog

| Prió | Item | Miért (evidence + hatás) | DoD | Érintett path-ok | Kockázat + mitigáció | Mérőszám |
|---|---|---|---|---|---|---|
| P0 | Solver output status contract explicit validálása (`ok/partial`) | Doksi megköveteli (`docs/solver_io_contract.md:54`), validator nem ellenőrzi explicit (`vrs_nesting/nesting/instances.py:255`) | Invalid status esetén determinisztikus hiba; unit test lefedi | `vrs_nesting/nesting/instances.py`, `tests/*` | Kicsi: backward break lehet régi fixture-eknél; mitigáció: migrációs teszt + egyértelmű error code | Contract defect rate proxy (invalid output átcsúszás) |
| P0 | End-to-end contract tests (CLI `run`, `dxf-run`) fake solverrel | Kritikus pathok unitban alul-teszteltek (csak 8 test, főleg parser/import: `tests/...`) | 2 új integration teszt temp run_dir-rel, artifact shape és stdout contract validálás | `tests/`, `vrs_nesting/cli.py` | Közepes: flaky subprocess; mitigáció: fake binaries + temp dirs + deterministic seed | Flake rate, regressziók száma release előtt |
| P0 | CI gate egyértelműsítés: `repo-gate` mint required check | Több workflow eltérő lefedettséggel (`.github/workflows/*.yml`) | PR policy-ban required check = `repo-gate`; docs frissítve | `.github/workflows/repo-gate.yml`, `docs/qa/testing_guidelines.md` | Kicsi: kezdeti PR friction; mitigáció: rollout kommunikáció | False green arány |
| P0 | Sparrow ellátási lánc stabilizálás (vendor-first, network fallback csökkentés CI-ben) | Hálózati/remote függőség false red-et okozhat (`scripts/ensure_sparrow.sh:146`) | CI-ben nincs fallback clone; pinned vendor/submodule használat enforce-olva | `scripts/ensure_sparrow.sh`, `.github/workflows/repo-gate.yml` | Közepes: kezdeti setup költség; mitigáció: dokumentált bootstrap | CI failure rate (infra vs code) |
| P1 | `cli.py` felbontása use-case modulokra | Magas orchestration coupling egy fájlban (`vrs_nesting/cli.py:75`, `vrs_nesting/cli.py:155`) | Külön `run_pipeline.py` és `dxf_pipeline.py`, CLI csak dispatch | `vrs_nesting/cli.py`, új `vrs_nesting/*pipeline*.py` | Közepes: refactor regresszió; mitigáció: golden integration test | Change-failure rate, review time |
| P1 | Központi config modell (seed/time_limit/bin paths) | Env/default kezelés szétszórt (`scripts/check.sh:7`, `vrs_nesting/runner/*.py`) | Egy typed config objektum; runner+scripts ugyanazt használja | `vrs_nesting/runner/*.py`, `scripts/check.sh` | Közepes: cross-file változás; mitigáció: incremental adapter | Konfig bugok száma, onboarding time |
| P1 | Error code catalog és nyelvi egységesítés | Vegyes HU/EN user-facing hibaüzenetek (`vrs_nesting/runner/sparrow_runner.py:90`, `vrs_nesting/cli.py:146`) | Egységes error format és dokumentált kódkészlet | `vrs_nesting/**/*.py`, `docs/*contract*.md` | Kicsi: breaking string assertions; mitigáció: tests update | Support ticket time-to-diagnose proxy |
| P1 | Dokumentáció szinkron helyreállítása (`how_to_run`) | Doksi elavult CLI-t mutat (`docs/how_to_run.md:45` vs `vrs_nesting/cli.py:245`) | Minden parancs futtatható; docs smoke check script | `docs/how_to_run.md`, `docs/dxf_run_artifacts_contract.md` | Kicsi; mitigáció: CI docs command lint | Docs drift incidensek |
| P2 | Run directory allokáció deduplikáció | Két külön implementáció (`vrs_nesting/run_artifacts/run_dir.py:26`, `vrs_nesting/runner/sparrow_runner.py:95`) | Sparrow runner is `create_run_dir`-t használja vagy közös allocator | `vrs_nesting/runner/sparrow_runner.py`, `vrs_nesting/run_artifacts/run_dir.py` | Kicsi; mitigáció: backward-compatible meta mezők | Maintenance cost proxy (duplikált LOC) |
| P2 | Solver plugin boundary (`sparrow` vs `vrs_solver`) | Jelenleg közvetlen runner-hívásokkal csatolt (`vrs_nesting/sparrow/multi_sheet_wrapper.py:10`, `vrs_nesting/cli.py:19`) | Egy közös solver adapter interfész + contract tests | `vrs_nesting/runner/`, `vrs_nesting/cli.py` | Közepes/nagy; mitigáció: adapter pattern, phased migration | Extensibility lead time |
| P2 | Nightly perf baseline | Van guard smoke (`scripts/smoke_time_budget_guard.py:89`), de nincs trend | Nightly benchmark artifact + threshold alert | `.github/workflows/*`, `scripts/smoke_time_budget_guard.py` | Kicsi; mitigáció: non-blocking report first | Build time trend, perf regressziók |

## Next 2 Weeks Plan
1. Hét 1: P0/1-4 végrehajtás (status validation, E2E contract tests, required CI gate, Sparrow supply stabilization).
2. Hét 1 vége: `repo-gate` required check beállítás + docs/qa update + 1 dry run PR.
3. Hét 2 eleje: P1/1-2 (`cli.py` szeparáció és config centralizálás) minimális viselkedésváltozással.
4. Hét 2 közepe: P1/3-4 (error catalog + docs sync) és regressziós tesztek.
5. Hét 2 vége: mérőszám baseline rögzítés (CI fail reason split, smoke runtime, flake rate proxy).
