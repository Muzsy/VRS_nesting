# Codex checklist - dxf_prefilter_e2_t7_diagnostics_and_repair_summary_renderer_v1

- [x] Canvas + goal YAML + run prompt + checklist + report artefaktok elerhetoek
- [x] Letrejott kulon backend diagnostics renderer service: `api/services/dxf_preflight_diagnostics_renderer.py`
- [x] A service T1->T6 output shape-eket aggregal egyetlen deterministic summary objektumba
- [x] A summary kulon retegekben adja: source inventory, role mapping, issue, repair, acceptance, artifact references
- [x] Az issue-normalizalas explicit `severity/source/family/code/message/details` mezokkel tortenik
- [x] A repair summary kulon tartja az applied gap repair, applied duplicate dedupe, skipped source entities, remaining unresolved jeleket
- [x] Az artifact references local backend reference marad (`artifact_kind`, `path`, `exists`, `download_label`)
- [x] A task nem nyitotta meg a persistence / route / upload trigger / UI scope-ot
- [x] Keszult task-specifikus unit teszt csomag (`tests/test_dxf_preflight_diagnostics_renderer.py`)
- [x] Keszult task-specifikus smoke script (`scripts/smoke_dxf_prefilter_e2_t7_diagnostics_and_repair_summary_renderer_v1.py`)
- [x] Checklist es report evidence alapon frissitve
- [x] `./scripts/verify.sh --report codex/reports/web_platform/dxf_prefilter_e2_t7_diagnostics_and_repair_summary_renderer_v1.md` PASS
