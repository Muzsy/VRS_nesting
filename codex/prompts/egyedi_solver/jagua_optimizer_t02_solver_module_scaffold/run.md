# Runner — JG-02 jagua_optimizer_t02_solver_module_scaffold

## Feladat

A VRS_nesting repo gyökerében dolgozz. Hajtsd végre a JG-02 architecture/refactor taskot:

```text
JG-02 — jagua_optimizer_t02_solver_module_scaffold
```

Ez viselkedésmegőrző Rust refaktor. **Ne implementálj új solver algoritmust.**

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
docs/egyedi_solver/jagua_optimizer_source_audit.md
canvases/egyedi_solver/jagua_optimizer_t02_solver_module_scaffold.md
codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t02_solver_module_scaffold.yaml
codex/codex_checklist/egyedi_solver/jagua_optimizer_t02_solver_module_scaffold.md
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

- `rust/vrs_solver/src/main.rs` viselkedésmegőrző modularizálása.
- Új Rust modulok létrehozása:
  - `rust/vrs_solver/src/io.rs`
  - `rust/vrs_solver/src/geometry.rs`
  - `rust/vrs_solver/src/sheet.rs`
  - `rust/vrs_solver/src/item.rs`
  - `rust/vrs_solver/src/adapter.rs`
  - `rust/vrs_solver/src/optimizer/mod.rs`
- A `main.rs` CLI/orchestration szerepre szűkítése.
- Baseline és refaktor utáni output szemantikai összehasonlítása.
- Rust build, validator, repo verify.
- Report, task checklist, globális progress checklist frissítése.

### Tilos

- Új optimizer algoritmus, score model, candidate generation, repair loop, SA vagy Sparrow-style search implementálása.
- `jagua-rs` magasabb szintű API bekötése teljes adapterként. Ez JG-04 scope.
- Outer-only hole gate implementálása. Ez JG-03 scope.
- IO contract kompatibilitást törő módosítása.
- `Cargo.toml` dependency/feature/verzió módosítása.
- Python runner, cavity-prepack, DXF, API vagy worker runtime módosítása.
- Bármely olyan fájl módosítása, amely nem szerepel a JG-02 goal YAML outputs listájában.

## Végrehajtási lépések

### 1. Task és dependency ellenőrzés

Keresd meg a JG-02 definíciót itt:

```text
canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_canvas_yaml_runner_task_bontas.md
canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md
canvases/egyedi_solver/jagua_optimizer_task_index.md
```

Ellenőrizd:

- task id: `JG-02`;
- slug: `jagua_optimizer_t02_solver_module_scaffold`;
- phase: `Phase 0 / architecture`;
- dependency: `JG-01`;
- acceptance gate: cargo build + output equivalence + repo gate;
- JG-01 report első sora `PASS`;
- `docs/egyedi_solver/jagua_optimizer_source_audit.md` tartalmazza: `JG-02_STATUS: READY`.

Ha bármelyik nem igazolható, `BLOCKED`.

### 2. Goal YAML sanity

Validáld a goal YAML-t:

```bash
python3 - <<'PY'
import yaml
from pathlib import Path
p = Path('codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t02_solver_module_scaffold.yaml')
data = yaml.safe_load(p.read_text(encoding='utf-8'))
assert isinstance(data, dict), 'YAML top-level must be mapping'
assert isinstance(data.get('steps'), list) and data['steps'], 'YAML must contain non-empty steps list'
for i, step in enumerate(data['steps'], 1):
    assert isinstance(step.get('name'), str) and step['name'].strip(), f'step {i} missing name'
    assert isinstance(step.get('description'), str) and step['description'].strip(), f'step {i} missing description'
    assert isinstance(step.get('outputs'), list) and step['outputs'], f'step {i} missing outputs'
print('YAML_OK')
PY
```

Ellenőrizd, hogy nincs sandbox-specifikus vagy lokális abszolút útvonal a YAML-ben.

### 3. Baseline rögzítése refaktor előtt

Olvasd el és dokumentáld a jelenlegi `rust/vrs_solver/src/main.rs` viselkedését.

Minimum baseline elemek:

- input DTO-k;
- output DTO-k;
- `contract_version`;
- `stock_to_shape()` és `expand_sheets()` szemantika;
- `normalize_allowed_rotations()`;
- `expand_instances()` rendezés;
- `try_place_on_sheet()` row/cursor heurisztika;
- `rect_inside_sheet_shape()` hole-aware ellenőrzés;
- unit tesztek;
- main orchestration flow.

Futtasd refaktor előtt:

```bash
cargo build --release --manifest-path rust/vrs_solver/Cargo.toml
```

Ezután futtasd a meglévő vrs_solver smoke útvonalat. A repo meglévő mintája a `scripts/check.sh` vrs_solver blokkja, amely:

- ideiglenes `solver_input.json`-t ír;
- `python3 -m vrs_nesting.runner.vrs_solver_runner` útvonalon futtatja a binaryt;
- `python3 scripts/validate_nesting_solution.py --run-dir <run_dir>` validátort hív;
- determinism hash smoke-ot futtat.

