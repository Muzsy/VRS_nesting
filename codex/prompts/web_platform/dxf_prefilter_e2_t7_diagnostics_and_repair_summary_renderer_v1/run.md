# DXF Prefilter E2-T7 Diagnostics and repair summary renderer V1
TASK_SLUG: dxf_prefilter_e2_t7_diagnostics_and_repair_summary_renderer_v1

Olvasd el:
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `docs/web_platform/architecture/dxf_prefilter_v1_scope_and_boundary.md`
- `docs/web_platform/architecture/dxf_prefilter_error_catalog_and_user_facing_messages.md`
- `docs/web_platform/architecture/dxf_prefilter_api_contract_specification.md`
- `api/services/dxf_preflight_inspect.py`
- `api/services/dxf_preflight_role_resolver.py`
- `api/services/dxf_preflight_gap_repair.py`
- `api/services/dxf_preflight_duplicate_dedupe.py`
- `api/services/dxf_preflight_normalized_dxf_writer.py`
- `api/services/dxf_preflight_acceptance_gate.py`
- `tests/test_dxf_preflight_inspect.py`
- `tests/test_dxf_preflight_role_resolver.py`
- `tests/test_dxf_preflight_gap_repair.py`
- `tests/test_dxf_preflight_duplicate_dedupe.py`
- `tests/test_dxf_preflight_normalized_dxf_writer.py`
- `tests/test_dxf_preflight_acceptance_gate.py`
- `scripts/smoke_dxf_prefilter_e2_t1_preflight_inspect_engine_v1.py`
- `scripts/smoke_dxf_prefilter_e2_t2_color_layer_role_resolver_v1.py`
- `scripts/smoke_dxf_prefilter_e2_t3_gap_repair_v1.py`
- `scripts/smoke_dxf_prefilter_e2_t4_duplicate_contour_dedupe_v1.py`
- `scripts/smoke_dxf_prefilter_e2_t5_normalized_dxf_writer_v1.py`
- `scripts/smoke_dxf_prefilter_e2_t6_acceptance_gate_v1.py`
- `canvases/web_platform/dxf_prefilter_e2_t6_acceptance_gate_v1.md`
- `canvases/web_platform/dxf_prefilter_e2_t7_diagnostics_and_repair_summary_renderer_v1.md`
- `codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e2_t7_diagnostics_and_repair_summary_renderer_v1.yaml`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosithatsz, ami szerepel valamelyik YAML step `outputs` listajaban.
- A minosegkaput kizarolag wrapperrel futtasd.
- Ez **backend diagnostics renderer task**. Ne vezess be DB persistence-t, storage uploadot,
  API route-ot, upload triggert, worker orchestrationt vagy frontend valtoztatast.
- Ne vezess be uj DXF parser/validator motort, es a rendererben ne futtass uj importer/validator probe-ot.
- A renderer kizarolag a mar meglevo T1 inspect, T2 role resolution, T3 gap repair,
  T4 duplicate dedupe, T5 normalized writer es T6 acceptance gate output shape-ekre uljon.
- Ne nyisd ujra a T1→T6 policy vagy precedence vilagot. A T7 csak a meglevo jeleket normalizalja es rendereli.
- Az artifact references T7-ben meg local backend referenciak maradjanak; ne generalj signed URL-t vagy storage-backed linket.
- A T7 ne csusson at E3 persistence/API vagy E4 UI scope-ba.

Modellezesi elvek:
- A service bemenete minimum a 6 elozo task local truth-ja.
- A kimenet legyen egyetlen, deterministic, JSON-serialisable summary objektum.
- A summary minimum kulon retegekben adja vissza:
  - `source_inventory_summary`
  - `role_mapping_summary`
  - `issue_summary`
  - `repair_summary`
  - `acceptance_summary`
  - `artifact_references`
- Az issue-normalizalas minimum tartalmazza:
  - `severity`
  - `source`
  - `family`
  - `code` vagy `display_code`
  - `message`
  - `details`
- A repair summary kulonitse el:
  - applied gap repair-eket
  - applied duplicate dedupe donteseket
  - writer skipped source entity-ket
  - megmaradt unresolved jeleket
- Az acceptance summary kulon tartsa:
  - `acceptance_outcome`
  - importer highlight-ot
  - validator highlight-ot
  - precedence rule echo-t
- Az artifact references minimum egy local normalized DXF referenciat adjon:
  - `artifact_kind`
  - `path`
  - `exists`
  - `download_label`

Kulon figyelj:
- a renderer ne novelje tovabb a T6 acceptance gate felelosseget; kulon service legyen;
- a source inventory summary hasznalja a T1 inventory truth-ot, ne szamoljon ujra semmit DXF-bol;
- a renderer ne legyen `ezdxf`-fuggo futasi oldalon, ha a bemenet mar eloallt;
- a summary shape legyen eleg stabil, hogy a kovetkezo E3/E4 retegek ezt egyetlen truthkent hasznalhassak;
- a reportban kulon nevezd meg, hogy mi marad E3/E4 scope-ban.

A reportban kulon nevezd meg:
- hogyan epul fel a vegso summary object;
- hogyan normalizalod az issue severity/source/family reteget;
- hogyan kulonul el az applied repair summary es az unresolved signals vilaga;
- milyen artifact reference shape-et ad a service local backend szinten;
- hogyan bizonyitja a tesztcsomag az accepted/review/rejected flow-kat;
- hogyan bizonyitod, hogy a renderer nem nyitott uj parser/importer/validator/persistence/API/UI scope-ot.

A vegen futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e2_t7_diagnostics_and_repair_summary_renderer_v1.md`

Eredmeny:
- Frissitsd a checklistet es a reportot evidence alapon.
- A reportban legyen DoD -> Evidence Matrix.
- Add meg a vegleges fajltartalmakat.
