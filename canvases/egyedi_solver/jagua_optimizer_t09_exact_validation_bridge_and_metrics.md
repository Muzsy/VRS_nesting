# JG-09 — jagua_optimizer_t09_exact_validation_bridge_and_metrics

## Funkció

A JG-09 feladat célja az exact validation bridge és a futási/metrikai zárás bevezetése a `jagua_optimizer_phase1_outer_only` útvonalhoz.

A JG-08 után a Rust solver már képes determinisztikus initial construction layoutot előállítani rectangular, outer-only Phase 1 inputokra. JG-09 feladata annak biztosítása, hogy a solver outputból **ne lehessen sikeres eredmény**, ha a független Python exact validator overlapot, stock-boundary hibát, sheet-index hibát, spacing/margin sértést vagy count mismatch-et talál.

A task nem minőségi optimizer és nem repair loop. A cél egy erős validációs és riportolási határ:

- Rust output contract audit és opcionális, backward-compatible metrics bővítés;
- Python runner oldali exact validation status és error rögzítés;
- invalid `ok`/`partial` layout runner szinten FAIL legyen;
- valid layout PASS legyen;
- report/meta tartalmazza: runtime, placed, unplaced, used_sheets, utilization;
- regression smoke script valid és negatív fixture-ökkel.

## Source of truth

A feladat kizárólag repo-beli, ellenőrizhető forrásokra épülhet:

- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `canvases/jagua_rs_sajat_optimizer/plan/deep-research-report.md`
- `canvases/jagua_rs_sajat_optimizer/plan/jagua_rs_sajat_optimizer_fejlesztesi_terv.md`
- `canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_canvas_yaml_runner_task_bontas.md`
- `canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md`
- `canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_master_plan.md`
- `canvases/egyedi_solver/jagua_optimizer_task_index.md`
- `codex/prompts/egyedi_solver/jagua_optimizer_master_runner.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t08_initial_construction_placer_v1.md`
- `docs/solver_io_contract.md`
- `rust/vrs_solver/src/io.rs`
- `rust/vrs_solver/src/main.rs`
- `rust/vrs_solver/src/adapter.rs`
- `rust/vrs_solver/src/optimizer/initializer.rs`
- `rust/vrs_solver/src/optimizer/candidates.rs`
- `vrs_nesting/runner/vrs_solver_runner.py`
- `vrs_nesting/nesting/instances.py`
- `scripts/smoke_jagua_initial_construction.py`
- `scripts/verify.sh`

Ha bármely kötelező tervdokumentum vagy dependency report hiányzik, a task `BLOCKED`.

## Dependency státusz és gate

**Közvetlen dependency:** JG-08.

JG-08 akkor tekinthető teljesültnek, ha:

- `codex/reports/egyedi_solver/jagua_optimizer_t08_initial_construction_placer_v1.md` létezik;
- első sora `PASS`;
- tartalmazza: `JG-09_STATUS: READY`;
- az aktuális kódban létezik a JG-08 construction placer útvonal (`optimizer/candidates.rs`, `optimizer/initializer.rs` vagy dokumentált ekvivalens);
- `scripts/smoke_jagua_initial_construction.py` PASS volt a report szerint.

**Jelen package-generálási megfigyelés:** a feltöltött snapshotban JG-08 report első sora `PASS`, és a report végén `JG-09_STATUS: READY` szerepel, ezért a JG-09 implementáció indítható.

## DISCOVERED_MISMATCH — régi fejlesztési terv vs aktuális task-bontás

A régebbi `canvases/jagua_rs_sajat_optimizer/plan/jagua_rs_sajat_optimizer_fejlesztesi_terv.md` JG-09-et még `Irregular sheet model spike` néven írja le. Az aktuális, JG-00 által létrehozott task-bontás és progress checklist szerint JG-09 már:

```text
JG-09 — jagua_optimizer_t09_exact_validation_bridge_and_metrics
```

**Proposed resolution:** a végrehajtó agent az aktuális `jagua_optimizer_canvas_yaml_runner_task_bontas.md`, `jagua_optimizer_task_progress_checklist.md`, `jagua_optimizer_master_plan.md` és JG-08 `JG-09_STATUS: READY` gate alapján dolgozzon. Irregular/remnant sheet spike nem része JG-09 scope-nak.

## Stratégiai háttér

A JG lánc Phase 1 célja egy valid rectangular multi-sheet solver felépítése hole nélkül. A JG-08 első elhelyezőt ad, de egy nesting solver ipari szempontból csak akkor fogadható el, ha az utolsó igazság egy független exact validator. A Rust solver saját candidate/boundary logikája nem lehet végső bizonyíték: a Python `validate_multi_sheet_output()` már ellenőrzi a v1 contractot, a sheet boundaryt, hole intersectiont, spacinget, margin sértést, duplicate instance-t, allowed rotationt, overlapot és coverage mismatch-et.

JG-09 ezt a meglévő validátort köti szigorú runner/report contractba: `ok` vagy `partial` solver output csak akkor maradhat sikeres, ha a validator PASS. Ha invalid, a runner hibával álljon meg, mentse a validation error bizonyítékot, és a report ne adhasson PASS-t.

