# Contract — SGH-Q07 RotationPolicy + Continuous Rotation Foundation

## Scope

Moduláris `RotationPolicy` réteg a VRS rectangular nesting solverben.
- `RotationPolicyKind` enum 6 varianttal
- `Placement.rotation_deg`: `i64` → `f64` migráció
- Általános szögű bbox matematika (tetszőleges θ)
- Policy-alapú szöggenerálás minden optimizer call site-on
- Legacy backward compat megőrzve

---

## RotationPolicyKind enum

```rust
pub enum RotationPolicyKind {
    Locked,              // csak 0°
    HalfTurn,            // 0°, 180°
    Orthogonal,          // 0°, 90°, 180°, 270° — DEFAULT
    FortyFive,           // 0°, 45°, 90°, 135°, 180°, 225°, 270°, 315°
    Discrete(Vec<f64>),  // explicit lista (arbitrary szögek)
    Continuous,          // seedelt, determinisztikus mintavételezés
}
```

Default: `Orthogonal` (backward compat).

---

## candidate_angles contract

```rust
pub fn candidate_angles(kind: &RotationPolicyKind, seed: u64, sample_count: usize) -> Vec<AngleDeg>
```

- `Locked` → `[0.0]`
- `HalfTurn` → `[0.0, 180.0]`
- `Orthogonal` → `[0.0, 90.0, 180.0, 270.0]`
- `FortyFive` → `[0.0, 45.0, 90.0, 135.0, 180.0, 225.0, 270.0, 315.0]`
- `Discrete(v)` → normalizált, dedup-olt `v`
- `Continuous` → `sample_count` db seedelt pseudo-random szög (xorshift64), mindig tartalmazza a 4 kanonikus szöget

Minden output normalizált [0, 360) ra és dedup-olt.

---

## Policy resolution precedence

```
resolve_part_rotation_angles(part, global_policy, seed, sample_count)
  1. part.rotation_policy (Part-szintű override — legerősebb)
  2. part.allowed_rotations_deg (legacy discrete, ha nem üres)
  3. global_policy (SolverInput.rotation_policy — gyengébb)
  4. Orthogonal (default fallback)
```

---

## Rotation math contract

### dims_for_rotation (általános szög)

```rust
pub fn dims_for_rotation(w: f64, h: f64, rot_deg: f64) -> (f64, f64)
```

`bbox_w = |w·cos(θ)| + |h·sin(θ)|`, `bbox_h = |w·sin(θ)| + |h·cos(θ)|`.

Kanonikus szögeknél (0/90/180/270) egész-pontos eredményt ad.

### rotated_bbox_min_offset

```rust
pub fn rotated_bbox_min_offset(w: f64, h: f64, rot_deg: f64) -> (f64, f64)
```

A forgatott téglalap 4 sarkából számított min_x, min_y eltolás.
CCW rotation, matematikai konvenció.

### placement_anchor_from_rect_min

```rust
pub fn placement_anchor_from_rect_min(rx: f64, ry: f64, w: f64, h: f64, rot_deg: f64) -> (f64, f64)
```

Inverz: bbox bal-alsó sarokból → placement anchor (eredetileg jobb-felső-sarok, CCW rotált).

---

## Placement.rotation_deg: f64 migráció

- `io::Placement.rotation_deg`: `i64` → `f64`
- JSON serializáció: egész szögek (pl. 90.0) → `90` (nem `90.0`) a `serialize_rotation_deg` custom serializer révén
- `PlacementTransform.rotation_deg` (`state.rs`): megmaradt `i64` (Q07 hatókörén kívül)

---

## Continuous policy determinizmus

`ContinuousRng(seed: u64)` — xorshift64 × konstans szorzó. Ugyanazon seed → bit-identikus output.
`sample_count` db szög, mindig kiegészítve a 4 kanonikus szöggel (0/90/180/270).

---

## Backward compatibility

| Scenario | Viselkedés |
|----------|-----------|
| `allowed_rotations_deg: [0, 90]` | Discrete [0.0, 90.0] — pontosan mint Q06 előtt |
| `allowed_rotations_deg: [0, 90, 180, 270]` | Discrete [0.0, 90.0, 180.0, 270.0] |
| `rotation_policy` hiányzik, `allowed_rotations_deg` üres | Orthogonal (0/90/180/270) |
| JSON output integer szögek | `90` nem `90.0` |

---

## Érintett fájlok

| Fájl | Változás |
|------|---------|
| `rust/vrs_solver/src/rotation_policy.rs` | ÚJ — teljes RotationPolicy modul |
| `rust/vrs_solver/src/lib.rs` | `pub mod rotation_policy` export |
| `rust/vrs_solver/src/io.rs` | `Placement.rotation_deg: f64`, `SolverInput.rotation_policy`, custom serializer |
| `rust/vrs_solver/src/item.rs` | `Part.rotation_policy`, `Instance.allowed_rotations_deg: Vec<f64>`, f64 rotation math |
| `rust/vrs_solver/src/optimizer/mod.rs` | `try_place_on_sheet` f64 |
| `rust/vrs_solver/src/optimizer/initializer.rs` | `resolve_part_rotation_angles`, f64 rotations |
| `rust/vrs_solver/src/optimizer/separator.rs` | `resolve_part_rotation_angles`, f64 |
| `rust/vrs_solver/src/optimizer/compress.rs` | `resolve_part_rotation_angles`, f64 |
| `rust/vrs_solver/src/optimizer/moves.rs` | `CandidateMove::Rotate` f64, epsilon comparisons |
| `rust/vrs_solver/src/optimizer/repair.rs` | `RepairItem.allowed_rotations: Vec<f64>` |
| `rust/vrs_solver/src/optimizer/sheet_elimination.rs` | f64 rotations |
