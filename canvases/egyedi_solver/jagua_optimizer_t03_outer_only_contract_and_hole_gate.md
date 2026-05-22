# JG-03 — jagua_optimizer_t03_outer_only_contract_and_hole_gate

## Funkció

A JG-03 feladat célja a Phase 1 `jagua-rs` + saját optimizer irány **outer-only input contractjának** rögzítése és kikényszerítése.

A JG-02 után a `vrs_solver` moduláris, de még mindig rectangular row/cursor baseline. A kockázat most az, hogy a Python exact validator már ismeri a part `outer_points` / `holes_points` mezőit, miközben a Rust `Part` DTO jelenleg csak `id`, `width`, `height`, `quantity`, `allowed_rotations_deg` mezőket olvas. Serde alapértelmezés szerint az ismeretlen mezőket figyelmen kívül hagyja, ezért egy hole-os part csendben rectangular bbox-ként futhatna át. Ez Phase 1-ben tilos.

JG-03 ezért nem optimalizáló task, hanem **contract + gate task**:

- hole-os partokat tilos csendben rectangular itemmé degradálni;
- a Phase 1 jagua profil csak outer-only, rectangular/multi-sheet bemenetet fogadhat;
- unsupported input determinisztikus, auditálható státuszt vagy hibát adjon;
- a későbbi cavity-prepack miatt a hole metadata nem veszhet el;
- a meglévő rectangle-only smoke és legacy runner útvonal nem törhet.

## Source of truth

A feladat kizárólag repo-beli, ellenőrizhető forrásokra épülhet:

- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `canvases/jagua_rs_sajat_optimizer/plan/deep-research-report.md`
- `canvases/jagua_rs_sajat_optimizer/plan/jagua_rs_sajat_optimizer_fejlesztesi_terv.md`
- `canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_canvas_yaml_runner_task_bontas.md`
- `canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md`
- `canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_master_plan.md`
- `canvases/egyedi_solver/jagua_optimizer_task_index.md`
- `codex/prompts/egyedi_solver/jagua_optimizer_master_runner.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t02_solver_module_scaffold.md`
- `docs/solver_io_contract.md`
- `rust/vrs_solver/src/io.rs`
- `rust/vrs_solver/src/item.rs`
- `rust/vrs_solver/src/sheet.rs`
- `rust/vrs_solver/src/adapter.rs`
- `rust/vrs_solver/src/main.rs`
- `vrs_nesting/runner/vrs_solver_runner.py`
- `vrs_nesting/nesting/instances.py`
- `scripts/check.sh`

Ha bármely kötelező tervdokumentum vagy dependency report hiányzik, a task `BLOCKED`.

## Dependency státusz

**Közvetlen dependency:** JG-02.

JG-02 akkor tekinthető teljesültnek, ha a repo-beli report első sora `PASS`, és a report végén szerepel:

```text
JG-03_STATUS = READY
```

A JG-02 utáni valós modulhatárok:

- `rust/vrs_solver/src/main.rs` — CLI/orchestration, contract version check.
- `rust/vrs_solver/src/io.rs` — `SolverInput`, `SolverOutput`, `Placement`, `Unplaced`, `Metrics`.
- `rust/vrs_solver/src/item.rs` — `Part`, `Instance`, allowed rotation és instance expansion.
- `rust/vrs_solver/src/sheet.rs` — `Stock`, `SheetShape`, sheet expansion és stock-hole aware rectangle check.
- `rust/vrs_solver/src/adapter.rs` — `solve(input)` orchestration.
- `rust/vrs_solver/src/optimizer/mod.rs` — row/cursor baseline placement.

## Stratégiai háttér

A master plan szerint az első élesebb cél nem a hole/cavity nesting, hanem egy stabil, validálható rectangular multi-sheet alap. A hole/cavity kezelés későbbi Phase 3 rétegben jöhet vissza cavity-prepack + macro expansion formában. Emiatt Phase 1-ben a legsúlyosabb hiba nem az, ha a solver nem tud hole-os partot kezelni, hanem az, ha ezt nem jelzi, és a layout látszólag sikeres lesz, miközben a lyuk-szemantika elveszett.

