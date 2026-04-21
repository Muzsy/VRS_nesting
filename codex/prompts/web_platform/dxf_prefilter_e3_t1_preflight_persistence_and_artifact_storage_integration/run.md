# DXF Prefilter E3-T1 Preflight persistence es artifact storage bekotes
TASK_SLUG: dxf_prefilter_e3_t1_preflight_persistence_and_artifact_storage_integration

Olvasd el:
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `docs/web_platform/architecture/dxf_prefilter_data_model_and_migration_plan.md`
- `docs/web_platform/architecture/dxf_prefilter_api_contract_specification.md`
- `docs/web_platform/architecture/h0_storage_bucket_strategia_es_path_policy.md`
- `api/supabase_client.py`
- `api/services/file_ingest_metadata.py`
- `api/services/dxf_preflight_normalized_dxf_writer.py`
- `api/services/dxf_preflight_acceptance_gate.py`
- `api/services/dxf_preflight_diagnostics_renderer.py`
- `api/routes/files.py`
- `worker/raw_output_artifacts.py`
- `tests/test_dxf_preflight_normalized_dxf_writer.py`
- `tests/test_dxf_preflight_acceptance_gate.py`
- `tests/test_dxf_preflight_diagnostics_renderer.py`
- `scripts/smoke_dxf_prefilter_e2_t5_normalized_dxf_writer_v1.py`
- `scripts/smoke_dxf_prefilter_e2_t6_acceptance_gate_v1.py`
- `scripts/smoke_dxf_prefilter_e2_t7_diagnostics_and_repair_summary_renderer_v1.py`
- `canvases/web_platform/dxf_prefilter_e2_t5_normalized_dxf_writer_v1.md`
- `canvases/web_platform/dxf_prefilter_e2_t6_acceptance_gate_v1.md`
- `canvases/web_platform/dxf_prefilter_e2_t7_diagnostics_and_repair_summary_renderer_v1.md`
- `canvases/web_platform/dxf_prefilter_e3_t1_preflight_persistence_and_artifact_storage_integration.md`
- `codex/goals/canvases/web_platform/fill_canvas_dxf_prefilter_e3_t1_preflight_persistence_and_artifact_storage_integration.yaml`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosithatsz, ami szerepel valamelyik YAML step `outputs` listajaban.
- A minosegkaput kizarolag wrapperrel futtasd.
- Ez **persistence + artifact storage integration task**. Ne vezess be FastAPI route-ot, request modelt,
  OpenAPI exportot, upload triggert, geometry import gate-et vagy frontend valtoztatast.
- A service ne futtasson uj DXF parse/importer/validator probe-ot; kizarolag a mar eloallt T1->T7 truthot perzisztalja.
- A repo current-code truth szerint nincs implementalt rules-profile domain. Ne implementald most a teljes
  `dxf_rules_profiles` / `dxf_rules_profile_versions` tablakat csak azert, hogy FK legyen a preflight runon.
  Helyette a V1 persistence truth tartalmazzon `rules_profile_snapshot_jsonb`-ot.
- A T7 summary stabilized boundary; ezt persisted truth-va kell tenni, nem ujraepiteni DB-bol vagy ujraszamolni.
- A `preflight_diagnostics` row-k forrasa a T7 `issue_summary.items` legyen, ne egy uj diagnostics generator.
- A T5 `normalized_dxf.output_path` local artifact a canonical storage source. Ha a fajl nincs meg, ne talalj ki uploadot.
- A canonical artifact bucket most `geometry-artifacts`; ne csinalj globalis multi-bucket config refaktort.
- A `preflight_artifacts` implementacio legyen explicit storage-truth: ne rejtsd el a storage bucket/path adatot csak metadata_jsonb-ben.
- A task terminalis local preflight snapshotot perzisztal; nem kell worker/queue/polling lifecycle.

Modellezesi elvek:
- A migration minimalisan hozza be:
  - `app.preflight_runs`
  - `app.preflight_diagnostics`
  - `app.preflight_artifacts`
- A `preflight_runs` minimum tartalmazza:
  - `project_id`
  - `source_file_object_id`
  - `run_seq`
  - `run_status`
  - `acceptance_outcome`
  - `rules_profile_snapshot_jsonb`
  - `summary_jsonb`
  - `source_hash_sha256`
  - `normalized_hash_sha256`
  - timestamp mezok
- A `preflight_artifacts` minimum tartalmazza:
  - `preflight_run_id`
  - `artifact_kind`
  - `storage_bucket`
  - `storage_path`
  - `artifact_hash_sha256`
  - `content_type`
  - `size_bytes`
  - `metadata_jsonb`
- A canonical storage path minimum legyen:
  - `projects/{project_id}/preflight/{preflight_run_id}/{artifact_kind}/{content_hash}.{ext}`
- A service kimenete adjon vissza persisted run summary truth-ot, amelyben a run id, diagnostics count, artifact refs es a persisted summary snapshot is latszik.

Kulon figyelj:
- a T1-ben ne csuszz at T2 trigger scope-ba es ne modositsd a `files.py` finalize flow-t;
- a T1-ben ne csuszz at T3 geometry import gate scope-ba;
- a T1-ben ne csuszz at artifact list/url route scope-ba;
- ha a docs-level E1-T5 modellhez kepest explicit storage oszlop kell a `preflight_artifacts` tablaba, ezt tedd meg,
  de a reportban nevezd meg a current-code indokot;
- ha a rules-profile FK domaint most nem implementalod, ezt a reportban kulon nevezd meg mint tudatos boundary;
- a smoke es unit teszt legyen deterministic, fake Supabase gateway-jel.

A reportban kulon nevezd meg:
- hogyan lesz a T7 summary persisted truth-va;
- hogyan keletkeznek a `preflight_diagnostics` row-k a T7 issue summary-bol;
- hogyan epul a canonical storage path es miert a `geometry-artifacts` bucket a helyes;
- miert nem implemental teljes rules-profile domaint a task;
- hogyan sharpeneli a task a `preflight_artifacts` storage-truthot az E1-T5 docs-level modellhez kepest;
- hogyan bizonyitja a tesztcsomag az accepted / review-required / rejected flow-kat;
- mi marad kifejezetten E3-T2 / E3-T3 / kesobbi API/UI scope-ban.

A vegen futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e3_t1_preflight_persistence_and_artifact_storage_integration.md`

Eredmeny:
- Frissitsd a checklistet es a reportot evidence alapon.
- A reportban legyen DoD -> Evidence Matrix.
- Add meg a vegleges fajltartalmakat.
