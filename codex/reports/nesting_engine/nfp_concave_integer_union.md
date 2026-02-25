# Codex Report — nfp_concave_integer_union

**Status:** PASS_WITH_NOTES

---

## 1) Meta

- **Task slug:** `nfp_concave_integer_union`
- **Kapcsolódó canvas:** `canvases/nesting_engine/nfp_concave_integer_union.md`
- **Kapcsolódó goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_nfp_concave_integer_union.yaml`
- **Futás dátuma:** 2026-02-25
- **Branch / commit:** `main` / `841f1d5` (uncommitted changes)
- **Fókusz terület:** Geometry

## 2) Scope

### 2.1 Cél

1. A concave stable baseline `union_nfp_fragments()` útvonalból a `FloatOverlay` teljes eltávolítása.
2. Integer-only union bevezetése `i_overlay::core::overlay::Overlay` API-val.
3. Regressziós védelem beépítése, hogy a float overlay import ne tudjon visszacsúszni.
4. KI-007 scope-frissítés: ez a task kizárólag a concave baseline union float driftet kezeli.

### 2.2 Nem-cél (explicit)

1. Orbitális exact algoritmus fejlesztése.
2. Holes támogatás a concave baseline unionban.
3. `scripts/*` wrapper vagy `rust/vrs_solver/**` módosítás.
4. Az `offset` / `feasibility` / `pipeline` további float útvonalainak kezelése.

## 3) Változások összefoglalója

### 3.1 Érintett fájlok

- `canvases/nesting_engine/nfp_concave_integer_union.md`
- `rust/nesting_engine/src/nfp/concave.rs`
- `docs/known_issues/nesting_engine_known_issues.md`
- `rust/nesting_engine/tests/nfp_no_float_overlay.rs`
- `codex/codex_checklist/nesting_engine/nfp_concave_integer_union.md`
- `codex/reports/nesting_engine/nfp_concave_integer_union.md`

### 3.2 Miért változtak?

- A `concave.rs` union útvonal integer-only overlay-re lett cserélve, a float union drift lezárására.
- A guard teszt explicit forrásszintű tiltást ad a `FloatOverlay` / `i_overlay::float` visszacsúszásra.
- A KI-007 bejegyzés scope-ja pontosítva lett, hogy ez csak részprobléma-feloldás.
- A canvas/report/checklist frissült a felderítési bizonyítékokkal és DoD-evidence leképezéssel.

## 4) Verifikáció

### 4.1 Kötelező parancs

- `./scripts/verify.sh --report codex/reports/nesting_engine/nfp_concave_integer_union.md` -> PASS (lásd AUTO_VERIFY blokk).

### 4.2 Opcionális, task-specifikus parancsok

- `cargo test --manifest-path rust/nesting_engine/Cargo.toml --test nfp_regression --test nfp_no_float_overlay` -> PASS.

### 4.3 Ha valami kimaradt

- Nincs kimaradt kötelező ellenőrzés; a verify eredmény az AUTO_VERIFY blokkban kerül rögzítésre.

## 5) DoD -> Evidence Matrix

| DoD pont | Státusz | Bizonyíték (path + line) | Magyarázat | Kapcsolódó teszt/ellenőrzés |
|---|---|---|---|---|
| concave.rs-ben nincs FloatOverlay / `i_overlay::float` union import | PASS | `rust/nesting_engine/src/nfp/concave.rs:5`, `rust/nesting_engine/tests/nfp_no_float_overlay.rs:1` | A `concave.rs` import blokk csak integer overlay API-t használ; külön guard teszt ellenőrzi a tiltott stringeket. | `cargo test --manifest-path rust/nesting_engine/Cargo.toml --test nfp_no_float_overlay` |
| A union integer-only útvonalon fut | PASS | `rust/nesting_engine/src/nfp/concave.rs:313`, `/home/muszy/.cargo/registry/src/index.crates.io-1949cf8c6b5b557f/i_overlay-4.4.0/src/core/overlay.rs:173` | A `union_nfp_fragments()` `Overlay::with_shapes_options(...).overlay(...)` hívást használ; az upstream API integer `IntShape/IntPoint` típusokon működik. | `cargo test --manifest-path rust/nesting_engine/Cargo.toml --test nfp_regression` |
| Concave fixture regressziók PASS | PASS | `rust/nesting_engine/tests/nfp_regression.rs:90` | A concave fixture library teszt ellenőrzi a csúcsszámot, canonical ring egyezést, determinisztikát és self-intersection hiányát. | `cargo test --manifest-path rust/nesting_engine/Cargo.toml --test nfp_regression` |
| `boundary_clean` továbbra is kötelező a concave stable baseline kimenet végén | PASS | `rust/nesting_engine/src/nfp/concave.rs:93` | A stable baseline változatlanul `clean_polygon_boundary(&unioned)` hívással tér vissza. | `cargo test --manifest-path rust/nesting_engine/Cargo.toml --test nfp_regression` |
| Kötelező repo gate wrapperrel futtatva | PASS | `codex/reports/nesting_engine/nfp_concave_integer_union.md` | A `verify.sh` wrapper lefutott, a gate zöld, az AUTO_VERIFY blokkban rögzített futásidővel és log hivatkozással. | `./scripts/verify.sh --report codex/reports/nesting_engine/nfp_concave_integer_union.md` |

## 8) Advisory notes

- Az integer overlay API `i32` koordinátatartományon fut; a `Point64(i64)` bemenethez determinisztikus normalizáció+shift került be, hogy a union útvonal ne használjon float döntést.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-02-25T01:43:59+01:00 → 2026-02-25T01:47:10+01:00 (191s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/nesting_engine/nfp_concave_integer_union.verify.log`
- git: `main@841f1d5`
- módosított fájlok (git status): 10

**git diff --stat**

```text
 docs/known_issues/nesting_engine_known_issues.md |   7 +-
 rust/nesting_engine/src/nfp/concave.rs           | 251 +++++++++++++++++++++--
 2 files changed, 242 insertions(+), 16 deletions(-)
```

**git status --porcelain (preview)**

```text
 M docs/known_issues/nesting_engine_known_issues.md
 M rust/nesting_engine/src/nfp/concave.rs
?? MEMORY.md
?? canvases/nesting_engine/nfp_concave_integer_union.md
?? codex/codex_checklist/nesting_engine/nfp_concave_integer_union.md
?? codex/goals/canvases/nesting_engine/fill_canvas_nfp_concave_integer_union.yaml
?? codex/prompts/nesting_engine/nfp_concave_integer_union/
?? codex/reports/nesting_engine/nfp_concave_integer_union.md
?? codex/reports/nesting_engine/nfp_concave_integer_union.verify.log
?? rust/nesting_engine/tests/nfp_no_float_overlay.rs
```

<!-- AUTO_VERIFY_END -->
