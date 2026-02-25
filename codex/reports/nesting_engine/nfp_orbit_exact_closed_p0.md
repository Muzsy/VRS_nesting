# Codex Report — nfp_orbit_exact_closed_p0

**Status:** PASS_WITH_NOTES

---

## 1) Meta

- **Task slug:** `nfp_orbit_exact_closed_p0`
- **Kapcsolódó canvas:** `canvases/nesting_engine/nfp_orbit_exact_closed_p0.md`
- **Kapcsolódó goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_nfp_orbit_exact_closed_p0.yaml`
- **Futás dátuma:** 2026-02-25
- **Branch / commit:** `main` / `fb83cb4` (uncommitted changes)
- **Fókusz terület:** Geometry

## 2) Scope

### 2.1 Cél

1. ExactOrbit no-fallback minőségi rés zárása: legalább 3 `prefer_exact` concave fixture legyen tényleges `ExactClosed`.
2. Determinisztikus dead-end kezelés: ne azonnali fail legyen, hanem determinisztikus alternatív iránypróba.
3. Next-event jelöltek bővítése minimális szükséges eseménnyel (`vertex_to_vertex`), i128 predikátumokkal.
4. Regressziós proof szigorítása: `prefer_exact` esetén zárás + canonical különbség bizonyítása stable baseline-hoz képest.

### 2.2 Nem-cél (explicit)

1. Stable baseline (decomposition + convex + union) átírása.
2. Holes támogatás bevezetése.
3. Új dependency hozzáadása.
4. `scripts/verify.sh` módosítása.

## 3) Változások összefoglalója

### 3.1 Érintett fájlok

- `canvases/nesting_engine/nfp_orbit_exact_closed_p0.md`
- `rust/nesting_engine/src/nfp/concave.rs`
- `rust/nesting_engine/tests/nfp_regression.rs`
- `poc/nfp_regression/concave_touching_group.json`
- `poc/nfp_regression/concave_interlock_c.json`
- `poc/nfp_regression/concave_multi_contact.json`
- `codex/codex_checklist/nesting_engine/nfp_orbit_exact_closed_p0.md`
- `codex/reports/nesting_engine/nfp_orbit_exact_closed_p0.md`

### 3.2 Miért változtak?

- Az orbit ciklusban backtrackinges alternatív iránypróba került be: dead-end/revisit jelöltnél tiltott transitionnel új jelölt választódik.
- A next-event generátor `vertex_to_vertex` eseményt is figyelembe vesz, ami korábban elvesző kontakt-eseteket lefed.
- A regressziós teszt explicit `>=3 ExactClosed` követelményt enforce-ol, és fixture listát is gyűjt.
- A 3 cél fixture `prefer_exact: true` + `expect_exact_error: false` policy-ra lett állítva.

## 4) Verifikáció

### 4.1 Kötelező parancs

- `./scripts/verify.sh --report codex/reports/nesting_engine/nfp_orbit_exact_closed_p0.md` -> PASS (lásd AUTO_VERIFY blokk).

### 4.2 Opcionális, task-specifikus parancsok

- `cargo test --manifest-path rust/nesting_engine/Cargo.toml --test nfp_regression` -> PASS.
- `cargo test --manifest-path rust/nesting_engine/Cargo.toml --test orbit_next_event_trace_smoke` -> PASS.
- `cd rust/nesting_engine && cargo test -q nfp_regression` -> PASS.

### 4.3 Ha valami kimaradt

- Nincs kimaradt kötelező ellenőrzés.

## 5) DoD -> Evidence Matrix

| DoD pont | Státusz | Bizonyíték (path + line) | Magyarázat | Kapcsolódó teszt/ellenőrzés |
|---|---|---|---|---|
| `cargo test -q nfp_regression` PASS | PASS | `codex/reports/nesting_engine/nfp_orbit_exact_closed_p0.md` (Verifikáció szekció) | A DoD-ban kért parancs lefutott zölden. | `cd rust/nesting_engine && cargo test -q nfp_regression` |
| Dead-end esetben determinisztikus alternatív iránykezelés | PASS | `rust/nesting_engine/src/nfp/concave.rs:330`, `rust/nesting_engine/src/nfp/concave.rs:348`, `rust/nesting_engine/src/nfp/concave.rs:357`, `rust/nesting_engine/src/nfp/concave.rs:366`, `rust/nesting_engine/src/nfp/concave.rs:444` | Tiltott transition készlet (`banned_transitions`) és kétfázisú iránypróba (`allow_immediate_backtrack`) biztosítja, hogy dead-end/revisit után legyen determinisztikus következő jelölt. | `cargo test --manifest-path rust/nesting_engine/Cargo.toml --test nfp_regression` |
| Next-event bővítés hiányzó eseménytípussal | PASS | `rust/nesting_engine/src/nfp/concave.rs:105`, `rust/nesting_engine/src/nfp/concave.rs:504`, `rust/nesting_engine/src/nfp/concave.rs:658`, `rust/nesting_engine/src/nfp/concave.rs:787` | `EventKind::VertexToVertex` és a hozzá tartozó jelölt- + kontaktellenőrzés bekerült; minden predikátum integer/i128 maradt. | `cargo test --manifest-path rust/nesting_engine/Cargo.toml --test orbit_next_event_trace_smoke` |
| Prefer_exact proof szigorítás (`>=3 ExactClosed`) | PASS | `rust/nesting_engine/tests/nfp_regression.rs:109`, `rust/nesting_engine/tests/nfp_regression.rs:175`, `rust/nesting_engine/tests/nfp_regression.rs:230`, `rust/nesting_engine/tests/nfp_regression.rs:293` | A teszt már külön számolja az exact no-fallback lezárásokat, és minimum 3-at kötelezővé tesz. | `cargo test --manifest-path rust/nesting_engine/Cargo.toml --test nfp_regression` |
| 3 cél fixture ExactClosed policy-ra állítva | PASS | `poc/nfp_regression/concave_touching_group.json:9`, `poc/nfp_regression/concave_interlock_c.json:9`, `poc/nfp_regression/concave_multi_contact.json:9` | A három cél fixture explicit `prefer_exact: true` és `expect_exact_error: false` beállítást kapott. | `cargo test --manifest-path rust/nesting_engine/Cargo.toml --test nfp_regression` |
| Kötelező verify wrapper futtatva | PASS | `codex/reports/nesting_engine/nfp_orbit_exact_closed_p0.md` (AUTO_VERIFY blokk) | A standard repo gate wrapper lefut és a report AUTO_VERIFY blokkban rögzíti a PASS eredményt. | `./scripts/verify.sh --report codex/reports/nesting_engine/nfp_orbit_exact_closed_p0.md` |

## 6) Prefer_exact outcome (expected vs actual)

| Fixture | expected (no-fallback) | actual | exact != stable proof |
|---|---|---|---|
| `concave_touching_group.json` | ExactClosed | ExactClosed | Igen (`allow_exact_equals_stable=false`) |
| `concave_interlock_c.json` | ExactClosed | ExactClosed | Igen (`allow_exact_equals_stable=false`) |
| `concave_multi_contact.json` | ExactClosed | ExactClosed | Igen (`allow_exact_equals_stable=false`) |

## 8) Advisory notes

- A `OrbitFailureReason::LoopDetected` enum-ág jelenleg nem kerül konstrukcióra (dead_code warning), mert a loopok most transition-tiltás + backtracking mechanizmussal kezelődnek.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-02-25T22:01:16+01:00 → 2026-02-25T22:04:58+01:00 (222s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/nesting_engine/nfp_orbit_exact_closed_p0.verify.log`
- git: `main@fb83cb4`
- módosított fájlok (git status): 10

