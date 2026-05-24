# JG-15 — `jagua_optimizer_t15_irregular_sheet_capability_spike`

## Task identity

- **Task id:** JG-15
- **Slug:** `jagua_optimizer_t15_irregular_sheet_capability_spike`
- **Phase:** Phase 2 / irregular spike
- **Goal:** Determine whether the current `jagua-rs` integration can support irregular/remnant sheet boundaries natively, without item holes and without container holes, and produce a concrete PASS/NO-GO decision for the Phase 2 implementation path.
- **Dependency:** JG-14 — `jagua_optimizer_t14_phase1_benchmark_matrix`
- **Primary report:** `codex/reports/egyedi_solver/jagua_optimizer_t15_irregular_sheet_capability_spike.md`
- **Decision report:** `docs/egyedi_solver/jagua_irregular_sheet_spike_decision.md`
- **Verify log:** `codex/reports/egyedi_solver/jagua_optimizer_t15_irregular_sheet_capability_spike.verify.log`

## Dependency gate

JG-15 csak akkor implementálható, ha ezek bizonyítottan teljesülnek:

- `codex/reports/egyedi_solver/jagua_optimizer_t14_phase1_benchmark_matrix.md` létezik;
- a JG-14 report első sora `PASS`;
- a JG-14 report tartalmazza: `PHASE1_GATE_DECISION: PASS`;
- a JG-14 report tartalmazza: `JG-15_STATUS: READY`;
- `scripts/bench_jagua_optimizer_phase1_rectangular.py` létezik;
- `codex/reports/egyedi_solver/jagua_optimizer_phase1_rectangular_benchmark.md` létezik.

Ha bármelyik feltétel nem teljesül, a JG-15 futás `BLOCKED`, és nem szabad spike kódot vagy döntési reportot sikeresként lezárni.

## DISCOVERED_MISMATCH

A tervdokumentációk között verzióeltérés van:

```text
old plan says: jagua_rs_sajat_optimizer_fejlesztesi_terv.md → Task JG-15 — Multi-child cavity-prepack V2
current task breakdown says: jagua_optimizer_canvas_yaml_runner_task_bontas.md → JG-15 — jagua_optimizer_t15_irregular_sheet_capability_spike
current checklist says: JG-15 — Jagua irregular/remnant sheet boundary képesség spike
current chain says: JG-14 report → JG-15_STATUS: READY after Phase 1 gate PASS
resolution: follow current task breakdown, checklist, master runner and JG-14 handoff; do not implement cavity-prepack in JG-15
```

## Strategic background

Phase 1 bizonyította a rectangular, outer-only, multi-sheet flow-t. Phase 2 célja annak eldöntése, hogy az optimizer hogyan kezeljen **alakos / remnant sheetet**. Ez kritikus ipari irány, mert a valós gyártásban sokszor nem teljes téglalap táblára, hanem levágott maradékra kell pakolni.

JG-15 nem végleges irregular provider. Ez egy capability spike: kódon és mérésen keresztül kell eldönteni, hogy:

1. a `jagua-rs` natívan tud-e sheet/container irregular boundaryt úgy, hogy a placement már eleve ne menjen ki az L-alakú / konkáv usable régióból; vagy
2. saját boundary validator szükséges, miközben a jagua továbbra is használható item-item collision / geometry backendként.

A terv nem bukik akkor sem, ha a natív boundary support nem elég. Ebben az esetben JG-15 döntési reportja `NO-GO_NATIVE_BOUNDARY` vagy repo-konform ekvivalens döntést ad, és JG-16 a saját boundary validator + irregular sheet provider irányba mehet tovább.

## Out of scope

- Nem cél production irregular sheet provider bevezetése; ez JG-16 feladata.
- Nem cél margin offset vagy usable polygon végleges kezelése; ez JG-16 feladata.
- Nem cél sheet elimination vagy Phase 1 benchmark tuning.
- Nem cél cavity extraction, cavity-prepack vagy hole-os itemek támogatása.
- Nem cél container hole / stock hole kezelés. JG-15 kizárólag hole nélküli irregular outer boundary spike.
- Nem cél teljes Sparrow vagy jagua optimizer újraírás.
- Nem cél exact validation bridge gyengítése vagy megkerülése.
- Nem cél `SolverOutput` v1 contract törése.

