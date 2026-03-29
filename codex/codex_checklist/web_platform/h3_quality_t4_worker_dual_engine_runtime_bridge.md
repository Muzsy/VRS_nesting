# Codex checklist - h3_quality_t4_worker_dual_engine_runtime_bridge

- [x] Canvas + goal YAML + run prompt artefaktok elerhetoek
- [x] Keszult explicit worker backend selector (`WORKER_ENGINE_BACKEND`) `sparrow_v1` defaulttal es `nesting_engine_v2` alternativaval
- [x] A worker backend alapjan valaszt input builder/hash helpert es runner modult
- [x] A canonical `solver_input` artifact es az `engine_meta.json` backend-aware truthot ir
- [x] A raw artifact persist megtartja a `nesting_output.json` v2 kimenetet
- [x] A result normalizer kapott explicit v2 agat, a v1 ag megmaradt
- [x] Keszult task-specifikus smoke script: `scripts/smoke_h3_quality_t4_worker_dual_engine_runtime_bridge.py`
- [x] `python3 -m py_compile worker/main.py worker/engine_adapter_input.py worker/raw_output_artifacts.py worker/result_normalizer.py scripts/smoke_h3_quality_t4_worker_dual_engine_runtime_bridge.py` PASS
- [x] `python3 scripts/smoke_h3_quality_t4_worker_dual_engine_runtime_bridge.py` PASS
- [x] `./scripts/verify.sh --report codex/reports/web_platform/h3_quality_t4_worker_dual_engine_runtime_bridge.md` PASS
- [x] Report DoD -> Evidence matrix kitoltve
