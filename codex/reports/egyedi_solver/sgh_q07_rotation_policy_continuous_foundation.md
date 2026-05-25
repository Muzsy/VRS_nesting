PASS

# Report — SGH-Q07 `sgh_q07_rotation_policy_continuous_foundation`

## Status

PASS — Moduláris `RotationPolicy` réteg bevezetve. `RotationPolicyKind` (6 variant) + `candidate_angles` + determinisztikus `ContinuousRng`. `Placement.rotation_deg` migrálva `i64` → `f64`. Általános szögű bbox matematika. Legacy `allowed_rotations_deg` backward compat megőrizve. Minden pre-Q07 teszt (192) zöld. Új SGH-Q07 tesztek (19): mind zöld. `cargo test --lib`: 211/211 PASS.

## Meta

- **Task slug:** `sgh_q07_rotation_policy_continuous_foundation`
- **Kapcsolódó canvas:** `canvases/egyedi_solver/sgh_q07_rotation_policy_continuous_foundation.md`
- **Kapcsolódó goal YAML:** `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q07_rotation_policy_continuous_foundation.yaml`
- **Futás dátuma:** 2026-05-25
- **Branch / commit:** `main`
- **Fókusz terület:** `rust/vrs_solver/src/rotation_policy.rs`, `io.rs`, `item.rs`, `optimizer/`

---

## Dependency evidence

| Gate | Státusz | Bizonyíték |
|------|---------|------------|
| SGH-Q06 report első sor PASS | PASS | `codex/reports/egyedi_solver/sgh_q06_loss_model_smooth_collision_severity.md` sor 1: PASS |
| SGH-Q07_STATUS: READY marker | PASS | `codex/reports/egyedi_solver/sgh_q06_loss_model_smooth_collision_severity.md`: `SGH-Q07_STATUS: READY` |
| Q06 fájlok nem módosítva | PASS | Nincs érintett fájl |

---

## Sparrow source audit evidence

Ténylegesen olvasott fájlok:

| Fájl | Struct / függvény | Auditált tartalom |
|------|-------------------|-------------------|
| `.cache/sparrow/src/sample/uniform_sampler.rs` | `ROT_N_SAMPLES`, `sample_rotation()` | Continuous rotation: 16 uniform sample, seed-based |
| `jagua-rs-0.6.4/src/geo_enums.rs` | `RotationRange::None/Continuous/Discrete` | jagua-rs rotation policy enum |
| `.cache/sparrow/src/search/coord_descent.rs` | `CDAxis::Wiggle` | Coordinate descent rotation wiggle |

**jagua-rs RotationRange (auditált):**
```rust
pub enum RotationRange {
    None,
    Continuous,
    Discrete(Vec<f64>),
}
```

**Sparrow uniform_sampler (auditált):**
```rust
const ROT_N_SAMPLES: usize = 16;
fn sample_rotation(seed: u64, i: usize) -> f64 { ... }
```

**VRS ContinuousRng adaptáció (rotation_policy.rs):**
```rust
struct ContinuousRng(u64);
impl ContinuousRng {
    fn next_angle(&mut self) -> f64 {
        self.0 ^= self.0 << 13; self.0 ^= self.0 >> 7; self.0 ^= self.0 << 17;
        let frac = (self.0.wrapping_mul(6364136223846793005)) as f64 / u64::MAX as f64;
        frac * 360.0
    }
}
```

---

## Changed files / functions matrix

