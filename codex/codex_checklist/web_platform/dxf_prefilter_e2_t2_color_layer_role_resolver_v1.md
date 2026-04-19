# Codex checklist - dxf_prefilter_e2_t2_color_layer_role_resolver_v1

- [x] Canvas + goal YAML + run prompt artefaktok elerhetoek
- [x] Letrejott kulon backend role resolver service: `api/services/dxf_preflight_role_resolver.py`
- [x] A T2-ben tenylegesen hasznalt rules profile mezok minimal validator/normalizer hataron mennek at (`strict_mode`, `interactive_review_on_ambiguity`, `cut_color_map`, `marking_color_map`)
- [x] Az explicit canonical layer mapping (`CUT_OUTER`, `CUT_INNER`, `MARKING`) precedence-t elvez a color hint es topology proxy felett
- [x] A color-hint policy tud `cut-like` es `marking-like` iranyt adni canonical layer hianyaban; nem irhatja felul a mar canonical source layert
- [x] A topology proxy determinisztikusan segit outer vs inner feloldasban, de nem talal ki uj nyers signalokat
- [x] A resolver kulon listazza a `layer_role_assignments`, `entity_role_assignments`, `resolved_role_inventory`, `review_required_candidates`, `blocking_conflicts`, `diagnostics` retegeket
- [x] A task nem nyitotta meg a repair / normalized DXF writer / acceptance gate / route / persistence / UI scope-ot
- [x] Az explicit `CUT_OUTER` / `CUT_INNER` current-code truth tovabbra is zold ut marad (importer regression nincs)
- [x] Keszult task-specifikus unit teszt (`tests/test_dxf_preflight_role_resolver.py`, 20 teszt) es smoke script (`scripts/smoke_dxf_prefilter_e2_t2_color_layer_role_resolver_v1.py`, 7 scenario)
- [x] A checklist es report evidence-alapon frissult (DoD -> Evidence Matrix)
- [x] `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e2_t2_color_layer_role_resolver_v1.md` PASS (check.sh exit 0, 172s, `main@ec942a6`; lasd a report AUTO_VERIFY blokkot es `.verify.log` fajlt)
