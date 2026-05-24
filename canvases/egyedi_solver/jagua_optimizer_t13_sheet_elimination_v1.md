# JG-13 — `jagua_optimizer_t13_sheet_elimination_v1`

## Task identity

- **Task id:** JG-13
- **Slug:** `jagua_optimizer_t13_sheet_elimination_v1`
- **Phase:** Phase 1 / sheet count reduction
- **Goal:** Sheet Elimination V1: choose the weakest used sheet, try to move all its items to the remaining sheets, commit only if the layout remains exact-valid and `sheet_count_used` decreases; otherwise rollback without degrading the current valid layout.
- **Dependency:** JG-12 — `jagua_optimizer_t12_multi_sheet_manager_v1`
- **Primary report:** `codex/reports/egyedi_solver/jagua_optimizer_t13_sheet_elimination_v1.md`
- **Verify log:** `codex/reports/egyedi_solver/jagua_optimizer_t13_sheet_elimination_v1.verify.log`

## Dependency gate

JG-13 csak akkor implementálható, ha ezek bizonyítottan teljesülnek:

- `codex/reports/egyedi_solver/jagua_optimizer_t12_multi_sheet_manager_v1.md` létezik;
- a JG-12 report első sora `PASS`;
- a JG-12 report tartalmazza: `JG-13_STATUS: READY`;
- `rust/vrs_solver/src/optimizer/multisheet.rs` létezik;
- `scripts/smoke_jagua_multisheet_manager_v1.py` létezik;
- a JG-12 report bizonyítja, hogy a multi-sheet smoke és repo gate PASS.

Ha bármelyik nem teljesül, a JG-13 futás `BLOCKED`, és nem szabad implementációs kódot módosítani.

## Source-of-truth megjegyzés

A hivatalos aktuális task-bontás szerint:

```text
JG-13 = Sheet Elimination V1
```

A régebbi `jagua_rs_sajat_optimizer_fejlesztesi_terv.md` egy helyen `Task JG-13 — Single-child cavity-prepack` néven említi a 13-as taskot. Ez tervverzió-eltérés. JG-13 esetén az aktuális `jagua_optimizer_canvas_yaml_runner_task_bontas.md`, a progress checklist, a task index és a JG-12 report `JG-13_STATUS: READY` jelzése az irányadó.

```text
DISCOVERED_MISMATCH:
- old plan says: Task JG-13 — Single-child cavity-prepack
- current task breakdown says: JG-13 — jagua_optimizer_t13_sheet_elimination_v1
- resolution: follow current task breakdown/checklist/master-runner chain; do not implement cavity-prepack in JG-13
```

## Strategic background

A Phase 1 célja stabil rectangular, outer-only, multi-sheet solver. JG-12 már létrehozta a `MultiSheetManager` koordinációs réteget, amely a construction + repair flow-t egy helyre gyűjti. JG-13 erre épít: a több sheetes eredmény minőségét azzal javítja, hogy megpróbálja eltüntetni a leggyengébb sheetet.

Ez ipari szempontból fontosabb, mint egy puszta packing-density finomítás, mert a használt táblák száma közvetlen költség. A sheet elimináció azonban veszélyes művelet: ha sikertelen vagy invalid layoutot hoz létre, tilos sikerként elfogadni. Ezért JG-13 fő kockázatkezelési szabálya: **snapshot → attempt → exact validation → commit vagy rollback**.

## Out of scope

- Nem cél a JG-14 benchmark matrix megvalósítása.
- Nem cél remnant/irregular sheet support.
- Nem cél cavity extraction vagy cavity-prepack.
- Nem cél hole-os partok támogatása; Phase 1 továbbra is outer-only / hole-gated.
- Nem cél SA, global metaheuristic, NFP provider vagy Sparrow teljes átvétel.
- Nem cél a ScoreModel súlyainak széles tuningja; csak akkor módosítható, ha a sheet elimination döntési metrikához minimálisan szükséges és backward-compatible.
- Tilos az exact validator gyengítése, kikapcsolása vagy megkerülése.

