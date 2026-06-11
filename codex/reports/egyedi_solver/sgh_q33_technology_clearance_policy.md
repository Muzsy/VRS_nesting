# SGH-Q33 Report

## Scope

SGH-Q33 introduces a central Rust-side `TechnologyClearancePolicy` module that bridges the
existing repo-level technology fields (`kerf_mm`, `spacing_mm`, `margin_mm`) into the Rust
solver layer. This is a **foundational, diagnostic-only** task: Q33 centralises and validates
the policy but does **not** apply polygon offsets or modify solver collision / spacing behaviour.

## Existing repo audit

### What already existed

| Layer | Fields present |
|---|---|
| DB (`supabase/migrations/20260310230000_h0_e2_t3_technology_domain_alapok.sql`) | `kerf_mm`, `spacing_mm`, `margin_mm` |
| API routes (`api/routes/run_configs.py`) | `kerf_mm`, `spacing_mm`, `margin_mm` |
| Snapshot builder (`api/services/run_snapshot_builder.py`) | `kerf_mm`, `spacing_mm`, `margin_mm` |
| Worker adapter (`worker/engine_adapter_input.py`) | `kerf_mm`, `spacing_mm`, `margin_mm` |
| Rust `SolverInput` (pre-Q33) | `margin_mm: Option<f64>` only |
| Rust multisheet pipeline (pre-Q33) | No centralised clearance handling |

Backend / API / snapshot already had `kerf_mm`, `spacing_mm`, `margin_mm`.
Rust `SolverInput` previously only had `margin_mm`.
Q33 does not duplicate the backend technology model.

## New Rust policy module

**`rust/vrs_solver/src/technology/clearance.rs`**

```rust
pub struct TechnologyClearancePolicy {
    pub margin_mm: f64,
    pub spacing_mm: f64,
    pub kerf_mm: f64,
    pub validation_tolerance_mm: f64,
}
```

Methods:
- `from_solver_input(input: &SolverInput) -> Result<Self, String>` — builds from input with defaults; validates.
- `effective_sheet_margin_mm(&self) -> f64`
- `effective_part_spacing_mm(&self) -> f64`
- `effective_kerf_mm(&self) -> f64`
- `validate(&self) -> Result<(), String>` — returns `Err` on any negative value.

Default rules:
```
margin_mm  = input.margin_mm.unwrap_or(0.0)
spacing_mm = input.spacing_mm.unwrap_or(margin_mm)
kerf_mm    = input.kerf_mm.unwrap_or(0.0)
validation_tolerance_mm = 1e-6
```

**`rust/vrs_solver/src/technology/mod.rs`** — re-exports `TechnologyClearancePolicy`.

**`rust/vrs_solver/src/lib.rs`** — added `pub mod technology`.

## Input compatibility

`SolverInput` extended backwards-compatibly:

```rust
#[serde(default)]
pub spacing_mm: Option<f64>,   // NEW — defaults to margin_mm when absent

#[serde(default)]
pub kerf_mm: Option<f64>,      // NEW — defaults to 0.0 when absent
```

`margin_mm: Option<f64>` unchanged. All Q32 and earlier inputs continue to deserialise
without modification. The `#[serde(default)]` annotation means missing JSON keys produce `None`.

Fields intentionally **not** added (spec-forbidden): `part_spacing_mm`, `sheet_margin_mm`.

### UNSUPPORTED_MARGIN_MM_RUNTIME guard update

The pre-existing `UNSUPPORTED_MARGIN_MM_RUNTIME` guard (which rejected non-zero `margin_mm`
for the Phase 1 profile) now has a Q33 carve-out: it is skipped for the
`sparrow_cde_multisheet` pipeline, which has centralised policy handling. All other pipelines
retain the original behaviour.

## Diagnostics integration

`OptimizerDiagnosticsOutput` extended with 7 optional fields:

```rust
pub technology_policy_active: Option<bool>,
pub technology_margin_mm: Option<f64>,
pub technology_spacing_mm: Option<f64>,
pub technology_kerf_mm: Option<f64>,
pub technology_effective_sheet_margin_mm: Option<f64>,
pub technology_effective_part_spacing_mm: Option<f64>,
pub technology_effective_kerf_mm: Option<f64>,
```

All are `#[serde(skip_serializing_if = "Option::is_none")]`.

**`adapter.rs`** changes:
1. `TechnologyClearancePolicy` imported from `crate::technology`.
2. Policy created at the start of `solve()`: `let technology_policy = TechnologyClearancePolicy::from_solver_input(&input)?;`
3. Policy passed to `run_sparrow_finite_stock_multisheet_pipeline(&input, ..., &technology_policy)`.
4. All 7 diagnostic fields populated in the `sparrow_cde_multisheet` diagnostics output.
5. Other `OptimizerDiagnosticsOutput` struct literals (single-sheet Sparrow, Phase 1 full solver) have all 7 fields set to `None`.

## Mini smoke run

