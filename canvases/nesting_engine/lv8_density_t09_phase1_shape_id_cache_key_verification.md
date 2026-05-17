# LV8 Density T09 — Phase 1 shape_id / spacing / kernel cache-key verification

## 🎯 Funkció

A T09 célja a meglévő `NfpCacheKey` és `shape_id()` szemantika formális, tesztekkel alátámasztott verifikációja. A T07 spike kódaudit alapján a cache már használatban van és a `shape_id()` inflated polygonból képzett hashként szerepel, de a spacing-hatás, kernel-szeparáció és pipeline-version szükségessége **UNPROVEN** maradt. A T08 már hozzáadta a cache observability mezőket (`clear_all_events`, `peak_entries`), ezért T09 kizárólag a cache-key invariánsokra fókuszál.

Ez a task **elsősorban teszt + audit report**. Production cache-key módosítás csak akkor engedélyezett, ha a kötelező invariáns tesztek tényleges hibát bizonyítanak.

---

## T09 előfeltételek

T09 csak T08 után indulhat.

Kötelező reportok:

```text
codex/reports/nesting_engine/lv8_density_t07_phase1_0_cache_path_discovery_spike.md
codex/reports/nesting_engine/lv8_density_t08_phase1_cache_stats_hardening.md
```

Elfogadott státusz:

```text
PASS
PASS_WITH_NOTES
```

Ha bármelyik előfeltétel hiányzik vagy `FAIL/BLOCKED`, ne módosíts production kódot; készíts `BLOCKED` reportot.

---

## Valós repo-kiindulópontok

### Cache modul

```text
rust/nesting_engine/src/nfp/cache.rs
```

A friss T08 snapshot alapján már tartalmazza:

```rust
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
    pub clear_all_events: u64,
    pub peak_entries: usize,
}

pub fn shape_id(poly: &Polygon64) -> u64 { ... }
```

A cache-key jelenlegi védelmi szintje:

- `shape_id_a`, `shape_id_b` — polygon-hash alapú, nem part-id alapú.
- `rotation_steps_b` — discrete rotation index, float angle nélkül.
- `nfp_kernel` — kernel-aware cache, hogy `OldConcave` és `CgalReference` ne pollute-olja egymást.

### T07 handoff

T07 report szerint:

- A fő NFP cache útvonalak megtalálhatók a `nfp_placer.rs` fájlban.
- OldConcave és cgal_reference státusz dokumentált.
- `shape_id` origin kódaudit alapján inflated polygonból képzettnek tűnik.
- A spacing-hatás formális bizonyítása T09 follow-up.
- A provider fallback (`cgal_reference` → `old_concave`) miatt T09-ben explicit kernel-matrix kell.
- `pipeline_version` szükségessége `UNPROVEN`.

### T08 handoff

T08 report szerint:

- `clear_all_events` és `peak_entries` bekerültek.
- `pending_phase1_fields` lezárva.
- T08 nem módosított cache-key szemantikát.

---

## Scope

### Engedélyezett production módosítások

Csak akkor, ha a teszt bizonyítja, hogy a jelenlegi kulcs hibás:

```text
rust/nesting_engine/src/nfp/cache.rs
rust/nesting_engine/src/placement/nfp_placer.rs
```

Alapesetben T09-nek **nem kell** production kódot módosítania.

### Engedélyezett teszt / task artefaktok

```text
rust/nesting_engine/tests/nfp_cache_key_invariants.rs
codex/codex_checklist/nesting_engine/lv8_density_t09_phase1_shape_id_cache_key_verification.md
codex/reports/nesting_engine/lv8_density_t09_phase1_shape_id_cache_key_verification.md
codex/reports/nesting_engine/lv8_density_t09_phase1_shape_id_cache_key_verification.verify.log
```

---

## Kötelező invariánsok

### 1. Polygon geometry változás → más shape_id

A spacing hatását nem kell full placement pipeline-on át bizonyítani. Elég célzottan modellezni: ugyanaz a nominal négyzet és egy „inflated-like” nagyobb négyzet különböző koordinátákkal **más** `shape_id`-t kell adjon.

Elvárt teszt:

```text
shape_id_changes_when_polygon_coordinates_change
```

### 2. Equivalent polygon boundary → azonos shape_id

A canonicalization nem törhet el. Ugyanaz a polygon más kezdőponttal, lezárt/nyitott ringgel vagy eltérő windinggal azonos hash-t kell adjon.

Elvárt teszt:

```text
shape_id_stable_for_equivalent_polygon_boundary_external
```

Megjegyzés: a cache.rs-ben már van belső unit teszt hasonlóra, de T09-ben legyen külön integration-level invariant is, mert ez a Phase 1 gate része.

### 3. Holes beleszámítanak a shape_id-ba

Azonos outer mellett más hole vagy hiányzó hole más `shape_id` legyen. Ugyanazok a holes más sorrendben / canonical windinggal azonos hash-t adhatnak, de a hole-tartalom nem veszhet el.

Elvárt tesztek:

```text
shape_id_includes_holes
shape_id_is_stable_for_equivalent_holes
```

### 4. Cache-key szeparál kernel szerint