## Relevant current repo files

### Rust solver / geometry

- `rust/vrs_solver/src/sheet.rs` — `Stock` már fogad `outer_points` és `holes_points` mezőket; `SheetShape` tárolja az outer polygont `_outer_poly` néven, valamint `hole_polys` listát.
- `rust/vrs_solver/src/sheet.rs` — `rect_inside_sheet_shape()` jelenleg bbox boundaryt ellenőriz és hole collisiont vizsgál, de az irregular outer polygonhoz nem használja az `_outer_poly` mezőt. Ez a JG-15 egyik fő auditpontja.
- `rust/vrs_solver/src/geometry.rs` — VRS point/rect helper és `to_jag_polygon`, `jag_edge_from_points` adapter funkciók.
- `rust/vrs_solver/src/adapter.rs` — `JaguaAdapter::check_polygon_collision()` létezik; `JaguaAdapter::check_rect_in_sheet()` jelenleg `rect_inside_sheet_shape()`-ra delegál, tehát a bbox-only irregular boundary kockázat itt is releváns.
- `rust/vrs_solver/src/optimizer/initializer.rs` — construction placer rectangular sheet bbox alapján dolgozik.
- `rust/vrs_solver/src/optimizer/repair.rs` — violation check és repair loop; JG-15-ben csak audit/regression szinten érintett.
- `rust/vrs_solver/src/optimizer/multisheet.rs` — Phase 1 manager; JG-15-ben nem kell végleges irregular supportot integrálni.
- `rust/vrs_solver/src/io.rs` — `SolverInput`, `SolverOutput`, `Metrics` v1 contract.
- `rust/vrs_solver/Cargo.toml` — `jagua-rs = "0.6.4"` dependency.

### Python runner / exact validation

- `vrs_nesting/nesting/instances.py` — exact validator már képes `stock.outer_points` alapján Shapely polygonból sheetet építeni és `sheet_poly.covers(poly)` ellenőrzést futtatni. Ez jó oracle az L-alakú boundary violation felismeréshez.
- `vrs_nesting/runner/vrs_solver_runner.py` — canonical runner; `runner_meta.json` rögzíti a `validation_status` és `validation_error` mezőket.
- `scripts/bench_jagua_optimizer_phase1_rectangular.py` — JG-14 benchmark minta, de JG-15-nek külön spike script kell.
- `scripts/check.sh` és `scripts/verify.sh` — standard repo gate.

## Real code observations to verify during implementation

- `Stock.outer_points` Rust oldalon parse-olható és `SheetShape._outer_poly` létrejön, de a jelenlegi placement boundary helper nem használja az outer polygon collision/containmentet.
- `can_fit_any_stock()` jelenleg csak sheet bbox méretet használ, ezért irregular/remnant boundaryre nem elégséges.
- A Python exact validation bridge várhatóan már felismeri az L-shape notch-ba lógó placementet, mert Shapely `covers()` ellenőrzést használ.
- A current Phase 1 solver valószínűleg képes olyan placementet gyártani, amely bbox szerint belül van, de L-alakú sheet tényleges poligonjából kilóg. Ezt JG-15-ben kontrollált fixture-rel bizonyítani kell, nem feltételezni.
- A `jagua-rs` jelenlegi publikus használata a repóban `SPolygon`, `Edge`, `Point` és `CollidesWith` primitive-ekre korlátozódik; container/bin boundary API-ra nincs meglévő wrapper a repóban.

## Implementation target

Készíts capability spike-ot ezekkel a kötelező outputokkal:

