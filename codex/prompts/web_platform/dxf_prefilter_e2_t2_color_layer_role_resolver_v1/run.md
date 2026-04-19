# DXF Prefilter E2-T2 Color/layer role resolver V1
TASK_SLUG: dxf_prefilter_e2_t2_color_layer_role_resolver_v1

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
- `api/services/dxf_preflight_inspect.py`
- `vrs_nesting/dxf/importer.py`
- `tests/test_dxf_preflight_inspect.py`
- `scripts/smoke_dxf_prefilter_e2_t1_preflight_inspect_engine_v1.py`
- `canvases/web_platform/dxf_prefilter_e2_t1_preflight_inspect_engine_v1.md`
- `canvases/web_platform/dxf_prefilter_e2_t2_color_layer_role_resolver_v1.md`
- `codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e2_t2_color_layer_role_resolver_v1.yaml`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosithatsz, ami szerepel valamelyik YAML step `outputs` listajaban.
- A minosegkaput kizarolag wrapperrel futtasd.
- Ez **role-resolver backend task**. Ne vezess be repair, normalized DXF writer,
  acceptance gate, DB persistence, API route vagy frontend valtoztatast.
- Ne hivd ujra kozvetlenul a DXF importert es ne olvass forrasfajlt a resolverben;
  a T2 az E2-T1 inspect result objektumara uljon.
- Ne talalj ki uj nyers signalokat: a resolver csak a T1 inspect truth altal hordozott
  `layer`, `color_index`, `linetype_name`, `contour/open-path/duplicate/topology`
  signalokra tamaszkodhat.
- Az explicit canonical layer mapping (`CUT_OUTER`, `CUT_INNER`, `MARKING`) elvezzen
  precedence-t a color hint es a topology proxy felett.
- A color policy role-first legyen: a color csak `cut-like` vagy `marking-like`
  iranyt adhat, nem irhatja felul a mar canonical source layert.
- Ne csinalj geometry modositas, gap javitast, contour dedupe fixet vagy DXF ujrairast;
  ezek T3/T4/T5 scope-ban maradnak.
- Ne adj acceptance outcome-ot (`accepted_for_import`, `rejected`, stb.); a T2 kimenete
  role-resolved truth + review/blocking conflict signal legyen.
- A linetype a T2-ben legfeljebb diagnosztikai/raw evidence szerepu lehet; ne vezess be
  linetype-first role policy-t.

Modellezesi elvek:
- Bemenet: inspect result + minimal rules profile.
- A rules profile boundary csak a T2-ben tenylegesen hasznalt mezokre nyiljon ki:
  `strict_mode`, `interactive_review_on_ambiguity`, `cut_color_map`, `marking_color_map`.
- A resolver kulon retegeken adja vissza a `layer_role_assignments`,
  `entity_role_assignments`, `resolved_role_inventory`, `review_required_candidates`,
  `blocking_conflicts` es `diagnostics` mezoket.
- `cut-like` jel eseten a T1 topology proxy segithet outer vs inner feloldasban,
  de ha a proxy nem egyertelmu, ne talalj ki uj heurisztikat; legyen review-required
  vagy blocking conflict a policy szerint.
- Nyitott path maradhat marking-jellegu; cut-like open path nem lehet csendes success.

Kulon figyelj:
- a mai importer strict truth (`CUT_OUTER`/`CUT_INNER`) maradjon a legkonnyebb zold ut;
- a smoke es unit teszt legyen backend-fuggetlen es deterministic;
- a reportban kulon nevezd meg a precedence szabalyokat es a konfliktus-csaladokat;
- nevezd meg egyertelmuen, mi marad T3/T4/T5/T6 scope-ban.

A reportban kulon nevezd meg:
- milyen minimal rules profile mezoket hasznal a resolver;
- milyen precedence szabaly alapjan szuletik a canonical role assignment;
- hogyan kezeli a resolver az explicit layer vs color-hint konfliktust;
- hogyan kezeli a cut-like open-path esetet acceptance gate nelkul;
- milyen deterministic bizonyitekok vannak a unit tesztben es a smoke-ban;
- mi maradt kifejezetten a kovetkezo taskokra.

A vegen futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e2_t2_color_layer_role_resolver_v1.md`

Eredmeny:
- Frissitsd a checklistet es a reportot evidence alapon.
- A reportban legyen DoD -> Evidence Matrix.
- Add meg a vegleges fajltartalmakat.