A jagua/Sparrow audit alapján a jagua-rs erős collision backend, de a natív holed item kezelés nem bizonyított. Ezért a VRS oldali szerződésnek explicit módon kell különválasztania:

- Phase 1: outer-only, rectangular/multi-sheet, hole-os part unsupported.
- Phase 2: irregular/remnant vizsgálat kontrollált capability flaggel.
- Phase 3: cavity-prepack és hole metadata visszaállítás exact final validationnel.

## Valós kód audit megfigyelések

- `docs/solver_io_contract.md` már létezik, és v1 contractként dokumentálja a part `outer_points` / `holes_points` mezőket, de az output `status` jelenleg csak `ok` vagy `partial`.
- `vrs_nesting/nesting/instances.py` a Python validator oldalon már képes part `outer_points`, `prepared_outer_points`, `holes_points`, `prepared_holes_points` feldolgozására.
- `validate_multi_sheet_output()` jelenleg csak `status in {"ok", "partial"}` értéket fogad el.
- `rust/vrs_solver/src/item.rs` jelenlegi `Part` DTO-ja nem tartalmaz `outer_points`, `holes_points`, `prepared_outer_points`, `prepared_holes_points` mezőket.
- `rust/vrs_solver/src/sheet.rs` jelenleg támogat `Stock.holes_points` mezőt és hole-aware rectangle collision checket. Ez legacy smoke miatt ma működő útvonal, de Phase 1 jagua profil alatt külön policy döntést igényel.
- `vrs_nesting/runner/vrs_solver_runner.py` futás után mindig `_validate_contract_fields()` hívással validálja a solver outputot, ezért unsupported status vagy non-layout output bevezetésekor ezt a boundary-t is frissíteni kell.
- `scripts/check.sh` standard vrs_solver smoke-ja jelenleg stock hole-t tartalmaz. Emiatt JG-03 nem törheti meg a default legacy smoke-ot; az új strict outer-only gate-et profilhoz kell kötni, vagy a legacy/default útvonalat explicit kompatibilisen kell hagyni.

## DISCOVERED_MISMATCH / feloldás

A task bontás JG-03 output listája eredetileg csak `rust/vrs_solver/src/io.rs` és `rust/vrs_solver/src/main.rs` fájlokat említ Rust oldalon. JG-02 után azonban a valós kódban:

- a `Part` DTO az `item.rs` fájlban van;
- a solve orchestration az `adapter.rs` fájlban van;
- a stock hole policy a `sheet.rs` fájlt is érintheti.

Ezért a JG-03 YAML outputs listája tudatosan kiegészül ezekkel a valós fájlokkal. Ez nem scope-bővítés új optimizer irányba, hanem a JG-02 refaktor utáni valódi modulhatárok követése.

## Task scope

### Benne van

- `docs/solver_io_contract.md` frissítése a Phase 1 profile/capability/unsupported szabályokkal.
- `SolverInput` opcionális profile/capability mezőinek bevezetése, visszafelé kompatibilisen.
- Part hole mezők explicit DTO-szintű felvétele vagy raw JSON preflight alkalmazása, hogy ne lehessen a `holes_points` / `prepared_holes_points` mezőket csendben ignorálni.
- Hole-os part determinisztikus unsupported/error kezelése.
- Phase 1 jagua profil capability policy rögzítése: rectangular multi-sheet, item holes nélkül.
- A stock hole/remnant policy explicit elkülönítése: legacy/default smoke nem törhet, de Phase 1 jagua profil alatt ne legyen véletlenül irregular/remnant capability engedélyezve.
- Python runner és validator boundary frissítése, hogy az unsupported állapot auditálható legyen.
- Új smoke script: `scripts/smoke_jagua_optimizer_outer_only_contract.py`.
- Negatív fixture a smoke scriptben hole-os parttal.
- Pozitív fixture a smoke scriptben outer-only parttal.
- Rust build, célzott smoke, exact validation a valid layoutokra, repo verify.
- Task-specifikus és globális checklist frissítése.

