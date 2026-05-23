# JG-05 — jagua_optimizer_t05_rectangular_sheet_provider_and_fixtures

## Funkció

A JG-05 feladat célja a Phase 1 `jagua-rs` + saját optimizer munkalánc **rectangular sheet provider** rétegének és a hozzá tartozó determinisztikus outer-only fixture packnak az előkészítése.

Ez még nem teljes optimizer-fejlesztés. A JG-05 feladata, hogy a JG-03 outer-only contract és a JG-04 JaguaAdapter PoC után legyen egy stabil, auditálható alap a rectangular multi-sheet futásokhoz:

- a stock `quantity` determinisztikusan expandált sheet-listává alakuljon;
- a `sheet_index` mapping stabil és dokumentált legyen;
- a margin/gap alapmezők a fixture-ökben megjelenjenek;
- a smoke és small/medium fixture-ök outer-only szerződés szerint validak legyenek;
- az invalid fixture vagy invalid output ne mehessen át PASS-ként;
- minden elfogadott layout exact validatorral bizonyított legyen.

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
- `codex/reports/egyedi_solver/jagua_optimizer_t03_outer_only_contract_and_hole_gate.md`
- `codex/reports/egyedi_solver/jagua_optimizer_t04_jagua_adapter_contract_poc.md` — kötelező dependency, ha még hiányzik, a task `BLOCKED`
- `docs/solver_io_contract.md`
- `rust/vrs_solver/src/io.rs`
- `rust/vrs_solver/src/sheet.rs`
- `rust/vrs_solver/src/item.rs`
- `rust/vrs_solver/src/adapter.rs`
- `rust/vrs_solver/src/optimizer/mod.rs`
- `rust/vrs_solver/src/main.rs`
- `vrs_nesting/runner/vrs_solver_runner.py`
- `vrs_nesting/nesting/instances.py`
- `scripts/validate_nesting_solution.py`
- `scripts/check.sh`

Ha bármely kötelező tervdokumentum vagy dependency report hiányzik, a task `BLOCKED`. A jelen csomag generálásakor a friss snapshotban JG-03 PASS volt, de a JG-04 report nem volt jelen; ezért a runner külön preflight gate-et tartalmaz.

## Dependency státusz

**Közvetlen dependency:** JG-03 és JG-04.

JG-05 csak akkor indítható tényleges implementációra, ha:

1. `codex/reports/egyedi_solver/jagua_optimizer_t03_outer_only_contract_and_hole_gate.md` első sora `PASS`;
2. a JG-03 report tartalmazza: `JG-04_STATUS: READY`;
3. `codex/reports/egyedi_solver/jagua_optimizer_t04_jagua_adapter_contract_poc.md` létezik és első sora `PASS`;
4. a JG-04 report tartalmazza: `JG-05_STATUS: READY` vagy ezzel egyenértékű, egyértelmű next-task readiness jelzést;
5. a JG-04 során létrejött adapter contract / smoke eredmények nem tiltják a rectangular provider továbblépést.

Ha ezek közül bármi hiányzik, a JG-05 runner nem implementálhat, hanem `BLOCKED` reportot kell írnia.

## Stratégiai háttér

A master plan és a task bontás szerint a korai Phase 1 cél nem ipari irregular/cavity nesting, hanem egy stabil rectangular multi-sheet alap. Erre épülhet később az item geometry store, rotation cache, candidate generation és placement scorer. A rectangular provider ezért kulcsfontosságú alapréteg:

- ezzel ellenőrizhető, hogy a solver nem csak egyetlen sheetet kezel;
- a `stock.quantity` nem veszhet el;
- a `sheet_index` értelmezése fix marad;
- a későbbi optimizer lépések ugyanarra a bővített sheet-listára hivatkozhatnak;
- a fixture pack regressziós alapot ad a JG-06+ taskokhoz.

A feladat nem a density maximalizálásáról szól. A siker itt a contract-stabilitás, determinisztikus sheet expansion és validatorral bizonyított valid layout.

## Valós kód audit megfigyelések

A friss repo snapshot alapján:

