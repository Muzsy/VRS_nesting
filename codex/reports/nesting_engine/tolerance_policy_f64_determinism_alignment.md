# Codex Report — tolerance_policy_f64_determinism_alignment

**Status:** PASS_WITH_NOTES

---

## 1) Meta

- **Task slug:** `tolerance_policy_f64_determinism_alignment`
- **Kapcsolódó canvas:** `canvases/nesting_engine/tolerance_policy_f64_determinism_alignment.md`
- **Kapcsolódó goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_tolerance_policy_f64_determinism_alignment.yaml`
- **Futás dátuma:** 2026-03-08
- **Branch / commit:** `main` / `5db951f` (uncommitted changes)
- **Fókusz terület:** Mixed

## 2) Scope

### 2.1 Cél

1. A/B/C determinism boundary modell bevezetése doksi-kód szinten.
2. Központosított float-policy helper bevezetése (`cmp_eps`, `eq_eps`, `is_near_zero`).
3. `offset.rs` és `pipeline.rs` float-érintett döntési pontjainak policy-alapú hardeningje.
4. `narrow.rs` célzott float-boundary evidence tesztek hozzáadása.
5. Dedicált float-boundary determinism smoke bekötése a repo gate-be.
6. KI-007 gyűjtő issue lezárása a ténylegesen implementált scope alapján.

### 2.2 Nem-cél (explicit)

1. Teljes geometriai integer-only átírás.
2. Új placer/search feature bevezetése.
3. Performance-optimalizációs kör.
4. Determinism hash contract módosítása.

## 3) Változások összefoglalója

### 3.1 Érintett fájlok

- **Task artifacts:**
  - `canvases/nesting_engine/tolerance_policy_f64_determinism_alignment.md`
  - `codex/goals/canvases/nesting_engine/fill_canvas_tolerance_policy_f64_determinism_alignment.yaml`
  - `codex/prompts/nesting_engine/tolerance_policy_f64_determinism_alignment/run.md`
  - `codex/codex_checklist/nesting_engine/tolerance_policy_f64_determinism_alignment.md`
  - `codex/reports/nesting_engine/tolerance_policy_f64_determinism_alignment.md`
- **Rust:**
  - `rust/nesting_engine/src/geometry/float_policy.rs`
  - `rust/nesting_engine/src/geometry/mod.rs`
  - `rust/nesting_engine/src/geometry/offset.rs`
  - `rust/nesting_engine/src/geometry/pipeline.rs`
  - `rust/nesting_engine/src/feasibility/narrow.rs`
- **Gate / smoke / fixture:**
  - `scripts/check.sh`
  - `scripts/smoke_nesting_engine_float_policy_determinism.sh`
  - `poc/nesting_engine/float_policy_near_touching_fixture_v2.json`
- **Docs:**
  - `docs/nesting_engine/tolerance_policy.md`
  - `docs/nesting_engine/architecture.md`
  - `docs/known_issues/nesting_engine_known_issues.md`

### 3.2 Miért változtak?

- A float-érintett geometriai útvonalak policy-határai explicit dokumentációt és közös helper API-t kaptak.
- Az `offset`/`pipeline` modulban az epsilon összehasonlítások és canonicalization viselkedés központosított lett.
- Új, prefixelt evidence tesztek készültek a három érintett területre.
- A float-boundary smoke fix fixture-rel bekerült a `check.sh` gate útvonalba.
- KI-007 lezárásra került, mert a driftet okozó fő doc-code eltérés rendezve lett.

## 4) Verifikáció

### 4.1 Kötelező parancs

- `./scripts/verify.sh --report codex/reports/nesting_engine/tolerance_policy_f64_determinism_alignment.md` -> PASS (AUTO_VERIFY blokk).

### 4.2 Opcionális, task-specifikus parancsok

- `cargo test --manifest-path rust/nesting_engine/Cargo.toml offset_determinism_` -> PASS.
- `cargo test --manifest-path rust/nesting_engine/Cargo.toml pipeline_float_policy_` -> PASS.
- `cargo test --manifest-path rust/nesting_engine/Cargo.toml narrow_float_policy_` -> PASS.
- `RUNS=10 ./scripts/smoke_nesting_engine_float_policy_determinism.sh` -> PASS.

### 4.3 Ha valami kimaradt

- Nem maradt ki kötelező ellenőrzés.

## 5) DoD -> Evidence Matrix

| DoD pont | Státusz | Bizonyíték (path + line) | Magyarázat | Kapcsolódó teszt/ellenőrzés |
|---|---|---|---|---|
| A/B/C determinism boundary modell dokumentálva van, doc-code drift nélkül. | PASS | `docs/nesting_engine/tolerance_policy.md:55`, `docs/nesting_engine/architecture.md:21` | A tolerance policy és az architecture is explicit zónamodellt ír le. | Doksi review |
| Van központosított float-policy helper, és az érintett geometry modulok ezt használják. | PASS | `rust/nesting_engine/src/geometry/float_policy.rs:1`, `rust/nesting_engine/src/geometry/offset.rs:12`, `rust/nesting_engine/src/geometry/pipeline.rs:7` | A közös helper bevezetve és bekötve mindkét érintett geometry modulban. | `cargo test ... offset_determinism_`, `cargo test ... pipeline_float_policy_` |
| Nincs ad hoc epsilon szétszórva az érintett döntési pontokon. | PASS | `rust/nesting_engine/src/geometry/offset.rs:55`, `rust/nesting_engine/src/geometry/pipeline.rs:441` | A döntési összehasonlítások `cmp_eps/eq_eps/is_near_zero` helperen futnak. | `cargo test ... offset_determinism_`, `cargo test ... pipeline_float_policy_` |
| Van dedikált `offset_determinism_` regressziós evidence. | PASS | `rust/nesting_engine/src/geometry/offset.rs:331` | Két explicit prefixelt teszt védi a canonical hole-order és near-zero winding stabilitást. | `cargo test ... offset_determinism_` |
| Van dedikált `pipeline_float_policy_` regressziós evidence. | PASS | `rust/nesting_engine/src/geometry/pipeline.rs:761` | Prefixelt pipeline tesztek vannak bbox stability, canonical ring start és repeated-run byte identity esetekre. | `cargo test ... pipeline_float_policy_` |
| Van dedikált `narrow_float_policy_` regressziós evidence. | PASS | `rust/nesting_engine/src/feasibility/narrow.rs:443` | Prefixelt narrow tesztek coverelik a near-touching rounding boundary és determinisztikus ismétlés esetet. | `cargo test ... narrow_float_policy_` |
| Van célzott float-boundary repeated-run determinism smoke. | PASS | `scripts/smoke_nesting_engine_float_policy_determinism.sh:1`, `poc/nesting_engine/float_policy_near_touching_fixture_v2.json:1` | Új smoke wrapper + dedikált near-boundary fixture készült. | `RUNS=10 ./scripts/smoke_nesting_engine_float_policy_determinism.sh` |
| A smoke a `scripts/check.sh` része (PR gate útvonalon fut). | PASS | `scripts/check.sh:98`, `scripts/check.sh:619` | A script executable listában és kötelező smoke futásban is szerepel. | `./scripts/verify.sh --report ...` |
| `./scripts/verify.sh --report ...` PASS. | PASS | `codex/reports/nesting_engine/tolerance_policy_f64_determinism_alignment.md` | AUTO_VERIFY blokk rögzíti a sikeres futást. | `./scripts/verify.sh --report ...` |
| KI-007 lezárása/leszűkítése explicit és követhető. | PASS | `docs/known_issues/nesting_engine_known_issues.md:103` | KI-007 `RESOLVED` státuszba került e task sluggal és dátummal. | Doksi review |

## 7) Doksi szinkron

- `tolerance_policy.md`: A/B/C boundary modell + float-policy helper hivatkozás.
- `architecture.md`: determinism boundary modell külön szakaszban.
- `known_issues`: KI-007 lezárva erre a taskra.

## 8) Advisory notes

- Ez a kör kifejezetten **stabilizációs / policy-alignment task**, nem teljes integer-only rewrite.
- KI-008 (architecture modul-map "planned" státusz) ettől még külön, nem-blokkoló dokumentációs debt maradt.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-03-08T20:27:59+01:00 → 2026-03-08T20:31:28+01:00 (209s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/nesting_engine/tolerance_policy_f64_determinism_alignment.verify.log`
- git: `main@5db951f`
- módosított fájlok (git status): 17

