# Codex checklist - dxf_prefilter_e1_t2_domain_glossary_and_role_model

- [x] Canvas + goal YAML + run prompt artefaktok elerhetoek
- [x] Letrejott a glossary dokumentum: `docs/web_platform/architecture/dxf_prefilter_domain_glossary_and_role_model.md`
- [x] A dokumentum explicit kulonvalasztja a file/object, geometry revision, contour es DXF prefilter canonical role-szinteket
- [x] A dokumentum rogziti: geometry revision-level current truth = `part` / `sheet`
- [x] A dokumentum rogziti: contour-level current truth = `outer` / `hole`
- [x] A dokumentum rogziti: future canonical prefilter role-vilag = `CUT_OUTER`, `CUT_INNER`, `MARKING`
- [x] A dokumentum rogziti: `MARKING` future canonical glossary-term, nem current geometry import truth
- [x] A dokumentum rogziti: frontend `stock_dxf` / `part_dxf` legacy upload terminology, nem source-of-truth
- [x] A dokumentum tartalmaz explicit anti-pattern listat
- [x] `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e1_t2_domain_glossary_and_role_model.md` PASS
- [x] Report DoD -> Evidence matrix kitoltve
