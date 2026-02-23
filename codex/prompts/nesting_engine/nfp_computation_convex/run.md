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

### 4.3 — Nem-konvex bemenet nem generálhat hibás NFP-t

Ha `is_convex(a)` vagy `is_convex(b)` hamis: a függvény
`Err(NfpError::NotConvex)` értékkel tér vissza. **Soha nem pánikol,
soha nem generál "jónak látszó" de hibás NFP-t.**

### 4.4 — CCW invariáns ellenőrzése

A `convex.rs` bemeneténél `debug_assert!(is_ccw(&poly))` —
az inflate pipeline CCW-t garantál, de ez a garancia a unit tesztekkel
igazolandó.

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
5. **Konvex NFP implementáció** — nfp/convex.rs (Minkowski-összeg)
6. **Regressziós fixture könyvtár** — poc/nfp_regression/ alapítása
7. **Integrációs teszt** — rust/nesting_engine/tests/nfp_regression.rs
8. **Checklist + report vázlat** — codex artefaktok
9. **Repo gate** — ./scripts/verify.sh (kötelező, utoljára)

---

## 7) DoD ellenőrzőlista (a gate előtt saját ellenőrzés)

Minden pontot saját magad ellenőrizz, mielőtt a verify.sh-t futtatod:

- [ ] `compute_convex_nfp()` ≥ 4 unit teszt PASS (kézzel számolt ref értékekkel)
- [ ] Nem-konvex bemenet → `Err(NfpError::NotConvex)` (nem panic!)
- [ ] Üres polygon → `Err(NfpError::EmptyPolygon)`
- [ ] `cross_product_i128()` helper létezik, minden irányítottság-ellenőrzés azt hívja
- [ ] `NfpCacheKey.rotation_steps_b` típusa `i16` (grep: nincs f64 a cache kulcsban)
- [ ] Cache hit/miss statisztika legalább debug szinten logolva
- [ ] Determinizmus: azonos input → azonos NFP kimeneti csúcslista kétszer egymás után
- [ ] `poc/nfp_regression/` létezik ≥ 2 fixture JSON-nel
- [ ] `rust/nesting_engine/tests/nfp_regression.rs` integrációs teszt PASS
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
- `codex/codex_checklist/nesting_engine/nfp_computation_convex.md`
- `codex/reports/nesting_engine/nfp_computation_convex.md`