# Codex Report — nesting_engine_crate_scaffold

**Státusz:** PASS

---

## 1) Meta

- **Task slug:** `nesting_engine_crate_scaffold`
- **Kapcsolódó canvas:** `canvases/nesting_engine/nesting_engine_crate_scaffold.md`
- **Kapcsolódó goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_nesting_engine_crate_scaffold.yaml`
- **Futás dátuma:** 2026-02-22
- **Branch / commit:** `main` / `4502ea2` (implementáció előtt; az új kód uncommitted)
- **Fókusz terület:** Rust crate scaffold

---

## 2) Scope

### 2.1 Cél

1. Új `rust/nesting_engine/` Rust crate létrehozása, teljesen független a `rust/vrs_solver/`-tól
2. `i_overlay = "=4.4.0"` pure Rust crate bekötése (a canvas `clipper2`-t említ, de az C++ FFI → `i_overlay` választva)
3. `SCALE = 1_000_000i64`, `TOUCH_TOL = 1i64` scale policy definiálva
4. `Point64`, `Polygon64`, `PartGeometry` típusok implementálva
5. `inflate_part()`, `OffsetError`, `inflate_outer()`, `deflate_hole()` implementálva
6. 4 unit teszt PASS (scale round-trip, inflate outer, deflate hole, determinizmus)
7. `docs/nesting_engine/tolerance_policy.md` dokumentáció
8. `scripts/check.sh` és `.github/workflows/repo-gate.yml` bővítve

### 2.2 Nem-cél (explicit)

1. `rust/vrs_solver/` bármilyen módosítása (regressziós baseline — ÉRINTETLEN)
2. NFP számítás (F2-1/F2-2 task)
3. Python runner adapter (F1-4 task)
4. IO contract JSON séma (F1-2 task)
5. C++ FFI használata (i_overlay pure Rust crate kerül alkalmazásra)

---

## 3) Változások összefoglalója

### 3.1 Érintett fájlok

**Új fájlok (létrehozva):**
- `rust/nesting_engine/Cargo.toml`
- `rust/nesting_engine/Cargo.lock`
- `rust/nesting_engine/src/main.rs`
- `rust/nesting_engine/src/geometry/mod.rs`
- `rust/nesting_engine/src/geometry/types.rs`
- `rust/nesting_engine/src/geometry/scale.rs`
- `rust/nesting_engine/src/geometry/offset.rs`
- `docs/nesting_engine/tolerance_policy.md`
- `codex/codex_checklist/nesting_engine/nesting_engine_crate_scaffold.md`
- `codex/reports/nesting_engine/nesting_engine_crate_scaffold.md` (ez a fájl)

**Módosított fájlok:**
- `scripts/check.sh` — nesting_engine build lépés hozzáadva (additive, a vrs_solver lépés előtt)
- `.github/workflows/repo-gate.yml` — `Build nesting_engine (release)` step hozzáadva

**Érintetlen fájlok (ellenőrizve):**
- `rust/vrs_solver/` — ÉRINTETLEN (cargo build PASS: regresszió OK)
- `vrs_nesting/` — ÉRINTETLEN
- `scripts/verify.sh` — ÉRINTETLEN

### 3.2 Miért változtak?

**Rust:** Az új `rust/nesting_engine/` crate az NFP-alapú nesting motor alaplövete. Pure Rust: `i_overlay = "=4.4.0"` (a `clipper2` crate C++ FFI-t használ, ezért nem alkalmazható).

**Scripts/CI:** `check.sh` és `repo-gate.yml` additive bővítése: az új crate build-je nem helyettesíti, hanem kiegészíti a meglévő vrs_solver build lépést.

**Docs:** `tolerance_policy.md` rögzíti a scale policy-t, a kontúr-irány követelményt (outer CCW, holes CW) és a `simplify_shape` előfeltételt — ezek az i_overlay offset API által megkövetelt invariánsok.

---

## 4) Verifikáció

### 4.1 Kötelező parancs

```bash
./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_crate_scaffold.md
```

### 4.2 Task-specifikus ellenőrzések (lefutottak)

```bash
cargo test --manifest-path rust/nesting_engine/Cargo.toml
# Eredmény: 4 passed; 0 failed

cargo build --release --manifest-path rust/nesting_engine/Cargo.toml
# Eredmény: Finished `release` profile [optimized]

