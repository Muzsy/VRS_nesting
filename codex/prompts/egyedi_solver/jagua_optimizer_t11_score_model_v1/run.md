# Runner prompt — JG-11 jagua_optimizer_t11_score_model_v1

## Feladat

A helyi VRS_nesting repo gyökerében dolgozz. Hajtsd végre a JG-11 taskot:

```text
JG-11 — jagua_optimizer_t11_score_model_v1
```

Ez a task a JG-10 repair-search után bevezeti a Phase 1 rectangular / outer-only ScoreModel V1-et. Ne készíts általános tervet. Olvasd el a megadott repo fájlokat, ellenőrizd a dependency-t, implementáld a scope-ot, futtasd a teszteket, frissítsd a checklistet és reportot.

---

## Kötelező dependency preflight

Mielőtt bármilyen kódot módosítasz, ellenőrizd:

```text
codex/reports/egyedi_solver/jagua_optimizer_t10_repair_search_loop_v1.md
```

JG-10 feltételek:

- report létezik;
- első sora `PASS`;
- tartalmazza: `JG-11_STATUS: READY`;
- létezik `rust/vrs_solver/src/optimizer/repair.rs`;
- létezik `rust/vrs_solver/src/optimizer/stopping.rs`;
- létezik `scripts/smoke_jagua_repair_search_v1.py`;
- a report bizonyítja, hogy repair smoke és exact validation regression PASS.

Ha bármelyik feltétel nem teljesül, állj meg:

```text
STATUS: BLOCKED
REASON: Missing or non-PASS dependency: JG-10
```

