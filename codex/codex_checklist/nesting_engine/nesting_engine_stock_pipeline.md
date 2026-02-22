# Codex Checklist — nesting_engine_stock_pipeline

**Task slug:** `nesting_engine_stock_pipeline`  
**Canvas:** `canvases/nesting_engine/nesting_engine_stock_pipeline.md`  
**Goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_nesting_engine_stock_pipeline.yaml`

---

## DoD

- [x] `StockRequest` es `StockResponse` bevezetve a `rust/nesting_engine/src/io/pipeline_io.rs`-ben (`stocks` serde default kompatibilitassal).
- [x] Rust pipeline stock ag implementalva: `inflate_outer(stock_polygon, -delta_mm)` + status policy (`ok` / `self_intersect` / `error`).
- [x] Part inflacio viselkedes valtozatlan maradt (meglevo part tesztek tovabbra is PASS).
- [x] `vrs_nesting/geometry/offset.py` stock offset alapertelmezetten Rust subprocess JSON stdio hivasra allt.
- [x] Stock self-intersect eseten determinisztikus fail (`GeometryOffsetError` + `GEO_RUST_SELF_INTERSECT`).
- [x] Rust determinizmus teszt hozzaadva irreguláris stock + hole esetre, byte-azonos JSON osszehasonlitassal es bbox-irany ellenorzessel.
- [x] `docs/nesting_engine/io_contract_v2.md` tartalmazza a "Pipeline preprocessing contract (pipeline_v1)" szekciot (`parts` + `stocks`).
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_stock_pipeline.md` PASS.
- [x] `codex/reports/nesting_engine/nesting_engine_stock_pipeline.verify.log` letrejott.

## Lokalis ellenorzesek

- [x] `cargo test --manifest-path rust/nesting_engine/Cargo.toml -q` PASS.
- [x] `python3 -m pytest -q tests/test_geometry_offset.py` PASS.
- [x] `python3 scripts/smoke_geometry_pipeline.py` PASS.