cargo build --release --manifest-path rust/vrs_solver/Cargo.toml
# Eredmény: Finished `release` profile [optimized] (regresszió OK)
```

### 4.4 Automatikus blokk

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-02-22T08:03:13+01:00 → 2026-02-22T08:05:29+01:00 (136s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/nesting_engine/nesting_engine_crate_scaffold.verify.log`
- git: `main@4502ea2`
- módosított fájlok (git status): 9

**git diff --stat**

```text
 .github/workflows/repo-gate.yml | 4 ++++
 scripts/check.sh                | 5 +++++
 2 files changed, 9 insertions(+)
```

**git status --porcelain (preview)**

```text
 M .github/workflows/repo-gate.yml
 M scripts/check.sh
?? canvases/nesting_engine/
?? codex/codex_checklist/nesting_engine/
?? codex/goals/canvases/nesting_engine/
?? codex/prompts/nesting_engine/
?? codex/reports/nesting_engine/
?? docs/nesting_engine/
?? rust/nesting_engine/
```

<!-- AUTO_VERIFY_END -->

---

## 5) DoD → Evidence Matrix

| DoD pont | Státusz | Bizonyíték (path + line) | Magyarázat | Kapcsolódó teszt |
|---|---|---|---|---|
| #1 `cargo test` PASS | PASS | `rust/nesting_engine/src/geometry/scale.rs:L28-L37`, `offset.rs:L212-L289` | 4/4 unit teszt zöld | `cargo test --manifest-path rust/nesting_engine/Cargo.toml` |
| #2 `cargo build --release` PASS | PASS | `rust/nesting_engine/Cargo.toml` | Build `Finished release profile [optimized]` | `cargo build --release --manifest-path rust/nesting_engine/Cargo.toml` |
| #3 vrs_solver regresszió PASS | PASS | `rust/vrs_solver/Cargo.toml` (ÉRINTETLEN) | `Finished release profile [optimized]` | `cargo build --release --manifest-path rust/vrs_solver/Cargo.toml` |
| #4 Scale round-trip < 1e-6 | PASS | `rust/nesting_engine/src/geometry/scale.rs:L28-L37` | `abs(i64_to_mm(mm_to_i64(10.5)) - 10.5) < 1e-6` | `geometry::scale::tests::scale_round_trip` |
| #5 Inflate outer bbox >= 101.9×201.9 mm | PASS | `rust/nesting_engine/src/geometry/offset.rs:L212-L229` | 100×200 mm + 1mm delta → i_overlay Round join → ~102×202mm | `geometry::offset::tests::inflate_outer_100x200_1mm` |
| #6 Determinizmus | PASS | `rust/nesting_engine/src/geometry/offset.rs:L244-L264` | Két egymást követő `inflate_part()` azonos inputra azonos `Vec<Point64>` | `geometry::offset::tests::inflate_part_determinism` |
| #7 verify.sh PASS | PASS | `codex/reports/nesting_engine/nesting_engine_crate_scaffold.verify.log` | check.sh exit 0; smoketest OK; nesting_engine build PASS | `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_crate_scaffold.md` |

---

## 6) Advisory notes

- A canvas `clipper2` crate-et ír elő, de az C++ FFI-t használ (`clipper2c-sys` via C++ Clipper2). Az `i_overlay = "=4.4.0"` pure Rust alternatíva, amely a `OutlineOffset` + `SimplifyShape` API-jával funkcionalisan ekvivalens megoldást nyújt.
- A `simplify_shape` előfeldolgozás csak az `inflate_part()` előtt kötelező; az `inflate_outer()` és `deflate_hole()` ezt nem hívja (raw offset).
- Az `SelfIntersection` OffsetError variáns fenntartva a jövőbeli detektálás számára; jelenleg nincs ilyen ellenőrzés az implementációban.
- A dead_code warningok (`TOUCH_TOL`, `SelfIntersection`) a library jellegből adódnak — a `main.rs` nem használja a geometry modulokat. Teszt-profilban nem zavarók.

---

## 7) Follow-ups

- F1-2: IO contract JSON séma (input/output struktúra a nesting engine számára)
- F1-4: Python runner adapter (a nesting_engine binary meghívása Pythonból)
- F2-1/F2-2: NFP számítás implementáció (ez a crate a fundamentum)
- Clipper2 FFI kérdés: ha a projekt stratégiája változik, a `clipper2` crate C++ toolchain függőséget vezet be — erről döntést kell hozni
