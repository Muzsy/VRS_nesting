# canvases/nesting_engine/nfp_convex_edge_merge_fastpath.md

> **Mentés helye a repóban:** `canvases/nesting_engine/nfp_convex_edge_merge_fastpath.md`
> **TASK_SLUG:** `nfp_convex_edge_merge_fastpath`
> **Terület (AREA):** `nesting_engine`

---

# NFP Nesting Engine — Konvex NFP edge-merge fastpath

## 🎯 Funkció

A meglévő `compute_convex_nfp()` (pairwise vertex sums + convex hull, O(n×m×log))
mellé egy **O(n+m) edge-merge fastpath** bevezetése. Ez lesz az elsődleges
(`fast`) útvonal; a hull implementáció referencia- és fallback-funkcióba kerül.

**Miért szükséges:** A nesting engine-ben a konvex NFP tömegesen hívódik:
placement loop, cache miss-enként, rotációs variánsoknál, és az F2-2 konkáv
fallback-jában konvex dekompozíció esetén. O(n×m) csúcspár-generálás inflate
utáni 200–400 csúcsos poligonoknál 40k–160k pontot jelent hívásonként —
ez cache mellett is domináns költséggé válhat sok egyedi alak-párra.

**Nem cél:**
- A hull implementáció eltávolítása (referencia + fallback marad)
- Konkáv NFP implementáció (F2-2 task)
- IFP / CFR / SA (F2-3, F2-4 task)
- `rust/vrs_solver/` bármilyen módosítása

---

## 🧠 Fejlesztési részletek

### Érintett fájlok

**Módosuló (meglévő):**
- `rust/nesting_engine/src/nfp/convex.rs` — edge-merge fastpath hozzáadása,
  hull → referencia/fallback átnevezés, publikus API frissítése

**Nem módosul:**
- `rust/nesting_engine/src/nfp/cache.rs` — cache API változatlan
- `rust/nesting_engine/src/nfp/mod.rs` — NfpError változatlan
- `rust/nesting_engine/src/geometry/types.rs` — helperek változatlanok
- `poc/nfp_regression/*.json` — fixture-ök változatlanok
- `rust/nesting_engine/tests/nfp_regression.rs` — **bővítendő** (cross-check teszt)

**Bővítendő:**
- `rust/nesting_engine/tests/nfp_regression.rs` — edge-merge vs. hull keresztellenőrzés

---

### Algoritmikus specifikáció — edge-merge (O(n+m))

#### Előfeltételek (azonosak a hull-lal)
- Mindkét poligon CCW, konvex, legalább 3 csúcs
- Duplikált szomszédos csúcsok és záró ismétlés eltávolítva (`normalize_ring`)

#### Az algoritmus lépései

**1. Stabil kezdőpont kiválasztása**

Mindkét poligonban megkeressük a lexikografikusan legkisebb csúcsot:
```
start_a = argmin_lex(a_outer)   // legkisebb (x, y)
start_b = argmin_lex(b_neg)     // legkisebb (x, y) a tükrözött B-n
```
A B tükrözése: `b_neg[i] = (-b[i].x, -b[i].y)`, majd A és b_neg mindkét
listája `start_a` / `start_b` indextől rotálva (CCW).

**2. Él-vektorok kinyerése**

```
eA[i] = A[(start_a + i + 1) % n] - A[(start_a + i) % n]
eB[j] = B_neg[(start_b + j + 1) % m] - B_neg[(start_b + j) % m]
```

**3. Szög-merge (merge-sort logika)**

Két mutató (`i`, `j`) indul 0-ról. Minden lépésben:
- Számoljuk `cross = cross_product_i128(eA[i], eB[j])`
- Ha `cross > 0`: eA[i] "kisebb szögű" → kimeneti él += eA[i], i++
- Ha `cross < 0`: eB[j] "kisebb szögű" → kimeneti él += eB[j], j++
- Ha `cross == 0`: párhuzamos élek → kimeneti él += eA[i] + eB[j], i++, j++
  *(collinear merge — ez szünteti meg a kollineáris duplikációkat)*

Folytatás amíg `i < n && j < m`, majd a maradék élek hozzáfűzése.

**4. Kontúrpontok prefix-sum-mal**

Kezdőpont: `A[start_a] + B_neg[start_b]`

```
p[0] = A[start_a] + B_neg[start_b]
p[k+1] = p[k] + merged_edges[k]
```

**5. Kimenet**
CCW irányú `Polygon64`, holes üres. Az utolsó csúcs egyezik az elsővel
(zárt kontúr) — normalize_ring eltávolítja a duplikációt.

---

### Publikus API (frissített)

```rust
/// Gyors O(n+m) edge-merge Minkowski-összeg.
/// Előfeltétel: a, b konvex, CCW, >= 3 csúcs.
/// Ha a bemenet nem teljesíti: Err(NfpError::NotConvex / EmptyPolygon).
pub fn compute_convex_nfp(a: &Polygon64, b: &Polygon64) -> Result<Polygon64, NfpError>

/// Referencia / fallback: pairwise sums + hull (O(nm log nm)).
/// Használat: keresztellenőrzés, degenerált bemenetek, tesztelés.
pub fn compute_convex_nfp_reference(a: &Polygon64, b: &Polygon64) -> Result<Polygon64, NfpError>
```

A `compute_convex_nfp()` az edge-merge fast path-ot hívja.
A `compute_convex_nfp_reference()` a jelenlegi hull implementáció,
átnevezve — semmi sem törlődik.

