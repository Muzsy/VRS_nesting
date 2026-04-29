PASS

## 1) Meta
- Task slug: `cavity_t1_contract_and_policy`
- Kapcsolodo canvas: `canvases/nesting_engine/cavity_t1_contract_and_policy.md`
- Kapcsolodo goal YAML: `codex/goals/canvases/nesting_engine/fill_canvas_cavity_t1_contract_and_policy.yaml`
- Futas datuma: `2026-04-29`
- Branch / commit: `main` (dirty working tree)
- Fokusz terulet: `Docs | Contract | Policy`

## 2) Scope

### 2.1 Cel
- `cavity_plan_v1` contract dokumentacio letrehozasa.
- `part_in_part=prepack` quality policy dokumentalasa worker/engine hataron.
- `io_contract_v2` additive cavity-prepack policy szekcio formalizalasa.

### 2.2 Nem-cel
- `worker/cavity_prepack.py` implementacio.
- Result normalizer kodmodositas.
- Rust engine parser vagy fallback logika modositas.
- UI/export valtoztatas.

## 3) Valtozasok osszefoglalasa

### 3.1 Erintett fajlok
- `docs/nesting_engine/cavity_prepack_contract_v1.md`
- `docs/nesting_quality/cavity_prepack_quality_policy.md`
- `docs/nesting_engine/io_contract_v2.md`
- `codex/codex_checklist/nesting_engine/cavity_t1_contract_and_policy.md`
- `codex/reports/nesting_engine/cavity_t1_contract_and_policy.md`

### 3.2 Mi valtozott es miert
- Uj contract dokumentum rogziti a `cavity_plan_v1` schemajat, invariansait,
  instance/quantity accounting szabalyait es backward compatibilityt.
- Uj quality policy dokumentum rogziti a `prepack` worker policy jelentest,
  a Rust CLI korlatot (`off|auto`) es rollout sorrendet.
- `io_contract_v2` additive szekcioja tisztazza, hogy a cavity prepack sidecar
  artifact, nem uj Rust IO contract verzio.

## 4) Verifikacio

### 4.1 Feladatfuggo ellenorzes
- Dokumentacio review: pathok, mezonevek, policy mappingek valos repo allapothoz igazodnak.

### 4.2 Kotelezo repo gate
- `./scripts/verify.sh --report codex/reports/nesting_engine/cavity_t1_contract_and_policy.md` -> PASS

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek | Magyarazat | Kapcsolodo ellenorzes |
| --- | --- | --- | --- | --- |
| `cavity_plan_v1` schema dokumentalt | PASS | `docs/nesting_engine/cavity_prepack_contract_v1.md:16`, `docs/nesting_engine/cavity_prepack_contract_v1.md:52`, `docs/nesting_engine/cavity_prepack_contract_v1.md:75` | Top-level schema, virtual parts, instance/quantity szabalyok explicit leirva. | Dokumentacio review |
| `part_in_part=prepack` jelentese dokumentalt | PASS | `docs/nesting_quality/cavity_prepack_quality_policy.md:16`, `docs/nesting_quality/cavity_prepack_quality_policy.md:39`, `docs/nesting_engine/io_contract_v2.md:259` | Worker policy mapping es effective engine `off` szabaly rogzitve. | Dokumentacio review |
| Rust engine input tovabbra is `nesting_engine_v2` | PASS | `docs/nesting_engine/cavity_prepack_contract_v1.md:8`, `docs/nesting_engine/io_contract_v2.md:251` | Kifejezetten rogzitettuk, hogy nincs uj Rust contract verzio. | Dokumentacio review |
| Parent outer-only/holes-empty v1 korlat dokumentalt | PASS | `docs/nesting_engine/cavity_prepack_contract_v1.md:93`, `docs/nesting_engine/io_contract_v2.md:269` | Top-level parent virtual part invariansok explicit szerepelnek. | Dokumentacio review |
| Cut-order nem-cel es manufacturing follow-up dokumentalt | PASS | `docs/nesting_engine/cavity_prepack_contract_v1.md:117`, `docs/nesting_engine/io_contract_v2.md:289` | Nem-cel deklaracio explicit megnevezi a cut-order hianyt. | Dokumentacio review |
| Nincs implementacios kod ebben a taskban | PASS | `codex/reports/nesting_engine/cavity_t1_contract_and_policy.md:13`, `codex/reports/nesting_engine/cavity_t1_contract_and_policy.md:18` | A scope es non-goal szekcio explicit dokumentacios korre korlatoz. | Diff review |

## 6) Advisory notes
- A `prepack` policy jelen dokumentumban worker-side runtime policy; T2-ben lesz
  tenyleges profile/worker mapping kodbekotes.
