# JG-04 — jagua_optimizer_t04_jagua_adapter_contract_poc

## Funkció

A JG-04 feladat célja egy vékony, VRS-oldali **JaguaAdapter contract PoC** létrehozása a `rust/vrs_solver` moduláris solverben.

Ez nem teljes optimizer-loop és nem layout API bekötés. A feladat célja az első bizonyított kapcsolat a `jagua-rs` collision/geometry backend és a saját optimizer boundary között:

- saját, VRS-owned adapter contract definiálása;
- VRS polygon/rect geometriák biztonságos jagua geometry konverziójának spike-ja;
- egyszerű item-item collision/overlap smoke;
- egyszerű item-sheet/boundary jellegű smoke, ha a jelenlegi `jagua-rs` API-val stabilan megoldható;
- hibakezelési kategóriák rögzítése: `unsupported`, `conversion_error`, `backend_error`;
- f64→f32 konverziós kockázat dokumentálása;
- annak bizonyítása, hogy a jagua-specifikus típusok nem szivárognak át az optimizer publikus modelljébe.

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
- `codex/reports/egyedi_solver/jagua_optimizer_t03_outer_only_contract_and_hole_gate.md`
- `docs/egyedi_solver/jagua_optimizer_source_audit.md`
- `docs/solver_io_contract.md`
- `rust/vrs_solver/Cargo.toml`
- `rust/vrs_solver/src/adapter.rs`
- `rust/vrs_solver/src/geometry.rs`
- `rust/vrs_solver/src/item.rs`
- `rust/vrs_solver/src/sheet.rs`
- `rust/vrs_solver/src/main.rs`
- `scripts/check.sh`

Ha bármely kötelező tervdokumentum vagy dependency report hiányzik, a task `BLOCKED`.

## Dependency státusz

**Közvetlen dependency:** JG-02 és JG-03.

A dependency akkor teljesült, ha:

- `codex/reports/egyedi_solver/jagua_optimizer_t02_solver_module_scaffold.md` első sora `PASS`;
- `codex/reports/egyedi_solver/jagua_optimizer_t03_outer_only_contract_and_hole_gate.md` első sora `PASS`;
- a JG-03 report végén szerepel: `JG-04_STATUS: READY`.

A friss snapshot alapján a JG-02 utáni valós modulhatárok:

- `rust/vrs_solver/src/main.rs` — CLI/orchestration.
- `rust/vrs_solver/src/io.rs` — `SolverInput`, `SolverOutput`, `Placement`, `Unplaced`, `Metrics` DTO-k.
- `rust/vrs_solver/src/item.rs` — `Part`, `Instance`, rotation helpers, `part_has_holes()`.
- `rust/vrs_solver/src/sheet.rs` — `Stock`, `SheetShape`, jagua-backed sheet/hole collision helper.
- `rust/vrs_solver/src/adapter.rs` — jelenleg a solver orchestration és JG-03 hole gate helye.
- `rust/vrs_solver/src/geometry.rs` — `Point`, `Rect`, `PointInput`, `to_jag_point()`, `to_jag_polygon()`, `jag_edge_from_points()`.
- `rust/vrs_solver/src/optimizer/mod.rs` — row/cursor baseline placement.

## Stratégiai háttér

A projektirány szerint a `jagua-rs` rövid távon nem önálló teljes solverként, hanem először collision/feasibility backendként kerül a saját optimizer mögé. A JG-04 ezért nem próbál sheet eliminációt, repair search-et, cavity-prepacket vagy irregular nestinget megvalósítani. A cél egy kicsi, mérhető adapter contract, amely később a rectangular baseline, majd a saját kereső/repair komponensek alá tehető.

## DISCOVERED_MISMATCH

A régebbi `canvases/jagua_rs_sajat_optimizer/plan/jagua_rs_sajat_optimizer_fejlesztesi_terv.md` a JG-04-et még így nevezi:

```text
Task JG-04 — Rectangular single-sheet baseline optimizer
```

Az aktuális, részletes task-bontásban és a master runnerben viszont a JG-04 hivatalos definíciója:

```text
JG-04 — jagua_optimizer_t04_jagua_adapter_contract_poc
Phase 1 / backend adapter
```

