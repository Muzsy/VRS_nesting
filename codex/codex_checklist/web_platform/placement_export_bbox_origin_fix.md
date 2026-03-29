# Codex checklist - placement_export_bbox_origin_fix

- [x] Canvas + goal YAML + run prompt artefaktok elerhetoek
- [x] A worker placement referenciaja (`bbox_min_corner`) explicit es kovetkezetes truth-ra kerult
- [x] A `worker/result_normalizer.py` a projektalt bbox-ot a normalizalt lokalis bbox-bol szamolja
- [x] A `worker/sheet_svg_artifacts.py` bbox-min base offsettel exportal
- [x] A `worker/sheet_dxf_artifacts.py` ugyanazzal a placement szemantikaval exportal, mint az SVG
- [x] A canonical projection es a tenyleges SVG/DXF export ugyanarra a sheet-beli helyzetre mutat
- [x] Determinisztikus out-of-sheet guard bevezetve (`assert_projection_within_sheet_bounds`)
- [x] A worker regressziosan bizonyitottan alkalmazza a nem nulla (`180.0`) rotaciot
- [x] A task expliciten out-of-scope-kent kezeli a shape-aware rotation valasztast (solver policy valtozatlan)
- [x] Letrejott task-specifikus smoke: `scripts/smoke_placement_export_bbox_origin_fix.py`
- [x] `python3 -m py_compile worker/main.py worker/result_normalizer.py worker/sheet_svg_artifacts.py worker/sheet_dxf_artifacts.py scripts/smoke_placement_export_bbox_origin_fix.py` PASS
- [x] `python3 scripts/smoke_placement_export_bbox_origin_fix.py` PASS
- [x] Regresszios ellenorzes: `smoke_h1_e6_t1`, `smoke_h1_e6_t2`, `smoke_h1_e6_t3` PASS
- [x] `./scripts/verify.sh --report codex/reports/web_platform/placement_export_bbox_origin_fix.md` PASS
- [x] Report DoD -> Evidence matrix kitoltve
