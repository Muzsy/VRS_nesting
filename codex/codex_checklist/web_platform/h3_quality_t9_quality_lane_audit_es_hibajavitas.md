# Codex checklist - h3_quality_t9_quality_lane_audit_es_hibajavitas

- [x] Canvas + goal YAML + run prompt artefaktok elerhetoek
- [x] `vrs_nesting/runner/nesting_engine_runner.py` parser kezeli a `--compaction off|slide` flaget
- [x] A runner `main()` tovabbitja a `--compaction` flaget a `nesting_engine_cli_args` listaban
- [x] A `run_nesting_engine()` tovabbra is az altalanos `extra_cli_args` uton kapja a flaget (nincs kulon special-case)
- [x] A T1 smoke backend-agnosztikus `engine_meta` truthot ellenoriz, stale literal nelkul
- [x] Letrejott az uj T9 closure-fix smoke: `scripts/smoke_h3_quality_t9_quality_lane_audit_es_hibajavitas.py`
- [x] A T9 smoke bizonyitja a parser+arg-forward fixet, a T1 smoke zold allapotat, es a T1/T6 outputs/report konzisztenciat
- [x] `scripts/check.sh` futtatja az uj T9 smoke-ot
- [x] T1 historical drift rendezve (YAML/report outputs konzisztens)
- [x] T6 historical drift rendezve (YAML/report outputs konzisztens)
- [x] Feladat-specifikus minimum ellenorzesek lefutottak
- [x] `./scripts/verify.sh --report codex/reports/web_platform/h3_quality_t9_quality_lane_audit_es_hibajavitas.md` lefutott
- [x] Report DoD -> Evidence Matrix kitoltve