```text
rust/vrs_solver/src/bin/jagua_irregular_sheet_spike.rs
tests/fixtures/egyedi_solver/jagua_irregular_l_shape.json
scripts/smoke_jagua_irregular_sheet_spike.py
docs/egyedi_solver/jagua_irregular_sheet_spike_decision.md
codex/reports/egyedi_solver/jagua_optimizer_t15_irregular_sheet_capability_spike.md
codex/codex_checklist/egyedi_solver/jagua_optimizer_t15_irregular_sheet_capability_spike.md
```

A spike legyen kicsi, determinisztikus, offline futtatható és auditálható. Nem production integrációt kell készíteni, hanem bizonyítékot és döntést.

## Required spike behaviour

### 1. L-shape / concave remnant fixture

Hozz létre egy egyszerű, hole nélküli, konkáv L-alakú stock fixture-t:

```text
tests/fixtures/egyedi_solver/jagua_irregular_l_shape.json
```

Minimum elvárás:

- `contract_version = v1`;
- `solver_profile = jagua_optimizer_phase1_outer_only` vagy dokumentált spike profile, ha ténylegesen szükséges;
- legalább egy `stock` `outer_points` mezővel, amely L-alakú / konkáv polygon;
- `holes_points` üres vagy hiányzik;
- legalább egy item, amely teljesen befér az L-shape egyik karjába;
- legalább egy kontrollhelyzet, amely bbox szerint belül lenne, de az L-shape hiányzó sarkába/notch-ába lógna;
- item hole és stock hole nem szerepelhet benne.

### 2. Rust spike bin

Hozd létre:

```text
rust/vrs_solver/src/bin/jagua_irregular_sheet_spike.rs
```

A bin célja nem production solver, hanem bizonyítékgyűjtés. Minimum:

- olvassa vagy beépített módon reprodukálja az L-shape boundary esetet;
- vizsgálja a jelenlegi `SheetShape` / `JaguaAdapter` boundary viselkedést;
- próbálja meg bizonyítani, hogy a `jagua-rs` aktuális, repo-ban használt API-jával elérhető-e natív irregular container boundary check;
- ha nincs ilyen natív API, ezt explicit módon jelezze, ne találjon ki nem létező jagua típust;
- adjon géppel olvasható kimenetet vagy jól grep-elhető sorokat a smoke script számára.

Elfogadható döntési kimeneti mezők / sorok:

```text
NATIVE_BOUNDARY_SUPPORT: YES | NO | UNKNOWN
OWN_BOUNDARY_VALIDATOR_REQUIRED: YES | NO
L_SHAPE_BOUNDARY_VIOLATION_DETECTED: YES | NO
CURRENT_BBOX_ONLY_RISK_DETECTED: YES | NO
DECISION: NATIVE_JAGUA_BOUNDARY | OWN_BOUNDARY_VALIDATOR_PLUS_JAGUA_COLLISION | REVISE
```

### 3. Python smoke script

Hozd létre:

```text
scripts/smoke_jagua_irregular_sheet_spike.py
```

A smoke script minimum ellenőrzései:

- fixture létezik és JSON-ként parse-olható;
- fixture hole nélküli;
- fixture tartalmaz `outer_points` L-shape / konkáv stockot;
- Rust spike bin buildel és fut;
- a spike kimenete tartalmaz konkrét döntési sorokat;
- boundary violation felismerhető;
- item-item collision regresszió nincs elrontva;
- exact validation bridge felismeri a tudatosan invalid L-shape boundary violationt;
- nincs item hole vagy container hole bekeverve;
- döntési report létrejött vagy frissült.

### 4. Decision report

Hozd létre:

```text
docs/egyedi_solver/jagua_irregular_sheet_spike_decision.md
```

A report zárjon konkrét döntéssel:

```text
JG-15_DECISION: NATIVE_JAGUA_BOUNDARY | OWN_BOUNDARY_VALIDATOR_PLUS_JAGUA_COLLISION | REVISE | STOP
```

Minimum tartalom:

- mit vizsgált a spike;
- pontos fixture leírás;
- mit tudott a current repo boundary model;
- mit tudott vagy nem tudott bizonyítottan a `jagua-rs` API;
- exact validation evidence;
- performance / complexity risk röviden;
- JG-16 irány:
  - ha native support bizonyított: native jagua irregular boundary provider irány;
  - ha nem bizonyított: saját boundary validator + jagua item-item collision irány;
  - ha bizonytalan: `REVISE`, további auditpontokkal.

