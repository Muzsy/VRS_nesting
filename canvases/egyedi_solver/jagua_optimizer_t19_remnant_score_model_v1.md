# JG-19 — `jagua_optimizer_t19_remnant_score_model_v1`

## Task identity

- **Task id:** JG-19
- **Slug:** `jagua_optimizer_t19_remnant_score_model_v1`
- **Phase:** Phase 2 / remnant scoring
- **Goal:** Remnant/sheet cost score V1: remnant preferencia, új teljes tábla nyitási büntetés, usable-area utilization és auditálható sheet-cost/utilization breakdown.
- **Dependency:** JG-18 — `jagua_optimizer_t18_irregular_candidate_generation`
- **Primary report:** `codex/reports/egyedi_solver/jagua_optimizer_t19_remnant_score_model_v1.md`
- **Verify log:** `codex/reports/egyedi_solver/jagua_optimizer_t19_remnant_score_model_v1.verify.log`

## Dependency gate

JG-19 csak akkor implementálható, ha ezek bizonyítottan teljesülnek:

- `codex/reports/egyedi_solver/jagua_optimizer_t18_irregular_candidate_generation.md` létezik;
- a JG-18 report első sora `PASS` vagy repo-konform `PASS_WITH_NOTES`;
- a JG-18 report tartalmazza: `JG-19_STATUS: READY`;
- `rust/vrs_solver/src/optimizer/candidates.rs` tartalmazza az irregular-aware candidate API-t;
- `scripts/smoke_jagua_irregular_candidate_generation.py` létezik és JG-18 report szerint PASS volt;
- nincs JG-18 által jelölt `STOP`, `NO-GO` vagy unresolved irregular candidate blocker.

Ha bármelyik feltétel nem teljesül, a JG-19 futás `BLOCKED`, és nem szabad score-modell módosítást sikeresként lezárni.

## Strategic background

JG-15–JG-18 után a Phase 2 képes hole-free irregular/remnant stockokat beolvasni, boundary-valid placementeket szűrni, és irregular-aware candidate pontokat generálni. A következő hiányzó réteg nem geometriai, hanem **objective/scoring döntési réteg**: vegyes normál téglalap sheet + remnant készlet esetén a solvernek magyarázhatóan preferálnia kell a remnant használatát, ha az valid és életszerűen hasznos.

A JG-19 nem végleges vállalati inventory/costing rendszer. Ez egy V1 nesting objective proxy, amelynek célja:

- ne legyen minden sheet egyforma költségű;
- a teljes új tábla nyitása legyen drágább, mint egy már rendelkezésre álló remnant használata;
- a usable-area utilization jelenjen meg score-breakdownban;
- invalid boundary/overlap layout továbbra se lehessen jó score-ral sikeres;
- a döntés legyen auditálható reportban és smoke-ban.

## Current repo observations

A csomag a friss repo snapshot valós kódja alapján készült:

- `rust/vrs_solver/src/optimizer/score.rs`
  - létezik;
  - Phase 1 ScoreModel V1 már van;
  - `ScoreWeights` jelenlegi mezői: `placed_area_reward`, `unplaced_penalty_per_item`, `sheet_count_penalty_per_sheet`, `overlap_penalty_per_pair`, `boundary_penalty_per_item`, `compactness_weight`;
  - `ObjectiveBreakdown` jelenleg placed/unplaced/sheet_count/overlap/boundary/compactness komponenseket tartalmaz;
  - invalid layout dominancia már létezik overlap/boundary `1e9` büntetéssel;
  - nincs sheet-cost/remnant preference/usable-area utilization mező.
- `rust/vrs_solver/src/sheet.rs`
  - `Stock` jelenleg `id`, `quantity`, `width`, `height`, `outer_points`, `holes_points` mezőket tartalmaz;
  - `SheetShape` tartalmaz `area`, `has_irregular_outer`, `outer_vertices`, bbox és polygon adatokat;
  - nem tartalmaz stock-id, sheet-kind, material-cost vagy inventory-cost mezőt;
  - ezért JG-19-ben vagy backward-compatible metadata bővítés kell, vagy jól dokumentált inference/proxy.
- `rust/vrs_solver/src/optimizer/multisheet.rs`
  - `MultiSheetDiagnostics` tartalmaz `per_sheet: Vec<SheetSummary>` mezőt;
  - `SheetSummary` jelenleg `sheet_index`, `placed_count`, `placed_area`;
  - `SheetShape.area` alapján usable-area utilization kiszámítható.
