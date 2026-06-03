# SGH-Q26 package — Single-sheet Sparrow validation test suite, revised

This package replaces the previous Q26 draft. Use this revised package instead.

It is not another porting task. It is a staged test-suite task for the native production `sparrow_cde` path, covering progressively harder **single-sheet** scenarios, now with a concrete LV8-derived real-DXF gate.

## Apply

Copy the package contents into the repository root:

```bash
cp -R canvases codex scripts README_SGH_Q26_SINGLE_SHEET_SPARROW_VALIDATION_SUITE_REVISED_PACKAGE.md /home/muszy/projects/VRS_nesting/
```

Then run the task with the runner prompt:

```text
codex/prompts/egyedi_solver/sgh_q26_single_sheet_sparrow_validation_suite/run.md
```

## Scope

The task must add:

- `rust/vrs_solver/tests/sparrow_single_sheet_validation.rs`
- optional fixtures under `rust/vrs_solver/tests/fixtures/sgh_q26_single_sheet_validation/`
- `rust/vrs_solver/tests/fixtures/sgh_q26_single_sheet_validation/lv8_derived_subset_manifest.json`
- `scripts/smoke_sgh_q26_single_sheet_validation_suite.py`
- `scripts/smoke_sgh_q26_lv8_derived_single_sheet_validation.py`
- Q26 report/checklist artifacts

## Required validation levels

- tiny/easy single-sheet solve;
- rotation-required one-sheet solve;
- irregular strict-CDE one-sheet solve;
- medium rectangle mix;
- medium mixed rotations;
- serious synthetic 40–80 instance one-sheet fixture;
- LV8-derived real-DXF 40–80 instance one-sheet validation from `samples/real_work_dxf/0014-01H/lv8jav`;
- deterministic same-seed proof;
- negative overcapacity proof;
- existing small real-DXF one-sheet smoke.

## Hard exclusions

- No compression.
- No first-sheet-191 / full-276 LV8 acceptance.
- No multisheet fixture gate.
- No benchmark tuning.
- No solver production refactor.
- No legacy core reintroduction.

## Mandatory gates

```bash
cargo build --manifest-path rust/vrs_solver/Cargo.toml --release
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
cargo test --manifest-path rust/vrs_solver/Cargo.toml --test sparrow_single_sheet_validation -- --nocapture
python3 scripts/smoke_sgh_q26_single_sheet_validation_suite.py
python3 scripts/smoke_sgh_q26_lv8_derived_single_sheet_validation.py
python3 scripts/smoke_real_dxf_sparrow_pipeline.py
./scripts/check.sh
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q26_single_sheet_sparrow_validation_suite.md
```
