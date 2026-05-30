# Checklist — SGH-Q24 Sparrow parity quality hardening

## Hard PASS gates

- [ ] Report starts with exactly `PASS` or `REVISE`.
- [ ] Production Phase1 default remains `sparrow_cde`.
- [ ] Production `sparrow_cde` forces CDE backend.
- [ ] Production search budget is non-trivial: grid > 1, focused samples > 0, coordinate descent > 0/top-k > 1, unless a fixture-specific smoke budget explicitly overrides it and is not production default.
- [ ] Search diagnostics prove non-trivial candidate generation/evaluation on medium and LV8 hard rows.
- [ ] Exploration pool implemented and active: inserts/restores/disruptions counted.
- [ ] Compression loop implemented as restore -> compact/shrink objective -> separate -> accept/reject, not only one left/down local move.
- [ ] Production `sparrow_cde` loss model is not `bbox_area` as primary loss.
- [ ] `loss_bbox_proxy_used_as_primary == false` for production `sparrow_cde` rows.
- [ ] Existing medium fixture remains `ok`, `12/12`, final pairs `0`, boundary violations `0`.
- [ ] `lv8_12types_x1` is `ok`, `12/12`, final pairs `0`, boundary violations `0`.
- [ ] `lv8_24_instances` is `ok`, `24/24`, final pairs `0`, boundary violations `0`.
- [ ] No bbox/LBF/legacy fallback in any production `sparrow_cde` hard-gate row.
- [ ] `lv8_50_instances` benchmark row is measured or explicitly accounted as skipped with reason.
- [ ] `lv8_100_instances` benchmark row is measured or explicitly accounted as skipped with reason.
- [ ] `lv8_full_276` benchmark row is measured or explicitly accounted as skipped with reason.
- [ ] Benchmark denominator includes failed/partial/unsupported/timeout rows; no cherry-picking.
- [ ] Smoke script fails on any hard-gate regression.
- [ ] Benchmark writes JSON and Markdown measurement reports.
- [ ] `cargo build --release`, `cargo test --lib`, smoke, quick bench, and `./scripts/check.sh` executed, or exact non-PASS limitation documented.

## Reject conditions

- [ ] Report-only or benchmark-only work.
- [ ] Production search remains effectively Q23R3 weak config.
- [ ] Medium hard gate regresses.
- [ ] LV8 12-types-x1 or 24-instance hard rows fail.
- [ ] Production loss still reports `bbox_area` as primary model.
- [ ] Compression remains only primitive local step without separation/rollback lifecycle.
- [ ] Exploration remains one restart without pool/restore/disruption policy.
- [ ] Hidden fallback to bbox/LBF/legacy occurs.
- [ ] Larger LV8 rows are silently omitted.
- [ ] PASS claimed without executed hard smoke/bench gates.
