# JG-12 — `jagua_optimizer_t12_multi_sheet_manager_v1`

## Task identity

- **Task id:** JG-12
- **Slug:** `jagua_optimizer_t12_multi_sheet_manager_v1`
- **Phase:** Phase 1 / multi-sheet
- **Goal:** MultiSheetManager V1: több rectangular sheet kezelése, sheetenkénti construction/repair, stable ordering.
- **Dependency:** JG-11 — `jagua_optimizer_t11_score_model_v1`
- **Primary report:** `codex/reports/egyedi_solver/jagua_optimizer_t12_multi_sheet_manager_v1.md`
- **Verify log:** `codex/reports/egyedi_solver/jagua_optimizer_t12_multi_sheet_manager_v1.verify.log`

## Dependency gate

JG-12 csak akkor implementálható, ha ezek bizonyítottan teljesülnek:

- `codex/reports/egyedi_solver/jagua_optimizer_t11_score_model_v1.md` létezik;
- a JG-11 report első sora `PASS`;
- a JG-11 report tartalmazza: `JG-12_STATUS: READY`;
- `rust/vrs_solver/src/optimizer/score.rs` létezik, és tartalmazza a ScoreModel V1 elemeit;
- `scripts/smoke_jagua_score_model_v1.py` létezik;
- a report bizonyítja, hogy a score smoke és repo gate PASS.

Ha bármelyik nem teljesül, a JG-12 futás `BLOCKED`, és nem szabad implementációs kódot módosítani.

## Source-of-truth megjegyzés

A hivatalos aktuális task-bontás szerint:

```text
JG-12 = MultiSheetManager V1
```

A régebbi `jagua_rs_sajat_optimizer_fejlesztesi_terv.md` egy helyen `Task JG-12 — Cavity extraction` néven említi a 12-es taskot. Ez tervverzió-eltérés. JG-12 esetén az aktuális `jagua_optimizer_canvas_yaml_runner_task_bontas.md`, a progress checklist és a JG-11 report `JG-12_STATUS: READY` jelzése az irányadó.

```text
DISCOVERED_MISMATCH:
- old plan says: Task JG-12 — Cavity extraction
- current task breakdown says: JG-12 — jagua_optimizer_t12_multi_sheet_manager_v1
- resolution: follow current task breakdown/checklist/master-runner chain; do not implement cavity extraction in JG-12
```

## Strategic background

A Phase 1 célja stabil rectangular multi-sheet solver, hole-ok kizárásával. JG-08 létrehozta az initial construction placer alapját, JG-09 exact validation gate-et, JG-10 repair loopot, JG-11 auditálható ScoreModel V1-et. JG-12 ezekre építve különválasztja és ellenőrizhetővé teszi a több sheet kezelését.

A jelenlegi kód már képes több sheetet látni, mert:

- `sheet::expand_sheets()` expandálja a stock mennyiségeket stabil sorrendben;
- `Placement.sheet_index` létező output contract mező;
- `Metrics.sheet_count_used` létező output contract mező;
- `candidate::generate_candidates(sheet_count, placed)` sheetenként origin- és bbox-alapú candidate pontokat generál;
- `initializer::build_initial_layout()` több sheet felett iterál;
- `repair::run_repair()` több sheet candidate-jeit is használja;
- `score::ScoreModel` már számolja a használt sheetek számát.

A hiány: nincs önálló `MultiSheetManager` modul, amely egy helyre gyűjti a sheet assignment, used_sheets, per-sheet diagnostics és construction/repair sequencing szabályait. JG-12 ezt a koordinációs réteget vezeti be.

## Out of scope

- Sheet elimináció nem része JG-12-nek. Az JG-13.
- Irregular/remnant sheet support nem része JG-12-nek. Az későbbi phase.
- Cavity extraction / cavity prepack nem része JG-12-nek.
- Hole-os partok támogatása nem része JG-12-nek; Phase 1 továbbra is outer-only / hole-gated.
- NFP, Sparrow teljes átvétel, SA tuning, packing-density optimalizálás nem része JG-12-nek.
- Exact validator gyengítése vagy megkerülése tilos.

