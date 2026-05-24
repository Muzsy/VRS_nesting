# Runner prompt — JG-17 `jagua_optimizer_t17_irregular_boundary_validation`

## Feladat

A VRS_nesting repo gyökerében dolgozz. Hajtsd végre a JG-17 taskot:

```text
JG-17 — jagua_optimizer_t17_irregular_boundary_validation
```

Cél: irregular/remnant sheet boundary validation véglegesítése úgy, hogy item nem lóghat ki a usable stock polygonból, és invalid boundary layout nem lehet successful.

Ne készíts JG-18 candidate generationt, új optimizer searchöt, part-hole támogatást, stock-hole támogatást vagy cavity-prepack logikát. Ez a task boundary validation/policy/gate feladat.

## Kötelező olvasmányok

Először olvasd el:

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
canvases/egyedi_solver/jagua_optimizer_t17_irregular_boundary_validation.md
codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t17_irregular_boundary_validation.yaml
codex/codex_checklist/egyedi_solver/jagua_optimizer_t17_irregular_boundary_validation.md
```

## 1. Dependency gate

Mielőtt kódot módosítasz, ellenőrizd:

```text
codex/reports/egyedi_solver/jagua_optimizer_t16_irregular_sheet_provider_and_margin.md
docs/egyedi_solver/jagua_irregular_sheet_spike_decision.md
docs/solver_io_contract.md
```

JG-17 feltételek:

- JG-16 report létezik;
- JG-16 report első sora `PASS` vagy `PASS_WITH_NOTES`;
- JG-16 report tartalmazza: `JG-17_STATUS: READY`;
- JG-15 decision report létezik;
- JG-15 decision report tartalmazza: `JG-15_DECISION: OWN_BOUNDARY_VALIDATOR_PLUS_JAGUA_COLLISION`;
- `docs/solver_io_contract.md` dokumentálja a JG-16 irregular sheet boundary policy-t;
- nincs `STOP` / `NO-GO` / unresolved blocker, amely JG-17-et tiltja.

Ha bármelyik feltétel nem teljesül, állj meg:

```text
STATUS: BLOCKED
REASON: Missing or non-PASS dependency: JG-16
```

Ilyenkor ne módosíts Rust/Python runtime boundary kódot. Csak a JG-17 reportot frissítsd a dependency evidence-szel.

## 2. Valós kód audit

Auditáld az aktuális kódot:

```text
rust/vrs_solver/src/sheet.rs
rust/vrs_solver/src/geometry.rs
rust/vrs_solver/src/adapter.rs
rust/vrs_solver/src/io.rs
rust/vrs_solver/src/optimizer/mod.rs
rust/vrs_solver/src/optimizer/initializer.rs
rust/vrs_solver/src/optimizer/repair.rs
rust/vrs_solver/src/optimizer/score.rs
rust/vrs_solver/src/optimizer/multisheet.rs
vrs_nesting/nesting/instances.py
vrs_nesting/runner/vrs_solver_runner.py
docs/solver_io_contract.md
```

Külön ellenőrizd:

- `SheetShape.has_irregular_outer`, `area`, `_outer_poly`, `hole_polys` mezők aktuális állapota;
- `rect_inside_sheet_shape()` tényleges boundary logikája;
- corner containment és edge crossing policy;
- rectangular path regresszió-kockázata;
- `JaguaAdapter::check_rect_in_sheet()` használata;
- construction placer és repair milyen boundary helperre épül;
- ScoreModel boundary penalty milyen violations adatra épül;
- `optimizer/boundary.rs` létezik-e;
- Python exact validator `outer_points`, `sheet_poly.covers()`, `margin_mm` és invalid output kezelés;
- runner `validation_status=fail` útvonala.

## 3. Hard rules

```text
REAL_CODE_ONLY:
- Work only from actual repository files.
- Do not invent files, modules, APIs, functions, schemas, or test commands.
- If the expected element does not exist, report it as mismatch/blocker.
```

```text
NO_SILENT_GEOMETRY_LOSS:
- Do not drop holes, contours, item identities, quantities, transforms, margin data, or validation data silently.
- Container holes remain unsupported unless a later explicit task changes that contract.
```

```text
EXACT_VALIDATION_REQUIRED:
- Any accepted layout must pass the existing exact validation bridge.
- Invalid layout cannot be accepted as success.
- validation_status=fail is a hard failure.
```

```text
CHECKLIST_REQUIRED:
- Update the task-specific checklist entries in jagua_optimizer_task_progress_checklist.md.
- A task cannot be PASS unless the relevant checklist items are checked or explicitly marked BLOCKED/DEVIATION with evidence.
```

## 4. Implementációs scope

JG-17-ben implementáld vagy dokumentáltan delegáld:

1. Boundary validation policy layer:
   - új `rust/vrs_solver/src/optimizer/boundary.rs`, ha a valós kód alapján ez a repo-konform megoldás;
   - `rust/vrs_solver/src/optimizer/mod.rs` module export;
   - wrapper/facade a `rect_inside_sheet_shape()` logikára, ha a meglévő helper már helyes.
2. Boundary-touch policy:
   - dokumentáltan dönts arról, edge/corner touch mikor PASS/FAIL;
   - ha a jagua `SPolygon.collides_with(point)` boundary semantics nem teljesen bizonyított, safe-side policy-t alkalmazz és dokumentáld.
3. Construction/repair/score integration:
   - construction ne generáljon accepted placementet boundary fail esetén;
   - repair `find_violations()` boundary failt `BoundaryOrSheet` violationként kezeljen;
   - score boundary penalty továbbra is hard validity guard legyen.
4. Exact validation bridge:
   - Python exact validator továbbra is rejectálja a notch/outside placementet;
   - runner invalid output esetén `validation_status=fail` és error legyen, ne success.
5. Margin policy:
   - `margin_mm > 0` Phase 1 Rust runtime alatt ne legyen silent success;
   - ha marad `UNSUPPORTED_MARGIN_MM_RUNTIME`, azt smoke-ban bizonyítsd;
   - ne állíts runtime margin shrink supportot, ha nincs implementálva.

Kötelező outputok:

```text
rust/vrs_solver/src/optimizer/boundary.rs
rust/vrs_solver/src/optimizer/mod.rs
rust/vrs_solver/src/sheet.rs
rust/vrs_solver/src/adapter.rs
rust/vrs_solver/src/optimizer/initializer.rs
rust/vrs_solver/src/optimizer/repair.rs
rust/vrs_solver/src/optimizer/score.rs
docs/solver_io_contract.md
tests/fixtures/egyedi_solver/jagua_irregular_boundary_validation.json
scripts/smoke_jagua_irregular_boundary_validation.py
codex/reports/egyedi_solver/jagua_optimizer_t17_irregular_boundary_validation.md
codex/codex_checklist/egyedi_solver/jagua_optimizer_t17_irregular_boundary_validation.md
canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md
```

Ha valamelyik felsorolt runtime fájlt végül nem kell módosítani, dokumentáld a reportban. Ha további fájl kell, előbb frissítsd a YAML outputs listáját.

## 5. Fixture és smoke követelmények

Hozd létre:

```text
tests/fixtures/egyedi_solver/jagua_irregular_boundary_validation.json
scripts/smoke_jagua_irregular_boundary_validation.py
```

A smoke script bizonyítsa:

- rectangular stock provider/boundary regresszió nincs;
- L-shape/remnant stock `outer_points` input valid;
- positive control: item teljesen sheeten belül → PASS;
- negative control: item a konkáv notch régióban vagy sheeten kívül → FAIL;
- invalid boundary layout nem lehet successful;
- `margin_mm > 0` Phase 1-ben nem accepted/silent;
- exact validator és runner fail semantics működik.

## 6. Futtatandó parancsok

Minimálisan:

```bash
python3 scripts/smoke_jagua_irregular_boundary_validation.py
cargo test --manifest-path rust/vrs_solver/Cargo.toml
./scripts/verify.sh --report codex/reports/egyedi_solver/jagua_optimizer_t17_irregular_boundary_validation.md
```

Ha releváns és már létezik:

```bash
python3 scripts/smoke_jagua_irregular_sheet_provider.py
python3 scripts/smoke_jagua_exact_validation_bridge.py
```

Ha dependency vagy környezeti hiba miatt nem fut le, dokumentáld pontosan. Ne keverd össze az environment failt a solver minőségével.

## 7. Report követelmény

Frissítsd:

```text
codex/reports/egyedi_solver/jagua_optimizer_t17_irregular_boundary_validation.md
```

A report tartalmazza:

- első sor: `PASS`, `PASS_WITH_NOTES`, `FAIL` vagy `BLOCKED`;
- dependency evidence;
- valós kód audit summary;
- boundary validation policy;
- boundary-touch policy;
- proxy vs exact boundary check viszonya;
- positive és negative fixture evidence;
- margin policy evidence;
- invalid layout fail evidence;
- futtatott parancsok;
- checklist update státusz;
- risks/blockers.

Csak akkor írd bele:

```text
JG-18_STATUS: READY
```

ha minden acceptance gate PASS, a repo verify zöld, és nincs unresolved boundary/margin/validation blocker.

## 8. Végső válasz formátuma

```text
STATUS: PASS | PASS_WITH_NOTES | FAIL | BLOCKED
SUMMARY:
- ...
CHANGED_FILES:
- ...
VERIFY:
- command: ...
- result: ...
BLOCKERS:
- ...
NEXT:
- JG-18_STATUS: READY | not ready
```
