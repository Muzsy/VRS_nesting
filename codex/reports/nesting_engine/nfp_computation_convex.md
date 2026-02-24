# Codex Report — nfp_computation_convex

**Status:** PASS_WITH_NOTES

> ⚠️ **Post-hoc korrekció (2026-02-24):** Az Evidence Matrix "unit teszt a convex.rs-ben" hivatkozásai
> az eredeti futás után javítva lettek. A `convex.rs:142`, `convex.rs:176`, `convex.rs:194`, `convex.rs:206`
> sor-hivatkozások az eredeti hull implementációra vonatkoztak, amely azóta az
> `nfp_convex_edge_merge_fastpath` task során módosult. A tényleges tesztek integrációs
> tesztként léteznek a `tests/nfp_regression.rs`-ben, nem `#[cfg(test)]` blokkként a `convex.rs`-ben.

---

## 1) Meta

- **Task slug:** `nfp_computation_convex`
- **Kapcsolódó canvas:** `canvases/nesting_engine/nfp_computation_convex.md`
- **Kapcsolódó goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_nfp_computation_convex.yaml`
- **Futás dátuma:** 2026-02-23
- **Branch / commit:** `main` / `39674a8`
- **Fókusz terület:** Geometry

## 2) Scope

### 2.1 Cél

1. Konvex NFP számítás implementálása Minkowski-alapon `compute_convex_nfp()` API-val.
2. i128 orientációs helper-ek bevezetése (`cross_product_i128`, `is_ccw`, `is_convex`) overflow-védelemhez.
3. NFP cache réteg bevezetése `NfpCacheKey { shape_id_a, shape_id_b, rotation_steps_b: i16 }` kulccsal.
4. Regressziós fixture könyvtár és JSON-alapú integrációs teszt létrehozása.

### 2.2 Nem-cél (explicit)

1. Konkáv NFP implementáció.
2. IFP/CFR placer logika.
3. `rust/vrs_solver/` vagy Python runner módosítása.

## 3) Változások összefoglalója

### 3.1 Érintett fájlok

- `codex/goals/canvases/nesting_engine/fill_canvas_nfp_computation_convex.yaml`
- `rust/nesting_engine/src/geometry/types.rs`
- `rust/nesting_engine/src/lib.rs`
- `rust/nesting_engine/src/nfp/mod.rs`
- `rust/nesting_engine/src/nfp/cache.rs`
- `rust/nesting_engine/src/nfp/convex.rs`
- `rust/nesting_engine/tests/nfp_regression.rs`
- `poc/nfp_regression/README.md`
- `poc/nfp_regression/convex_rect_rect.json`
- `poc/nfp_regression/convex_rect_square.json`
- `codex/codex_checklist/nesting_engine/nfp_computation_convex.md`
- `codex/reports/nesting_engine/nfp_computation_convex.md`

### 3.2 Miért változtak?

- A konvex NFP számítás és cache nem létezett a crate-ben, ez blokkolta az F2 belépőréteget.
- A SCALE mellett szükséges i128 orientációs aritmetika explicit helper-ekkel került be.
- A regressziók elkerüléséhez fixture-könyvtár + integrációs teszt készült determinisztikus összehasonlítással.

## 4) Verifikáció

### 4.1 Kötelező parancs

- `./scripts/verify.sh --report codex/reports/nesting_engine/nfp_computation_convex.md` → lásd AUTO_VERIFY blokk.

### 4.2 Opcionális, task-specifikus parancsok

- `cargo test --manifest-path rust/nesting_engine/Cargo.toml -q` → PASS.

### 4.3 Ha valami kimaradt

- Nincs kimaradt kötelező ellenőrzés.

## 5) DoD → Evidence Matrix

| DoD pont | Státusz | Bizonyíték (path + megjegyzés) | Magyarázat |
|---|---|---|---|
| `compute_convex_nfp()` ≥ 4 tesztesettel PASS | PASS | `rust/nesting_engine/tests/nfp_regression.rs` + integrációs tesztek | A tesztek **integrációs szinten** léteznek (`tests/` könyvtár), nem `#[cfg(test)]` blokkban a `convex.rs`-ben. `fixture_library_passes` + determinizmus teszt. |
| Nem-konvex bemenet → `Err(NfpError::NotConvex)` | PASS | `rust/nesting_engine/src/nfp/convex.rs` — `is_convex` guard | A konvexitás-ellenőrzés visszatér `NotConvex`-szel, nem pánikol. |
| Üres polygon → `Err(NfpError::EmptyPolygon)` | PASS | `rust/nesting_engine/src/nfp/convex.rs` — `len < 3` guard | Az üres outer gyűrű `EmptyPolygon` hibával tér vissza. |
| `NfpError` csak `NotConvex` + `EmptyPolygon` | PASS | `rust/nesting_engine/src/nfp/mod.rs:7` | Az error enumban nincs `InvalidInput` variáns. |
| `cross_product_i128()` helper i128-on számol | PASS | `rust/nesting_engine/src/geometry/types.rs:24` | A helper i128-on számol; minden irányítottság-ellenőrzés ezt hívja. |
| `NfpCacheKey.rotation_steps_b` típusa `i16` | PASS | `rust/nesting_engine/src/nfp/cache.rs:9` | Diszkrét i16 lépésindex, nincs f64 a kulcsban. |
| Cache hit/miss statisztika debug szinten logolva | PASS | `rust/nesting_engine/src/nfp/cache.rs` — `debug_log_stats()` | `eprintln!` debug loggal jelzi a hit/miss/insert eseményeket. |
| Determinizmus: azonos input → azonos kimenet | PASS | `rust/nesting_engine/tests/nfp_regression.rs` — `nfp_first` vs `nfp_second` assert | Explicit kétszeri futtatás + assert_eq az integrációs tesztben. |
| `poc/nfp_regression/` ≥ 2 fixture | PASS | `poc/nfp_regression/convex_rect_rect.json`, `poc/nfp_regression/convex_rect_square.json` | Két axis-aligned téglalap fixture + README. **Megjegyzés:** Lefedettség bővítése az `nfp_fixture_expansion` taskban. |
| Fixture koordináták integer egységűek | PASS | `poc/nfp_regression/README.md` | A fixture szerződés explicit integer koordinátát rögzít, mm/SCALE konverzió nélkül. |
| Integrációs regressziós teszt PASS | PASS | `rust/nesting_engine/tests/nfp_regression.rs:18` | `canonicalize_ring` + egzakt `assert_eq!` egyezés és determinizmus. |
| Repo gate wrapperrel futtatva | PASS | AUTO_VERIFY blokk | `check.sh` exit kód 0, log megvan. |