## Valós kód audit megfigyelések a package-generáláskor

A friss snapshot alapján:

- `rust/vrs_solver/src/io.rs`
  - `SolverOutput` mezők: `contract_version`, `status`, `unsupported_reason`, `placements`, `unplaced`, `metrics`.
  - `Metrics` jelenleg: `placed_count`, `unplaced_count`, `sheet_count_used`, `seed`, `time_limit_s`, `project_name`.
  - Nincs explicit `runtime_sec`, `used_sheets`, `utilization`, `validation_status` mező a Rust outputban.
- `rust/vrs_solver/src/main.rs`
  - JSON inputot olvas, `adapter::solve(input)?` hívással outputot ír.
  - Jelenleg nincs futásidő mérés a Rust outputban.
- `rust/vrs_solver/src/adapter.rs`
  - Phase 1 profile esetén JG-08 `build_initial_layout()` útvonal fut.
  - Unsupported hole-os Phase 1 inputra `status="unsupported"` és `unsupported_reason` jön vissza.
- `vrs_nesting/runner/vrs_solver_runner.py`
  - importálja és hívja a `validate_multi_sheet_output(inp, out)` függvényt.
  - `_validate_contract_fields(snapshot_path, output_path)` hibát dob invalid outputra.
  - `unsupported` status esetén jelenleg exact validation nélkül tér vissza, ami elfogadható, ha nincsenek placements és explicit unsupported_reason van, de ezt JG-09-ben dokumentált meta státusszal kell lezárni.
  - `runner_meta.json` már tartalmaz `duration_sec`, `placements_count`, `unplaced_count`, `sheet_count_used`, de nincs explicit `validation_status`, `validation_error`, `used_sheets`, `utilization`.
- `vrs_nesting/nesting/instances.py`
  - `validate_multi_sheet_output(input_payload, output_payload)` exact validator létezik.
  - Ellenőrzi többek között: output status, placements/unplaced lista, sheet-index, stock coverage, margin, overlap, spacing, duplicate instance, allowed rotation, expected coverage.
  - Jelenleg `None`-t ad vissza, nincs külön metrics-visszatérési helper.
- `scripts/smoke_jagua_initial_construction.py`
  - valid/negative smoke mintákat használ, de nem dedikált runner-bridge teszt; JG-09-hez külön script kell.

## Scope

Benne van:

- exact validation bridge hardening a Python runnerben;
- invalid `ok`/`partial` output elutasítása akkor is, ha a Rust solver process exit code 0;
- validation státusz és error mentése `runner_meta.json`-ba;
- metrics kiegészítés legalább runner/report szinten: runtime, placed, unplaced, used_sheets, utilization;
- backward-compatible Rust `Metrics` bővítés opcionálisan, ha a runner/report contract ezt indokolja;
- `scripts/smoke_jagua_exact_validation_bridge.py` létrehozása;
- valid fixture PASS, overlap invalid fixture FAIL, out-of-sheet invalid fixture FAIL;
- unsupported status külön kezelése: nem valid success, csak explicit unsupported branch;
- report és task checklist frissítése;
- `JG-10_STATUS: READY` csak PASS + exact validation evidence + repo verify zöld esetén.

Tilos:

- JG-10 repair-search loop;
- JG-11 score model;
- irregular/remnant sheet provider;
- cavity-prepack vagy hole nesting;
- Phase 1 hole-os part elfogadása successful layoutként;
- invalid layout sikeresnek jelölése;
- exact validator gyengítése vagy kikapcsolása;
- silent geometry loss: holes, contours, item identity, quantity, transform vagy validation adat eltűntetése;
- jagua-rs típusok kiszivárogtatása a publikus VRS output/runner contractba;
- production UI/API módosítás.

## Kötelező hard rules

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

## Végrehajtási terv

### 1. Dependency preflight

- Olvasd el JG-08 reportját.
- Ha JG-08 report nincs, nem `PASS`, vagy nem tartalmaz `JG-09_STATUS: READY` jelzést, állj meg `BLOCKED` státusszal.
- Ellenőrizd, hogy JG-08 fő artifactjai léteznek: `optimizer/candidates.rs`, `optimizer/initializer.rs`, `scripts/smoke_jagua_initial_construction.py`.
- Dokumentáld a dependency evidence-t a reportban.

### 2. Exact validator bridge audit

- Vizsgáld meg `vrs_solver_runner.py` `_run_solver_with_paths()` és `_validate_contract_fields()` útvonalát.
- Vizsgáld meg `validate_multi_sheet_output()` negatív és pozitív viselkedését.
- Döntsd el, hogy kell-e publikus helper a runnerhez, például `validate_solver_output_and_collect_metrics(...)`. Ha igen, csak repo-konform, tesztelhető módon add hozzá.
- Dokumentáld, hogyan különül el: `valid`, `invalid`, `unsupported`, `solver_failed`, `timeout`.

### 3. Runner meta és metrics zárás

