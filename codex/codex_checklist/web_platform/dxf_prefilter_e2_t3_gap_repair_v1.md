# Codex checklist - dxf_prefilter_e2_t3_gap_repair_v1

- [x] Canvas + goal YAML + run prompt artefaktok elerhetoek
- [x] Minimalis public importer/probe boundary bovites a residual open path geometriara: `probe_layer_open_paths` es `_collect_layer_rings` modositas a `vrs_nesting/dxf/importer.py`-ban
- [x] Letrejott kulon backend gap repair service: `api/services/dxf_preflight_gap_repair.py`
- [x] A service csak cut-like (`CUT_OUTER`, `CUT_INNER`) residual open path vilagban dolgozik; marking-like es unassigned layer nem kap csendes auto-gap-repairt
- [x] A T3-ban tenylegesen hasznalt rules profile mezok minimal boundary-n mennek at: `auto_repair_enabled`, `max_gap_close_mm`, `strict_mode`, `interactive_review_on_ambiguity`
- [x] Auto-repair csak akkor fut, ha egyszerre teljesul: `auto_repair_enabled=True`, gap <= `max_gap_close_mm`, a partner-pairing egyertelmu, es a reprobe konzisztens
- [x] A kimenet kulon retegeken adja vissza: `repair_candidate_inventory`, `applied_gap_repairs`, `repaired_path_working_set`, `remaining_open_path_candidates`, `review_required_candidates`, `blocking_conflicts`, `diagnostics`
- [x] Az `applied_gap_repairs` minden eleme `bridge_source="T3_residual_gap_repair"`-t hordoz (elkulonul a meglevo importer chaining truth-tol)
- [x] A diagnostics kulon nevezi meg, hogy mi volt meglevo importer chaining eredmeny es mi az, amit a T3 uj residual gap repair retege vegzett
- [x] A task nem ad `accepted_for_import`, `rejected` stb. acceptance outcome-ot es nem ir DXF artifactot
- [x] Nincs duplicate contour dedupe, normalized DXF writer, DB persistence, API route vagy frontend modositas
- [x] Keszult task-specifikus unit teszt csomag (`tests/test_dxf_preflight_gap_repair.py`, 22 teszt) es smoke script (`scripts/smoke_dxf_prefilter_e2_t3_gap_repair_v1.py`, 9 scenario)
- [x] A tesztek es smoke determinisztikusak es backend-fuggetlenek (in-memory / temp JSON fixture alapu)
- [x] A checklist es report evidence-alapon frissult (DoD -> Evidence Matrix)
- [x] `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e2_t3_gap_repair_v1.md` PASS (check.sh exit 0, 183s, `main@bd85189`; lasd a report AUTO_VERIFY blokkot es `.verify.log` fajlt)