- `rust/vrs_solver/src/adapter.rs`
  - `diag` jelenleg eldobásra kerül: `let _ = diag`;
  - `io::Metrics` csak `placed_count`, `unplaced_count`, `sheet_count_used`, `seed`, `time_limit_s`, `project_name` mezőket serializál;
  - ha JG-19 score/diagnostics kimenetet akar JSON-ban is bizonyítani, itt vagy `Metrics`/report/smoke szinten kell bekötni, backward-compatible módon.
- `docs/solver_io_contract.md`
  - JG-16/JG-17 irregular boundary és JG-18 candidate generation contract szakaszok már szerepelnek;
  - JG-19 remnant score/sheet-cost contract még nincs.
- `scripts/smoke_jagua_score_model_v1.py`
  - létezik, JG-11 regressionként használható;
  - JG-19-hez új `scripts/smoke_jagua_remnant_score_model_v1.py` szükséges.
- `tests/fixtures/egyedi_solver/jagua_irregular_candidate_generation.json`
  - létezik;
  - JG-19-hez külön vegyes rectangular + remnant fixture kell, hogy a sheet-choice döntés bizonyítható legyen.

## DISCOVERED_MISMATCH / implementation note

```text
task breakdown says: remnant/sheet cost score V1 with remnant preference, full sheet opening penalty, usable-area utilization
current repo says: Stock/SheetShape has no explicit remnant/inventory-cost schema; ScoreModel V1 is generic Phase 1 scoring with only sheet_count and compactness; adapter currently drops MultiSheetDiagnostics
proposed resolution: implement a backward-compatible V1 sheet-cost metadata strategy. Prefer explicit optional Stock metadata only if it can be added without breaking existing fixtures. Otherwise define a documented proxy/inference policy, e.g. irregular stock or stock id containing remnant is treated as lower opening cost for V1 smoke, and record this as non-final inventory proxy in docs/egyedi_solver/jagua_remnant_score_model_v1.md.
```

JG-19 ne törje el a Phase 1 rectangular behavior-t és ne vezessen be hallgatólagos üzleti inventory szabályt. Ha a valós kód audit szerint nincs megbízható explicit remnant input field, a V1 proxyt dokumentálni kell, és későbbi inventory/cost taskra kell hagyni a végleges sémát.

## Exact scope

JG-19 implementációs scope:

1. `ScoreWeights` bővítése remnant/sheet-cost V1 komponensekkel.
2. `ObjectiveBreakdown` bővítése auditálható sheet-cost és usable-area utilization mezőkkel.
3. Sheet metadata modell vagy dokumentált V1 inference/proxy:
   - remnant preferencia súly;
   - új teljes tábla nyitási büntetés;
   - usable-area utilization per used sheet és/vagy aggregate;
   - sheet-cost contribution.
4. `SheetShape` és/vagy kapcsolódó sheet metadata bővítése, ha szükséges és backward-compatible.
5. ScoreModel invalid-dominancia megtartása: overlap/boundary penalty továbbra is dominál.
6. Vegyes rectangular + remnant fixture és smoke script létrehozása.
7. Reportban sheet choice magyarázat és score breakdown.
8. Rectangular-only score regression bizonyítása.
9. JG-18 irregular candidate/boundary regressziók megtartása.
10. Contract dokumentáció létrehozása/frissítése.
11. Checklist és globális progress checklist frissítése.
12. Csak valódi PASS esetén a report végére: `JG-20_STATUS: READY`.

## Out of scope

- Nem cél JG-20 Phase 2 benchmark matrix.
- Nem cél végleges inventory/costing schema, ERP/inventory integráció vagy material price modell.
- Nem cél stock/container hole, part hole vagy cavity-prepack támogatás.
- Nem cél új candidate generator vagy boundary validator újraírása.
- Nem cél sheet elimination algoritmus átírása, kivéve ha a score használata minimális, dokumentált integrációt igényel.
- Nem cél `SolverOutput` v1 breaking változtatás; opcionális új mező csak backward-compatible lehet.
- Nem cél Python exact validator lazítása vagy kikapcsolása.

## Required implementation outputs

A JG task-bontás és a valós kód alapján legalább ezek érintettek vagy vizsgálandók:

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

Ha a valós audit alapján valamelyik fájl módosítása szükségtelen, a reportban rögzítsd. Ha további fájl kell, előbb frissítsd a YAML `outputs` listáját, mert az `AGENTS.md` szerint csak deklarált output módosítható.

## Detailed execution plan

