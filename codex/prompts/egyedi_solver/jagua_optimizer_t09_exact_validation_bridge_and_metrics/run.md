# Runner prompt — JG-09 jagua_optimizer_t09_exact_validation_bridge_and_metrics

## Feladat

A helyi VRS_nesting repo gyökerében dolgozz. Hajtsd végre a JG-09 taskot:

```text
JG-09 — jagua_optimizer_t09_exact_validation_bridge_and_metrics
```

Ez a task a JG-08 után létrejött Phase 1 rectangular, outer-only solver outputját zárja össze a Python exact validatorral és a report/runner metrikákkal.

Ne készíts általános tervet. Olvasd el a megadott repo fájlokat, ellenőrizd a dependency-t, implementáld a scope-ot, futtasd a teszteket, frissítsd a checklistet és reportot.

---

## Kötelező dependency preflight

Mielőtt bármilyen kódot módosítasz, ellenőrizd:

```text
codex/reports/egyedi_solver/jagua_optimizer_t08_initial_construction_placer_v1.md
```

JG-08 feltételek:

- report létezik;
- első sora `PASS`;
- tartalmazza: `JG-09_STATUS: READY`;
- az aktuális kódban létezik `rust/vrs_solver/src/optimizer/candidates.rs`;
- az aktuális kódban létezik `rust/vrs_solver/src/optimizer/initializer.rs`;
- létezik `scripts/smoke_jagua_initial_construction.py`;
- a report bizonyítja, hogy a JG-08 initial construction smoke és exact validator PASS volt.

Ha bármelyik feltétel nem teljesül, állj meg:

```text
STATUS: BLOCKED
REASON: Missing or non-PASS dependency: JG-08
```

Ilyenkor ne implementálj JG-09 kódot, csak frissítsd a JG-09 reportot a dependency evidence-szel.

---

## Kötelező olvasmányok

