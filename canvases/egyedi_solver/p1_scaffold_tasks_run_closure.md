# P1 scaffold taskok implementacios lezaro futasa

## 🎯 Funkcio
Ez a task a P1 audit 3. javitando pontjat zarja: az eredeti P1 scaffold taskok report/checklist artefaktjait tenyleges implementacios futasstatuszra emeli, bizonyitek-alapu DoD matrixszal.
A cel, hogy a `dxf_import_convention_layers`, `geometry_offset_robustness`, `rotation_policy_and_instance_regression`, `determinism_and_time_budget` taskok ne maradjanak "vaz" allapotban.

## 🧠 Fejlesztesi reszletek
### Scope
- Benne van:
  - A 4 P1 task report frissitese scaffold -> implementacios evidenciara.
  - A 4 P1 task checklist frissitese scaffold DoD -> implementacios DoD-re.
  - Verify futtatasa mind a 4 reporton.
- Nincs benne:
  - Uj funkcio implementacio a solver pipeline-ban.
  - P0/P1 kodlogika tovabbi modositasai.

### Erintett fajlok
- `codex/reports/egyedi_solver/dxf_import_convention_layers.md`
- `codex/reports/egyedi_solver/geometry_offset_robustness.md`
- `codex/reports/egyedi_solver/rotation_policy_and_instance_regression.md`
- `codex/reports/egyedi_solver/determinism_and_time_budget.md`
- `codex/reports/egyedi_solver/dxf_import_convention_layers.verify.log`
- `codex/reports/egyedi_solver/geometry_offset_robustness.verify.log`
- `codex/reports/egyedi_solver/rotation_policy_and_instance_regression.verify.log`
- `codex/reports/egyedi_solver/determinism_and_time_budget.verify.log`
- `codex/codex_checklist/egyedi_solver/dxf_import_convention_layers.md`
- `codex/codex_checklist/egyedi_solver/geometry_offset_robustness.md`
- `codex/codex_checklist/egyedi_solver/rotation_policy_and_instance_regression.md`
- `codex/codex_checklist/egyedi_solver/determinism_and_time_budget.md`
- `codex/codex_checklist/egyedi_solver/p1_scaffold_tasks_run_closure.md`
- `codex/reports/egyedi_solver/p1_scaffold_tasks_run_closure.md`

### DoD
- [ ] A 4 P1 report mar nem scaffold formatumot, hanem implementacios evidence matrixot tartalmaz.
- [ ] A 4 P1 checklist mar nem "Scaffold DoD" formatumu, hanem implementacios zarasi pontokat tartalmaz.
- [ ] Mind a 4 report verify futasa PASS.
- [ ] A lezaro reportban osszefoglalas + bizonyitek szerepel.

### Kockazat + mitigacio + rollback
- Kockazat: a report statusz frissitese elcsuszhat valos kodbizonyitek nelkul.
- Mitigacio: minden DoD ponthoz konkret path+line hivatkozas kerul.
- Rollback: csak dokumentacios artefaktok modosulnak, visszavonasuk izolalt.

## 🧪 Tesztallapot
- Kotelezo gate: `./scripts/verify.sh --report codex/reports/egyedi_solver/p1_scaffold_tasks_run_closure.md`
- Kapcsolodo futasok:
  - `./scripts/verify.sh --report codex/reports/egyedi_solver/dxf_import_convention_layers.md`
  - `./scripts/verify.sh --report codex/reports/egyedi_solver/geometry_offset_robustness.md`
  - `./scripts/verify.sh --report codex/reports/egyedi_solver/rotation_policy_and_instance_regression.md`
  - `./scripts/verify.sh --report codex/reports/egyedi_solver/determinism_and_time_budget.md`

## 🌍 Lokalizacio
N/A

## 📎 Kapcsolodasok
- `codex/reports/egyedi_solver_p1_audit.md`
- `codex/reports/egyedi_solver/dxf_import_convention_layers_impl.md`
- `codex/reports/egyedi_solver/geometry_offset_robustness_impl.md`
- `vrs_nesting/project/model.py`
- `vrs_nesting/nesting/instances.py`
- `vrs_nesting/runner/vrs_solver_runner.py`
- `scripts/check.sh`
