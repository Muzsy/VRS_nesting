# codex/prompts/nesting_engine/nesting_engine_stock_pipeline/run.md

Szerep: **VRS_nesting task runner (canvas+YAML+verify fegyelmezett végrehajtás)**

Feladat:
F1-5 lezárása: determinisztikus stock offset a Rust kernelben (irregular bins / remnants előkészítése).
- A pipeline IO contract bővül StockRequest/StockResponse-szal.
- A Rust pipeline a stock outer-t deflate-eli, a hole-okat inflate-eli (inverse offset).
- A Python offset_stock_geometry Shapely-je kivezetésre kerül, helyette Rust subprocess JSON stdio hívás lesz.
- Determinizmus teszt: irreguláris stock + hole bit-azonos output ismételt futásra.

Kötelező szabályok:
- Kövesd az AGENTS.md + codex szabályokat.
- Ne találgass: a meglévő repó fájlstruktúrája és konvenciói alapján dolgozz.
- Csak a YAML step `outputs` listájában szereplő fájlokat hozhatod létre/módosíthatod.
- A part infláció viselkedése nem változhat (regresszió tilos).
- A stock offset nem “auto-fix”: self-intersect -> reject + status/self_intersect.

Inputok:
- Canvas: `canvases/nesting_engine/nesting_engine_stock_pipeline.md`
- Goal YAML: `codex/goals/canvases/nesting_engine/fill_canvas_nesting_engine_stock_pipeline.yaml`

Végrehajtás:
1) Olvasd be a canvas + YAML tartalmát, és hajtsd végre a step-eket sorrendben.
2) Pipeline IO bővítés:
   - `rust/nesting_engine/src/io/pipeline_io.rs`: StockRequest/Response + PipelineRequest/Response `stocks` mező (serde default).
3) Rust pipeline:
   - `rust/nesting_engine/src/geometry/pipeline.rs`: a stock ág implementációja `inflate_outer(polygon, -delta_mm)`-mal.
   - Status/diagnosztika: ok / self_intersect / error.
4) Dokumentáció:
   - `docs/nesting_engine/io_contract_v2.md`: új szekció “Pipeline preprocessing contract (pipeline_v1)” stock mezőkkel.
5) Python kivezetés:
   - `vrs_nesting/geometry/offset.py`: `offset_stock_geometry` Rust pipeline-t hívjon; Shapely stock ne fusson defaultból.
6) Teszt:
   - Rust teszt irreguláris stockra (outer + hole), kétszeri futás byte-azonos JSON összehasonlítással + bbox irány ellenőrzéssel.
7) Checklist + report.
8) Verify:
   `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_stock_pipeline.md`
   és mentsd:
   `codex/reports/nesting_engine/nesting_engine_stock_pipeline.verify.log`

Kimenetek:
- `canvases/nesting_engine/nesting_engine_stock_pipeline.md`
- `rust/nesting_engine/src/io/pipeline_io.rs`
- `rust/nesting_engine/src/geometry/pipeline.rs`
- `docs/nesting_engine/io_contract_v2.md`
- `vrs_nesting/geometry/offset.py`
- `codex/codex_checklist/nesting_engine/nesting_engine_stock_pipeline.md`
- `codex/reports/nesting_engine/nesting_engine_stock_pipeline.md`
- `codex/reports/nesting_engine/nesting_engine_stock_pipeline.verify.log`