Ilyenkor ne implementálj JG-11 kódot, csak frissítsd a JG-11 reportot dependency evidence-szel.

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
canvases/egyedi_solver/jagua_optimizer_t11_score_model_v1.md
codex/goals/canvases/egyedi_solver/fill_canvas_jagua_optimizer_t11_score_model_v1.yaml
codex/codex_checklist/egyedi_solver/jagua_optimizer_t11_score_model_v1.md
```

A `run.md` és a canvas az irányadó. Ha a régi fejlesztési terv JG-11-et irregular boundary adapterként vagy más néven említi, dokumentáld `DISCOVERED_MISMATCH` blokkal, és az aktuális task-bontást kövesd: JG-11 = ScoreModel V1.

---

## Valós kód audit

Vizsgáld meg az aktuális kódot:

```text
rust/vrs_solver/src/optimizer/mod.rs
rust/vrs_solver/src/optimizer/score.rs
rust/vrs_solver/src/optimizer/state.rs
rust/vrs_solver/src/optimizer/moves.rs
rust/vrs_solver/src/optimizer/candidates.rs
rust/vrs_solver/src/optimizer/initializer.rs
rust/vrs_solver/src/optimizer/repair.rs
rust/vrs_solver/src/optimizer/stopping.rs
rust/vrs_solver/src/adapter.rs
rust/vrs_solver/src/item.rs
rust/vrs_solver/src/sheet.rs
rust/vrs_solver/src/io.rs
rust/vrs_solver/Cargo.toml
vrs_nesting/runner/vrs_solver_runner.py
scripts/smoke_jagua_repair_search_v1.py
scripts/check.sh
scripts/verify.sh
```

Külön ellenőrizd:

- `score.rs` aktuális skeletonját: `ObjectiveBreakdown` jelenlegi mezői, placeholder, unit tesztek;
- `LayoutState` és `PlacementTransform` használhatóságát;
- `PlacedItem` / `UnplacedItem` mezőit;
- `bbox_from_placement()` signature-t;
- `PlacedBbox::overlaps()` signature-t;
- `rect_inside_sheet_shape()` használhatóságát;
- `Part` és `ItemGeometryStore` area / rotation cache mezőit;
- JG-10 `RepairDiagnostics` mezőit;
- a publikus `SolverOutput` contractot, hogy JG-11 ne törje.

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

Tilos az exact validator gyengítése, kikapcsolása vagy megkerülése. Tilos olyan score modellt írni, amely invalid layoutot a valid layout fölé rangsorol.

---

## Implementációs scope

### 1. ScoreModel API

Bővítsd a meglévő fájlt:

```text
rust/vrs_solver/src/optimizer/score.rs
```

Ne hozz létre duplikált score modult. A meglévő `ObjectiveBreakdown` skeleton továbbfejleszthető vagy kompatibilisen lecserélhető.

Minimum elvárt elemek:

- `ScoreWeights` vagy repo-konform ekvivalens;
- `ScoreModel` vagy repo-konform ekvivalens;
- `ObjectiveBreakdown` auditálható komponensekkel;
- `ScoreResult` / `total_score` / `total_cost` vagy ekvivalens;
- explicit dokumentált score irány: magasabb jobb vagy alacsonyabb jobb;
- összehasonlító helper vagy egyértelmű tesztelt ordering.

### 2. Score komponensek

Minimum komponensek:

```text
placed area
unplaced penalty
sheet count penalty
overlap penalty
boundary penalty
compactness proxy / penalty
total score vagy total cost
```

Elvárás:

- placed area reward/komponens csak validitási penalty után számítson;
- unplaced penalty legyen érdemi;
- sheet count penalty működjön, de ne nyomja el a validitási penaltyt;
- overlap és boundary penalty nagy súlyú legyen;
- compactness proxy nem írhatja felül a validitást.

### 3. Invalid-layout scoring

Használd a valós helperöket, ha signature alapján illeszkednek:

```text
rust/vrs_solver/src/optimizer/initializer.rs::bbox_from_placement
rust/vrs_solver/src/optimizer/candidates.rs::PlacedBbox::overlaps
rust/vrs_solver/src/sheet.rs::rect_inside_sheet_shape
rust/vrs_solver/src/item.rs::dims_for_rotation
```

Ha `LayoutState`-ből scoringolsz, alakíts ki valós, tesztelt mappinget a part dimensions felé. Ha közvetlenül `Placement` listából scoringolsz, dokumentáld, miért nem `LayoutState` az elsődleges bemenet.

### 4. Default weight profile

A default weight profile legyen dokumentált és egy helyen definiált. Ne legyen szétszórt magic number káosz.

A profile minimum dokumentálja:

- score irány;
- placed area súly;
- unplaced penalty;
- sheet count penalty;
- overlap penalty;
- boundary penalty;
- compactness penalty;
- miért nem írhatják felül a validitást a minőségi komponensek.

### 5. Dokumentáció

Hozd létre:

```text
docs/egyedi_solver/jagua_optimizer_score_model_v1.md
```

Tartalmazza:

- ScoreModel V1 célja;
- komponensek definíciója;
- default weight profile táblázata;
- score iránya és ordering szabálya;
- invalid layout policy;
- determinisztikusság;
- ismert korlátok;
- kapcsolat JG-12/JG-13/JG-14 felé.

### 6. Smoke script

Hozd létre:

```text
scripts/smoke_jagua_score_model_v1.py
```

A smoke script legyen determinisztikus és repo-konform. Legalább ezeket ellenőrizze:

- `cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::score` PASS;
- invalid layout score-ja rosszabb valid alternatívánál;
- unplaced penalty működik;
- sheet count penalty működik;
- overlap/boundary penalty nagy súlyú;
- compactness proxy nem írja felül a validitást;
- score determinisztikus azonos állapotra;
- JG-10 repair smoke regresszió PASS, ha a környezet engedi.

Ha a smoke Pythonból nem tud közvetlenül Rust internalt vizsgálni, futtassa a Rust unit teszteket, majd használjon CLI/fixture outputot vagy dokumentált minimal smoke stratégiát. Ne hamisíts PASS-t.

### 7. Unit tesztek

A Rust unit tesztekben legalább legyenek ilyen scenario-k:

- valid layout score stabil;
- unplaced item rontja a score-t;
- több sheet rontja a score-t azonos placed area mellett;
- overlap rontja a score-t;
- boundary hiba rontja a score-t;
- compactness csak tie-breaker / minőségi komponens;
- azonos inputra azonos score.

### 8. Checklist és progress frissítés

Frissítsd:

```text
codex/codex_checklist/egyedi_solver/jagua_optimizer_t11_score_model_v1.md
canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md
```

Csak bizonyított pontot pipálj ki. Ha dependency, környezeti vagy implementációs okból valami nem teljesült, jelöld `BLOCKED` / `DEVIATION` megjegyzéssel, ne pipáld ki hamisan.

### 9. Report

Töltsd ki:

```text
codex/reports/egyedi_solver/jagua_optimizer_t11_score_model_v1.md
```

A report tartalmazza:

- dependency evidence;
- real code audit;
- score API döntés;
- score weights/profile default táblázat;
- objective breakdown example;
- invalid vs valid scoring evidence;
- unit/smoke eredmények;
- exact validation policy evidence;
- git diff/status;
- végső státusz.

Csak akkor írd a report végére:

```text
JG-12_STATUS: READY
```

ha JG-11 PASS, score smoke PASS és repo verify zöld.

---

## Kötelező parancsok

A végén futtasd vagy dokumentáltan próbáld futtatni:

```bash
cargo build --manifest-path rust/vrs_solver/Cargo.toml
cargo test --manifest-path rust/vrs_solver/Cargo.toml
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::score
python3 scripts/smoke_jagua_repair_search_v1.py
python3 scripts/smoke_jagua_score_model_v1.py
./scripts/verify.sh --report codex/reports/egyedi_solver/jagua_optimizer_t11_score_model_v1.md
```

Ha bármelyik környezeti okból elakad, a report legyen `REVISE` vagy `BLOCKED`, ne `PASS`.

---

## Acceptance criteria

A JG-11 csak akkor PASS, ha:

- JG-10 dependency PASS + `JG-11_STATUS: READY` bizonyított;
- Score komponensek dokumentálva: placed area, unplaced penalty, sheet count, overlap/boundary penalty, compactness proxy;
- `ObjectiveBreakdown` outputban auditálható;
- Score weight defaultok dokumentálva;
- invalid layout score-ja mindig rosszabb valid alternatívánál az erre készített tesztben;
- unplaced penalty érdemben büntet;
- sheet count penalty működik;
- boundary/overlap penalty nagy súlyú;
- compactness proxy nem írja felül a validitást;
- score determinisztikus azonos állapotra;
- profile default reportban szerepel;
- score smoke tesztek PASS;
- repo verify PASS és log mentve;
- checklist frissítve;
- `JG-12_STATUS: READY` csak bizonyított PASS után szerepel.

---

## Végső válasz formátum

```text
STATUS: PASS | REVISE | BLOCKED

SUMMARY:
- ...

IMPLEMENTED:
- ...

SCORE_PROFILE:
- ...

VERIFY:
- command: ...
- result: ...
- log: ...

CHANGED_FILES:
- ...

NEXT:
- JG-12_STATUS: READY | NOT_READY
```
