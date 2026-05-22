# Runner — JG-01 jagua_optimizer_t01_repo_and_source_audit

## Feladat

A VRS_nesting repo gyökerében dolgozz. Hajtsd végre a JG-01 audit taskot:

```text
JG-01 — jagua_optimizer_t01_repo_and_source_audit
```

Ez audit és döntés-előkészítés. Ne implementálj solver-kódot.

## Kötelező bemenetek

Először olvasd el teljes egészében:

```text
AGENTS.md
docs/codex/overview.md
docs/codex/yaml_schema.md
docs/codex/report_standard.md
docs/qa/testing_guidelines.md
canvases/jagua_rs_sajat_optimizer/plan/deep-research-report.md
canvases/jagua_rs_sajat_optimizer/plan/jagua_rs_sajat_optimizer_fejlesztesi_terv.md
canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_canvas_yaml_runner_task_bontas.md
canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md
canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_master_plan.md
canvases/egyedi_solver/jagua_optimizer_task_index.md
codex/prompts/egyedi_solver/jagua_optimizer_master_runner.md
canvases/egyedi_solver/jagua_optimizer_t01_repo_and_source_audit.md
codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t01_repo_and_source_audit.yaml
codex/codex_checklist/egyedi_solver/jagua_optimizer_t01_repo_and_source_audit.md
```

Ha bármelyik hiányzik, állj meg `STATUS: BLOCKED` státusszal.

## Globális hard rules

```text
REAL_CODE_ONLY:
- Work only from actual repository files.
- Do not invent files, modules, APIs, functions, schemas, or test commands.
- If the expected element does not exist, report it as mismatch/blocker.
```

```text
NO_SILENT_GEOMETRY_LOSS:
- Do not drop holes, contours, item identities, quantities, transforms, or validation data silently.
```

```text
EXACT_VALIDATION_REQUIRED:
- Any task that produces or modifies nesting layout behavior must require exact final validation.
- Invalid layout cannot be accepted as success.
```

```text
CHECKLIST_REQUIRED:
- Update the task-specific checklist entries in jagua_optimizer_task_progress_checklist.md.
- A task cannot be PASS unless the relevant checklist items are checked or explicitly marked BLOCKED/DEVIATION with evidence.
```

## Scope

### Benne van

- Kódszintű audit.
- Path + line anchorok gyűjtése.
- Source audit markdown elkészítése.
- Report, checklist és progress checklist frissítése.
- Standard verify wrapper futtatása.

### Tilos

- Production runtime / solver viselkedés módosítása.
- `rust/vrs_solver/**`, `worker/**`, `api/**`, `vrs_nesting/**` módosítása, kivéve ha a canvas/YAML ezt explicit audit-outputként kéri. JG-01-ben nem kéri.
- Dependency módosítás.
- Külső web, külső git clone, külső vendor import.
- README-szintű, anchor nélküli audit.

## Végrehajtási lépések

### 1. Task azonosítása

Keresd meg a JG-01 definíciót itt:

```text
canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_canvas_yaml_runner_task_bontas.md
canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md
canvases/egyedi_solver/jagua_optimizer_task_index.md
```

Nyerd ki a task id-t, slugot, phase-t, dependencyt, expected outputokat, acceptance gate-et és checklist pontokat. Ha JG-00 nem látszik késznek vagy a JG-01 task nem található pontosan, `BLOCKED`.

### 2. Repo szabályok és YAML ellenőrzés

Validáld a goal YAML-t:

```bash
python3 - <<'PY'
import yaml
from pathlib import Path
p = Path('codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t01_repo_and_source_audit.yaml')
data = yaml.safe_load(p.read_text(encoding='utf-8'))
assert isinstance(data, dict), 'YAML top-level must be mapping'
assert isinstance(data.get('steps'), list) and data['steps'], 'YAML must contain non-empty steps list'
print('YAML_OK')
PY
```

