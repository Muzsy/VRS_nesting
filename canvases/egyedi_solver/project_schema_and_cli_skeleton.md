# Projekt schema + CLI skeleton + run artifact alap

## 🎯 Funkcio
Ez a task egy minimalis, determinisztikus VRS belepesi pontot ad: projekt schema dokumentacio, CLI run entrypoint, es run artifact konyvtar kezeles. Implementacio ebben a taskban kesobb tortenik, itt a konkret vegrehajtasi celok rogzitese a cel.

## 🧠 Fejlesztesi reszletek
### Scope
- Benne van:
  - MVP projekt schema dokumentalasa es strict validacios szabalyok rogzitese.
  - `python3 -m vrs_nesting.cli run <project.json>` belepesi pont definialasa.
  - `runs/<run_id>/project.json` snapshot contract rogzites.
- Nincs benne:
  - Solver algoritmus implementacio.
  - DXF import/export reszletes megvalositas.
  - CI workflow atalakitas.

### Erintett fajlok
- `NINCS: vrs_nesting/cli.py`
- `NINCS: vrs_nesting/project/model.py`
- `NINCS: vrs_nesting/run_artifacts/run_dir.py`
- `NINCS: docs/mvp_project_schema.md`
- `codex/codex_checklist/egyedi_solver/project_schema_and_cli_skeleton.md`
- `codex/reports/egyedi_solver/project_schema_and_cli_skeleton.md`

### DoD
- [ ] Letrejon a CLI belepesi pont: `python3 -m vrs_nesting.cli run <project.json>`.
- [ ] A project schema strict validaciot ad deterministicus hibaformatummal.
- [ ] A run snapshot mentes mukodik: `runs/<run_id>/project.json`.
- [ ] Minimal run log struktura rogzitett.
- [ ] A report es checklist a task futas vegen kitoltott es verify-olt.

### Kockazat + mitigacio + rollback
- Kockazat: tul tag schema korai lock-inhez vezet.
- Mitigacio: MVP mezo lista freeze, explicit verziozas, unknown mezo tiltasa.
- Rollback: uj fajlok visszavonasa git alapon, meglevo Sparrow pipeline-t nem erinti.

## 🧪 Tesztallapot
- Kotelezo gate: `./scripts/verify.sh --report codex/reports/egyedi_solver/project_schema_and_cli_skeleton.md`
- Task-specifikus ellenorzes a vegrehajto runban:
  - CLI help/run exit kodok.
  - Snapshot letrejott path ellenorzes.

## 🌍 Lokalizacio
Nem relevans.

## 📎 Kapcsolodasok
- `codex/reports/egyedi_solver_backlog.md`
- `tmp/egyedi_solver/mvp_terv_tablas_nesting_fix_w_h_alakos_tabla_alap_a_meglevo_vrs_nesting_repora_epitve.md`
- `tmp/egyedi_solver/uj_tablas_solver_fix_w_h_alakos_stock_komplett_dokumentacio.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `vrs_nesting/runner/sparrow_runner.py`
- `scripts/verify.sh`
