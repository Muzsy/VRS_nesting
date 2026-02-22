# canvases/nesting_engine/nesting_engine_stock_pipeline.md

> **Mentés helye a repóban:** `canvases/nesting_engine/nesting_engine_stock_pipeline.md`  
> **TASK_SLUG:** `nesting_engine_stock_pipeline`  
> **Terület (AREA):** `nesting_engine`

---

# F1-5 — Deterministic Stock Offset (irregular bins + remnants)

## 🎯 Funkció

A “Truth Layer” determinisztikus geometriája jelenleg csak a part (alkatrész) inflációra teljes Rust oldalon.
A stock (tábla / usable area) számítás Pythonban még Shapely alapú (`vrs_nesting/geometry/offset.py` → `offset_stock_geometry`), ami:

- nem garantál tökéletes platformközi determinizmust,
- és akadály a jövőbeli irreguláris táblák (remnants) bevezetéséhez.

Ennek a feladatnak a célja:
- A stock usable area determinisztikus előállítása a Rust kernelben,
- a pipeline IO contract kiterjesztése `StockRequest` / `StockResponse`-szal,
- Python oldalon a Shapely stock offset **kivezetése**: a stock is a Rust pipeline-ból jön.

**Stock offset definíció (inverz a parthoz képest):**
- stock outer: **deflate** (befelé tolás)
- stock holes/defects: **inflate** (kifelé tolás)

A delta definíciója a pipeline-ban egységes:
- `delta_mm = margin_mm + kerf_mm * 0.5`  
ugyanazt alkalmazzuk stockra is (outer deflate, holes inflate), hogy a clearance-szabályok a “Truth Layer” mindkét oldalán konzisztensen érvényesüljenek.

## 🧠 Fejlesztési részletek

### Érintett meglévő fájlok (valós)
- `rust/nesting_engine/src/io/pipeline_io.rs`
  - Ma: `PipelineRequest { version, kerf_mm, margin_mm, parts: Vec<PartRequest> }`
  - Bővítés: `stocks: Vec<StockRequest>` (serde default üres listára)
  - Response bővítés: `stocks: Vec<StockResponse>` (serde default üres listára)

- `rust/nesting_engine/src/geometry/pipeline.rs`
  - Ma: `run_inflate_pipeline(req)` csak parts-ot dolgoz fel.
  - Bővítés: stock ág:
    - `inflate_outer(stock_polygon, -delta_mm)` használata:
      - negatív delta → outer befelé, holes kifelé (i_overlay outline viselkedése)
    - Self-intersect viselkedés: invalid nominal stock → `self_intersect` státusz (reject), nincs auto-fix.

- `docs/nesting_engine/io_contract_v2.md`
  - Itt jelenleg a solver IO v2 contract van.
  - Kiegészítés: egy külön “Pipeline preprocessing contract (pipeline_v1)” szekció,
    ahol a `PipelineRequest/Response` kiterjesztése és a `StockRequest/Response` mezők normatívan rögzítve vannak.

- `vrs_nesting/geometry/offset.py`
  - Ma: part → Rust bridge; stock → Shapely.
  - Cél: stock → Rust pipeline (ugyanazon subprocess JSON stdio hívással).
  - Elv: a Python oldal egy requestben küldi a parts+stocks adatot, és mindkettőt a Rust válaszból olvassa ki.

### IO contract döntések (pipeline_v1)
- `PipelineRequest` bővül:
  - `parts: [...]` (megmarad)
  - `stocks: [...]` (új, default `[]`)
- `StockRequest` mezők:
  - `id: string`
  - `outer_points_mm: [[f64,f64]]`
  - `holes_points_mm: [[[f64,f64]]]` (anyaghiba/lyuk kontúrok)
- `PipelineResponse` bővül:
  - `stocks: [...]` (új, default `[]`)
- `StockResponse` mezők (név konvenció):
  - `id: string`
  - `status: string` (`ok` / `self_intersect` / `error`)
  - `usable_outer_points_mm: [[f64,f64]]` (a deflate utáni outer)
  - `usable_holes_points_mm: [[[f64,f64]]]` (az inflate utáni holes)
  - `diagnostics: [Diagnostic]` (ugyanaz a Diagnostic struct, legalább SELF_INTERSECT / OFFSET_ERROR)

### Stock offset algoritmus (Rust)
- Nominal validation: `polygon_self_intersects(stock.outer)` → `self_intersect`
- Offset:
  - `inflate_outer(stock_polygon, -delta_mm)`  
    (negatív delta → outer deflate + holes inflate)
- Output:
  - mm-ben vissza, determinisztikus i64↔mm konverzióval.

### Python kivezetés
- `offset_stock_geometry` ne használjon Shapely-t.
- Ugyanaz a bináris és timeout policy mint a partnál.
- Ha a Rust válasz `self_intersect`: determinisztikus error (fail) – a stock usable area nem javítható csendben.

## 🧪 Tesztállapot

### DoD
- [x] `StockRequest` és `StockResponse` bevezetve a `rust/nesting_engine/src/io/pipeline_io.rs`-ben (serde default kompatibilitás megmarad)
- [x] stock_offset PASS: outer befelé, holes kifelé (negatív delta a `inflate_outer`-on)
- [x] `vrs_nesting/geometry/offset.py` már nem használ Shapely-t stock számításhoz
- [x] Determinizmus teszt: irreguláris (nem téglalap) stock + hole esetén a pipeline output bit-azonos ismételt futásra (egyező JSON)
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_stock_pipeline.md` PASS

## 🌍 Lokalizáció

Nincs UI. Hibaüzenetek stabil “code: message” formában, fejlesztői angol logokkal.

## 📎 Kapcsolódások

- `rust/nesting_engine/src/main.rs` (`inflate-parts` stdin/stdout JSON)
- `rust/nesting_engine/src/io/pipeline_io.rs` (Pipeline contract)
- `rust/nesting_engine/src/geometry/pipeline.rs` (inflate + stock inverse offset)
- `rust/nesting_engine/src/geometry/offset.rs` (`inflate_outer` + delta előjel)
- `vrs_nesting/geometry/offset.py` (Python bridge)
- `docs/nesting_engine/io_contract_v2.md` (contract dokumentálás)