A baseline outputot ne commitold feleslegesen. A reportba a parancsokat, run-dir útvonalat, normalizált JSON összehasonlítás lényegét és hash-t írd be.

### 4. Modulstruktúra kialakítása

Refaktoráld a kódot viselkedésváltozás nélkül.

Célfájlok:

```text
rust/vrs_solver/src/io.rs
rust/vrs_solver/src/geometry.rs
rust/vrs_solver/src/sheet.rs
rust/vrs_solver/src/item.rs
rust/vrs_solver/src/adapter.rs
rust/vrs_solver/src/optimizer/mod.rs
rust/vrs_solver/src/main.rs
```

Javasolt felosztás:

```text
io.rs
- SolverInput
- SolverOutput
- Placement
- Unplaced
- Metrics

geometry.rs
- PointInput
- Point
- Rect
- point_from_input()
- polygon_bbox()
- to_jag_point()
- to_jag_polygon()
- jag_edge_from_points()
- rect_corners()
- rect_edges()

sheet.rs
- Stock
- SheetShape
- stock_to_shape()
- expand_sheets()
- rect_inside_sheet_shape()

item.rs
- Part
- Instance
- normalize_allowed_rotations()
- dims_for_rotation()
- rotated_bbox_min_offset()
- placement_anchor_from_rect_min()
- can_fit_any_stock()
- expand_instances()

adapter.rs
- solve(input: SolverInput) -> Result<SolverOutput, String>
- solver orchestration, metrics assembly

optimizer/mod.rs
- SheetCursor
- try_place_on_sheet()
- row/cursor baseline placement

main.rs
- mod declarations
- parse_args()
- file read/write
- serde_json parse/write
- adapter::solve()
```

A pontos felosztást a Rust visibility/import szabályokhoz igazítsd, de a viselkedés nem változhat.

### 5. Validation mismatch kezelése

A task bontás `validation` fókuszt is említ, de a hivatalos JG-02 output lista nem tartalmazza:

```text
rust/vrs_solver/src/validation.rs
```

Default döntés:

- Ne hozz létre `validation.rs`-t.
- A validációs fókuszt a meglévő Python exact validator futtatása és a behavior-equivalence bizonyítása jelenti.

Ha mégis szükséges lenne `validation.rs`, előbb dokumentáld `REQUIRES_DECISION` blokkban, és csak YAML outputs frissítése után dolgozz rajta.

### 6. Refaktor utáni ellenőrzés

Futtasd:

```bash
cargo build --release --manifest-path rust/vrs_solver/Cargo.toml
```

Ha vannak releváns Rust unit tesztek:

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml
```

Futtasd ugyanazt a smoke inputot, mint baseline előtt.

Kötelező output-equivalence ellenőrzés:

- normalizált JSON összehasonlítás;
- `placements`;
- `unplaced`;
- `metrics.placed_count`;
- `metrics.unplaced_count`;
- `metrics.sheet_count_used`;
- `instance_id`, `part_id`, `sheet_index`, `x`, `y`, `rotation_deg`;
- validator PASS.

Ha byte-for-byte eltérés van, de normalizált JSON egyezik, dokumentáld.

### 7. Report és checklist

Frissítsd:

```text
codex/reports/egyedi_solver/jagua_optimizer_t02_solver_module_scaffold.md
codex/codex_checklist/egyedi_solver/jagua_optimizer_t02_solver_module_scaffold.md
canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md
```

A reportban kötelező szakaszok:

- status;
- scope;
- baseline summary;
- module split summary;
- changed files;
- behavior change YES/NO table;
- output-equivalence evidence;
- validation evidence;
- cargo build/test evidence;
- verify evidence;
- diff summary;
- blockers/deviations;
- JG-03 readiness decision.

### 8. Standard repo verify

Futtasd:

```bash
./scripts/verify.sh --report codex/reports/egyedi_solver/jagua_optimizer_t02_solver_module_scaffold.md
```

A log helye:

```text
codex/reports/egyedi_solver/jagua_optimizer_t02_solver_module_scaffold.verify.log
```

Ha a környezet miatt nem fut le, különítsd el:

- production kódhiba;
- Rust build hiba;
- Python dependency hiba;
- külső binary hiba;
- meglévő repo-hiba.

Nincs tiszta PASS piros vagy hiányzó verify mellett.

## Végső válasz formátuma

```text
STATUS: PASS | REVISE | BLOCKED

SUMMARY:
- ...

BASELINE:
- ...

MODULE_SPLIT:
- ...

VERIFY:
- cargo build: ...
- cargo test: ...
- repo verify: ...
- log: ...

CHANGED_FILES:
- ...

BEHAVIOR_CHANGE:
- YES/NO table location: ...

CHECKLIST:
- ...

NEXT:
- JG-03 ready: yes/no
```

Csak bizonyított, repo-ból ellenőrzött tényeket írj.
