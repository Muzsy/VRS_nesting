# Report — lv8_density_t09_phase1_shape_id_cache_key_verification

**Státusz:** PASS

A T09 cache-key invariáns verifikáció elkészült dedikált integration tesztekkel. Minden kötelező invariáns zöld, ezért production cache-key módosítás nem történt.

## 1) Meta

- **Task slug:** `lv8_density_t09_phase1_shape_id_cache_key_verification`
- **Kapcsolódó canvas:** `canvases/nesting_engine/lv8_density_t09_phase1_shape_id_cache_key_verification.md`
- **Kapcsolódó goal YAML:** `codex/goals/canvases/nesting_engine/fill_canvas_lv8_density_t09_phase1_shape_id_cache_key_verification.yaml`
- **Futás dátuma:** 2026-05-17
- **Fókusz terület:** Cache-key invariants

## 2) Előfeltétel

- `codex/reports/nesting_engine/lv8_density_t07_phase1_0_cache_path_discovery_spike.md` → `PASS_WITH_NOTES`
- `codex/reports/nesting_engine/lv8_density_t08_phase1_cache_stats_hardening.md` → `PASS`

## 3) Változások

- Új fájl: `rust/nesting_engine/tests/nfp_cache_key_invariants.rs`
- Task artefaktok:
  - `codex/codex_checklist/nesting_engine/lv8_density_t09_phase1_shape_id_cache_key_verification.md`
  - `codex/reports/nesting_engine/lv8_density_t09_phase1_shape_id_cache_key_verification.md`
  - `codex/reports/nesting_engine/lv8_density_t09_phase1_shape_id_cache_key_verification.verify.log`

## 4) Cache-key decision matrix

| Invariant | Result | Evidence | Decision impact |
|---|---|---|---|
| `shape_id_changes_when_polygon_coordinates_change` | PASS | `rust/nesting_engine/tests/nfp_cache_key_invariants.rs` | Geometry/spacing-like koordinátaváltozás hash-szinten szeparált. |
| `shape_id_stable_for_equivalent_polygon_boundary_external` | PASS | `rust/nesting_engine/tests/nfp_cache_key_invariants.rs` | Equivalent boundary nem okoz alias hibát. |
| `shape_id_includes_holes` | PASS | `rust/nesting_engine/tests/nfp_cache_key_invariants.rs` | Hole tartalom része a shape hashnek. |
| `shape_id_is_stable_for_equivalent_holes` | PASS | `rust/nesting_engine/tests/nfp_cache_key_invariants.rs` | Equivalent hole reprezentáció stabil hash-t ad. |
| `cache_key_separates_nfp_kernel` | PASS | `rust/nesting_engine/tests/nfp_cache_key_invariants.rs` | Kernel-enként külön cache-key biztosított. |
| `cache_key_separates_rotation_steps` | PASS | `rust/nesting_engine/tests/nfp_cache_key_invariants.rs` | Rotációs index szeparáció működik. |
| `cache_key_is_order_sensitive_external` | PASS | `rust/nesting_engine/tests/nfp_cache_key_invariants.rs` | A/B irány külön kulcsot ad. |

pipeline_version_required: NO
reason: Az összes kötelező invariáns zöld, aliasolási bug nem reprodukálható a shape-hash + kernel + rotation + order-sensitive kulcsmodellben.

## 5) Verifikáció

- `cargo check -p nesting_engine` → PASS
- `cargo test -p nesting_engine --test nfp_cache_key_invariants -- --nocapture` → PASS (7 passed)
- `cargo test -p nesting_engine nfp::cache -- --nocapture` → PASS

## 6) Production-code-change check

- `production_cache_key_changed: false`
- `rust/nesting_engine/src/nfp/cache.rs` és `rust/nesting_engine/src/placement/nfp_placer.rs` nem módosult T09 scope-ban.


<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-05-17T02:09:13+02:00 → 2026-05-17T02:12:00+02:00 (167s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/nesting_engine/lv8_density_t09_phase1_shape_id_cache_key_verification.verify.log`
- git: `main@c0447aa`
- módosított fájlok (git status): 7

**git status --porcelain (preview)**

```text
?? canvases/nesting_engine/lv8_density_t09_phase1_shape_id_cache_key_verification.md
?? codex/codex_checklist/nesting_engine/lv8_density_t09_phase1_shape_id_cache_key_verification.md
?? codex/goals/canvases/nesting_engine/fill_canvas_lv8_density_t09_phase1_shape_id_cache_key_verification.yaml
?? codex/prompts/nesting_engine/lv8_density_t09_phase1_shape_id_cache_key_verification/
?? codex/reports/nesting_engine/lv8_density_t09_phase1_shape_id_cache_key_verification.md
?? codex/reports/nesting_engine/lv8_density_t09_phase1_shape_id_cache_key_verification.verify.log
?? rust/nesting_engine/tests/nfp_cache_key_invariants.rs
```

<!-- AUTO_VERIFY_END -->