## Relevant current repo files

### Rust solver

- `rust/vrs_solver/src/optimizer/mod.rs` — jelenlegi optimizer modul exportok és régi row/cursor helper.
- `rust/vrs_solver/src/optimizer/initializer.rs` — initial construction, `ConstructionDiagnostics`, `build_initial_layout()`, `bbox_from_placement()`.
- `rust/vrs_solver/src/optimizer/repair.rs` — `run_repair()`, `RepairDiagnostics`, `find_violations()`.
- `rust/vrs_solver/src/optimizer/score.rs` — JG-11 ScoreModel V1, sheet count cost és objective breakdown.
- `rust/vrs_solver/src/optimizer/candidates.rs` — sheet-aware candidate pontok és `PlacedBbox`.
- `rust/vrs_solver/src/optimizer/state.rs` — `LayoutState`, `PlacedItem`, `UnplacedItem`, `PlacementTransform`.
- `rust/vrs_solver/src/optimizer/moves.rs` — `CandidateMove`, sheet-index mezőkkel.
- `rust/vrs_solver/src/optimizer/stopping.rs` — `StoppingPolicy`.
- `rust/vrs_solver/src/adapter.rs` — a valós runtime boundary; itt hívódik a Phase 1 build/repair flow.
- `rust/vrs_solver/src/main.rs` — CLI JSON input/output wrapper; csak akkor módosítandó, ha tényleges CLI wiring változik.
- `rust/vrs_solver/src/io.rs` — `SolverOutput`, `Placement`, `Unplaced`, `Metrics`; meglévő v1 mezők nem törhetők.
- `rust/vrs_solver/src/item.rs` — instance expansion, rotations, `ItemGeometryStore`.
- `rust/vrs_solver/src/sheet.rs` — stock expansion, `SheetShape`, sheet boundary.

### Python / smoke / wrapper

- `vrs_nesting/runner/vrs_solver_runner.py` — Python oldali Rust solver boundary.
- `scripts/smoke_jagua_initial_construction.py`
- `scripts/smoke_jagua_repair_search_v1.py`
- `scripts/smoke_jagua_score_model_v1.py`
- `scripts/smoke_jagua_exact_validation_bridge.py`
- `scripts/check.sh`
- `scripts/verify.sh`

## Real code observations to verify during implementation

- `adapter::solve()` jelenleg közvetlenül hívja `build_initial_layout()` és `run_repair()` függvényeket Phase 1 profil esetén.
- `sheet_count_used` jelenleg `max(sheet_index) + 1` számításból jön. JG-12-nek ezt stabil helperbe kell emelnie, és tesztelnie kell üres/lyukas sheet index esetekre is.
- `build_initial_layout()` és `run_repair()` már használ több sheetet, de nincs közös multi-sheet diagnostics / manager boundary.
- `Metrics` jelenleg csak globális darabszámokat és `sheet_count_used` mezőt tartalmaz. Ha JG-12 per-sheet metrics mezőt ad hozzá, az csak additív lehet, és a meglévő mezők nem változhatnak.
- A non-Phase1 row/cursor fallback továbbra is létezik az adapterben. JG-12 elsődleges scope-ja a `jagua_optimizer_phase1_outer_only` profil.

## Implementation target

Vezess be egy explicit MultiSheetManager V1 koordinációs réteget:

```text
rust/vrs_solver/src/optimizer/multisheet.rs
```

Minimum elvárt elemek:

- `MultiSheetManager` vagy repo-konform ekvivalens;
- determinisztikus sheet ordering;
- stabil `sheet_index` contract;
- `used_sheets` / `sheet_count_used` helper;
- sheetenkénti placement/unplaced/violation/score vagy diagnostics summary;
- Phase 1 construction + repair orchestration egy helyen;
- single-sheet regresszió megőrzése;
- multi-sheet fixture és deterministic seed smoke.

## Detailed implementation steps

