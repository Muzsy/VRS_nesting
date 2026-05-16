# LV8 Density T08 — Phase 1 NfpCache stats hardening és clear_all/peak tracking

## 🎯 Funkció

A T08 célja a meglévő `NfpCache` megfigyelhetőségének megerősítése. Ez nem új cache-architektúra, nem LRU-refaktor és nem algoritmusfejlesztés. A task a T07 read-only spike eredményeire épül, amely szerint a jelenlegi `NfpCache` már létezik, multi-sheet flow-ban használatban van, de a cache telítődés / clear események és peak méret nem látszanak megfelelően a runtime statisztikában.

A T08-ban be kell vezetni két új cache observability mezőt:

```text
nfp_cache_clear_all_events
nfp_cache_peak_entries
```

Ezeknek végig kell futniuk a Rust cache statoktól a `NfpPlacerStatsV1` struktúrán át a `NEST_NFP_STATS_V1` stderr JSON-ig, majd a Python benchmark harness `summary.json` normalizált `engine_stats` blokkjáig.

---

## T08 előfeltételek

A T08 a T07 után indulhat.

Kötelező report:

```text
codex/reports/nesting_engine/lv8_density_t07_phase1_0_cache_path_discovery_spike.md
```

A friss snapshotban a T07 státusza `PASS_WITH_NOTES`. Ez **nem blokkolja T08-at**, mert a T07 kifejezetten T08-ra adta át a cache stats / clear-all observability scope-ot.

A T07 work artifact `tmp/phase1_spike_cache_path_discovery.md` a zip snapshotban hiányozhat, mert a `tmp/` artefaktok nem feltétlenül kerülnek a projektfájl-exportba. Ha hiányzik, a T07 report legyen a kötelező forrás. Ez nem blocker.

---

## Valós repo-kiindulópontok

### Cache modul

```text
rust/nesting_engine/src/nfp/cache.rs
```

A jelenlegi struktúra:

```rust
pub const MAX_ENTRIES: usize = 10_000;

pub struct CacheStats {
    pub hits: u64,
    pub misses: u64,
    pub entries: usize,
}

pub struct NfpCache {
    store: HashMap<NfpCacheKey, Polygon64>,
    hits: u64,
    misses: u64,
}
```

Jelenleg a `clear_all()` törli a store-t és nullázza a hit/miss számlálókat is. T08-ban ezt observability szempontból javítani kell: a run-szintű hit/miss számláló **maradjon kumulatív**, a clear esemény pedig külön `clear_all_events` counterben jelenjen meg.

### Placement stats

```text
rust/nesting_engine/src/placement/nfp_placer.rs
```

A `NfpPlacerStatsV1` már tartalmazza:

```rust
nfp_cache_hits
nfp_cache_misses
nfp_cache_entries_end
nfp_compute_calls
...
```

T08-ban ehhez kell hozzáadni:

```rust
nfp_cache_clear_all_events
nfp_cache_peak_entries
```

A `serde::Serialize` derive miatt ezek automatikusan bekerülhetnek a `NEST_NFP_STATS_V1` JSON-ba, ha a stats struktúra kitöltése megtörténik.

### Multi-sheet cache stats aggregáció

```text
rust/nesting_engine/src/multi_bin/greedy.rs
```

A jelenlegi flow a multi-sheet futás végén beállítja:

```rust
stats.nfp_cache_entries_end = nfp_cache.stats().entries as u64;
```

T08-ban ugyanitt kell beállítani az új mezőket is:

```rust
let cache_stats = nfp_cache.stats();
stats.nfp_cache_entries_end = cache_stats.entries as u64;
stats.nfp_cache_clear_all_events = cache_stats.clear_all_events;
stats.nfp_cache_peak_entries = cache_stats.peak_entries as u64;
```

### Python harness normalizáció

```text
scripts/experiments/lv8_2sheet_claude_search.py
```

A T04 óta ez parse-olja a `NEST_NFP_STATS_V1` sort és normalizálja az `engine_stats` blokkot. T04-ben a következő mezők még pendingként szerepeltek:

```text
nfp_cache_clear_all_events
nfp_cache_peak_entries
```

T08-ban ezeket normalizált mezőkké kell tenni, és a pending listát ennek megfelelően le kell zárni.

Kapcsolódó teszt:

```text
tests/test_lv8_density_engine_stats_export.py
```

---

## Scope

### Engedélyezett módosítások

```text
rust/nesting_engine/src/nfp/cache.rs
rust/nesting_engine/src/placement/nfp_placer.rs
rust/nesting_engine/src/multi_bin/greedy.rs
scripts/experiments/lv8_2sheet_claude_search.py
tests/test_lv8_density_engine_stats_export.py
rust/nesting_engine/tests/nfp_cache_stats_hardening.rs
codex/codex_checklist/nesting_engine/lv8_density_t08_phase1_cache_stats_hardening.md
codex/reports/nesting_engine/lv8_density_t08_phase1_cache_stats_hardening.md
codex/reports/nesting_engine/lv8_density_t08_phase1_cache_stats_hardening.verify.log
```

### Nem cél

T08-ban **ne** implementálj LRU-t. A terv szerint LRU csak akkor jön, ha későbbi benchmark bizonyítja, hogy `clear_all_events > 0` valós fixture-ön és ez teljesítményproblémát okoz.