Feloldás: a JG-04 runner az aktuális `jagua_optimizer_canvas_yaml_runner_task_bontas.md`, a master runner és a JG-03 `JG-04_STATUS: READY` output alapján dolgozzon. A rectangular single-sheet baseline optimizer külön, későbbi vagy átnevezett taskként kezelendő, nem ennek a csomagnak a scope-ja.

## Valós kód audit megfigyelések

- `rust/vrs_solver/Cargo.toml` már tartalmazza: `jagua-rs = "0.6.4"`.
- `rust/vrs_solver/src/geometry.rs` már importál jagua típusokat: `SPolygon`, `Point`, `Edge`, és létezik f64→f32 konverzió `to_jag_point()` néven.
- `rust/vrs_solver/src/sheet.rs` már használja a `CollidesWith` traitet és jagua `SPolygon`-t stock hole collision ellenőrzésre.
- `rust/vrs_solver/src/adapter.rs` név alatt ma nem backend adapter contract van, hanem solver orchestration (`solve(input)`) és a JG-03 Phase 1 hole gate.
- `rust/vrs_solver/src/main.rs` modul deklarációi között nincs külön `jagua_adapter` modul és nincs `src/bin` könyvtár.
- A task-bontás explicit outputként kéri: `rust/vrs_solver/src/bin/jagua_adapter_smoke.rs` és `scripts/smoke_jagua_adapter_contract.py`.
- A JG-04 implementációnál különösen figyelni kell, hogy a jagua-specifikus típusok ne kerüljenek a publikus optimizer contractba; maradjanak a Rust belső adapter/geometry boundary mögött.

## Task scope

### Benne van

- Vékony VRS-owned adapter contract vagy struct/trait definiálása.
- Adapter error enum vagy stabil hibakategória kialakítása: `unsupported`, `conversion_error`, `backend_error`.
- VRS polygon/rect → jagua geometry conversion PoC.
- Item-item collision smoke valid/nem ütköző esettel.
- Item-item collision smoke invalid/overlap esettel.
- Item-sheet vagy boundary jellegű smoke, ha a jelenlegi jagua API stabilan támogatja.
- `rust/vrs_solver/src/bin/jagua_adapter_smoke.rs` létrehozása.
- `scripts/smoke_jagua_adapter_contract.py` létrehozása, amely buildeli/futtatja a Rust smoke binárist és ellenőrzi a kimenetet.
- `cargo build`, `cargo test`, smoke script, repo verify.
- Report és checklist frissítése.

### Nincs benne

- Nem szabad teljes jagua layout API-t vagy Sparrow-szerű optimizer-loopot bekötni.
- Nem szabad sheet eliminationt, repair loopot, simulated annealinget vagy új score modelt implementálni.
- Nem szabad cavity-prepack, part-in-hole vagy macro-part expansion logikát írni.
- Nem szabad hole-os part nestinget engedélyezni; JG-03 outer-only gate marad érvényben.
- Nem szabad a meglévő `solve(input)` rectangular baseline viselkedését megváltoztatni.
- Nem szabad invalid layoutot vagy csak „nem crash-el” típusú smoke-ot sikernek elfogadni.

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

A pontos Rust megoldást a futtató agentnek a valós `jagua-rs` 0.6.4 API alapján kell véglegesítenie, de a contract elve:

1. **Publikus VRS modell:** legyen saját adapter input/output/error típus, amely nem exportál `jagua_rs::*` típust.
2. **Belső conversion boundary:** jagua típusok csak `geometry.rs` vagy belső adapter modulban jelenjenek meg.
3. **POC műveletek:** minimum két rect/polygon ütközésvizsgálat: nem átfedő = no collision, átfedő = collision.
4. **Sheet/boundary smoke:** egy item legyen sheeten belül, egy item lépje túl a boundaryt, vagy ha ezt csak meglévő `rect_inside_sheet_shape()` helperrel lehet stabilan ellenőrizni, akkor ezt dokumentáltan használd.
5. **Hibakezelés:** conversion error legyen elkülönítve backend/runtime error-tól; unsupported branch csak dokumentált API-hiány esetén legyen.
6. **Precizitás:** f64 bemenetről f32 jagua pontra való konverzió legyen explicit és reportban dokumentált.

