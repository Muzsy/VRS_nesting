# Runner prompt — JG-10 jagua_optimizer_t10_repair_search_loop_v1

## Feladat

A helyi VRS_nesting repo gyökerében dolgozz. Hajtsd végre a JG-10 taskot:

```text
JG-10 — jagua_optimizer_t10_repair_search_loop_v1
```

Ez a task a JG-08 initial construction és a JG-09 exact validation bridge után bevezeti a Phase 1 rectangular / outer-only repair-search V1-et.

Ne készíts általános tervet. Olvasd el a megadott repo fájlokat, ellenőrizd a dependency-t, implementáld a scope-ot, futtasd a teszteket, frissítsd a checklistet és reportot.

---

## Kötelező dependency preflight

Mielőtt bármilyen kódot módosítasz, ellenőrizd:

```text
codex/reports/egyedi_solver/jagua_optimizer_t09_exact_validation_bridge_and_metrics.md
```

JG-09 feltételek:

- report létezik;
- első sora `PASS`;
- tartalmazza: `JG-10_STATUS: READY`;
- létezik `scripts/smoke_jagua_exact_validation_bridge.py`;
- létezik `vrs_nesting/runner/vrs_solver_runner.py` JG-09 validation_status / validation_error / utilization mezőkkel;
- a report bizonyítja, hogy invalid output nem lehet successful.

Ha bármelyik feltétel nem teljesül, állj meg:

```text
STATUS: BLOCKED
REASON: Missing or non-PASS dependency: JG-09
```

