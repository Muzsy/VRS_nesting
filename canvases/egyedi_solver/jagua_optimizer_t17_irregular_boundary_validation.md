# JG-17 — `jagua_optimizer_t17_irregular_boundary_validation`

## Task identity

- **Task id:** JG-17
- **Slug:** `jagua_optimizer_t17_irregular_boundary_validation`
- **Phase:** Phase 2 / boundary validation
- **Goal:** Irregular/remnant sheet boundary validation véglegesítése: item nem lóghat ki a usable stock polygonból, és invalid boundary layout nem lehet successful.
- **Dependency:** JG-16 — `jagua_optimizer_t16_irregular_sheet_provider_and_margin`
- **Primary report:** `codex/reports/egyedi_solver/jagua_optimizer_t17_irregular_boundary_validation.md`
- **Verify log:** `codex/reports/egyedi_solver/jagua_optimizer_t17_irregular_boundary_validation.verify.log`

## Dependency gate

JG-17 csak akkor implementálható, ha ezek bizonyítottan teljesülnek:

- `codex/reports/egyedi_solver/jagua_optimizer_t16_irregular_sheet_provider_and_margin.md` létezik;
- a JG-16 report első sora `PASS` vagy repo-konform `PASS_WITH_NOTES`;
- a JG-16 report tartalmazza: `JG-17_STATUS: READY`;
- `docs/egyedi_solver/jagua_irregular_sheet_spike_decision.md` létezik;
- a decision report tartalmazza: `JG-15_DECISION: OWN_BOUNDARY_VALIDATOR_PLUS_JAGUA_COLLISION`;
- `docs/solver_io_contract.md` dokumentálja a JG-16 irregular sheet boundary policy-t;
- nincs JG-16 által jelölt `STOP` / `NO-GO` / unresolved margin blocker, amely JG-17-et tiltja.

Ha bármelyik feltétel nem teljesül, a JG-17 futás `BLOCKED`, és nem szabad boundary validation kódot sikeresként lezárni.

## Strategic background

JG-15 kimondta, hogy a jelenlegi `jagua-rs` integrációból nem látszik natív irregular/concave sheet container API. A jó irány: **saját VRS boundary validator + jagua item-item collision**. JG-16 ennek provider oldali előkészítését elvégezte: `Stock.outer_points`, irregular `SheetShape`, `_outer_poly`, `has_irregular_outer`, area metadata és conservative margin policy már létezik.

JG-17 feladata nem új keresőheurisztika, hanem a boundary validation policy és gate megszilárdítása. A cél az, hogy a construction/repair/score/exact validator útvonalakon ugyanaz az elv érvényesüljön: ami a konkáv stock hiányzó régiójába vagy margin/usable régión kívülre kerülne, az nem tekinthető valid layoutnak.

## Current repo observations

A csomag a friss repo snapshot valós kódja alapján készült:

- `rust/vrs_solver/src/sheet.rs`
  - `SheetShape` már tartalmaz `has_irregular_outer: bool`, `area: f64`, `_outer_poly: SPolygon` és `hole_polys` mezőket;
  - `rect_inside_sheet_shape()` már nem csak bbox prechecket futtat: irregular outer esetén corner containment + edge crossing check történik;
  - container hole exclusion továbbra is jelen van, de Phase 1 adapter szinten unsupported.
- `rust/vrs_solver/src/adapter.rs`
  - Phase 1 profile: part holes, stock holes és `margin_mm > 0` explicit unsupported;
  - `JaguaAdapter::check_rect_in_sheet()` jelenleg a `rect_inside_sheet_shape()` helperre épül.
- `rust/vrs_solver/src/optimizer/repair.rs`
  - `find_violations()` boundary/sheet hibának jelöli az invalid `sheet_index` és `rect_inside_sheet_shape()` fail eseteket;
  - repair útvonal tehát már használja az aktuális boundary helper logikát.
- `rust/vrs_solver/src/optimizer/score.rs`
  - `ScoreModel` boundary penalty-t számol a repair `find_violations()` alapján;
  - validity penalty dominálja az optimalizációs pontszámot.
- `rust/vrs_solver/src/optimizer/mod.rs`
  - nincs még `boundary` modul;
  - a task-bontás fő outputként `rust/vrs_solver/src/optimizer/boundary.rs` fájlt vár, ezért JG-17-ben ezt létre kell hozni és `mod.rs`-be be kell kötni.
