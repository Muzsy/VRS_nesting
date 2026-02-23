# canvases/nesting_engine/nfp_computation_convex.md

> **Mentés helye a repóban:** `canvases/nesting_engine/nfp_computation_convex.md`
> **TASK_SLUG:** `nfp_computation_convex`
> **Terület (AREA):** `nesting_engine`

---

# NFP Nesting Engine — F2-1: Konvex NFP számítás + cache

## 🎯 Funkció

Konvex polygon-pár No-Fit Polygon (NFP) számítása Minkowski-összeg alapon, és az
eredmények gyorsítótárazása (cache). Ez a Fázis 2 első lépése — a konvex eset
alacsony kockázatú, de az itt lefektetett architektúra (cache API, rotációs
politika, kontúrirány-invariáns) közvetlen örökség F2-2 és F2-3 számára.

**Fontos:** ez a task NEM implementálja a konkáv NFP-t, az IFP-t vagy a CFR-t.
Önálló értéke: téglalap és egyszerű konvex alkatrészek esetén már az F2-1
eredmény is jobb kihasználtságot ad, mint a BLF rács.

**Nem cél:**
- Konkáv NFP (F2-2 task)
- Inner-Fit Polygon / CFR (F2-3 task)
- Simulated Annealing (F2-4 task)
- A meglévő `rust/vrs_solver/` bármilyen módosítása
- Python runner módosítása

---

## 🧠 Fejlesztési részletek

### Érintett fájlok

**Létrehozandó (ha még nem létezik) / módosítandó:**
- `rust/nesting_engine/src/nfp/mod.rs` — modul regisztráció + `NfpError` enum
- `rust/nesting_engine/src/nfp/convex.rs` — Minkowski-összeg konvex esetben
- `rust/nesting_engine/src/nfp/cache.rs` — NFP cache: `(shape_id_a, shape_id_b, rotation_steps_b) → Polygon64`
- `rust/nesting_engine/src/geometry/types.rs` — `cross_product_i128`, `is_ccw`, `is_convex` helperek
- `rust/nesting_engine/tests/nfp_regression.rs` — integrációs regressziós teszt
- `poc/nfp_regression/README.md` — a regressziós könyvtár leírása és fixture formátum
- `poc/nfp_regression/convex_rect_rect.json` — téglalap × téglalap referencia fixture
- `poc/nfp_regression/convex_rect_square.json` — téglalap × négyzet referencia fixture

**Módosuló (meglévő):**
- `rust/nesting_engine/src/lib.rs` vagy `main.rs` — `nfp` modul exportálása

**Nem módosul:**
- `rust/nesting_engine/src/geometry/pipeline.rs` (az `is_ccw` invariáns a types.rs-ben van)

**Nem módosul:**
- `rust/vrs_solver/` (egyetlen fájl sem)
- `vrs_nesting/` (egyetlen fájl sem)
- `scripts/verify.sh`
- A meglévő `feasibility/`, `placement/`, `multi_bin/`, `export/` modulok

---

### Algoritmikus specifikáció

#### Minkowski-összeg (konvex eset) — pairwise vertex sums + convex hull

Az implementált algoritmus (`convex.rs`) az alábbi lépésekből áll:

**1. Előfeldolgozás és invariáns-ellenőrzés**
- `normalize_ring()`: duplikált szomszédos csúcsok és záró ismétlés eltávolítása
- `is_ccw()` / `is_convex()` ellenőrzés mindkét bemenetre — ha nem teljesül: `Err(NfpError::NotConvex)`
- Release buildben is: ha a gyűrű CW, megfordítja (`a_outer.reverse()`) — ez robusztusabb, mint a csak debug assertelés

**2. B tükrözése**
```
neg_b[i] = (-b[i].x, -b[i].y)
```

**3. Pairwise csúcsösszeg (O(n×m) pont)**
```
pairwise_sums = { a[i] + neg_b[j]  |  minden i, j }
```
Eredmény: n×m darab `Point64` koordináta.

