# Codex Report — nfp_convex_edge_merge_fastpath

**Status:** PASS_WITH_NOTES

---

## 1) Meta

- **Task slug:** `nfp_convex_edge_merge_fastpath`
- **Kapcsolódó canvas:** `canvases/nesting_engine/nfp_convex_edge_merge_fastpath.md`
- **Kapcsolódó goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_nfp_convex_edge_merge_fastpath.yaml`
- **Futás dátuma:** 2026-02-24
- **Branch / commit:** `main` / `8673be9` (uncommitted changes)
- **Fókusz terület:** Geometry

## 2) Scope

### 2.1 Cél

1. A konvex NFP számítás elsődleges útvonalának cseréje O(n+m) edge-merge fastpath-ra.
2. A meglévő O(nm log nm) hull megoldás megtartása referencia/fallback API-ként.
3. Fastpath-vs-reference keresztellenőrzés beépítése fixture szinten.

### 2.2 Nem-cél (explicit)

1. Konkáv NFP (F2-2) implementáció.
2. NFP cache vagy Python runner módosítás.
3. `rust/vrs_solver/` bármilyen módosítása.

## 3) Változások összefoglalója

### 3.1 Érintett fájlok

- `rust/nesting_engine/src/nfp/convex.rs`
- `rust/nesting_engine/tests/nfp_regression.rs`
- `codex/codex_checklist/nesting_engine/nfp_convex_edge_merge_fastpath.md`
- `codex/reports/nesting_engine/nfp_convex_edge_merge_fastpath.md`

### 3.2 Miért változtak?

- A fastpath csökkenti a konvex NFP költségét O(n+m)-re az eredményhelyesség megtartása mellett.
- A referencia hull implementáció külön API-ba került, így fallback és regressziós összevetés továbbra is elérhető.
- A fixture cross-check teszt garantálja, hogy a két útvonal konvex esetben ekvivalens.

## 4) Verifikáció

### 4.1 Kötelező parancs

- `./scripts/verify.sh --report codex/reports/nesting_engine/nfp_convex_edge_merge_fastpath.md` -> lásd AUTO_VERIFY blokk.

### 4.2 Opcionális, task-specifikus parancsok

- `cargo test --manifest-path rust/nesting_engine/Cargo.toml --test nfp_regression` -> PASS.
- `cargo test --manifest-path rust/nesting_engine/Cargo.toml` -> PASS.

### 4.3 Ha valami kimaradt

- Nincs kimaradt kötelező ellenőrzés.

## 5) DoD -> Evidence Matrix

| DoD pont | Státusz | Bizonyíték (path + line) | Magyarázat | Kapcsolódó teszt/ellenőrzés |
|---|---|---|---|---|
| `compute_convex_nfp()` edge-merge fastpath | PASS | `rust/nesting_engine/src/nfp/convex.rs:6` | A publikus API él-vektor merge logikát használ i/j mutatókkal és prefix-sum kontúrépítéssel. | `cargo test --manifest-path rust/nesting_engine/Cargo.toml` |
| `compute_convex_nfp_reference()` hull referencia/fallback | PASS | `rust/nesting_engine/src/nfp/convex.rs:106` | A korábbi pairwise sums + convex hull implementáció külön referenciafüggvénybe került. | `cargo test --manifest-path rust/nesting_engine/Cargo.toml` |
| Fixture regresszió PASS az új fastpath-on | PASS | `rust/nesting_engine/tests/nfp_regression.rs:19` | A meglévő `fixture_library_passes` változatlanul az új API-t hívja. | `cargo test --manifest-path rust/nesting_engine/Cargo.toml --test nfp_regression` |
| Új cross-check: edge-merge == hull minden fixture-re | PASS | `rust/nesting_engine/tests/nfp_regression.rs:73` | Új teszt minden fixture-re kanonizált ring összehasonlítást végez. | `cargo test --manifest-path rust/nesting_engine/Cargo.toml --test nfp_regression` |
| `cross==0` collinear merge kezelése | PASS | `rust/nesting_engine/src/nfp/convex.rs:60` | A merge comparator null cross esetén összeadott élvektort pushol (i++, j++). | `cargo test --manifest-path rust/nesting_engine/Cargo.toml` |
| Determinizmus azonos inputra | PASS | `rust/nesting_engine/src/nfp/convex.rs:381` | A lexikografikus kezdőpont (`argmin_lex`) és a determinism unit teszt együtt fix kimeneti sorrendet ad. | `cargo test --manifest-path rust/nesting_engine/Cargo.toml` |
| Kötelező repo gate wrapperrel futtatva | PASS | `codex/reports/nesting_engine/nfp_convex_edge_merge_fastpath.md:76` | A verify.sh automatikus blokk tartalmazza a check.sh futás eredményét és a log hivatkozást. | `./scripts/verify.sh --report codex/reports/nesting_engine/nfp_convex_edge_merge_fastpath.md` |

## 8) Advisory notes

- A crate bináris célja továbbra is adhat `dead_code` warningot bizonyos geometry helper függvényekre.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-02-24T01:12:52+01:00 → 2026-02-24T01:15:49+01:00 (177s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/nesting_engine/nfp_convex_edge_merge_fastpath.verify.log`
- git: `main@8673be9`
- módosított fájlok (git status): 8

**git diff --stat**

```text
 rust/nesting_engine/src/nfp/convex.rs       | 156 +++++++++++++++++++++++++++-
 rust/nesting_engine/tests/nfp_regression.rs |  38 ++++++-
 2 files changed, 190 insertions(+), 4 deletions(-)
```

**git status --porcelain (preview)**

```text
 M rust/nesting_engine/src/nfp/convex.rs
 M rust/nesting_engine/tests/nfp_regression.rs
?? canvases/nesting_engine/nfp_convex_edge_merge_fastpath.md
?? codex/codex_checklist/nesting_engine/nfp_convex_edge_merge_fastpath.md
?? codex/goals/canvases/nesting_engine/fill_canvas_nfp_convex_edge_merge_fastpath.yaml
?? codex/prompts/nesting_engine/nfp_convex_edge_merge_fastpath/
?? codex/reports/nesting_engine/nfp_convex_edge_merge_fastpath.md
?? codex/reports/nesting_engine/nfp_convex_edge_merge_fastpath.verify.log
```

<!-- AUTO_VERIFY_END -->
