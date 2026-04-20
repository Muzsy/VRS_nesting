# DXF Prefilter E2-T5 Normalized DXF writer V1
TASK_SLUG: dxf_prefilter_e2_t5_normalized_dxf_writer_v1

Olvasd el:
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `docs/web_platform/architecture/dxf_prefilter_v1_scope_and_boundary.md`
- `docs/web_platform/architecture/dxf_prefilter_domain_glossary_and_role_model.md`
- `docs/web_platform/architecture/dxf_prefilter_policy_matrix_and_rules_profile_schema.md`
- `docs/web_platform/architecture/dxf_prefilter_state_machine_and_lifecycle_model.md`
- `docs/web_platform/architecture/dxf_prefilter_error_catalog_and_user_facing_messages.md`
- `vrs_nesting/dxf/importer.py`
- `vrs_nesting/dxf/exporter.py`
- `api/services/dxf_preflight_inspect.py`
- `api/services/dxf_preflight_role_resolver.py`
- `api/services/dxf_preflight_gap_repair.py`
- `api/services/dxf_preflight_duplicate_dedupe.py`
- `tests/test_dxf_exporter_source_mode.py`
- `tests/test_dxf_preflight_inspect.py`
- `tests/test_dxf_preflight_role_resolver.py`
- `tests/test_dxf_preflight_gap_repair.py`
- `tests/test_dxf_preflight_duplicate_dedupe.py`
- `scripts/smoke_dxf_prefilter_e2_t1_preflight_inspect_engine_v1.py`
- `scripts/smoke_dxf_prefilter_e2_t2_color_layer_role_resolver_v1.py`
- `scripts/smoke_dxf_prefilter_e2_t3_gap_repair_v1.py`
- `scripts/smoke_dxf_prefilter_e2_t4_duplicate_contour_dedupe_v1.py`
- `canvases/web_platform/dxf_prefilter_e2_t1_preflight_inspect_engine_v1.md`
- `canvases/web_platform/dxf_prefilter_e2_t2_color_layer_role_resolver_v1.md`
- `canvases/web_platform/dxf_prefilter_e2_t3_gap_repair_v1.md`
- `canvases/web_platform/dxf_prefilter_e2_t4_duplicate_contour_dedupe_v1.md`
- `canvases/web_platform/dxf_prefilter_e2_t5_normalized_dxf_writer_v1.md`
- `codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e2_t5_normalized_dxf_writer_v1.yaml`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosithatsz, ami szerepel valamelyik YAML step `outputs` listajaban.
- A minosegkaput kizarolag wrapperrel futtasd.
- Ez **normalized DXF writer backend task**. Ne vezess be acceptance gate-et,
  DB persistence-t, API route-ot, upload triggert vagy frontend valtoztatast.
- Ne vezess be uj DXF parser motort es ne csereld le a meglevo importer truth-ot.
- A T5 a meglevo importer public truth-ra (`normalize_source_entities`) es a T4
  `deduped_contour_working_set` kimenetere epuljon.
- A cut-like worldot **nem** az eredeti source entity-kbol kell visszairni, hanem
  a T4 `deduped_contour_working_set` alapjan canonical `CUT_OUTER` / `CUT_INNER`
  layerre.
- A marking-like worldot a T2 role truth alapjan, source geometry replay-jel
  lehet canonical `MARKING` layerre irni, de ne nyiss meg marking repair/dedupe
  vagy review UX vilagot.
- A minimal rules profile boundary csak a T5-ban tenylegesen hasznalt mezore nyiljon:
  `canonical_layer_colors`.
- Ne talalj ki machine/export artifact vilagot: a T5 csak local normalized DXF
  artifactot ir explicit `output_path`-ra.
- Ne adj acceptance outcome-ot (`accepted_for_import`, `preflight_rejected`, stb.).
  Ha unresolved truth marad, azt diagnosticsban nevezd meg, de ne csinalj belole gate dontest.

Modellezesi elvek:
- Bemenet: inspect result + role resolution + gap repair result + duplicate dedupe result +
  minimal rules profile + explicit `output_path`.
- A writer kimenet kulon retegeken adja vissza a `rules_profile_echo`, `normalized_dxf`,
  `writer_layer_inventory`, `skipped_source_entities` es `diagnostics` mezoket.
- A `normalized_dxf` metadata kulon nevezze meg legalabb az `output_path`, `writer_backend`,
  `written_layers`, `written_entity_count`, `cut_contour_count`, `marking_entity_count` adatokat.
- A cut-like world canonicalized writer legyen; a marking-like world source replay boundary maradjon.
- A `canonical_layer_colors` policyhoz deterministic default tartozzon, es a reportban kulon nevezz meg,
  hogy milyen canonical szinvilag lett rogzitve.

Kulon figyelj:
- a role resolver truth mar ne nyiljon ujra; a T5 a T2-re epit;
- a T3/T4 working truth-ot ne talald ujra, csak writer-oldalon hasznald fel;
- a smoke es unit teszt legyen deterministic es backend-fuggetlen a repo toolinghoz kepest;
- ahol a source entity replay nem lehetseges deterministic modon, ott structured skip diagnostika kell,
  nincs silent elvesztes;
- a reportban kulon nevezd meg, hogy a canonicalized cut writer es a marking passthrough writer miert ket kulon reteg;
- nevezd meg egyertelmuen, mi marad T6 scope-ban.

A reportban kulon nevezd meg:
- milyen minimal rules profile mezot hasznal a writer service;
- hogyan kulonul el a T4 deduped cut contour writer es a marking source replay;
- hogyan alkalmazza a service a `canonical_layer_colors` policy-t;
- hogyan akadalyozza meg a writer, hogy a source duplicate/open cut geometry visszaszivarogjon;
- hogyan kezeli a service a nem replay-elheto source entity-ket;
- milyen deterministic bizonyitekok vannak a unit tesztben es a smoke-ban;
- mi maradt kifejezetten a kovetkezo taskra.

A vegen futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e2_t5_normalized_dxf_writer_v1.md`

Eredmeny:
- Frissitsd a checklistet es a reportot evidence alapon.
- A reportban legyen DoD -> Evidence Matrix.
- Add meg a vegleges fajltartalmakat.