## Relevant current repo files

### Rust solver

- `rust/vrs_solver/src/optimizer/mod.rs` — optimizer modul exportok; JG-13-ban innen kell exportálni a `sheet_elimination` modult.
- `rust/vrs_solver/src/optimizer/multisheet.rs` — JG-12 MultiSheetManager, `compute_sheet_count_used()`, per-sheet diagnostics; JG-13 alapja.
- `rust/vrs_solver/src/optimizer/initializer.rs` — bbox helper és construction logic; reinsert attempthez használható minták.
- `rust/vrs_solver/src/optimizer/repair.rs` — `run_repair()`, `find_violations()`, deterministic repair queue és `RepairDiagnostics`; rollback utáni validitás ellenőrzéshez és reinsertion stílushoz irányadó.
- `rust/vrs_solver/src/optimizer/candidates.rs` — `generate_candidates()` és `PlacedBbox`; sheet-aware deterministic candidate generation.
- `rust/vrs_solver/src/optimizer/score.rs` — ScoreModel V1, `ObjectiveBreakdown`, sheet-count penalty; attempt comparison és diagnostics alap.
- `rust/vrs_solver/src/optimizer/state.rs` — `LayoutState`, `PlacedItem`, `UnplacedItem`, `PlacementTransform`; snapshot/rollback modelhez használható vagy mintaként kezelendő.
- `rust/vrs_solver/src/optimizer/moves.rs` — `CandidateMove`; ha reinsert/move candidate abstraction kell, ehhez igazodj.
- `rust/vrs_solver/src/optimizer/stopping.rs` — `StoppingPolicy`; JG-13-nak tiszteletben kell tartania a limitet.
- `rust/vrs_solver/src/adapter.rs` — Phase 1 runtime boundary; JG-13 wiring itt vagy `MultiSheetManager` alatt történjen, de output contract nem törhet.
- `rust/vrs_solver/src/io.rs` — `SolverOutput`, `Placement`, `Unplaced`, `Metrics`; `contract_version = v1` kompatibilitás nem törhető.
- `rust/vrs_solver/src/item.rs` — instance expansion, rotations, `ItemGeometryStore`.
- `rust/vrs_solver/src/sheet.rs` — stock expansion, sheet boundary.

### Python / smoke / wrapper

- `vrs_nesting/runner/vrs_solver_runner.py` — Python oldali Rust solver boundary.
- `scripts/smoke_jagua_multisheet_manager_v1.py` — JG-12 multi-sheet regression alap.
- `scripts/smoke_jagua_initial_construction.py`
- `scripts/smoke_jagua_repair_search_v1.py`
- `scripts/smoke_jagua_score_model_v1.py`
- `scripts/smoke_jagua_exact_validation_bridge.py`
- `scripts/check.sh`
- `scripts/verify.sh`

## Real code observations to verify during implementation

- JG-12 után `adapter::solve()` Phase 1 pathja `MultiSheetManager::run()`-on keresztül fut.
- `MultiSheetManager::run()` jelenleg construction + repair után adja vissza a layoutot; sheet elimination még nincs benne.
- `compute_sheet_count_used()` v1 contractja `max(sheet_index)+1`, nem distinct sheet count. JG-13 commit feltétele ezért csak akkor tiszta, ha az eliminált sheet a legmagasabb használt index vagy ha explicit, valid és backward-compatible sheet compaction döntés születik.
- `repair::run_repair()` már rendelkezik determinisztikus reinsert logikával és stopping policy-val; JG-13-nak lehetőség szerint ezt vagy ugyanilyen mintát kell használnia.
- `find_violations()` képes overlap és boundary/sheet hibák detektálására. Eliminációs siker invalid layout esetén tilos.
- `Metrics.sheet_count_used` jelenleg az adapterben is `max(sheet_index)+1` alapján számolódik; a JG-13-nak ezt nem törheti.
- Nincs jelenlegi `rust/vrs_solver/src/optimizer/sheet_elimination.rs`; ezt JG-13 hozza létre.

