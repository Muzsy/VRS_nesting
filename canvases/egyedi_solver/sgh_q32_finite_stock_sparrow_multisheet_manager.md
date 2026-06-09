# SGH-Q32 — Sparrow-native finite-stock heterogeneous multisheet manager

## 0. Kontextus

A Q31 után a native Sparrow core már erős egytáblás eredményt ad: a dense191 LV8-derived 191 darabos teszt egyetlen 1500×3000 sheeten, `seed=42`, `time_limit_s=600` mellett `status=ok`, `placed=191/191`, `final_pairs=0`, kb. 251 s alatt konvergált.

Ez azt bizonyítja, hogy a per-sheet Sparrow separation/search core használható. A production nestinghez viszont nem elég egy single-sheet core. A valódi workflow:

```text
Input: X darab alkatrész + Y darab rendelkezésre álló sheet/stock.
A sheetek lehetnek heterogén méretű téglalapok.
A solver időkereten belül a legjobb valid kiosztást keresi.
```

Nem elfogadható production modell a fix sheet-count próbálgatás. A helyes modell a **finite-stock pool optimizer**: a manager az összes rendelkezésre álló sheetből választ aktív subseteket, futtatja a Sparrow core-t, javítja a megoldást, minimalizálja a felhasznált sheet-területet, és időlimit végén a legjobb valid állapotot adja vissza.

Ebben a taskban csak **téglalap stockokat** kell támogatni. Alakos/remnant sheet és compression nem scope.

---

## 1. Valós repo-kiindulópontok

Kötelezően ezekre a meglévő fájlokra építs:

```text
rust/vrs_solver/src/io.rs
rust/vrs_solver/src/adapter.rs
rust/vrs_solver/src/sheet.rs
rust/vrs_solver/src/optimizer/score.rs
rust/vrs_solver/src/optimizer/sparrow/mod.rs
rust/vrs_solver/src/optimizer/sparrow/model.rs
rust/vrs_solver/src/optimizer/sparrow/optimizer.rs
rust/vrs_solver/src/optimizer/sparrow/lbf.rs
rust/vrs_solver/src/optimizer/sparrow/sample/search.rs
rust/vrs_solver/src/optimizer/sparrow/explore.rs
rust/vrs_solver/src/optimizer/sparrow/quantify/tracker.rs
rust/vrs_solver/src/optimizer/sparrow/profile.rs
rust/vrs_solver/src/optimizer/sparrow/diagnostics.rs
```

Jelenlegi fontos tények:

- `OptimizerPipelineKind` jelenleg tartalmaz `SparrowCde` értéket, de nincs production `SparrowCdeMultisheet` finite-stock pipeline.
- `SparrowProblem::from_solver_input(parts, sheets, rotation_context, extra_unplaced, config)` már expanded sheet listával tud dolgozni.
- Q31 után `SPInstance` tartalmaz cache-elt `Rc<CdeBaseShape>` mezőt. Ezt meg kell őrizni.
- A régi `rust/vrs_solver/src/optimizer/multisheet.rs` legacy/Phase1 manager. Ezt tilos production Sparrow multisheet megoldásként toldozni.
- A Python `vrs_nesting/sparrow/multi_sheet_wrapper.py` nem production Rust `sparrow_cde` út. Ezt tilos használni.

---

## 2. Cél

Implementálj új **Sparrow-native finite-stock multisheet manager** réteget a native Sparrow core fölé.

A manager:

1. megkapja az összes alkatrészt és az összes rendelkezésre álló sheetet;
2. heterogén téglalap stock poolból dolgozik;
3. kezdeti megoldást épít nagy/nehezen pakolható alkatrészekkel előre;
4. sheet-választásnál preferálja a kisebb/alkalmasabb sheeteket, ne nyisson feleslegesen nagy sheetet;
5. aktív sheet subseteken futtatja a native Sparrow core-t;
6. engedi a Sparrow core-t cross-sheet move / reinsert / repair / local improvement irányban dolgozni;
7. ha minden alkatrész validan bent van, időkereten belül tovább próbálhat jobb stockhasználatot keresni;
8. ha nem fér be minden és elfogyott a stock pool, `partial` / `stock_exhausted` eredményt ad explicit unplaced listával;
9. partial outputban csak valid, collision-free, boundary-safe placementeket adhat vissza.

---

## 3. Nem-cél

Nem része Q32-nek:

- alakos/remnant sheet támogatás;
- belső furatok átadása a Sparrow core-nak;
- compression bekötése;
- upstream Sparrow A/B benchmark;
- Q31 base-shape cache refaktor visszabontása;
- legacy `WorkingLayout` / `VrsCollisionTracker` production visszahozása;
- Python wrapperes multisheet megoldás;
- solver-szemantika lazítása azért, hogy a teszt PASS legyen.

---

## 4. Kötelező új pipeline

Adj hozzá új pipeline enum értéket:

```rust
OptimizerPipelineKind::SparrowCdeMultisheet
```

Serde név:

```json
"optimizer_pipeline": "sparrow_cde_multisheet"
```

Az adapterben legyen új ág:

```rust
OptimizerPipelineKind::SparrowCdeMultisheet => run_sparrow_finite_stock_multisheet_pipeline(...)
```

A meglévő `sparrow_cde` single/core út ne törjön el.

A `sparrow_cde_multisheet` pipeline:

- mindig CDE backendet használjon;
- ne fallbackeljen legacy multisheet managerre;
- ne használjon compressiont;
- teljes diagnostics outputot adjon;
- minden returned placementet validáljon final output előtt.

---

## 5. Kötelező új modul

Hozz létre új Rust modult:

```text
rust/vrs_solver/src/optimizer/sparrow/multisheet.rs
```

és exportáld:

```rust
pub mod multisheet;
```

itt:

```text
rust/vrs_solver/src/optimizer/sparrow/mod.rs
```

Javasolt fő típusok:

```rust
pub struct SparrowFiniteStockManager { ... }

pub struct FiniteStockRunConfig { ... }

pub struct FiniteStockRunResult { ... }

pub struct SheetSubsetCandidate { ... }

pub struct MultisheetIncumbent { ... }

pub enum FiniteStockStatus {
    Ok,
    PartialInsufficientStock,
    UnsupportedStockShape,
}
```

Nem kötelező pontosan ezekkel a nevekkel dolgozni, de a modul felelőssége legyen tiszta és auditálható.

---

## 6. Finite-stock logika

### 6.1 Teljes stock pool beolvasása

- `expand_sheets(input.stocks)` alapján minden sheet slot külön kezelendő.
- Minden expanded sheet kapjon stabil original sheet indexet.
- Ha a manager belső sheet subsetet/sorrendet használ, output előtt vissza kell mapelni az eredeti expanded sheet indexre.
- Heterogén stockoknál a `sheet_count_used = max(sheet_index)+1` logika hibás; unique used sheet indexekkel kell számolni.

### 6.2 Sheet kompatibilitás

Minden part esetén előre ellenőrizni kell:

- elfér-e legalább egy rendelkezésre álló stockon;
- elfér-e legalább egy engedélyezett rotációval;
- ha egy part soha nem fér el, explicit `PART_NEVER_FITS_STOCK` unplaced reason kell.

### 6.3 Kezdeti megoldás / aktív sheet subsetek

A manager képezzen candidate active-stock seteket.

Kötelező szempontok:

- nagy/nehezen pakolható partok előre;
- sheet választás méret, terület, kompatibilitás alapján;
- kisebb összterületű subsetek preferálása;
- nagy sheet csak akkor, ha szükséges;
- teljes stock pool fallback candidate mindig legyen;
- determinisztikus candidate ordering seed alapján.

Kis stockszámnál enumerálhatóak a subsetek. Nagy stockszámnál beam/greedy candidate lista is elfogadható, de dokumentálni kell.

### 6.4 Sparrow-core attempt

Minden selected sheet subsetre:

```text
selected sheet subset
-> SparrowProblem::from_solver_input(...)
-> SparrowOptimizer::solve(...)
-> final validation
-> optional sanitize/repair/ejection
-> incumbent scoring
```

A core-ban meg kell maradnia:

- CDE-backed strict trackernek;
- collision separationnek;
- cross-sheet search/move lehetőségnek;
- reinsert/repair/local-improvement jellegű próbáknak;
- Q31 base-shape cache-nek.

### 6.5 Full feasible solution ranking

Ha egy attempt:

```text
placed_count == total_instance_count
unplaced_count == 0
final_pairs == 0
boundary_violations == 0
```

akkor full feasible solution.

Ha marad idő, a manager próbáljon jobb stockhasználatot keresni:

- kisebb used sheet area;
- jobb used-sheet utilization;
- kevesebb used sheet count;
- jobb remnant/minőségi score.

Kötelező rangsor:

```text
1. full feasible előrébb van partialnál
2. full feasible esetén kisebb used_sheet_area jobb
3. magasabb utilization jobb
4. kevesebb used_sheet_count jobb
5. kisebb belső score jobb
6. determinisztikus tie-break
```

### 6.6 Partial / insufficient stock viselkedés

Ha minden elérhető sheet felhasználásával sem sikerül minden alkatrészt validan elhelyezni:

- `status = partial`;
- diagnostics jelölje: `STOCK_EXHAUSTED_PARTIAL` vagy `INSUFFICIENT_STOCK_CAPACITY`;
- legyen explicit unplaced lista;
- returned placements legyenek validak:

```text
final_pairs == 0
boundary_violations == 0
```

Nem megengedett collisionos partial output.

### 6.7 Partial sanitize / ejection-repair

Ha a Sparrow-core partial/infeasible layoutot ad:

1. építs collision graphot;
2. azonosíts collision komponenseket/klasztereket;
3. generálj több removal candidate-et:
   - highest-loss item;
   - largest-area item;
   - smallest-area item;
   - one-large-vs-multiple-small alternative;
   - boundary violator itemek;
4. minden candidate után validáld és/vagy próbálj reinsertiont más sheetre;
5. a legjobb valid partial incumbentet válaszd:
   - minél több placed instance;
   - minél nagyobb kept area;
   - minél jobb utilization;
   - collision/boundary hibamentesség kötelező.

Tilos primitív szabályt használni:

```text
“vedd ki az első ütköző itemet”
```

---

## 7. Diagnostics / output követelmények

Bővítsd `OptimizerDiagnosticsOutput`-ot optional mezőkkel legalább ezekkel:

```rust
sparrow_ms_active: Option<bool>
sparrow_ms_status: Option<String>
sparrow_ms_available_sheet_count: Option<usize>
sparrow_ms_used_sheet_count: Option<usize>
sparrow_ms_used_sheet_indices: Option<Vec<usize>>
sparrow_ms_used_sheet_area: Option<f64>
sparrow_ms_placed_part_area: Option<f64>
sparrow_ms_utilization_pct: Option<f64>
sparrow_ms_total_instances: Option<usize>
sparrow_ms_placed_instances: Option<usize>
sparrow_ms_unplaced_instances: Option<usize>
sparrow_ms_attempts: Option<usize>
sparrow_ms_candidate_subsets: Option<usize>
sparrow_ms_best_full_solution_found: Option<bool>
sparrow_ms_stock_exhausted: Option<bool>
sparrow_ms_final_pairs: Option<usize>
sparrow_ms_boundary_violations: Option<usize>
sparrow_ms_runtime_ms: Option<f64>
sparrow_ms_best_score: Option<f64>
```

Különösen fontos:

- `sparrow_ms_used_sheet_indices`;
- `sparrow_ms_used_sheet_area`;
- `sparrow_ms_utilization_pct`;
- `sparrow_ms_stock_exhausted`;
- `sparrow_ms_final_pairs`;
- `sparrow_ms_boundary_violations`.

---

## 8. Utilization és used sheet számítás

Heterogén/gapped sheeteknél tilos `max(sheet_index)+1` alapján számolni.

Kötelező:

```text
used_sheet_indices = unique placement.sheet_index értékek
used_sheet_count = used_sheet_indices.len()
used_sheet_area = sum(sheet.area for unique used sheets)
placed_part_area = sum(area of placed instances)
utilization_pct = 100 * placed_part_area / used_sheet_area
```

Ha egy sheet elérhető volt, de nincs rajta placement, nem számít használt sheetnek.

---

## 9. LV8 full276 fixture / input

A tesztekhez a teljes 276 darabos LV8 csomagot kell használni.

Forrás:

```text
samples/real_work_dxf/0014-01H/lv8jav_normalized/
```

A repo jelenlegi állapotában ez 12 normalizált DXF-et tartalmaz. A quantity a fájlnévből olvasandó (`_28db`, `_50db`, `_6db`, stb.), összesen 276.

Kötelező:

- 12 part type;
- total quantity = 276;
- normalized DXF-ekből outer contour;
- a fő Sparrow core ne kapjon `holes_points`-ot;
- ha `CUT_INNER` van, manifestben rögzítsd, de ebben a taskban ne add át holes-ként.

Hozz létre fixture-t:

```text
rust/vrs_solver/tests/fixtures/sgh_q32_finite_stock_multisheet/full_276_lv8_derived.json
```

és runner output inputokat:

```text
artifacts/benchmarks/sgh_q32/inputs/case_01_2x1500x3000.json
artifacts/benchmarks/sgh_q32/inputs/case_02_3x1500x3000.json
artifacts/benchmarks/sgh_q32/inputs/case_03_1x1500x3000_2x1000x2000.json
```

---

## 10. Kötelező LV8 full276 tesztfuttatások

Hozz létre runner scriptet:

```text
scripts/run_sgh_q32_finite_stock_multisheet_lv8.py
```

Minden case:

```json
{
  "optimizer_pipeline": "sparrow_cde_multisheet",
  "collision_backend": "cde",
  "seed": 42,
  "time_limit_s": 1200,
  "margin_mm": 0.0
}
```

A runner buildelje vagy ellenőrizze a release binárist:

```bash
cargo build --manifest-path rust/vrs_solver/Cargo.toml --release
```

### Case 01 — 2×1500×3000

Stock:

```json
[
  { "id": "S1500x3000", "quantity": 2, "width": 1500.0, "height": 3000.0 }
]
```

Hard acceptance:

```text
status == ok
placed_count == 276
unplaced_count == 0
sparrow_ms_final_pairs == 0
sparrow_ms_boundary_violations == 0
sparrow_ms_used_sheet_count <= 2
sparrow_ms_utilization_pct > 0
```

Ha nem teljesül, Q32 nem kész.

### Case 02 — 3×1500×3000

Stock:

```json
[
  { "id": "S1500x3000", "quantity": 3, "width": 1500.0, "height": 3000.0 }
]
```

Hard acceptance:

```text
status == ok
placed_count == 276
unplaced_count == 0
sparrow_ms_final_pairs == 0
sparrow_ms_boundary_violations == 0
sparrow_ms_used_sheet_count <= 2
sparrow_ms_used_sheet_area <= 9000000.0
sparrow_ms_utilization_pct > 0
```

Fontos: ha 3 sheet elérhető, de 2 sheet is elég, a manager nem használhat feleslegesen 3-at.

### Case 03 — 1×1500×3000 + 2×1000×2000

Stock:

```json
[
  { "id": "S1500x3000", "quantity": 1, "width": 1500.0, "height": 3000.0 },
  { "id": "S1000x2000", "quantity": 2, "width": 1000.0, "height": 2000.0 }
]
```

Acceptance kétféleképpen lehet PASS.

#### 03/A — minden elfér

```text
status == ok
placed_count == 276
unplaced_count == 0
sparrow_ms_final_pairs == 0
sparrow_ms_boundary_violations == 0
sparrow_ms_used_sheet_count <= 3
sparrow_ms_utilization_pct > 0
```

#### 03/B — nem fér el minden, de finite-stock partial korrekt

```text
status == partial
placed_count > 0
unplaced_count > 0
sparrow_ms_stock_exhausted == true
sparrow_ms_used_sheet_count == 3
sparrow_ms_final_pairs == 0
sparrow_ms_boundary_violations == 0
unplaced list nem üres
unsupported_reason vagy sparrow_ms_status jelzi: INSUFFICIENT_STOCK_CAPACITY / STOCK_EXHAUSTED_PARTIAL
```

Nem PASS:

```text
partial collisionos placementekkel
partial üres unplaced listával
ok final_pairs > 0 mellett
ok boundary violation mellett
legacy fallback
```

---

## 11. Artifact követelmények

A runner írja ki:

```text
artifacts/benchmarks/sgh_q32/finite_stock_multisheet_summary.json
artifacts/benchmarks/sgh_q32/finite_stock_multisheet_report.md
artifacts/benchmarks/sgh_q32/outputs/case_01_2x1500x3000_output.json
artifacts/benchmarks/sgh_q32/outputs/case_02_3x1500x3000_output.json
artifacts/benchmarks/sgh_q32/outputs/case_03_1x1500x3000_2x1000x2000_output.json
```

A summary JSON tartalmazza mindhárom case-t és a gate-ek bool eredményét.

---

## 12. Smoke validator

Hozz létre:

```text
scripts/smoke_sgh_q32_finite_stock_multisheet.py
```

A smoke ellenőrizze:

