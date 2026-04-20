# DXF Prefilter E2-T4 Duplicate contour dedupe V1
TASK_SLUG: dxf_prefilter_e2_t4_duplicate_contour_dedupe_v1

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
- `vrs_nesting/geometry/clean.py`
- `api/services/dxf_preflight_inspect.py`
- `api/services/dxf_preflight_role_resolver.py`
- `api/services/dxf_preflight_gap_repair.py`
- `tests/test_dxf_preflight_inspect.py`
- `tests/test_dxf_preflight_role_resolver.py`
- `tests/test_dxf_preflight_gap_repair.py`
- `scripts/smoke_dxf_prefilter_e2_t1_preflight_inspect_engine_v1.py`
- `scripts/smoke_dxf_prefilter_e2_t2_color_layer_role_resolver_v1.py`
- `scripts/smoke_dxf_prefilter_e2_t3_gap_repair_v1.py`
- `canvases/web_platform/dxf_prefilter_e2_t1_preflight_inspect_engine_v1.md`
- `canvases/web_platform/dxf_prefilter_e2_t2_color_layer_role_resolver_v1.md`
- `canvases/web_platform/dxf_prefilter_e2_t3_gap_repair_v1.md`
- `canvases/web_platform/dxf_prefilter_e2_t4_duplicate_contour_dedupe_v1.md`
- `codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e2_t4_duplicate_contour_dedupe_v1.yaml`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosithatsz, ami szerepel valamelyik YAML step `outputs` listajaban.
- A minosegkaput kizarolag wrapperrel futtasd.
- Ez **duplicate contour dedupe backend task**. Ne vezess be gap repairt, normalized DXF writert,
  acceptance gate-et, DB persistence-t, API route-ot vagy frontend valtoztatast.
- Ne vezess be uj DXF parser motort es ne csereld le a meglevo importer truth-ot.
- A T4 a meglevo importer public probe truth-ra (`normalize_source_entities`, `probe_layer_rings`) es
  a T3 `repaired_path_working_set` kimenetere epuljon.
- Ne valtoztasd meg a `CHAIN_ENDPOINT_EPSILON_MM` policy jelentest a T4 kedveert.
- A T4 csak cut-like canonical role-u, zart konturvilagban dolgozzon.
- Marking-like vagy unassigned kontur ne kapjon csendes duplicate dedupe-t.
- Csak akkor legyen auto-dedupe, ha egyszerre teljesul:
  - `auto_repair_enabled=true`
  - `duplicate_contour_merge_tolerance_mm` threshold teljesul
  - a duplicate group canonical role szinten egyertelmu
  - a keeper/drop policy egyertelmu es determinisztikus
- Ne talalj ki bonyolult topology-heurisztikat: nincs partial-overlap merge, nincs containment merge,
  nincs cross-role silent merge, nincs open-path javitas.
- Az eredeti importer-forrasbol jovo closed ring elvezzen elsoseget a T3 `source="T3_gap_repair"`
  ringgel szemben, ha ugyanabba a duplicate group-ba esnek.
- Ne adj acceptance outcome-ot (`accepted_for_import`, `rejected`, stb.) es ne irj DXF artifactot.

Modellezesi elvek:
- Bemenet: inspect result + role resolution + gap repair result + minimal rules profile.
- A minimal rules profile boundary csak a T4-ban tenylegesen hasznalt mezokre nyiljon ki:
  `auto_repair_enabled`, `duplicate_contour_merge_tolerance_mm`, `strict_mode`,
  `interactive_review_on_ambiguity`.
- A kimenet kulon retegeken adja vissza a `closed_contour_inventory`, `duplicate_candidate_inventory`,
  `applied_duplicate_dedupes`, `deduped_contour_working_set`, `remaining_duplicate_candidates`,
  `review_required_candidates`, `blocking_conflicts` es `diagnostics` mezoket.
- Kulon nevezd meg diagnosticsban, hogy az inspect `duplicate_contour_candidates` exact signalja es a T4
  tolerancias keeper/drop dedupe dontese ket kulon reteg.
- A `deduped_contour_working_set` eleg legyen a T5/T6 kovetkezo lane-eknek, anelkul hogy meg egyszer
  ki kellene talalniuk a duplicate keeper/drop eredmenyt.

Kulon figyelj:
- a role resolver truth mar ne nyiljon ujra; a T4 a T2-re epit;
- a T3 `repaired_path_working_set`-et ne szethackeld, csak a closed contour working set reszekent kezeld;
- a smoke es unit teszt legyen deterministic es backend-fuggetlen;
- a reportban kulon nevezd meg, hogy az inspect exact duplicate signal miert nem volt onmagaban eleg a T4-hez,
  es hogyan lett ebbol valodi keeper/drop dedupe truth;
- nevezd meg egyertelmuen, mi marad T5/T6 scope-ban.

A reportban kulon nevezd meg:
- milyen minimal rules profile mezoket hasznal a duplicate dedupe service;
- hogyan kulonul el az inspect exact duplicate signal es a T4 tolerancias dedupe;
- mi szamit egyertelmu auto-dedupe candidate-nek;
- mi a keeper/drop policy es miert determinisztikus;
- hogyan kezeli a service a tolerancian kivuli es ambiguus duplicate eseteket;
- hogyan kezeli a cross-role es marking/unassigned duplicate vilagot;
- milyen deterministic bizonyitekok vannak a unit tesztben es a smoke-ban;
- mi maradt kifejezetten a kovetkezo taskokra.

A vegen futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e2_t4_duplicate_contour_dedupe_v1.md`

Eredmeny:
- Frissitsd a checklistet es a reportot evidence alapon.
- A reportban legyen DoD -> Evidence Matrix.
- Add meg a vegleges fajltartalmakat.