1. Olvasd el a repo szabályokat és a JG tervdokumentációkat.
2. Ellenőrizd a JG-18 dependency gate-et.
3. Auditáld a jelenlegi score útvonalat: `score.rs`, `multisheet.rs`, `adapter.rs`, `io.rs`, `sheet.rs`.
4. Döntsd el a V1 sheet-cost metadata stratégiát:
   - explicit optional input metadata, ha biztonságosan és backward-compatible módon illeszthető;
   - vagy dokumentált V1 proxy/inference policy, ha nincs kész input schema.
5. Vezesd be a remnant/sheet-cost score komponenseket:
   - remnant preference;
   - new full sheet opening penalty;
   - usable-area utilization;
   - score breakdown mezők.
6. Biztosítsd, hogy invalid overlap/boundary layout továbbra is rosszabb legyen, mint bármely valid layout.
7. Hozz létre dokumentált vegyes rectangular + remnant fixture-t.
8. Készíts smoke scriptet, amely bizonyítja:
   - score breakdown elérhető;
   - remnant sheet választás magyarázható;
   - rectangular-only regression nincs;
   - invalid layout jó score-ral nem sikeres;
   - default weight profile reportolva.
9. Frissítsd `docs/egyedi_solver/jagua_remnant_score_model_v1.md` és `docs/solver_io_contract.md` dokumentumokat.
10. Futtasd a célzott smoke-ot, Rust score teszteket, JG-18 regressziót és repo verify wrapperét.
11. Frissítsd a task-specifikus checklistet és a globális progress checklist JG-19 szakaszát.
12. Csak valódi PASS esetén írd a report végére: `JG-20_STATUS: READY`.

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
- Any accepted layout must pass the existing exact validation bridge.
- Invalid layout cannot be accepted as success.
- A layout with boundary/overlap violation must not become preferable merely because remnant sheet cost is favorable.
```

```text
CHECKLIST_REQUIRED:
- Update the task-specific checklist entries in jagua_optimizer_task_progress_checklist.md.
- A task cannot be PASS unless the relevant checklist items are checked or explicitly marked BLOCKED/DEVIATION with evidence.
```

## Required tests / verification

Minimum targeted checks:

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::score
python3 scripts/smoke_jagua_remnant_score_model_v1.py
python3 scripts/smoke_jagua_score_model_v1.py
python3 scripts/smoke_jagua_irregular_candidate_generation.py
./scripts/verify.sh --report codex/reports/egyedi_solver/jagua_optimizer_t19_remnant_score_model_v1.md
```

Ha a valós repo parancsai eltérnek, a reportban dokumentáld, de ne találj ki nem létező toolt. Ha dependency vagy környezeti hiba miatt valamelyik parancs nem fut, különítsd el environment blocker és kódhiba között.

## Acceptance criteria

JG-19 akkor zárható PASS-szal, ha:

- JG-18 dependency bizonyítottan PASS + `JG-19_STATUS: READY`;
- sheet cost metadata modell vagy dokumentált V1 proxy létezik;
- remnant preferencia súly dokumentált;
- új teljes tábla nyitási büntetés dokumentált;
- usable-area utilization számítás működik;
- vegyes rectangular + remnant fixture fut;
- score breakdown magyarázható sheet választást ad;
- invalid boundary/overlap nem lehet jó score-ral sikeres;
- Score weight defaultok reportolva;
- rectangular-only score regresszió nincs;
- döntési példák szerepelnek a reportban;
- smoke/benchmark PASS;
- repo verify PASS és log mentve;
- task-specifikus és globális checklist frissítve;
- report első sora `PASS` vagy repo-konform `PASS_WITH_NOTES`;
- csak valódi PASS esetén szerepel: `JG-20_STATUS: READY`.

## Failure / rollback policy

- Ha explicit remnant metadata schema bevezetése breaking lenne, állj meg `REQUIRES_DECISION` vagy `BLOCKED` státusszal; ne vezesd be csendben inkompatibilis inputot.
- Ha a remnant preference invalid layoutot preferálna valid layout felett, a task `FAIL`.
- Ha a mixed fixture nem bizonyít magyarázható sheet choice-ot, a task `REVISE` vagy `FAIL`, nem PASS.
- Ha a Python exact validation regressziót mutat, rollbackeld a score/output integrációt, és dokumentáld.
- Ha csak környezeti dependency hiba van, ezt a reportban külön jelöld; ne keverd össze kódhibával.

## Phase gate impact

JG-19 nem zár phase gate-et, de közvetlenül előkészíti JG-20-at, amely a Phase 2 irregular/remnant benchmark matrix. A JG-19 reportban ezért egyértelműen szerepelnie kell, hogy JG-20 indítható-e.