Input: `artifacts/benchmarks/sgh_q33/inputs/technology_policy_smoke.json`
Output: `artifacts/benchmarks/sgh_q33/outputs/technology_policy_smoke_output.json`

Acceptance result:

| Check | Result |
|---|---|
| `status == ok` | PASS |
| `technology_policy_active == true` | PASS |
| `technology_margin_mm == 10.0` | PASS |
| `technology_spacing_mm == 2.0` | PASS |
| `technology_kerf_mm == 0.15` | PASS |
| `technology_effective_sheet_margin_mm == 10.0` | PASS |
| `technology_effective_part_spacing_mm == 2.0` | PASS |
| `technology_effective_kerf_mm == 0.15` | PASS |
| `final_pairs == 0` | PASS |
| `boundary_violations == 0` | PASS |

## Tests

File: `rust/vrs_solver/tests/technology_clearance_policy.rs` — 9 integration tests.

| Test | Description |
|---|---|
| `legacy_margin_only_defaults` | `spacing_mm` defaults to `margin_mm`; `kerf_mm` defaults to 0 |
| `legacy_no_fields_gives_zero_defaults` | All three fields absent → all 0.0 |
| `explicit_fields_parsed_correctly` | Explicit `margin_mm`, `spacing_mm`, `kerf_mm` read correctly |
| `zero_values_are_valid` | Zero values pass `validate()` |
| `negative_margin_mm_errors` | `margin_mm < 0` → `Err` mentioning `margin_mm` |
| `negative_spacing_mm_errors` | `spacing_mm < 0` → `Err` mentioning `spacing_mm` |
| `negative_kerf_mm_errors` | `kerf_mm < 0` → `Err` mentioning `kerf_mm` |
| `sparrow_cde_multisheet_diagnostics_contain_technology_fields` | Full solve: all 7 `technology_*` diagnostic fields present and correct |
| `q32_input_without_spacing_kerf_deserializes_and_runs` | Q32-style input (no `spacing_mm`/`kerf_mm`) runs correctly; defaults apply |

All 9 tests PASS.

## Gate results

```
cargo build --release   PASS  (warnings only, no errors)
cargo test --lib        PASS  455/455
cargo test --test technology_clearance_policy  PASS  9/9
python3 scripts/smoke_sgh_q33_technology_clearance_policy.py  PASS  43/43
./scripts/check.sh      PASS  [DONE] smoketest OK
./scripts/verify.sh     PASS
```

## Non-goals

- No polygon offset.
- No kerf-expanded geometry.
- No cavity prepack.
- No solver search tuning.
- No Sparrow collision/spacing behaviour change.
- No new `part_spacing_mm` or `sheet_margin_mm` fields.
- No legacy multisheet manager usage.
- No compression wired via technology module.

Q33 does not yet apply polygon offset / spacing-expanded geometry.
Q33 only centralizes, validates, and reports the technology clearance policy.

## Final verdict

**PASS.** All acceptance criteria met:

- Central `TechnologyClearancePolicy` Rust module created.
- Builds on existing repo field names: `margin_mm` / `spacing_mm` / `kerf_mm`.
- No duplicated `part_spacing_mm` / `sheet_margin_mm` fields.
- `SolverInput` backwards-compatible (existing Q32 inputs unchanged).
- Negative technology values rejected with descriptive error messages.
- `sparrow_cde_multisheet` diagnostics contain all `technology_*` fields.
- Mini synthetic run confirms field propagation end-to-end.
- Q31 base-shape cache and Q32 multisheet pipeline unaffected.
- No compression / legacy regression.
- All build / test / smoke / check / verify gates PASS.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-06-11T06:02:14+02:00 → 2026-06-11T06:04:37+02:00 (143s)
- parancs: `./scripts/check.sh`
- log: `/mnt/workspace/VRS_nesting/codex/reports/egyedi_solver/sgh_q33_technology_clearance_policy.verify.log`
- git: `main@322c907`
- módosított fájlok (git status): 10

**git diff --stat**

```text
 .claude/settings.local.json    |  8 +++++++-
 rust/vrs_solver/src/adapter.rs | 44 +++++++++++++++++++++++++++++++++++++++---
 rust/vrs_solver/src/io.rs      | 24 +++++++++++++++++++++++
 rust/vrs_solver/src/lib.rs     |  1 +
 4 files changed, 73 insertions(+), 4 deletions(-)
```

**git status --porcelain (preview)**

```text
 M .claude/settings.local.json
 M rust/vrs_solver/src/adapter.rs
 M rust/vrs_solver/src/io.rs
 M rust/vrs_solver/src/lib.rs
?? artifacts/benchmarks/sgh_q33/
?? codex/reports/egyedi_solver/sgh_q33_technology_clearance_policy.md
?? codex/reports/egyedi_solver/sgh_q33_technology_clearance_policy.verify.log
?? rust/vrs_solver/src/technology/
?? rust/vrs_solver/tests/technology_clearance_policy.rs
?? scripts/smoke_sgh_q33_technology_clearance_policy.py
```

<!-- AUTO_VERIFY_END -->
