# DXF Prefilter E2-T3 Gap repair V1
TASK_SLUG: dxf_prefilter_e2_t3_gap_repair_v1

Olvasd el:
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `docs/web_platform/architecture/dxf_prefilter_v1_scope_and_boundary.md`
- `docs/web_platform/architecture/dxf_prefilter_policy_matrix_and_rules_profile_schema.md`
- `docs/web_platform/architecture/dxf_prefilter_state_machine_and_lifecycle_model.md`
- `docs/web_platform/architecture/dxf_prefilter_error_catalog_and_user_facing_messages.md`
- `vrs_nesting/dxf/importer.py`
- `api/services/dxf_preflight_inspect.py`
- `api/services/dxf_preflight_role_resolver.py`
- `tests/test_dxf_importer_json_fixture.py`
- `tests/test_dxf_preflight_inspect.py`
- `tests/test_dxf_preflight_role_resolver.py`
- `scripts/smoke_dxf_prefilter_e2_t1_preflight_inspect_engine_v1.py`
- `scripts/smoke_dxf_prefilter_e2_t2_color_layer_role_resolver_v1.py`
- `canvases/web_platform/dxf_prefilter_e2_t1_preflight_inspect_engine_v1.md`
- `canvases/web_platform/dxf_prefilter_e2_t2_color_layer_role_resolver_v1.md`
- `canvases/web_platform/dxf_prefilter_e2_t3_gap_repair_v1.md`
- `codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e2_t3_gap_repair_v1.yaml`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosithatsz, ami szerepel valamelyik YAML step `outputs` listajaban.
- A minosegkaput kizarolag wrapperrel futtasd.
- Ez **gap-repair backend task**. Ne vezess be duplicate contour dedupe, normalized DXF writer,
  acceptance gate, DB persistence, API route vagy frontend valtoztatast.
- Ne vezess be uj DXF parser motort es ne csereld le a meglevo importer truth-ot.
- A T3 csak a meglevo importer public feluleteire epulhet. Ha a residual open path geometriat
  ma nem lehet eleg reszletesen elerni, azt minimalisan a public importer/probe boundary
  bovitesekent oldd meg, ne ad hoc masolassal.
- Ne valtoztasd meg a `CHAIN_ENDPOINT_EPSILON_MM` policy jelentest a T3 kedveert.
  A T3 a chaining utan is megmarado residual open path vilag javitasa legyen.
- A T3 csak cut-like layer/path vilagban dolgozzon, az E2-T2 role-resolution truth-ra epitve.
- Marking-like vagy unassigned vilag ne kapjon csendes auto-gap-repairt.
- Csak akkor legyen auto-repair, ha egyszerre teljesul:
  - `auto_repair_enabled=true`
  - `max_gap_close_mm` threshold teljesul
  - a partner-pairing egyertelmu
  - a javitas utan a reprobe konzisztens eredmenyt ad
- Ne talalj ki bonyolult topology-heurisztikat: nincs branch-resolve, nincs tobb partner kozul
  okoskodo valasztas, nincs self-intersection auto-fix, nincs outer/inner topology javitas.
- Ne adj acceptance outcome-ot (`accepted_for_import`, `rejected`, stb.) es ne irj DXF artifactot.

Modellezesi elvek:
- Bemenet: inspect result + role resolution + minimal rules profile.
- A minimal rules profile boundary csak a T3-ban tenylegesen hasznalt mezokre nyiljon ki:
  `auto_repair_enabled`, `max_gap_close_mm`, `strict_mode`, `interactive_review_on_ambiguity`.
- A kimenet kulon retegeken adja vissza a `repair_candidate_inventory`, `applied_gap_repairs`,
  `repaired_path_working_set`, `remaining_open_path_candidates`, `review_required_candidates`,
  `blocking_conflicts` es `diagnostics` mezoket.
- Kulon nevezd meg diagnosticsban, hogy mi volt mar meglevo importer chaining-eredmeny, es mi az,
  amit a T3 uj residual gap repair retege vegzett el.
- A `repaired_path_working_set` eleg legyen a T4/T5 kovetkezo lane-eknek, anelkul hogy meg egyszer
  ki kellene talalniuk a gap repair eredmenyet.

Kulon figyelj:
- a role resolver truth mar ne nyiljon ujra; a T3 a T2-re epit;
- a smoke es unit teszt legyen deterministic es backend-fuggetlen;
- a reportban kulon nevezd meg, hogy a mai inspect output miert volt onmagaban elegtelen a gap repairhez,
  es hogyan lett ez minimalis public probe bovitessel rendezve;
- nevezd meg egyertelmuen, mi marad T4/T5/T6 scope-ban.

A reportban kulon nevezd meg:
- milyen minimal rules profile mezoket hasznal a gap repair service;
- hogyan kulonul el a meglevo importer chaining truth es a T3 residual gap repair;
- mi szamit egyertelmu javithato gap-nek;
- hogyan kezeli a service a threshold feletti es ambiguus gap eseteket;
- hogyan kezeli a marking-like open path vilagot;
- milyen deterministic bizonyitekok vannak a unit tesztben es a smoke-ban;
- mi maradt kifejezetten a kovetkezo taskokra.

A vegen futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e2_t3_gap_repair_v1.md`

Eredmeny:
- Frissitsd a checklistet es a reportot evidence alapon.
- A reportban legyen DoD -> Evidence Matrix.
- Add meg a vegleges fajltartalmakat.
