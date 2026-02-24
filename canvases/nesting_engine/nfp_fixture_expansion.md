# canvases/nesting_engine/nfp_fixture_expansion.md

> **Mentés helye a repóban:** `canvases/nesting_engine/nfp_fixture_expansion.md`
> **TASK_SLUG:** `nfp_fixture_expansion`
> **Terület (AREA):** `nesting_engine`

---

# NFP Nesting Engine — Fixture könyvtár bővítése + white-box unit tesztek

## 🎯 Funkció

A `poc/nfp_regression/` könyvtár jelenleg 2 db axis-aligned téglalap fixture-t
tartalmaz. Ez nem elegendő az edge-merge fastpath általános helyességének
igazolásához. Ez a task bővíti a fixture készletet érdemi lefedettségre, és
bevezeti a `convex.rs`-be a hiányzó white-box unit teszteket.

**Miért szükséges:**
- A publikus `compute_convex_nfp()` edge-merge fastpath. Ha ez általános
  konvex esetekben hibás, az egész nesting engine hibás.
- A `edge_merge_equals_hull_on_all_fixtures` cross-check teszt csak annyit ér,
  amennyit a fixture-ök lefednek.
- A `convex.rs`-ben nincs `#[cfg(test)]` blokk — fehér doboz tesztek hiányoznak
  (NotConvex, EmptyPolygon, collinear merge, determinizmus közvetlen ellenőrzése).

**Nem cél:**
- Az edge-merge algoritmus módosítása
- A cache bekötése (külön task)
- Konkáv NFP (F2-2 task)
- Teljesítmény benchmark (külön task, F2-3 előtt)

---

## 🧠 Fejlesztési részletek

### Érintett fájlok

**Módosuló:**
- `rust/nesting_engine/src/nfp/convex.rs` — `#[cfg(test)]` blokk hozzáadása
- `rust/nesting_engine/tests/nfp_regression.rs` — új fixture-ök automatikusan lefutnak

**Új fájlok (fixtures):**
- `poc/nfp_regression/convex_rotated_rect.json`
- `poc/nfp_regression/convex_hexagon.json`
- `poc/nfp_regression/convex_skinny.json`
- `poc/nfp_regression/convex_collinear_edge.json`
- `poc/nfp_regression/convex_triangle.json`

**Nem módosul:**
- `rust/nesting_engine/src/nfp/mod.rs`
- `rust/nesting_engine/src/nfp/cache.rs`
- `rust/nesting_engine/src/geometry/types.rs`
- A meglévő 2 db fixture JSON (nem módosítandók)

---

### White-box unit tesztek (`convex.rs #[cfg(test)]`)

A következő tesztek kerülnek be mint közvetlen `#[cfg(test)]` blokk a `convex.rs`-be:

| Teszt neve | Mit ellenőriz |
|---|---|
| `test_not_convex_returns_err` | L-alak → `Err(NfpError::NotConvex)` |
| `test_empty_polygon_returns_err` | < 3 csúcs → `Err(NfpError::EmptyPolygon)` |
| `test_collinear_merge_no_extra_vertices` | Két azonos méretű téglalap: az NFP kontúr nem tartalmaz kollineáris extra csúcsot |
| `test_determinism` | Azonos input kétszer → bit-azonos csúcslista |
| `test_rect_rect_known_nfp` | 100×50 × 60×30 → kézzel számolt NFP (kicsit más mint az integrációs fixture, de konzisztens) |

### Fixture lefedettség tervezett esetek

#### 1. `convex_rotated_rect.json` — Elforgatott téglalap
```
polygon_a: 100×50 axis-aligned téglalap (CCW)
polygon_b: 60×30 téglalap 45°-kal elforgatva (CCW, kerekített koordinátán)
```
Ez az az eset, ahol az edge-merge szög-merge logikája nem triviális —
az élek szögei nem 0°/90°/180°/270°, a cross-sign komparátor nem esik
degenerált esetbe.

Expected NFP: kézzel számolható (Minkowski-definícióból), vagy hull-lal
előre kiszámítva és bejegyezve.

#### 2. `convex_hexagon.json` — Szabályos hatszög × téglalap
```
polygon_a: szabályos hatszög, r=50, CCW (6 csúcs, 60°-os szögek)
polygon_b: 40×20 axis-aligned téglalap (CCW)
```
Több csúcs, nem párhuzamos élek — az edge-merge merge loop n+m = 10 iteráció.

#### 3. `convex_skinny.json` — Skinny konvex (1:10 arány)
```
polygon_a: 10×100 keskeny téglalap (CCW)
polygon_b: 10×100 keskeny téglalap (CCW)
```
Két nagyon hasonló elnyúlt alak NFP-je — ez az eset szokta megmutatni
a numerikus instabilitást (közel-párhuzamos élek, `cross ≈ 0`).