Ellenőrizd, hogy nincs `/mnt/data`, `/tmp/task`, `C:\` vagy más sandbox-specifikus abszolút útvonal.

### 3. Valós kód audit

Auditáld legalább ezeket:

```text
rust/vrs_solver/Cargo.toml
rust/vrs_solver/Cargo.lock
rust/vrs_solver/src/main.rs
docs/solver_io_contract.md
vrs_nesting/runner/vrs_solver_runner.py
vrs_nesting/runner/solver_adapter.py
vrs_nesting/nesting/instances.py
scripts/validate_nesting_solution.py
worker/cavity_prepack.py
worker/cavity_validation.py
worker/result_normalizer.py
scripts/ensure_sparrow.sh
scripts/run_sparrow_smoketest.sh
vrs_nesting/runner/sparrow_runner.py
poc/sparrow_io/sparrow_commit.txt
```

Minden állítást path + line anchorral bizonyíts.

Kötelező audit kérdések:

1. Pontosan milyen `jagua-rs` verzió van bekötve?
2. A Rust solver ténylegesen mely `jagua-rs` primitiveket/API-kat használja?
3. A jelenlegi Rust solver csak feasibility/row-cursor baseline, vagy már optimizer-core?
4. Mit enged a `solver_io_contract.md` stock/part/sheet/hole szinten?
5. Hol történik a bináris feloldás, run-dir artifact mentés, timeout, output contract validation?
6. Hol van az adapter boundary a VRS solver és Sparrow között?
7. Mely meglévő validátorok adnak exact vagy near-exact végellenőrzési alapot?
8. Hol van a cavity-prepack, cavity validation és result expansion/restore logika?
9. Milyen Sparrow runner/fallback/smoketest minták használhatók későbbi keresési vagy gate mintának?
10. Van-e showstopper JG-02 indításához?

### 4. Source audit létrehozása

Hozd létre vagy frissítsd:

```text
docs/egyedi_solver/jagua_optimizer_source_audit.md
```

Kötelező szakaszok:

```text
# JG-01 Source Audit — jagua-rs + saját optimizer
## Scope and sources
## Repo rules and task source extraction
## Current vrs_solver state
## jagua-rs dependency and API usage
## Solver IO contract and runner boundary
## Existing validation anchors
## Cavity-prepack / expansion anchors
## Sparrow / search-pattern reuse anchors
## Rectangular Phase 1 readiness
## Irregular/remnant Phase 2 risks
## Hole/cavity Phase 3 risks
## License / dependency / build risks
## Reusable anchors table
## Blockers and REQUIRES_DECISION
## Recommendation for JG-02
```

A `Recommendation for JG-02` szakasz végén legyen explicit döntés:

```text
JG-02_STATUS: READY | BLOCKED | REQUIRES_DECISION
```

### 5. Checklist és report

Frissítsd:

```text
codex/codex_checklist/egyedi_solver/jagua_optimizer_t01_repo_and_source_audit.md
codex/reports/egyedi_solver/jagua_optimizer_t01_repo_and_source_audit.md
canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md
```

A task-specifikus checklistben csak azt pipáld ki, amit bizonyíték alátámaszt.

A globális progress checklist JG-01 státuszát csak akkor jelöld késznek, ha a source audit elkészült, a report DoD evidence matrix teljes, a verify lefutott, és nincs showstopper vagy az explicit döntés szerint JG-02 blokkolt. Ha nem módosítod a progress checklistet, a reportban írd le az okot.

### 6. Sanity parancsok

Futtasd, ha a környezet engedi:

```bash
cargo metadata --manifest-path rust/vrs_solver/Cargo.toml --no-deps >/dev/null
python3 -m pytest -q tests/test_solver_adapter_contract.py tests/worker/test_cavity_prepack.py tests/worker/test_cavity_validation.py tests/worker/test_result_normalizer_cavity_plan.py
```

Ha valamelyik környezeti dependency miatt nem fut, dokumentáld; ne találd ki a PASS-t.

### 7. Kötelező repo gate

Futtasd:

```bash
./scripts/verify.sh --report codex/reports/egyedi_solver/jagua_optimizer_t01_repo_and_source_audit.md
```

Ez hozza létre/frissíti:

```text
codex/reports/egyedi_solver/jagua_optimizer_t01_repo_and_source_audit.verify.log
```

Ha a gate piros, a JG-01 report státusza nem lehet PASS.

## Záró output

A végén a reportban és az ügynöki válaszban add meg:

```text
JG01_RESULT
STATUS: PASS | REVISE | BLOCKED
CREATED_OR_UPDATED:
- docs/egyedi_solver/jagua_optimizer_source_audit.md
- codex/codex_checklist/egyedi_solver/jagua_optimizer_t01_repo_and_source_audit.md
- codex/reports/egyedi_solver/jagua_optimizer_t01_repo_and_source_audit.md
- codex/reports/egyedi_solver/jagua_optimizer_t01_repo_and_source_audit.verify.log
VERIFY:
- ./scripts/verify.sh --report codex/reports/egyedi_solver/jagua_optimizer_t01_repo_and_source_audit.md
- PASS | FAIL | NOT_RUN
NEXT:
- JG-02 indítható / blokkolt / döntést igényel, indokkal
```
