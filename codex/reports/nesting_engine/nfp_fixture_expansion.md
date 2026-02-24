# Codex Report — nfp_fixture_expansion

**Status:** PASS_WITH_NOTES

---

## 1) Meta

- **Task slug:** `nfp_fixture_expansion`
- **Kapcsolódó canvas:** `canvases/nesting_engine/nfp_fixture_expansion.md`
- **Kapcsolódó goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_nfp_fixture_expansion.yaml`
- **Futás dátuma:** 2026-02-24
- **Branch / commit:** `main` / `588fefb` (uncommitted changes)
- **Fókusz terület:** Geometry

## 2) Scope

### 2.1 Cél

1. White-box unit tesztek bevezetése a `compute_convex_nfp()` fastpath viselkedésére.
2. Fixture könyvtár bővítése 5 új konvex esettel.
3. Fixture invariánsok explicit ellenőrzése (`is_convex`, `is_ccw`) és hull-vs-edge cross-check fenntartása.

### 2.2 Nem-cél (explicit)

1. Edge-merge algoritmus módosítása.
2. Konkáv NFP vagy cache integráció.
3. Teljesítmény benchmark.

## 3) Változások összefoglalója

### 3.1 Érintett fájlok

- **Rust:**
  - `rust/nesting_engine/src/nfp/convex.rs`
  - `rust/nesting_engine/tests/nfp_regression.rs`
- **Fixtures:**
  - `poc/nfp_regression/convex_rotated_rect.json`
  - `poc/nfp_regression/convex_hexagon.json`
  - `poc/nfp_regression/convex_skinny.json`
  - `poc/nfp_regression/convex_collinear_edge.json`
  - `poc/nfp_regression/convex_triangle.json`
- **Codex artefaktok:**
  - `codex/codex_checklist/nesting_engine/nfp_fixture_expansion.md`
  - `codex/reports/nesting_engine/nfp_fixture_expansion.md`

### 3.2 Miért változtak?

- A unit tesztnevek és ellenőrzések DoD-követelmény szerint pontosításra kerültek (hibakezelés, collinear merge, determinizmus, ismert téglalap-eset).
- Az új fixture-ek érdemi geometriai lefedettséget adnak (rotated, hexagon, skinny, collinear, triangle).
- Az integrációs teszt most explicit védi a fixture input minőséget (`convex + CCW`), így hibás fixture hamarabb jelez.

## 4) Verifikáció

### 4.1 Kötelező parancs

- `./scripts/verify.sh --report codex/reports/nesting_engine/nfp_fixture_expansion.md` -> lásd AUTO_VERIFY blokk.

### 4.2 Opcionális, task-specifikus parancsok

- `cargo test --manifest-path rust/nesting_engine/Cargo.toml --lib` -> PASS.
- `cargo test --manifest-path rust/nesting_engine/Cargo.toml --test nfp_regression` -> PASS.

### 4.3 Ha valami kimaradt

- Nincs kimaradt kötelező ellenőrzés.

## 5) DoD -> Evidence Matrix

| DoD pont | Státusz | Bizonyíték | Magyarázat | Kapcsolódó teszt/ellenőrzés |
|---|---|---|---|---|
| `convex.rs` `#[cfg(test)]` blokk >=5 unit teszttel | PASS | `rust/nesting_engine/src/nfp/convex.rs` (`tests` modul) | A modul 5 darab, név szerint elvárt white-box tesztet tartalmaz. | `cargo test --manifest-path rust/nesting_engine/Cargo.toml --lib` |
| `test_not_convex_returns_err` PASS | PASS | `rust/nesting_engine/src/nfp/convex.rs::test_not_convex_returns_err` | L-alak inputra `Err(NfpError::NotConvex)` assert. | `cargo test --manifest-path rust/nesting_engine/Cargo.toml --lib` |
| `test_empty_polygon_returns_err` PASS | PASS | `rust/nesting_engine/src/nfp/convex.rs::test_empty_polygon_returns_err` | `<3` csúcsú polygonra `Err(NfpError::EmptyPolygon)` assert. | `cargo test --manifest-path rust/nesting_engine/Cargo.toml --lib` |
| `test_collinear_merge_no_extra_vertices` PASS | PASS | `rust/nesting_engine/src/nfp/convex.rs::test_collinear_merge_no_extra_vertices` | Azonos 100x50 téglalapok esetén 4 csúcsú NFP és konkrét kontúr ellenőrzése. | `cargo test --manifest-path rust/nesting_engine/Cargo.toml --lib` |
| `test_determinism` PASS | PASS | `rust/nesting_engine/src/nfp/convex.rs::test_determinism` | Kétszeri futás kanonizált ringje azonos. | `cargo test --manifest-path rust/nesting_engine/Cargo.toml --lib` |
| `test_rect_rect_known_nfp` PASS | PASS | `rust/nesting_engine/src/nfp/convex.rs::test_rect_rect_known_nfp` | Ismert 100x50 vs 60x30 elvárt NFP kontúr ellenőrizve. | `cargo test --manifest-path rust/nesting_engine/Cargo.toml --lib` |
| 5 új fixture JSON létezik | PASS | `poc/nfp_regression/convex_rotated_rect.json`, `convex_hexagon.json`, `convex_skinny.json`, `convex_collinear_edge.json`, `convex_triangle.json` | A fixture könyvtár 2-ről 7 darabra bővült. | `cargo test --manifest-path rust/nesting_engine/Cargo.toml --test nfp_regression` |
| Minden fixture input `is_convex` + `is_ccw` | PASS | `rust/nesting_engine/tests/nfp_regression.rs` (`fixture_library_passes`, `edge_merge_equals_hull_on_all_fixtures`) | Mindkét teszt loop elején explicit invariant assert fut A és B polygonra. | `cargo test --manifest-path rust/nesting_engine/Cargo.toml --test nfp_regression` |
| Minden új fixture `expected_nfp` hull-lal számolt + kézzel ellenőrzött | PASS | Új fixture JSON-ok `expected_nfp` mezői + `edge_merge_equals_hull_on_all_fixtures` | A várható kontúrok hull szerinti értékkel lettek felvéve, majd kézi sanity ellenőrzéssel validálva. | `cargo test --manifest-path rust/nesting_engine/Cargo.toml --test nfp_regression` |
| `fixture_library_passes` PASS (7 fixture) | PASS | `rust/nesting_engine/tests/nfp_regression.rs::fixture_library_passes` | A teszt már legalább 7 fixture-t vár és mindet validálja. | `cargo test --manifest-path rust/nesting_engine/Cargo.toml --test nfp_regression` |
| `edge_merge_equals_hull_on_all_fixtures` PASS (7 fixture) | PASS | `rust/nesting_engine/tests/nfp_regression.rs::edge_merge_equals_hull_on_all_fixtures` | Minden fixture-n kanonizált edge-merge == hull egyezés PASS. | `cargo test --manifest-path rust/nesting_engine/Cargo.toml --test nfp_regression` |
| `cargo test` (lib + integration) PASS | PASS | Parancskimenet (helyi futás) | Mind a lib, mind az `nfp_regression` tesztkészlet zöld. | `cargo test --manifest-path rust/nesting_engine/Cargo.toml --lib`; `cargo test --manifest-path rust/nesting_engine/Cargo.toml --test nfp_regression` |
| Kötelező repo gate wrapperrel futtatva | PASS | AUTO_VERIFY blokk | A `verify.sh` futtatása megtörtént, a report automatikus blokkja PASS eredményt tartalmaz. | `./scripts/verify.sh --report codex/reports/nesting_engine/nfp_fixture_expansion.md` |

