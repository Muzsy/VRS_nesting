# Codex Report — nfp_concave_orbit_no_silent_fallback

**Status:** PASS_WITH_NOTES

---

## 1) Meta

- **Task slug:** `nfp_concave_orbit_no_silent_fallback`
- **Kapcsolódó canvas:** `canvases/nesting_engine/nfp_concave_orbit_no_silent_fallback.md`
- **Kapcsolódó goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_nfp_concave_orbit_no_silent_fallback.yaml`
- **Futás dátuma:** 2026-02-25
- **Branch / commit:** `main` / `8cc067c` (uncommitted changes)
- **Fókusz terület:** Geometry

## 2) Scope

### 2.1 Cél

1. Megszüntetni a silent fallbacket exact no-fallback módban (nincs `Ok(stable_seed)`).
2. Explicit orbit outcome és failure reason bevezetése telemetriával.
3. Prefer-exact regresszió explicit proof policyra átállítása (`ExactClosed` vagy `expect_exact_error`).
4. Három prefer-exact fixture explicit mezőkkel történő rögzítése.

### 2.2 Nem-cél (explicit)

1. Stable baseline algoritmus módosítása.
2. Orbit next-event geometriájának minőségi tuningja.
3. f64 PIP visszahozása vagy `rust/vrs_solver/**` módosítása.
4. Wrapper script módosítás.

## 3) Változások összefoglalója

### 3.1 Érintett fájlok

- `canvases/nesting_engine/nfp_concave_orbit_no_silent_fallback.md`
- `rust/nesting_engine/src/nfp/mod.rs`
- `rust/nesting_engine/src/nfp/concave.rs`
- `rust/nesting_engine/tests/nfp_regression.rs`
- `poc/nfp_regression/concave_touching_group.json`
- `poc/nfp_regression/concave_hole_pocket.json`
- `poc/nfp_regression/concave_interlock_c.json`
- `codex/codex_checklist/nesting_engine/nfp_concave_orbit_no_silent_fallback.md`
- `codex/reports/nesting_engine/nfp_concave_orbit_no_silent_fallback.md`

### 3.2 Miért változtak?

- Az `ExactOrbit` ágban a dead-end/loop/max_steps most explicit outcome-on keresztül megy, no-fallback módban hiba, fallback módban jelölt stable fallback.
- Az NfpError bővítés explicit orbit failure okokat ad (`OrbitDeadEnd`, `OrbitMaxStepsReached`, `OrbitNotClosed`).
- A regressziós teszt prefer-exact fixture-eken bizonyítja: vagy `ExactClosed` és `exact != stable`, vagy explicit elvárt orbit hiba.

## 4) Verifikáció

### 4.1 Kötelező parancs

- `./scripts/verify.sh --report codex/reports/nesting_engine/nfp_concave_orbit_no_silent_fallback.md` -> PASS (AUTO_VERIFY blokk).

### 4.2 Opcionális, task-specifikus parancsok

- `cargo test --manifest-path rust/nesting_engine/Cargo.toml concave::tests::` -> PASS.
- `cargo test --manifest-path rust/nesting_engine/Cargo.toml --test nfp_regression` -> PASS.

### 4.3 Ha valami kimaradt

- Nincs kimaradt kötelező ellenőrzés.

## 5) DoD -> Evidence Matrix

| DoD pont | Státusz | Bizonyíték (path + line) | Magyarázat | Kapcsolódó teszt/ellenőrzés |
|---|---|---|---|---|
| no-fallback módban dead-end/loop/max_steps nem adhat stable-t | PASS | `rust/nesting_engine/src/nfp/concave.rs:196`, `rust/nesting_engine/src/nfp/concave.rs:302` | `FailedNoFallback` outcome explicit `Err(reason.as_error())`-ra fordul, nincs `Ok(stable_seed)` ág. | `cargo test --manifest-path rust/nesting_engine/Cargo.toml concave::tests::` |
| explicit orbit failure típusok az error rétegben | PASS | `rust/nesting_engine/src/nfp/mod.rs:16`, `rust/nesting_engine/src/nfp/mod.rs:34` | Az `NfpError` bővült explicit orbit hibákkal (dead-end, max-steps, not-closed). | `cargo test --manifest-path rust/nesting_engine/Cargo.toml --test nfp_regression` |
| belső outcome telemetriával (`steps_count`, `events_count`) | PASS | `rust/nesting_engine/src/nfp/concave.rs:111`, `rust/nesting_engine/src/nfp/concave.rs:134`, `rust/nesting_engine/src/nfp/concave.rs:233` | `OrbitOutcome` + `OrbitTelemetry` külön jelöli az `ExactClosed`/`FallbackStable`/`FailedNoFallback` állapotokat. | `cargo test --manifest-path rust/nesting_engine/Cargo.toml concave::tests::` |
| prefer_exact proof policy (`ExactClosed + exact!=stable` vagy `expect_exact_error`) | PASS | `rust/nesting_engine/tests/nfp_regression.rs:98`, `rust/nesting_engine/tests/nfp_regression.rs:192`, `rust/nesting_engine/tests/nfp_regression.rs:248` | A regresszió explicit outcome policyt kényszerít: no-fallback exact success esetén ring-diff, vagy explicit elvárt orbit hiba. | `cargo test --manifest-path rust/nesting_engine/Cargo.toml --test nfp_regression` |
| 3 prefer_exact fixture explicit mezőkkel frissítve | PASS | `poc/nfp_regression/concave_touching_group.json:9`, `poc/nfp_regression/concave_hole_pocket.json:21`, `poc/nfp_regression/concave_interlock_c.json:33` | Mindhárom fixture explicit `allow_exact_equals_stable` + `expect_exact_error` mezőt kapott. | `cargo test --manifest-path rust/nesting_engine/Cargo.toml --test nfp_regression` |
| kötelező verify wrapper futtatása | PASS | `codex/reports/nesting_engine/nfp_concave_orbit_no_silent_fallback.md` | A verify wrapper futás és log az AUTO_VERIFY blokkban. | `./scripts/verify.sh --report codex/reports/nesting_engine/nfp_concave_orbit_no_silent_fallback.md` |

## 6) Fixture outcome evidence (prefer_exact)

| Fixture | prefer_exact | expect_exact_error | Outcome | Megjegyzés |
|---|---:|---:|---|---|
| `concave_touching_group.json` | true | true | ExpectedExactError | no-fallback exact explicit orbit hibával áll meg (a teszt ezt várja) |
| `concave_hole_pocket.json` | true | true | ExpectedExactError | no-fallback exact explicit orbit hibával áll meg (a teszt ezt várja) |
| `concave_interlock_c.json` | true | false | ExactClosed | no-fallback exact lezár és canonical ring különbözik a stable ringtől |

## 8) Advisory notes

- A no-silent-fallback policy most explicit és tesztelt; ugyanakkor 2 prefer-exact fixture jelenleg elvárt hibás (`expect_exact_error=true`), ami további orbit heurisztika finomhangolási backlogot jelez.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-02-25T19:51:16+01:00 → 2026-02-25T19:54:25+01:00 (189s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/nesting_engine/nfp_concave_orbit_no_silent_fallback.verify.log`
- git: `main@8cc067c`
- módosított fájlok (git status): 12

**git diff --stat**

```text
 poc/nfp_regression/concave_hole_pocket.json    |   4 +-
 poc/nfp_regression/concave_interlock_c.json    |   4 +-
 poc/nfp_regression/concave_touching_group.json |   4 +-
 rust/nesting_engine/src/nfp/concave.rs         | 225 ++++++++++++++++++++-----
 rust/nesting_engine/src/nfp/mod.rs             |   6 +
 rust/nesting_engine/tests/nfp_regression.rs    | 128 +++++++++-----
 6 files changed, 288 insertions(+), 83 deletions(-)
```

**git status --porcelain (preview)**

```text
 M poc/nfp_regression/concave_hole_pocket.json
 M poc/nfp_regression/concave_interlock_c.json
 M poc/nfp_regression/concave_touching_group.json
 M rust/nesting_engine/src/nfp/concave.rs
 M rust/nesting_engine/src/nfp/mod.rs
 M rust/nesting_engine/tests/nfp_regression.rs
?? canvases/nesting_engine/nfp_concave_orbit_no_silent_fallback.md
?? codex/codex_checklist/nesting_engine/nfp_concave_orbit_no_silent_fallback.md
?? codex/goals/canvases/nesting_engine/fill_canvas_nfp_concave_orbit_no_silent_fallback.yaml
?? codex/prompts/nesting_engine/nfp_concave_orbit_no_silent_fallback/
?? codex/reports/nesting_engine/nfp_concave_orbit_no_silent_fallback.md
?? codex/reports/nesting_engine/nfp_concave_orbit_no_silent_fallback.verify.log
```

<!-- AUTO_VERIFY_END -->