Olvasd el:

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
canvases/egyedi_solver/jagua_optimizer_t09_exact_validation_bridge_and_metrics.md
codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t09_exact_validation_bridge_and_metrics.yaml
codex/codex_checklist/egyedi_solver/jagua_optimizer_t09_exact_validation_bridge_and_metrics.md
```

A `run.md` és a canvas az irányadó. Ha a régi fejlesztési terv JG-09 irregular sheet spike-ot említ, azt dokumentáld `DISCOVERED_MISMATCH` blokkal, és az aktuális task-bontást kövesd: JG-09 = exact validation bridge and metrics.

---

## Valós kód audit

Vizsgáld meg az aktuális kódot:

```text
rust/vrs_solver/src/io.rs
rust/vrs_solver/src/main.rs
rust/vrs_solver/src/adapter.rs
rust/vrs_solver/src/optimizer/initializer.rs
rust/vrs_solver/src/optimizer/candidates.rs
rust/vrs_solver/src/optimizer/mod.rs
vrs_nesting/runner/vrs_solver_runner.py
vrs_nesting/nesting/instances.py
scripts/smoke_jagua_initial_construction.py
scripts/check.sh
scripts/verify.sh
```

Külön ellenőrizd:

- a runner pontosan hol hívja a `validate_multi_sheet_output()` függvényt;
- invalid validator error esetén jelenleg mentődik-e meta/log bizonyíték;
- `unsupported` status hogyan kerül kezdetben vissza;
- hol vannak a jelenlegi metrics mezők (`duration_sec`, placements/unplaced/sheet_count_used);
- hogyan számolható determinisztikusan `used_sheets` és `utilization`;
- kell-e helper a `vrs_nesting/nesting/instances.py` modulba a metrics számításhoz;
- kell-e Rust `Metrics` bővítés vagy elég a runner meta/report.

---

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

---

## Implementációs scope

Implementáld a JG-09 exact validation bridge és metrics zárást.

Expected touched files, ha a dependency teljesül:

```text
vrs_nesting/runner/vrs_solver_runner.py
vrs_nesting/nesting/instances.py
rust/vrs_solver/src/io.rs
rust/vrs_solver/src/main.rs
rust/vrs_solver/src/adapter.rs
scripts/smoke_jagua_exact_validation_bridge.py
codex/codex_checklist/egyedi_solver/jagua_optimizer_t09_exact_validation_bridge_and_metrics.md
canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md
codex/reports/egyedi_solver/jagua_optimizer_t09_exact_validation_bridge_and_metrics.md
```

Csak akkor módosíts Rust `io.rs/main.rs/adapter.rs` fájlokat, ha tényleg szükséges. A meglévő v1 output mezőknek működniük kell:

```text
contract_version
status
placements
unplaced
metrics
```

### Exact validation bridge

Kötelező viselkedés:

- `status in (ok, partial)` csak exact validator PASS után lehet runner szinten sikeres;
- overlap, out-of-sheet, invalid sheet-index, duplicate instance, spacing/margin vagy coverage mismatch esetén a runner hibával térjen vissza;
- invalid output esetén mentődjön `runner_meta.json` vagy dokumentált log evidence legalább:
  - `validation_status = fail` vagy ekvivalens;
  - `validation_error` a validator hibaüzenettel;
  - `return_code`/duration/cmd bizonyíték;
- valid output esetén mentődjön:
  - `validation_status = pass` vagy ekvivalens;
  - `validation_error = null` vagy hiányzó mező;
  - `placed_count`, `unplaced_count`, `sheet_count_used` vagy `used_sheets`;
  - `utilization`.
- `unsupported` status nem valid success. Legyen explicit `validation_status = skipped_unsupported` vagy dokumentált ekvivalens, és csak akkor elfogadható, ha nincs placement és van `unsupported_reason`.

### Metrics definíció

Minimum report/meta mezők:

```text
runtime_sec vagy duration_sec
placed_count
unplaced_count
used_sheets vagy sheet_count_used
utilization
validation_status
validation_error
```

Javasolt utilization definíció:

```text
utilization = placed_area / used_sheet_area
```

ahol:

- `placed_area`: az elhelyezett instance-ek validált polygon területének összege;
- `used_sheet_area`: az érintett sheet indexek stock polygon területének összege, margin/hole kezelésnél a repo meglévő validator helperjeivel vagy dokumentált ekvivalenssel.

Ha a valós kód alapján egyszerűbb, determinisztikus definíciót választasz, dokumentáld pontosan a reportban.

---

## Smoke és negatív teszt elvárás

Hozd létre:

```text
scripts/smoke_jagua_exact_validation_bridge.py
```

A script illeszkedjen a meglévő JG smoke mintákhoz.

Minimum ellenőrzések:

1. Valid rectangular Phase 1 fixture:
   - runner exit 0;
   - exact validator PASS;
   - `validation_status=pass` evidence;
   - metrics jelen vannak.
2. Overlap-invalid output:
   - fake solver binary vagy mutált output segítségével invalid `ok`/`partial` outputot kell előállítani;
   - runner/helper ezt elutasítja;
   - `validation_status=fail` vagy validator error bizonyított.
3. Out-of-sheet / invalid sheet-index output:
   - runner/helper elutasítja.
4. Unsupported hole-os Phase 1 input:
   - nem valid success;
   - explicit unsupported/skip branch.
5. Regression:
   - `scripts/smoke_jagua_initial_construction.py` továbbra is PASS.

---

## Kötelező parancsok

Futtasd:

```bash
cargo build --manifest-path rust/vrs_solver/Cargo.toml
cargo test --manifest-path rust/vrs_solver/Cargo.toml
python3 scripts/smoke_jagua_initial_construction.py
python3 scripts/smoke_jagua_exact_validation_bridge.py
./scripts/verify.sh --report codex/reports/egyedi_solver/jagua_optimizer_t09_exact_validation_bridge_and_metrics.md
```

Ha bármelyik nem fut le környezeti okból, dokumentáld pontosan. Ne adj PASS-t, ha az exact validator bridge vagy repo verify nem bizonyított.

---

## Report és checklist

Frissítsd:

```text
codex/codex_checklist/egyedi_solver/jagua_optimizer_t09_exact_validation_bridge_and_metrics.md
canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md
codex/reports/egyedi_solver/jagua_optimizer_t09_exact_validation_bridge_and_metrics.md
```

A reportban legyen:

- dependency evidence;
- valós kód audit;
- validation bridge design döntés;
- metrics definíció;
- valid fixture output kivonat;
- invalid overlap és out-of-sheet rejection evidence;
- unsupported branch evidence;
- cargo/test/smoke/verify parancsok és eredmények;
- git status/diff summary;
- végső státusz.

Csak akkor zárd PASS-ra, ha minden acceptance gate teljesült. Csak akkor írd a report végére:

```text
JG-10_STATUS: READY
```

ha JG-09 PASS és repo verify zöld.

---

## Out of scope

Ne implementáld:

- JG-10 repair-search loop;
- JG-11 score/objective tuning;
- irregular/remnant sheet model;
- cavity-prepack vagy part-in-hole nesting;
- UI/API production változtatást;
- exact validator kikapcsolását vagy gyengítését.

---

## Végső válasz formátuma

```text
STATUS: PASS | REVISE | BLOCKED
SUMMARY:
- ...
FILES_CHANGED:
- ...
VALIDATION_EVIDENCE:
- ...
METRICS_EVIDENCE:
- ...
VERIFY:
- command: ...
- result: ...
- log: ...
NEXT_GATE:
- JG-10_STATUS: READY | NOT_READY
```
