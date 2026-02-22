# canvases/nesting_engine/nesting_engine_crate_scaffold.md

> **Mentés helye a repóban:** `canvases/nesting_engine/nesting_engine_crate_scaffold.md`
> **TASK_SLUG:** `nesting_engine_crate_scaffold`
> **Terület (AREA):** `nesting_engine`

---

# NFP Nesting Engine — Rust crate scaffold + Clipper2 + scale policy

## 🎯 Funkció

Új, önálló Rust crate létrehozása (`rust/nesting_engine/`) az NFP-alapú nesting motor számára. A crate a meglévő `rust/vrs_solver/`-tól teljesen független — azt nem érinti, az regressziós baseline marad.

A task célja:

- A crate workspace scaffold felállítása (Cargo.toml, src/main.rs, modulstruktúra)
- A `clipper2` pure Rust crate bekötése (nem C++ FFI)
- Egységes, kőbe vésett scale policy definiálása (mm → i64 → mm)
- Clipper2 offset alap smoke: outer inflate + hole deflate egyszerű téglalapra
- A repo gate CI build kiterjesztése az új crate-re

**Nem cél:**

- NFP számítás (az F2-1, F2-2 task)
- Python runner adapter (az F1-4 task)
- IO contract (az F1-2 task)
- A meglévő `rust/vrs_solver/` bármilyen módosítása

---

## 🧠 Fejlesztési részletek

### Érintett fájlok

**Létrehozandó (új):**

- `rust/nesting_engine/Cargo.toml`
- `rust/nesting_engine/src/main.rs`
- `rust/nesting_engine/src/geometry/mod.rs`
- `rust/nesting_engine/src/geometry/types.rs`
- `rust/nesting_engine/src/geometry/offset.rs`
- `rust/nesting_engine/src/geometry/scale.rs`
- `docs/nesting_engine/tolerance_policy.md`

**Módosuló (meglévő):**

- `scripts/check.sh` — az új crate `cargo build --release` hozzáadása
- `.github/workflows/repo-gate.yml` — az új crate CI build bekötése

**Nem módosul:**

- `rust/vrs_solver/` (egyetlen fájl sem)
- `vrs_nesting/` (egyetlen fájl sem)
- `scripts/verify.sh`

---

### Scale policy (kőbe vésett definíció)

```
SCALE = 1_000_000i64   (1 mm = 1_000_000 egység)
```

- Minden bemeneti koordináta (mm, f64) → `round(val * SCALE) as i64`
- Minden kimeneti koordináta → `val as f64 / SCALE as f64`
- A konverzió veszteséges, de determinisztikus és reprodukálható
- Maximális kezelhető méret: ±9_223_372m (i64 max / SCALE) → teljesen elegendő
- Tolerancia a "touching" detektáláshoz: `TOUCH_TOL = 1i64` (= 1 µm)

Ez a policy a `docs/nesting_engine/tolerance_policy.md`-ben dokumentálandó.

---

### Crate modulstruktúra

```
rust/nesting_engine/
  Cargo.toml
  src/
    main.rs              ← CLI skeleton (egyelőre: --version, --help)
    geometry/
      mod.rs             ← pub use re-exportok
      types.rs           ← Point64, Polygon64, PartGeometry struktúrák
      scale.rs           ← mm_to_i64(), i64_to_mm(), scale policy konstansok
      offset.rs          ← inflate_polygon(), deflate_polygon() Clipper2-vel
```

---

### `types.rs` — alaptípusok

```rust
/// Egyetlen pont skálázott egész koordinátákban (1 egység = 1 µm = 1/SCALE mm)
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Point64 {
    pub x: i64,
    pub y: i64,
}

/// Zárt polygon: pontok listája, az utolsó pont implicitite össze van kötve az elsővel
#[derive(Debug, Clone)]
pub struct Polygon64 {
    pub outer: Vec<Point64>,
    pub holes: Vec<Vec<Point64>>,
}

/// Egy alkatrész geometriája (nominális vagy inflated)
#[derive(Debug, Clone)]
pub struct PartGeometry {
    pub id: String,
    pub polygon: Polygon64,
}
```

---

### `scale.rs` — scale policy

```rust
pub const SCALE: i64 = 1_000_000;
pub const TOUCH_TOL: i64 = 1;

/// mm (f64) → skálázott i64
pub fn mm_to_i64(mm: f64) -> i64 {
    (mm * SCALE as f64).round() as i64
}

/// skálázott i64 → mm (f64)
pub fn i64_to_mm(scaled: i64) -> f64 {
    scaled as f64 / SCALE as f64
}
```

---

### `offset.rs` — Clipper2 inflate/deflate

A `clipper2` Rust crate-et kell használni (nem C++ FFI).

```rust
/// Outer polygon inflate: pozitív delta (kerf + margin, mm-ben megadva)
pub fn inflate_outer(polygon: &Polygon64, delta_mm: f64) -> Result<Polygon64, OffsetError> { ... }

/// Hole polygon deflate: negatív delta (befelé tol)
pub fn deflate_hole(hole: &[Point64], delta_mm: f64) -> Result<Vec<Point64>, OffsetError> { ... }

/// Teljes PartGeometry inflate: outer kifelé, holes befelé
pub fn inflate_part(geom: &PartGeometry, delta_mm: f64) -> Result<PartGeometry, OffsetError> { ... }
```

Hibakód:

```rust
#[derive(Debug)]
pub enum OffsetError {
    HoleCollapsed { hole_index: usize },
    SelfIntersection,
    ClipperError(String),
}
```

---

### Smoke teszt (beépített, `cargo test`-tel futtatható)

```rust
#[cfg(test)]
mod tests {
    // 1) Scale round-trip: 10.5 mm → i64 → mm == 10.5 mm (tolerancián belül)
    // 2) Inflate outer: 100x200mm téglalap, delta=1mm → 102x202mm bounding box
    // 3) Deflate hole: 50x50mm lyuk, delta=1mm → 48x48mm bounding box
    // 4) Determinizmus: ugyanaz az input → ugyanaz az output (byte-szinten azonos)
}
```

---

### `scripts/check.sh` módosítás

A meglévő `cargo build --release` lépés mellé (vagy utána) kerüljön:

```bash
# nesting_engine build
cargo build --release --manifest-path rust/nesting_engine/Cargo.toml
```

Fontos: **ne töröljük** a `vrs_solver` build lépést — az regressziós baseline.

---

### `.github/workflows/repo-gate.yml` módosítás

A meglévő `cargo build` step bővítendő az új crate-tel, vagy külön step-ként kerüljön be, a meglévő vrs_solver step megőrzésével.

---

### Kockázat + mitigáció + rollback

| Kockázat | Mitigáció | Rollback |
|---|---|---|
| `clipper2` crate API változás | Pin konkrét verzió a Cargo.toml-ban, pl. `clipper2 = "=0.x.y"` | Cargo.lock visszaállítás |
| Clipper2 offset után önmetsző polygon | `OffsetError::SelfIntersection` explicit hiba, nem silent corrupt | Nincs state változás, az offset call pure function |
| `check.sh` bővítés eltöri a meglévő gate-et | Csak additive változás: `||` helyett önálló step, vrs_solver build érintetlen | git revert a check.sh változásra |
| Új crate-et a CI nem találja | Repo-relatív manifest path megadása: `--manifest-path rust/nesting_engine/Cargo.toml` | CI lépés eltávolítása |

---

## ✅ Pipálható DoD lista

### Felderítés
- [ ] `AGENTS.md` elolvasva
- [ ] `docs/codex/overview.md` elolvasva
- [ ] `docs/codex/yaml_schema.md` elolvasva
- [ ] `docs/codex/report_standard.md` elolvasva
- [ ] Meglévő `rust/vrs_solver/Cargo.toml` minta megvizsgálva (dependency pinning minta)
- [ ] Meglévő `scripts/check.sh` cargo build lépés megkeresve

### Implementáció
- [ ] `rust/nesting_engine/Cargo.toml` létrehozva, `clipper2` pinned dependency
- [ ] `src/main.rs` CLI skeleton (`--version`, `--help`)
- [ ] `src/geometry/types.rs` — `Point64`, `Polygon64`, `PartGeometry`
- [ ] `src/geometry/scale.rs` — `SCALE`, `TOUCH_TOL`, `mm_to_i64()`, `i64_to_mm()`
- [ ] `src/geometry/offset.rs` — `inflate_part()`, `OffsetError`
- [ ] `docs/nesting_engine/tolerance_policy.md` — scale policy + touching policy dokumentálva
- [ ] `scripts/check.sh` — új crate build hozzáadva, vrs_solver build érintetlen
- [ ] `.github/workflows/repo-gate.yml` — új crate CI build bekötve

### Tesztek
- [ ] `cargo test` PASS az új crate-en (scale round-trip, inflate outer, deflate hole, determinizmus)
- [ ] `cargo build --release --manifest-path rust/nesting_engine/Cargo.toml` PASS
- [ ] `cargo build --release --manifest-path rust/vrs_solver/Cargo.toml` PASS (regresszió: nem tört el)

### Gate
- [ ] `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_crate_scaffold.md` PASS

---

## 🧪 Tesztállapot

**Kötelező gate:**
```
./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_crate_scaffold.md
```

**Task-specifikus ellenőrzések:**
```bash
cargo test --manifest-path rust/nesting_engine/Cargo.toml
cargo build --release --manifest-path rust/nesting_engine/Cargo.toml
cargo build --release --manifest-path rust/vrs_solver/Cargo.toml   # regresszió check
```

**Elfogadási kritérium:**
- Scale round-trip teszt: `abs(i64_to_mm(mm_to_i64(10.5)) - 10.5) < 1e-6`
- Inflate outer teszt: 100×200mm téglalap, delta=1.0mm → bbox legalább 101.9×201.9mm
- Determinizmus: két egymást követő `inflate_part()` hívás azonos inputra azonos `Vec<Point64>`-et ad

---

## 🌍 Lokalizáció

Nem releváns.

---

## 📎 Kapcsolódások

**Backlog canvas (szülő dokumentum):**
- `canvases/nesting_engine/nesting_engine_backlog.md` — F1-1 task

**Mintafájlok a repóban (érdemes megnézni implementáció előtt):**
- `rust/vrs_solver/Cargo.toml` — dependency pinning minta
- `rust/vrs_solver/src/main.rs` — Rust CLI stdin/stdout JSON minta
- `scripts/check.sh` — cargo build lépés elhelyezése
- `.github/workflows/repo-gate.yml` — CI build minta

**Codex workflow:**
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`

**Következő task (F1-2):**
- `canvases/nesting_engine/nesting_engine_io_contract_v2.md`