## Implementációs irány

### Rust oldal

Érintett fájlok:

- `rust/vrs_solver/src/adapter.rs`
- `rust/vrs_solver/src/geometry.rs`
- `rust/vrs_solver/src/bin/jagua_adapter_smoke.rs`
- szükség esetén `rust/vrs_solver/src/main.rs`, ha modul export/hozzáférés miatt minimálisan szükséges
- szükség esetén `rust/vrs_solver/src/lib.rs`, ha a bináris smoke tiszta hozzáféréséhez library crate kell — ezt csak valós build-igény esetén hozd létre, és dokumentáld

Minimum elvárás:

- A meglévő `solve(input)` publikus behavior ne változzon rectangle-only smokeokon.
- Ha `adapter.rs` túlterhelt név, ne töröld a meglévő orchestrationt; inkább belső `JaguaAdapter` structot/traitet adj hozzá vagy hozz létre kicsi új modult a YAML outputs bővítésének dokumentálásával.
- `jagua-rs` típusok maradjanak belső részletek.
- A smoke bináris determinisztikus outputot adjon, például JSON vagy stabil text summary formában.

### Python smoke

Hozd létre:

```text
scripts/smoke_jagua_adapter_contract.py
```

A script:

- építse vagy futtassa a `jagua_adapter_smoke` Rust binárist;
- ellenőrizze a valid/no-overlap és invalid/overlap esetet;
- ellenőrizze az item-sheet/boundary smoke eredményét, ha implementált;
- ellenőrizze, hogy a smoke outputban szerepeljen f32/f64 conversion note vagy API observation;
- exit code 0 csak akkor legyen, ha minden explicit assertion teljesült;
- ne hagyjon hátra fölösleges repo-szennyezést.

## Kötelező ellenőrzések

```bash
cargo build --release --manifest-path rust/vrs_solver/Cargo.toml
cargo test --manifest-path rust/vrs_solver/Cargo.toml
python3 scripts/smoke_jagua_adapter_contract.py
python3 scripts/smoke_jagua_optimizer_outer_only_contract.py
./scripts/verify.sh --report codex/reports/egyedi_solver/jagua_optimizer_t04_jagua_adapter_contract_poc.md
```

Ha valamelyik környezeti dependency miatt nem fut, dokumentáld pontosan, és ne adj tiszta PASS-t.

## Acceptance criteria

- Adapter trait/contract leírva saját publikus modellben.
- Jagua-specifikus típusok nem szivárognak át az optimizer publikus modelljébe.
- VRS polygon → jagua geometry konverzió első verziója elkészült vagy spike-olva.
- Egyszerű item-item collision smoke valid esetet felismer.
- Egyszerű item-item collision smoke invalid/overlap esetet felismer.
- Item-sheet / boundary jellegű smoke lefut, ha a jagua API támogatja.
- f32/f64 vagy unit konverziós kockázat dokumentálva.
- Adapter hibakezelés explicit: unsupported, conversion_error, backend_error.
- A POC nem köt be még teljes optimizer-loopot.
- Cargo build PASS.
- Report tartalmaz API-megfigyeléseket és ismert korlátokat.
- Repo verify PASS és log mentve.

## Failure / rollback policy

- Ha a jagua API a várt collision műveletet nem támogatja, ne erőltesd a teljes adaptert; jelöld `REQUIRES_DECISION` vagy `BLOCKED`, és reportold az API-hiányt.
- Ha a PoC miatt bármely meglévő solver smoke törik, rollbackeld a production behavior változást, és csak audit/report maradjon.
- Ha library crate létrehozása szükséges, de nagy refaktorral járna, állj meg `REQUIRES_DECISION` státusszal.
- Ha csak a smoke bináris buildje bukik, de a meglévő solver nem, akkor `REVISE`, nem PASS.

## Következő task kapcsolat

Sikeres JG-04 után a következő taskok indíthatósága:

```text
JG-05_STATUS: READY
JG-08_DEPENDENCY_JG04: READY
```

Csak akkor jelöld ezeket READY-nek, ha a JG-04 acceptance gate-ek bizonyítottan teljesültek.
