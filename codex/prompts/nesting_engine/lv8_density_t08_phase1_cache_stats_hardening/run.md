# Runner — lv8_density_t08_phase1_cache_stats_hardening

## Feladat

Végrehajtandó task: **T08 — Phase 1 NfpCache stats hardening és clear_all/peak tracking**.

Ez production Rust + Python observability task. Nem LRU-refaktor, nem cache-key módosítás, nem algoritmusfejlesztés. A cél, hogy a meglévő `NfpCache` két hiányzó run-szintű statisztikája — `clear_all_events` és `peak_entries` — látható legyen a Rust statoktól a benchmark `summary.json`-ig.

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
canvases/nesting_engine/lv8_density_t08_phase1_cache_stats_hardening.md
codex/goals/canvases/nesting_engine/fill_canvas_lv8_density_t08_phase1_cache_stats_hardening.yaml
codex/reports/nesting_engine/lv8_density_t07_phase1_0_cache_path_discovery_spike.md
```

A T07 `PASS_WITH_NOTES` nem blokkol. Ha `tmp/phase1_spike_cache_path_discovery.md` nincs a snapshotban, használd a T07 reportot forrásként.

## Scope

Engedélyezett production módosítások:

```text
rust/nesting_engine/src/nfp/cache.rs
rust/nesting_engine/src/placement/nfp_placer.rs
rust/nesting_engine/src/multi_bin/greedy.rs
scripts/experiments/lv8_2sheet_claude_search.py
tests/test_lv8_density_engine_stats_export.py
rust/nesting_engine/tests/nfp_cache_stats_hardening.rs
```

Engedélyezett task artefaktok:

```text
codex/codex_checklist/nesting_engine/lv8_density_t08_phase1_cache_stats_hardening.md
codex/reports/nesting_engine/lv8_density_t08_phase1_cache_stats_hardening.md
codex/reports/nesting_engine/lv8_density_t08_phase1_cache_stats_hardening.verify.log
```

Tilos:

```text
- LRU implementáció
- NfpCacheKey / shape_id szemantika módosítása
- placement algoritmus vagy candidate ordering módosítása
- quality profile módosítás
- SA / LNS / beam / lookahead módosítás
```

Ha ezek nélkül nem teljesíthető a task, állj meg és írj FAIL/BLOCKED reportot.

## Végrehajtási lépések

### 1) Előfeltétel ellenőrzés

```bash
python3 - <<'PY'
from pathlib import Path
p = Path('codex/reports/nesting_engine/lv8_density_t07_phase1_0_cache_path_discovery_spike.md')
print('T07 report:', 'OK' if p.is_file() else 'MISSING')
if p.is_file():
    head = '\n'.join(p.read_text(encoding='utf-8', errors='replace').splitlines()[:40])
    print(head)