- `docs/solver_io_contract.md` már explicit dokumentálja a `sheet_index` semantics részt: a `stocks` sorrendben, quantity szerint expandálódik, 0-alapú indexszel.
- `rust/vrs_solver/src/sheet.rs` már tartalmaz `Stock`, `SheetShape`, `stock_to_shape()`, `expand_sheets()` és `rect_inside_sheet_shape()` függvényeket.
- A meglévő `expand_sheets()` sorrendben iterál a `stocks` elemein, és minden pozitív quantity után ugyanannyi `SheetShape` klónt pushol.
- `rust/vrs_solver/src/optimizer/mod.rs` a placement outputban a sheet-lista enumerációjából érkező `sheet_index` értéket írja.
- `rust/vrs_solver/src/adapter.rs` jelenleg az `expand_sheets()` eredményét használja és `sheet_count_used` értékét a max placement sheet index + 1 alapján számolja.
- `scripts/check.sh` már tartalmaz vrs_solver build + runner + validator smoke-ot, de a jelenlegi beágyazott fixture nem JG-05 task-specifikus rectangular fixture pack.
- `vrs_nesting/runner/vrs_solver_runner.py` már tud run artifactokat és `runner_meta.json`-t írni; ez a JG-05 smoke scriptben újrahasználható.
- `scripts/validate_nesting_solution.py` és `vrs_nesting/nesting/instances.py` a valid layoutokat ellenőrző exact validation path alapja.
- `tests/fixtures/egyedi_solver/` jelenleg nem létező mappa a snapshotban; a JG-05 hozza létre.
- A snapshotban JG-04 report/artifact nem látható, ezért a tényleges JG-05 implementációt dependency preflighthez kell kötni.

## DISCOVERED_MISMATCH / feloldás

A task bontás szerint JG-05 függősége JG-03 és JG-04. A package-generáláskor használt friss snapshotban a JG-03 report PASS és `JG-04_STATUS: READY`, de a JG-04 csomag/report nem volt a repo-ban.

Feloldás a csomagban:

```text
REQUIRES_DEPENDENCY_GATE:
- JG-05 runner must check JG-04 PASS before implementation.
- If JG-04 report is missing or not PASS, write BLOCKED and do not modify production code.
```

Ez nem módosítja a JG-05 task tartalmát, csak megakadályozza a dependency nélküli implementációt.

## Task scope

### Benne van

- Rectangular sheet provider szerződésének dokumentálása a valós `sheet.rs` / solver IO contract alapján.
- `Stock.quantity` → expanded sheet lista determinisztikus ellenőrzése.
- Stabil `sheet_index` mapping tesztelése több stock és több quantity esetén.
- `tests/fixtures/egyedi_solver/` fixture mappa létrehozása, ha nem létezik.
- `tests/fixtures/egyedi_solver/jagua_rect_smoke.json` létrehozása kicsi, gyors, outer-only valid inputként.
- `tests/fixtures/egyedi_solver/jagua_rect_medium.json` létrehozása small realistic / medium regression inputként, több quantity-vel.
- Margin/gap mezők dokumentálása és fixture-szintű explicit szerepeltetése, ha a jelenlegi contract támogatja; ha nem támogatja, `DEVIATION` blokkban kell dokumentálni, hogy mely mezők contracton kívüliek.
- `scripts/smoke_jagua_rectangular_sheet_provider.py` létrehozása.
- Smoke scriptben: cargo build, runner futtatás fixture-ökre, exact validator, deterministic sheet index ellenőrzés, invalid output/fixture negative check.
- Report és task-specifikus + globális checklist frissítése bizonyíték alapján.
- Standard repo verify futtatása.

### Nincs benne

- Nem szabad teljes jagua layout API vagy optimizer loop bekötést írni.
- Nem szabad JG-06 ItemGeometryStore / rotation cache feladatot előre implementálni.
- Nem szabad candidate generationt, scorer-t, repair loopot, SA-t vagy density optimizationt bevezetni.
- Nem szabad irregular/remnant sheet nestinget implementálni.
- Nem szabad cavity-prepack, part-in-hole, hole-os item placement vagy macro expansion funkciót implementálni.
- Nem szabad invalid layoutot sikeresnek jelölni.
- Nem szabad a legacy/default `scripts/check.sh` vrs_solver smoke útvonalat törni.

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

## Javasolt provider contract

A JG-05 implementáló agent ne találjon ki új sheet modellt, hanem a jelenlegi contractot tegye explicit regressziósan ellenőrzötté.

Minimum contract:

1. `stocks` sorrendje megmarad.
2. Minden `stock.quantity > 0` pontosan annyi expanded sheet slotot ad.
3. `stock.quantity <= 0` policy dokumentált: vagy controlled error, vagy explicit skip. Ha a jelenlegi kód skipel, ezt dokumentálni kell, és nem szabad csendes contract-változtatást bevezetni bizonyíték nélkül.
4. Expanded sheet index 0-tól indul.
5. Több stock esetén index mapping: `S0#0`, `S0#1`, ..., `S1#0`, ...
6. Placement `sheet_index` mindig az expanded sheet listára hivatkozik.
7. Validatornak el kell kapnia az out-of-range vagy invalid sheet indexet.
8. Margin/gap mezők csak akkor legyenek runtime döntést befolyásoló mezők, ha a solver IO contract és valós kód ezt támogatja. Ha még nem támogatottak, a fixture-ben dokumentációs mezőként vagy `DEVIATION`-ként kell kezelni, nem szabad hamis működésként eladni.

