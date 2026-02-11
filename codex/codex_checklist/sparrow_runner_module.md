# Codex checklist — sparrow_runner_module

## Kötelező (workflow)

- [x] Elolvastam: `AGENTS.md`, `docs/codex/overview.md`, `docs/codex/yaml_schema.md`, `docs/codex/report_standard.md`
- [x] A canvas pontos, csak valós fájlokra hivatkozik: `canvases/sparrow_runner_module.md`
- [x] A goal YAML a szabvány sémát használja, és az outputs szabályt betartja: `codex/goals/canvases/fill_canvas_sparrow_runner_module.yaml`

## Implementáció

- [x] Létrejött a python csomag váz: `vrs_nesting/__init__.py`, `vrs_nesting/runner/__init__.py`
- [x] Létrejött a runner modul: `vrs_nesting/runner/sparrow_runner.py`
- [x] Frissült a smoketest belépési pont: `scripts/run_sparrow_smoketest.sh`
- [x] Frissült a CI artefakt mentés failure esetén: `.github/workflows/sparrow-smoketest.yml`
- [x] Frissült a gitignore: `.gitignore` (runs/)

## Minőségkapu és bizonyítékok

- [x] Lefutott: `./scripts/verify.sh --report codex/reports/sparrow_runner_module.md` (PASS)
- [x] A report AUTO_VERIFY blokkja frissült és a log létrejött: `codex/reports/sparrow_runner_module.verify.log`
- [x] A reportban a DoD -> Evidence Matrix minden pontja kitöltve.

## Utóellenőrzés (gyors)

- [x] `python3 -m vrs_nesting.runner.sparrow_runner --help` működik
- [x] A smoketest futás `runs/<run_id>/` alá ír (snapshot + logs + output + runner_meta.json)