PY
```

Ha a T07 report hiányzik vagy FAIL/BLOCKED, készíts BLOCKED reportot.

### 2) Cache stat hardening

Módosítsd:

```text
rust/nesting_engine/src/nfp/cache.rs
```

Elvárt `CacheStats`:

```rust
pub struct CacheStats {
    pub hits: u64,
    pub misses: u64,
    pub entries: usize,
    pub clear_all_events: u64,
    pub peak_entries: usize,
}
```

Elvárt `NfpCache` belső mezők:

```rust
clear_all_events: u64,
peak_entries: usize,
```

Elvárt szemantika:

- `get()` hit/miss továbbra is kumulatív counters.
- `insert()` után frissül `peak_entries`.
- `clear_all()` törli a store-t, növeli `clear_all_events`-t, de nem nullázza a hit/miss/peak számlálókat.
- `stats()` visszaadja az új mezőket is.

### 3) Placement stats és multi-bin export

Módosítsd:

```text
rust/nesting_engine/src/placement/nfp_placer.rs
rust/nesting_engine/src/multi_bin/greedy.rs
```

Add hozzá `NfpPlacerStatsV1` mezőkhöz:

```rust
pub nfp_cache_clear_all_events: u64,
pub nfp_cache_peak_entries: u64,
```

Frissítsd:

- `Default`
- `merge_from()`
- multi-bin final cache stats assignment

A `multi_bin/greedy.rs` helyen ne hívd meg többször szükségtelenül `nfp_cache.stats()`-ot; egyszer olvasd ki, és abból állítsd be a három cache end mezőt.

### 4) Python harness és T04 tesztek

Módosítsd:

```text
scripts/experiments/lv8_2sheet_claude_search.py
tests/test_lv8_density_engine_stats_export.py
```

Elvárás:

- `_normalize_engine_stats()` adja vissza:
  - `nfp_cache_clear_all_events`
  - `nfp_cache_peak_entries`
- `pending_phase1_fields` már ne tartalmazza ezt a két mezőt.
- Régi raw stats, amely nem tartalmazza az új mezőket, ne törje el a parser-t; ilyen esetben normalized érték lehet `None`.

### 5) Rust teszt

Hozd létre:

```text
rust/nesting_engine/tests/nfp_cache_stats_hardening.rs
```

Minimum tesztek:

```text
- peak_entries tracks maximum entries after insert
- hits and misses accumulate across get calls
- clear_all increments clear_all_events and preserves cumulative hits/misses/peak_entries
- optional: capacity-triggered clear_all increments clear_all_events
```

A tesztek legyenek determinisztikusak és gyorsak.

### 6) Célzott ellenőrzések

Futtasd legalább:

```bash
cargo check -p nesting_engine
cargo test -p nesting_engine nfp_cache_stats_hardening
python3 -m pytest tests/test_lv8_density_engine_stats_export.py
```

Ha a repo saját workspace layoutja miatt valamelyik parancs pontosítása szükséges, igazítsd a repo mintáihoz, de a reportban írd le.

### 7) Report és checklist

Hozd létre:

```text
codex/codex_checklist/nesting_engine/lv8_density_t08_phase1_cache_stats_hardening.md
codex/reports/nesting_engine/lv8_density_t08_phase1_cache_stats_hardening.md
```

A report tartalmazza:

- Státusz: PASS / PASS_WITH_NOTES / FAIL / BLOCKED.
- Scope összefoglaló.
- Módosított fájlok listája.
- Mi maradt T09/T10 scope-ban.
- Tesztparancsok és eredmények.
- DoD → Evidence Matrix.
- Production-code-change check.

### 8) Standard repo gate

Futtasd:

```bash
./scripts/verify.sh --report codex/reports/nesting_engine/lv8_density_t08_phase1_cache_stats_hardening.md
```

A verify log:

```text
codex/reports/nesting_engine/lv8_density_t08_phase1_cache_stats_hardening.verify.log
```

Ha a gate bukik, a report státusza FAIL legyen, és ne jelöld késznek a taskot.

## Acceptance checklist

- [ ] `CacheStats` tartalmazza `clear_all_events` és `peak_entries` mezőket.
- [ ] `NfpCache` számlálja a clear eseményeket és peak entries maximumot.
- [ ] `clear_all()` nem nullázza a kumulatív hit/miss számlálókat.
- [ ] `NfpPlacerStatsV1` exportálja az új mezőket.
- [ ] `multi_bin/greedy.rs` kitölti az új mezőket a cache final stats alapján.
- [ ] `scripts/experiments/lv8_2sheet_claude_search.py` normalizálja az új mezőket.
- [ ] `tests/test_lv8_density_engine_stats_export.py` frissítve és zöld.
- [ ] `rust/nesting_engine/tests/nfp_cache_stats_hardening.rs` létezik és zöld.
- [ ] `cargo check -p nesting_engine` zöld.
- [ ] Standard verify zöld.
- [ ] Nincs LRU implementáció.
- [ ] Nincs cache-key szemantika módosítás.

