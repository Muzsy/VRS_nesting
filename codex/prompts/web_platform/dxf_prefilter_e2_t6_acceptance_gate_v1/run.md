# DXF Prefilter E2-T6 Acceptance gate V1
TASK_SLUG: dxf_prefilter_e2_t6_acceptance_gate_v1

Olvasd el:
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `docs/web_platform/architecture/dxf_prefilter_v1_scope_and_boundary.md`
- `docs/web_platform/architecture/dxf_prefilter_state_machine_and_lifecycle_model.md`
- `docs/web_platform/architecture/dxf_prefilter_error_catalog_and_user_facing_messages.md`
- `vrs_nesting/dxf/importer.py`
- `api/services/dxf_geometry_import.py`
- `api/services/geometry_validation_report.py`
- `api/services/dxf_preflight_inspect.py`
- `api/services/dxf_preflight_role_resolver.py`
- `api/services/dxf_preflight_gap_repair.py`
- `api/services/dxf_preflight_duplicate_dedupe.py`
- `api/services/dxf_preflight_normalized_dxf_writer.py`
- `tests/test_dxf_preflight_inspect.py`
- `tests/test_dxf_preflight_role_resolver.py`
- `tests/test_dxf_preflight_gap_repair.py`
- `tests/test_dxf_preflight_duplicate_dedupe.py`
- `tests/test_dxf_preflight_normalized_dxf_writer.py`
- `scripts/smoke_dxf_prefilter_e2_t1_preflight_inspect_engine_v1.py`
- `scripts/smoke_dxf_prefilter_e2_t2_color_layer_role_resolver_v1.py`
- `scripts/smoke_dxf_prefilter_e2_t3_gap_repair_v1.py`
- `scripts/smoke_dxf_prefilter_e2_t4_duplicate_contour_dedupe_v1.py`
- `scripts/smoke_dxf_prefilter_e2_t5_normalized_dxf_writer_v1.py`
- `canvases/web_platform/dxf_prefilter_e2_t1_preflight_inspect_engine_v1.md`
- `canvases/web_platform/dxf_prefilter_e2_t2_color_layer_role_resolver_v1.md`
- `canvases/web_platform/dxf_prefilter_e2_t3_gap_repair_v1.md`
- `canvases/web_platform/dxf_prefilter_e2_t4_duplicate_contour_dedupe_v1.md`
- `canvases/web_platform/dxf_prefilter_e2_t5_normalized_dxf_writer_v1.md`
- `canvases/web_platform/dxf_prefilter_e2_t6_acceptance_gate_v1.md`
- `codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e2_t6_acceptance_gate_v1.yaml`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosithatsz, ami szerepel valamelyik YAML step `outputs` listajaban.
- A minosegkaput kizarolag wrapperrel futtasd.
- Ez **acceptance gate backend task**. Ne vezess be DB persistence-t, storage uploadot,
  API route-ot, upload triggert, async worker orchestrationt vagy frontend valtoztatast.
- Ne vezess be uj DXF parser vagy uj validator motort.
- A gate a T5 `normalized_dxf.output_path` artifactra uljon; ne a source DXF-et olvasd ujra.
- A normalized artifact visszatesztelese a tenyleges `import_part_raw(...)` utvonalon tortenjen.
- Ne duplikald a geometry import canonical normalizer logikajat es ne duplikald a geometry validator logikajat.
  Nyiss minimal public pure helper boundaryt a meglevo szolgaltatasokban, es arra epits.
- Private `_...` helperre kozvetlenul ne epits vegleges T6 boundaryt.
- A verdict precedence legyen explicit es deterministic:
  1. importer fail -> `preflight_rejected`
  2. validator rejected -> `preflight_rejected`
  3. blocking conflicts -> `preflight_rejected`
  4. review-required signalok -> `preflight_review_required`
  5. teljes pass -> `accepted_for_import`
- A T6 az elso task, amely mar kimondhat gate verdictet, de ez meg mindig local service truth,
  nem persistence/API state bridge.

Modellezesi elvek:
- Bemenet: inspect result + role resolution + gap repair result + duplicate dedupe result + normalized writer result.
- A service outputja minimum kulon retegeken adja vissza:
  - `acceptance_outcome`
  - `normalized_dxf_echo`
  - `importer_probe`
  - `validator_probe`
  - `blocking_reasons`
  - `review_required_reasons`
  - `diagnostics`
- Az `importer_probe` es `validator_probe` legyen kulon, ne mosodjon ossze a verdicttel.
- A review-required reasons minimum tudjon forrast adni az elozo taskokbol:
  role review-required, remaining open-path, remaining duplicate, skipped source entities.
- A blocking reasons minimum kulonitse el a role/gap/dedupe blocking es a validator/importer bukast.

Kulon figyelj:
- a T5 writer policy vilagot ne nyisd ujra;
- a T6 ne csusson at T7 diagnostics renderer scope-ba, de legyen eleg strukturalt,
  hogy a kovetkezo tasknak legyen mire epulnie;
- a gate outcome csak akkor lehet `accepted_for_import`, ha a normalized artifact tenylegesen atment
  az importer + validator lancon, es nincs megmaradt blocking/review signal;
- a smoke es unit teszt legyen deterministic es fedje le a 3 canonical outcome-ot;
- a reportban kulon nevezd meg, hogy melyik public helper boundary nyilt a geometry import es validator retegekben.

A reportban kulon nevezd meg:
- hogyan teszteli vissza a gate a T5 normalized artifactot a tenyleges importerrel;
- milyen public helper boundary nyilt a canonical geometry/bbox/hash eloallitashoz;
- milyen public helper boundary nyilt a local validator probe-hoz;
- mi az acceptance outcome precedence es hol van ez kodban/tesztben bizonyitva;
- hogyan kulonul el a blocking reasons es review-required reasons csalad;
- hogyan bizonyitja a tesztcsomag a 3 canonical outcome-ot;
- mi marad kifejezetten T7/E3 scope-ban.

A vegen futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e2_t6_acceptance_gate_v1.md`

Eredmeny:
- Frissitsd a checklistet es a reportot evidence alapon.
- A reportban legyen DoD -> Evidence Matrix.
- Add meg a vegleges fajltartalmakat.