- A `cavity_plan_v1` intentionally additive sidecar, hogy a Rust IO boundary
  stabil maradjon.

## 7) Follow-up
- T2: runtime profile es policy wiring.
- T3: worker-side prepack modul implementacio.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-04-29T21:33:08+02:00 → 2026-04-29T21:35:48+02:00 (160s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/nesting_engine/cavity_t1_contract_and_policy.verify.log`
- git: `main@1247346`
- módosított fájlok (git status): 40

**git diff --stat**

```text
 api/routes/runs.py                    | 53 +++++++++++++++++++++++++++++++----
 docs/nesting_engine/io_contract_v2.md | 46 ++++++++++++++++++++++++++++++
 2 files changed, 94 insertions(+), 5 deletions(-)
```

**git status --porcelain (preview)**

```text
 M api/routes/runs.py
 M docs/nesting_engine/io_contract_v2.md
?? canvases/nesting_engine/cavity_t0_artifact_recovery_and_baseline_replay.md
?? canvases/nesting_engine/cavity_t1_contract_and_policy.md
?? canvases/nesting_engine/cavity_t2_runtime_profile_prepack_mode.md
?? canvases/nesting_engine/cavity_t3_worker_cavity_prepack_v1.md
?? canvases/nesting_engine/cavity_t4_worker_integration_and_artifacts.md
?? canvases/nesting_engine/cavity_t5_result_normalizer_expansion.md
?? canvases/nesting_engine/cavity_t6_svg_dxf_export_validation.md
?? canvases/nesting_engine/cavity_t7_ui_observability.md
?? canvases/nesting_engine/cavity_t8_production_regression_benchmark.md
?? codex/codex_checklist/nesting_engine/cavity_t0_artifact_recovery_and_baseline_replay.md
?? codex/codex_checklist/nesting_engine/cavity_t1_contract_and_policy.md
?? codex/goals/canvases/nesting_engine/fill_canvas_cavity_t0_artifact_recovery_and_baseline_replay.yaml
?? codex/goals/canvases/nesting_engine/fill_canvas_cavity_t1_contract_and_policy.yaml
?? codex/goals/canvases/nesting_engine/fill_canvas_cavity_t2_runtime_profile_prepack_mode.yaml
?? codex/goals/canvases/nesting_engine/fill_canvas_cavity_t3_worker_cavity_prepack_v1.yaml
?? codex/goals/canvases/nesting_engine/fill_canvas_cavity_t4_worker_integration_and_artifacts.yaml
?? codex/goals/canvases/nesting_engine/fill_canvas_cavity_t5_result_normalizer_expansion.yaml
?? codex/goals/canvases/nesting_engine/fill_canvas_cavity_t6_svg_dxf_export_validation.yaml
?? codex/goals/canvases/nesting_engine/fill_canvas_cavity_t7_ui_observability.yaml
?? codex/goals/canvases/nesting_engine/fill_canvas_cavity_t8_production_regression_benchmark.yaml
?? codex/prompts/nesting_engine/cavity_t0_artifact_recovery_and_baseline_replay/
?? codex/prompts/nesting_engine/cavity_t1_contract_and_policy/
?? codex/prompts/nesting_engine/cavity_t2_runtime_profile_prepack_mode/
?? codex/prompts/nesting_engine/cavity_t3_worker_cavity_prepack_v1/
?? codex/prompts/nesting_engine/cavity_t4_worker_integration_and_artifacts/
?? codex/prompts/nesting_engine/cavity_t5_result_normalizer_expansion/
?? codex/prompts/nesting_engine/cavity_t6_svg_dxf_export_validation/
?? codex/prompts/nesting_engine/cavity_t7_ui_observability/
?? codex/prompts/nesting_engine/cavity_t8_production_regression_benchmark/
?? codex/reports/nesting_engine/cavity_t0_artifact_recovery_and_baseline_replay.md
?? codex/reports/nesting_engine/cavity_t0_artifact_recovery_and_baseline_replay.verify.log
?? codex/reports/nesting_engine/cavity_t1_contract_and_policy.md
?? codex/reports/nesting_engine/cavity_t1_contract_and_policy.verify.log
?? codex/reports/nesting_engine/otszog_bodypad_runtime_root_cause_20260428.md
?? docs/nesting_engine/cavity_prepack_contract_v1.md
?? docs/nesting_quality/cavity_prepack_quality_policy.md
?? scripts/smoke_cavity_t0_artifact_recovery_and_baseline_replay.py
?? tests/test_run_artifact_url_recovery.py
```

<!-- AUTO_VERIFY_END -->
