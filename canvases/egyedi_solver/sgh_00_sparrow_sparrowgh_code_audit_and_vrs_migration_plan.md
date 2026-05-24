# SGH-00 — `sgh_00_sparrow_sparrowgh_code_audit_and_vrs_migration_plan`

## Task identity

- **Task id:** SGH-00
- **Slug:** `sgh_00_sparrow_sparrowgh_code_audit_and_vrs_migration_plan`
- **Track:** SparrowGH/Sparrow migration track, JG-20 utáni optimizer quality hardening
- **Goal:** A Sparrow és SparrowGH/coroush fork valós kódjának auditja, majd konkrét, repo-kompatibilis VRS migrációs terv kidolgozása a saját `rust/vrs_solver/src/optimizer` rétegbe.
- **Dependency:** JG-20 — `jagua_optimizer_t20_phase2_irregular_benchmark_matrix`
- **Primary report:** `codex/reports/egyedi_solver/sgh_00_sparrow_sparrowgh_code_audit_and_vrs_migration_plan.md`
- **Verify log:** `codex/reports/egyedi_solver/sgh_00_sparrow_sparrowgh_code_audit_and_vrs_migration_plan.verify.log`
- **Audit output:** `docs/egyedi_solver/sparrow_sparrowgh_code_audit.md`
- **Migration output:** `docs/egyedi_solver/sparrowgh_vrs_migration_plan.md`

## Strategic decision

JG-20 után nem a JG-21 cavity-prepack irány az elsődleges következő lépés, hanem az optimizer minőségi hardening. A beszélgetés alapján a hardening algoritmikus alapja ne általános saját greedy továbbfoltozás legyen, hanem a **SparrowGH/Sparrow kódból átvett vagy újraimplementált search/repair/bin-reduction logika**.

A feladat nem külső benchmark backend építése. Nem akarunk SparrowGH CLI-t production vagy benchmark backendként bekötni. A cél:

```text
Sparrow/SparrowGH kódaudit
→ átvehető algoritmikus komponensek azonosítása
→ mapping a VRS saját jagua_optimizer moduljaira
→ migrációs terv
→ következő SGH implementációs taskok pontos bontása
```

## Dependency gate

SGH-00 csak akkor zárható `PASS` státusszal, ha a JG-20 Phase 2 gate bizonyítottan zöld:

- `codex/reports/egyedi_solver/jagua_optimizer_t20_phase2_irregular_benchmark_matrix.md` létezik;
- a report első sora `PASS` vagy `PASS_WITH_NOTES`;
- tartalmazza: `PHASE2_GATE_DECISION: PASS`;
- tartalmazza: `JG-21_STATUS: READY` vagy explicit Phase 2 továbbhaladási jelzést;
- nincs JG-20 által jelölt `STOP`, `NO-GO` vagy unresolved boundary/validation blocker.

Ha a gate nem teljesül, a task álljon meg `BLOCKED` státusszal. Ebben az esetben csak a reportot és a checklistet frissítsd, ne írj migrációs tervet kész tényként.

## Current repo observations

A csomag a friss `VRS_nesting-main.zip` snapshot valós struktúrája alapján készült.

### Repo rules and task workflow

- `AGENTS.md` rögzíti a real-code-only, outputs-list és verify wrapper szabályokat.
- `docs/codex/yaml_schema.md` szerint a goal YAML kizárólag `steps` listából állhat, minden stepben `name`, `description`, `outputs`, opcionálisan `inputs` mezőkkel.
- `docs/codex/overview.md` szerint minden taskhoz canvas, goal YAML, checklist, report és verify log tartozik.
- `docs/codex/report_standard.md` szerint a reportban DoD → Evidence mátrix kell.

### Jagua optimizer current anchors

Létező VRS optimizer fájlok, amelyeket kötelező auditálni és mappingelni:

```text
rust/vrs_solver/src/adapter.rs
rust/vrs_solver/src/io.rs
rust/vrs_solver/src/main.rs
rust/vrs_solver/src/sheet.rs
rust/vrs_solver/src/item.rs
rust/vrs_solver/src/geometry.rs
rust/vrs_solver/src/optimizer/mod.rs
rust/vrs_solver/src/optimizer/boundary.rs
rust/vrs_solver/src/optimizer/candidates.rs
rust/vrs_solver/src/optimizer/initializer.rs
rust/vrs_solver/src/optimizer/repair.rs
rust/vrs_solver/src/optimizer/score.rs
rust/vrs_solver/src/optimizer/multisheet.rs
rust/vrs_solver/src/optimizer/sheet_elimination.rs
rust/vrs_solver/src/optimizer/moves.rs
rust/vrs_solver/src/optimizer/state.rs
rust/vrs_solver/src/optimizer/stopping.rs
vrs_nesting/runner/vrs_solver_runner.py
vrs_nesting/nesting/instances.py
scripts/bench_jagua_optimizer_phase1_rectangular.py
scripts/bench_jagua_optimizer_phase2_irregular.py
scripts/smoke_jagua_irregular_boundary_validation.py
scripts/smoke_jagua_remnant_score_model_v1.py
```

### Current optimizer state to verify

A helyi agentnek nem szabad ezeket kész tényként kezelnie; ellenőrizze a valós kódban:

- `initializer.rs` jelenleg kezdeti konstrukciót végez, existing candidate sorrend alapján.
- `repair.rs` jelenleg valid layout repair/search V1, nem teljes Sparrow separator.
- `sheet_elimination.rs` létezik, de V1 jellegű, nem teljes SparrowGH-style bin reduction.
- `moves.rs` jelenleg skeleton/egyszerű move model lehet; ezt auditálni kell.
- `state.rs` jelenleg nem biztos, hogy támogat ideiglenes infeasible/colliding working layoutot.
- `score.rs` score breakdownot ad, de auditálni kell, hogy hol döntési mechanizmus és hol utólagos metrika.

## External source audit scope

Auditálandó külső források:

```text
https://github.com/JeroenGar/sparrow
https://github.com/coroush/sparrow
https://github.com/coroush/sparrow-grasshopper  # ha külön wrapper/source repo elérhető
```

A helyi agent clone-olhatja ezeket ideiglenes könyvtárba, például:

```text
/tmp/vrs_sparrow_audit/JeroenGar_sparrow
/tmp/vrs_sparrow_audit/coroush_sparrow
/tmp/vrs_sparrow_audit/coroush_sparrow_grasshopper
```

A külső repo-kat **nem** szabad vendorolni, bemásolni vagy production dependencyként bekötni ebben a taskban.

### Expected SparrowGH/coroush audit targets

Ha léteznek, auditáld legalább:

```text
src/bp_optimizer/mod.rs
src/bp_optimizer/bp_lbf.rs
src/bp_optimizer/bp_separator.rs
src/bp_optimizer/bp_explore.rs
src/bp_optimizer/bp_moves.rs
src/config.rs
src/sample/search.rs
src/eval/lbf_evaluator.rs
src/eval/sep_evaluator.rs
src/quantify/tracker.rs
```

### Expected original Sparrow audit targets

Ha léteznek, auditáld legalább:

```text
src/optimizer/separator.rs
src/optimizer/explore.rs
src/optimizer/compress.rs
src/optimizer/worker.rs
src/sample/search.rs
src/eval/sep_evaluator.rs
src/eval/lbf_evaluator.rs
src/quantify/tracker.rs
src/config.rs
```

Ha egy várt fájl nem létezik, ne találd ki. Írd be az auditba:

```text
NOT_FOUND: <repo>/<path>
```

## Exact scope

SGH-00 scope:

1. JG-20 dependency gate ellenőrzése.
2. Repo szabályok és meglévő JG/Jagua optimizer minták újraolvasása.
3. Külső Sparrow/SparrowGH/coroush source audit.
4. Licenc és attribution audit.
5. Algoritmikus komponensek azonosítása:
   - initial FFD/LBF construction;
   - LBF/sample placement;
   - separator/collision repair;
   - collision loss / weighted loss / tracker;
   - incumbent snapshot / rollback;
   - multi-worker best-loss selection;
   - bin/sheet elimination;
   - transfer/swap/reinsert move operatorok;
   - solution pool / perturbation / stagnation handling;
   - compaction;
   - stopping/time budget.