**4. Konvex burok (Andrew monotone chain)**
- Pontok rendezése (x, y) szerint lexikografikusan
- `dedup()` (azonos koordinátájú pontok eltávolítása)
- Lower hull + upper hull építése `turn(a,b,c) <= 0` feltétellel
- A `turn()` KIZÁRÓLAG `cross_product_i128()`-et hív (i64 közvetlen szorzat tilos)
- `turn <= 0` kiszűri a kollineáris pontokat is → a kimenet minimalizált csúcsszámú kontúr

**5. Kimenet**
- CCW irányú, kollineáris-mentes konvex poligon
- Kezdőpont: lexikografikusan legkisebb (x,y) csúcs (a sort stabilitásából adódóan)

---

#### Komplexitás és következmények

| Tulajdonság | Edge-merge módszer (O(n+m)) | Pairwise+hull (implementált) |
|---|---|---|
| Időbonyolultság | O(n+m) | O(n×m × log(n×m)) |
| Kollineáris pontok | megtarthatja | eltávolítja (`turn<=0`) |
| Kezdőpont | extrém csúcsból indulva | lex. min (x,y) |
| Determinizmus forrása | angle-merge sorrend | lex. sort + dedup + fix hull eljárás |

**Kis elemszámnál (n,m < 20) a különbség elhanyagolható.** Inflate/offset után
400 csúcsos poligonoknál n×m = 160k pont + sort — ez F2-3-ban cache nélkül
szűk keresztmetszet lehet. A cache (F2-1-ben felépítve) ezt a problémát
teljesen eliminálhatja azonos alak-párra.

**A kollineáris-mentesség következménye:** az NFP kontúr csúcsszáma minimális.
Ez az F2-3 (CFR = IFP \ NFP-unió) szempontjából kedvező (kevesebb pont → gyorsabb
boolean műveletek az `i_overlay`-ben).

---

#### CCW-javítás viselkedése (release vs. debug)

A kód **release buildben is megfordítja** a CW bemenetet (`if !is_ccw { reverse() }`),
nem csak debug assertel. Ez robosztusabb az assert-only megközelítésnél, de
a pipeline invariáns (inflate always CCW) ettől függetlenül fennmarad és kötelező.

---

#### Kontúrirány-invariáns

Az NFP modul bemenete a `geometry/pipeline.rs` által inflated `Polygon64`.
Az inflate pipeline CCW-t garantál az outer kontúrra. A `convex.rs`
`debug_assert!(is_ccw(&poly))` hívással ellenőrzi debug buildben, és
release-ben is javítja, ha szükséges.

---

### Cache tervezés (F2-2 kompatibilis)

#### Kulcs típus

```rust
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct NfpCacheKey {
    pub shape_id_a: u64,
    pub shape_id_b: u64,
    pub rotation_steps_b: i16,  // diszkrét lépések, NEM f64 fokszám
}
```

**Rotációs politika (kőbe vésett):**
- Az engedélyezett rotációk halmaza a job inputból jön (pl. `[0, 90, 180, 270]`)
- Minden egyes rotáció egy lépésszámmal (`rotation_steps_b: i16`) van azonosítva,
  ahol a lépésköz a job szintű `rotation_step_deg` paraméterből adódik
- A cache kulcsban **soha nem szerepel f64 fokszám** — ez a cache-miss
  forrása lenne nem-determinisztikus kerekítési hibák esetén
- A `rotation_steps_b` értéke 0..=(360/rotation_step_deg − 1) tartományban van

**Miért kritikus ez:** Ha f64 rotációs kulcsot használnánk, az `0.9999...°` és
az `1.0000...°` különböző cache entry lenne, és azonos inputra más NFP-t
adhatna vissza különböző futtatásokban.

#### Cache struktúra