Ilyenkor ne implementálj JG-10 kódot, csak frissítsd a JG-10 reportot dependency evidence-szel.

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
canvases/egyedi_solver/jagua_optimizer_t10_repair_search_loop_v1.md
codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t10_repair_search_loop_v1.yaml
codex/codex_checklist/egyedi_solver/jagua_optimizer_t10_repair_search_loop_v1.md
```

A `run.md` és a canvas az irányadó. Ha a régi fejlesztési terv JG-10 irregular sheet providert említ, dokumentáld `DISCOVERED_MISMATCH` blokkal, és az aktuális task-bontást kövesd: JG-10 = repair search loop V1.

---

## Valós kód audit

Vizsgáld meg az aktuális kódot:

```text
rust/vrs_solver/src/optimizer/mod.rs
rust/vrs_solver/src/optimizer/state.rs
rust/vrs_solver/src/optimizer/moves.rs
rust/vrs_solver/src/optimizer/score.rs
rust/vrs_solver/src/optimizer/candidates.rs
rust/vrs_solver/src/optimizer/initializer.rs
rust/vrs_solver/src/adapter.rs
rust/vrs_solver/src/item.rs
rust/vrs_solver/src/sheet.rs
rust/vrs_solver/src/io.rs
rust/vrs_solver/Cargo.toml
vrs_nesting/runner/vrs_solver_runner.py
vrs_nesting/nesting/instances.py
scripts/smoke_jagua_initial_construction.py
scripts/smoke_jagua_exact_validation_bridge.py
scripts/check.sh
scripts/verify.sh
```

Külön ellenőrizd:

- `CandidateMove` skeleton aktuális formáját;
- `LayoutState` és `PlacementTransform` használhatóságát;
- `build_initial_layout()` és `ConstructionDiagnostics` visszatérési contractját;
- `bbox_from_placement()` és `PlacedBbox::overlaps()` használhatóságát;
- `rect_inside_sheet_shape()` boundary checket;
- allowed rotation normalizálást és `placement_anchor_from_rect_min()` viselkedést;
- hogy létezik-e már `repair.rs` vagy `stopping.rs`;
- hogy a Cargo.toml-ban van-e random/RNG dependency; ha nincs, ne vezess be szükségtelen randomizálást.

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

Tilos az exact validator gyengítése, kikapcsolása vagy megkerülése.

---

## Implementációs scope

### 1. StoppingPolicy V1

Hozd létre:

```text
rust/vrs_solver/src/optimizer/stopping.rs
```

Minimum:

- time limit;
- max iteration vagy stagnation limit;
- explicit stop reason;
- determinisztikus viselkedés;
- unit tesztek.

A repair belső időbudget nem lehet nagyobb, mint amit a solver input `time_limit_s` enged. Ha a valós kód miatt pontos budget-megosztás kell, dokumentáld.

### 2. MoveGenerator V1

Bővítsd:

```text
rust/vrs_solver/src/optimizer/moves.rs
```

Minimum:

- translate/move jellegű candidate;
- reinsert jellegű candidate;
- rotate jellegű candidate allowed rotations alapján;
- stabil sorrend: sheet index → y → x → rotation → instance id vagy repo-konform ekvivalens;
- azonos input + seed → azonos candidate sorrend.

A meglévő `CandidateMove` serializálható skeletonját lehetőleg tartsd kompatibilisen.

### 3. RepairEngine V1

Hozd létre:

```text
rust/vrs_solver/src/optimizer/repair.rs
```

Minimum:

- Phase 1 rectangular / outer-only scope;
- overlap és boundary hibák külön diagnosztikája;
- mesterségesen hibás kezdőállapot javítható legyen legalább egy smoke/unit scenario-ban;
- hibás placement eltávolítása + reinsert/move/rotate próba;
- sikertelen repair esetén rollback vagy explicit fail/unplaced reason;
- minden instance identity megmarad: placed vagy unplaced, de nem tűnik el;
- repair attempt/success/fail metrika.

Javasolt meglévő helperök:

```text
rust/vrs_solver/src/optimizer/candidates.rs::generate_candidates
rust/vrs_solver/src/optimizer/candidates.rs::PlacedBbox::overlaps
rust/vrs_solver/src/optimizer/initializer.rs::bbox_from_placement
rust/vrs_solver/src/sheet.rs::rect_inside_sheet_shape
rust/vrs_solver/src/item.rs::dims_for_rotation
rust/vrs_solver/src/item.rs::placement_anchor_from_rect_min
rust/vrs_solver/src/item.rs::normalize_allowed_rotations
```

Ne hivatkozz ezekre vakon: előbb ellenőrizd a valós signature-t.

### 4. Integráció

Frissítsd:

```text
rust/vrs_solver/src/optimizer/mod.rs
rust/vrs_solver/src/adapter.rs
```

A Phase 1 branch (`jagua_optimizer_phase1_outer_only`) a construction után futtathatja a repair V1-et. A publikus output contract maradjon:

```text
contract_version, status, unsupported_reason, placements, unplaced, metrics
```

Ha repair metrics új mezőként bekerül Rust `Metrics`-be, csak backward-compatible módon tedd. Ha a report/smoke szinten elég, dokumentáld, hogy miért.

---

## Smoke / test elvárás

Hozd létre:

```text
scripts/smoke_jagua_repair_search_v1.py
```

A smoke legalább ezt bizonyítsa:

- mesterségesen hibás kezdőállapotból egy repair scenario valid állapotot ad;
- overlap hiba külön diagnosztizálható;
- boundary hiba külön diagnosztizálható;
- azonos seed determinisztikus eredményt ad;
- time limit betartott;
- invalid layout nem successful;
- JG-08 initial construction regression PASS;
- JG-09 exact validation bridge regression PASS.

Ha a repair-only kezdőállapot Pythonból nem etethető be közvetlenül a solver CLI-be, akkor a smoke script futtassa a releváns Rust unit teszteket is, és ezt dokumentálja. Ne hamisíts integration evidence-et.

---

## Kötelező parancsok

Futtasd, ahol a környezet engedi:

```bash
cargo build --manifest-path rust/vrs_solver/Cargo.toml
cargo test --manifest-path rust/vrs_solver/Cargo.toml
python3 scripts/smoke_jagua_initial_construction.py
python3 scripts/smoke_jagua_exact_validation_bridge.py
python3 scripts/smoke_jagua_repair_search_v1.py
./scripts/verify.sh --report codex/reports/egyedi_solver/jagua_optimizer_t10_repair_search_loop_v1.md
```

Ha valamelyik parancs környezeti dependency miatt fail, különítsd el:

- implementációs hiba;
- teszthiba;
- környezeti dependency hiba;
- meglévő repo-hiba.

Hiányzó bizonyítékkal ne adj PASS-t.

---

## Checklist és report

Frissítsd:

```text
codex/codex_checklist/egyedi_solver/jagua_optimizer_t10_repair_search_loop_v1.md
canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md
codex/reports/egyedi_solver/jagua_optimizer_t10_repair_search_loop_v1.md
```

A report tartalmazza:

- dependency evidence;
- olvasott dokumentumok és szabályfájlok;
- valós kód audit;
- DISCOVERED_MISMATCH / REQUIRES_DECISION, ha volt;
- repair design döntés;
- implementált fájlok;
- repair attempt/success/fail metrics;
- smoke/test parancsok és kimenet-részletek;
- exact validation evidence;
- git status és diff stat;
- végső státusz.

Csak akkor írd a report végére:

```text
JG-11_STATUS: READY
```

ha JG-10 PASS, repair smoke PASS, exact validator evidence PASS, és repo verify zöld.

---

## Végső válasz formátuma

```text
STATUS: PASS | REVISE | BLOCKED

SUMMARY:
- ...

IMPLEMENTED:
- ...

TESTS:
- command: ...
  result: ...

REPORT:
- codex/reports/egyedi_solver/jagua_optimizer_t10_repair_search_loop_v1.md

CHECKLIST:
- ...

NEXT:
- JG-11_STATUS: READY | NOT_READY
```
