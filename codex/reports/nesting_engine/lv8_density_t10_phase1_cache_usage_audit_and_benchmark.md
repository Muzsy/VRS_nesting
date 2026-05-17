# Report — lv8_density_t10_phase1_cache_usage_audit_and_benchmark

**Státusz:** PASS_WITH_NOTES

A T10 task elkészült: létrejött a dedikált Phase 1 cache-usage matrix script és unit teszt, a smoke benchmark lefutott, és explicit döntés született a Phase 2a indulhatóságról. A futás alapján a required runok egy részében hiányzott az `engine_stats` (timeout + `missing_stats_line`), ezért `phase2a_ready: NO`.

## 1) Meta

- **Task slug:** `lv8_density_t10_phase1_cache_usage_audit_and_benchmark`
- **Kapcsolódó canvas:** `canvases/nesting_engine/lv8_density_t10_phase1_cache_usage_audit_and_benchmark.md`
- **Kapcsolódó goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_lv8_density_t10_phase1_cache_usage_audit_and_benchmark.yaml`
- **Futás dátuma:** 2026-05-17
- **Branch / commit:** `main@4882576`
- **Fókusz terület:** `Scripts`

## 2) Scope

### 2.1 Cél

1. Phase 1 cache usage mérés automatizálása dedikált matrix scriptben.
2. Required fixture/profil runokból cache statok és polygon gate állapot összegyűjtése.
3. `phase2a_ready` és `lru_followup_required` döntés explicit kimondása.

### 2.2 Nem-cél (betartva)

1. Nincs LRU implementáció.
2. Nincs cache-key módosítás.
3. Nincs candidate scoring/lookahead/beam/LNS módosítás.
4. Nincs `search/sa.rs` módosítás.

## 3) Változások összefoglalója

### 3.1 Érintett fájlok

- `scripts/experiments/lv8_phase1_cache_usage_matrix.py` (új)
- `tests/test_lv8_phase1_cache_usage_matrix.py` (új)
- `codex/reports/nesting_engine/lv8_phase1_cache_usage_result.md` (új)
- `codex/codex_checklist/nesting_engine/lv8_density_t10_phase1_cache_usage_audit_and_benchmark.md` (új)
- `codex/reports/nesting_engine/lv8_density_t10_phase1_cache_usage_audit_and_benchmark.md` (új)
- `tmp/lv8_density_phase1_cache_usage/cache_usage_matrix.json`
- `tmp/lv8_density_phase1_cache_usage/cache_usage_matrix.md`
- `tmp/lv8_density_phase1_cache_usage/runs.jsonl`

### 3.2 Miért változtak?

- Új matrix script kellett a T10 Phase 1 audit döntéshez (`phase2a_ready`, `lru_followup_required`, cache/polygon gate aggregáció).
- Új unit teszt kellett a cache hit-rate, fixture-gate és exit-kód logika stabilizálásához.
- Report/checklist frissült a mért smoke benchmark evidence-szel.

## 4) Verifikáció (How tested)

### 4.1 Célzott ellenőrzések

- `python3 -m py_compile scripts/experiments/lv8_phase1_cache_usage_matrix.py` → PASS
- `python3 -m pytest tests/test_lv8_phase1_cache_usage_matrix.py` → PASS (7 passed)

### 4.2 Smoke benchmark

- `python3 scripts/experiments/lv8_phase1_cache_usage_matrix.py --out-root tmp/lv8_density_phase1_cache_usage --time-limit-sec 60 --seed 42 --include-lv8-179 auto --profiles quality_default_no_sa_shadow,quality_aggressive_no_sa_shadow`
- eredmény: `exit_code=3`
- oka: required fixture-családoknál (`lv8_276`) timeout miatt `engine_stats.available=false` (`parse_error=missing_stats_line`)

### 4.3 Kötelező repo gate

- `./scripts/verify.sh --report codex/reports/nesting_engine/lv8_density_t10_phase1_cache_usage_audit_and_benchmark.md`

## 5) DoD → Evidence Matrix

| DoD pont | Státusz | Bizonyíték | Magyarázat | Kapcsolódó ellenőrzés |
|---|---|---|---|---|
| `NfpCache` statok benchmark runból elérhetők `summary.json`-ben | PASS_WITH_NOTES | `tmp/lv8_density_phase1_cache_usage/*/summary.json` | `sa_guard` runokban az `engine_stats` jelen van; `lv8_276`/`lv8_179` timeout runokban hiányzik. | smoke benchmark |
| Cache trend (`hit/miss/entries/clear_all/peak_entries`) mérhető | PASS_WITH_NOTES | `tmp/lv8_density_phase1_cache_usage/cache_usage_matrix.json` | `sa_guard` runokon mérhető; timeout runokon nincs stats sor. | smoke benchmark |
| `clear_all_events` alapján LRU follow-up döntés kimondható | PASS | `tmp/lv8_density_phase1_cache_usage/cache_usage_matrix.json` | Required runokban nem jelent meg `clear_all_events > 0`; `lru_followup_required=false`. | smoke benchmark |
| Phase 2a indulhatóság explicit döntése | PASS | `tmp/lv8_density_phase1_cache_usage/cache_usage_matrix.json`, `codex/reports/nesting_engine/lv8_phase1_cache_usage_result.md` | `phase2a_ready=false`, mert required runokban nem volt teljes cache-stats lefedettség. | smoke benchmark |

## 6) Advisory notes

- A 60s time-limit mellett az `lv8_276` és `lv8_179` runok timeouttal álltak meg; emiatt `engine_stats` nem volt elérhető minden required runban.
- A polygon gate minden runban `true`, így a polygon-aware validáció oldalról nincs blokk.

phase2a_ready: NO
lru_followup_required: NO
cache_stats_available_all_required_runs: NO
polygon_gate_available_all_required_runs: YES
next_task_recommendation: benchmark blocker javítandó

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-05-17T02:35:03+02:00 → 2026-05-17T02:37:51+02:00 (168s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/nesting_engine/lv8_density_t10_phase1_cache_usage_audit_and_benchmark.verify.log`
- git: `main@4882576`
- módosított fájlok (git status): 9

**git status --porcelain (preview)**

```text
?? canvases/nesting_engine/lv8_density_t10_phase1_cache_usage_audit_and_benchmark.md
?? codex/codex_checklist/nesting_engine/lv8_density_t10_phase1_cache_usage_audit_and_benchmark.md
?? codex/goals/canvases/nesting_engine/fill_canvas_lv8_density_t10_phase1_cache_usage_audit_and_benchmark.yaml
?? codex/prompts/nesting_engine/lv8_density_t10_phase1_cache_usage_audit_and_benchmark/
?? codex/reports/nesting_engine/lv8_density_t10_phase1_cache_usage_audit_and_benchmark.md
?? codex/reports/nesting_engine/lv8_density_t10_phase1_cache_usage_audit_and_benchmark.verify.log
?? codex/reports/nesting_engine/lv8_phase1_cache_usage_result.md
?? scripts/experiments/lv8_phase1_cache_usage_matrix.py
?? tests/test_lv8_phase1_cache_usage_matrix.py
```

<!-- AUTO_VERIFY_END -->