```rust
pub struct NfpCache {
    store: HashMap<NfpCacheKey, Polygon64>,
    hits: u64,
    misses: u64,
}

impl NfpCache {
    pub fn get(&mut self, key: &NfpCacheKey) -> Option<&Polygon64>;
    pub fn insert(&mut self, key: NfpCacheKey, nfp: Polygon64);
    pub fn stats(&self) -> CacheStats;  // hits, misses, entry count
}
```

**Tervezési döntés (F2-2 örökség):** A cache kulcsban `shape_id_a` és `shape_id_b`
*sorrend-érzékeny* (NFP(A,B) ≠ NFP(B,A)). Az F2-2-ben ugyanezt a cache-t
fogja használni a konkáv NFP generátor — a kulcs struktúra nem változhat.

---

### Overflow védelem — i128 cross product

A Minkowski-összeg él-rendezésénél és a CCW ellenőrzésnél keresztszorzatot
számolunk. Koordináták: `SCALE = 1_000_000`, max koordináta `~10^4 mm` →
max i64 érték `~10^10`. Keresztszorzat: `dx1 * dy2 - dx2 * dy1` ahol minden
tag max `~2*10^10` → szorzat max `~4*10^20`, ami túlcsordul i64-en (max `~9.2*10^18`).

**Kötelező szabály:** Minden cross product számítás `i128`-on történik:
```rust
fn cross_product_i128(dx1: i64, dy1: i64, dx2: i64, dy2: i64) -> i128 {
    (dx1 as i128) * (dy2 as i128) - (dx2 as i128) * (dy1 as i128)
}
```
Ez a helper a `geometry/types.rs`-be kerül (vagy `nfp/convex.rs`-be), és
az NFP pipeline minden irányítottság-ellenőrzése ezt hívja.

---

### Regressziós fixture formátum (`poc/nfp_regression/`)

**Koordináta konvenció:** A fixture JSON-ok koordinátái **integer egységben** vannak
megadva (nem mm-ben, nem SCALE-lel szorozva). A Rust integrációs teszt közvetlenül
`i64` értékként olvassa be és `Point64`-ré konvertálja. Ez konzisztens önmagával és
a `canonicalize_ring` alapú egzakt egyezés-ellenőrzéssel.

Minden fixture JSON fájl:
```json
{
  "description": "téglalap A (100x50) × téglalap B (60x30), B rotáció=0°",
  "polygon_a": [[0,0],[100,0],[100,50],[0,50]],
  "polygon_b": [[0,0],[60,0],[60,30],[0,30]],
  "rotation_deg_b": 0,
  "expected_nfp": [[-60,-30],[100,-30],[100,50],[-60,50]],
  "expected_vertex_count": 4
}
```

Az összehasonlítás **egzakt** (`assert_eq!`) a kanonizált kontúrokon (`canonicalize_ring`):
CCW orientáció + lexikografikusan legkisebb csúcs a kezdőpont. Nincs koordináta-tolerancia —
az integer aritmetika determinisztikus, kerekítési hiba nincs.

---

### Pipálható feladatlista (implementáció sorrendje)

- [ ] `rust/nesting_engine/src/nfp/mod.rs` — modul scaffold
- [ ] `geometry/types.rs` bővítése `cross_product_i128()` helperrel
- [ ] `is_convex()` és `is_ccw()` helperek (ha még nem léteznek)
- [ ] `nfp/convex.rs` — `compute_convex_nfp(a: &Polygon64, b: &Polygon64) -> Result<Polygon64, NfpError>`
- [ ] `nfp/cache.rs` — `NfpCache` + `NfpCacheKey` + stats
- [ ] Unit tesztek `convex.rs`-ben (min. 4 eset: rect×rect, rect×square, square×square, nem-konvex input → Err)
- [ ] `poc/nfp_regression/` könyvtár + 2 fixture JSON
- [ ] `poc/nfp_regression/README.md`
- [ ] Rust integrációs teszt: fixture-ök betöltése és NFP egyezés-ellenőrzés
- [ ] Cache stats logolása (debug szinten) a nfp modul init/drop-jakor
- [ ] `lib.rs` / `main.rs` bővítése: `pub mod nfp;`

