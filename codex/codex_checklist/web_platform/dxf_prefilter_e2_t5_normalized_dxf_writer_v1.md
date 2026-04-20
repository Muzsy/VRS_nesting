# Codex checklist - dxf_prefilter_e2_t5_normalized_dxf_writer_v1

- [x] Canvas + goal YAML + run prompt + checklist + report artefaktok elerhetoek
- [x] Letrejott kulon backend normalized DXF writer service: `api/services/dxf_preflight_normalized_dxf_writer.py`
- [x] A service az E2-T1 inspect + E2-T2 role-resolution + E2-T3 gap-repair + E2-T4 duplicate-dedupe truth-ra ul
- [x] A T5-ben tenylegesen hasznalt rules profile mezok minimal boundary-n mennek at: `canonical_layer_colors`
- [x] A cut-like world a T4 `deduped_contour_working_set` alapjan irodik canonical `CUT_OUTER` / `CUT_INNER` layerre
- [x] A marking-like world T2 role truth alapjan source replay-jel irodik canonical `MARKING` layerre, deterministic skip diagnosztikaval
- [x] A writer alkalmazza a `canonical_layer_colors` policy-t deterministic defaulttal
- [x] A service explicit `output_path`-ra ir local normalized DXF artifactot es metadata/diagnostics reteget ad vissza
- [x] A task nem vezetett be acceptance outcome-ot, DB persistence-t, API route-ot, upload triggert vagy frontend valtoztatast
- [x] Keszult task-specifikus unit teszt csomag (`tests/test_dxf_preflight_normalized_dxf_writer.py`, 5 teszt)
- [x] Keszult task-specifikus smoke script (`scripts/smoke_dxf_prefilter_e2_t5_normalized_dxf_writer_v1.py`)
- [x] Checklist es report evidence alapon frissitve
- [x] `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e2_t5_normalized_dxf_writer_v1.md` PASS