- `vrs_nesting/nesting/instances.py`
  - Python exact validator `outer_points` alapján Shapely stock polygont épít;
  - `sheet_poly.covers(placement_poly)` rejectálja a stock polygonon kívüli vagy hole-ba eső placementet;
  - `margin_mm > 0` esetén `buffer(-margin_mm)` usable polygon ellenőrzést végez.
- `vrs_nesting/runner/vrs_solver_runner.py`
  - invalid layout esetén `validation_status=fail` és runner error;
  - unsupported solver output esetén `validation_status=skipped_unsupported`, mert az nem layout response.
- `docs/solver_io_contract.md`
  - dokumentálja a Phase 1 outer-only capability policy-t;
  - dokumentálja, hogy `margin_mm > 0` Rust runtime alatt Phase 1-ben unsupported.

## DISCOVERED_MISMATCH / implementation note

```text
task breakdown says: rust/vrs_solver/src/optimizer/boundary.rs is a main implementation output
current repo says: rust/vrs_solver/src/optimizer/boundary.rs does not exist yet
current boundary logic lives in: rust/vrs_solver/src/sheet.rs::rect_inside_sheet_shape and repair.rs::find_violations
proposed resolution: create optimizer/boundary.rs as a VRS-owned boundary validation façade/policy layer, wire it from optimizer/mod.rs, and make construction/repair/score use it or delegate through it without changing SolverOutput v1
```

JG-17 nem írhatja felül vakon a JG-16 logikát. Ha az új `boundary.rs` modul csak biztonságosan tudja becsomagolni a meglévő helper logikát, az elfogadható. Ha a task során kiderül, hogy a `SPolygon.collides_with(point)` boundary-touch viselkedése nem elég egyértelmű, a policy-t dokumentálni kell, és safe-side irányba kell dönteni.

## Exact scope

JG-17 implementációs scope:

1. Boundary validation policy dokumentálása és kódbeli központosítása.
2. Új `rust/vrs_solver/src/optimizer/boundary.rs` modul létrehozása, ha a valós kód alapján ez a repo-konform út.
3. Boundary-touch policy explicit rögzítése:
   - rectangular stock edge touch elfogadható, ha nem lép túl a bboxon;
   - irregular stocknál a policy legyen dokumentált és safe-side;
   - ha a jagua primitive boundary semantics nem bizonyítható pontosan, a reportban rögzíteni kell.
4. Positive fixture: item teljesen sheeten belül → PASS.
5. Negative fixture: item a konkáv L-shape notch régiójába lóg vagy teljesen ott van → FAIL.
6. Margin-zóna policy:
   - `margin_mm > 0` Phase 1 Rust runtime alatt továbbra is `UNSUPPORTED_MARGIN_MM_RUNTIME`, vagy ha a task biztonságosan runtime margin validationt vezet be, azt dokumentálni és exact validatorral bizonyítani kell;
   - silent margin ignore tilos.
7. Existing construction/repair/score boundary detection összehangolása az új façade/policy réteggel.
8. Python exact validator és runner invalid-layout fail viselkedésének smoke bizonyítása.
9. Rectangular regresszió bizonyítása.
10. Checklist és report frissítése.

## Out of scope

- Nem cél JG-18 boundary-aware candidate generation.
- Nem cél új search/metaheuristic, SA, NFP provider vagy Sparrow átvétel.
- Nem cél part hole, stock/container hole vagy cavity-prepack támogatás.
- Nem cél runtime `margin_mm` shrink teljes implementációja, kivéve ha minimális és bizonyítottan biztonságos; silent ignore semmiképp nem engedhető.
- Nem cél `SolverOutput` v1 breaking változtatás.
- Nem cél a Python exact validator lazítása vagy kikapcsolása.

## Required implementation outputs

A JG task-bontás és a valós kód alapján legalább ezek érintettek vagy vizsgálandók:

```text
rust/vrs_solver/src/optimizer/boundary.rs
rust/vrs_solver/src/optimizer/mod.rs
rust/vrs_solver/src/sheet.rs
rust/vrs_solver/src/adapter.rs
rust/vrs_solver/src/optimizer/repair.rs
rust/vrs_solver/src/optimizer/score.rs
vrs_nesting/nesting/instances.py
vrs_nesting/runner/vrs_solver_runner.py
docs/solver_io_contract.md
tests/fixtures/egyedi_solver/jagua_irregular_boundary_validation.json
scripts/smoke_jagua_irregular_boundary_validation.py
codex/reports/egyedi_solver/jagua_optimizer_t17_irregular_boundary_validation.md
codex/codex_checklist/egyedi_solver/jagua_optimizer_t17_irregular_boundary_validation.md
canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md
```

