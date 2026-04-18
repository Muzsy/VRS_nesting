# DXF Prefilter E1-T2 Domain glossary and role model
TASK_SLUG: dxf_prefilter_e1_t2_domain_glossary_and_role_model

Olvasd el:
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `docs/web_platform/architecture/dxf_prefilter_v1_scope_and_boundary.md`
- `vrs_nesting/dxf/importer.py`
- `api/services/dxf_geometry_import.py`
- `api/services/geometry_derivative_generator.py`
- `api/services/geometry_contour_classification.py`
- `api/routes/files.py`
- `frontend/src/pages/ProjectDetailPage.tsx`
- `frontend/src/pages/NewRunPage.tsx`
- `supabase/migrations/20260310220000_h0_e2_t1_app_schema_es_enumok.sql`
- `canvases/web_platform/dxf_prefilter_e1_t2_domain_glossary_and_role_model.md`
- `codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e1_t2_domain_glossary_and_role_model.yaml`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosithatsz, ami szerepel valamelyik
  YAML step `outputs` listajaban.
- Ez **docs-only glossary freeze** task. Ne vezess be Python, TypeScript,
  SQL, migration, enum, route vagy API implementacios valtoztatast.
- Ne valtoztasd meg a meglvo `app.geometry_role`, `file_kind`, `contour_role`
  vagy frontend tipusokat ebben a taskban.
- Ne talalj ki mar implementaltkent olyan role-t vagy enumot, ami jelenleg csak
  jovobeli prefilter canonical terminus.
- A dokumentumnak a jelenlegi kodra kell epulnie: importer, geometry import,
  derivative generator, contour classification, file upload es frontend entrypointok
  konkret figyelembevetelével.

A dokumentacios elvarasok:
- Kulonitsd el a file/object-level, geometry revision-level, contour-level es
  DXF prefilter canonical layer-role szinteket.
- Rogzitsd, hogy a current-code geometry revision role jelenleg `part` / `sheet`.
- Rogzitsd, hogy a contour-level role jelenleg `outer` / `hole`.
- Rogzitsd, hogy a DXF prefilter jovobeli canonical role-vilag: `CUT_OUTER`,
  `CUT_INNER`, `MARKING`.
- Rogzitsd kulon, hogy a `MARKING` glossary-szintu future canonical term, nem
  mar bekotott geometry import truth.
- Rogzitsd, hogy a frontend legacy `stock_dxf` / `part_dxf` upload terminologia
  nem source-of-truth.
- Legyen explicit tiltott osszemosas / anti-pattern lista.

A reportban nevezd meg kulon:
- melyik meglevo fajlokra epul a glossary;
- mely fogalmak current-code truth-kent rogzitettek;
- mely fogalmak future canonical prefilter szohasznalatkent jelennek meg;
- miert fontos a role-szintek elvalasztasa a kovetkezo taskokhoz.

A vegen futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e1_t2_domain_glossary_and_role_model.md`

Eredmeny:
- Frissitsd a checklistet es a reportot evidence-alapon.
- A reportban legyen DoD -> Evidence matrix es korrekt AUTO_VERIFY blokk.
- Add meg a vegleges fajltartalmakat.
