FAIL (RC correctness gate)

## 1) Meta
- Task slug: `engine_v2_nfp_rc_t07_nfp_correctness_validator`
- Kapcsolodo canvas: `canvases/nesting_engine/engine_v2_nfp_rc_t07_nfp_correctness_validator.md`
- Kapcsolodo goal YAML: `codex/goals/canvases/nesting_engine/fill_canvas_engine_v2_nfp_rc_t07_nfp_correctness_validator.yaml`
- Futas datuma: `2026-05-04`
- Fokusz terulet: `NFP correctness validator bin + gate meres`

## 2) Scope
- Uj bin implementalasa: `rust/nesting_engine/src/bin/nfp_correctness_benchmark.rs`
- Exact collision checker + mintavetelezes + verdict kepzes.
- Report/checklist kitoltese T07 kriteriumok menten.

## 3) Erintett fajlok
- `rust/nesting_engine/src/bin/nfp_correctness_benchmark.rs`
- `codex/codex_checklist/nesting_engine/engine_v2_nfp_rc_t07_nfp_correctness_validator.md`
- `codex/reports/nesting_engine/engine_v2_nfp_rc_t07_nfp_correctness_validator.md`

## 4) Futtatott parancsok es eredmenyek
- `cargo run --bin nfp_correctness_benchmark -- --help` -> PASS
- `cargo run --bin nfp_correctness_benchmark -- --fixture tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_01.json --nfp-source reduced_convolution_v1 --output-json` -> PASS
- `cargo run --bin nfp_correctness_benchmark -- --fixture tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_01.json --nfp-source mock_exact --output-json` -> PASS
- `ls rust/nesting_engine/src/bin/nfp_correctness_benchmark.rs` -> PASS
- `cargo check -p nesting_engine` -> PASS (warning-only)

## 5) Meresi outputok (T07)

### 5.1 RC source (`reduced_convolution_v1`)
- `pair_id`: `lv8_pair_01`
- `nfp_was_available`: `true`
- `false_positive_count`: `0`
- `false_negative_count`: `383`
- `false_positive_rate`: `0.0`
- `false_negative_rate`: `0.1915`
- `correctness_verdict`: `FAIL_FALSE_NEGATIVE`

### 5.2 Mock source (`mock_exact`)
- `false_positive_rate`: `0.0`
- `false_negative_rate`: `0.0`
- `correctness_verdict`: `PASS`

## 6) Ketszintu gate statusz
- `validator_infra_pass: true`
  - Bin fut (`--help`), JSON mezok explicit, `mock_exact false_positive_rate=0.0`, verdict ertekkeszlet implementalva.
- `rc_correctness_pass: false`
  - RC futott es `NOT_AVAILABLE` nem volt, de `false_negative_rate=0.1915` > `0.01`.
- `t08_unblocked: false`
  - T08 gate blokkolt, mert `rc_correctness_pass=false`.

## 7) Acceptance criteria allapot
- [x] SZINT 1: validator infra pass
- [x] SZINT 1: mock_exact `false_positive_rate=0.0`
- [x] SZINT 1: JSON-ban explicit `false_positive_rate` es `false_negative_rate`
- [x] SZINT 1: `correctness_verdict` ertekkeszlet dokumentalt
- [x] SZINT 2: RC run megtortent, verdict nem `NOT_AVAILABLE`
- [x] SZINT 2: `false_positive_rate=0.0`
- [ ] SZINT 2: `false_negative_rate < 0.01` (nem teljesult)

## 8) Blocker / kockazat
- Blocker: igen, T08 inditas gatolt.
- Kockazat: magas. A mostani RC + cleanup output a meres szerint erosen konzervativ (19.15% FN), ez jelentosen csokkenti a hasznos kihasznalhato placement-teret.

## 9) Kovetkezo task indithatosag
- T07 fejlesztesi feladat vegrehajtva.
- Kovetkezo task (`T08`) ebben az allapotban **nem indithato** a task-gate szerint (`t08_unblocked=false`).

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-05-04T01:55:00+02:00 → 2026-05-04T01:58:02+02:00 (182s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/nesting_engine/engine_v2_nfp_rc_t07_nfp_correctness_validator.verify.log`
- git: `main@3f16462`
- módosított fájlok (git status): 4

**git status --porcelain (preview)**

```text
?? codex/codex_checklist/nesting_engine/engine_v2_nfp_rc_t07_nfp_correctness_validator.md
?? codex/reports/nesting_engine/engine_v2_nfp_rc_t07_nfp_correctness_validator.md
?? codex/reports/nesting_engine/engine_v2_nfp_rc_t07_nfp_correctness_validator.verify.log
?? rust/nesting_engine/src/bin/nfp_correctness_benchmark.rs
```

<!-- AUTO_VERIFY_END -->
