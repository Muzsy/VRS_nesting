# Runner — lv8_density_t10b_phase1_cache_stats_timeout_blocker

## Feladat

Végrehajtandó task: **T10B — Phase 1 cache stats timeout blocker fix**.

A T10 task zöld repo gate-tel zárult, de a saját döntési mezői szerint a Phase 2a nem indítható:

```text
phase2a_ready: NO
cache_stats_available_all_required_runs: NO
next_task_recommendation: benchmark blocker javítandó
```

A T10B célja ennek a konkrét blockernek a javítása vagy döntésképes dokumentálása. Ne kezdj T11 bbox-growth scoring fejlesztésbe.

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
canvases/nesting_engine/lv8_density_t10b_phase1_cache_stats_timeout_blocker.md
codex/goals/canvases/nesting_engine/fill_canvas_lv8_density_t10b_phase1_cache_stats_timeout_blocker.yaml
codex/reports/nesting_engine/lv8_density_t10_phase1_cache_usage_audit_and_benchmark.md
codex/reports/nesting_engine/lv8_phase1_cache_usage_result.md
scripts/experiments/lv8_phase1_cache_usage_matrix.py
scripts/experiments/lv8_2sheet_claude_search.py
```

## Scope

Engedélyezett fájlok:

```text
scripts/experiments/lv8_phase1_cache_usage_matrix.py
tests/test_lv8_phase1_cache_usage_matrix.py
codex/codex_checklist/nesting_engine/lv8_density_t10b_phase1_cache_stats_timeout_blocker.md
codex/reports/nesting_engine/lv8_density_t10b_phase1_cache_stats_timeout_blocker.md
codex/reports/nesting_engine/lv8_density_t10b_phase1_cache_stats_timeout_blocker.verify.log
codex/reports/nesting_engine/lv8_phase1_cache_usage_result.md
```

Feltételesen módosítható, csak ha indokolt:

```text
scripts/experiments/lv8_2sheet_claude_search.py
```

Tilos:

```text
- Rust production engine módosítás
- NFP cache-key módosítás
- LRU implementáció
- Candidate scoring / bbox-growth bevezetése
- Lookahead / beam / LNS módosítás
- SA hard-cut
- quality_default / quality_aggressive átírása no-SA-ra
- fake benchmark eredmény gyártása
```

## Végrehajtás

### 1) T10 blocker ellenőrzése

Futtasd:

```bash
python3 - <<'PY'
from pathlib import Path
for p in [
    Path('codex/reports/nesting_engine/lv8_density_t10_phase1_cache_usage_audit_and_benchmark.md'),
    Path('codex/reports/nesting_engine/lv8_phase1_cache_usage_result.md'),
]:
    print('---', p)
    print(p.read_text(encoding='utf-8', errors='replace')[:3000] if p.exists() else 'MISSING')
PY
```

Ha a T10 nem `phase2a_ready: NO` / `cache_stats_available_all_required_runs: NO` / `benchmark blocker javítandó`, készíts `BLOCKED` reportot és állj meg.

### 2) Matrix script javítása

Frissítsd:

```text
scripts/experiments/lv8_phase1_cache_usage_matrix.py
```

Minimum elvárás:

- explicit timeout/missing stats kezelés;
- új döntési mezők:

```text
phase2a_unblocked
phase2a_ready_source
lv8_stats_available
sa_guard_stats_available
```

- külön LV8 time-limit vagy stats-required-family konfiguráció;
- nincs fake stats;
- a missing stats sorok megmaradnak a matrix JSON/MD outputban.

Javasolt CLI:

```text
--lv8-time-limit-sec N
--stats-required-families sa_guard,lv8_276
--allow-lv8-timeout-without-stats 0|1
```

A pontos CLI lehet más, de dokumentáld a reportban.

### 3) Unit tesztek

Frissítsd:

```text
tests/test_lv8_phase1_cache_usage_matrix.py
```

Fedd le:

```text
- külön LV8 time-limit átadás
- stats_required_families döntési logika
- LV8 timeout row nem vész el
- phase2a_unblocked false missing stats esetén
- sa_guard-only vagy mixed readiness forrás dokumentált
- clear_all és hit-rate regresszió változatlan
```

### 4) Célzott ellenőrzések

```bash
python3 -m py_compile scripts/experiments/lv8_phase1_cache_usage_matrix.py
python3 -m pytest tests/test_lv8_phase1_cache_usage_matrix.py
```

### 5) T10B smoke run

Példa parancs, ha az implementált CLI támogatja:

```bash
python3 scripts/experiments/lv8_phase1_cache_usage_matrix.py \
  --out-root tmp/lv8_density_phase1_cache_usage_t10b \
  --time-limit-sec 60 \
  --lv8-time-limit-sec 180 \
  --seed 42 \
  --include-lv8-179 auto \
  --profiles quality_default_no_sa_shadow,quality_aggressive_no_sa_shadow
```

Ha a környezet nem tudja lefuttatni az LV8 hosszabb runokat, ezt ne hamisítsd. Jelöld `PASS_WITH_NOTES` vagy `BLOCKED` státusszal.

### 6) Reportok

Frissítsd:

```text
codex/reports/nesting_engine/lv8_phase1_cache_usage_result.md
```

Hozd létre:

```text
codex/codex_checklist/nesting_engine/lv8_density_t10b_phase1_cache_stats_timeout_blocker.md
codex/reports/nesting_engine/lv8_density_t10b_phase1_cache_stats_timeout_blocker.md
```

A T10B report végén szerepeljen:

```text
phase2a_unblocked: YES | NO
phase2a_ready_source: full_required_stats | smoke_stats_plus_lv8_advisory | blocked | other
lv8_stats_available: YES | NO
sa_guard_stats_available: YES | NO
next_task_recommendation: T11 indulhat | T10B tovább javítandó | long LV8 benchmark szükséges
```

### 7) Repo gate

```bash
./scripts/verify.sh --report codex/reports/nesting_engine/lv8_density_t10b_phase1_cache_stats_timeout_blocker.md
```

## Kimeneti elvárás

A végén adj meg röviden:

```text
status: PASS | PASS_WITH_NOTES | BLOCKED | FAIL
phase2a_unblocked: YES | NO
phase2a_ready_source: ...
lv8_stats_available: YES | NO
sa_guard_stats_available: YES | NO
next_task_recommendation: ...
```