| Fájl | Változás típusa | Érintett függvények/struktúrák |
|------|-----------------|-------------------------------|
| `rust/vrs_solver/src/rotation_policy.rs` | ÚJ | `RotationPolicyKind`, `candidate_angles`, `ContinuousRng`, `normalize_angle`, `dedup_angles`, `dims_for_rotation_f64`, `rotated_bbox_min_offset_f64`, `placement_anchor_from_rect_min_f64` |
| `rust/vrs_solver/src/lib.rs` | MÓDOSÍTOTT | `pub mod rotation_policy` hozzáadva |
| `rust/vrs_solver/src/io.rs` | MÓDOSÍTOTT | `Placement.rotation_deg: f64`, `serialize_rotation_deg`, `SolverInput.rotation_policy` |
| `rust/vrs_solver/src/item.rs` | MÓDOSÍTOTT | `Part.rotation_policy`, `Instance.allowed_rotations_deg: Vec<f64>`, `resolve_part_rotation_angles`, `dims_for_rotation` (infallible f64), `rotated_bbox_min_offset`, `placement_anchor_from_rect_min` |
| `rust/vrs_solver/src/optimizer/mod.rs` | MÓDOSÍTOTT | `try_place_on_sheet` f64 rotations |
| `rust/vrs_solver/src/optimizer/initializer.rs` | MÓDOSÍTOTT | `resolve_part_rotation_angles`, infallible rotation math |
| `rust/vrs_solver/src/optimizer/separator.rs` | MÓDOSÍTOTT | `find_best_candidate_for_target` f64, `rotation_deg.to_bits()` ordering |
| `rust/vrs_solver/src/optimizer/compress.rs` | MÓDOSÍTOTT | `resolve_part_rotation_angles`, f64 epsilon comparison |
| `rust/vrs_solver/src/optimizer/moves.rs` | MÓDOSÍTOTT | `CandidateMove::Rotate { new_rotation_deg: f64 }`, epsilon-based contains, `seed_at_origin`, `lbf_clear_on_sheet`, `try_reinsert`, `try_transfer` |
| `rust/vrs_solver/src/optimizer/repair.rs` | MÓDOSÍTOTT | `RepairItem.allowed_rotations: Vec<f64>`, `resolve_part_dims` |
| `rust/vrs_solver/src/optimizer/sheet_elimination.rs` | MÓDOSÍTOTT | `resolve_dims`, `lbf_select_clear_reinsert`, `try_separator_fallback_for_item` f64 |

---

## RotationPolicy contract evidence

| Contract pont | Státusz | Bizonyíték |
|---------------|---------|------------|
| `RotationPolicyKind` enum 6 variant | PASS | `rotation_policy.rs:RotationPolicyKind` |
| Locked → [0.0] | PASS | `rotation_policy_locked_generates_only_zero` |
| HalfTurn → [0.0, 180.0] | PASS | `rotation_policy_half_turn_generates_0_180` |
| Orthogonal → [0.0, 90.0, 180.0, 270.0] | PASS | `rotation_policy_orthogonal_matches_legacy_0_90_180_270` |
| FortyFive → 8 szög | PASS | `rotation_policy_forty_five_generates_8_angles` |
| Legacy `allowed_rotations_deg` backward compat | PASS | `legacy_allowed_rotations_deg_still_supported` |
| Part policy > global policy | PASS | `part_policy_overrides_global_policy` |
| Global policy fallback | PASS | `global_policy_used_when_part_has_no_explicit_policy` |
| 45° bbox math helyes | PASS | `arbitrary_45_degree_bbox_math_is_correct` (100×20 @ 45° → ≈84.85×84.85) |
| Continuous non-orthogonal szögek | PASS | `continuous_policy_generates_non_orthogonal_angles` |
| Continuous determinizmus | PASS | `continuous_policy_same_seed_is_deterministic` (to_bits) |
| 45°/continuous fér be ahol orthogonal nem | PASS | `continuous_rotation_can_fit_rectangle_that_orthogonal_cannot` (100×20 part, 90×90 sheet) |
| Separator policy-aware | PASS | `separator_uses_rotation_policy_not_hardcoded_orthogonal` |
| Compress policy-aware | PASS | `compression_uses_rotation_policy_not_hardcoded_orthogonal` |
| JSON integer szögek `.0` nélkül | PASS | `serialize_rotation_deg` custom serializer |
| f64 ordering (to_bits) | PASS | `separator.rs: rotation_deg.to_bits().cmp()` |
| Epsilon-based f64 contains | PASS | `moves.rs: rots.iter().any(|&r| (r - rot_norm).abs() < 1e-6)` |

