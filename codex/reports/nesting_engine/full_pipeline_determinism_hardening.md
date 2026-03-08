# Codex Report — full_pipeline_determinism_hardening

**Status:** PASS_WITH_NOTES

---

## 1) Meta

- **Task slug:** `full_pipeline_determinism_hardening`
- **Kapcsolódó canvas:** `canvases/nesting_engine/full_pipeline_determinism_hardening.md`
- **Kapcsolódó goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_full_pipeline_determinism_hardening.yaml`
- **Futás dátuma:** 2026-03-08
- **Branch / commit:** `main` / `588ad24` (uncommitted changes)
- **Fókusz terület:** Mixed

## 2) Scope

### 2.1 Cél

1. Repo-native canonicalization contract lezárása a docs és kód között.
2. 10-run determinism smoke keményítése teljes output byte-azonosságra.
3. Python oldali canonical hash újraszámolás bizonyítása a solver `meta.determinism_hash` mezőhöz.
4. Touching policy explicit evidence tesztek hozzáadása `touching_policy_` prefixszel.
5. PR gate integráció megtartása a meglévő `scripts/check.sh` + `repo-gate.yml` útvonalon.

### 2.2 Nem-cél (explicit)

1. Teljes geometriai integer-only átírás.
2. Új placer/search mód bevezetése.
3. Objective sorrend vagy timeout policy újradefiniálása.
4. Platform rotation workflow (`platform-determinism-rotation.yml`) helyettesítése.

## 3) Változások összefoglalója

### 3.1 Érintett fájlok

- **Rust:**
  - `rust/nesting_engine/src/feasibility/narrow.rs`
  - `rust/nesting_engine/src/export/output_v2.rs`
- **Scripts:**
  - `scripts/smoke_nesting_engine_determinism.sh`
  - `scripts/check.sh`
- **Docs:**
  - `docs/nesting_engine/json_canonicalization.md`
  - `docs/nesting_engine/io_contract_v2.md`
  - `docs/nesting_engine/tolerance_policy.md`
  - `docs/known_issues/nesting_engine_known_issues.md`
- **Codex artifacts:**
  - `codex/codex_checklist/nesting_engine/full_pipeline_determinism_hardening.md`
  - `codex/reports/nesting_engine/full_pipeline_determinism_hardening.md`

### 3.2 Miért változtak?

- A canonicalization dokumentáció JCS-többletállításait repo-native contractra zártuk, a tényleges Rust/Python útvonalhoz igazítva.
- A determinism smoke már a teljes `nest` stdout JSON-t hasonlítja, és eltérésnél baseline/mismatch artefaktot ment.
- A smoke Python oldalon újraszámolja a canonical hash-t, és egyezteti a solver `meta.determinism_hash` értékével.
- A touching policy explicit, külön futtatható evidence teszteket kapott.
- A `check.sh` explicit futtatja a `determinism_` és `touching_policy_` teszteket, valamint a 10-run determinism smoke-ot.

## 4) Verifikáció

### 4.1 Kötelező parancs

- `./scripts/verify.sh --report codex/reports/nesting_engine/full_pipeline_determinism_hardening.md` -> PASS (AUTO_VERIFY blokk).

### 4.2 Opcionális, task-specifikus parancsok

- `cargo test --manifest-path rust/nesting_engine/Cargo.toml determinism_` -> PASS.
- `cargo test --manifest-path rust/nesting_engine/Cargo.toml touching_policy_` -> PASS.
- `RUNS=10 ./scripts/smoke_nesting_engine_determinism.sh` -> PASS.

### 4.3 Ha valami kimaradt

- Nem maradt ki kötelező ellenőrzés.

## 5) DoD -> Evidence Matrix

| DoD pont | Státusz | Bizonyíték (path + line) | Magyarázat | Kapcsolódó teszt/ellenőrzés |
|---|---|---|---|---|
| A `determinism_hash` canonicalization contract doksi-kód szinten egységes. | PASS | `docs/nesting_engine/json_canonicalization.md:35`, `rust/nesting_engine/src/export/output_v2.rs:75`, `scripts/canonicalize_json.py:96` | A dokumentált hash-view és canonicalizációs szabály ugyanarra a `nesting_engine.hash_view.v1` contractra mutat Rust/Python oldalon. | `cargo test ... determinism_` |
| A `json_canonicalization.md` nem állít többet, mint amit a Rust/Python implementáció garantál. | PASS | `docs/nesting_engine/json_canonicalization.md:18`, `docs/nesting_engine/json_canonicalization.md:101` | A normatív szöveg explicit repo-native equivalence-re szűkít, nem állít teljes RFC 8785 megfelelést. | Doksi review + `cargo test ... determinism_` |
| Van 10-run determinism smoke ugyanarra az inputra, ugyanazzal a seed-del. | PASS | `scripts/smoke_nesting_engine_determinism.sh:8`, `scripts/check.sh:607` | A smoke alapértelmezett futásszáma 10, és check gate-ben is `RUNS=10`-zel fut. | `RUNS=10 ./scripts/smoke_nesting_engine_determinism.sh` |
| A 10-run smoke a teljes output JSON byte-identitását ellenőrzi. | PASS | `scripts/smoke_nesting_engine_determinism.sh:53`, `scripts/smoke_nesting_engine_determinism.sh:96` | A script a teljes stdout JSON fájlokat hasonlítja `cmp`-vel, nem csak hash mezőt. | `RUNS=10 ./scripts/smoke_nesting_engine_determinism.sh` |
| A smoke ellenőrzi, hogy a Python canonical hash egyezik a solver `meta.determinism_hash` mezővel. | PASS | `scripts/smoke_nesting_engine_determinism.sh:56`, `scripts/smoke_nesting_engine_determinism.sh:85` | Minden run után Python oldali canonical hash újraszámolás történik és egyezést assertál. | `RUNS=10 ./scripts/smoke_nesting_engine_determinism.sh` |
| Explicit evidence tesztek vannak `touching_policy_` prefixszel. | PASS | `rust/nesting_engine/src/feasibility/narrow.rs:384`, `rust/nesting_engine/src/feasibility/narrow.rs:435` | Két explicit touching policy teszt került be a kért prefixekkel. | `cargo test ... touching_policy_` |
| `touching = infeasible` dokumentálva van. | PASS | `docs/nesting_engine/tolerance_policy.md:65`, `docs/nesting_engine/tolerance_policy.md:75` | A policy explicit kimondja a touching tiltást, külön part-part és bin-boundary bontással. | `cargo test ... touching_policy_` |
| A determinism smoke a `scripts/check.sh` része, tehát PR-ban automatikusan fut. | PASS | `scripts/check.sh:607`, `docs/nesting_engine/io_contract_v2.md:135`, `.github/workflows/repo-gate.yml:1` | A `check.sh` futtatja a 10-run smoke-ot; a repo gate workflow a `check.sh`-n keresztül kötelező PR check. | `./scripts/verify.sh --report ...` |
| `./scripts/verify.sh --report codex/reports/nesting_engine/full_pipeline_determinism_hardening.md` PASS. | PASS | `codex/reports/nesting_engine/full_pipeline_determinism_hardening.md` | A verify futás eredménye az AUTO_VERIFY blokkban lesz rögzítve. | `./scripts/verify.sh --report codex/reports/nesting_engine/full_pipeline_determinism_hardening.md` |
| Checklist + report elkészül Report Standard v2 szerint. | PASS | `codex/codex_checklist/nesting_engine/full_pipeline_determinism_hardening.md:1`, `codex/reports/nesting_engine/full_pipeline_determinism_hardening.md:1` | A checklist és report létrehozva, a kötelező struktúrával és evidence mátrixszal. | Doksi review |

## 6) IO contract / minták

- A v2 IO contract nem kapott új verziót.
- A `meta.determinism_hash` contract változatlanul `nesting_engine.hash_view.v1`.
- A változás a contract értelmezésének és evidence gate-jének hardeningje.

## 7) Doksi szinkron

- Frissült canonicalization, IO contract, tolerance policy és known issues.
- KI-006 státusz: `RESOLVED (full_pipeline_determinism_hardening, 2026-03-08)`.

## 8) Advisory notes

- Ez a kör kifejezetten **repo-native determinism contract hardening**, nem teljes geometriai integer-only átírás.
- KI-007 (további f64 útvonalak) továbbra is külön issue scope-ban marad.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-03-08T18:44:33+01:00 → 2026-03-08T18:47:40+01:00 (187s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/nesting_engine/full_pipeline_determinism_hardening.verify.log`
- git: `main@588ad24`
- módosított fájlok (git status): 14