#### 4. `convex_collinear_edge.json` — Collinear edge-merge eset
```
polygon_a: 100×50 téglalap (CCW)
polygon_b: 100×50 azonos méretű téglalap (CCW)
```
Azonos méretű téglalapok esetén az összes szemközti él párhuzamos
(cross == 0) → az összes él collinear merge ágon megy át.
Az NFP egy 200×100 téglalap — ezt pontosan lehet ellenőrizni.

#### 5. `convex_triangle.json` — Háromszög
```
polygon_a: egyenlő oldalú háromszög, oldalél=100, CCW
polygon_b: kisebb egyenlő oldalú háromszög, oldalél=50, CCW
```
3 csúcsos poligon — minimális eset, ahol az edge-merge n+m = 6 iteráció.

---

### Fixture formátum (változatlan)

```json
{
  "description": "...",
  "polygon_a": [[x,y], ...],
  "polygon_b": [[x,y], ...],
  "rotation_deg_b": 0,
  "expected_nfp": [[x,y], ...],
  "expected_vertex_count": N
}
```

Koordináták: integer egységben (nem mm, nem SCALE). A Rust teszt közvetlenül
`i64`-ként olvassa be, `canonicalize_ring` + egzakt `assert_eq!`.

Az `expected_nfp` kézzel számolt értékek **vagy** hull-lal előre kiszámított
és kézzel ellenőrzött értékek. Mindkét esetben: a fixture létrehozása előtt
a kézzel számolt értéket és a hull-os eredményt össze kell vetni.

---

### Pipálható feladatlista

- [ ] `convex.rs` `#[cfg(test)]` blokk: 5 unit teszt (lásd fenti táblázat)
- [ ] `convex_rotated_rect.json` fixture: koordináták + expected_nfp kiszámítva és ellenőrizve
- [ ] `convex_hexagon.json` fixture: koordináták + expected_nfp
- [ ] `convex_skinny.json` fixture: koordináták + expected_nfp
- [ ] `convex_collinear_edge.json` fixture: koordináták + expected_nfp
- [ ] `convex_triangle.json` fixture: koordináták + expected_nfp
- [ ] `fixture_library_passes` integrációs teszt PASS az összes új fixture-re
- [ ] `edge_merge_equals_hull_on_all_fixtures` cross-check PASS az összes új fixture-re

---

## 🧪 Tesztállapot

### DoD (Definition of Done)

- [ ] `convex.rs`-ben `#[cfg(test)]` blokk létezik ≥ 5 unit teszttel
- [ ] `test_not_convex_returns_err` PASS
- [ ] `test_empty_polygon_returns_err` PASS
- [ ] `test_collinear_merge_no_extra_vertices` PASS
- [ ] `test_determinism` PASS
- [ ] `test_rect_rect_known_nfp` PASS
- [ ] `poc/nfp_regression/` ≥ 7 fixture (2 meglévő + 5 új)
- [ ] `fixture_library_passes` PASS az összes (7) fixture-re
- [ ] `edge_merge_equals_hull_on_all_fixtures` PASS az összes (7) fixture-re
- [ ] `./scripts/verify.sh --report codex/reports/nesting_engine/nfp_fixture_expansion.md` PASS

### Kockázatok

| Kockázat | Valószínűség | Hatás | Mitigáció |
|---|---|---|---|
| Elforgatott téglalap expected_nfp kiszámítása hibás | Közepes | Fixture FAIL, de ez jó — megtalálja a hibát | Hull-lal előre kiszámítani és kézzel ellenőrizni |
| Skinny case numerikus instabilitás (cross ≈ 0 de nem == 0) | Közepes | edge-merge != hull → cross-check FAIL | Ez a kívánt viselkedés: a FAIL megmutatja a stabilitási határt |
| `convex.rs` unit tesztek sorszámfüggők (line number hivatkozások a reportban) | Alacsony | Report Evidence Matrix elavul | Ne sor-számot, hanem függvénynevet hivatkozzon a report |

---

## 🌍 Lokalizáció

Nem releváns (belső Rust modul + test fixtures).

---

## 📎 Kapcsolódások

**Előzmény (elvégzett):**
- `canvases/nesting_engine/nfp_computation_convex.md` — hull implementáció
- `canvases/nesting_engine/nfp_convex_edge_merge_fastpath.md` — edge-merge fastpath (PASS, `8673be9`)

**Következő task:**
- `canvases/nesting_engine/nfp_computation_concave.md` — F2-2 konkáv NFP

**Referencia:**
- `poc/nfp_regression/README.md` — fixture formátum leírás
- `rust/nesting_engine/tests/nfp_regression.rs` — integrációs teszt (automatikusan futtatja az új fixture-öket)