**git diff --stat**

```text
 poc/nfp_regression/concave_multi_contact.json  |   4 +-
 poc/nfp_regression/concave_touching_group.json |   2 +-
 rust/nesting_engine/src/nfp/concave.rs         | 180 +++++++++++++++++++------
 rust/nesting_engine/tests/nfp_regression.rs    | 145 ++++++++++----------
 4 files changed, 215 insertions(+), 116 deletions(-)
```

**git status --porcelain (preview)**

```text
 M poc/nfp_regression/concave_multi_contact.json
 M poc/nfp_regression/concave_touching_group.json
 M rust/nesting_engine/src/nfp/concave.rs
 M rust/nesting_engine/tests/nfp_regression.rs
?? canvases/nesting_engine/nfp_orbit_exact_closed_p0.md
?? codex/codex_checklist/nesting_engine/nfp_orbit_exact_closed_p0.md
?? codex/goals/canvases/nesting_engine/fill_canvas_nfp_orbit_exact_closed_p0.yaml
?? codex/prompts/nesting_engine/nfp_orbit_exact_closed_p0/
?? codex/reports/nesting_engine/nfp_orbit_exact_closed_p0.md
?? codex/reports/nesting_engine/nfp_orbit_exact_closed_p0.verify.log
```

<!-- AUTO_VERIFY_END -->
