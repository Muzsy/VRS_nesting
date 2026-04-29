PASS_WITH_NOTES

## 1) Meta
- Task slug: `cavity_t0_artifact_recovery_and_baseline_replay`
- Kapcsolodo canvas: `canvases/nesting_engine/cavity_t0_artifact_recovery_and_baseline_replay.md`
- Kapcsolodo goal YAML: `codex/goals/canvases/nesting_engine/fill_canvas_cavity_t0_artifact_recovery_and_baseline_replay.yaml`
- Futas datuma: `2026-04-29`
- Branch / commit: `main` (dirty working tree)
- Fokusz terulet: `API artifact URL recovery + baseline evidence`

## 2) Scope

### 2.1 Cel
- Artifact URL recovery javitas `solver_input` es `engine_meta` artifactokra.
- Teszt/smoke bizonyitek, hogy bucket mismatch eseten van fallback bucket probalkozas.
- Legacy baseline hibaallapot rogzitese lokalis repro artifactokbol.

### 2.2 Nem-cel (explicit)
- Cavity prepack implementacio.
- Rust NFP/BLF fallback logika modositas.
- Timeout/work_budget tuning.
- Warning suppression.

## 3) Valtozasok osszefoglalasa

### 3.1 Erintett fajlok
- `api/routes/runs.py`
- `tests/test_run_artifact_url_recovery.py`
- `scripts/smoke_cavity_t0_artifact_recovery_and_baseline_replay.py`
- `codex/codex_checklist/nesting_engine/cavity_t0_artifact_recovery_and_baseline_replay.md`
- `codex/reports/nesting_engine/cavity_t0_artifact_recovery_and_baseline_replay.md`

### 3.2 Mi valtozott es miert
- `api/routes/runs.py`: uj helper kerult be az artifact download URL endpointhez.
  A logika bucket fallbacket alkalmaz: eloszor artifact row bucket, majd API
  `storage_bucket`.
- `tests/test_run_artifact_url_recovery.py`: unit tesztek a bucket candidate
  sorrendre, fallback viselkedesre es storage_key hibaagra.
- `scripts/smoke_cavity_t0_artifact_recovery_and_baseline_replay.py`: fake
  Supabase smoke, amely run-artifacts bucket hiba utan source-files fallback
  signed URL eredmenyt var.

## 4) Verifikacio

### 4.1 Opcionais ellenorzesek
- `python3 -m pytest -q tests/test_run_artifact_url_recovery.py` -> PASS (`3 passed`)
- `python3 scripts/smoke_cavity_t0_artifact_recovery_and_baseline_replay.py` -> PASS
- `python3 -m py_compile api/routes/runs.py tests/test_run_artifact_url_recovery.py scripts/smoke_cavity_t0_artifact_recovery_and_baseline_replay.py` -> PASS

### 4.2 Baseline legacy bizonyitek (lokalis artifact)
- `tmp/runs/20260330T224752Z_sample_dxf_1ebe1445/downloaded_artifact_urls.json`
  szerint korabban `solver_input` es `engine_meta` artifact URL endpoint `400 artifact url failed`.
- `tmp/repro_f683e6f7/manual_repro_20260427/stderr.log` bizonyitja:
  `warning: --placer nfp fallback to blf`, `NEST_NFP_STATS_V1 effective_placer=blf`,
  `SA_PROFILE_V1`.
- `tmp/repro_f683e6f7/manual_repro_20260427/stdout.json` bizonyitja a partial
  kimenetet `TIME_LIMIT_EXCEEDED` unplaced okokkal.

### 4.3 Korlatozas
- Valos production API endpoint ujrafuttatas es signed URL letoltes ebben a
  futasban nem tortent (kulso hozzaferesi blokk). Emiatt a production replay
  T0 DoD csak reszben zarhato.

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek | Magyarazat | Kapcsolodo ellenorzes |
| --- | --- | --- | --- | --- |
| Artifact URL endpoint recovery logika letezik `solver_input`/`engine_meta` esetekre | PASS | `api/routes/runs.py:905`, `api/routes/runs.py:921`, `api/routes/runs.py:968` | Bucket candidate + fallback signing helper bekerult az endpointbe. | pytest + smoke |
| Bucket mismatch eseten fallback bucket probalkozas bizonyitott | PASS | `tests/test_run_artifact_url_recovery.py:49`, `tests/test_run_artifact_url_recovery.py:65` | Fake Supabase elso bucket hibajat kovetoen masodik bucket sikeres. | pytest |
| Storage key hiany explicit hibaaggal kezelt | PASS | `api/routes/runs.py:928`, `tests/test_run_artifact_url_recovery.py:71` | Ures storage_key eseten SupabaseHTTPError keletkezik. | pytest |
| Task-specifikus smoke keszult | PASS | `scripts/smoke_cavity_t0_artifact_recovery_and_baseline_replay.py:1` | Smoke run-artifacts fail -> source-files fallback utat validal. | smoke script |
| Legacy baseline hibaallapot dokumentalt | PASS | `tmp/runs/20260330T224752Z_sample_dxf_1ebe1445/downloaded_artifact_urls.json:6`, `tmp/repro_f683e6f7/manual_repro_20260427/stderr.log:3`, `tmp/repro_f683e6f7/manual_repro_20260427/stdout.json:1` | Korabbi artifact URL fail + fallback to blf + timeout unplaced bizonyitek rogzitve. | artifact olvasas |
| Production run URL recovery valos API endpointen ujraellenorizve | FAIL | N/A | Kulso hozzaferesi blokk: ebben a futasban nincs elerheto production API/regisztralt tokenes letoltes. | N/A |
| Production 1:1 replay uj letoltott snapshot alapjan | FAIL | N/A | Uj letoltes nelkul nem igazolhato, csak korabbi lokalis repro bizonyitek van. | N/A |

## 6) Advisory notes
- A javitas API oldali bucket fallback; worker write-path valtoztatas most nem
  volt szukseges.
- A jelen bizonyitek fake Supabase tesztekkel igazolja a recovery logikat, de
  production bizonyitas kovetkezo futast igenyel.

## 7) Follow-up
- T0 folytatas: production API ellen valos signed URL ujrafuttatas.
- Ha sikeres: ugyanazon run `solver_input` letoltesevel fresh legacy replay.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-04-29T21:22:58+02:00 → 2026-04-29T21:26:00+02:00 (182s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/nesting_engine/cavity_t0_artifact_recovery_and_baseline_replay.verify.log`
- git: `main@1247346`
- módosított fájlok (git status): 34

**git diff --stat**

```text
 api/routes/runs.py | 53 ++++++++++++++++++++++++++++++++++++++++++++++++-----
 1 file changed, 48 insertions(+), 5 deletions(-)
```

**git status --porcelain (preview)**

```text
 M api/routes/runs.py
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
?? codex/reports/nesting_engine/otszog_bodypad_runtime_root_cause_20260428.md
?? scripts/smoke_cavity_t0_artifact_recovery_and_baseline_replay.py
?? tests/test_run_artifact_url_recovery.py
```

<!-- AUTO_VERIFY_END -->
