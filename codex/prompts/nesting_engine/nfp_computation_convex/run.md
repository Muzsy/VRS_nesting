# VRS Nesting Codex Task — NFP Nesting Engine: F2-1 Konvex NFP számítás + cache
TASK_SLUG: nfp_computation_convex

## 1) Kötelező olvasnivaló (prioritási sorrend)

Olvasd el és tartsd be, ebben a sorrendben:

1. `AGENTS.md`
2. `docs/codex/overview.md`
3. `docs/codex/yaml_schema.md`
4. `docs/codex/report_standard.md`
5. `docs/nesting_engine/tolerance_policy.md` — SCALE=1_000_000, TOUCH_TOL=1i64
6. `rust/nesting_engine/src/geometry/types.rs` — Point64, Polygon64 típusok
7. `rust/nesting_engine/src/geometry/pipeline.rs` — inflated pipeline (CCW invariáns forrása)
8. `rust/nesting_engine/src/lib.rs` (vagy main.rs) — modul regisztrációs pont
9. `poc/nesting_engine/baseline_benchmark.md` — F1 baseline (a javulás mérési alap)
10. `canvases/nesting_engine/nfp_computation_convex.md` — task specifikáció
11. `codex/goals/canvases/nesting_engine/fill_canvas_nfp_computation_convex.yaml` — lépések

Ha bármelyik fájl nem létezik: állj meg, és írd le pontosan mit kerestél és hol.

---

## 2) Cél

Az F2-1 task célja a konvex polygon-pár NFP (No-Fit Polygon) számításának
implementálása Minkowski-összeg alapon, és az eredmények gyorsítótárazása.
Ez a Fázis 2 belépőpontja — az itt lefektetett cache API és rotációs politika
közvetlen örökség F2-2 (konkáv NFP) és F2-3 (CFR/IFP placer) számára.

---

## 3) Nem cél

- Konkáv NFP (F2-2 task)
- Inner-Fit Polygon / CFR számítás (F2-3 task)
- Simulated Annealing (F2-4 task)
- `rust/vrs_solver/` bármilyen módosítása
- Python runner módosítása
- Az F1 baseline placer cseréje (az F2-3 feladata)

---

## 4) Kritikus implementációs megszorítások (nem alkuképes)

### 4.1 — i128 cross product (overflow védelem)

Koordináták `SCALE=1_000_000` esetén max `~10^10` értékűek. Két ilyen szám
szorzata `~10^20`, ami **túlcsordul i64-en** (max ~9.2×10^18). Ez csendesen
hibás NFP kontúrhoz vezet.

**Kötelező:** minden cross product számítás `i128`-on:
```rust
fn cross_product_i128(dx1: i64, dy1: i64, dx2: i64, dy2: i64) -> i128 {
    (dx1 as i128) * (dy2 as i128) - (dx2 as i128) * (dy1 as i128)
}
```
Közvetlen `i64` szorzat az irányítottság-ellenőrzésekben **tilos**.

### 4.2 — Cache kulcsban TILOS az f64 rotáció

A `NfpCacheKey.rotation_steps_b` típusa `i16` (diszkrét lépésszám),
**soha nem f64 fokszám**. Az f64 kulcs cache-miss forrás és
determinizmus-gyilkos lenne. A kulcstípus az F2-2-ben sem változhat.

### 4.3 — Algoritmus: fastpath edge-merge + referencia hull (Minkowski ugyanaz, útvonal más)

Az F2-1-ben két implementáció létezik ugyanarra a matematikai célra:
`NFP(A,B)=A ⊕ (-B)` (konvex polygon-pár).

#### 4.3.1 — `compute_convex_nfp()` = **FASTPATH edge-vector merge** (O(n+m))
Ez a fő belépési pont konvex NFP-re. Lépések:

