# canvases/nesting_engine/cfr_sort_key_precompute_and_hash_cache.md

## 🎯 Funkció

Teljesítmény P0/P1: a `rust/nesting_engine/src/nfp/cfr.rs` CFR komponens-rendezésének gyorsítása úgy, hogy **ne számoljuk újra** a `ring_hash_u64`-t és a sort-kulcsot minden összehasonlításnál.

Cél:
- `compute_cfr(...)` viselkedése **byte-stabil** marad (ugyanaz a kimenet, ugyanaz a determinisztika),
- a rendezéshez szükséges kulcsok (`min_point`, `abs_area`, `vertex_count`, `ring_hash`) **komponensenként egyszer** készüljenek el,
- a `sort_by` comparator csak előre kiszámolt kulcsokat hasonlítson össze.

## 🧠 Fejlesztési részletek

### Felderítés (aktuális állapot)
- A jelenlegi `rust/nesting_engine/src/nfp/cfr.rs` `sort_components` comparatora minden összehasonlításnál újraszámolja:
  - `ring_hash_u64` (sha256),
  - `component_area_abs`,
  - `vertex_count`,
  - `min_point`.
- Emiatt azonos komponensekre a hash és sort-kulcs elemek többször futnak le rendezés közben, ami felesleges CPU-terhelést okoz.
- A célzott, minimál-invazív javítás: canonicalize + invalid-drop után komponensenként egyszer előállított sort-kulcs (`SortKey`) és dekorált rendezés (`Decorated`), majd visszamappelés `Vec<Polygon64>`-ra.

### Kontextus
A `cfr_canonicalize_and_sort_hardening` után a CFR kimenet kanonizált és totálisan rendezett, de a jelenlegi implementációban a `ring_hash_u64(...)` (sha256) a comparatorban könnyen **többször** fut le ugyanarra a komponensre, ami sok komponens esetén felesleges CPU.

### Elvárt megoldás (determinista és minimál invazív)
A `compute_cfr(...)` végén a `Vec<Polygon64>` helyett használj ideiglenesen egy “decorated” listát:

- `struct SortKey { min_point: Point64, abs_area: i128/u128, vertex_count: usize, ring_hash: u64 }`
- `struct Decorated { poly: Polygon64, key: SortKey }`

Pipeline:
1) canonicalize minden `Polygon64`-ot (mint most),
2) dobd a degenerált/0-area komponenseket (mint most),
3) **komponensenként egyszer** számold ki a `SortKey`-t,
4) sort `Decorated` listát `key` szerint,
5) map vissza `Vec<Polygon64>`.

### Test-only guardrail (kötelező)
Adj hozzá teszt-only számlálót arra, hogy a `ring_hash_u64` hány alkalommal futott:

- `#[cfg(test)] static RING_HASH_CALLS: AtomicUsize = ...`
- `ring_hash_u64` növeli
- unit tesztben:
  - reset counter
  - compute_cfr(...)
  - assert: `RING_HASH_CALLS == component_count` (vagy <= component_count + kis konstans, ha van üres ág)
  
Cél: megfogni, ha valaki később visszateszi a hash számítást a comparatorba.

### Érintett fájlok
- `rust/nesting_engine/src/nfp/cfr.rs`
- Codex artefaktok:
  - `codex/codex_checklist/nesting_engine/cfr_sort_key_precompute_and_hash_cache.md`
  - `codex/reports/nesting_engine/cfr_sort_key_precompute_and_hash_cache.md`
  - `codex/reports/nesting_engine/cfr_sort_key_precompute_and_hash_cache.verify.log`

## 🧪 Tesztállapot

### DoD
- [ ] `cfr.rs` komponens-sort kulcs előszámítva (nincs sha256 a comparatorban)
- [ ] `ring_hash_u64` hívás komponensenként egyszer (test guardrail igazolja)
- [ ] A meglévő CFR unit tesztek továbbra is PASS (startpoint/orientáció/permutáció-stabil)
- [ ] Gate PASS:
  `./scripts/verify.sh --report codex/reports/nesting_engine/cfr_sort_key_precompute_and_hash_cache.md`

## 🌍 Lokalizáció
Nem releváns.

## 📎 Kapcsolódások
- `canvases/nesting_engine/cfr_canonicalize_and_sort_hardening.md`
- `rust/nesting_engine/src/nfp/cfr.rs`
- `rust/nesting_engine/src/nfp/cache.rs` (hash minta)
- `AGENTS.md`, `docs/codex/yaml_schema.md`, `docs/codex/report_standard.md`
