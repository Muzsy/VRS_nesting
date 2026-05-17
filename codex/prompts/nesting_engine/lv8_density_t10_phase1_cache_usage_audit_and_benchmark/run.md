# Runner — lv8_density_t10_phase1_cache_usage_audit_and_benchmark

## Feladat

Végrehajtandó task: **T10 — Phase 1 cache usage audit and benchmark**.

Ez Phase 1 záró benchmark/audit task. A T08 cache stats hardening és T09 cache-key invariant verification után a cél az, hogy a meglévő LV8 harnessből valós futási cache statokat gyűjtsünk, kimondjuk az LRU szükségességét vagy hiányát, és eldöntsük, hogy a Phase 2a bbox-growth scoring indulhat-e.

## Kötelező források

Olvasd el először:

```text
AGENTS.md
docs/codex/overview.md
docs/codex/yaml_schema.md
docs/codex/report_standard.md
docs/qa/testing_guidelines.md
canvases/nesting_engine/lv8_density_task_index.md
codex/prompts/nesting_engine/lv8_density_master_runner.md
canvases/nesting_engine/lv8_density_t10_phase1_cache_usage_audit_and_benchmark.md
codex/goals/canvases/nesting_engine/fill_canvas_lv8_density_t10_phase1_cache_usage_audit_and_benchmark.yaml
codex/reports/nesting_engine/lv8_density_t08_phase1_cache_stats_hardening.md
codex/reports/nesting_engine/lv8_density_t09_phase1_shape_id_cache_key_verification.md
```

T08/T09 státusz PASS vagy PASS_WITH_NOTES lehet. Ha T09 nem `pipeline_version_required: NO` döntéssel zárult, T10 ne menjen benchmarkra; készíts BLOCKED reportot.

## Scope

Elsődlegesen új script + teszt + report készül.

Engedélyezett fájlok:

```text
scripts/experiments/lv8_phase1_cache_usage_matrix.py
tests/test_lv8_phase1_cache_usage_matrix.py
codex/codex_checklist/nesting_engine/lv8_density_t10_phase1_cache_usage_audit_and_benchmark.md
codex/reports/nesting_engine/lv8_density_t10_phase1_cache_usage_audit_and_benchmark.md
codex/reports/nesting_engine/lv8_density_t10_phase1_cache_usage_audit_and_benchmark.verify.log
codex/reports/nesting_engine/lv8_phase1_cache_usage_result.md
```

Benchmark output:

```text
tmp/lv8_density_phase1_cache_usage/cache_usage_matrix.json
tmp/lv8_density_phase1_cache_usage/cache_usage_matrix.md
tmp/lv8_density_phase1_cache_usage/runs.jsonl
```

Csak konkrét cache-bypass hiba esetén módosítható:

```text
rust/nesting_engine/src/placement/nfp_placer.rs
rust/nesting_engine/src/multi_bin/greedy.rs
scripts/experiments/lv8_2sheet_claude_search.py
```

Tilos:

```text
- LRU implementáció
- cache-key módosítás
- candidate scoring / lookahead / beam / LNS módosítás
- SA hard-cut
- quality_default / quality_aggressive átírása no-SA-ra
- search/sa.rs módosítása
- kötelező 600s LV8 benchmark a verify alatt
```

## Végrehajtási lépések

### 1) Előfeltétel ellenőrzés

```bash
python3 - <<'PY'
from pathlib import Path
for name in [
    'codex/reports/nesting_engine/lv8_density_t08_phase1_cache_stats_hardening.md',
    'codex/reports/nesting_engine/lv8_density_t09_phase1_shape_id_cache_key_verification.md',
]:
    p = Path(name)
    print(name, 'OK' if p.is_file() else 'MISSING')
    if p.is_file():
        text = p.read_text(encoding='utf-8', errors='replace')
        print('\n'.join(text.splitlines()[:40]))
PY
```

Ellenőrizd kézzel is:

```text
T08: PASS vagy PASS_WITH_NOTES
T09: PASS vagy PASS_WITH_NOTES
T09: pipeline_version_required: NO
T09: production_cache_key_changed: false
```

### 2) Matrix script elkészítése

Hozd létre:

```text
scripts/experiments/lv8_phase1_cache_usage_matrix.py
```

Követelmények:

- Használja a meglévő `scripts/experiments/lv8_2sheet_claude_search.py` harness-t subprocessként, ne duplikálja a solver futtatását.
- CLI:

```text
--out-root
--time-limit-sec
--seed
--include-lv8-179 auto|0|1
--profiles comma-separated list
```