T08-ban **ne** módosíts cache key szemantikát. A shape_id / spacing / pipeline_version invariánsok T09 scope.

T08-ban **ne** módosíts placement algoritmust, candidate ordert, NFP compute logikát vagy quality profile-t.

---

## Részletes végrehajtási elvárás

### 1) `NfpCache` statisztika bővítése

A `CacheStats` legyen legalább:

```rust
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct CacheStats {
    pub hits: u64,
    pub misses: u64,
    pub entries: usize,
    pub clear_all_events: u64,
    pub peak_entries: usize,
}
```

A `NfpCache` tároljon:

```rust
clear_all_events: u64,
peak_entries: usize,
```

Elvárt viselkedés:

- `hits` kumulatív run-szintű számláló.
- `misses` kumulatív run-szintű számláló.
- `clear_all_events` nő minden `clear_all()` hívásnál.
- `peak_entries` a run során látott legnagyobb `store.len()` érték.
- `entries` a jelenlegi `store.len()`.
- `clear_all()` törli a store-t, de **nem nullázza** a kumulatív `hits`, `misses`, `clear_all_events`, `peak_entries` számlálókat.

### 2) Debug log frissítése

A debug-only cache log tartalmazza az új mezőket is. Ez csak debug buildben számít, de segít későbbi auditnál.

### 3) `NfpPlacerStatsV1` bővítése

A `NfpPlacerStatsV1` kapja meg:

```rust
pub nfp_cache_clear_all_events: u64,
pub nfp_cache_peak_entries: u64,
```

Frissítendő:

- struct mezők
- `Default`
- `merge_from()`
- minden olyan hely, ahol a cache végállapotot kitöltik

### 4) Multi-bin export

A `multi_bin/greedy.rs` futás végén olvasd ki egyszer a cache statokat, és töltsd be mindhárom végállapot mezőt:

```text
nfp_cache_entries_end
nfp_cache_clear_all_events
nfp_cache_peak_entries
```

Ne változtasd meg a cache lifetime-ot.

### 5) Harness normalizáció

A `scripts/experiments/lv8_2sheet_claude_search.py` `_normalize_engine_stats()` függvényében térképezd:

```text
raw.nfp_cache_clear_all_events -> normalized.nfp_cache_clear_all_events
raw.nfp_cache_peak_entries -> normalized.nfp_cache_peak_entries
```

A korábbi `pending_phase1_fields` ne listázza tovább ezeket pendingként, ha az új mezők már rendelkezésre állnak. Ha a pending list API-t meg kell tartani backward compatibility miatt, akkor legyen üres lista, vagy csak valóban még hiányzó mezőket tartalmazzon.

### 6) Tesztek

Adj hozzá Rust cache unit/integration tesztet:

```text
rust/nesting_engine/tests/nfp_cache_stats_hardening.rs
```

Minimum tesztesetek:

1. `peak_entries` nő insert után.
2. cache hit/miss kumulatív.
3. `clear_all()` után:
   - `entries == 0`
   - `clear_all_events == 1`
   - `hits` és `misses` nem nullázódik
   - `peak_entries` megmarad
4. `MAX_ENTRIES` telítés esetén `clear_all_events` nő. Ha a 10_000+ insert túl drága lenne, akkor ezt külön teszt-helperrel vagy explicit módon dokumentált egyszerű teszttel oldd meg.

Frissítsd a Python T04 tesztet:

```text
tests/test_lv8_density_engine_stats_export.py
```

Minimum elvárás:

- Valid raw stats tartalmazza az új mezőket.
- Normalized output tartalmazza az új mezőket.
- `pending_phase1_fields` már nem tartalmazza a két T08 által lezárt mezőt.

---

## Acceptance gate

T08 akkor PASS, ha:

- `CacheStats` tartalmazza `clear_all_events` és `peak_entries` mezőket.
- `NfpPlacerStatsV1` tartalmazza és exportálja a két mezőt.
- `NEST_NFP_STATS_V1` raw JSON-ban megjelenhet a két mező.
- A Python harness normalizálja a két mezőt az `engine_stats.normalized` blokkba.
- `tests/test_lv8_density_engine_stats_export.py` frissítve és zöld.
- Új Rust cache stats teszt zöld.
- `cargo check -p nesting_engine` zöld.
- `./scripts/verify.sh --report codex/reports/nesting_engine/lv8_density_t08_phase1_cache_stats_hardening.md` zöld.
- Nem történt LRU implementáció.
- Nem történt cache-key szemantika módosítás.

---

## Report elvárás

A T08 report tartalmazza:

- Rövid összefoglaló: milyen mezők kerültek be.
- T07 handoff alapján mi lett implementálva, mi maradt T09/T10-re.
- Evidence matrix minden acceptance pontra.
- Tesztparancsok és eredmények.
- `AUTO_VERIFY` blokk a standard verify wrapperből.
- Külön advisory note, ha `clear_all()` hit/miss viselkedésének megváltoztatása downstream stat értelmezést érint.

---

## Stop / rollback feltételek

Állj meg és írj `FAIL` vagy `BLOCKED` reportot, ha:

- A `NfpCache` statisztika módosítása placement eredményváltozást okoz.
- A Rust compile csak cache-key módosítással lenne megoldható.
- A T08 cél eléréséhez LRU-t kellene bevezetni.
- A Python harness backward compatibility megszakad úgy, hogy régi raw stats sort már nem tud parse-olni.

