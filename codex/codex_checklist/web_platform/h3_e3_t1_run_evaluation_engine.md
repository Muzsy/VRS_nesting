# H3-E3-T1 Run evaluation engine — Checklist

## Alap
- [x] Relevans fajlok azonositva (felderites)
- [x] Canvas elkeszult (kockazat + rollback + DoD)
- [x] YAML steps + outputs pontos (outputs szabaly betartva)

## DoD
- [x] Letrejott az `app.run_evaluations` persisted truth reteg.
- [x] Az evaluation egy runhoz reprodukalhato `total_score`-t tud kepezni.
- [x] A score komponensekre bontva, indokolhatoan kerul az `evaluation_jsonb`-be.
- [x] Az engine explicit `scoring_profile_version_id` alapu kontraktussal mukodik.
- [x] Optionalis project-level scoring selection fallback dokumentalt es ellenorzott.
- [x] Csak a mar letezo H1/H2 persisted metrikakra epul score-komponens.
- [x] A meg nem letezo H3 jelek nem kerulnek kitalalasra; unsupported/not_applied allapotban latszanak.
- [x] A threshold eredmenyek es tie-breaker inputok elerhetok, de ranking nem keszul.
- [x] Az evaluation write viselkedese run-szintu idempotens replace.
- [x] A task nem nyul a H1/H2 truth tablakhoz es nem csuszik at ranking/comparison scope-ba.
- [x] Keszult dedikalt service, route es task-specifikus smoke script.
- [x] Checklist es report evidence-alapon ki van toltve.
- [x] `./scripts/verify.sh --report codex/reports/web_platform/h3_e3_t1_run_evaluation_engine.md` PASS.
