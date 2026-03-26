# H3-E3-T2 Ranking engine — Checklist

## Alap
- [x] Relevans fajlok azonositva (felderites)
- [x] Canvas elkeszult (kockazat + rollback + DoD)
- [x] YAML steps + outputs pontos (outputs szabaly betartva)

## DoD
- [x] Letrejott az `app.run_ranking_results` persisted truth reteg.
- [x] Egy batch candidate-halmazahoz reprodukalhato ranking kepezheto.
- [x] A ranking kizarolag a mar persisted batch + evaluation truthra epul.
- [x] Hianyzo evaluation eseten a task nem gyart reszleges sorrendet.
- [x] A batch-item scoring context es az evaluation scoring context konzisztenciaja ellenorzott.
- [x] Azonos `total_score` eseten deterministic tie-break logika ervenyesul.
- [x] A `ranking_reason_jsonb` auditálhato indoklast es tie-break trace-et tarol.
- [x] Keszult minimalis POST / GET (es ha kell DELETE) ranking backend contract.
- [x] A task nem csuszik at comparison / selected-run / business-metrics scope-ba.
- [x] Keszult task-specifikus smoke script.
- [x] Checklist es report evidence-alapon frissitve.
- [x] `./scripts/verify.sh --report codex/reports/web_platform/h3_e3_t2_ranking_engine.md` PASS.