---

## DoD → Evidence matrix

| DoD pont | Státusz | Bizonyíték |
|----------|---------|------------|
| Sparrow source audit megtörtént, valós pathokkal | PASS | `uniform_sampler.rs` + `geo_enums.rs` + `coord_descent.rs` auditálva |
| `RotationPolicyKind` enum 6 varianttal | PASS | `rotation_policy.rs` |
| `candidate_angles` determinisztikus | PASS | `continuous_policy_same_seed_is_deterministic` |
| `Placement.rotation_deg` f64-re migrálva | PASS | `io.rs` |
| JSON backward compat (integer szögek) | PASS | `serialize_rotation_deg` |
| Általános szögű bbox math | PASS | `dims_for_rotation_f64`, `rotated_bbox_min_offset_f64` |
| Policy resolution precedence | PASS | `resolve_part_rotation_angles` |
| 45°/continuous fér be ahol orthogonal nem | PASS | fit fixture teszt (100×20 part, 90×90 sheet) |
| Célzott Rust tesztek zöldek (13 kötelező + 2 extra) | PASS | 15/15 `rotation_policy` |
| `cargo test --lib` zöld | PASS | 211/211 |
| `./scripts/verify.sh --report ...` zöld | PASS | AUTO_VERIFY szekció |

---

## Tests added / fixed

### Új tesztek — `rotation_policy.rs` (15 db)

| Teszt | Viselkedés |
|-------|-----------|
| `rotation_policy_locked_generates_only_zero` | Locked → [0.0] |
| `rotation_policy_half_turn_generates_0_180` | HalfTurn → [0.0, 180.0] |
| `rotation_policy_orthogonal_matches_legacy_0_90_180_270` | Orthogonal = legacy 4 szög |
| `rotation_policy_forty_five_generates_8_angles` | FortyFive → 8 szög |
| `legacy_allowed_rotations_deg_still_supported` | Part.allowed_rotations_deg backward compat |
| `part_policy_overrides_global_policy` | Part-szintű policy > global policy |
| `global_policy_used_when_part_has_no_explicit_policy` | Global policy fallback |
| `arbitrary_45_degree_bbox_math_is_correct` | 100×20 @ 45° → bbox ≈ 84.85×84.85 |
| `continuous_policy_generates_non_orthogonal_angles` | Legalább 1 non-canonical szög |
| `continuous_policy_same_seed_is_deterministic` | to_bits bit-identikus |
| `continuous_rotation_can_fit_rectangle_that_orthogonal_cannot` | 100×20 fér 90×90-be 45°-on |
| `separator_uses_rotation_policy_not_hardcoded_orthogonal` | Separator policy-aware |
| `compression_uses_rotation_policy_not_hardcoded_orthogonal` | Compress policy-aware |
| `rotated_bbox_min_offset_canonical_angles_correct` | Min offset kanonikus szögeknél |
| `placement_anchor_keeps_bbox_inside_rect` | Inverz transform konzisztens |

### Meglévő tesztek — változatlanul zöld (192 db)

Összes pre-Q07 teszt változatlanul PASS.

---

## Default no-downgrade evidence

```text
RotationPolicyKind::default() → Orthogonal

allowed_rotations_deg: [0, 90] → resolve_part_rotation_angles → [0.0, 90.0]
  (Discrete policy, backward compat)

JSON output: rotation_deg: 90.0 → serialized as 90 (not 90.0)
  serialize_rotation_deg custom serializer

All 192 pre-Q07 tests: PASS ✓
```

---

## Verify commands and results

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml rotation_policy
# Result: 15/15 PASS

cargo test --manifest-path rust/vrs_solver/Cargo.toml item
# Result: 21/21 PASS

cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::initializer
# Result: 15/15 PASS

cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::separator
# Result: 28/28 PASS

cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::compress
# Result: 4/4 PASS

cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::moves
# Result: 19/19 PASS

cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::sheet_elimination
# Result: 11/11 PASS

cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
# Result: 211/211 PASS

./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q07_rotation_policy_continuous_foundation.md
# Result: lásd AUTO_VERIFY szekció
```

---

SGH-Q08_STATUS: READY

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-05-25T21:16:27+02:00 → 2026-05-25T21:19:30+02:00 (183s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/sgh_q07_rotation_policy_continuous_foundation.verify.log`
- git: `main@d0dd47f`
- módosított fájlok (git status): 24

**git diff --stat**

```text
 rust/vrs_solver/src/io.rs                          |  25 +-
 rust/vrs_solver/src/item.rs                        | 377 +++++++++++++--------
 rust/vrs_solver/src/lib.rs                         |   1 +
 rust/vrs_solver/src/optimizer/bpp_phase.rs         |  19 +-
 rust/vrs_solver/src/optimizer/compress.rs          |  30 +-
 rust/vrs_solver/src/optimizer/explore.rs           |  20 +-
 rust/vrs_solver/src/optimizer/initializer.rs       |  70 ++--
 rust/vrs_solver/src/optimizer/mod.rs               |  15 +-
 rust/vrs_solver/src/optimizer/moves.rs             |  77 ++---
 rust/vrs_solver/src/optimizer/multisheet.rs        |   3 +-
 rust/vrs_solver/src/optimizer/phase.rs             |  20 +-
 rust/vrs_solver/src/optimizer/repair.rs            |  19 +-
 rust/vrs_solver/src/optimizer/score.rs             |   8 +-
 rust/vrs_solver/src/optimizer/separator.rs         |  24 +-
 rust/vrs_solver/src/optimizer/sheet_elimination.rs |  56 ++-
 rust/vrs_solver/src/optimizer/working.rs           |  11 +-
 16 files changed, 422 insertions(+), 353 deletions(-)
```

**git status --porcelain (preview)**

```text
 M rust/vrs_solver/src/io.rs
 M rust/vrs_solver/src/item.rs
 M rust/vrs_solver/src/lib.rs
 M rust/vrs_solver/src/optimizer/bpp_phase.rs
 M rust/vrs_solver/src/optimizer/compress.rs
 M rust/vrs_solver/src/optimizer/explore.rs
 M rust/vrs_solver/src/optimizer/initializer.rs
 M rust/vrs_solver/src/optimizer/mod.rs
 M rust/vrs_solver/src/optimizer/moves.rs
 M rust/vrs_solver/src/optimizer/multisheet.rs
 M rust/vrs_solver/src/optimizer/phase.rs
 M rust/vrs_solver/src/optimizer/repair.rs
 M rust/vrs_solver/src/optimizer/score.rs
 M rust/vrs_solver/src/optimizer/separator.rs
 M rust/vrs_solver/src/optimizer/sheet_elimination.rs
 M rust/vrs_solver/src/optimizer/working.rs
?? canvases/egyedi_solver/sgh_q07_rotation_policy_continuous_foundation.md
?? codex/codex_checklist/egyedi_solver/sgh_q07_rotation_policy_continuous_foundation.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q07_rotation_policy_continuous_foundation.yaml
?? codex/prompts/egyedi_solver/sgh_q07_rotation_policy_continuous_foundation/
?? codex/reports/egyedi_solver/sgh_q07_rotation_policy_continuous_foundation.md
?? codex/reports/egyedi_solver/sgh_q07_rotation_policy_continuous_foundation.verify.log
?? docs/egyedi_solver/sgh_q07_rotation_policy_contract.md
?? rust/vrs_solver/src/rotation_policy.rs
```

<!-- AUTO_VERIFY_END -->