### Nincs benne

- Nem szabad hole-os part nestinget implementálni.
- Nem szabad part-in-hole/cavity-prepack útvonalat implementálni.
- Nem szabad irregular/remnant nestinget implementálni.
- Nem szabad JaguaAdapter PoC-t vagy teljes jagua layout API bekötést írni; ez JG-04 scope.
- Nem szabad optimizer algoritmust, score modelt, candidate generationt, repair loopot vagy SA-t bevezetni.
- Nem szabad existing legacy rectangle smoke-ot törni.
- Nem szabad invalid layoutot sikeresnek jelölni.

## Kötelező globális invariánsok

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

## Javasolt contract design

1. **Visszafelé kompatibilitás:** a meglévő v1 default input, amely nem ad meg `solver_profile` mezőt, továbbra is fusson a jelenlegi smoke-okkal.
2. **Explicit Phase 1 profil:** vezess be opcionális `solver_profile` mezőt, például `jagua_optimizer_phase1_outer_only` értékkel. Ha más név jobb a repo konvenciói szerint, dokumentáld.
3. **Capabilities:** rögzítsd dokumentáltan, hogy a Phase 1 profil támogatja: rectangular/multi-sheet baseline futtatást; 0/90/180/270 rotációt; item holes: nem támogatott; part-in-hole: nem támogatott; irregular/remnant stock: nem támogatott ebben a fázisban.
4. **Unsupported handling:** hole-os part esetén determinisztikusan legyen jelölve: vagy `status: unsupported` + `unsupported_reason`, vagy kontrollált non-zero solver error stabil reason stringgel.
5. **No silent geometry loss:** ha inputban `holes_points` vagy `prepared_holes_points` szerepel partnál, azt a Rust vagy Python boundary észlelje.
6. **Exact validation:** csak `ok` / `partial` layout státuszra fusson exact layout validation; unsupported állapotot nem szabad valid layout PASS-ként könyvelni.

## Implementációs irány

### Rust oldal

Érintett fájlok:

- `rust/vrs_solver/src/io.rs`
- `rust/vrs_solver/src/item.rs`
- `rust/vrs_solver/src/adapter.rs`
- `rust/vrs_solver/src/sheet.rs`, ha a Phase 1 stock policy miatt szükséges
- `rust/vrs_solver/src/main.rs`, ha CLI/contract boundary módosítás szükséges

Minimum elvárás:

- Az input DTO legyen képes észlelni part hole mezőket.
- A gate a solver logika előtt fusson, ne placement után.
- Az unsupported reason stabil string legyen, például `UNSUPPORTED_PART_HOLES_PHASE1`.
- Ha stock holes/remnant szigorítás történik Phase 1 profil alatt, az ne törje a default `scripts/check.sh` legacy smoke-ot.
- `quantity`, `instance_id`, `part_id` coverage továbbra is validálható maradjon.

### Python runner / validator oldal

Érintett fájlok:

- `vrs_nesting/runner/vrs_solver_runner.py`
- `vrs_nesting/nesting/instances.py`

Minimum elvárás:

- A runner különítse el a successful layout validációt és az unsupported non-layout státuszt.
- Az unsupported státusz ne menjen át exact layout PASS-ként.
- A `runner_meta.json` vagy a reportolható output tartalmazza az unsupported okot, ha output-alapú megoldás készül.
- Ha non-zero error alapú megoldás készül, a stderr/run log tartalmazza a stabil reason stringet.

### Smoke script

Új fájl:

- `scripts/smoke_jagua_optimizer_outer_only_contract.py`

Minimum tesztesetek:

1. Positive outer-only fixture: rectangular stock + rectangular part + Phase 1 profile → solver fut, output `ok` vagy `partial`, exact validation PASS.
2. Negative holed part fixture: part `holes_points` vagy `prepared_holes_points` mezővel + Phase 1 profile → deterministic unsupported/error, no placement accepted as success.
3. Legacy regression: default profile / existing check-style rectangle path továbbra is kompatibilis, vagy a script explicit jelzi, hogy a standard repo gate fedezi.
4. No silent geometry loss assertion: a negatív fixture-ben a smoke ne csak exit code-ot nézzen, hanem ellenőrizze a reason stringet is.

