# Runner prompt — JG-15 `jagua_optimizer_t15_irregular_sheet_capability_spike`

## Feladat

A helyi VRS_nesting repóban hajtsd végre a JG-15 taskot:

```text
JG-15 — `jagua_optimizer_t15_irregular_sheet_capability_spike`
```

Ez egy **capability spike**, nem production irregular sheet provider. A cél annak eldöntése, hogy a jelenlegi `jagua-rs` integráció használható-e natív irregular/remnant sheet boundary kezelésre, vagy saját boundary validator kell a jagua item-item collision mellé.

## 0. Repo és szabályok

Dolgozz a repo gyökerében. Ne használj külső webet. Ne dolgozz repo-n kívül.

Elsőként olvasd el:

```text
AGENTS.md
docs/codex/overview.md
docs/codex/yaml_schema.md
docs/codex/report_standard.md
docs/qa/testing_guidelines.md
canvases/jagua_rs_sajat_optimizer/plan/deep-research-report.md
canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_canvas_yaml_runner_task_bontas.md
canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_master_plan.md
canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md
canvases/jagua_rs_sajat_optimizer/plan/jagua_rs_sajat_optimizer_fejlesztesi_terv.md
canvases/egyedi_solver/jagua_optimizer_t15_irregular_sheet_capability_spike.md
codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t15_irregular_sheet_capability_spike.yaml
codex/codex_checklist/egyedi_solver/jagua_optimizer_t15_irregular_sheet_capability_spike.md
```

## 1. Dependency gate

Mielőtt kódot módosítasz, ellenőrizd:

```text
codex/reports/egyedi_solver/jagua_optimizer_t14_phase1_benchmark_matrix.md
scripts/bench_jagua_optimizer_phase1_rectangular.py
codex/reports/egyedi_solver/jagua_optimizer_phase1_rectangular_benchmark.md
```

Kötelező feltételek:

- JG-14 report létezik;
- JG-14 report első sora `PASS`;
- JG-14 report tartalmazza: `PHASE1_GATE_DECISION: PASS`;
- JG-14 report tartalmazza: `JG-15_STATUS: READY`.

Ha bármelyik hiányzik, állj meg `BLOCKED` státusszal, és csak reportot/checklistet frissíts. Ne hozz létre spike kódot sikeresként.

## 2. Valós kód audit

Auditáld és idézd a reportban a következő fájlok releváns pontjait:

```text
rust/vrs_solver/src/sheet.rs
rust/vrs_solver/src/geometry.rs
rust/vrs_solver/src/adapter.rs
rust/vrs_solver/src/optimizer/initializer.rs
rust/vrs_solver/src/optimizer/repair.rs
rust/vrs_solver/src/optimizer/multisheet.rs
rust/vrs_solver/src/io.rs
rust/vrs_solver/Cargo.toml
vrs_nesting/nesting/instances.py
vrs_nesting/runner/vrs_solver_runner.py
scripts/bench_jagua_optimizer_phase1_rectangular.py
scripts/smoke_jagua_exact_validation_bridge.py
scripts/check.sh
scripts/verify.sh
```

Külön bizonyítsd vagy cáfold:

- `Stock.outer_points` támogatott-e Rust oldalon;
- `SheetShape._outer_poly` ténylegesen használva van-e boundary checkben;
- `rect_inside_sheet_shape()` csak bbox+hole ellenőrzés-e;
- a Python exact validator `outer_points` alapján felismeri-e az L-shape boundary violationt;
- van-e már repóban natív jagua container/bin irregular boundary wrapper.

## 3. Tervverzió-eltérés kezelése

A reportban legyen explicit blokk:

```text
DISCOVERED_MISMATCH:
- old plan says: Task JG-15 — Multi-child cavity-prepack V2
- current task breakdown says: JG-15 — jagua_optimizer_t15_irregular_sheet_capability_spike
- resolution: follow current task breakdown/checklist/master-runner chain; do not implement cavity-prepack in JG-15
```

## 4. Implementációs scope

Hozd létre / frissítsd kizárólag a YAML outputsban szereplő fájlokat.

Kötelező új outputok:

```text
rust/vrs_solver/src/bin/jagua_irregular_sheet_spike.rs
tests/fixtures/egyedi_solver/jagua_irregular_l_shape.json
scripts/smoke_jagua_irregular_sheet_spike.py
docs/egyedi_solver/jagua_irregular_sheet_spike_decision.md
codex/reports/egyedi_solver/jagua_optimizer_t15_irregular_sheet_capability_spike.md
codex/codex_checklist/egyedi_solver/jagua_optimizer_t15_irregular_sheet_capability_spike.md
canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md
```

Ne implementáld JG-16 irregular sheet providert. Ne implementálj cavity-prepacket. Ne vezess be item-hole vagy stock-hole supportot.

## 5. Fixture elvárás

A fixture:

```text
tests/fixtures/egyedi_solver/jagua_irregular_l_shape.json
```

Legyen:

- `contract_version = v1`;
- legalább egy `stock.outer_points` L-alakú / konkáv polygon;
- stock `holes_points` ne legyen, vagy legyen üres lista;
- item hole ne legyen;
- legalább egy pozitív kontroll placement teljesen az L-shape-en belül;
- legalább egy negatív kontrollhelyzet, amely bbox szerint belül van, de a notch-ba lógna.

## 6. Rust spike bin

Hozd létre:

```text
rust/vrs_solver/src/bin/jagua_irregular_sheet_spike.rs
```

A bin futása adjon grep-elhető döntési sorokat:

```text
NATIVE_BOUNDARY_SUPPORT: YES | NO | UNKNOWN
OWN_BOUNDARY_VALIDATOR_REQUIRED: YES | NO
L_SHAPE_BOUNDARY_VIOLATION_DETECTED: YES | NO
CURRENT_BBOX_ONLY_RISK_DETECTED: YES | NO
DECISION: NATIVE_JAGUA_BOUNDARY | OWN_BOUNDARY_VALIDATOR_PLUS_JAGUA_COLLISION | REVISE
```

Ne találj ki nem létező `jagua-rs` API-t. Ha a crate lokális source/registry alapján nincs natív container boundary API, dokumentáld. A binnek akkor is futnia kell, és saját döntési sort kell adnia.

## 7. Smoke script

Hozd létre:

```text
scripts/smoke_jagua_irregular_sheet_spike.py
```

A script minimum:

1. ellenőrzi a fixture létezését és JSON validitását;
2. ellenőrzi, hogy a fixture hole-free;
3. ellenőrzi, hogy van konkáv `outer_points` stock;
4. buildeli/futtatja a Rust spike bin-t;
5. ellenőrzi, hogy a döntési sorok jelen vannak;
6. ellenőrzi, hogy boundary violation felismerhető;
7. futtat vagy direkt meghív olyan exact validation kontrollt, amely invalid L-shape placementre FAIL-t vár;
8. futtat legalább egy item-item collision regressziós kontrollt, ha repo-konform módon elérhető;
9. ellenőrzi, hogy a döntési reportban van `JG-15_DECISION:` sor;
10. PASS/FAIL összegzést ír.

## 8. Decision report

Hozd létre:

```text
docs/egyedi_solver/jagua_irregular_sheet_spike_decision.md
```

A report végén legyen pontos sor:

```text
JG-15_DECISION: NATIVE_JAGUA_BOUNDARY | OWN_BOUNDARY_VALIDATOR_PLUS_JAGUA_COLLISION | REVISE | STOP
```

Ha nincs bizonyított natív jagua boundary support, de a saját boundary validator + jagua collision út működőképesnek látszik, akkor ez legyen a döntés:

```text
JG-15_DECISION: OWN_BOUNDARY_VALIDATOR_PLUS_JAGUA_COLLISION
```

Ha a döntés nem `STOP`, a JG-15 implementation reportban szerepelhet:

```text
JG-16_STATUS: READY
```

## 9. Tesztek és gate

Futtasd és dokumentáld:

```bash
cargo build --manifest-path rust/vrs_solver/Cargo.toml --bin jagua_irregular_sheet_spike
cargo run --manifest-path rust/vrs_solver/Cargo.toml --bin jagua_irregular_sheet_spike
python3 scripts/smoke_jagua_irregular_sheet_spike.py
python3 scripts/bench_jagua_optimizer_phase1_rectangular.py
python3 scripts/smoke_jagua_exact_validation_bridge.py
cargo test --manifest-path rust/vrs_solver/Cargo.toml
./scripts/verify.sh --report codex/reports/egyedi_solver/jagua_optimizer_t15_irregular_sheet_capability_spike.md
```

Ha egy parancs a valós repo alapján nem futtatható, dokumentáld pontosan, és csak akkor adj `BLOCKED` státuszt, ha emiatt a döntés nem bizonyítható.

## 10. Checklist és report

Frissítsd:

```text
codex/codex_checklist/egyedi_solver/jagua_optimizer_t15_irregular_sheet_capability_spike.md
canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md
codex/reports/egyedi_solver/jagua_optimizer_t15_irregular_sheet_capability_spike.md
```

A report első sora legyen:

```text
PASS
```

csak akkor, ha:

- dependency gate PASS;
- fixture, bin, smoke és decision report elkészült;
- boundary violation felismerése bizonyított;
- döntés konkrét;
- task checklist pipálva;
- repo verify PASS.

Egyébként az első sor legyen `REVISE` vagy `BLOCKED`, bizonyítékkal.

## Hard rules

```text
REAL_CODE_ONLY:
- Work only from actual repository files.
- Do not invent files, modules, APIs, functions, schemas, or test commands.
- If the expected element does not exist, report it as mismatch/blocker.
```

```text
NO_SILENT_GEOMETRY_LOSS:
- Do not drop holes, contours, item identities, quantities, transforms, or validation data silently.
- Do not silently reinterpret an irregular sheet as its bounding box.
```

```text
EXACT_VALIDATION_REQUIRED:
- Any boundary-violating output must be rejected by exact validation.
- Invalid layout cannot be accepted as success.
```

```text
CHECKLIST_REQUIRED:
- Update the task-specific checklist entries in jagua_optimizer_task_progress_checklist.md.
- A task cannot be PASS unless the relevant checklist items are checked or explicitly marked BLOCKED/DEVIATION with evidence.
```

## Végső válasz formátum

```text
STATUS: PASS | REVISE | BLOCKED
SUMMARY:
- ...
CREATED_OR_MODIFIED:
- ...
DECISION:
- JG-15_DECISION: ...
VERIFY:
- command: ...
- result: ...
- log: ...
NEXT:
- JG-16_STATUS: READY | BLOCKED | REVISE_REQUIRED
```