**git diff --stat**

```text
 docs/known_issues/nesting_engine_known_issues.md |  51 ++---
 docs/nesting_engine/io_contract_v2.md            |  12 +-
 docs/nesting_engine/json_canonicalization.md     | 256 +++++++----------------
 docs/nesting_engine/tolerance_policy.md          |  11 +
 rust/nesting_engine/src/export/output_v2.rs      |  36 +++-
 rust/nesting_engine/src/feasibility/narrow.rs    |  22 ++
 scripts/check.sh                                 |  11 +-
 scripts/smoke_nesting_engine_determinism.sh      |  55 ++++-
 8 files changed, 223 insertions(+), 231 deletions(-)
```

**git status --porcelain (preview)**

```text
 M docs/known_issues/nesting_engine_known_issues.md
 M docs/nesting_engine/io_contract_v2.md
 M docs/nesting_engine/json_canonicalization.md
 M docs/nesting_engine/tolerance_policy.md
 M rust/nesting_engine/src/export/output_v2.rs
 M rust/nesting_engine/src/feasibility/narrow.rs
 M scripts/check.sh
 M scripts/smoke_nesting_engine_determinism.sh
?? canvases/nesting_engine/full_pipeline_determinism_hardening.md
?? codex/codex_checklist/nesting_engine/full_pipeline_determinism_hardening.md
?? codex/goals/canvases/nesting_engine/fill_canvas_full_pipeline_determinism_hardening.yaml
?? codex/prompts/nesting_engine/full_pipeline_determinism_hardening/
?? codex/reports/nesting_engine/full_pipeline_determinism_hardening.md
?? codex/reports/nesting_engine/full_pipeline_determinism_hardening.verify.log
```

<!-- AUTO_VERIFY_END -->