Ha a valós audit alapján valamelyik fájl módosítása szükségtelen, a reportban rögzítsd. Ha további fájl kell, előbb frissítsd a YAML `outputs` listáját, mert az `AGENTS.md` szerint csak deklarált output módosítható.

## Detailed execution plan

1. Olvasd el a repo szabályokat és a JG tervdokumentációkat.
2. Ellenőrizd a JG-16 dependency gate-et.
3. Auditáld a jelenlegi Rust boundary útvonalat: `sheet.rs`, `adapter.rs`, `optimizer/repair.rs`, `optimizer/score.rs`, construction initializer és multisheet manager.
4. Auditáld a Python exact validator és runner fail semantics útvonalat.
5. Hozd létre vagy integráld az `optimizer/boundary.rs` modult úgy, hogy a boundary policy egy helyen auditálható legyen.
6. Kösd be a modult `optimizer/mod.rs`-be, és ahol szükséges, használd a construction/repair/score útvonalakon.
7. Dokumentáld a boundary-touch policy-t és a proxy vs exact boundary check viszonyát a `docs/solver_io_contract.md`-ben.
8. Készíts irregular boundary fixture-t pozitív és negatív példákkal.
9. Készíts smoke scriptet, amely legalább ezt bizonyítja:
   - inside-L placement PASS;
   - notch/outside-L placement FAIL;
   - invalid layout nem successful;
   - rectangular boundary regresszió nincs;
   - `margin_mm > 0` nem silent success;
   - exact validator fail átmegy runner meta `validation_status=fail` bizonyítékon.
10. Frissítsd a task-specifikus checklistet és a globális progress checklist JG-17 szakaszát.
11. Futtasd a célzott smoke-ot, Rust teszteket és a repo verify wrapperét.

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
- validation_status=fail is a hard failure.
```

```text
CHECKLIST_REQUIRED:
- Update the task-specific checklist entries in jagua_optimizer_task_progress_checklist.md.
- A task cannot be PASS unless the relevant checklist items are checked or explicitly marked BLOCKED/DEVIATION with evidence.
```

## Test expectations

Minimum targeted checks:

```bash
python3 scripts/smoke_jagua_irregular_boundary_validation.py
cargo test --manifest-path rust/vrs_solver/Cargo.toml
./scripts/verify.sh --report codex/reports/egyedi_solver/jagua_optimizer_t17_irregular_boundary_validation.md
```

Additional existing checks should be reused if relevant:

```bash
python3 scripts/smoke_jagua_irregular_sheet_provider.py
python3 scripts/smoke_jagua_exact_validation_bridge.py
```

Do not invent commands. If a command is unavailable or dependency-blocked, document the exact error and classify it as environment vs code vs task failure.

## Acceptance criteria

- [ ] JG-16 dependency gate PASS.
- [ ] Boundary validation policy dokumentálva.
- [ ] Boundary-touch policy dokumentálva.
- [ ] Proxy Rust boundary check és Python exact boundary check viszonya dokumentálva.
- [ ] `optimizer/boundary.rs` létrejött vagy a report indokolja, miért nem repo-konform.
- [ ] Existing construction/repair/score boundary útvonalak ugyanazt a policy-t használják vagy dokumentáltan ugyanoda delegálnak.
- [ ] Sheeten belüli irregular item PASS.
- [ ] Konkáv sheetből kilógó / notch régióba eső item FAIL.
- [ ] Margin-zóna input nem lehet silent success.
- [ ] Invalid boundary layout nem lehet successful.
- [ ] Rectangular boundary validation regresszió nincs.
- [ ] Validator smoke lefut irregular fixture-ön.
- [ ] Report tartalmaz negatív és pozitív példát.
- [ ] Repo verify PASS és log mentve, vagy blocker pontosan dokumentálva.
- [ ] Globális és task-specifikus checklist frissítve.
- [ ] Csak valódi PASS esetén szerepel: `JG-18_STATUS: READY`.

## Failure / rollback policy

- Ha a boundary façade bevezetése regressziót okoz rectangular stockon, állj meg `REVISE` vagy `FAIL` státusszal.
- Ha a jagua primitive boundary semantics miatt a boundary-touch policy nem bizonyítható, ne lazítsd a validációt; safe-side döntést vagy `REQUIRES_DECISION` blokkot írj.
- Ha margin kezelés bizonytalan, tartsd explicit unsupportedként; silent ignore tilos.
- Ha exact validator fail mégis successful státuszként megy át, `FAIL`, nem `PASS_WITH_NOTES`.
