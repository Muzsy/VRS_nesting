# Rotacios policy + instance regresszio

## 🎯 Funkcio
Ez a P1 task a rotacios policy es instance-kezeles regresszio-biztositasi keretet rogzitit: a listaalapu `allowed_rotations_deg` model mar be van vezetve, de a teljes validacios es regresszios coverage formalizalasa szukseges. P1, mert a P0 mukodik, de hosszu tavon correctness drift kockazata marad.

## 🧠 Fejlesztesi reszletek
### Scope
- Benne van:
  - `allowed_rotations_deg` policy vegpontok (project model, solver, validator, exporter) regresszioellenorzesi terve.
  - `instance_id` stabilitas es duplikacio-tiltas tesztelhetosegenek leirasa.
  - 0/180 policy edge-casek lefedesi vaza.
- Nincs benne:
  - Uj rotacios fokszamok bevezetese 0/90/180/270-on tul.
  - Solver placement heurisztika csere.

### Erintett modulok/fajlok
- `vrs_nesting/project/model.py`
- `vrs_nesting/nesting/instances.py`
- `rust/vrs_solver/src/main.rs`
- `vrs_nesting/dxf/exporter.py`
- `NINCS: vrs_nesting/validate/solution_validator.py`
- `scripts/validate_nesting_solution.py`
- `codex/reports/egyedi_solver/rotation_policy_and_instance_regression.md`
- `codex/codex_checklist/egyedi_solver/rotation_policy_and_instance_regression.md`

### DoD
- [ ] A canvasban egyertelmu policy scope van (instance_id, allowed rotations, duplicate guard).
- [ ] A report vaz tartalmaz regresszios teszttervet (0/180, tiltott 90, duplicate instance).
- [ ] A checklist tartalmazza a P0 gate kompatibilitas ellenorzeset.
- [ ] A scaffold report/checklist kitoltve.

### Kockazat + mitigacio + rollback
- Kockazat: policy drift solver es validator kozott inkonzisztens hibakat okoz.
- Mitigacio: kozos fixture + kozos invarians lista (`scripts/validate_nesting_solution.py`).
- Rollback: policy ellenorzesek fokozatos kapcsolasa, gyors visszaallassal.

### Regresszio-orseg (P0 nem romolhat)
- Kotelezo ellenorzes: `./scripts/verify.sh --report codex/reports/egyedi_solver/rotation_policy_and_instance_regression.md`.
- P0 referenciak: `canvases/egyedi_solver/allowed_rotations_deg_policy_migration.md`, `scripts/check.sh`.

## 🧪 Tesztallapot
- Kotelezo gate: `./scripts/verify.sh --report codex/reports/egyedi_solver/rotation_policy_and_instance_regression.md`
- Relevans letezo szkriptek:
  - `./scripts/check.sh`
  - `python3 scripts/validate_nesting_solution.py --help`

## 🌍 Lokalizacio
N/A

## 📎 Kapcsolodasok
- `tmp/egyedi_solver/mvp_terv_tablas_nesting_fix_w_h_alakos_tabla_alap_a_meglevo_vrs_nesting_repora_epitve.md`
- `tmp/egyedi_solver/uj_tablas_solver_fix_w_h_alakos_stock_komplett_dokumentacio.md`
- `canvases/egyedi_solver/allowed_rotations_deg_policy_migration.md`
- `canvases/egyedi_solver/nesting_solution_validator_and_smoke.md`
