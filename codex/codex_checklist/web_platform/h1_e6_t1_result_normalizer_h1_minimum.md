# Codex checklist - h1_e6_t1_result_normalizer_h1_minimum

- [x] Canvas + goal YAML + run prompt artefaktok elerhetoek
- [x] Keszult explicit worker-oldali result normalizer helper: `worker/result_normalizer.py`
- [x] A normalizer a snapshot manifest truth alapjan oldja fel a part/sheet mappinget
- [x] A `run_layout_sheets` projection hasznalt sheetenkent keszul
- [x] A `run_layout_placements` projection deterministic `transform_jsonb` + `bbox_jsonb` sorokat ad
- [x] A `run_layout_unplaced` aggregalt `remaining_qty` szemantikaval keszul
- [x] A `run_metrics` counts/utilization ertekek determinisztikusan szamolodnak
- [x] A projection write run-szintu idempotens replace (`delete + insert/upsert`) viselkedest ad
- [x] A worker `done` zarasa mar a normalizer summary-bol jon
- [x] A task scope nem nyitott viewer/export vagy nagy runs API redesign iranyba
- [x] Letrejott task-specifikus smoke: `scripts/smoke_h1_e6_t1_result_normalizer_h1_minimum.py`
- [x] `python3 -m py_compile worker/main.py worker/result_normalizer.py worker/engine_adapter_input.py worker/raw_output_artifacts.py scripts/smoke_h1_e6_t1_result_normalizer_h1_minimum.py` PASS
- [x] `python3 scripts/smoke_h1_e6_t1_result_normalizer_h1_minimum.py` PASS
- [x] `./scripts/verify.sh --report codex/reports/web_platform/h1_e6_t1_result_normalizer_h1_minimum.md` PASS
- [x] Report DoD -> Evidence matrix kitoltve