Azonos `shape_id_a`, `shape_id_b`, `rotation_steps_b` mellett `OldConcave` és `CgalReference` külön cache entry. Ha OldConcave result van a cache-ben, ugyanazzal a geometriával CgalReference key miss legyen.

Elvárt teszt:

```text
cache_key_separates_nfp_kernel
```

### 5. Cache-key szeparál rotation_steps_b szerint

Azonos shape ID-k és kernel mellett eltérő `rotation_steps_b` külön key. Ez védi a rotációs NFP eredményeket.

Elvárt teszt:

```text
cache_key_separates_rotation_steps
```

### 6. Cache-key order-sensitive marad

Az NFP(A, B) nem azonos NFP(B, A)-val. A cache key A/B sorrendje ne legyen kommutatív.

Elvárt teszt:

```text
cache_key_is_order_sensitive_external
```

### 7. pipeline_version döntés dokumentálva

T09 végén a reportban explicit döntés kell:

```text
pipeline_version_required: YES | NO | DEFERRED
```

Alapértelmezett elvárt döntés: `NO`, ha a tesztek bizonyítják, hogy a cache key polygon-hash + kernel + rotation mezőkkel elég erős. `YES` csak akkor, ha konkrét failing invariant bizonyítja, hogy ugyanaz a polygon-hash két eltérő NFP-szemantikát takarhat.

---

## Nem-célok

T09 nem végezheti el:

- LRU implementáció.
- Cache usage benchmark.
- LV8 hosszú futtatás.
- Candidate scoring, lookahead, beam, LNS módosítás.
- Quality profile módosítás.
- SA hard-cut döntés.
- CGAL binary build / external `nfp_cgal_probe` futtatás.

A CGAL fallback szcenáriót **cache-key szinten** kell fedni: `NfpKernel::CgalReference` és `NfpKernel::OldConcave` key nem aliasolhat.

---

## Implementációs javaslat

Adj hozzá új integration test fájlt:

```text
rust/nesting_engine/tests/nfp_cache_key_invariants.rs
```

Használható importok:

```rust
use nesting_engine::geometry::types::{Point64, Polygon64};
use nesting_engine::nfp::cache::{shape_id, NfpCache, NfpCacheKey, NfpKernel};
```

Helper polygonok:

- `square(size: i64) -> Polygon64`
- `rectangle(w: i64, h: i64) -> Polygon64`
- `polygon_with_hole(...) -> Polygon64`
- `key(shape_a, shape_b, rotation_steps, kernel) -> NfpCacheKey`

A tesztek gyorsak és determinisztikusak legyenek; nem kell NFP-t számolniuk, csak cache-key és shape-id szemantikát.

---

## Verifikáció

Kötelező célzott ellenőrzések:

```bash
cargo check -p nesting_engine
cargo test -p nesting_engine --test nfp_cache_key_invariants -- --nocapture
cargo test -p nesting_engine nfp::cache -- --nocapture
```

Kötelező repo gate:

```bash
./scripts/verify.sh --report codex/reports/nesting_engine/lv8_density_t09_phase1_shape_id_cache_key_verification.md
```

---

## DoD

- [ ] T07 és T08 report státusza ellenőrizve.
- [ ] Új integration test fájl létrejött: `rust/nesting_engine/tests/nfp_cache_key_invariants.rs`.
- [ ] Legalább 6 invariáns teszt van: geometry-change, equivalent boundary, holes, kernel separation, rotation separation, order sensitivity.
- [ ] A tesztek nem igényelnek CGAL binárist vagy hosszú benchmarkot.
- [ ] Ha nincs failing invariant, production cache-key szemantika változatlan marad.
- [ ] Ha van failing invariant, csak minimális `cache.rs` / `nfp_placer.rs` módosítás történt, reportban indoklással.
- [ ] `pipeline_version_required` döntés szerepel a reportban.
- [ ] `cargo check -p nesting_engine` zöld.
- [ ] `cargo test -p nesting_engine --test nfp_cache_key_invariants -- --nocapture` zöld.
- [ ] `./scripts/verify.sh --report ...` zöld.

---

## Elvárt report döntések

A report végén legyen külön szekció:

```markdown
## Cache-key decision matrix

| Invariant | Result | Evidence | Decision impact |
|---|---|---|---|
| Geometry coordinate change changes shape_id | PASS/FAIL | ... | spacing protected / not protected |
| Equivalent boundary stable | PASS/FAIL | ... | canonicalization safe / unsafe |
| Holes included | PASS/FAIL | ... | holes protected / not protected |
| Kernel separated | PASS/FAIL | ... | cgal fallback safe / unsafe |
| Rotation separated | PASS/FAIL | ... | rotation protected / not protected |
| Order sensitive | PASS/FAIL | ... | NFP direction protected / not protected |

pipeline_version_required: YES | NO | DEFERRED
reason: ...
```

Ha `pipeline_version_required=YES`, a report státusza legfeljebb `PASS_WITH_NOTES`, és T10 előtt külön follow-up szükséges a kulcs-séma módosítására, kivéve ha T09-ben már minimálisan javítva lett.
