# H3-E3-T3 Best-by-objective lekerdezesek — Checklist

## Alap
- [x] Relevans fajlok azonositva (felderites)
- [x] Canvas elkeszult (kockazat + rollback + DoD)
- [x] YAML steps + outputs pontos (outputs szabaly betartva)

## DoD
- [x] Keszult dedikalt best-by-objective service reteg.
- [x] Keszult dedikalt best-by-objective route.
- [x] A route be van kotve az `api/main.py`-ba.
- [x] A task nem vezet be uj persisted comparison truth tablat.
- [x] A query a mar letezo persisted ranking/evaluation/metrics truthra epul.
- [x] `material-best` lekerdezheto valos metric orderinggel.
- [x] `time-best` lekerdezheto valos manufacturing timing orderinggel.
- [x] `priority-best` lekerdezheto read-side projectionkent snapshot + unplaced truth alapjan.
- [x] `cost-best` expliciten kezelt, de nem kitalalt uzleti koltsegformula.
- [x] A projection payload auditálhato objective reason-t ad.
- [x] A task nem ir `run_evaluations`, `run_ranking_results`, `project_selected_runs` vagy `run_business_metrics` tablaba.
- [x] Keszult task-specifikus smoke script.
- [x] Checklist es report evidence-alapon ki van toltve.
- [x] `./scripts/verify.sh --report codex/reports/web_platform/h3_e3_t3_best_by_objective_lekerdezesek.md` PASS.
