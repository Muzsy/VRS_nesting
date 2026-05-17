# T10 Checklist — lv8_density_t10_phase1_cache_usage_audit_and_benchmark

- [x] Kötelező források beolvasva (`AGENTS.md`, Codex/QA szabályok, T10 canvas/YAML/runner, T08/T09 report).
- [x] Előfeltételek ellenőrizve: T08 `PASS`, T09 `PASS`, `pipeline_version_required: NO`, `production_cache_key_changed: false`.
- [x] Új script létrehozva: `scripts/experiments/lv8_phase1_cache_usage_matrix.py`.
- [x] Új unit teszt létrehozva: `tests/test_lv8_phase1_cache_usage_matrix.py`.
- [x] Célzott ellenőrzések lefuttatva:
  - `python3 -m py_compile scripts/experiments/lv8_phase1_cache_usage_matrix.py`
  - `python3 -m pytest tests/test_lv8_phase1_cache_usage_matrix.py`
- [x] Smoke benchmark futtatva a T10 runner szerinti paraméterekkel.
- [x] Benchmark outputok elkészültek:
  - `tmp/lv8_density_phase1_cache_usage/cache_usage_matrix.json`
  - `tmp/lv8_density_phase1_cache_usage/cache_usage_matrix.md`
  - `tmp/lv8_density_phase1_cache_usage/runs.jsonl`
- [x] Phase 1 eredményriport elkészült: `codex/reports/nesting_engine/lv8_phase1_cache_usage_result.md`.
- [x] T10 report kitöltve explicit decision mezőkkel.
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/lv8_density_t10_phase1_cache_usage_audit_and_benchmark.md` futtatása.
