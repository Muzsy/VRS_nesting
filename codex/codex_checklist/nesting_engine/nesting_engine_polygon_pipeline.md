# Codex Checklist — nesting_engine_polygon_pipeline

**Task slug:** `nesting_engine_polygon_pipeline`  
**Canvas:** `canvases/nesting_engine/nesting_engine_polygon_pipeline.md`  
**Goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_nesting_engine_polygon_pipeline.yaml`

---

## Felderites

- [x] `AGENTS.md` elolvasva
- [x] `docs/codex/overview.md` elolvasva
- [x] `docs/codex/yaml_schema.md` elolvasva
- [x] `docs/codex/report_standard.md` elolvasva
- [x] `rust/nesting_engine/src/geometry/offset.rs` megvizsgalva
- [x] `rust/nesting_engine/src/geometry/scale.rs` megvizsgalva
- [x] `rust/nesting_engine/src/geometry/types.rs` megvizsgalva
- [x] `rust/nesting_engine/src/main.rs` megvizsgalva
- [x] `docs/nesting_engine/tolerance_policy.md` megvizsgalva
- [x] `docs/nesting_engine/io_contract_v2.md` megvizsgalva
- [x] `docs/nesting_engine/json_canonicalization.md` megvizsgalva
- [x] `scripts/check.sh` sorrendhiba azonositva (`nesting_engine` a `vrs_solver` elott volt)

## Implementacio

- [x] `rust/nesting_engine/src/io/mod.rs` letrehozva
- [x] `rust/nesting_engine/src/io/pipeline_io.rs` letrehozva (`PipelineRequest`, `PipelineResponse`, diagnostics)
- [x] `rust/nesting_engine/src/geometry/pipeline.rs` letrehozva (`run_inflate_pipeline`, hole fallback, self-intersection post-check)
- [x] `rust/nesting_engine/src/geometry/mod.rs` frissitve (`pub mod pipeline`)
- [x] `rust/nesting_engine/src/main.rs` frissitve (`inflate-parts` subcommand stdin/stdout JSON kezelessel)
- [x] `poc/nesting_engine/pipeline_smoke_input.json` letrehozva
- [x] `poc/nesting_engine/pipeline_smoke_expected.json` letrehozva
- [x] `docs/nesting_engine/architecture.md` letrehozva
- [x] `scripts/check.sh` sorrend korrigalva (`vrs_solver` sor < `nesting_engine` sor)

## Tesztek

- [x] `cargo test --manifest-path rust/nesting_engine/Cargo.toml` PASS
- [x] `python3 -m json.tool poc/nesting_engine/pipeline_smoke_input.json` PASS
- [x] `cargo build --release --manifest-path rust/vrs_solver/Cargo.toml` PASS
- [x] `cargo build --release --manifest-path rust/nesting_engine/Cargo.toml` PASS
- [x] Pipeline smoke determinizmus (`diff /tmp/pipe_out1.json /tmp/pipe_out2.json`) PASS

## Gate

- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_polygon_pipeline.md` PASS
