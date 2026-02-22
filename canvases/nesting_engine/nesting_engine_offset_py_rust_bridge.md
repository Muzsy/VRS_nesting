# nesting_engine_offset_py_rust_bridge

## Funkcio

A Python oldali part offset/inflate (`vrs_nesting/geometry/offset.py`) alapertelmezett motorja legyen a Rust `nesting_engine inflate-parts` JSON stdin/stdout pipeline.

Celpont: Phase 1 / F1-3 lezarsa ugy, hogy a feasibility-geometria forrasa a Rust kernel legyen, mikozben a Python API kompatibilis marad.

### Kotelezo eredmeny
- `offset_part_geometry()` default utvonala Rust subprocess (`inflate-parts`) legyen.
- A Shapely fallback csak explicit policy mellett aktivhato.
- `SELF_INTERSECT` statusz fail legyen.
- `HOLE_COLLAPSED` statusz ne okozzon crash-t.

### Nem cel (explicit)
- `offset_stock_geometry()` Rust-ra mozgatasa. A stock offset marad Shapely ebben a taskban.
- NFP/placement/Phase2 valtoztatas.

## Fejlesztesi reszletek

### Erintett valos fajlok
- `vrs_nesting/geometry/offset.py`
- `vrs_nesting/sparrow/input_generator.py` (API kompatibilitas referenciakent)
- `rust/nesting_engine/src/main.rs`
- `rust/nesting_engine/src/io/pipeline_io.rs`
- `rust/nesting_engine/src/geometry/pipeline.rs`
- `scripts/check.sh`
- `vrs_nesting/runner/nesting_engine_runner.py`

### Valos JSON contract (Rust kod alapjan)

`inflate-parts` stdin (`PipelineRequest`):
- `version: string`
- `kerf_mm: number`
- `margin_mm: number`
- `parts: PartRequest[]`
- `PartRequest.id: string`
- `PartRequest.outer_points_mm: [x, y][]`
- `PartRequest.holes_points_mm: [ [x, y][] ]`

`inflate-parts` stdout (`PipelineResponse`):
- `version: string`
- `parts: PartResponse[]`
- `PartResponse.id: string`
- `PartResponse.status: "ok" | "hole_collapsed" | "self_intersect" | "error"`
- `PartResponse.inflated_outer_points_mm: [x, y][]`
- `PartResponse.inflated_holes_points_mm: [ [x, y][] ]`
- `PartResponse.diagnostics: Diagnostic[]`
- `Diagnostic.code: string` (pl. `HOLE_COLLAPSED`, `SELF_INTERSECT`, `OFFSET_ERROR`)
- `Diagnostic.detail: string`
- opcionális: `hole_index`, `nominal_hole_bbox_mm`, `preserve_for_export`, `usable_for_nesting`

### Bináris feloldas (repo gyakorlat)
- `vrs_nesting/runner/nesting_engine_runner.py`: explicit arg -> `NESTING_ENGINE_BIN` env -> `nesting_engine` PATH.
- `scripts/check.sh`: baseline smoke konkret release pathon futtat: `rust/nesting_engine/target/release/nesting_engine`.
- A bridge ennek megfeleloen oldja fel a binarist, plusz engedjen app-szintu env override-t (`VRS_NESTING_ENGINE_BIN`).

### Implementacios elvek
1. A part offset kerese JSON requestet epit:
   - `version = "pipeline_v1"`
   - `kerf_mm = spacing_mm`
   - `margin_mm = 0.0` (igy Rust oldalon `delta = spacing_mm / 2`)
2. Rust subprocess hivas:
   - command: `[resolved_bin, "inflate-parts"]`
   - stdin/stdout text JSON
   - timeout kezeles
3. Hibakezeles:
   - non-zero exit -> determinisztikus `GeometryOffsetError`
   - stdout parse/schema hiba -> determinisztikus `GeometryOffsetError`
   - `self_intersect` -> determinisztikus fail
   - `hole_collapsed` -> sikeres visszaadas (nem crash)
4. Fallback policy:
   - default: Rust
   - Shapely fallback csak explicit env policy engedelyezesevel
5. API kompatibilitas:
   - `offset_part_geometry(payload, spacing_mm=...)` signature valtozatlan
   - `offset_stock_geometry(...)` signature/viselkedes valtozatlan (Shapely)

### Determinizmus megjegyzes (report advisory)
- `rust/nesting_engine/src/placement/blf.rs` szabad forgatas f64 trig alapu; bit-azonos determinismhez kesobb LUT/fixed-point lehet szukseges.

## Tesztallapot

### DoD / kotelezo ellenorzesek
- Van unit teszt, ami bizonyitja, hogy part offsetnel a Rust subprocess ut hívódik.
- Van unit teszt `self_intersect` statusz fail utjara.
- Van unit teszt `hole_collapsed` statusz crash-mentes kezelesere.
- Van unit teszt az explicit Shapely engine policyre.
- `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_offset_py_rust_bridge.md` PASS.

## Lokalizacio

Nincs UI. Logok/hibak fejlesztoi jelleguek, rovidek, stabil kodokkal.

## Kapcsolodasok

- `docs/nesting_engine/architecture.md`
- `rust/nesting_engine/src/main.rs`
- `rust/nesting_engine/src/io/pipeline_io.rs`
- `rust/nesting_engine/src/geometry/pipeline.rs`
- `vrs_nesting/geometry/offset.py`
- `vrs_nesting/sparrow/input_generator.py`