## Implementation target

Vezess be Sheet Elimination V1 modult:

```text
rust/vrs_solver/src/optimizer/sheet_elimination.rs
```

Minimum elvárt elemek:

- `SheetEliminationEngine` vagy repo-konform ekvivalens;
- `SheetEliminationDiagnostics` vagy repo-konform ekvivalens;
- weakest sheet selection rule;
- deterministic reinsert order;
- rollback snapshot;
- attempt/success/fail metrics;
- exact validation / violation check kapu;
- time limit / stopping policy figyelembevétele;
- unit tests;
- smoke script: `scripts/smoke_jagua_sheet_elimination_v1.py`.

## Recommended algorithm V1

1. Vegyél snapshotot az aktuális valid layout állapotáról: placements, unplaced, sheet_count_used, diagnostics.
2. Számítsd ki a használt sheeteket és sheetenkénti summaryt.
3. Válaszd ki a leggyengébb sheetet determinisztikusan:
   - elsődlegesen legalacsonyabb placed area vagy legalacsonyabb placed count;
   - tie-break: legmagasabb sheet index preferált, mert `max+1` sheet_count contract mellett ez csökkenti legbiztonságosabban a `sheet_count_used` értéket;
   - a pontos szabályt dokumentáld és teszteld.
4. Távolítsd el a kiválasztott sheet placementjeit, és tedd őket reinsert queue-ba.
5. Próbáld őket visszahelyezni a többi sheetre determinisztikus sorrendben:
   - nagyobb area előre;
   - majd `instance_id` növekvő;
   - candidate pontok a meglévő `generate_candidates()` mintája szerint.
6. A kiválasztott sheetre ne helyezz vissza, különben nincs elimináció.
7. Minden attempt során tiszteld a `StoppingPolicy`-t.
8. Ha minden item visszakerült, futtasd a violation/exact validation gate-et.
9. Commit csak akkor:
   - nincs invalid placement;
   - nincs új unplaced romlás;
   - `sheet_count_used` csökkent;
   - a layout score nem romlott, vagy a score döntés explicit dokumentált.
10. Ha bármely feltétel nem teljesül, rollback az eredeti snapshotra.

## Detailed implementation steps