Ha a döntés nem `STOP`, a JG-15 task report jelölheti:

```text
JG-16_STATUS: READY
```

## Required implementation steps

1. Ellenőrizd a JG-14 dependency gate-et.
2. Olvasd el a repo szabályokat és JG tervdokumentumokat.
3. Auditáld a valós Rust és Python boundary/validation kódot.
4. Dokumentáld a tervverzió-eltérést (`DISCOVERED_MISMATCH`).
5. Készítsd el az L-shape fixture-t.
6. Készítsd el a Rust spike bin-t.
7. Készítsd el a Python smoke scriptet.
8. Futtasd a spike-ot és rögzítsd a döntési kimenetet.
9. Futtasd az exact validation bridge kontrolltesztet.
10. Készítsd el a döntési reportot.
11. Futtasd a task-specifikus ellenőrzéseket és a repo gate-et.
12. Frissítsd a task-specifikus checklistet és a globális progress checklist JG-15 szakaszát.
13. Frissítsd a JG-15 implementation reportot evidence-szel.

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
- JG-15 is hole-free irregular outer boundary only; any hole-bearing fixture must be rejected or marked out of scope.
```

```text
EXACT_VALIDATION_REQUIRED:
- Boundary-violating L-shape placements must be detected by exact validation.
- Invalid layout cannot be accepted as success.
- The spike decision cannot be PASS if boundary violation is not detected.
```

```text
CHECKLIST_REQUIRED:
- Update the task-specific checklist entries in jagua_optimizer_task_progress_checklist.md.
- A task cannot be PASS unless the relevant checklist items are checked or explicitly marked BLOCKED/DEVIATION with evidence.
```

## Testing expectations

Futtasd, ha elérhető:

```bash
cargo build --manifest-path rust/vrs_solver/Cargo.toml --bin jagua_irregular_sheet_spike
cargo run --manifest-path rust/vrs_solver/Cargo.toml --bin jagua_irregular_sheet_spike
python3 scripts/smoke_jagua_irregular_sheet_spike.py
python3 scripts/bench_jagua_optimizer_phase1_rectangular.py
python3 scripts/smoke_jagua_exact_validation_bridge.py
cargo test --manifest-path rust/vrs_solver/Cargo.toml
./scripts/verify.sh --report codex/reports/egyedi_solver/jagua_optimizer_t15_irregular_sheet_capability_spike.md
```

Ha valamelyik parancs nem értelmezhető a valós repo alapján, ne találj ki helyettesítést; dokumentáld `REQUIRES_DECISION` vagy `BLOCKED` státusszal.

## Acceptance criteria

- JG-14 dependency gate PASS.
- L-shape / concave remnant fixture elkészült és hole-free.
- Rust spike bin elkészült és fut.
- Boundary violation felismerése bizonyított.
- Item-item collision regresszió nem romlott.
- Jagua native boundary support vagy saját boundary validator út konkrét döntéssel dokumentált.
- Döntési report elkészült `JG-15_DECISION: ...` sorral.
- JG-16 indíthatósága egyértelműen jelölve van.
- Task-specific és globális checklist frissítve.
- Repo verify PASS, vagy környezeti/blocker hiba pontosan dokumentálva.

## Failure / rollback policy

- Ha JG-14 gate nem PASS, állj meg `BLOCKED` státusszal.
- Ha a fixture hole-t tartalmaz, ne használd JG-15 PASS bizonyítékként.
- Ha a spike nem tudja bizonyítani a boundary violation felismerését, a döntés nem lehet PASS.
- Ha native jagua boundary support nem bizonyítható, ez nem hiba: döntés legyen saját boundary validator + jagua collision út, vagy `REVISE`, ha még nincs elég bizonyíték.
- A production solver pathot csak spikehoz szükséges minimális módon érintsd; ne vezess be JG-16-os provider implementációt.
