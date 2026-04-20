# Codex checklist - dxf_prefilter_e2_t4_duplicate_contour_dedupe_v1

- [x] Canvas + goal YAML + run prompt artefaktok elerhetoek
- [x] Letrejott kulon backend duplicate dedupe service: `api/services/dxf_preflight_duplicate_dedupe.py`
- [x] A service az E2-T1 inspect + E2-T2 role-resolution + E2-T3 gap-repair truth-ra ul, importer probe alapon (`normalize_source_entities`, `probe_layer_rings`)
- [x] A T4-ban tenylegesen hasznalt rules profile mezok minimal boundary-n mennek at: `auto_repair_enabled`, `duplicate_contour_merge_tolerance_mm`, `strict_mode`, `interactive_review_on_ambiguity`
- [x] A service csak cut-like (`CUT_OUTER`, `CUT_INNER`) zart konturvilagban vegez auto dedupe dontest
- [x] A duplicate equivalence tolerancias es determinisztikus; a keeper/drop policy explicit (importer_probe elony, canonical source layer elony, stabil tie-break)
- [x] A kimenet kulon retegeken adja vissza: `closed_contour_inventory`, `duplicate_candidate_inventory`, `applied_duplicate_dedupes`, `deduped_contour_working_set`, `remaining_duplicate_candidates`, `review_required_candidates`, `blocking_conflicts`, `diagnostics`
- [x] A task nem ad acceptance outcome-ot es nem ir DXF artifactot
- [x] A diagnostics kulon nevezi az inspect exact duplicate signal es a T4 tolerancias keeper/drop dontes elvalasztasat
- [x] Keszult task-specifikus unit teszt csomag (`tests/test_dxf_preflight_duplicate_dedupe.py`, 11 teszt)
- [x] Keszult task-specifikus smoke script (`scripts/smoke_dxf_prefilter_e2_t4_duplicate_contour_dedupe_v1.py`)
- [x] A tesztek es smoke determinisztikusak, backend-fuggetlen JSON fixture alapon futnak
- [x] Checklist es report evidence alapon frissitve
- [x] `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e2_t4_duplicate_contour_dedupe_v1.md` PASS