- `OptimizerPipelineKind::SparrowCdeMultisheet` létezik;
- `sparrow_cde_multisheet` deserializálható;
- `optimizer/sparrow/multisheet.rs` létezik;
- az új Sparrow multisheet modul nem importál `WorkingLayout`-ot;
- az új Sparrow multisheet modul nem importál `VrsCollisionTracker`-t;
- nincs Python `multi_sheet_wrapper.py` használat;
- nincs compression bekötés;
- Q31 base-shape cache megmaradt;
- runner létrehozta mindhárom output JSON-t;
- case01 gate PASS;
- case02 gate PASS;
- case03 vagy OK gate PASS, vagy korrekt partial gate PASS;
- summary JSON tartalmazza: total quantity 276, 12 part type, used sheet utilization, final pairs, boundary violations, unplaced count.

---

## 13. Kötelező Rust tesztek

Adj hozzá:

```text
rust/vrs_solver/tests/sparrow_finite_stock_multisheet.rs
```

Kötelező tesztek:

1. `sparrow_cde_multisheet` enum deserialize.
2. Heterogén stock expand + original sheet index mapping stabil.
3. Unique used sheet count nem `max(sheet_index)+1`.
4. Ha 3 azonos sheet érhető el, de 2 is elég synthetic problémához, a manager nem használ 3-at.
5. Partial sanitize: collisionos partial core resultből a manager nem ad collisionos placementet.
6. Stock exhaustion esetén explicit unplaced reason.
7. Q31 base-shape cache továbbra is aktív.

---

## 14. Kötelező report

Report path:

```text
codex/reports/egyedi_solver/sgh_q32_finite_stock_sparrow_multisheet_manager.md
```

A report Report Standard v2 szerint készüljön. Kötelező szekciók:

```text
# SGH-Q32 Report

## Scope
## Source files changed
## Existing code audit
## Finite-stock manager architecture
## Sheet subset / stock selection strategy
## Initial solution strategy
## Sparrow-core integration
## Cross-sheet move / repair / local improvement
## Partial sanitize / unplaced reporting
## Utilization calculation
## LV8 full276 inputs
## Case 01 results
## Case 02 results
## Case 03 results
## Acceptance gates
## Build/test commands
## Known remaining limitations
## Final verdict
```

A Final verdict csak akkor lehet PASS, ha:

```text
Case 01 PASS
Case 02 PASS
Case 03 PASS as OK or correct partial
cargo build PASS
cargo test PASS
smoke PASS
./scripts/check.sh PASS
./scripts/verify.sh PASS
```

Ha bármelyik parancs nem futott, nincs PASS.

Kötelező marker sorok a report végén:

```text
Q32_STATUS: PASS|FAIL
Q32_CASE01_STATUS: PASS|FAIL
Q32_CASE02_STATUS: PASS|FAIL
Q32_CASE03_STATUS: PASS|FAIL
Q32_CASE01_PLACED: <n>
Q32_CASE02_PLACED: <n>
Q32_CASE03_PLACED: <n>
Q32_CASE01_USED_SHEETS: <n>
Q32_CASE02_USED_SHEETS: <n>
Q32_CASE03_USED_SHEETS: <n>
Q32_CASE01_FINAL_PAIRS: <n>
Q32_CASE02_FINAL_PAIRS: <n>
Q32_CASE03_FINAL_PAIRS: <n>
Q32_CASE03_UNPLACED: <n>
Q32_FINAL_VERDICT: <short text>
```

---

## 15. Kötelező parancsok

Futtasd a végén:

```bash
cargo build --manifest-path rust/vrs_solver/Cargo.toml --release
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
cargo test --manifest-path rust/vrs_solver/Cargo.toml --test sparrow_finite_stock_multisheet
python3 scripts/run_sgh_q32_finite_stock_multisheet_lv8.py
python3 scripts/smoke_sgh_q32_finite_stock_multisheet.py
./scripts/check.sh
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q32_finite_stock_sparrow_multisheet_manager.md
```

Ha bármelyik hibázik, javítsd a kódot és futtasd újra. Ne lazíts acceptance gate-et.

---

## 16. Acceptance összefoglaló

Q32 csak akkor kész, ha:

```text
- van új Sparrow-native finite-stock multisheet manager;
- nem legacy multisheet manager;
- nem Python wrapper;
- nem compression;
- heterogén rectangle stock poolt kezel;
- candidate sheet subseteket próbál;
- kisebb/jobb sheet használatot preferál;
- case01 full276 2×1500×3000: OK;
- case02 full276 3×1500×3000: OK max 2 used sheettel;
- case03 mixed stock: OK vagy korrekt stock-exhausted partial;
- partial output soha nem collisionos;
- utilization számolva és reportolva;
- unplaced lista valós és explicit;
- Q31 base-shape cache megmarad;
- minden build/test/smoke/verify PASS.
```
