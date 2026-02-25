# Codex Report — bcd_orbit_determinism_fuzz

**Status:** PASS_WITH_NOTES

## 1) Scope

### 1.1 Cél

1. Orbit next-event döntéshez normatív spec + trace ellenőrizhetőség.
2. CLI szintű determinism harness 50 ismétléssel, canonical JSON byte-egyezésre.
3. Célzott fuzz/quarantine fixture folyamat stdlib-only generátorral.

### 1.2 Kezdeti hiányzó bizonyítékpontok (felderítés)

1. Nem volt külön normatív next-event spec doksi a trace mezőkről.
2. Nem volt integration smoke teszt, ami az első 1-3 orbit döntés mezőit byte-azonosan ellenőrzi.
3. Nem volt külön, 50x CLI futást végző canonical diff smoke script.
4. Nem volt stdlib-only célzott fuzz/quarantine fixture generátor script.

## 2) Added/Changed Files

1. `docs/nesting_engine/orbit_next_event_spec.md`
2. `rust/nesting_engine/src/nfp/concave.rs`
3. `rust/nesting_engine/tests/orbit_next_event_trace_smoke.rs`
4. `scripts/canonicalize_json.py`
5. `scripts/smoke_nesting_engine_determinism.sh`
6. `scripts/fuzz_nfp_regressions.py`
7. `poc/nfp_regression/quarantine_generated_20260225_20260225_near_parallel.json`
8. `poc/nfp_regression/quarantine_generated_20260225_20260225_sliver_gap.json`
9. `poc/nfp_regression/quarantine_generated_20260225_20260225_collinear_dense.json`
10. `codex/reports/nesting_engine/bcd_orbit_determinism_fuzz.md`

## 3) Runbook (Reproducible)

1. Orbit trace smoke:
   `cd rust/nesting_engine && cargo test --test orbit_next_event_trace_smoke`
2. NFP regression suite:
   `cd rust/nesting_engine && cargo test --test nfp_regression`
3. Full nesting_engine tests:
   `cd rust/nesting_engine && cargo test`
4. Determinism smoke (50x):
   `./scripts/smoke_nesting_engine_determinism.sh`
5. Targeted fuzz + quarantine generation:
   `python3 scripts/fuzz_nfp_regressions.py --seed 20260225 --count 3`
6. Repo gate:
   `./scripts/check.sh`

## 4) PASS Criteria

1. `cargo test` a `rust/nesting_engine` crate-ben PASS.
2. `scripts/smoke_nesting_engine_determinism.sh` PASS, ha mind az 50 canonical output byte-azonos.
3. `scripts/fuzz_nfp_regressions.py` PASS, ha a generálás után a `nfp_regression` suite zöld.
4. `./scripts/check.sh` PASS.

## 5) DoD → Evidence

| DoD | Status | Evidence |
|---|---|---|
| Orbit next-event spec + trace séma | PASS | `docs/nesting_engine/orbit_next_event_spec.md` tartalmaz event definíciót, next-event választást, tie-breaket, touching group szabályokat, invariánsokat, trace mezőlistát. |
| 1-3 döntéses golden trace smoke | PASS | `rust/nesting_engine/tests/orbit_next_event_trace_smoke.rs` két fixture-en (`concave_touching_group`, `concave_multi_contact`) ellenőrzi: `step_index`, `touching_group_signature`, `chosen_direction`, `next_event_kind`, `next_event_t_num/den`, `tie_break_reason`. |
| Trace collector nem zajos, tesztből használható | PASS | `rust/nesting_engine/src/nfp/concave.rs` új publikus trace API-t ad (`collect_orbit_next_event_trace`) stdout nélkül; normál compute útvonal változatlanul zajmentes. |
| 50× CLI determinism canonical byte-egyezéssel | PASS | `scripts/smoke_nesting_engine_determinism.sh` release build + 50 futás + `scripts/canonicalize_json.py` canonicalizálás + `cmp -s`; mismatch esetén `/tmp/out_a.json` és `/tmp/out_b.json`, nonzero exit. |
| Célzott fuzz→quarantine folyamat | PASS | `scripts/fuzz_nfp_regressions.py` seedelt, célzott kategóriákat generál (`near_parallel`, `near_tangent`, `sliver_gap`, `collinear_dense`), quarantine fájlt ír és futtatja a regressziós suite-et. |
| Min. 3 új quarantine fixture | PASS | `poc/nfp_regression/quarantine_generated_20260225_20260225_{near_parallel,sliver_gap,collinear_dense}.json` létrejött és suite-kompatibilis. |
| Repo gate | PASS | `./scripts/check.sh` lefutott és PASS. |

## 6) Quarantine / Acceptance

1. Generated esetek quarantine névterében maradnak: `quarantine_generated_*`.
2. Ezek nem tekintendők accepted fixture-nek automatikusan.
3. CI-ben nincs automatikus expected-builder futtatás.
4. Acceptance csak manuális review + explicit átnevezés/átmozgatás után javasolt.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-02-25T20:34:34+01:00 → 2026-02-25T20:37:26+01:00 (172s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/nesting_engine/bcd_orbit_determinism_fuzz.verify.log`
- git: `main@739ba24`
- módosított fájlok (git status): 11

**git diff --stat**

```text
 rust/nesting_engine/src/nfp/concave.rs | 152 ++++++++++++++++++++++++++++++++-
 1 file changed, 151 insertions(+), 1 deletion(-)
```

**git status --porcelain (preview)**

```text
 M rust/nesting_engine/src/nfp/concave.rs
?? codex/reports/nesting_engine/bcd_orbit_determinism_fuzz.md
?? codex/reports/nesting_engine/bcd_orbit_determinism_fuzz.verify.log
?? docs/nesting_engine/orbit_next_event_spec.md
?? poc/nfp_regression/quarantine_generated_20260225_20260225_collinear_dense.json
?? poc/nfp_regression/quarantine_generated_20260225_20260225_near_parallel.json
?? poc/nfp_regression/quarantine_generated_20260225_20260225_sliver_gap.json
?? rust/nesting_engine/tests/orbit_next_event_trace_smoke.rs
?? scripts/canonicalize_json.py
?? scripts/fuzz_nfp_regressions.py
?? scripts/smoke_nesting_engine_determinism.sh
```

<!-- AUTO_VERIFY_END -->
