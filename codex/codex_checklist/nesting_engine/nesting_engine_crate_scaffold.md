# Codex Checklist — nesting_engine_crate_scaffold

**Task slug:** `nesting_engine_crate_scaffold`
**Canvas:** `canvases/nesting_engine/nesting_engine_crate_scaffold.md`
**Goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_nesting_engine_crate_scaffold.yaml`

---

## Felderítés

- [x] `AGENTS.md` elolvasva
- [x] `docs/codex/overview.md` elolvasva
- [x] `docs/codex/yaml_schema.md` elolvasva
- [x] `docs/codex/report_standard.md` elolvasva
- [x] Meglévő `rust/vrs_solver/Cargo.toml` minta megvizsgálva (dependency pinning minta)
- [x] Meglévő `scripts/check.sh` cargo build lépés megkeresve
- [x] `.github/workflows/repo-gate.yml` CI build minta megvizsgálva

## Implementáció

- [x] `rust/nesting_engine/Cargo.toml` létrehozva, `i_overlay = "=4.4.0"` pinned dependency
  - Megjegyzés: `clipper2` crate C++ FFI-t használ → `i_overlay` pure Rust crate választva
- [x] `rust/nesting_engine/src/main.rs` CLI skeleton (`--version`, `--help`, exit 1 egyébként)
- [x] `rust/nesting_engine/src/geometry/mod.rs` — moduldeklarációk
- [x] `rust/nesting_engine/src/geometry/types.rs` — `Point64`, `Polygon64`, `PartGeometry`
- [x] `rust/nesting_engine/src/geometry/scale.rs` — `SCALE`, `TOUCH_TOL`, `mm_to_i64()`, `i64_to_mm()`
- [x] `rust/nesting_engine/src/geometry/offset.rs` — `inflate_part()`, `OffsetError`, winding-direction policy
- [x] `docs/nesting_engine/tolerance_policy.md` — scale policy + touching policy + kontúr-irány + simplify policy dokumentálva
- [x] `scripts/check.sh` — új crate build hozzáadva, vrs_solver build érintetlen
- [x] `.github/workflows/repo-gate.yml` — új crate CI build bekötve

## Tesztek

- [x] `cargo test --manifest-path rust/nesting_engine/Cargo.toml` PASS (4/4 teszt)
  - `scale_round_trip` ✓
  - `inflate_outer_100x200_1mm` ✓
  - `deflate_hole_50x50_1mm` ✓
  - `inflate_part_determinism` ✓
- [x] `cargo build --release --manifest-path rust/nesting_engine/Cargo.toml` PASS
- [x] `cargo build --release --manifest-path rust/vrs_solver/Cargo.toml` PASS (regresszió: nem tört el)

## Gate

- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_crate_scaffold.md` PASS
