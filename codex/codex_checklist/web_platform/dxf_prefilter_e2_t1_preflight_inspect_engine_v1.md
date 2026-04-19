# Codex checklist - dxf_prefilter_e2_t1_preflight_inspect_engine_v1

- [x] Canvas + goal YAML + run prompt artefaktok elerhetoek
- [x] Minimal, public importer-felulet kinyilt a raw inspect celra; nem uj parser logika keszult
- [x] A normalized entity inventory hordozza a preflight T1-hez szukseges `layer/type/closed/color_index/linetype_name` raw signalokat (JSON + DXF backendre is, determinisztikus hiany-kezelessel)
- [x] Letrejott kulon backend inspect service: `api/services/dxf_preflight_inspect.py`
- [x] A service inspect result objektumot ad vissza, kulon inventory es diagnostics reteggel (`entity/layer/color/linetype inventory`, `contour_candidates`, `open_path_candidates`, `duplicate_contour_candidates`, `outer_like_candidates`, `inner_like_candidates`, `diagnostics`)
- [x] A service javitas, role assignment es acceptance outcome nelkul tud jelolteket listazni
- [x] A task nem nyitotta meg a route / `dxf_geometry_import` pipeline / persistence / UI scope-ot
- [x] A mai `import_part_raw()` acceptance viselkedese nem romlott (meglevo importer unit + smoke tesztek tovabbra is zoldek)
- [x] Keszult task-specifikus unit teszt (`tests/test_dxf_preflight_inspect.py`) es smoke script (`scripts/smoke_dxf_prefilter_e2_t1_preflight_inspect_engine_v1.py`)
- [x] A checklist es a report evidence-alapon frissult (DoD -> Evidence Matrix)
- [x] `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e2_t1_preflight_inspect_engine_v1.md` PASS