---

## 🧪 Tesztállapot

### DoD (Definition of Done)

- [ ] `compute_convex_nfp()` legalább 4 kézzel ellenőrzött tesztesetet PASS-ol (rect×rect, más méretarányok)
- [ ] Nem-konvex input esetén a függvény `Err(NfpError::NotConvex)` hibával tér vissza (nem pánikol, nem generál hibás outputot)
- [ ] i128 cross product helper megvan és az összes irányítottság-ellenőrzés azt hívja
- [ ] `NfpCacheKey.rotation_steps_b` típusa `i16` (nem f64) — a kulcs-típus kommentben dokumentálva, hogy miért
- [ ] NFP cache hit/miss statisztika legalább debug szinten logolva
- [ ] Determinisztikus output: azonos `(a, b, rotation_steps_b)` input → bit-azonos NFP polygon kétegymást követő futásban
- [ ] `poc/nfp_regression/` könyvtár létezik, legalább 2 fixture fájllal
- [ ] A regressziós fixture-ök Rust integrációs tesztként futnak (`cargo test`)
- [ ] A meglévő F1 gate-ek nem sérülnek (0 overlap, 0 out-of-bounds, determinism hash)
- [ ] `./scripts/verify.sh --report codex/reports/nesting_engine/nfp_computation_convex.md` PASS

### Kockázatok és rollback terv

| Kockázat | Valószínűség | Hatás | Mitigáció |
|---|---|---|---|
| i64 overflow cross product-ban | Magas (ha nem figyelsz) | Helytelen NFP kontúr, csendesen rossz eredmény | Kötelező i128 cross product, unit teszt nagy koordinátákra |
| f64 rotációs kulcs csúszik be a cache-be | Közepes | Cache-miss, nem-determinisztikus viselkedés | `i16` kulcstípus, `#[deny(clippy::float_arithmetic)]` a cache modulban |
| Inflate output nem CCW | Alacsony | Helytelen NFP irány | Release-ben is javítja a kód; pipeline invariáns is véd |
| Nem-konvex polygon konvex-ként kezelve | Alacsony-közepes | Hibás NFP, overlap az F2-3-ban | `is_convex()` ellenőrzés + `Err(NfpError::NotConvex)` visszatérés |
| Cache API inkompatibilis F2-2-vel | Alacsony (de drága) | F2-2 cache-t újra kell írni | Cache kulcs tervezési döntések dokumentálva, F2-2 kompatibilitás canvasban rögzítve |
| **Teljesítmény: n×m pont nagy csúcsszámnál** | Közepes (inflate után 200-400 csúcs előfordulhat) | O(n×m×log) = 160k+ pont / NFP hívás cache miss esetén | NFP cache minden alak-párra — cache miss csak egyszer fordul elő azonos párra; F2-3-ban mérni kell |

**Rollback:** Ha a Minkowski-összeg implementáció hibásnak bizonyul a regressziós teszteken, a task nem merge-elhető. Az F2-3 és F2-4 task-ok blokkoltak, amíg az NFP regressziós tesztek nem zöldek. Nincs "kész, majd javítjuk" opció az NFP alaprétegen.

---

## 🌍 Lokalizáció

Nem releváns (belső Rust modul, nincs UI).

---

## 📎 Kapcsolódások

**Előzmény (elvégzett):**
- `canvases/nesting_engine/nesting_engine_baseline_placer.md` — F1-4 baseline (a javulás mérési alap)
- `docs/nesting_engine/tolerance_policy.md` — SCALE, TOUCH_TOL definíciók
- `rust/nesting_engine/src/geometry/pipeline.rs` — inflated geometria forrása

**Következő task:**
- `canvases/nesting_engine/nfp_computation_concave.md` — F2-2 konkáv NFP (a cache API-t örökli)

**Kutatási referencia:**
- Burke, Kendall, Whitwell (2007): *Complete and robust no-fit polygon generation...*
- `poc/nfp_regression/README.md` — fixture formátum leírás
