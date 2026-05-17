# LV8 Density T10 — Phase 1 cache usage audit and benchmark

## 🎯 Funkció

A T10 célja a Phase 1 lezárása: a T07 cache path discovery, T08 cache-stats hardening és T09 cache-key invariant verification után futtatható, mérhető cache-usage auditot és benchmark riportot kell készíteni. A task nem algoritmikus optimalizáció: nem módosít placement sorrendet, nem vezet be scoringot, lookaheadet, beamet vagy LNS-t. A cél az, hogy a Phase 2a előtt legyen egy stabil, polygon-aware validált, engine_stats-alapú baseline.

A T10 végén a következő állításokat kell bizonyítani vagy cáfolni:

```text
1. A NfpCache statok tényleges benchmark runokból elérhetők summary.json-ben.
2. A cache hit/miss/entries/clear_all/peak_entries trend mérhető.
3. LV8 és SA-guard fixture-ön nincs cache clear_all esemény, vagy ha van, LRU follow-up szükséges.
4. A Phase 2a indulhat-e biztonságosan.
```

---

## Előfeltételek

T10 csak T08 és T09 után indulhat.

Kötelező reportok:

```text
codex/reports/nesting_engine/lv8_density_t08_phase1_cache_stats_hardening.md
codex/reports/nesting_engine/lv8_density_t09_phase1_shape_id_cache_key_verification.md
```

Elfogadott státusz:

```text
PASS
PASS_WITH_NOTES
```

A T09 elvárt döntése:

```text
pipeline_version_required: NO
production_cache_key_changed: false
```

Ha T08 vagy T09 hiányzik, FAIL/BLOCKED státuszú, vagy T09 `pipeline_version_required: YES` döntést hozott, ne futtass benchmarkot. Készíts T10 `BLOCKED` reportot és írd le a blokkoló okot.

---

## Valós repo-kiindulópontok

### Benchmark harness

```text
scripts/experiments/lv8_2sheet_claude_search.py
```

A T04/T05/T08 után ez már képes:

- `NESTING_ENGINE_EMIT_NFP_STATS=1` beállításra,
- `NEST_NFP_STATS_V1` stderr JSON parse-olására,
- `engine_stats` blokk írására `summary.json`-be,
- `nfp_cache_clear_all_events` és `nfp_cache_peak_entries` normalizálására,
- polygon-aware validation gate meghívására,
- `valid`, `valid_quantity_gate`, `valid_polygon_gate`, `polygon_validation` mezők írására.

### Phase 0 shadow matrix helper

```text
scripts/experiments/lv8_phase0_shadow_run_matrix.py
```

Ez hasznos mintát ad fixture inventoryra és profile-párok futtatására, de T10-ben külön Phase 1 cache usage matrix script javasolt, mert itt nem SA hard-cut döntés a cél, hanem cache trend riport.

### Fixture-ek

Kötelezően támogatandó:

```text
tests/fixtures/nesting_engine/ne2_input_lv8jav.json
poc/nesting_engine/f2_4_sa_quality_fixture_v2.json
```

Opcionális, ha létezik:

```text
tmp/lv8_singlesheet_etalon_20260514/inputs/lv8_sheet1_179.json
```

A T01/T06 tapasztalat alapján az LV8 179 fixture hiányozhat a zip snapshotból. Ez nem lehet blocker; ilyenkor `fixture_missing` sort kell írni a matrixba.

### Profilok

T02 után léteznek:

```text
quality_default_no_sa_shadow
quality_aggressive_no_sa_shadow
```

T10-ben az elsődleges Phase 1 baseline a no-SA shadow path legyen, mivel a no-SA hard-cut még `DEFER_HARD_CUT`, de a Phase 2 algoritmikus irány no-SA baseline-on fog továbbmenni.

A legacy SA profilok nem T10 fókuszai. Ha összehasonlításként futnak, külön `comparison_only` mezővel kerüljenek a reportba.

---

## Scope

### Engedélyezett fájlok

Új benchmark-matrix script:

```text
scripts/experiments/lv8_phase1_cache_usage_matrix.py
```

Új Python teszt:

```text
tests/test_lv8_phase1_cache_usage_matrix.py
```

Task artefaktok:

```text
codex/codex_checklist/nesting_engine/lv8_density_t10_phase1_cache_usage_audit_and_benchmark.md
codex/reports/nesting_engine/lv8_density_t10_phase1_cache_usage_audit_and_benchmark.md
codex/reports/nesting_engine/lv8_density_t10_phase1_cache_usage_audit_and_benchmark.verify.log
codex/reports/nesting_engine/lv8_phase1_cache_usage_result.md
```

Benchmark output könyvtár:

```text
tmp/lv8_density_phase1_cache_usage/
```

A `tmp/` artefaktok lehetnek helyi futási outputok; ha a zip snapshot nem tartalmazza őket, a reportban akkor is szerepeljen a tartalmuk rövid összefoglalója.

### Csak konkrét cache-bypass hiba esetén módosítható

```text
rust/nesting_engine/src/placement/nfp_placer.rs
rust/nesting_engine/src/multi_bin/greedy.rs
scripts/experiments/lv8_2sheet_claude_search.py
```

Alapértelmezésben T10-nek nem kell production Rust kódot módosítania. A T10 fő outputja script + report + tests.

---

## Nem-célok

T10 nem végezheti el:

- LRU implementáció.
- Cache-key módosítás.
- Candidate scoring / bbox-growth bevezetés.
- Lookahead / beam / LNS módosítás.
- SA hard-cut.
- `quality_default` vagy `quality_aggressive` átírása no-SA-ra.
- `search/sa.rs` módosítása.
- Teljes 600 másodperces LV8 quality benchmark kötelező futtatása a standard verify alatt.

---

## Kötelező új script: `lv8_phase1_cache_usage_matrix.py`

Hozz létre egy új scriptet:

```text
scripts/experiments/lv8_phase1_cache_usage_matrix.py
```

### CLI javaslat

```bash
python3 scripts/experiments/lv8_phase1_cache_usage_matrix.py \
  --out-root tmp/lv8_density_phase1_cache_usage \
  --time-limit-sec 60 \
  --seed 42 \
  --include-lv8-179 auto \
  --profiles quality_default_no_sa_shadow,quality_aggressive_no_sa_shadow
```

### Kötelező működés

A script:

1. Ellenőrzi a fixture-eket:
   - `lv8_276`: kötelező, ha hiányzik → `BLOCKED`.
   - `sa_guard`: kötelező, ha hiányzik → `BLOCKED`.
   - `lv8_179`: opcionális, ha hiányzik → `fixture_missing` row.
2. Profile-onként futtatja a meglévő `lv8_2sheet_claude_search.py` harness-t.
3. Minden run `summary.json`-éből kiolvassa:
   - `engine_stats.available`
   - `engine_stats.normalized.nfp_cache_hit_count`
   - `engine_stats.normalized.nfp_cache_miss_count`
   - `engine_stats.normalized.nfp_cache_entries_end`
   - `engine_stats.normalized.nfp_cache_clear_all_events`
   - `engine_stats.normalized.nfp_cache_peak_entries`
   - `engine_stats.normalized.nfp_compute_count`
   - `valid_polygon_gate`
   - `valid_quantity_gate`
   - `valid`
   - `placed_instances`
   - `utilization_pct`
   - `runtime_sec`
4. Számolja:
   - `cache_total_lookups = hits + misses`
   - `cache_hit_rate = hits / (hits + misses)` ha nevező > 0
   - `clear_all_required_lru_followup = any(clear_all_events > 0)`
5. Kiírja:

```text
tmp/lv8_density_phase1_cache_usage/cache_usage_matrix.json
tmp/lv8_density_phase1_cache_usage/cache_usage_matrix.md
tmp/lv8_density_phase1_cache_usage/runs.jsonl
```

6. A script stdouton tömör JSON-t írjon:

```json
{"status":"PASS","rows":N,"lru_followup_required":false,"phase2a_ready":true}
```

### Exit code szabály

- `0`: script lefutott, nincs BLOCKED állapot.
- `2`: kötelező fixture vagy kötelező stats hiányzik.
- `3`: bármely kötelező runnál `engine_stats.available != true`.

---

## Benchmark méret és futási politika

T10-ben a standard verify ne kényszerítsen 600s LV8 futást. A matrix script default `--time-limit-sec 60` legyen, mert a cél cache-stat láthatóság és trend, nem végső packing minőség.

A reportban két szint legyen:

1. **Smoke benchmark** — kötelező T10 gate:
   - LV8 276, 60 sec, seed 42, no-SA shadow profilok.
   - SA guard, 60 sec, seed 42, no-SA shadow profilok.
   - LV8 179, ha létezik.
2. **Long benchmark** — opcionális, ha a futtató agent időkerete engedi:
   - LV8 276, 180 vagy 600 sec.
   - Eredmény külön szekcióban, nem szükséges PASS-hoz.

---

## Acceptance gate

T10 PASS feltételei:

- T08 és T09 reportok léteznek és PASS/PASS_WITH_NOTES státuszúak.
- `scripts/experiments/lv8_phase1_cache_usage_matrix.py` létrejött.
- `tests/test_lv8_phase1_cache_usage_matrix.py` létrejött és zöld.
- A matrix script legalább smoke módban fut.
- Minden kötelező run `summary.json` tartalmaz `engine_stats.available = true` értéket.
- Minden kötelező runnál a cache hit/miss/entries/clear_all/peak mezők parse-olhatók.
- `clear_all_events` értéke reportolva van. Ha bármely runban >0, T10 nem bukik, de `lru_followup_required: true` és T11 előtt LRU döntés szükséges.
- `valid_polygon_gate` reportolva van minden runra.
- `codex/reports/nesting_engine/lv8_phase1_cache_usage_result.md` elkészül.
- `./scripts/verify.sh --report ...` zöld.

---

## Elvárt report döntések

A T10 report végén explicit szerepeljen:

```text
phase2a_ready: YES | NO | DEFERRED
lru_followup_required: YES | NO
cache_stats_available_all_required_runs: YES | NO
polygon_gate_available_all_required_runs: YES | NO
```

Elvárt normál kimenet:

```text
phase2a_ready: YES
lru_followup_required: NO
cache_stats_available_all_required_runs: YES
polygon_gate_available_all_required_runs: YES
```

Ha `phase2a_ready: NO` vagy `DEFERRED`, a report írja le a T11 előtti blokkoló follow-upot.

---

## DoD → Evidence Matrix követelmény

A T10 report DoD matrixa legalább ezeket tartalmazza:

| DoD pont | Elvárt bizonyíték |
|---|---|
| T08/T09 előfeltétel ellenőrizve | report path + státusz |
| Matrix script létrejött | `scripts/experiments/lv8_phase1_cache_usage_matrix.py` |
| Matrix script tesztelve | `tests/test_lv8_phase1_cache_usage_matrix.py` |
| Engine stats minden required runban elérhető | `cache_usage_matrix.json` summary |
| Cache hit/miss/clear_all/peak mezők reportolva | `cache_usage_matrix.md/json` |
| Polygon-aware validation gate reportolva | matrix sorok valid_polygon_gate mezője |
| LRU döntés kimondva | `lru_followup_required` |
| Phase 2a readiness kimondva | `phase2a_ready` |
| Repo gate zöld | AUTO_VERIFY blokk |

---

## Következő task

Ha T10 PASS vagy PASS_WITH_NOTES és `phase2a_ready: YES`, indulhat:

```text
T11 — lv8_density_t11_phase2a_bbox_growth_scoring
```

Ha `lru_followup_required: YES`, akkor T11 előtt külön LRU mini-task szükséges, vagy a T11 reportnak explicit meg kell indokolnia, miért nem blokkoló.