---

### Cross-check teszt (kötelező)

Az `nfp_regression.rs`-be új tesztfüggvény kerül:

```
fn edge_merge_equals_hull_on_all_fixtures()
```

Minden fixture-re:
1. `compute_convex_nfp()` → edge-merge eredmény
2. `compute_convex_nfp_reference()` → hull eredmény
3. `assert_eq!(canonicalize(edge_merge), canonicalize(hull))`

Ez garantálja, hogy a két implementáció konvex esetben azonos NFP-t ad.

---

### Overflow és determinizmus

A `cross_product_i128()` helper az edge-merge merge-sort komparátorában
is kötelező — közvetlen i64 szorzat tilos.

Determinizmus forrása az edge-merge-ben:
- Lexikografikusan stabil kezdőpont (nem a "legalsó" mint SVGNest-ben,
  hanem lex. min (x,y) — azonos a hull kimenet kezdőpontjával)
- Fix merge-sort sorrend párhuzamos éleknél (`cross == 0` ág)

---

### Komplexitás összefoglaló

| Módszer | Komplexitás | Kollinearitás | Kezdőpont |
|---|---|---|---|
| Edge-merge (új fast path) | O(n+m) | collinear merge (`cross==0`) | lex. min (x,y) |
| Hull (referencia/fallback) | O(n×m×log(n×m)) | turn<=0 eltávolít | lex. min (x,y) |

---

### Pipálható feladatlista

- [ ] `compute_convex_nfp_reference()` átnevezés (jelenlegi hull kód, semmi sem törlődik)
- [ ] `compute_convex_nfp()` új implementáció: edge-merge fastpath
- [ ] `b_neg` tükrözés + `normalize_ring` előfeldolgozás
- [ ] Lexikografikus kezdőpont (`argmin_lex`) mindkét poligonon
- [ ] Él-vektor kinyerés + szög-merge loop (`cross_product_i128` alapú)
- [ ] Párhuzamos él kezelés (`cross == 0`: collinear merge)
- [ ] Prefix-sum kontúrépítés + `normalize_ring` kimenet
- [ ] Unit tesztek edge-merge-re (rect×rect, square×square, párhuzamos élek esete)
- [ ] `nfp_regression.rs` bővítése: `edge_merge_equals_hull_on_all_fixtures()`

---

## 🧪 Tesztállapot

### DoD (Definition of Done)

- [ ] `compute_convex_nfp()` az edge-merge implementációt hívja (nem a hull-t)
- [ ] `compute_convex_nfp_reference()` a hull implementáció (átnevezve, változatlan logika)
- [ ] A meglévő fixture regressziós teszt (`fixture_library_passes`) PASS marad — edge-merge-re fut
- [ ] Új cross-check teszt: `edge_merge_equals_hull_on_all_fixtures()` PASS
  (minden fixture-re `canonicalize(edge_merge) == canonicalize(hull)`)
- [ ] Párhuzamos élek (`cross == 0`) collinear merge kezelése unit teszttel igazolva
- [ ] Determinisztikus output: azonos input kétszer → azonos NFP csúcslista
- [ ] `cross_product_i128()` az egyetlen szorzási útvonal a merge komparátorban
- [ ] A meglévő F1 gate-ek nem sérülnek (0 overlap, 0 out-of-bounds, determinism hash)
- [ ] `./scripts/verify.sh --report codex/reports/nesting_engine/nfp_convex_edge_merge_fastpath.md` PASS

### Kockázatok és rollback terv

| Kockázat | Valószínűség | Hatás | Mitigáció |
|---|---|---|---|
| Helytelen kezdőpont → az edge-merge != hull kimenet | Közepes | Cross-check teszt FAIL | `argmin_lex` unit teszt; canonicalize cross-check kötelező |
| Párhuzamos élek (`cross==0`) hibás kezelése → extra csúcs vagy hiányzó kontúrszakasz | Közepes | Hibás NFP, overlap F2-3-ban | Dedikált unit teszt párhuzamos élű poligon-párra |
| `i128` elmarad a merge komparátorból | Magas (ha nem figyelsz) | Csendesen helytelen merge sorrend | `cross_product_i128` kötelező, i64 szorzat tilos |
| CCW nem garantált → helytelen él-sorrend | Alacsony | Hibás merge irány | Ugyanaz az `is_ccw + reverse` logika mint a hull-ban |

**Rollback:** Ha a cross-check teszt (`edge_merge_equals_hull`) nem PASS, a `compute_convex_nfp()` visszakapja a hull implementációt, és az edge-merge `_wip` suffixszel, csak tesztelési kontextusban marad. Az F2-2/F2-3 task-ok a hull-ra épülve is megkezdhetők.

---

## 🌍 Lokalizáció

Nem releváns (belső Rust modul).

---

## 📎 Kapcsolódások

**Előzmény (elvégzett):**
- `canvases/nesting_engine/nfp_computation_convex.md` — hull implementáció (referencia alap)
- `rust/nesting_engine/src/nfp/convex.rs` — módosítandó fájl
- `rust/nesting_engine/tests/nfp_regression.rs` — bővítendő cross-check teszttel

**Következő task (ez után):**
- `canvases/nesting_engine/nfp_computation_concave.md` — F2-2 konkáv NFP

**Kutatási referencia:**
- Burke, Kendall, Whitwell (2007): §3 "Edge vector merge" pszeudokód
- `poc/nfp_regression/` — meglévő fixture-ök (cross-check alapja)