1. Ellenőrizd a JG-11 dependency-t.
2. Olvasd el a JG task dokumentációkat, a repo szabályokat és ezt a canvast.
3. Auditáld a valós kódot, különösen `adapter.rs`, `initializer.rs`, `repair.rs`, `score.rs`, `io.rs`, `sheet.rs`.
4. Hozd létre az `optimizer/multisheet.rs` modult.
5. Exportáld `optimizer/mod.rs` alatt: `pub mod multisheet;`.
6. A Phase 1 adapter pathban a közvetlen `build_initial_layout()` + `run_repair()` hívásokat cseréld MultiSheetManager orchestration hívásra, de az output contract maradjon kompatibilis.
7. Implementáld és unit teszteld a használt sheet számítást:
   - no placements → 0;
   - only sheet 0 → 1;
   - sheet 0 + sheet 1 → 2;
   - csak sheet 2 esetén a contract szerint vagy `max+1`, vagy explicit DEVIATION dokumentálandó. A jelenlegi contract `max+1`; csak tudatos döntéssel térj el.
8. Biztosítsd, hogy `placed.len() + unplaced.len() == expanded_instances.len()` több sheet mellett is teljesül.
9. Biztosítsd, hogy `sheet_index` minden placementnél `0 <= sheet_index < sheets.len()` exact validation előtt.
10. Készíts multi-sheet smoke scriptet:

```text
scripts/smoke_jagua_multisheet_manager_v1.py
```

11. Frissítsd a JG-12 reportot és checklisteket.
12. Futtasd a task-specifikus teszteket és a repo gate-et.

## Contract requirements

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

## Testing expectations

Minimum commands to run if available in the local environment:

```bash
cargo build --manifest-path rust/vrs_solver/Cargo.toml
cargo test --manifest-path rust/vrs_solver/Cargo.toml
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::multisheet
python3 scripts/smoke_jagua_initial_construction.py
python3 scripts/smoke_jagua_repair_search_v1.py
python3 scripts/smoke_jagua_score_model_v1.py
python3 scripts/smoke_jagua_multisheet_manager_v1.py
./scripts/verify.sh --report codex/reports/egyedi_solver/jagua_optimizer_t12_multi_sheet_manager_v1.md
```

Ha bármelyik parancs nincs jelen vagy környezeti okból nem fut, a reportban konkrét loggal kell jelölni. Környezeti hiba nem lehet rejtett PASS.

## Acceptance criteria

- `rust/vrs_solver/src/optimizer/multisheet.rs` létrejött és valós kód használja.
- `optimizer/mod.rs` exportálja a multisheet modult.
- Phase 1 adapter flow MultiSheetManageren keresztül fut.
- Több rectangular sheet fixture valid.
- `sheet_index` contract nem törik.
- `sheet_count_used` pontos és tesztelt.
- Unplaced kezelés több sheet mellett is helyes.
- Azonos seed / azonos input determinisztikus sheet assignmentet ad.
- Sheetenkénti metrics vagy diagnostics reportolva van.
- Construction + repair több sheet mellett ellenőrzött.
- Single-sheet fixture regresszió nem romlik.
- Exact validation bridge továbbra is végső gate.
- JG-12 progress checklist frissült.
- Repo verify PASS és log mentve.
- Report első sora csak akkor `PASS`, ha minden acceptance gate bizonyított.
- Report végén csak akkor szerepelhet `JG-13_STATUS: READY`, ha JG-12 valóban PASS.

## Failure / rollback policy

- Ha JG-11 dependency nem PASS: `BLOCKED`, nincs implementáció.
- Ha a MultiSheetManager bevezetése single-sheet regressziót okoz: rollback vagy `REVISE`, nincs PASS.
- Ha exact validation invalid layoutot jelez: nincs PASS.
- Ha per-sheet metrics miatt IO contractot kell bővíteni, a meglévő mezők nem törhetők; ha ez nem tartható, `REQUIRES_DECISION`.
- Ha régi tervdokumentáció és aktuális task-bontás ellentmond, az aktuális task-bontás követendő, az eltérés riportolandó.

## Phase gate

JG-12 a Phase 1 multi-sheet alap gate egyik fő eleme. A következő task, JG-13 Sheet Elimination V1, csak akkor indítható, ha JG-12 bizonyítottan stabil több sheetes alapot ad.