1. Ellenőrizd a JG-12 dependency-t.
2. Olvasd el a JG task dokumentációkat, repo szabályokat, ezt a canvast és a goal YAML-t.
3. Auditáld a valós kódot, különösen `multisheet.rs`, `repair.rs`, `candidates.rs`, `score.rs`, `adapter.rs`, `io.rs`.
4. Hozd létre az `optimizer/sheet_elimination.rs` modult.
5. Exportáld `optimizer/mod.rs` alatt: `pub mod sheet_elimination;`.
6. Döntsd el, hogy az elimináció `MultiSheetManager::run()` része lesz vagy külön meghívható post-process. Az elsődleges javaslat: JG-13-ban a Phase 1 manager run végén, construction+repair után fusson optional V1 passként.
7. Implementáld a weakest sheet kiválasztási szabályt és unit teszteket.
8. Implementáld a rollback snapshotot úgy, hogy sikertelen attempt után byte/mező szinten visszaálljon a korábbi placement/unplaced állapot.
9. Implementáld a reinsert attemptet úgy, hogy a kiválasztott sheetre ne kerüljön vissza item.
10. Implementáld a diagnostics mezőket: attempts, successful_eliminations, failed_eliminations, rollback_count, selected_sheet, before/after sheet_count_used, stop_reason.
11. Integráld az exact/violation checket. Ha csak Rust oldali violation check érhető el, azt használd kötelező minimumnak; Python smoke-ban futtasd az exact validation bridge-et, ha elérhető.
12. Készíts Rust unit teszteket és `scripts/smoke_jagua_sheet_elimination_v1.py` smoke scriptet.
13. Frissítsd a task-specifikus és globális checklistet.
14. Frissítsd a reportot részletes evidence-szel.
15. Futtasd a task-specifikus és repo-wide ellenőrzéseket.

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
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::sheet_elimination
python3 scripts/smoke_jagua_multisheet_manager_v1.py
python3 scripts/smoke_jagua_sheet_elimination_v1.py
python3 scripts/smoke_jagua_exact_validation_bridge.py
./scripts/verify.sh --report codex/reports/egyedi_solver/jagua_optimizer_t13_sheet_elimination_v1.md
```

Ha bármelyik parancs nincs jelen vagy környezeti okból nem fut, a reportban konkrét loggal kell jelölni. Környezeti hiba nem lehet rejtett PASS.

## Acceptance criteria

- `rust/vrs_solver/src/optimizer/sheet_elimination.rs` létrejött és valós kód használja.
- `optimizer/mod.rs` exportálja a `sheet_elimination` modult.
- Sheet elimináció csak JG-12 PASS után futtatható.
- Weakest sheet kiválasztási szabály dokumentált és determinisztikus.
- Sheet ürítési próbák implementálva.
- Reinsert order determinisztikus.
- Sikeres elimináció esetén `sheet_count_used` csökken.
- Sikertelen elimináció rollbackel.
- Rollback után a valid layout nem romlik.
- Mesterséges fixture-ben legalább egy sheet eliminálható.
- Reportban attempt/success/fail metrikák szerepelnek.
- Invalid layout nem lehet eliminációs siker.
- Time limit/stopping policy figyelembe véve.
- Regression futott JG-12 fixture-ökre.
- Exact validation gate nem gyengült.
- Repo verify PASS és log mentve.

## Report requirements

Frissítsd:

```text
codex/reports/egyedi_solver/jagua_optimizer_t13_sheet_elimination_v1.md
```

A report tartalmazza:

- dependency evidence JG-12-ből;
- source-of-truth mismatch dokumentációt a régi JG-13 cavity-prepack tervnév miatt;
- real code audit összefoglalót;
- weakest sheet rule pontos leírását;
- rollback policy bizonyítékát;
- attempt/success/fail metrikákat;
- tesztparancsokat és eredményeket;
- exact validation / violation gate evidence-t;
- git diff / changed files összefoglalót;
- végső státuszt.

A report végén csak akkor szerepelhet:

```text
JG-14_STATUS: READY
```

ha JG-13 valóban PASS, és a sheet elimináció validált, rollback-biztos.

## Checklist update requirements

Frissítsd:

```text
codex/codex_checklist/egyedi_solver/jagua_optimizer_t13_sheet_elimination_v1.md
canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md
```

Csak bizonyított pontot pipálj ki. Ha egy pont nem teljesült, maradjon üresen, vagy kapjon explicit `BLOCKED/DEVIATION` megjegyzést bizonyítékkal.

## Failure / rollback policy

- Ha dependency hiányzik vagy nem PASS: `BLOCKED`, nincs implementation diff.
- Ha a sheet elimination invalid layoutot hoz létre: rollback és `REVISE` vagy `FAIL`, nem PASS.
- Ha a sheet count nem csökken: az attempt lehet dokumentált failure, de nem successful elimination.
- Ha time limit miatt félbeszakad: rollback az utolsó valid snapshotra.
- Ha exact validation nem futtatható környezeti okból: nincs tiszta PASS.
- Ha downstream output contract sérül: rollback vagy javítás kötelező.

## Phase gate relevance

JG-13 a Phase 1 benchmark gate közvetlen előfeltétele. JG-14 csak akkor indítható, ha a sheet elimináció:

- valid layoutot hagy maga után;
- rollback-biztos;
- legalább mesterséges fixture-ben bizonyítja a sheet count reductiont;
- nem okoz regressziót a JG-12 multi-sheet fixture-ökön.
