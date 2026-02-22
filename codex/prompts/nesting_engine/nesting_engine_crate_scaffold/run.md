# VRS Nesting Codex Task — NFP Nesting Engine: Rust crate scaffold + Clipper2 + scale policy
TASK_SLUG: nesting_engine_crate_scaffold

## 1) Kötelező olvasnivaló (prioritási sorrend)

Olvasd el és tartsd be, ebben a sorrendben:

1. `AGENTS.md` — repo-szabályok, gate parancsok
2. `docs/codex/overview.md` — workflow és DoD
3. `docs/codex/yaml_schema.md` — steps-séma kötelező
4. `docs/codex/report_standard.md` — report struktúra + AUTO_VERIFY blokk
5. `docs/qa/testing_guidelines.md` — minőségkapu részletek
6. `canvases/nesting_engine/nesting_engine_crate_scaffold.md` — a feladat specifikációja
7. `codex/goals/canvases/nesting_engine/fill_canvas_nesting_engine_crate_scaffold.yaml` — végrehajtandó lépések

Ha bármelyik fájl nem létezik: állj meg, és írd le pontosan mit kerestél és hol.

---

## 2) Cél

Új, önálló Rust crate létrehozása (`rust/nesting_engine/`) az NFP-alapú nesting motor
számára. A crate teljesen független a meglévő `rust/vrs_solver/`-tól — azt egyetlen
fájlban sem érinti.

A task deliverable-jei:
- `rust/nesting_engine/` crate scaffold (Cargo.toml + modulstruktúra)
- `clipper2` pure Rust crate bekötése (pinned verzió, **nem** C++ FFI)
- Scale policy: `SCALE = 1_000_000i64` (1 mm = 1 000 000 egység), `TOUCH_TOL = 1i64`
- `Point64`, `Polygon64`, `PartGeometry` típusok
- `inflate_part()` és `OffsetError` implementáció Clipper2-vel
- `cargo test` unit tesztek (scale round-trip, inflate, deflate, determinizmus)
- `docs/nesting_engine/tolerance_policy.md` dokumentáció
- `scripts/check.sh` és `.github/workflows/repo-gate.yml` bővítése az új crate build-del

## 3) Nem cél

- A `rust/vrs_solver/` bármilyen módosítása (az regressziós baseline, ÉRINTETLEN marad)
- NFP számítás (az F2-1/F2-2 task feladata)
- Python runner adapter (az F1-4 task feladata)
- IO contract JSON séma (az F1-2 task feladata)
- C++ FFI — kizárólag pure Rust `clipper2` crate használható

---

## 4) Munkaszabályok (nem alkuképes)

- **Valós repó elv:** nem találhatsz ki fájlokat, mezőket, parancsokat — csak a ténylegesen
  létező fájlokra hivatkozz. Ha valamit nem találsz, jelezd.
- **Outputs szabály:** csak olyan fájlt hozhatsz létre / módosíthatsz, ami szerepel az adott
  YAML step `outputs` listájában.
- **Minimal-invazív:** a meglévő működés nem romolhat. A `vrs_solver` build és smoke PASS
  marad a gate végén.
- **Gate csak wrapperrel:** a minőségkaput kizárólag a wrapperrel futtasd, ne rögtönözz
  párhuzamos check parancsokat.

---

## 5) Végrehajtás

Hajtsd végre a YAML `steps` lépéseit **sorrendben**, lépésről lépésre:

```
codex/goals/canvases/nesting_engine/fill_canvas_nesting_engine_crate_scaffold.yaml
```

Minden step után ellenőrizd:
- A step `outputs` listájában szereplő fájlok valóban létrejöttek / módosultak.
- Más fájl nem változott.

---

## 6) Kritikus ellenőrzési pontok

**Clipper2 verzió:** keress rá a crates.io-n a `clipper2` crate legfrissebb stabil
verziójára. Pineld be a Cargo.toml-ban (`clipper2 = "=X.Y.Z"` formátumban).
Ne használj wildcard verziót.

**vrs_solver regresszió:** a gate futtatása előtt explicit ellenőrizd:
```bash
cargo build --release --manifest-path rust/vrs_solver/Cargo.toml
```
Ha ez FAIL: a check.sh módosítás hibás — javítsd, mielőtt a gate-et futtatod.

**check.sh additive módosítás:** a meglévő lépések sorrendje és tartalma nem változhat.
Az új nesting_engine build lépés a vrs_solver lépés UTÁN kerüljön be.

---

## 7) Kötelező gate (a végén, egyszer)

```bash
./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_crate_scaffold.md
```

Ez automatikusan:
- lefuttatja a teljes `check.sh`-t (beleértve az új nesting_engine build-et)
- logot ment: `codex/reports/nesting_engine/nesting_engine_crate_scaffold.verify.log`
- frissíti a report `AUTO_VERIFY` blokkját

---

## 8) Elvárt kimenetek

A feladat végén a következő fájloknak kell létezniük és PASS státuszban lenniük:

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
- `codex/reports/nesting_engine/nesting_engine_crate_scaffold.md`
- `codex/reports/nesting_engine/nesting_engine_crate_scaffold.verify.log`

**Módosított fájlok:**
- `scripts/check.sh` — nesting_engine build lépés hozzáadva
- `.github/workflows/repo-gate.yml` — nesting_engine CI build bekötve

**Érintetlen (ellenőrizd, hogy valóban nem változott):**
- `rust/vrs_solver/` (teljes könyvtár)
- `vrs_nesting/` (teljes könyvtár)
- `scripts/verify.sh`

---

## 9) Elfogadási kritériumok

A feladat akkor PASS, ha:

1. `cargo test --manifest-path rust/nesting_engine/Cargo.toml` — PASS
2. `cargo build --release --manifest-path rust/nesting_engine/Cargo.toml` — PASS
3. `cargo build --release --manifest-path rust/vrs_solver/Cargo.toml` — PASS (regresszió)
4. Scale round-trip teszt: `abs(i64_to_mm(mm_to_i64(10.5)) - 10.5) < 1e-6`
5. Inflate outer: 100×200mm téglalap + 1.0mm delta → bbox ≥ 101.9×201.9mm
6. Determinizmus: két egymást követő `inflate_part()` hívás azonos inputra azonos outputot ad
7. `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_crate_scaffold.md` — PASS