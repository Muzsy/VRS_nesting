# Codex Report — nfp_concave_orbit_next_event

**Status:** PASS_WITH_NOTES

---

## 1) Meta

- **Task slug:** `nfp_concave_orbit_next_event`
- **Kapcsolódó canvas:** `canvases/nesting_engine/nfp_concave_orbit_next_event.md`
- **Kapcsolódó goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_nfp_concave_orbit_next_event.yaml`
- **Futás dátuma:** 2026-02-25
- **Branch / commit:** `main` / `978f16f` (uncommitted changes)
- **Fókusz terület:** Geometry

## 2) Scope

### 2.1 Cél

1. ExactOrbit ágon next-event alapú, racionális `t` léptetés bevezetése (`p += v * t`).
2. Touching group multi-contact komponens kezelés + determinisztikus candidate irány rendezés.
3. Determinisztikus eseményválasztás (fraction compare + event-kind/lex tie-break) és integer-only predikátumok.
4. Regressziós tesztek bővítése `prefer_exact`/`expect_exact_fallback` fixture policyval.
5. Legalább 3 concave fixture exact no-fallback futás bizonyítása.

### 2.2 Nem-cél (explicit)

1. Stable baseline (decomposition+convex+union) algoritmus cseréje.
2. Holes teljes körű támogatás bevezetése.
3. Wrapper scriptek (`scripts/check.sh`, `scripts/verify.sh`) módosítása.
4. `rust/vrs_solver/**` módosítása.

## 3) Változások összefoglalója

### 3.1 Érintett fájlok

- `canvases/nesting_engine/nfp_concave_orbit_next_event.md`
- `rust/nesting_engine/src/nfp/concave.rs`
- `rust/nesting_engine/tests/nfp_regression.rs`
- `poc/nfp_regression/concave_touching_group.json`
- `poc/nfp_regression/concave_slit.json`
- `poc/nfp_regression/concave_hole_pocket.json`
- `poc/nfp_regression/concave_interlock_c.json`
- `poc/nfp_regression/concave_multi_contact.json`
- `codex/codex_checklist/nesting_engine/nfp_concave_orbit_next_event.md`
- `codex/reports/nesting_engine/nfp_concave_orbit_next_event.md`

### 3.2 Miért változtak?

- A `concave.rs` ExactOrbit ágában az egységlépés next-event léptetésre lett cserélve racionális idővel és determinisztikus eseményválasztással.
- A touching group és candidate iránylogika többkontaktos komponensre és stabil tie-breakre lett átírva.
- A regressziós teszt explicit exact-no-fallback coverage-et mér legalább 3 concave fixture-en.
- A fixture meta (`prefer_exact`, `expect_exact_fallback`) az új exact/fallback elvárásokat deklarálja.

## 4) Verifikáció

### 4.1 Kötelező parancs

- `./scripts/verify.sh --report codex/reports/nesting_engine/nfp_concave_orbit_next_event.md` -> PASS (lásd AUTO_VERIFY blokk).

### 4.2 Opcionális, task-specifikus parancsok

- `cargo test --manifest-path rust/nesting_engine/Cargo.toml --test nfp_regression` -> PASS.
- `cargo test --manifest-path rust/nesting_engine/Cargo.toml concave::tests::` -> PASS.

### 4.3 Ha valami kimaradt

- Nincs kimaradt kötelező ellenőrzés.

## 5) DoD -> Evidence Matrix

| DoD pont | Státusz | Bizonyíték (path + line) | Magyarázat | Kapcsolódó teszt/ellenőrzés |
|---|---|---|---|---|
| Next-event léptetés racionális `t`-vel | PASS | `rust/nesting_engine/src/nfp/concave.rs:60`, `rust/nesting_engine/src/nfp/concave.rs:288`, `rust/nesting_engine/src/nfp/concave.rs:432` | `Fraction` reprezentáció, eseményjelölt számítás és `apply_translation_fraction` biztosítja a determinisztikus `p += v*t` lépést. | `cargo test --manifest-path rust/nesting_engine/Cargo.toml --test nfp_regression` |
| Touching group multi-contact + determinisztikus irányválasztás | PASS | `rust/nesting_engine/src/nfp/concave.rs:1031`, `rust/nesting_engine/src/nfp/concave.rs:1067`, `rust/nesting_engine/src/nfp/concave.rs:1129`, `rust/nesting_engine/src/nfp/concave.rs:1237` | A kontaktok komponensekre bontása és a candidate irányok kvadráns/cross/lex alapú rendezése stabil döntési sorrendet ad. | `cargo test --manifest-path rust/nesting_engine/Cargo.toml --test nfp_regression` |
| Loop/dead-end guard + boundary clean | PASS | `rust/nesting_engine/src/nfp/concave.rs:182`, `rust/nesting_engine/src/nfp/concave.rs:237`, `rust/nesting_engine/src/nfp/concave.rs:208` | Visited signature, max_steps guard és `clean_polygon_boundary()` a visszaadott pályán garantálja a kontrollált lezárást. | `cargo test --manifest-path rust/nesting_engine/Cargo.toml concave::tests::` |
| Legalább 3 concave fixture exact no-fallback módban lefut | PASS | `poc/nfp_regression/concave_touching_group.json:9`, `poc/nfp_regression/concave_hole_pocket.json:9`, `poc/nfp_regression/concave_interlock_c.json:9`, `rust/nesting_engine/tests/nfp_regression.rs:163`, `rust/nesting_engine/tests/nfp_regression.rs:238` | Három fixture `prefer_exact: true`; a teszt `enable_fallback: false` módban kétszer futtatja őket és minimum 3 sikeres no-fallback futást elvár. | `cargo test --manifest-path rust/nesting_engine/Cargo.toml --test nfp_regression` |
| Determinisztika exact módban | PASS | `rust/nesting_engine/tests/nfp_regression.rs:181`, `rust/nesting_engine/tests/nfp_regression.rs:198`, `rust/nesting_engine/src/nfp/concave.rs:1480` | Exact no-fallback fixture-eken kétszeri futás canonical ring egyezést ellenőriz; a modul-szintű concave teszt is védi a loop-guard melletti determinizmust. | `cargo test --manifest-path rust/nesting_engine/Cargo.toml --test nfp_regression`; `cargo test --manifest-path rust/nesting_engine/Cargo.toml concave::tests::` |
| Kötelező repo gate wrapperrel | PASS | `codex/reports/nesting_engine/nfp_concave_orbit_next_event.md` | A `verify.sh` futás eredménye az AUTO_VERIFY blokkban kerül rögzítésre. | `./scripts/verify.sh --report codex/reports/nesting_engine/nfp_concave_orbit_next_event.md` |

## 8) Advisory notes

- Az exact ág loop/dead-end esetben kontrollált orbit-zárást végez, és ha ez nem ad tiszta pályát, stabil seed boundary-t ad vissza az exact útvonalon belül; ez determinisztikus, de további geometriai minőségmérés ajánlott.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-02-25T19:19:42+01:00 → 2026-02-25T19:22:50+01:00 (188s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/nesting_engine/nfp_concave_orbit_next_event.verify.log`
- git: `main@978f16f`
- módosított fájlok (git status): 11

**git diff --stat**

```text
 poc/nfp_regression/concave_hole_pocket.json    |   2 +-
 poc/nfp_regression/concave_interlock_c.json    |   2 +-
 poc/nfp_regression/concave_touching_group.json |   2 +-
 rust/nesting_engine/src/nfp/concave.rs         | 846 ++++++++++++++++++++++---
 rust/nesting_engine/tests/nfp_regression.rs    |  77 ++-
 5 files changed, 820 insertions(+), 109 deletions(-)
```

**git status --porcelain (preview)**

```text
 M poc/nfp_regression/concave_hole_pocket.json
 M poc/nfp_regression/concave_interlock_c.json
 M poc/nfp_regression/concave_touching_group.json
 M rust/nesting_engine/src/nfp/concave.rs
 M rust/nesting_engine/tests/nfp_regression.rs
?? canvases/nesting_engine/nfp_concave_orbit_next_event.md
?? codex/codex_checklist/nesting_engine/nfp_concave_orbit_next_event.md
?? codex/goals/canvases/nesting_engine/fill_canvas_nfp_concave_orbit_next_event.yaml
?? codex/prompts/nesting_engine/nfp_concave_orbit_next_event/
?? codex/reports/nesting_engine/nfp_concave_orbit_next_event.md
?? codex/reports/nesting_engine/nfp_concave_orbit_next_event.verify.log
```

<!-- AUTO_VERIFY_END -->