- A runner minden sikeres valid layout után írjon `validation_status="pass"` jellegű bizonyítékot a `runner_meta.json`-ba.
- Invalid layout esetén írjon `validation_status="fail"`, `validation_error=<validator error>` mezőket, majd hibával térjen vissza.
- Unsupported esetben legyen explicit `validation_status="skipped_unsupported"` vagy dokumentált ekvivalens, és ne legyen successful layoutként reportolva.
- A meta/report tartalmazza:
  - `duration_sec` vagy `runtime_sec`;
  - `placed_count`;
  - `unplaced_count`;
  - `sheet_count_used` vagy `used_sheets`;
  - `utilization`.
- A utilization definícióját dokumentáld. Javasolt: `placed_area / used_sheet_area`, ahol a placed area az elhelyezett part polygon területe, a used sheet area pedig a használt sheetek usable/outer területe. Ha a repo jelenlegi helperje mást támogat, dokumentáld a tényleges definíciót.

### 4. Rust output contract audit és opcionális bővítés

- Ellenőrizd, hogy a Rust `Metrics` mezők elegendők-e a runner/report elvárásaihoz.
- Ha Rust outputot bővítesz, csak backward-compatible módon tedd; a meglévő `contract_version`, `status`, `placements`, `unplaced`, `metrics` mezőknek maradniuk kell.
- Ha validation státusz kizárólag Python runner meta mezőben jelenik meg, ezt explicit dokumentáld: a final exact validation a runner felelőssége, nem a Rust solveré.

### 5. Smoke script

Hozd létre:

```text
scripts/smoke_jagua_exact_validation_bridge.py
```

Minimum ellenőrzések:

- valid rectangular Phase 1 fixture real solverrel → runner exit 0, `validation_status=pass`, exact validator PASS;
- fake vagy mutált solver output overlap-pal → runner exit != 0 vagy helper `ValueError`, `validation_status=fail` bizonyított;
- fake vagy mutált solver output out-of-sheet / invalid sheet-index hibával → runner exit != 0 vagy helper `ValueError`;
- unsupported Phase 1 hole-os fixture → nem valid success, explicit unsupported/skip branch;
- metrics presence: runtime/duration, placed, unplaced, used_sheets/sheet_count_used, utilization a meta/reportban;
- invalid `ok`/`partial` status soha nem tekinthető successful JG-09 eredménynek.

### 6. Report és checklist

- Frissítsd a task-specifikus checklistet.
- Frissítsd a globális `jagua_optimizer_task_progress_checklist.md` JG-09 szakaszát.
- A report tartalmazza a parancsokat, kimenet-részleteket, validation evidence-t és metrics example-t.
- Csak akkor írj `JG-10_STATUS: READY` sort, ha JG-09 PASS, exact validation bridge bizonyított, task smoke PASS, és repo verify PASS.

## Kötelező parancsok

Futtasd és dokumentáld:

```bash
cargo build --manifest-path rust/vrs_solver/Cargo.toml
cargo test --manifest-path rust/vrs_solver/Cargo.toml
python3 scripts/smoke_jagua_initial_construction.py
python3 scripts/smoke_jagua_exact_validation_bridge.py
./scripts/verify.sh --report codex/reports/egyedi_solver/jagua_optimizer_t09_exact_validation_bridge_and_metrics.md
```

Ha bármelyik környezeti okból elakad, dokumentáld pontosan. Ne adj PASS-t, ha az exact validator bridge vagy repo verify nem bizonyított.

## Acceptance criteria

JG-09 akkor PASS, ha:

- JG-08 dependency PASS és `JG-09_STATUS: READY` bizonyított;
- valid fixture PASS státuszt ad a runneren keresztül;
- overlap invalid fixture FAIL státuszt ad;
- out-of-sheet vagy invalid sheet-index fixture FAIL státuszt ad;
- invalid layout nem lehet successful;
- report/meta tartalmazza: runtime, placed, unplaced, used_sheets/sheet_count_used, utilization;
- validation status outputban vagy runner meta/reportban látható;
- partial success világosan elkülönül a valid successtől;
- task smoke és regression smoke fut;
- repo verify PASS és log mentve;
- checklist frissítve;
- `JG-10_STATUS: READY` csak bizonyított PASS után szerepel.

## Failure / rollback policy

- Ha a runner exact validation hardening megtöri a meglévő valid `vrs_solver_runner` smoke-okat, revertáld vagy javítsd a bridge-et, ne kapcsold ki a validátort.
- Ha Rust metrics bővítés contract-kompatibilitási kockázatot okoz, tartsd a bővítést Python runner meta/report szinten.
- Ha Shapely vagy dependency hiány miatt exact validator nem fut, JG-09 nem PASS; dokumentáld környezeti blockernek.
- Ha unsupported hole-os input successful layoutként jelenik meg, JG-09 FAIL.

## Phase gate

JG-09 Phase 1 validation gate. JG-10 repair search csak akkor indítható, ha JG-09 PASS és a report végén szerepel:

```text
JG-10_STATUS: READY
```
