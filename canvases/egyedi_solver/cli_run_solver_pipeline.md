# CLI run solver pipeline osszedrotozas (end-to-end)

## 🎯 Funkcio
A `python3 -m vrs_nesting.cli run <project.json>` parancs teljes end-to-end pipeline-t futtasson:
`project validalas + run_dir letrehozas` → `solver_input.json build` → `vrs_solver_runner` (ugyanabba a run_dir-be) → `validator` → `DXF exporter` → `runs/<run_id>/out/* + report.json`.

Kimenet CLI-n:
- stdout: **csak** a `run_dir` path (shell integraciohoz)
- minden egyeb: `run.log` + stderr.

## 🧠 Fejlesztesi reszletek

### Scope
- Benne van:
  - CLI `run` parancs teljes pipeline osszedrotozasa.
  - `runs/<run_id>/solver_input.json` generalas a `project.json` alapjan (Solver IO contract v1).
  - Solver futtatas ugyanabba a run_dir-be (nem keletkezhet masodik run mappa).
  - Output validalas: `vrs_nesting.validate.solution_validator.validate_nesting_solution`.
  - Export: `vrs_nesting.dxf.exporter.export_per_sheet` → `runs/<run_id>/out/sheet_XXX.dxf`.
  - `runs/<run_id>/report.json` letrehozasa (run szintu osszegzes + export summary).
  - `samples/project_rect_1000x2000.json` olyan allapotba hozasa, hogy a strict schema **elfogadja** CLI project bemenetkent.
- Nincs benne:
  - DXF import workflow.
  - UI / web app integracio.
  - Halado export preset/layer matrix.

### Elvart run artifact struktura
Minimum:
- `runs/<run_id>/project.json` (normalizalt snapshot)
- `runs/<run_id>/run.log`
- `runs/<run_id>/solver_input.json`
- `runs/<run_id>/solver_output.json`
- `runs/<run_id>/runner_meta.json`
- `runs/<run_id>/solver_stdout.log`
- `runs/<run_id>/solver_stderr.log`
- `runs/<run_id>/out/` + `sheet_001.dxf ...`
- `runs/<run_id>/report.json`

### stdout/stderr es log szabaly
- CLI stdout: kizartlag a `run_dir` abszolut path.
- CLI stderr: hiba/uzenetek.
- Pipeline reszletek: `runs/<run_id>/run.log`.
- A runner tovabbra is irhat `solver_stdout.log` es `solver_stderr.log` fajlokat.

### `report.json` minimalis tartalom
- `contract_version`: `"v1"`
- `project_name`, `seed`, `time_limit_s`
- `run_dir`, `status`
- `paths`: `project_json`, `solver_input_json`, `solver_output_json`, `runner_meta_json`, `out_dir`
- `metrics`: `placements_count`, `unplaced_count`, `sheet_count_used`
- `export_summary`: az `export_per_sheet(...)` visszaadott osszegzese
- `validator`: legalabb `status: "pass"` sikeres futas eseten

### Implementacios iranyok (konkret)
- `vrs_nesting/cli.py`:
  - a `run` parancs ne csak snapshot-ot keszitsen, hanem:
    1) project validate + run_dir allocate
    2) `solver_input.json` build + mentes a run_dir-be
    3) solver futtatas runneren keresztul **ugyanabba a run_dir-be**
    4) validator futtatas
    5) exporter futtatas `out/` ala
    6) `report.json` kiiras
  - stdout-on **csak** `run_dir` legyen (minden egyeb log stderr vagy run.log).
- `vrs_nesting/runner/vrs_solver_runner.py`:
  - maradjon kompatibilis a jelenlegi `python3 -m vrs_nesting.runner.vrs_solver_runner ...` CLI-vel.
  - vezess be egy uj API-t, ami **meglevo run_dir**-ben futtat (pl. `run_solver_in_dir(...)`), es ezt hasznalja a CLI orchestrator.
- `samples/project_rect_1000x2000.json`:
  - a strict project schema nem enged meg ismeretlen top-level mezoket (`vrs_nesting/project/model.py`), ezert a demo “extra” mezoket el kell tavolitani vagy kulon mintafajlba kell tenni.

### Erintett fajlok
- `vrs_nesting/cli.py`
- `vrs_nesting/runner/vrs_solver_runner.py`
- `vrs_nesting/validate/solution_validator.py` (csak hasznalat, nem feltetlen modositas)
- `vrs_nesting/dxf/exporter.py` (csak hasznalat, nem feltetlen modositas)
- `samples/project_rect_1000x2000.json`
- `codex/codex_checklist/egyedi_solver/cli_run_solver_pipeline.md`
- `codex/reports/egyedi_solver/cli_run_solver_pipeline.md`

### DoD
- [ ] CLI run vegigviszi a pipeline-t: `project -> solver_input -> runner -> validator -> exporter -> report.json`.
- [ ] `python3 -m vrs_nesting.cli run samples/project_rect_1000x2000.json` sikeresen lefut (solver bin megfelelo beallitasa mellett).
- [ ] A futas eredmenye egyetlen run_dir-ben jelenik meg, nincs “dupla” run letrehozas.
- [ ] Letrejon: `runs/<run_id>/out/sheet_001.dxf` (ha van placement) + `runs/<run_id>/report.json`.
- [ ] A `python3 -m vrs_nesting.runner.vrs_solver_runner ...` tovabbra is mukodik valtozatlanul.
- [ ] Verify gate PASS.

### Kockazat + mitigacio + rollback
- Kockazat: runner refaktor elrontja a jelenlegi gate-et (`scripts/check.sh` runner CLI smoke).
  - Mitigacio: runner CLI path megtartasa, csak uj “run_in_dir” API hozzadasa.
- Kockazat: CLI stdout szemetelese miatt shell integracio torik.
  - Mitigacio: stdout-on kizarolag run_dir; minden mas stderr/run.log.
- Rollback: `vrs_nesting/cli.py` es runner valtozasok visszavonasa git alapon; gate-et a verify step megfogja.

## 🧪 Tesztallapot
- Kotelezo gate: `./scripts/verify.sh --report codex/reports/egyedi_solver/cli_run_solver_pipeline.md`
- Task-specifikus smoke (manualis):
  - `python3 -m vrs_nesting.cli run samples/project_rect_1000x2000.json`
  - ellenorizd a fenti artifact listat a visszaadott run_dir-ben.

## 🌍 Lokalizacio
Nem relevans.

## 📎 Kapcsolodasok
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/solver_io_contract.md`
- `docs/mvp_project_schema.md`
- `vrs_nesting/project/model.py`
- `vrs_nesting/runner/vrs_solver_runner.py`
- `vrs_nesting/validate/solution_validator.py`
- `vrs_nesting/dxf/exporter.py`
- `scripts/check.sh`
- `scripts/verify.sh`
