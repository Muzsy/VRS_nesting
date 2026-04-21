# Codex checklist - dxf_prefilter_e3_t1_preflight_persistence_and_artifact_storage_integration

- [x] Canvas + goal YAML + run prompt artefaktok elérhetőek
- [x] Minimális migration létrejött: `app.preflight_runs`, `app.preflight_diagnostics`, `app.preflight_artifacts` táblák RLS-szel
- [x] A migration nem követel meg azonnali `dxf_rules_profiles` / `dxf_rules_profile_versions` FK domaint; `rules_profile_snapshot_jsonb` JSONB snapshot-ot használ helyette
- [x] A `preflight_artifacts` tábla explicit storage truth-ot tartalmaz: `storage_bucket`, `storage_path`, `artifact_hash_sha256`, `content_type`, `size_bytes`, `metadata_jsonb`
- [x] Létrejött kulon backend persistence service: `api/services/dxf_preflight_persistence.py`
- [x] A service a T7 summary snapshot-ot `summary_jsonb`-ban menti; nem újraszámolja
- [x] A T7 `issue_summary.normalized_issues` lista alapján `preflight_diagnostics` row-k keletkeznek (egy sor / normalized issue)
- [x] A T5 normalized DXF local artifact a `geometry-artifacts` bucketbe kerül canonical content-addressed storage path-ra
- [x] A canonical storage path mintája: `projects/{project_id}/preflight/{preflight_run_id}/{artifact_kind}/{content_hash}.{ext}`
- [x] A service nem futtat új DXF parse / importer / validator probe-ot
- [x] A service nem hoz létre FastAPI route-ot, request model-t, OpenAPI exportot, trigger-t vagy acceptance gate-et
- [x] Készült task-specifikus unit teszt (`tests/test_dxf_preflight_persistence.py`, 24 teszt) és smoke script (`scripts/smoke_dxf_prefilter_e3_t1_preflight_persistence_and_artifact_storage_integration.py`, 8 scenario)
- [x] A tesztek determinisztikusak, fake DB/storage gateway-jel (nincs valós Supabase-hívás)
- [x] A checklist és report evidence-alapon frissült (DoD -> Evidence Matrix)
- [x] `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e3_t1_preflight_persistence_and_artifact_storage_integration.md` PASS (check.sh exit 0, 184s, `main@32d36ad`; lasd a report AUTO_VERIFY blokkot es `.verify.log` fajlt)