## Tesztelési elvárások

Kötelező minimum:

```bash
cargo build --release --manifest-path rust/vrs_solver/Cargo.toml
cargo test --manifest-path rust/vrs_solver/Cargo.toml
python3 scripts/smoke_jagua_optimizer_outer_only_contract.py
./scripts/verify.sh --report codex/reports/egyedi_solver/jagua_optimizer_t03_outer_only_contract_and_hole_gate.md
```

Ha az unsupported output új státuszt vezet be, a tesztnek külön kell bizonyítania, hogy `ok`/`partial` layout esetén exact validator fut, `unsupported` esetén nincs layout sikernek könyvelve, és a reason string stabil.

## Report elvárások

A report útvonala:

```text
codex/reports/egyedi_solver/jagua_optimizer_t03_outer_only_contract_and_hole_gate.md
```

A report tartalmazza:

- dependency evidence: JG-02 PASS és JG-03 READY;
- contract változások összefoglalója;
- unsupported policy pontos leírása;
- Rust DTO/gate változások;
- Python runner/validator változások;
- smoke fixture-ek leírása;
- exact validation evidence;
- legacy regression evidence;
- repo verify blokk;
- checklist státusz;
- `JG-04_STATUS: READY` csak akkor, ha minden acceptance gate PASS.

## Checklist update kötelezettség

Frissítendő:

- `codex/codex_checklist/egyedi_solver/jagua_optimizer_t03_outer_only_contract_and_hole_gate.md`
- `canvases/jagua_rs_sajat_optimizer/plan/jagua_optimizer_task_progress_checklist.md`

A task nem PASS, ha a JG-03 szakasz checklist pontjai nincsenek kipipálva vagy explicit `BLOCKED/DEVIATION` megjegyzéssel ellátva.

## Acceptance criteria

- JG-02 dependency bizonyítottan PASS.
- Phase 1 capability policy dokumentált.
- `solver_profile`, `capabilities`, `unsupported_reason` contract kérdés kezelve és dokumentálva.
- Hole-os part input Phase 1 profil alatt determinisztikus unsupported/error státuszt ad.
- Hole kontúrok nem vesznek el csendben.
- Container hole/remnant kezelés nincs véletlenül Phase 1 jagua capability-ként engedélyezve.
- Python runner/validator oldali státuszkezelés ellenőrizve.
- Rectangle-only korábbi smoke nem törik.
- Unsupported státusz reportban és/vagy output metában megjelenik.
- Negatív hole-os fixture elkészült.
- Pozitív outer-only fixture elkészült.
- `cargo build`, `cargo test`, új smoke script és repo verify PASS.
- Exact final validation minden elfogadott layouton PASS.
- Checklist és report frissítve.
- JG-04 indíthatósága egyértelmű.

## Failure / rollback policy

- Ha az output `status` bővítése túl invazív vagy sok validator regressziót okoz, állj meg `REQUIRES_DECISION` státusszal, és dokumentáld az alternatívát: non-zero unsupported error reason stringgel.
- Ha a default legacy smoke törik, ne pipáld a taskot PASS-ra.
- Ha a hole gate csak Python oldalon működik, de a Rust binary standalone továbbra is silently drops hole fields, az nem elég: `REVISE` vagy `BLOCKED`.
- Ha exact validation nem fut az elfogadott layoutokra, az task failure.
- Rollback: a JG-03 által módosított contract/DTO/runner fájlok visszaállítása után a JG-02 report szerinti behavior baseline-nak újra PASS-nak kell lennie.

## Phase gate érintettség

JG-03 a Gate 1 egyik alapfeltétele. Gate 1 nem indítható tovább, ha a hole-os input nem explicit unsupported/error, vagy ha Phase 1-ben geometry loss lehetséges.
