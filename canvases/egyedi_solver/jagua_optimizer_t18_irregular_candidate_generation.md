# JG-18 — `jagua_optimizer_t18_irregular_candidate_generation`

## Task identity

- **Task id:** JG-18
- **Slug:** `jagua_optimizer_t18_irregular_candidate_generation`
- **Phase:** Phase 2 / irregular search
- **Goal:** Boundary-aware candidate generation irregular/remnant sheetre: interior samples, edge-near, vertex-near és neighbor-near candidate pontok determinisztikus, diagnosztikázható generálása.
- **Dependency:** JG-17 — `jagua_optimizer_t17_irregular_boundary_validation`
- **Primary report:** `codex/reports/egyedi_solver/jagua_optimizer_t18_irregular_candidate_generation.md`
- **Verify log:** `codex/reports/egyedi_solver/jagua_optimizer_t18_irregular_candidate_generation.verify.log`

## Dependency gate

JG-18 csak akkor implementálható, ha ezek bizonyítottan teljesülnek:

- `codex/reports/egyedi_solver/jagua_optimizer_t17_irregular_boundary_validation.md` létezik;
- a JG-17 report első sora `PASS` vagy repo-konform `PASS_WITH_NOTES`;
- a JG-17 report tartalmazza: `JG-18_STATUS: READY`;
- `rust/vrs_solver/src/optimizer/boundary.rs` létezik és `optimizer/mod.rs` beköti;
- a JG-17 boundary smoke script létezik: `scripts/smoke_jagua_irregular_boundary_validation.py`;
- nincs JG-17 által jelölt `STOP`, `NO-GO` vagy unresolved boundary blocker.

Ha bármelyik feltétel nem teljesül, a JG-18 futás `BLOCKED`, és nem szabad candidate-generation kódot sikeresként lezárni.

## Strategic background

JG-15 kimondta, hogy a Phase 2 irregular/remnant irányban a járható út a **saját VRS boundary validator + jagua item-item collision** modell. JG-16 bevezette az irregular/remnant sheet provider oldali contractot. JG-17 megszilárdította a boundary validation policy-t és létrehozta a központi `optimizer/boundary.rs` façade réteget.

JG-18 feladata az első valódi irregular-search bővítés: a jelenlegi rectangular candidate pontok mellé olyan boundary-aware candidate forrásokat kell adni, amelyek nem csak `(0,0)` és meglévő bbox sarkok/right/top/top-right pontok alapján próbálnak elhelyezni. Ez különösen L-shape/remnant stock esetén fontos, mert a usable régió részei nem feltétlenül érhetők el jó minőségben rectangular BLF-szerű pontokból.

## Current repo observations

A csomag a friss repo snapshot valós kódja alapján készült:

- `rust/vrs_solver/src/optimizer/candidates.rs`
  - létezik;
  - `CandidatePoint { sheet_index, x, y }` és `PlacedBbox` definiált;
  - `generate_candidates(sheet_count, placed)` jelenleg sheet origin + placed bbox right/top/top-right pontokat generál;
  - sorted/dedup determinisztikus sorrend van: `(sheet_index ASC, y ASC, x ASC)`;
  - nincs candidate source enum, rejection reason breakdown, interior/edge/vertex sampling vagy sheet-shape input.
- `rust/vrs_solver/src/optimizer/initializer.rs`
  - `build_initial_layout()` a `generate_candidates(sheets.len(), &placed_bboxes)` kimenetét használja;
  - `ConstructionDiagnostics` csak aggregate countokat tartalmaz: `candidates_tried`, `rejected_out_of_sheet`, `rejected_collision`, `rejected_unsupported_rotation`, `items_unplaced_no_candidate`;
  - `rect_within_boundary()` már a JG-17 boundary façade-en keresztül fut.
- `rust/vrs_solver/src/optimizer/repair.rs`
  - repair reinsertion szintén `generate_candidates(sheets.len(), &placed_bboxes)` hívást használ;
  - nincs külön repair candidate source/rejection reason metrika.
- `rust/vrs_solver/src/optimizer/sheet_elimination.rs`
  - sheet-elimination reinsertion szintén a jelenlegi `generate_candidates()`-re támaszkodik, majd kizárja az eliminálandó sheetet;
  - JG-18-hoz ezt regressziós szempontból auditálni kell, de a sheet elimination strategy cseréje nem cél.
