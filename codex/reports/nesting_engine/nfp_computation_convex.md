# Codex Report — nfp_computation_convex

**Status:** PASS_WITH_NOTES

---

## 1) Meta

- **Task slug:** `nfp_computation_convex`
- **Kapcsolódó canvas:** `canvases/nesting_engine/nfp_computation_convex.md`
- **Kapcsolódó goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_nfp_computation_convex.yaml`
- **Futás dátuma:** 2026-02-23
- **Branch / commit:** `main` / `39674a8` (uncommitted changes)
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

- `./scripts/verify.sh --report codex/reports/nesting_engine/nfp_computation_convex.md` -> lásd AUTO_VERIFY blokk.

### 4.2 Opcionális, task-specifikus parancsok

- `cargo test --manifest-path rust/nesting_engine/Cargo.toml -q` -> PASS.

### 4.3 Ha valami kimaradt

- Nincs kimaradt kötelező ellenőrzés.

## 5) DoD -> Evidence Matrix

| DoD pont | Státusz | Bizonyíték (path + line) | Magyarázat | Kapcsolódó teszt/ellenőrzés |
|---|---|---|---|---|
| `compute_convex_nfp()` legalább 4 unit teszt PASS | PASS | `rust/nesting_engine/src/nfp/convex.rs:142` | 7 unit teszt került be (kézi referencia + hibaág + determinizmus). | `cargo test --manifest-path rust/nesting_engine/Cargo.toml -q` |
| Nem-konvex bemenet -> `Err(NfpError::NotConvex)` | PASS | `rust/nesting_engine/src/nfp/convex.rs:176` | A konkáv polygon teszt explicit `NotConvex` hibát vár. | `cargo test --manifest-path rust/nesting_engine/Cargo.toml -q` |
| Üres polygon -> `Err(NfpError::EmptyPolygon)` | PASS | `rust/nesting_engine/src/nfp/convex.rs:194` | Az üres outer gyűrű `EmptyPolygon` hibával tér vissza. | `cargo test --manifest-path rust/nesting_engine/Cargo.toml -q` |
| `NfpError` enum csak `NotConvex` + `EmptyPolygon` | PASS | `rust/nesting_engine/src/nfp/mod.rs:7` | Az error enumban nincs `InvalidInput` variáns, csak a két elvárt ág. | `cargo test --manifest-path rust/nesting_engine/Cargo.toml -q` |
| `cross_product_i128()` helper létezik és i128-at használ | PASS | `rust/nesting_engine/src/geometry/types.rs:24` | A helper i128-on számol; a konvexitás és hull turn-check ezt használja. | `cargo test --manifest-path rust/nesting_engine/Cargo.toml -q` |
| `NfpCacheKey.rotation_steps_b` típusa `i16` | PASS | `rust/nesting_engine/src/nfp/cache.rs:9` | A cache kulcs diszkrét i16 lépésindexet használ, f64 nélkül. | `rg -n "rotation_steps_b|f64" rust/nesting_engine/src/nfp/cache.rs` |
| Cache hit/miss statisztika debug szinten logolva | PASS | `rust/nesting_engine/src/nfp/cache.rs:59` | `debug_log_stats()` `eprintln!` debug loggal jelzi a hit/miss/insert eseményeket. | `cargo test --manifest-path rust/nesting_engine/Cargo.toml -q` |
| Determinizmus: azonos input -> azonos kimenet | PASS | `rust/nesting_engine/src/nfp/convex.rs:206` | Unit teszt kétszeri futtatásnál azonos csúcslistát vár; fixture teszt is ellenőrzi. | `cargo test --manifest-path rust/nesting_engine/Cargo.toml -q` |
| `poc/nfp_regression/` >= 2 fixture | PASS | `poc/nfp_regression/convex_rect_rect.json:1` | Két referenciafixture készült (`rect_rect`, `rect_square`) + README formátumleírás. | N/A |
| Fixture koordináták integer egységűek | PASS | `poc/nfp_regression/README.md:9` | A fixture szerződés explicit integer koordinátát rögzít, mm/SCALE konverzió nélkül. | `cargo test --manifest-path rust/nesting_engine/Cargo.toml -q` |
| Integrációs regressziós teszt PASS | PASS | `rust/nesting_engine/tests/nfp_regression.rs:18` | A teszt fixture betöltést, `canonicalize_ring` + egzakt `assert_eq!` egyezést és determinizmust ellenőriz. | `cargo test --manifest-path rust/nesting_engine/Cargo.toml -q` |
| Kötelező repo gate wrapperrel futtatva | PASS | `codex/reports/nesting_engine/nfp_computation_convex.md` | Az eredmény és log hivatkozás automatikusan a verify blokkba kerül. | `./scripts/verify.sh --report codex/reports/nesting_engine/nfp_computation_convex.md` |

## 8) Advisory notes

- A package jelenleg bináris+library célt is épít; emiatt a bináris targetben a frissen bevezetett geometry helper-ekre `dead_code` warning látszik.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-02-24T00:47:25+01:00 → 2026-02-24T00:50:40+01:00 (195s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/nesting_engine/nfp_computation_convex.verify.log`
- git: `main@39674a8`
- módosított fájlok (git status): 10

**git diff --stat**

```text
 canvases/nesting_engine/nfp_computation_convex.md  | 105 ++++++++++++++++-----
 .../nesting_engine/nfp_computation_convex.md       |   3 +
 .../fill_canvas_nfp_computation_convex.yaml        | 103 +++++++++++---------
 .../nesting_engine/nfp_computation_convex/run.md   |  42 +++++++--
 .../nesting_engine/nfp_computation_convex.md       |   8 +-
 .../nfp_computation_convex.verify.log              |  49 +++++-----
 rust/nesting_engine/src/geometry/types.rs          |  12 +++
 rust/nesting_engine/src/nfp/cache.rs               |   5 +
 rust/nesting_engine/src/nfp/convex.rs              |  34 +++++++
 rust/nesting_engine/src/nfp/mod.rs                 |   6 ++
 10 files changed, 266 insertions(+), 101 deletions(-)
```

**git status --porcelain (preview)**

```text
 M canvases/nesting_engine/nfp_computation_convex.md
 M codex/codex_checklist/nesting_engine/nfp_computation_convex.md
 M codex/goals/canvases/nesting_engine/fill_canvas_nfp_computation_convex.yaml
 M codex/prompts/nesting_engine/nfp_computation_convex/run.md
 M codex/reports/nesting_engine/nfp_computation_convex.md
 M codex/reports/nesting_engine/nfp_computation_convex.verify.log
 M rust/nesting_engine/src/geometry/types.rs
 M rust/nesting_engine/src/nfp/cache.rs
 M rust/nesting_engine/src/nfp/convex.rs
 M rust/nesting_engine/src/nfp/mod.rs
```

<!-- AUTO_VERIFY_END -->