**git diff --stat**

```text
 docs/known_issues/nesting_engine_known_issues.md |  38 ++-----
 docs/nesting_engine/architecture.md              |  42 ++++++--
 docs/nesting_engine/tolerance_policy.md          |  61 ++++++++---
 rust/nesting_engine/src/feasibility/narrow.rs    |  47 +++++++++
 rust/nesting_engine/src/geometry/mod.rs          |   1 +
 rust/nesting_engine/src/geometry/offset.rs       |  91 ++++++++++++++++-
 rust/nesting_engine/src/geometry/pipeline.rs     | 125 +++++++++++++++++++++--
 scripts/check.sh                                 |  13 +++
 8 files changed, 356 insertions(+), 62 deletions(-)
```

**git status --porcelain (preview)**

```text
 M docs/known_issues/nesting_engine_known_issues.md
 M docs/nesting_engine/architecture.md
 M docs/nesting_engine/tolerance_policy.md
 M rust/nesting_engine/src/feasibility/narrow.rs
 M rust/nesting_engine/src/geometry/mod.rs
 M rust/nesting_engine/src/geometry/offset.rs
 M rust/nesting_engine/src/geometry/pipeline.rs
 M scripts/check.sh
?? canvases/nesting_engine/tolerance_policy_f64_determinism_alignment.md
?? codex/codex_checklist/nesting_engine/tolerance_policy_f64_determinism_alignment.md
?? codex/goals/canvases/nesting_engine/fill_canvas_tolerance_policy_f64_determinism_alignment.yaml
?? codex/prompts/nesting_engine/tolerance_policy_f64_determinism_alignment/
?? codex/reports/nesting_engine/tolerance_policy_f64_determinism_alignment.md
?? codex/reports/nesting_engine/tolerance_policy_f64_determinism_alignment.verify.log
?? poc/nesting_engine/float_policy_near_touching_fixture_v2.json
?? rust/nesting_engine/src/geometry/float_policy.rs
?? scripts/smoke_nesting_engine_float_policy_determinism.sh
```

<!-- AUTO_VERIFY_END -->
