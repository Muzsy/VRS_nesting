# Codex checklist - dxf_prefilter_e3_t5_feature_flag_and_rollout_gate

- [x] Canvas + goal YAML + run prompt artefaktok elérhetők
- [x] `Settings` kap `dxf_preflight_required: bool` mezőt a `api/config.py`-ban
- [x] `API_DXF_PREFLIGHT_REQUIRED` env var (alias: `DXF_PREFLIGHT_REQUIRED`) helyesen parse-olódik bool-ként
- [x] `complete_upload` flag ON esetén validate + preflight runtime taskot regisztrál
- [x] `complete_upload` flag OFF esetén validate + `import_source_dxf_geometry_revision_async` taskot regisztrál
- [x] `replace_file` route flag OFF esetén HTTP 409-et dob (nem nyit replacement upload slotot)
- [x] `frontend/src/lib/featureFlags.ts` létrejött `DXF_PREFLIGHT_ENABLED` build-time gate-tel
- [x] `App.tsx` DXF Intake route csak `DXF_PREFLIGHT_ENABLED` esetén van regisztrálva
- [x] `ProjectDetailPage.tsx` DXF Intake CTA csak `DXF_PREFLIGHT_ENABLED` esetén látszik
- [x] Elkészült a task-specifikus unit teszt (`tests/test_dxf_preflight_feature_flag_gate.py`)
- [x] Elkészült a task-specifikus smoke (`scripts/smoke_dxf_prefilter_e3_t5_feature_flag_and_rollout_gate.py`)
- [x] `python3 -m pytest tests/test_dxf_preflight_feature_flag_gate.py -v` OK — 22 passed
- [x] `python3 scripts/smoke_dxf_prefilter_e3_t5_feature_flag_and_rollout_gate.py` OK — ALL SCENARIOS PASSED
- [x] `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e3_t5_feature_flag_and_rollout_gate.md` PASS
