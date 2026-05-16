# LV8 Density T07 — Phase 1.0 cache path discovery spike

## 🎯 Funkció

A T07 célja a Phase 1.0 rövid, kötelező cache path discovery spike végrehajtása. Ez **audit / mérési előkészítő task**, nem cache-refaktor és nem algoritmusfejlesztés.

A végleges LV8 packing density terv szerint Phase 1 már nem új `PairNfpCache` építése, hanem a meglévő `rust/nesting_engine/src/nfp/cache.rs` auditja és keményítése. A T07 ennek első, 0.5–1 napos al-lépése: pontosan fel kell térképezni, hogy a jelenlegi kódbázisban az NFP számítási utak hogyan használják a `NfpCache`-t, milyen geometriából készül a `shape_id()`, szükséges-e LRU, és kell-e később `pipeline_version` vagy más cache-key bővítés.

A T07 outputja egy fix struktúrájú spike report:

```text
tmp/phase1_spike_cache_path_discovery.md
```

A T07 csak akkor tekinthető sikeresnek, ha a report gépiesen ellenőrizhető formában megválaszolja a végleges tervben szereplő Phase 1.0 kérdéseket, és létrehozza a T08–T10 konkrét indulási feltételeit.

---

## T07 előfeltételek

A T07 a T06 után indulhat.

Kötelező reportok:

```text
codex/reports/nesting_engine/lv8_density_t06_phase0_shadow_run_baseline_report.md
codex/reports/nesting_engine/lv8_density_phase0_shadow_baseline.md
```

A friss snapshotban a T06 státusza `PASS_WITH_NOTES`, a `hard_cut_decision` pedig `DEFER_HARD_CUT`. Ez **nem blokkolja T07-et**. A T07 nem igényel no-SA hard-cutot, mert cache auditot végez, nem quality profile default váltást.

Ha a T06 report hiányzik, vagy `FAIL/BLOCKED`, a T07 ne végezzen cache path auditot; készítsen `BLOCKED` reportot.

---

## Valós repo-kiindulópontok a friss snapshot alapján

### Meglévő cache modul

```text
rust/nesting_engine/src/nfp/cache.rs
```

Fontos kódrészletek:

```rust
pub const MAX_ENTRIES: usize = 10_000;

pub struct NfpCacheKey {
    pub shape_id_a: u64,
    pub shape_id_b: u64,
    pub rotation_steps_b: i16,
    pub nfp_kernel: NfpKernel,
}

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

A jelenlegi `clear_all()` nullázza a store-t és a hit/miss számlálókat is. Ez T08/T10 szempontból fontos megfigyelés lehet, de T07-ben még nem kell módosítani.

### Fő cache-használati utak

A friss snapshot alapján cache-hívások látszanak több helyen:

```text
rust/nesting_engine/src/placement/nfp_placer.rs
```

Jellemző pontok:

```text
shape_id(&to_lib_polygon(&moving))
NfpCacheKey { shape_id_a, shape_id_b, rotation_steps_b, nfp_kernel }
cache.get(&key)
compute_nfp_lib(...)
cache.insert(key, poly_rel.clone())
```

Auditálandó szakaszok:

```text
nfp_placer.rs körülbelül: 900–940
nfp_placer.rs körülbelül: 1140–1180
nfp_placer.rs körülbelül: 1260–1330
nfp_placer.rs körülbelül: 2040–2090
```

A pontos line számokat a friss kódból kell reportolni, nem ebből a canvasból vakon átvenni.

### Multi-sheet cache lifetime

```text
rust/nesting_engine/src/multi_bin/greedy.rs
```

A friss snapshotban a multi-bin greedy létrehoz egy `NfpCache::new()` példányt, majd átadja `nfp_place()`-nek. T07-ben ellenőrizni kell, hogy ez tényleg teljes multi-sheet run scope-e, és a cache nem jön-e létre újra sheetenként vagy evalonként más útvonalakon.

### NFP provider és kernel audit

Érintett fájlok:

```text
rust/nesting_engine/src/nfp/provider.rs
rust/nesting_engine/src/nfp/concave.rs
rust/nesting_engine/src/nfp/cgal_reference_provider.rs
```

Kérdés: a cache key `nfp_kernel` mezője ténylegesen a futó providerhez igazodik-e, vagy van kernel útvonal, ahol cache bypass történik.

### T06 baseline artefaktok

T06 létrehozta:

```text
scripts/experiments/lv8_phase0_shadow_run_matrix.py
tests/test_lv8_phase0_shadow_run_matrix.py
codex/reports/nesting_engine/lv8_density_phase0_shadow_baseline.md
```

A T07-nek nem kell új shadow matrixot futtatnia, de felhasználhatja a T06 reportot és, ha a snapshot tartalmazza, a `tmp/lv8_density_phase0_shadow_runs/` artefaktokat.

---

## Scope

### Engedélyezett módosítások

A T07 alapvetően read-only audit. Engedélyezett outputok:

```text
tmp/phase1_spike_cache_path_discovery.md
codex/codex_checklist/nesting_engine/lv8_density_t07_phase1_0_cache_path_discovery_spike.md
codex/reports/nesting_engine/lv8_density_t07_phase1_0_cache_path_discovery_spike.md
codex/reports/nesting_engine/lv8_density_t07_phase1_0_cache_path_discovery_spike.verify.log
```

### Tilos módosítani

A T07-ben tilos production kódot módosítani:

```text
rust/nesting_engine/src/**
scripts/experiments/**
vrs_nesting/**
worker/**
tests/**
```

Ha a cache path audit közben olyan hibát találsz, ami kódmódosítást igényel, **ne javítsd T07-ben**. Dokumentáld a T07 reportban, és add át T08/T09/T10 scope-ba.

---

## Kötelező spike report struktúra

A `tmp/phase1_spike_cache_path_discovery.md` pontosan ezzel a szekcióstruktúrával készüljön:

```markdown
# Phase 1.0 cache path discovery spike — output

## NFP call graph
- list every fn that COULD call NFP computation
- mark which of those actually go through NfpCache::get / insert
- mark which BYPASS the cache (if any)

## Per-kernel cache usage
- OldConcave path: cache-passing? where (file:line)?
- cgal_reference path: cache-passing? where (file:line)?
- reduced_convolution path (if active): cache-passing?

## shape_id origin verification
- Is the polygon passed to shape_id() inflated or nominal?
- Test / evidence: same part geometry with different spacing_mm would produce different shape_id? Y/N/UNPROVEN
- Evidence source: code path, existing test, or blocked reason

## LRU vs clear_all decision input
- Does CacheStats expose clear_all_events today? Y/N
- Does CacheStats expose peak_entries today? Y/N
- Existing MAX_ENTRIES value
- Any evidence from T06/T04 summary stats about entries/hits/misses
- Decision: LRU needed now? Y/N/DEFER + reasoning

## pipeline_version field need (audit answer)
- Are there two pipelines that can produce identical inflated polygons but require different downstream NFP semantics? Y/N/UNPROVEN
- If yes: pipeline_version field is REQUIRED in later task
- If no: not needed now
- If unproven: what exact follow-up test belongs to T09?

## Phase 1 full audit revised estimate
- Original estimate: 3 days
- Revised estimate based on spike findings: X days
- Specific risks discovered
```

A T07 task report (`codex/reports/...md`) foglalja össze ugyanezt rövidebben, DoD → Evidence Matrix formában.

---

## Konkrét végrehajtási ellenőrzések

A kódoló ügynök legalább ezeket a parancsokat / ellenőrzéseket használja:

```bash
grep -R "compute_nfp_lib\|compute_stable_concave_nfp\|compute_nfp_lib_with_provider\|NfpCache\|shape_id\|cache.get\|cache.insert" -n rust/nesting_engine/src > tmp/t07_cache_symbol_scan.txt
```

```bash
python3 - <<'PY'
from pathlib import Path
required = [
    'rust/nesting_engine/src/nfp/cache.rs',
    'rust/nesting_engine/src/placement/nfp_placer.rs',
    'rust/nesting_engine/src/multi_bin/greedy.rs',
    'rust/nesting_engine/src/nfp/provider.rs',
    'rust/nesting_engine/src/nfp/concave.rs',
    'rust/nesting_engine/src/nfp/cgal_reference_provider.rs',
]
for path in required:
    p = Path(path)
    print(path, 'OK' if p.is_file() else 'MISSING')
PY
```

```bash
cargo check -p nesting_engine
```

A symbol scan output `tmp/t07_cache_symbol_scan.txt` csak segédartefakt. Nem kötelező végső output, de ha létrejön, nem baj. A kötelező végső output a spike report.

---

## Acceptance gate

A T07 akkor PASS, ha:

- [ ] A T06 report létezik és `PASS` vagy `PASS_WITH_NOTES`.
- [ ] `tmp/phase1_spike_cache_path_discovery.md` létezik.
- [ ] A spike report tartalmazza a kötelező 6 fő szekciót.
- [ ] Minden NFP compute path besorolva: cache-elt / bypass / inactive / unknown-with-reason.
- [ ] Minden ismert kernel útvonal állapota dokumentálva: OldConcave, cgal_reference, reduced_convolution ha aktív.
- [ ] `shape_id()` origin kérdés megválaszolva vagy T09 follow-up-ra bontva.
- [ ] LRU vs clear_all döntési input megadva.
- [ ] `pipeline_version` szükségessége eldöntve vagy T09 follow-up-ra bontva.
- [ ] Phase 1 full audit becslése frissítve.
- [ ] Production code nem módosult.
- [ ] Repo gate lefutott: `./scripts/verify.sh --report codex/reports/nesting_engine/lv8_density_t07_phase1_0_cache_path_discovery_spike.md`.

`PASS_WITH_NOTES` elfogadható, ha a report legalább egy kérdésre `UNPROVEN` választ ad, de konkrét T08/T09/T10 follow-upot rendel hozzá.

`FAIL/BLOCKED`, ha:

- hiányzik vagy FAIL/BLOCKED a T06 report,
- a cache pathok nem feltérképezhetők a repo snapshotból,
- production kód módosult T07-ben,
- a repo gate bukik.

---

## Kapcsolódás a következő taskokhoz

A T07 reportnak egyértelműen meg kell mondania, hogy a következő taskok mit vegyenek át:

- **T08:** milyen cache stats hardening szükséges (`clear_all_events`, `peak_entries`, esetleges LRU-decision).
- **T09:** milyen shape_id / spacing / kernel / pipeline_version teszteket kell írni.
- **T10:** melyik NFP pathokat kell benchmarkban bizonyítani és melyik kernel útvonalon kell cache-hit mérés.

A T07 nem zárhatja le ezeket implementációval, csak scope-olja őket.
