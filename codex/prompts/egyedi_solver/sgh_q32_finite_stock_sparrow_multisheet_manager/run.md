# Run prompt — SGH-Q32 finite-stock Sparrow multisheet manager

Olvasd el és hajtsd végre pontosan:

1. `AGENTS.md`
2. `docs/codex/yaml_schema.md`
3. `docs/codex/report_standard.md`
4. `canvases/egyedi_solver/sgh_q32_finite_stock_sparrow_multisheet_manager.md`
5. `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q32_finite_stock_sparrow_multisheet_manager.yaml`
6. `codex/codex_checklist/egyedi_solver/sgh_q32_finite_stock_sparrow_multisheet_manager.md`

## Feladat

Implementáld a production irányú **Sparrow-native finite-stock heterogeneous multisheet manager** réteget a jelenlegi native `sparrow_cde` core fölé.

Ez nem fix táblaszám-próbálgatás. A helyes modell:

```text
Input:
- X darab alkatrész
- Y darab rendelkezésre álló sheet/stock
- heterogén téglalap sheetek is lehetnek
- globális time_limit

Output:
- ha minden elfér validan: status == ok
- ha nem fér el minden és elfogyott a stock: status == partial + explicit unplaced lista
- partial output is collision-free és boundary-safe legyen
```

## Valós repo-kiindulópontok

A kód alapján jelenleg:

- `rust/vrs_solver/src/io.rs` tartalmazza az `OptimizerPipelineKind` enumot.
- `rust/vrs_solver/src/adapter.rs` route-olja a pipeline-okat.
- `rust/vrs_solver/src/sheet.rs` kezeli a `Stock` / `SheetShape` struktúrákat és expanded sheet logikát.
- `rust/vrs_solver/src/optimizer/sparrow/model.rs` tartalmazza a native `SparrowProblem` / `SPInstance` modelleket.
- Q31 után `SPInstance` cache-elt `Rc<CdeBaseShape>` mezőt használ. Ezt meg kell őrizni.
- `rust/vrs_solver/src/optimizer/multisheet.rs` legacy/Phase1 manager. Ne ezt toldozd production megoldásként.
- Python `multi_sheet_wrapper.py` nem használható production megoldásként.

## Kötelező implementáció

### 1. Új pipeline

Add hozzá:

```rust
OptimizerPipelineKind::SparrowCdeMultisheet
```

Serde név:

```json
"sparrow_cde_multisheet"
```

Adapter ág:

```rust
OptimizerPipelineKind::SparrowCdeMultisheet => run_sparrow_finite_stock_multisheet_pipeline(...)
```

### 2. Új Rust modul

Hozd létre:

```text
rust/vrs_solver/src/optimizer/sparrow/multisheet.rs
```

és exportáld:

```text
rust/vrs_solver/src/optimizer/sparrow/mod.rs
```

A modul felelőssége:

```text
- finite stock pool kezelése
- heterogeneous rectangle sheet subset candidate generation
- original expanded sheet index mapping
- native Sparrow attempt futtatása selected sheet subseten
- incumbent scoring
- used sheet utilization calculation
- partial sanitize/ejection-repair
- stock exhaustion unplaced reporting
```

### 3. Manager működés

A manager:

```text
1. Kapja meg az összes alkatrészt és sheetet.
2. Építsen kezdeti megoldást / candidate subseteket:
   - nagy/nehéz alkatrészek előre
   - sheet kompatibilitás
   - kisebb/jobb sheet preferencia
   - full stock fallback
3. Futtassa a Sparrow-core-t aktív sheeteken.
4. Ha minden alkatrész bent van és valid, próbáljon jobb stockhasználatot keresni, amíg van idő.
5. Ha nem fér be minden és elfogyott a stock, adjon valid partial outputot explicit unplaced listával.
6. Time limit végén adja vissza a legjobb valid incumbentet.
```

### 4. Partial output szabály

Tilos collisionos partial outputot visszaadni.

Ha a Sparrow core partial/infeasible layoutot ad:

```text
- collision graph / conflict clusters
- multiple removal candidates
- reinsert attempt ahol lehet
- valid partial incumbent kiválasztása
- eltávolított instance-ok explicit unplaced listába
```

Nem elég:

```text
“kiveszem az első ütköző itemet”
```

## Szigorú tiltások

Tilos:

- legacy `optimizer/multisheet.rs` production használata;
- `WorkingLayout` / `VrsCollisionTracker` visszahozása az új Sparrow multisheet modulba;
- Python `multi_sheet_wrapper.py` használata;
- compression bekötése;
- CDE / strict collision szemantika lazítása;
- Q31 base-shape cache visszarontása;
- test acceptance gate lazítása;
- `ok` státusz `final_pairs > 0` mellett;
- `partial` státusz collisionos placementekkel;
- üres vagy hamis unplaced lista stock exhaustion esetén.

## Kötelező LV8 full276 tesztek

A runner:

```text
scripts/run_sgh_q32_finite_stock_multisheet_lv8.py
```

használja a teljes 276 darabos LV8 csomagot a normalizált DXF-ekből:

```text
samples/real_work_dxf/0014-01H/lv8jav_normalized/
```

A fő core ne kapjon holes-t. CUT_INNER csak manifest/report információ.

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

### Case 01 — 2×1500×3000

Hard gate:

```text
status == ok
placed_count == 276
unplaced_count == 0
sparrow_ms_final_pairs == 0
sparrow_ms_boundary_violations == 0
sparrow_ms_used_sheet_count <= 2
sparrow_ms_utilization_pct > 0
```

### Case 02 — 3×1500×3000

Hard gate:

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

Ha 3 sheet elérhető, de 2 elég, nem használhat 3-at.

### Case 03 — 1×1500×3000 + 2×1000×2000

PASS lehet OK vagy korrekt stock-exhausted partial.

OK gate:

```text
status == ok
placed_count == 276
unplaced_count == 0
final_pairs == 0
boundary_violations == 0
```

Partial gate:

```text
status == partial
placed_count > 0
unplaced_count > 0
sparrow_ms_stock_exhausted == true
sparrow_ms_used_sheet_count == 3
sparrow_ms_final_pairs == 0
sparrow_ms_boundary_violations == 0
explicit unplaced list
reason: INSUFFICIENT_STOCK_CAPACITY / STOCK_EXHAUSTED_PARTIAL
```

## Kötelező verifikáció

Futtasd és zöldítsd:

```bash
cargo build --manifest-path rust/vrs_solver/Cargo.toml --release
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
cargo test --manifest-path rust/vrs_solver/Cargo.toml --test sparrow_finite_stock_multisheet
python3 scripts/run_sgh_q32_finite_stock_multisheet_lv8.py
python3 scripts/smoke_sgh_q32_finite_stock_multisheet.py
./scripts/check.sh
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q32_finite_stock_sparrow_multisheet_manager.md
```

Ha bármelyik hibázik, javítsd. Ne gyengítsd a gate-eket.

## Report

A report Report Standard v2 szerint készüljön:

```text
codex/reports/egyedi_solver/sgh_q32_finite_stock_sparrow_multisheet_manager.md
```

PASS csak akkor írható, ha:

```text
Case 01 PASS
Case 02 PASS
Case 03 PASS as OK or correct partial
cargo build PASS
cargo test PASS
runner PASS
smoke PASS
check PASS
verify PASS
```

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

## Végső minősítés

Ez nem mérési vagy részleges refaktor task. A kész állapot egy működő production irányú finite-stock multisheet manager, három full276 LV8 futással igazolva.
