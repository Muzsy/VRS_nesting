# Runner prompt — JG-16 `jagua_optimizer_t16_irregular_sheet_provider_and_margin`

## Feladat

A helyi VRS_nesting repóban hajtsd végre a JG-16 taskot:

```text
JG-16 — `jagua_optimizer_t16_irregular_sheet_provider_and_margin`
```

Ez a task a Phase 2 irregular/remnant sheet provider és margin kezelés bevezetése. Nem capability spike és nem JG-17 boundary validation véglegesítés. A JG-15 döntési report alapján dolgozz.

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
canvases/egyedi_solver/jagua_optimizer_t16_irregular_sheet_provider_and_margin.md
codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t16_irregular_sheet_provider_and_margin.yaml
codex/codex_checklist/egyedi_solver/jagua_optimizer_t16_irregular_sheet_provider_and_margin.md
```

## 1. Dependency gate

Mielőtt kódot módosítasz, ellenőrizd:

```text
codex/reports/egyedi_solver/jagua_optimizer_t15_irregular_sheet_capability_spike.md
docs/egyedi_solver/jagua_irregular_sheet_spike_decision.md
```

JG-15 feltételek:

- a report létezik;
- első sora `PASS` vagy `PASS_WITH_NOTES`;
- tartalmazza: `JG-16_STATUS: READY`;
- a decision report létezik;
- a decision report egyértelműen kimondja, hogy JG-16 melyik irányt kövesse:
  - natív jagua irregular boundary; vagy
  - saját boundary validator + jagua item-item collision;
- nincs `STOP` / `NO-GO` döntés, amely JG-16-ot tiltja.

Ha bármelyik feltétel nem teljesül, állj meg:

```text
STATUS: BLOCKED
REASON: Missing or non-PASS dependency: JG-15
```

Ilyenkor ne módosíts Rust/Python runtime provider kódot. Csak a JG-16 reportot frissítsd a dependency evidence-szel.

## 2. Valós kód audit

Auditáld az aktuális kódot:

```text
rust/vrs_solver/src/sheet.rs
rust/vrs_solver/src/geometry.rs
rust/vrs_solver/src/adapter.rs
rust/vrs_solver/src/io.rs
rust/vrs_solver/src/optimizer/initializer.rs
rust/vrs_solver/src/optimizer/repair.rs
rust/vrs_solver/src/optimizer/multisheet.rs
vrs_nesting/nesting/instances.py
vrs_nesting/runner/vrs_solver_runner.py
docs/solver_io_contract.md
```

Külön ellenőrizd:

- `Stock.outer_points` és `Stock.holes_points` Rust parse állapotát;
- `SheetShape._outer_poly`, bbox és hole_polys mezőket;
- `rect_inside_sheet_shape()` tényleges boundary logikáját;
- van-e Rust oldali usable polygon / margin shrink;
- a Python exact validator `outer_points` + `margin_mm` kezelését;
- a `docs/solver_io_contract.md` JG-05 margin/spacing deviation szakaszát;
- a runner `validation_status` fail/pass kezelését.

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
- Container holes remain unsupported in JG-16.
- If stock.holes_points is present and non-empty, return/document unsupported; do not ignore it.
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

JG-16-ban implementáld vagy explicit unsupportedként dokumentáld:

1. Irregular/remnant stock provider `Stock.outer_points` alapján.
2. Sheet model explicit outer polygon + bbox + area metadata.
3. Usable polygon vagy conservative usable boundary policy.
4. Margin kezelés:
   - ha `margin_mm` Rust runtime mezővé válik, frissítsd `SolverInput` parse-t és contractot;
   - ha nem válik runtime mezővé, marginos irregular input nem zárható sikeresként silent ignore mellett.
5. Too-narrow remnant deterministic unsupported/fail reason.
6. Container hole tiltás: non-empty `stock.holes_points` unsupported.
7. Rectangular provider regressziómentesség.

Kötelező outputok:

```text
rust/vrs_solver/src/sheet.rs
rust/vrs_solver/src/geometry.rs
docs/solver_io_contract.md
tests/fixtures/egyedi_solver/jagua_irregular_margin.json
scripts/smoke_jagua_irregular_sheet_provider.py
codex/reports/egyedi_solver/jagua_optimizer_t16_irregular_sheet_provider_and_margin.md
codex/codex_checklist/egyedi_solver/jagua_optimizer_t16_irregular_sheet_provider_and_margin.md
```

Ha `rust/vrs_solver/src/io.rs` vagy `rust/vrs_solver/src/adapter.rs` módosítása szükséges, a YAML alapján ez engedett. Ha további fájl kell, előbb frissítsd a YAML outputs listáját.

## 5. Fixture és smoke követelmények

Hozd létre:

```text
tests/fixtures/egyedi_solver/jagua_irregular_margin.json
scripts/smoke_jagua_irregular_sheet_provider.py
```

A smoke script bizonyítsa:

- rectangular stock provider továbbra is működik;
- L-shape/remnant stock `outer_points` input valid;
- margin policy eredménye riportolható;
- too-narrow remnant deterministic unsupported/fail;
- non-empty stock `holes_points` nem accepted/silent;
- exact validation gate fut, invalid layout nem success.

## 6. Futtatandó parancsok

Minimálisan:

```bash
python3 scripts/smoke_jagua_irregular_sheet_provider.py
cargo test --manifest-path rust/vrs_solver/Cargo.toml
./scripts/verify.sh --report codex/reports/egyedi_solver/jagua_optimizer_t16_irregular_sheet_provider_and_margin.md
```

Ha dependency vagy környezeti hiba miatt nem fut le, dokumentáld pontosan. Ne keverd össze az environment failt a solver minőségével.

## 7. Report követelmény

Frissítsd:

```text
codex/reports/egyedi_solver/jagua_optimizer_t16_irregular_sheet_provider_and_margin.md
```

A report tartalmazza:

- első sor: `PASS`, `PASS_WITH_NOTES`, `FAIL` vagy `BLOCKED`;
- dependency evidence;
- JG-15 decision evidence;
- valós kód audit summary;
- margin policy döntés;
- implemented/unsupported scope;
- shape metadata és usable region adatok;
- fixture és smoke eredmények;
- exact validation evidence;
- futtatott parancsok;
- checklist update státusz;
- risks/blockers.

Csak akkor írd bele:

```text
JG-17_STATUS: READY
```

ha minden acceptance gate PASS, a repo verify zöld, és nincs unresolved margin/sheet provider blocker.

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
- JG-17_STATUS: READY | not ready
```