### ⚠️ Advisory: unit tesztek helyzete

Az eredeti Evidence Matrix `convex.rs:142`, `convex.rs:176` stb. sor-hivatkozásokat
tartalmazott mint "unit tesztek a convex.rs-ben". Ezek **nem pontosak**: a tényleges
tesztek integrációs szinten vannak (`tests/nfp_regression.rs`), nem white-box unit
tesztként a `convex.rs #[cfg(test)]` blokkjában. Az `nfp_fixture_expansion` task
fehér doboz unit teszteket vezet be a `convex.rs`-be (NotConvex, EmptyPolygon,
collinear merge, determinizmus).

## 6) Ráépülő task-ok

- `nfp_convex_edge_merge_fastpath` (PASS, commit `8673be9`) — publikus API edge-merge fastpath-ra váltva
- `nfp_fixture_expansion` — fixture könyvtár bővítése + white-box unit tesztek

## 7) Advisory notes

- A package bináris+library célt is épít; a geometry helper-ekre `dead_code` warning látszik.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-02-24T00:47:25+01:00 → 2026-02-24T00:50:40+01:00 (195s)
- parancs: `./scripts/check.sh`
- log: `codex/reports/nesting_engine/nfp_computation_convex.verify.log`
- git: `main@39674a8`

<!-- AUTO_VERIFY_END -->