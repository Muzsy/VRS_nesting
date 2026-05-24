# Runner prompt — JG-19 `jagua_optimizer_t19_remnant_score_model_v1`

## Feladat

A helyi VRS_nesting repóban dolgozz. Hajtsd végre a **JG-19 — `jagua_optimizer_t19_remnant_score_model_v1`** taskot a repo-beli canvas és YAML alapján.

Ez nem package-generálási feladat. A csomag már be van másolva a repóba. Neked a `run.md`, a canvas és a YAML alapján a JG-19 implementációs utasításokat kell végrehajtani.

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
canvases/egyedi_solver/jagua_optimizer_t19_remnant_score_model_v1.md
codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t19_remnant_score_model_v1.yaml
codex/codex_checklist/egyedi_solver/jagua_optimizer_t19_remnant_score_model_v1.md
```

## Dependency preflight

A futás elején ellenőrizd:

```text
codex/reports/egyedi_solver/jagua_optimizer_t18_irregular_candidate_generation.md
rust/vrs_solver/src/optimizer/candidates.rs
scripts/smoke_jagua_irregular_candidate_generation.py
```

Kötelező feltételek:

- a JG-18 report létezik;
- első sora `PASS` vagy `PASS_WITH_NOTES`;
- tartalmazza: `JG-19_STATUS: READY`;
- a JG-18 irregular-aware candidate útvonal létezik;
- nincs unresolved `STOP`, `NO-GO` vagy irregular candidate blocker.

Ha ezek közül bármi hiányzik, állj meg és írd a JG-19 reportba:

```text
STATUS: BLOCKED
REASON: <pontos dependency hiány>
```

## Valós kód audit

Auditáld a jelenlegi score és sheet metadata útvonalat:

```text
rust/vrs_solver/src/optimizer/score.rs
rust/vrs_solver/src/sheet.rs
rust/vrs_solver/src/optimizer/multisheet.rs
rust/vrs_solver/src/adapter.rs
rust/vrs_solver/src/io.rs
rust/vrs_solver/src/optimizer/boundary.rs
rust/vrs_solver/src/optimizer/candidates.rs
```

A reportban rögzítsd:

- jelenlegi `ScoreWeights` mezők;
- jelenlegi `ObjectiveBreakdown` mezők;
- sheet area / irregular metadata rendelkezésre állása;
- van-e explicit remnant/inventory-cost input field;
- hol vész el jelenleg a `MultiSheetDiagnostics` (`adapter.rs`);
- milyen output/metrics mezőkkel bizonyítható a score breakdown breaking change nélkül.

## Implementációs scope

A JG-19 célja: remnant/sheet cost ScoreModel V1.

Kötelező elemek:

1. Sheet cost metadata modell vagy dokumentált V1 proxy/inference policy.
2. Remnant preference weight dokumentált defaulttal.
3. Új teljes tábla nyitási büntetés dokumentált defaulttal.
4. Usable-area utilization számítás.
5. `ObjectiveBreakdown` sheet-cost/utilization mezőkkel bővítve.
6. ScoreModel invalid dominancia megőrzése: overlap/boundary penalty továbbra is mindent dominál.
7. Vegyes rectangular + remnant fixture.
8. Smoke script, amely magyarázható sheet választást és breakdown-t bizonyít.
9. Rectangular-only score regresszió bizonyítása.
10. JG-18 irregular candidate regresszió bizonyítása.
11. Contract dokumentáció és döntési példák.
12. Checklist + report lezárás.

## Explicit out of scope

Ne implementáld ezeket:

- JG-20 Phase 2 benchmark matrix;
- végleges inventory/costing schema vagy árkalkuláció;
- stock/container hole vagy part hole támogatás;
- cavity-prepack V2;
- új boundary validator vagy candidate generator újraírás;
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
- Do not drop holes, contours, item identities, quantities, transforms, margin data, stock identities, sheet metadata, or validation data silently.
- Container holes remain unsupported unless a later explicit task changes that contract.
```

```text
EXACT_VALIDATION_REQUIRED:
- Any accepted layout must pass exact validation.
- Invalid boundary/overlap layout cannot be accepted as success.
- Remnant preference must never overpower boundary/overlap validity penalties.
```

```text
CHECKLIST_REQUIRED:
- Update codex/codex_checklist/egyedi_solver/jagua_optimizer_t19_remnant_score_model_v1.md.
- Update canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md JG-19 szakaszát.
- Do not mark PASS unless checked items have concrete evidence.
```

## Kötelező outputok

A YAML outputs szabálya szerint csak deklarált fájlokat módosíts. Várható fő outputok:

```text
rust/vrs_solver/src/optimizer/score.rs
rust/vrs_solver/src/sheet.rs
rust/vrs_solver/src/optimizer/multisheet.rs
rust/vrs_solver/src/adapter.rs
rust/vrs_solver/src/io.rs
docs/egyedi_solver/jagua_remnant_score_model_v1.md
docs/solver_io_contract.md
scripts/smoke_jagua_remnant_score_model_v1.py
tests/fixtures/egyedi_solver/jagua_remnant_score_model_v1.json
codex/reports/egyedi_solver/jagua_optimizer_t19_remnant_score_model_v1.md
codex/codex_checklist/egyedi_solver/jagua_optimizer_t19_remnant_score_model_v1.md
canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md
```

Ha további fájl szükséges, előbb frissítsd a goal YAML-t, különben sérül az `AGENTS.md` outputs szabály.

## Kötelező ellenőrzések

Futtasd és dokumentáld:

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::score
python3 scripts/smoke_jagua_remnant_score_model_v1.py
python3 scripts/smoke_jagua_score_model_v1.py
python3 scripts/smoke_jagua_irregular_candidate_generation.py
./scripts/verify.sh --report codex/reports/egyedi_solver/jagua_optimizer_t19_remnant_score_model_v1.md
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
- sheet cost metadata/proxy döntés;
- default score weights;
- sheet_cost/utilization breakdown;
- vegyes rectangular + remnant döntési példa;
- invalid-vs-valid score evidence;
- rectangular-only regression evidence;
- JG-18 irregular regression evidence;
- exact validation evidence;
- futtatott parancsok és eredmények;
- módosított fájlok;
- deviations/blockers;
- csak valódi PASS esetén: `JG-20_STATUS: READY`.

## Végső válasz formátum

```text
STATUS: PASS | PASS_WITH_NOTES | FAIL | BLOCKED

SUMMARY:
- ...

FILES_CHANGED:
- ...

VERIFY:
- command: ...
- result: ...
- log: ...

NEXT:
- JG-20_STATUS: READY | NOT_READY
```