## Implementációs irány

### Rust oldal

Érintett fájlok:

- `rust/vrs_solver/src/sheet.rs`
- szükség esetén csak minimálisan: `rust/vrs_solver/src/io.rs`, `rust/vrs_solver/src/adapter.rs`, `rust/vrs_solver/src/optimizer/mod.rs`

Minimum elvárás:

- A rectangular sheet expansion legyen explicit, tesztelhető függvény vagy meglévő `expand_sheets()` dokumentált regressziós alap.
- Legyen Rust unit test a stable expansion orderre, ha a jelenlegi struktúra ezt könnyen támogatja.
- Ne változzon a placement behavior rectangle-only valid fixture-ökön, hacsak a report nem dokumentálja bizonyítékkal.

### Fixture pack

Hozd létre:

```text
tests/fixtures/egyedi_solver/jagua_rect_smoke.json
tests/fixtures/egyedi_solver/jagua_rect_medium.json
```

Elvárások:

- `contract_version: "v1"`.
- `solver_profile: "jagua_optimizer_phase1_outer_only"`, ha JG-03/JG-04 után ez a profil az aktív Phase 1 contract.
- Legalább egy fixture használjon több stock quantity-t.
- Legalább egy fixture kényszerítsen második sheet használatot úgy, hogy a `sheet_index` mapping ellenőrizhető legyen.
- Partok outer-only jellegűek legyenek; hole-os part nem szerepelhet valid fixture-ben.
- `allowed_rotations_deg` explicit szerepeljen.
- Margin/gap igényt dokumentáld a fixture-ben csak akkor, ha a JSON contract ezt elfogadja. Ha nem, a reportban írd le, hogy a jelenlegi v1 contractban nincs aktív margin/gap runtime mező.

### Smoke script

Hozd létre:

```text
scripts/smoke_jagua_rectangular_sheet_provider.py
```

A script minimum ellenőrzései:

- buildelt vagy explicit `VRS_SOLVER_BIN` solverrel fut;
- a két valid fixture-t runner útvonalon futtatja;
- minden `ok`/`partial` outputot exact validatorral ellenőriz;
- ellenőrzi a `sheet_index` értékek determinisztikus és range-en belüli voltát;
- ellenőrzi, hogy a több quantity-s stockból képzett expanded sheet mapping elvárt;
- negatív ellenőrzést végez invalid sheet indexre vagy invalid outputra, és bizonyítja, hogy a validator elkapja;
- nem hagy hátra szükségtelen repo-szennyezést.

## Kötelező parancsok

```bash
cargo build --release --manifest-path rust/vrs_solver/Cargo.toml
cargo test --manifest-path rust/vrs_solver/Cargo.toml
python3 scripts/smoke_jagua_rectangular_sheet_provider.py
./scripts/verify.sh --report codex/reports/egyedi_solver/jagua_optimizer_t05_rectangular_sheet_provider_and_fixtures.md
```

Ha környezeti dependency miatt valami nem fut, dokumentáld pontosan, és ne adj tiszta PASS-t.

## Acceptance criteria

- JG-03 és JG-04 dependency PASS igazolt, különben `BLOCKED`.
- Rectangular sheet provider contract dokumentált.
- Stock quantity → expanded sheet lista determinisztikus.
- Stable `sheet_index` mapping ellenőrizve.
- Margin/gap mezők státusza tisztázott: supported, ignored-but-documented vagy blocked.
- `jagua_rect_smoke.json` valid outer-only fixture.
- `jagua_rect_medium.json` valid small/medium outer-only fixture több quantity-vel.
- A valid fixture-ök solver IO contract szerint validak.
- Exact validator PASS minden elfogadott layouton.
- Invalid output/fixture nem megy át PASS-ként.
- `cargo build`, `cargo test`, smoke script és repo verify eredménye dokumentált.
- Task-specifikus checklist és globális progress checklist frissítve.
- Report végén egyértelmű next readiness jelzés szerepel.

## Failure / rollback policy

- Ha JG-04 hiányzik vagy nem PASS, ne implementálj, írj `BLOCKED` reportot.
- Ha a fixture validálás fail, ne lazíts a validatoron.
- Ha a sheet index mapping nem determinisztikus, ne adj PASS-t.
- Ha margin/gap contract nem támogatott, ne implementálj félkész mezőt csendben; dokumentáld `DEVIATION`-ként vagy kérj döntést.
- Ha bármely változás töri a legacy `scripts/check.sh` gate-et, rollbackeld vagy jelöld `REVISE/FAIL` státusszal.

## Következő task

Sikeres JG-05 után a report végén szerepeljen:

```text
JG-06_STATUS: READY
```

Ha a dependency, fixture, exact validation vagy repo verify nem tiszta, akkor:

```text
JG-06_STATUS: NOT_READY
```
