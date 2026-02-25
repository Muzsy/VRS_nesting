# Codex Report — f2_2_p1_bundle_determinism_and_regression_hardening

**Status:** PASS_WITH_NOTES

---

## 1) Meta

- **Task slug:** `f2_2_p1_bundle_determinism_and_regression_hardening`
- **Kapcsolódó canvas:** `canvases/nesting_engine/f2_2_p1_bundle_determinism_and_regression_hardening.md`
- **Kapcsolódó goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_f2_2_p1_bundle_determinism_and_regression_hardening.yaml`
- **Futás dátuma:** 2026-02-25
- **Branch / commit:** `main` / `0095826` (uncommitted changes)
- **Fókusz terület:** Mixed (Determinism + Docs + Regression workflow)

## 2) Scope

### 2.1 Cél

1. P1-1: byte-azonos canonical JSON unit teszt bevezetése Rust oldalon a hash-view stringre.
2. P1-2: canonicalization specifikáció pontosítása implementáció-kötött, normatív JCS-szubszetre.
3. P1-3: CLI canonical determinism smoke bekötése a `check.sh` quality gate-be (default 10, env-ből 50+).
4. P1-4: quarantine fixture acceptance workflow formalizálása a regressziós README-ben.

### 2.2 Nem-cél (explicit)

1. Concave/orbit algoritmus újabb módosítása.
2. Új dependency bevezetése.
3. `scripts/verify.sh` wrapper módosítása.
4. Holes támogatás vagy más F2-2 scope-bővítés.

## 3) Változások összefoglalója

### 3.1 Érintett fájlok

- `canvases/nesting_engine/f2_2_p1_bundle_determinism_and_regression_hardening.md`
- `rust/nesting_engine/src/export/output_v2.rs`
- `docs/nesting_engine/json_canonicalization.md`
- `scripts/check.sh`
- `poc/nfp_regression/README.md`
- `codex/codex_checklist/nesting_engine/f2_2_p1_bundle_determinism_and_regression_hardening.md`
- `codex/reports/nesting_engine/f2_2_p1_bundle_determinism_and_regression_hardening.md`

### 3.2 Before / After (4 P1 pont)

- **P1-1 canonical-bytes teszt**
  - Before: csak hash-stabilitás teszt volt, explicit canonical string bytes összevetés nélkül.
  - After: külön helper (`hash_view_v1_canonical_json_bytes`) + új unit teszt explicit expected canonical stringgel.
- **P1-2 spec drift**
  - Before: a doksi teljes RFC8785 fókuszú volt, kevésbé implementációhoz kötött normatív szinttel.
  - After: normatív JCS-kompatibilis szubszet, és explicit Rust/Python referencia serializáció szerepel.
- **P1-3 gate smoke**
  - Before: `smoke_nesting_engine_determinism.sh` létezett, de a kötelező check gate nem futtatta.
  - After: `check.sh` fast-input generálással futtatja; default runszám 10, `NESTING_ENGINE_DETERMINISM_RUNS` envvel emelhető (pl. 50).
- **P1-4 quarantine workflow**
  - Before: fixture README nem tartalmazott explicit quarantine->accept folyamatot.
  - After: külön workflow szekció leírja a generálás, accept, törés utáni döntési folyamat lépéseit.

## 4) Verifikáció

### 4.1 Kötelező parancs

- `./scripts/verify.sh --report codex/reports/nesting_engine/f2_2_p1_bundle_determinism_and_regression_hardening.md` -> PASS (AUTO_VERIFY blokk).

### 4.2 Opcionális, task-specifikus parancsok

- `cargo test --manifest-path rust/nesting_engine/Cargo.toml` -> PASS.
- `cargo test --manifest-path rust/nesting_engine/Cargo.toml hash_view_v1_canonical_json_is_byte_identical` -> PASS.
- `RUNS=3 INPUT_JSON=/tmp/f2_2_p1_fast_input.json ./scripts/smoke_nesting_engine_determinism.sh` -> PASS.

### 4.3 Ha valami kimaradt

- Nincs kimaradt kötelező ellenőrzés.

## 5) DoD -> Evidence Matrix

| DoD pont | Státusz | Bizonyíték (path + line) | Magyarázat | Kapcsolódó teszt/ellenőrzés |
|---|---|---|---|---|
| Canonical JSON byte-level teszt van Rustban | PASS | `rust/nesting_engine/src/export/output_v2.rs:71`, `rust/nesting_engine/src/export/output_v2.rs:128`, `rust/nesting_engine/src/export/output_v2.rs:168` | A hash-view canonical JSON előállítás külön helperben van, és explicit byte-string expected assert került be. | `cargo test --manifest-path rust/nesting_engine/Cargo.toml hash_view_v1_canonical_json_is_byte_identical` |
| json_canonicalization spec implementációhoz igazított normatív rész | PASS | `docs/nesting_engine/json_canonicalization.md:28`, `docs/nesting_engine/json_canonicalization.md:140`, `docs/nesting_engine/json_canonicalization.md:150` | A dokumentum most kimondja a JCS-szubszet szabályokat és név szerint rögzíti a Python/Rust referencia serializációt. | doksi review + `scripts/canonicalize_json.py` / `output_v2.rs` összevetés |
| Determinism smoke bekötve a check gate-be | PASS | `scripts/check.sh:95`, `scripts/check.sh:384`, `scripts/check.sh:398` | A smoke script executable listába került, fast input készül `/tmp` alá, majd a smoke fut default 10 runnal és env override támogatással. | `./scripts/check.sh` (verify részeként) |
| Quarantine acceptance workflow formalizálva | PASS | `poc/nfp_regression/README.md:40`, `poc/nfp_regression/README.md:53`, `poc/nfp_regression/README.md:65` | A README új szekcióban leírja a quarantine jelentését, accept lépéseit és törés utáni teendőket. | README review |
| `cargo test` (nesting_engine) PASS | PASS | `codex/reports/nesting_engine/f2_2_p1_bundle_determinism_and_regression_hardening.md` (Verifikáció) | A crate teljes tesztkészlete lefutott, benne az új canonical-bytes teszttel. | `cargo test --manifest-path rust/nesting_engine/Cargo.toml` |
| verify wrapper PASS | PASS | `codex/reports/nesting_engine/f2_2_p1_bundle_determinism_and_regression_hardening.md` (AUTO_VERIFY blokk) | A standard verify wrapper futása PASS, log fájl mentve. | `./scripts/verify.sh --report ...` |

## 8) Advisory notes

- A buildben továbbra is látszanak meglévő `dead_code` warningok (nem regresszió, nem blokkoló).

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-02-25T22:26:20+01:00 → 2026-02-25T22:29:41+01:00 (201s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/nesting_engine/f2_2_p1_bundle_determinism_and_regression_hardening.verify.log`
- git: `main@0095826`
- módosított fájlok (git status): 10