6. VRS modul mapping:
   - mit melyik `rust/vrs_solver/src/optimizer/*.rs` modulba érdemes átvenni;
   - mihez kell új modul;
   - mihez kell új state representation.
7. Migrációs terv kidolgozása konkrét SGH-01…SGH-N taskokra bontva.
8. Risk/rollback/validation terv.
9. Checklist és report kitöltése.

## Explicit out of scope

- Nem építünk külső SparrowGH benchmark backendet.
- Nem kötünk be SparrowGH CLI-t production vagy benchmark futtatásra.
- Nem vendoroljuk a külső repo-t.
- Nem írunk át Rust optimizer production kódot ebben a taskban.
- Nem implementálunk separator, sheet elimination, move vagy state refaktort ebben a taskban.
- Nem kezdjük el JG-21 cavity-prepack auditot.
- Nem támogatunk natív hole-os part nestinget.
- Nem írjuk át a DXF pipeline-t.
- Nem változtatjuk a solver IO contractot.
- Nem futtatunk nagy benchmarkot a külső SparrowGH motorral.

## Required outputs

SGH-00 végrehajtásának kötelező kimenetei:

```text
docs/egyedi_solver/sparrow_sparrowgh_code_audit.md
docs/egyedi_solver/sparrowgh_vrs_migration_plan.md
codex/codex_checklist/egyedi_solver/sgh_00_sparrow_sparrowgh_code_audit_and_vrs_migration_plan.md
codex/reports/egyedi_solver/sgh_00_sparrow_sparrowgh_code_audit_and_vrs_migration_plan.md
codex/reports/egyedi_solver/sgh_00_sparrow_sparrowgh_code_audit_and_vrs_migration_plan.verify.log
```

A canvas/YAML/runner csomag része, de futás közben csak akkor módosítsd, ha a valós repo audit alapján korrekció szükséges:

```text
canvases/egyedi_solver/sgh_00_sparrow_sparrowgh_code_audit_and_vrs_migration_plan.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_00_sparrow_sparrowgh_code_audit_and_vrs_migration_plan.yaml
codex/prompts/egyedi_solver/sgh_00_sparrow_sparrowgh_code_audit_and_vrs_migration_plan/run.md
```

## Audit document structure

`docs/egyedi_solver/sparrow_sparrowgh_code_audit.md` minimum struktúra:

```text
# Sparrow / SparrowGH code audit

## Source repositories and pinned refs
## License and attribution
## Original Sparrow architecture summary
## SparrowGH/coroush BPP architecture summary
## File-by-file audit
## Algorithmic components
## What is directly reusable
## What must be reimplemented VRS-style
## What must not be copied/adopted
## Gaps and uncertainties
## Evidence appendix
```

Minden file-by-file bejegyzés tartalmazza:

```text
- repo
- ref/commit
- path
- relevant functions/types
- what it does
- VRS relevance
- porting risk
- direct-copy allowed? yes/no/avoid
```

## Migration document structure

`docs/egyedi_solver/sparrowgh_vrs_migration_plan.md` minimum struktúra:

```text
# SparrowGH → VRS jagua_optimizer migration plan

## Decision
## Target architecture
## VRS module mapping
## State model changes
## Separator migration plan
## Initial construction migration plan
## Sheet elimination migration plan
## Move operators migration plan
## Solution pool / perturbation plan
## Scoring and exact validation integration
## Irregular/remnant handling
## Rotation policy handling
## Test and benchmark strategy
## Rollback strategy
## Proposed SGH task chain
## Acceptance gates
```

## Required migration task chain

A migrációs terv javasoljon konkrét következő taskokat. Minimum váz:

```text
SGH-01 — working layout / infeasible search state audit + scaffold
SGH-02 — per-sheet separator V1
SGH-03 — LBF + separator fallback construction
SGH-04 — sheet elimination / bin reduction V1
SGH-05 — transfer/swap/reinsert move operators
SGH-06 — solution pool / perturbation / stagnation handling
SGH-07 — VRS quality benchmark suite + exact validator gate
SGH-08 — irregular/remnant hardening on migrated search loop
```