- `rust/vrs_solver/src/optimizer/boundary.rs`
  - JG-17 után létezik;
  - `rect_within_boundary(rect, sheet)` az authoritative Rust-side boundary filter façade;
  - JG-18-ban minden új candidate source-nak ezen keresztül kell rejectálódnia.
- `rust/vrs_solver/src/sheet.rs`
  - `SheetShape` tartalmaz irregular outer boundary metadata-t és boundary helper logikát;
  - irregular stock esetén a JG-17 inset policy dokumentált.
- `scripts/smoke_jagua_irregular_candidate_generation.py`
  - jelenleg nem létezik;
  - JG-18 fő smoke outputként létrehozandó.

## DISCOVERED_MISMATCH / implementation note

```text
task breakdown says: extend candidate generator for irregular sheet interior/edge/vertex/neighbor-near points
current repo says: candidates.rs has only sheet_count + placed bbox input and cannot see SheetShape
current construction/repair/sheet-elimination call sites use generate_candidates(sheets.len(), &placed_bboxes)
proposed resolution: introduce a backward-compatible candidate-generation API that can accept &[SheetShape] and CandidateGenerationOptions/Diagnostics, keep or wrap the old rectangular behavior for regressions, and migrate initializer/repair/sheet_elimination deliberately
```

JG-18 ne törje el a Phase 1 rectangular behavior-t. Ha a régi `generate_candidates(sheet_count, placed)` API-t meg kell tartani regressziós kompatibilitásként, maradjon wrapperként, és az irregular-aware API legyen külön névvel vagy options paraméterrel bevezetve.

## Exact scope

JG-18 implementációs scope:

1. Candidate generation API bővítése irregular/remnant sheet awarenesshez.
2. Candidate source-ok bevezetése és diagnosztikája:
   - `origin` / rectangular legacy points;
   - `interior_sample` determinisztikus grid vagy policy-alapú mintavételezés;
   - `edge_near` candidate-ek usable boundary élek közelében;
   - `vertex_near` candidate-ek usable boundary vertexek közelében;
   - `neighbor_near` candidate-ek meglévő placed bboxok szomszédságában, vagy dokumentált fallback, ha a valós kód alapján még nem biztonságos.
3. Determinisztikus sorrend és dedup policy megtartása.
4. Candidate rejection reason metrika:
   - boundary/out-of-sheet;
   - collision;
   - unsupported rotation;
   - duplicate/filtered candidate, ha implementálva van.
5. `build_initial_layout()` és repair reinsertion candidate útvonalainak frissítése, hogy irregular sheeteken több candidate forrást próbáljanak.
6. Rectangular stock regresszió bizonyítása.
7. Irregular fixture-en legalább részleges valid elhelyezés bizonyítása.
8. Exact validation gate megtartása: invalid candidate nem kerülhet final layoutba.
9. Smoke script és report létrehozása.
10. Checklist és globális progress checklist frissítése.

## Out of scope

- Nem cél JG-19 remnant score/value model.
- Nem cél JG-20 Phase 2 benchmark matrix.
- Nem cél part hole, stock/container hole vagy cavity-prepack támogatás.
- Nem cél új NFP provider, jagua-rs fork vagy Sparrow integráció.
- Nem cél sheet elimination strategy újraírása, kivéve a candidate generator API call site kompatibilis frissítését.
- Nem cél `SolverOutput` v1 breaking változtatás.
- Nem cél Python exact validator lazítása vagy kikapcsolása.

## Required implementation outputs

A JG task-bontás és a valós kód alapján legalább ezek érintettek vagy vizsgálandók:

```text
rust/vrs_solver/src/optimizer/candidates.rs
rust/vrs_solver/src/optimizer/initializer.rs
rust/vrs_solver/src/optimizer/repair.rs
rust/vrs_solver/src/optimizer/sheet_elimination.rs
rust/vrs_solver/src/optimizer/boundary.rs
rust/vrs_solver/src/sheet.rs
scripts/smoke_jagua_irregular_candidate_generation.py
tests/fixtures/egyedi_solver/jagua_irregular_candidate_generation.json
docs/solver_io_contract.md
codex/reports/egyedi_solver/jagua_optimizer_t18_irregular_candidate_generation.md
codex/codex_checklist/egyedi_solver/jagua_optimizer_t18_irregular_candidate_generation.md
canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md
```