**git diff --stat**

```text
 docs/nesting_engine/json_canonicalization.md | 56 +++++++++++++++-------------
 poc/nfp_regression/README.md                 | 36 ++++++++++++++++++
 rust/nesting_engine/src/export/output_v2.rs  | 46 ++++++++++++++++++++++-
 scripts/check.sh                             | 20 ++++++++++
 4 files changed, 131 insertions(+), 27 deletions(-)
```

**git status --porcelain (preview)**

```text
 M docs/nesting_engine/json_canonicalization.md
 M poc/nfp_regression/README.md
 M rust/nesting_engine/src/export/output_v2.rs
 M scripts/check.sh
?? canvases/nesting_engine/f2_2_p1_bundle_determinism_and_regression_hardening.md
?? codex/codex_checklist/nesting_engine/f2_2_p1_bundle_determinism_and_regression_hardening.md
?? codex/goals/canvases/nesting_engine/fill_canvas_f2_2_p1_bundle_determinism_and_regression_hardening.yaml
?? codex/prompts/nesting_engine/f2_2_p1_bundle_determinism_and_regression_hardening/
?? codex/reports/nesting_engine/f2_2_p1_bundle_determinism_and_regression_hardening.md
?? codex/reports/nesting_engine/f2_2_p1_bundle_determinism_and_regression_hardening.verify.log
```

<!-- AUTO_VERIFY_END -->
