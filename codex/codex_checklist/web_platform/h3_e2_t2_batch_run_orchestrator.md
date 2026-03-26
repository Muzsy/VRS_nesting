# H3-E2-T2 Batch run orchestrator — Checklist

## Alap
- [x] Relevans fajlok azonositva (felderites)
- [x] Canvas elkeszult (kockazat + rollback + DoD)
- [x] YAML steps + outputs pontos (outputs szabaly betartva)

## DoD
- [x] Keszult dedikalt `api/services/run_batch_orchestrator.py` service.
- [x] Az orchestrator a canonical H1 run create flow-t reuse-olja (`create_queued_run_from_project_snapshot`).
- [x] Egy batchhez tobb candidate queued run kezeles implementalt.
- [x] A keletkezo runok batch-itemkent vissza vannak kotve.
- [x] A `candidate_label` es strategy/scoring kontextus batch-item szinten tarolodik.
- [x] A strategy/scoring owner-scope validacio eros es explicit.
- [x] Dokumentalt fail-fast szemantika mukodik best-effort rollbackkel.
- [x] A task nem csuszik at evaluation/ranking/comparison/review scope-ba.
- [x] Keszult task-specifikus smoke script.
- [x] Checklist es report evidence-alapon frissitve.
- [x] `./scripts/verify.sh --report codex/reports/web_platform/h3_e2_t2_batch_run_orchestrator.md` PASS.