Ha a valós audit alapján valamelyik fájl módosítása szükségtelen, a reportban rögzítsd. Ha további fájl kell, előbb frissítsd a YAML `outputs` listáját, mert az `AGENTS.md` szerint csak deklarált output módosítható.

## Detailed execution plan

1. Olvasd el a repo szabályokat és a JG tervdokumentációkat.
2. Ellenőrizd a JG-17 dependency gate-et.
3. Auditáld a jelenlegi candidate útvonalat: `candidates.rs`, `initializer.rs`, `repair.rs`, `sheet_elimination.rs`.
4. Auditáld a JG-17 boundary façade-t és a `SheetShape` irregular metadata-t.
5. Tervezd meg a candidate source modellt úgy, hogy a régi rectangular candidate sorrend regressziója ne sérüljön.
6. Vezesd be az irregular-aware candidate generálást:
   - interior samples;
   - edge-near pontok;
   - vertex-near pontok;
   - neighbor-near pontok vagy bizonyított fallback.
7. Add hozzá a candidate diagnostics/rejection reportingot.
8. Frissítsd az initializer és repair útvonalakat; sheet elimination call site-t legalább kompatibilitásig auditáld/frissítsd.
9. Készíts irregular candidate fixture-t és smoke scriptet.
10. Futtasd a célzott smoke-ot, Rust teszteket és repo verify wrapperét.
11. Frissítsd a task-specifikus checklistet és a globális progress checklist JG-18 szakaszát.
12. Csak valódi PASS esetén írd a report végére: `JG-19_STATUS: READY`.

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
- Any accepted layout must pass the existing exact validation bridge.
- Invalid layout cannot be accepted as success.
- Candidate validity must be proven through boundary + collision filters and final exact validation.
```

```text
CHECKLIST_REQUIRED:
- Update the task-specific checklist entries in jagua_optimizer_task_progress_checklist.md.
- A task cannot be PASS unless the relevant checklist items are checked or explicitly marked BLOCKED/DEVIATION with evidence.
```

## Required tests / verification

Minimum targeted checks:

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml
python3 scripts/smoke_jagua_irregular_candidate_generation.py
python3 scripts/smoke_jagua_irregular_boundary_validation.py
./scripts/verify.sh --report codex/reports/egyedi_solver/jagua_optimizer_t18_irregular_candidate_generation.md
```

If a command is unavailable because of environment dependency problems, classify it clearly as environment blocker and include the exact error in the report. Do not mark PASS without equivalent local evidence.

## Acceptance criteria

- JG-17 dependency gate passed.
- Candidate generator can use irregular sheet metadata or a documented irregular-aware context.
- Interior sampling is deterministic.
- Edge-near candidate generation is implemented.
- Vertex-near candidate generation is implemented.
- Neighbor-near candidate generation is implemented or blocked with precise evidence and fallback.
- Candidate rejection reason metrics are reported.
- Irregular fixture yields at least partial valid placement.
- Invalid candidate is filtered out and never accepted as final layout success.
- Candidate count metric appears in diagnostics/report.
- Same seed/input produces deterministic candidate order and stable layout hash/evidence.
- Rectangular candidate generation regression is absent.
- Report contains an irregular placement example and candidate-source summary.
- Repo verify PASS and verify log saved.
- Global and task-specific checklists updated.
- Only true PASS may unlock JG-19 via `JG-19_STATUS: READY`.

## Failure / rollback policy

- If new candidate sources produce invalid layouts, rollback to legacy rectangular candidate generator and report `REVISE` or `BLOCKED`.
- If irregular candidate generation improves count but exact validation fails, final status is not PASS.
- If deterministic order cannot be proven, do not enable the new generator by default.
- If candidate API migration would require broad search rewrite beyond the YAML outputs, stop and mark `REQUIRES_DECISION`.
- Do not remove JG-17 boundary validation as a workaround.