A helyi agent módosíthatja ezt a listát, de csak valós kódaudit alapján, és a reportban `DEVIATION` / `RATIONALE` szakaszban magyarázza meg.

## Hard rules

```text
REAL_CODE_ONLY:
- Csak valós repó fájlokra, valóban megtalált külső forrásokra és tényleges kódrészletekre támaszkodj.
- Ne találj ki Sparrow/SparrowGH modulokat, függvényeket vagy API-kat.
- Ha valami hiányzik, azt NOT_FOUND vagy UNKNOWN státusszal dokumentáld.
```

```text
NO_EXTERNAL_BENCHMARK_BACKEND:
- Ebben a taskban tilos SparrowGH CLI-t VRS benchmark backendként bekötni.
- A külső kód csak audit source.
- A migráció célja saját VRS optimizerbe portolt vagy újraimplementált logika.
```

```text
NO_PRODUCTION_CODE_CHANGE:
- SGH-00 audit+terv task.
- Ne módosíts Rust production optimizer kódot, Python runner code-ot vagy solver IO contractot.
- Ha kódmódosítás szükségesnek látszik, azt csak a migrációs tervben javasold következő SGH taskként.
```

```text
LICENSE_REQUIRED:
- Ellenőrizd az eredeti Sparrow és a coroush/SparrowGH licencét.
- Írd le, milyen attribution / copyright megőrzés kell direct copy esetén.
- Ha bármely külső repo licenc tisztázatlan, a direct-copy opció BLOCKED.
```

```text
EXACT_VALIDATION_REQUIRED:
- A migrációs tervben minden későbbi implementáció végső acceptance gate-je a VRS exact validator legyen.
- Ideiglenes infeasible/colliding search state megengedhető későbbi taskokban, de final accepted output csak validator PASS lehet.
```

```text
CHECKLIST_REQUIRED:
- Frissítsd a task-specifikus checklistet.
- A report csak akkor lehet PASS, ha minden DoD ponthoz evidence tartozik.
```

## Acceptance criteria / DoD

SGH-00 akkor PASS, ha:

- JG-20 dependency gate dokumentált és zöld, vagy BLOCKED esetben egyértelműen dokumentált.
- Legalább az eredeti Sparrow és a coroush/SparrowGH/coroush-sparrow forrás elérhetősége ellenőrizve van.
- Külső repo ref/commit és licenc dokumentálva van.
- File-by-file audit készült a releváns Sparrow/SparrowGH optimizer fájlokról.
- VRS oldali jelenlegi optimizer modulok auditálva és mappingelve vannak.
- Elkészült a migrációs terv, amely nem külső benchmark backendre, hanem saját VRS optimizerbe történő átvételre épül.
- A terv tartalmaz konkrét SGH-01… implementációs taskláncot acceptance gate-ekkel.
- A terv explicit kezeli: infeasible working state, separator, sheet elimination, moves, solution pool, scoring, exact validator, irregular/remnant és rotation policy kérdését.
- Nem történt production kódmódosítás.
- `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_00_sparrow_sparrowgh_code_audit_and_vrs_migration_plan.md` lefutott vagy környezeti okból dokumentáltan nem futtatható.

## Report status rules

- `PASS`: minden DoD teljesül, report evidence kitöltve, verify lefutott vagy dokumentáltan nem releváns audit-only környezeti blocker nélkül.
- `PASS_WITH_NOTES`: DoD teljesül, de vannak nem blokkoló bizonytalanságok, például egy wrapper repo nem elérhető, miközben a lényegi Sparrow/coroush source audit teljes.
- `FAIL`: kódaudit hiányos, migrációs terv általános/nem valós kódra épül, vagy production kód módosult scope-on kívül.
- `BLOCKED`: JG-20 dependency nem zöld, külső források nem elérhetők és nincs hiteles alternatív source, vagy licenc nem tisztázható.

## Recommended final marker

Sikeres SGH-00 report végére kerüljön:

```text
SGH-01_STATUS: READY
```
