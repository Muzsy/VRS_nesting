# JG-16 — `jagua_optimizer_t16_irregular_sheet_provider_and_margin`

## Task identity

- **Task id:** JG-16
- **Slug:** `jagua_optimizer_t16_irregular_sheet_provider_and_margin`
- **Phase:** Phase 2 / irregular provider
- **Goal:** Irregular/remnant sheet provider, usable polygon és margin kezelés bevezetése hole nélkül, a meglévő Phase 1 rectangular pipeline megtörése nélkül.
- **Dependency:** JG-15 — `jagua_optimizer_t15_irregular_sheet_capability_spike`
- **Primary report:** `codex/reports/egyedi_solver/jagua_optimizer_t16_irregular_sheet_provider_and_margin.md`
- **Verify log:** `codex/reports/egyedi_solver/jagua_optimizer_t16_irregular_sheet_provider_and_margin.verify.log`

## Dependency gate

JG-16 csak akkor implementálható, ha ezek bizonyítottan teljesülnek:

- `codex/reports/egyedi_solver/jagua_optimizer_t15_irregular_sheet_capability_spike.md` létezik;
- a JG-15 report első sora `PASS` vagy repo-konform `PASS_WITH_NOTES`;
- a JG-15 report tartalmazza: `JG-16_STATUS: READY`;
- a JG-15 döntési report létezik: `docs/egyedi_solver/jagua_irregular_sheet_spike_decision.md`;
- a JG-15 döntési report konkrétan kimondja, melyik Phase 2 irányt kell követni:
  - natív jagua irregular boundary; vagy
  - saját boundary validator + jagua item-item collision;
- nincs JG-15 által jelölt `STOP` / `NO-GO` blokk, amely JG-16-ot tiltja.

Ha bármelyik feltétel nem teljesül, a JG-16 futás `BLOCKED`, és nem szabad provider/margin kódot sikeresként lezárni. A jelenlegi package-generálási snapshotban JG-15 artifact nem volt jelen, ezért a runner ezt kötelező preflightként kezeli.

## Strategic background

JG-14 lezárta a Phase 1 rectangular / outer-only benchmark gate-et. JG-15 feladata annak eldöntése, hogy irregular/remnant sheet boundary kezeléshez használható-e közvetlenül a `jagua-rs`, vagy a VRS oldalán kell saját boundary validatort tartani, miközben jagua továbbra is item-item collision komponensként szolgál.

JG-16 ennek a döntésnek az első production felé vivő provider-lépése. A cél nem még az összes boundary validáció végleges lezárása, hanem a sheet modell, input provider, usable region és margin policy kialakítása úgy, hogy JG-17 már erre tudja ráépíteni az irregular boundary validation gate-et.

## Current repo observations

A csomag a friss repo snapshot valós kódja alapján készült:

- `rust/vrs_solver/src/sheet.rs`
  - `Stock` már tartalmaz `outer_points: Option<Vec<PointInput>>` mezőt;
  - `Stock` már tartalmaz `holes_points: Option<Vec<Vec<PointInput>>>` mezőt;
  - `SheetShape` már tárol bbox adatokat és `_outer_poly: SPolygon` mezőt;
  - `stock_to_shape()` rectangle mode és shaped outer polygon mode között választ;
  - `rect_inside_sheet_shape()` jelenleg bbox + container-hole exclusion alapján dönt, nem bizonyítottan concave outer polygon containment alapján.
- `rust/vrs_solver/src/geometry.rs`
  - van `Point`, `PointInput`, `Rect`, `polygon_bbox()`, `to_jag_polygon()` és edge helper;
  - nincs külön usable polygon / margin shrink helper Rust oldalon.
- `rust/vrs_solver/src/adapter.rs`
  - `PROFILE_PHASE1 = "jagua_optimizer_phase1_outer_only"`;
  - Phase 1 továbbra is part-hole unsupported gate-et használ;
  - `JaguaAdapter::check_rect_in_sheet()` a `rect_inside_sheet_shape()` helperre épít.
- `docs/solver_io_contract.md`
  - `outer_points` már v1 stock mezőként dokumentált;
  - `margin_mm` és `spacing_mm` jelenleg JG-05 DEVIATION: Python validator-only, Rust solver runtime még nem alkalmazza.
- `vrs_nesting/nesting/instances.py`
  - a Python exact validator stock `outer_points` alapján polygon sheetet épít;
  - `margin_mm` esetén Shapely `buffer(-margin_mm)` usable polygon ellenőrzést végez;
  - a placementeket containment és spacing alapján validálja.
- `vrs_nesting/runner/vrs_solver_runner.py`
  - `validation_status=pass|fail|skipped_unsupported` meta mezőt ír;
  - invalid layout esetén runner errorral és `validation_status=fail` adattal zár.

## DISCOVERED_MISMATCH / important deviation

```text
current Rust contract: SolverInput does not parse margin_mm / spacing_mm fields
current Python validator: margin_mm / spacing_mm are parsed and enforced during validation
current docs: docs/solver_io_contract.md marks margin_mm/spacing_mm as JG-05 DEVIATION, validator-only
JG-16 task goal: irregular provider and margin handling
resolution required in implementation: either promote margin_mm into Rust SolverInput with explicit behaviour, or keep conservative provider-level fallback and document unsupported runtime margin clearly. Silent margin ignoring is not acceptable for PASS.
```