1. `normalize_ring()` — duplikált és záró csúcsok eltávolítása
2. Méretellenőrzés (`< 3` csúcs → `EmptyPolygon`), konvexitás + CCW check
3. Release-ben is CCW javítás: `if !is_ccw { outer.reverse() }`
4. B tükrözése: `(-B)`
5. Kezdőpont normalizálás: `argmin_lex()` és `rotate_left()` A és (-B) outer gyűrűn
6. Élek képzése: `edge_vectors()`
7. **Szög szerinti összeolvasztás (merge)** cross sign alapján:
   - `cross(edge_a, edge_b) > 0` → A él
   - `< 0` → B él
   - `== 0` → kollineáris merge (`edge_a + edge_b`)
8. Kontúr felépítése prefix-sum-mal a merged edge vektorokon
9. `normalize_ring()` a kontúron, `len()<3` → `NotConvex`

**Komplexitás:** O(n+m). Ez az útvonal a későbbi F2-3 placer teljesítményének alapja.

#### 4.3.2 — `compute_convex_nfp_reference()` = **pairwise vertex sums + Andrew hull** (O(n×m log(n×m)))
Ez a referencia / fallback útvonal. Lépések:

1. `normalize_ring()` — duplikált és záró csúcsok eltávolítása
2. Méretellenőrzés (`< 3` csúcs → `EmptyPolygon`), konvexitás + CCW check
3. Release-ben is CCW javítás: `if !is_ccw { outer.reverse() }`
4. B tükrözése: `(-B)`
5. **Pairwise sums** — O(n×m): minden `a[i] + (-b[j])` pont összegyűjtve
6. **Andrew monotone chain hull**:
   - lex. sort (x, y), dedup
   - lower + upper hull, `turn(a,b,c) <= 0` esetén pop
   - `turn()` KIZÁRÓLAG `cross_product_i128()`-et hív
   - `turn <= 0` kollineáris pontokat is eltávolít → minimális csúcsszám

**Komplexitás:** O(n×m×log(n×m)). Főleg teszt/cross-check és fallback célra.

#### 4.3.3 — Kötelező korrektségi kontroll
Az integrációs regressziós tesztnek minden fixture-re kötelezően ellenőriznie kell:
`compute_convex_nfp()` == `compute_convex_nfp_reference()` (kanonizált ring alapján).

### 4.3 — Nem-konvex bemenet nem generálhat hibás NFP-t

Ha `is_convex(a)` vagy `is_convex(b)` hamis: a függvény
`Err(NfpError::NotConvex)` értékkel tér vissza. **Soha nem pánikol,
soha nem generál "jónak látszó" de hibás NFP-t.**

### 4.4 — CCW invariáns: release-ben is javít, nem csak assertel

A `convex.rs` `debug_assert!(is_ccw(&poly))` hívást tartalmaz, **de ezen felül
release-ben is megfordítja a CW inputot** (`if !is_ccw { outer.reverse() }`).
Ez robosztusabb a pure assert-only megközelítésnél.

A pipeline invariáns (inflate always CCW) ettől függetlenül kötelező és fenntartandó —
a release-es javítás csak biztonsági háló, nem a pipeline kötelezettség helyettesítője.

---

## 5) Architekturális döntés — F2-2 kompatibilitás

A `nfp/cache.rs` és a `NfpCacheKey` struktúra az F2-2 konkáv NFP generátor
belépési pontja is lesz. Az F2-1 implementáció során az alábbi döntések
**nem reversibilisek** F2-2 megkezdése nélkül:

- `shape_id_a: u64`, `shape_id_b: u64`: sorrend-érzékeny (NFP(A,B) ≠ NFP(B,A))
- `rotation_steps_b: i16`: a lépésszám értelmezése és tartománya rögzített
- `NfpCache::get()` / `insert()` / `stats()` API szignatúrái rögzítettek

Ha bármely döntést meg kell változtatni, azt a canvasban és a YAML-ben
dokumentálni kell, mielőtt az F2-2 task-ot megkezded.

---

## 6) Végrehajtás sorrendje (YAML lépések szerint)

