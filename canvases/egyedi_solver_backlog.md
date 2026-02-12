# Egyedi táblás solver backlog (P0-P3)

## 🎯 Funkció
A run célja az egyedi táblás solver fejlesztési backlogjának felépítése P0-P3 prioritásokkal, kizárólag valós repó-evidenciákra támaszkodva. Ez a canvas csak tervezést és priorizálást fed le; implementáció nem része.

## 🧠 Fejlesztési részletek
### Scope
- Kötelező onboarding források és minták felderítése.
- `tmp/egyedi_solver/*` dokumentumok feldolgozása.
- Kódbázis belépési pontok és hiányzó modulok azonosítása.
- P0-P3 backlog elkészítése task-szintű DoD + kockázat/mitigációval.

### Nem-cél
- Táblás solver vagy CLI implementálása.
- Új goal YAML-ek készítése P0 taskokra ebben a runban.
- Meglévő Sparrow smoketest pipeline működésének módosítása.

### Kötelező canvas szekciók (onboarding kivonat)
- `🎯 Funkció`
- `🧠 Fejlesztési részletek`
- `🧪 Tesztállapot`
- `🌍 Lokalizáció`
- `📎 Kapcsolódások`

### Goal YAML `steps` séma (onboarding kivonat)
```yaml
steps:
  - name: "<lépés neve>"
    description: >
      <végrehajtható utasítás>
    outputs:
      - "<fájl útvonal>"
```

### Backlog összefoglaló
- P0: architektúra és minimális futtatható táblás pipeline alapok (schema, CLI, solver IO, validáció, smoke).
- P1: stabilizálás (geometriai robusztusság, regressziós teszt, CI teljesítés, hibakezelés, determinisztika).
- P2: használhatóság és optimalizációs minőség javítás (preview, diagnosztika, heurisztikák tuningja).
- P3: hosszabb távú bővítések (metaheurisztika, fejlettebb objective, opciós exportok).

### Rövid P0-P3 lista
- P0: `project_schema_and_cli_skeleton`, `solver_io_contract_and_runner`, `table_solver_mvp_multisheet`, `nesting_solution_validator_and_smoke`, `dxf_export_per_sheet_mvp`.
- P1: `geometry_offset_robustness`, `rotation_policy_and_instance_regression`, `ci_nesttool_gate`, `determinism_and_time_budget`.
- P2: `preview_and_debug_exports`, `candidate_generation_tuning`, `failure_diagnostics_for_unplaceable_parts`.
- P3: `advanced_objective_and_metaheuristics`, `mixed_stock_selection`, `interactive_reporting_extensions`.

### Kockázatok és rollback terv
- Kockázat: túl széles backlog, homályos task-határok.
  - Mitigáció: minden taskhoz egyedi `TASK_SLUG`, konkrét DoD és fájlszintű érintettség.
- Kockázat: tervezett modulútvonalak nem léteznek jelenleg.
  - Mitigáció: a reportban explicit `NINCS: <path>` jelölés és P0 blocker címke.
- Rollback: a run csak dokumentációs artefaktokat érint; visszaállítás git alapon kockázatmentes.

## 🧪 Tesztállapot
- Kötelező gate: `./scripts/verify.sh --report codex/reports/egyedi_solver_backlog.md`.
- Implementációs teszt ebben a runban nincs (tervezési run).

## 🌍 Lokalizáció
Nem releváns (tervezési/backlog run).

## 📎 Kapcsolódások
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `codex/prompts/task_runner_prompt_template.md`
- `tmp/egyedi_solver/dxf_nesting_app_7_multi_sheet_wrapper_reszletes.md`
- `tmp/egyedi_solver/mvp_terv_tablas_nesting_fix_w_h_alakos_tabla_alap_a_meglevo_vrs_nesting_repora_epitve.md`
- `tmp/egyedi_solver/tablas_optimalizacios_algoritmus_jagua_rs_integracio_reszletes_rendszerleiras.md`
- `tmp/egyedi_solver/uj_tablas_solver_fix_w_h_alakos_stock_komplett_dokumentacio.md`
