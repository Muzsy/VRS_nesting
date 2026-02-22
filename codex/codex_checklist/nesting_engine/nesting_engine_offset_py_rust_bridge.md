# Codex Checklist — nesting_engine_offset_py_rust_bridge

**Task slug:** `nesting_engine_offset_py_rust_bridge`  
**Canvas:** `canvases/nesting_engine/nesting_engine_offset_py_rust_bridge.md`  
**Goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_nesting_engine_offset_py_rust_bridge.yaml`

---

## DoD

- [x] A `vrs_nesting/geometry/offset.py` part inflációja default Rust `inflate-parts` subprocess JSON stdio útvonalat használ.
- [x] Shapely fallback csak explicit policy-val aktiválható (`VRS_OFFSET_PART_ENGINE=shapely` vagy `VRS_OFFSET_ALLOW_SHAPELY_FALLBACK=1`).
- [x] `self_intersect` statusz determinisztikus fail.
- [x] `hole_collapsed` statusz nem okoz crash-t.
- [x] Unit tesztek lefedik: Rust hívás/request JSON, `self_intersect`, `hole_collapsed`, explicit Shapely policy.
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_offset_py_rust_bridge.md` PASS.
- [x] Report AUTO_VERIFY blokk és `.verify.log` elkészült.

## Lokális ellenőrzések

- [x] `python3 -m pytest -q tests/test_geometry_offset.py` PASS.
- [x] `python3 -m pytest -q tests/test_sparrow_input_generator.py` PASS.
- [x] `python3 -m pytest -q` PASS.
- [x] `python3 -m mypy --config-file mypy.ini vrs_nesting` PASS.
