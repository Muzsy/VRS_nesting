# Codex Checklist — arc_spline_polygonization_policy

**Task slug:** `arc_spline_polygonization_policy`  
**Canvas:** `canvases/nesting_engine/arc_spline_polygonization_policy.md`  
**Goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_arc_spline_polygonization_policy.yaml`

---

## DoD

- [x] `arc_tolerance_mm = 0.2` dokumentálva és ténylegesen alkalmazva van az importer curve policy-ban.
- [x] Repo-native arc-heavy fixture készlet elkészült a `samples/dxf_demo/` alatt.
- [x] A pozitív arc-heavy fixture-ök polygonizálása után nincs self-intersection.
- [x] A negatív arc-heavy fixture determinisztikusan `DXF_INVALID_RING` hibával bukik.
- [x] Kapcsolódó pytest csomag PASS (`tests/test_geometry_polygonize.py`, importer regression tesztek).
- [x] `python3 scripts/smoke_real_dxf_fixtures.py` PASS a bővített fixture körrel.
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/arc_spline_polygonization_policy.md` lefuttatva.