1. **Szabályok + kontextus betöltése** — tolerance_policy, types.rs, pipeline.rs
2. **i128 helper + CCW/konvexitás ellenőrzők** — geometry/types.rs bővítése
3. **NFP modul scaffold + NfpError** — nfp/mod.rs + lib.rs regisztráció
4. **Cache implementáció** — nfp/cache.rs (i16 kulcs, F2-2 kompatibilis API)
5. **Konvex NFP implementáció** — nfp/convex.rs (FASTPATH edge-merge + referencia hull)
6. **Regressziós fixture könyvtár** — poc/nfp_regression/ alapítása
7. **Integrációs teszt** — rust/nesting_engine/tests/nfp_regression.rs
8. **Checklist + report vázlat** — codex artefaktok
9. **Repo gate** — ./scripts/verify.sh (kötelező, utoljára)

---

## 7) DoD ellenőrzőlista (a gate előtt saját ellenőrzés)

Minden pontot saját magad ellenőrizz, mielőtt a verify.sh-t futtatod:

- [ ] `compute_convex_nfp()` és `compute_convex_nfp_reference()` létezik, külön útvonal
- [ ] `compute_convex_nfp()` ≥ 6 unit teszt PASS (kézzel számolt ref értékekkel + edge-case)
- [ ] Nem-konvex bemenet → `Err(NfpError::NotConvex)` (nem panic!)
- [ ] Üres polygon → `Err(NfpError::EmptyPolygon)`
- [ ] `NfpError` enum csak `NotConvex` és `EmptyPolygon` variánst tartalmaz (`InvalidInput` nincs)
- [ ] `cross_product_i128()` helper létezik, minden irányítottság-ellenőrzés azt hívja
- [ ] `NfpCacheKey.rotation_steps_b` típusa `i16` (grep: nincs f64 a cache kulcsban)
- [ ] Cache hit/miss statisztika legalább debug szinten logolva
- [ ] Determinizmus: azonos input → azonos NFP kimeneti csúcslista kétszer egymás után
- [ ] `poc/nfp_regression/` létezik, és legalább 7 fixture van (rotált / többcsúcsos / collinear / skinny)
- [ ] Fixture koordinátái integer egységben vannak (nem mm, nem SCALE-lel szorozva)
- [ ] `nfp_regression.rs` integrációs teszt `canonicalize_ring` + egzakt `assert_eq!`-t használ (nem toleranciás összehasonlítást)
- [ ] Integrációs tesztben: `compute_convex_nfp()` == `compute_convex_nfp_reference()` minden fixture-re
- [ ] `cargo build vrs_solver --release` PASS (F1 regresszió nem sérül)
- [ ] `cargo test` (nesting_engine) PASS (minden unit + integrációs teszt)

---

## 8) Gate futtatása (kötelező, kizárólag wrapperrel)

```bash
./scripts/verify.sh --report codex/reports/nesting_engine/nfp_computation_convex.md
```

Ez futtatja: `./scripts/check.sh` (teljes gate, beleértve F1 regressziót),
logot ment: `codex/reports/nesting_engine/nfp_computation_convex.verify.log`,
frissíti: a report `AUTO_VERIFY` blokkját.

**Ha FAIL:** ne merge-elj, javítsd a hibát, futtasd újra.

---

## 9) Output elvárás

A végén add meg a létrehozott/módosított fájlok teljes tartalmát, fájlonként
külön blokkokban (nem diffet, hanem teljes fájltartalmat):

- `rust/nesting_engine/src/nfp/mod.rs`
- `rust/nesting_engine/src/nfp/convex.rs`
- `rust/nesting_engine/src/nfp/cache.rs`
- `rust/nesting_engine/src/geometry/types.rs` (csak a módosított részek is elfogadott, ha a teljes fájl nagy)
- `rust/nesting_engine/tests/nfp_regression.rs`
- `poc/nfp_regression/README.md`
- `poc/nfp_regression/convex_rect_rect.json`
- `poc/nfp_regression/convex_rect_square.json`
- `poc/nfp_regression/convex_triangle.json`
- `poc/nfp_regression/convex_hexagon.json`
- `poc/nfp_regression/convex_rotated_rect.json`
- `poc/nfp_regression/convex_skinny.json`
- `poc/nfp_regression/convex_collinear_edge.json`
- `codex/codex_checklist/nesting_engine/nfp_computation_convex.md`
- `codex/reports/nesting_engine/nfp_computation_convex.md`