- Default profilok:

```text
quality_default_no_sa_shadow,quality_aggressive_no_sa_shadow
```

- Kötelező fixture-ek:

```text
tests/fixtures/nesting_engine/ne2_input_lv8jav.json
poc/nesting_engine/f2_4_sa_quality_fixture_v2.json
```

- Opcionális fixture:

```text
tmp/lv8_singlesheet_etalon_20260514/inputs/lv8_sheet1_179.json
```

- Outputok:

```text
<out-root>/cache_usage_matrix.json
<out-root>/cache_usage_matrix.md
<out-root>/runs.jsonl
```

A matrix JSON minden runra tartalmazza legalább:

```text
family_id
fixture_path
quality_profile
summary_path
engine_stats_available
nfp_cache_hit_count
nfp_cache_miss_count
nfp_cache_entries_end
nfp_cache_clear_all_events
nfp_cache_peak_entries
nfp_compute_count
cache_total_lookups
cache_hit_rate
valid_polygon_gate
valid_quantity_gate
valid
placed_instances
utilization_pct
runtime_sec
```

A top-level döntések:

```text
phase2a_ready: true|false
lru_followup_required: true|false
cache_stats_available_all_required_runs: true|false
polygon_gate_available_all_required_runs: true|false
```

### 3) Unit teszt

Hozd létre:

```text
tests/test_lv8_phase1_cache_usage_matrix.py
```

Ne futtass hosszú engine benchmarkot unit tesztben. Tesztelj mockolt summary-k alapján:

```text
- hit-rate számítás: hits/(hits+misses)
- zero lookup eset: hit_rate null/None
- missing optional lv8_179 fixture: fixture_missing row, nem failure
- missing required fixture: status BLOCKED / exit 2
- engine_stats.available false: exit 3 / not phase2a_ready
- clear_all_events > 0: lru_followup_required true
- valid_polygon_gate missing/false: polygon_gate_available false vagy row warning
```

### 4) Célzott ellenőrzések

```bash
python3 -m py_compile scripts/experiments/lv8_phase1_cache_usage_matrix.py
python3 -m pytest tests/test_lv8_phase1_cache_usage_matrix.py
```

### 5) Smoke benchmark

A release binary szükséges a meglévő harnesshez. Ha hiányzik, építsd a repo meglévő mintája szerint. Ezután futtasd:

```bash
python3 scripts/experiments/lv8_phase1_cache_usage_matrix.py \
  --out-root tmp/lv8_density_phase1_cache_usage \
  --time-limit-sec 60 \
  --seed 42 \
  --include-lv8-179 auto \
  --profiles quality_default_no_sa_shadow,quality_aggressive_no_sa_shadow
```

Ha a környezet nem alkalmas engine benchmark futtatására, készíts `BLOCKED` reportot. Ne gyárts fake benchmark eredményt.

### 6) Reportok

Készítsd el:

```text
codex/reports/nesting_engine/lv8_phase1_cache_usage_result.md
codex/codex_checklist/nesting_engine/lv8_density_t10_phase1_cache_usage_audit_and_benchmark.md
codex/reports/nesting_engine/lv8_density_t10_phase1_cache_usage_audit_and_benchmark.md
```

A T10 report végén legyen explicit:

```text
phase2a_ready: YES | NO | DEFERRED
lru_followup_required: YES | NO
cache_stats_available_all_required_runs: YES | NO
polygon_gate_available_all_required_runs: YES | NO
next_task_recommendation: T11 indulhat | LRU follow-up kell | benchmark blocker javítandó
```

### 7) Repo gate

Futtasd:

```bash
./scripts/verify.sh --report codex/reports/nesting_engine/lv8_density_t10_phase1_cache_usage_audit_and_benchmark.md
```

A végén a report státusza legyen PASS vagy PASS_WITH_NOTES. FAIL/BLOCKED csak konkrét dokumentált blocker esetén elfogadható.

## Kimeneti elvárás

A task végén röviden add meg:

```text
status: PASS | PASS_WITH_NOTES | FAIL | BLOCKED
phase2a_ready: YES | NO | DEFERRED
lru_followup_required: YES | NO
cache_stats_available_all_required_runs: YES | NO
polygon_gate_available_all_required_runs: YES | NO
new_script: scripts/experiments/lv8_phase1_cache_usage_matrix.py
new_tests: tests/test_lv8_phase1_cache_usage_matrix.py
verify: PASS | FAIL
next_task_recommendation: T11 indulhat / follow-up kell
```