## 6) Fixture részletek

- `convex_rotated_rect.json`: `expected_vertex_count=8`, kézzel ellenőrizve: igen.
- `convex_hexagon.json`: `expected_vertex_count=8`, kézzel ellenőrizve: igen.
- `convex_skinny.json`: `expected_vertex_count=4`, kézzel ellenőrizve: igen.
- `convex_collinear_edge.json`: `expected_vertex_count=4`, kézzel ellenőrizve: igen.
- `convex_triangle.json`: `expected_vertex_count=6`, kézzel ellenőrizve: igen.

## 8) Advisory notes

- A `cargo test --test nfp_regression` futásnál a bináris célból származó `dead_code` warningok jelen vannak, de a teszteredményt nem befolyásolják.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-02-24T19:25:40+01:00 → 2026-02-24T19:28:52+01:00 (192s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/nesting_engine/nfp_fixture_expansion.verify.log`
- git: `main@588fefb`
- módosított fájlok (git status): 16

**git diff --stat**

```text
 canvases/nesting_engine/nfp_computation_convex.md  |  91 +++++------
 .../nfp_convex_edge_merge_fastpath.md              |  52 ++++---
 .../nesting_engine/nfp_computation_convex.md       |  98 ++++++------
 rust/nesting_engine/src/nfp/convex.rs              | 168 ++++++++-------------
 rust/nesting_engine/tests/nfp_regression.rs        |  32 +++-
 5 files changed, 204 insertions(+), 237 deletions(-)
```

**git status --porcelain (preview)**

```text
 M canvases/nesting_engine/nfp_computation_convex.md
 M canvases/nesting_engine/nfp_convex_edge_merge_fastpath.md
 M codex/reports/nesting_engine/nfp_computation_convex.md
 M rust/nesting_engine/src/nfp/convex.rs
 M rust/nesting_engine/tests/nfp_regression.rs
?? canvases/nesting_engine/nfp_fixture_expansion.md
?? codex/codex_checklist/nesting_engine/nfp_fixture_expansion.md
?? codex/goals/canvases/nesting_engine/fill_canvas_nfp_fixture_expansion.yaml
?? codex/prompts/nesting_engine/nfp_fixture_expansion/
?? codex/reports/nesting_engine/nfp_fixture_expansion.md
?? codex/reports/nesting_engine/nfp_fixture_expansion.verify.log
?? poc/nfp_regression/convex_collinear_edge.json
?? poc/nfp_regression/convex_hexagon.json
?? poc/nfp_regression/convex_rotated_rect.json
?? poc/nfp_regression/convex_skinny.json
?? poc/nfp_regression/convex_triangle.json
```

<!-- AUTO_VERIFY_END -->