## Exact scope

JG-16 implementációs scope:

1. Sheet model kibővítése úgy, hogy explicit legyen:
   - original outer polygon;
   - usable polygon vagy documented usable boundary policy;
   - bbox metadata;
   - area / usable area metadata, ha a repo struktúrája megengedi.
2. Irregular/remnant sheet provider fogadása `Stock.outer_points` alapján.
3. Conservative margin policy kialakítása:
   - vagy Rust oldali explicit `margin_mm` input + usable polygon shrink;
   - vagy dokumentált unsupported/fallback, ha a valós kód alapján biztonságos shrink nem implementálható JG-16-ban.
4. L-alakú/remnant fixture létrehozása hole nélkül.
5. Too-narrow remnant unsupported / deterministic fail státusz kialakítása.
6. Rectangular provider regresszió bizonyítása.
7. Container holes tiltva maradnak.
8. Shape metadata riportolása: area, bbox, usable area, margin policy.

## Out of scope

- Nem cél part hole, item hole vagy container hole támogatás.
- Nem cél cavity-prepack, part-in-hole nesting vagy multi-child cavity logic.
- Nem cél JG-17 végleges irregular boundary validation gate teljes megvalósítása, de a provider nem adhat ki tudatosan invalid/silent-loss adatot.
- Nem cél új optimizer metaheuristic, SA, Sparrow átvétel vagy NFP provider.
- Nem cél a `SolverOutput` v1 breaking változtatása.
- Nem cél a Python exact validator lazítása vagy kikapcsolása.

## Required implementation outputs

A JG task-bontás alapján legalább ezek érintettek:

```text
rust/vrs_solver/src/sheet.rs
rust/vrs_solver/src/geometry.rs
docs/solver_io_contract.md
tests/fixtures/egyedi_solver/jagua_irregular_margin.json
scripts/smoke_jagua_irregular_sheet_provider.py
codex/reports/egyedi_solver/jagua_optimizer_t16_irregular_sheet_provider_and_margin.md
codex/codex_checklist/egyedi_solver/jagua_optimizer_t16_irregular_sheet_provider_and_margin.md
```

Ha a JG-15 decision report alapján további fájl szükséges, a YAML-t frissíteni kell az outputs szabály szerint, és a reportban rögzíteni kell.

## Detailed execution plan

1. Olvasd el a repo szabályokat és a JG tervdokumentációkat.
2. Ellenőrizd a JG-15 dependency gate-et.
3. Olvasd el a JG-15 döntési reportot, és abból állapítsd meg a Phase 2 boundary irányt.
4. Auditáld a jelenlegi Rust sheet/geometry/adapter/io modult és a Python runner/validator boundaryt.
5. Döntsd el, hogy JG-16-ban biztonságosan implementálható-e Rust oldali margin/usable polygon shrink.
6. Ha igen: implementáld explicit, determinisztikus módon.
7. Ha nem: a provider adjon `unsupported`/BLOCKED jellegű státuszt a marginos irregular inputokra, és dokumentáld, miért nem PASS a teljes margin runtime.
8. Készíts L-alakú/remnant fixture-t hole nélkül.
9. Készíts smoke scriptet, amely ellenőrzi:
   - rectangular regresszió;
   - L-shape/remnant input parse/provider;
   - margin utáni usable region metadata;
   - too-narrow remnant unsupported;
   - container holes tiltása;
   - runner/exact validator nem fogad invalid layoutot successként.
10. Frissítsd `docs/solver_io_contract.md`-t a valós JG-16 contracttal.
11. Frissítsd a task checklistet és a globális progress checklist JG-16 szakaszát.
12. Futtasd a célzott smoke-ot, Rust teszteket és a repo verify wrapperét.

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
- Container holes remain unsupported in JG-16 unless a later task explicitly enables them.
- If holes_points is present and non-empty for stock, return/document unsupported; do not ignore it.
```

```text
EXACT_VALIDATION_REQUIRED:
- Any accepted layout must pass the existing exact validation bridge.
- Invalid layout cannot be accepted as success.
- validation_status=fail is a hard failure, not a warning.
```

```text
CHECKLIST_REQUIRED:
- Update the task-specific checklist entries in jagua_optimizer_task_progress_checklist.md.
- A task cannot be PASS unless the relevant checklist items are checked or explicitly marked BLOCKED/DEVIATION with evidence.
```

## Acceptance criteria

- JG-15 dependency and decision report are verified.
- `SheetShape` / sheet provider has explicit outer polygon and usable polygon/margin policy.
- `Stock.outer_points` L-shape/remnant input is accepted only when hole-free and valid.
- Non-empty `Stock.holes_points` remains unsupported and is not silently ignored.
- Conservative margin behaviour is implemented or explicitly unsupported with evidence; margin must not be silently ignored.
- Too-narrow remnant returns deterministic unsupported/fail status.
- Rectangular stock provider regression is covered.
- Shape metadata report includes area, bbox, usable area/margin policy.
- Smoke fixture and script exist and run.
- `docs/solver_io_contract.md` documents the final JG-16 state.
- Exact validation gate remains mandatory for accepted layouts.
- Report first line is repo-konform status and includes `JG-17_STATUS: READY` only on real PASS.
