# Runner prompt — JG-18 `jagua_optimizer_t18_irregular_candidate_generation`

## Feladat

A helyi VRS_nesting repo gyökerében dolgozz. Hajtsd végre a JG-18 taskot a canvas és goal YAML alapján.

```text
TASK_ID=JG-18
TASK_SLUG=jagua_optimizer_t18_irregular_candidate_generation
CANVAS=canvases/egyedi_solver/jagua_optimizer_t18_irregular_candidate_generation.md
GOAL_YAML=codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t18_irregular_candidate_generation.yaml
REPORT=codex/reports/egyedi_solver/jagua_optimizer_t18_irregular_candidate_generation.md
VERIFY_LOG=codex/reports/egyedi_solver/jagua_optimizer_t18_irregular_candidate_generation.verify.log
```

Ez nem package-generálási feladat. A package már létrejött; most a benne lévő JG-18 implementációs utasításokat kell végrehajtani.

## Kötelező olvasás

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
canvases/egyedi_solver/jagua_optimizer_t18_irregular_candidate_generation.md
codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t18_irregular_candidate_generation.yaml
codex/codex_checklist/egyedi_solver/jagua_optimizer_t18_irregular_candidate_generation.md
```

## Dependency preflight

A futás elején ellenőrizd:

```text
codex/reports/egyedi_solver/jagua_optimizer_t17_irregular_boundary_validation.md
rust/vrs_solver/src/optimizer/boundary.rs
scripts/smoke_jagua_irregular_boundary_validation.py
```

Kötelező feltételek:

- a JG-17 report létezik;
- első sora `PASS` vagy `PASS_WITH_NOTES`;
- tartalmazza: `JG-18_STATUS: READY`;
- `optimizer/boundary.rs` létezik és a boundary policy dokumentált;
- nincs unresolved `STOP`, `NO-GO` vagy boundary blocker.

Ha ezek közül bármi hiányzik, állj meg és írd a JG-18 reportba:

```text
STATUS: BLOCKED
REASON: <pontos dependency hiány>
```

## Valós kód audit

Auditáld a jelenlegi candidate útvonalat:

```text
rust/vrs_solver/src/optimizer/candidates.rs
rust/vrs_solver/src/optimizer/initializer.rs
rust/vrs_solver/src/optimizer/repair.rs
rust/vrs_solver/src/optimizer/sheet_elimination.rs
rust/vrs_solver/src/optimizer/boundary.rs
rust/vrs_solver/src/sheet.rs
```

A reportban rögzítsd:

- jelenlegi candidate források;
- jelenlegi determinisztikus sort/dedup policy;
- hol használja a construction/repair/sheet-elimination a candidate generátort;
- milyen diagnostics mezők vannak;
- mi hiányzik az irregular-aware generationhöz.

## Implementációs scope

A JG-18 célja: boundary-aware candidate generation irregular/remnant sheetre.

Kötelező elemek:

1. Irregular-aware candidate generator API vagy wrapper.
2. Legacy rectangular behavior regresszió megtartása.
3. Candidate source/reason modell.
4. Determinisztikus interior sampling.
5. Edge-near candidate generation.
6. Vertex-near candidate generation.
7. Neighbor-near candidate generation, vagy dokumentált fallback ha valós blocker van.
8. Rejection reason/candidate count diagnosztika.
9. Construction és repair útvonal bekötése.
10. Sheet-elimination candidate call site kompatibilitás audit/frissítés.
11. Irregular fixture + smoke script.
12. Exact validation gate megtartása.

## Explicit out of scope

Ne implementáld ezeket:

- JG-19 remnant score/value model;
- JG-20 Phase 2 benchmark matrix;
- part hole vagy stock/container hole támogatás;
- cavity-prepack V2;
- új NFP provider vagy jagua-rs fork;
- `SolverOutput` v1 breaking változtatás;
- Python exact validator lazítása.

## Hard rules

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
- Any accepted layout must pass exact validation.
- Invalid layout cannot be accepted as success.
- Candidate validity must be proven through boundary + collision filters and final exact validation.
```

```text
CHECKLIST_REQUIRED:
- Update codex/codex_checklist/egyedi_solver/jagua_optimizer_t18_irregular_candidate_generation.md.
- Update canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md JG-18 szakaszát.
- Do not mark PASS unless checked items have concrete evidence.
```

## Kötelező outputok

A YAML outputs szabálya szerint csak deklarált fájlokat módosíts. Várható fő outputok:

```text
rust/vrs_solver/src/optimizer/candidates.rs
rust/vrs_solver/src/optimizer/initializer.rs
rust/vrs_solver/src/optimizer/repair.rs
rust/vrs_solver/src/optimizer/sheet_elimination.rs
scripts/smoke_jagua_irregular_candidate_generation.py
tests/fixtures/egyedi_solver/jagua_irregular_candidate_generation.json
docs/solver_io_contract.md
codex/reports/egyedi_solver/jagua_optimizer_t18_irregular_candidate_generation.md
codex/codex_checklist/egyedi_solver/jagua_optimizer_t18_irregular_candidate_generation.md
canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md
```

Ha további fájl szükséges, előbb frissítsd a goal YAML-t, különben sérül az `AGENTS.md` outputs szabály.

## Kötelező ellenőrzések

Futtasd és dokumentáld:

```bash
python3 scripts/smoke_jagua_irregular_candidate_generation.py
python3 scripts/smoke_jagua_irregular_boundary_validation.py
cargo test --manifest-path rust/vrs_solver/Cargo.toml
./scripts/verify.sh --report codex/reports/egyedi_solver/jagua_optimizer_t18_irregular_candidate_generation.md
```

Ha a környezet miatt valamelyik parancs nem fut, írd le pontosan a hibát, és ne adj PASS-t pusztán feltételezésre.

## Report követelmények

A report első sora legyen egyértelműen:

```text
PASS
```

vagy:

```text
PASS_WITH_NOTES
```

vagy:

```text
FAIL
```

vagy:

```text
BLOCKED
```

A report tartalmazza:

- dependency evidence;
- valós kód audit summary;
- candidate source breakdown;
- rejection reason metrika;
- irregular fixture placement példa;
- determinism evidence;
- rectangular regression evidence;
- exact validation evidence;
- futtatott parancsok és eredmények;
- módosított fájlok;
- deviations/blockers;
- csak valódi PASS esetén: `JG-19_STATUS: READY`.

## Végső válasz formátum

```text
STATUS: PASS | PASS_WITH_NOTES | FAIL | BLOCKED
SUMMARY:
- ...
FILES_CHANGED:
- ...
TESTS:
- command: ... result: ...
REPORT: codex/reports/egyedi_solver/jagua_optimizer_t18_irregular_candidate_generation.md
VERIFY_LOG: codex/reports/egyedi_solver/jagua_optimizer_t18_irregular_candidate_generation.verify.log
NEXT: JG-19 ready | not ready
```
