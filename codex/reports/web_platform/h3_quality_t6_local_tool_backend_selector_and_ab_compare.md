PASS

## 1) Meta
- Task slug: `h3_quality_t6_local_tool_backend_selector_and_ab_compare`
- Kapcsolodo canvas: `canvases/web_platform/h3_quality_t6_local_tool_backend_selector_and_ab_compare.md`
- Kapcsolodo goal YAML: `codex/goals/canvases/web_platform/fill_canvas_h3_quality_t6_local_tool_backend_selector_and_ab_compare.yaml`
- Futas datuma: `2026-03-30`
- Branch / commit: `main @ e5beb04 (dirty working tree)`
- Fokusz terulet: `Scripts (local tooling)`

## 2) Scope

### 2.1 Cel
- A local trial-run core/CLI/GUI explicit backend selectort kapjon (`auto | sparrow_v1 | nesting_engine_v2`).
- A platform start/restart subprocess `WORKER_ENGINE_BACKEND` env override-ot kapjon, ha konkret backend lett kerve.
- A summary es quality_summary kulon jelezze a requested vs effective backendet es azok egyezeset.
- A benchmark runner tudjon case x backend matrixot futtatni es `--compare-backends` convenience modot adjon.
- A benchmark output gepileg olvashato compare delta blokkot adjon.
- Keszuljon dedikalt smoke, amely mindent bizonyit valodi platform nelkul.

### 2.2 Nem-cel (explicit)
- Run-config API, DB schema vagy migration az engine backend tarolasara.
- Worker/main backend-selection policy tovabbi atalakitasa.
- Quality profile-ok (`fast_preview`, `quality_default`, `quality_aggressive`) bevezetese.
- Frontend UI rollout vagy permanent operator dashboard.

## 3) Valtozasok osszefoglalasa

### 3.1 Erintett fajlok
- **Scripts (core/CLI/GUI):**
  - `scripts/trial_run_tool_core.py`
  - `scripts/run_trial_run_tool.py`
  - `scripts/trial_run_tool_gui.py`
- **Scripts (benchmark):**
  - `scripts/run_h3_quality_benchmark.py`
- **Scripts (smoke):**
  - `scripts/smoke_h3_quality_t6_local_tool_backend_selector_and_ab_compare.py`
  - `scripts/smoke_trial_run_tool_tkinter_gui.py` (regresszio fix: uj GuiFormValues field)
- **Docs:**
  - `docs/nesting_quality/h3_quality_benchmark_harness.md`
- **Codex artefaktok:**
  - `canvases/web_platform/h3_quality_t6_local_tool_backend_selector_and_ab_compare.md`
  - `codex/goals/canvases/web_platform/fill_canvas_h3_quality_t6_local_tool_backend_selector_and_ab_compare.yaml`
  - `codex/prompts/web_platform/h3_quality_t6_local_tool_backend_selector_and_ab_compare/run.md`
  - `codex/codex_checklist/web_platform/h3_quality_t6_local_tool_backend_selector_and_ab_compare.md`
  - `codex/reports/web_platform/h3_quality_t6_local_tool_backend_selector_and_ab_compare.md`

### 3.2 Mi valtozott es miert

- **Backend selector a local tool lancban:**
  A `TrialRunConfig` kapott egy `engine_backend` mezot (default `auto`). A CLI `--engine-backend`, a GUI egy Combobox-on keresztul adja at. A `_run_platform_command` helperbe bevezettuk az `env_overrides` parametert; konkret backend eseten a `_start_platform_if_requested` es `_restart_platform_if_requested` `WORKER_ENGINE_BACKEND=<backend>` env override-ot adnak at a subprocess-nek.

- **Requested vs effective backend szetvalasztas:**
  A `_build_quality_summary_json` ket uj mezot kapott: `requested_engine_backend` (a configbol), `effective_engine_backend` (az `engine_meta.json` artifact evidence-bol). Az `engine_backend_match` mező `True`/`False`/`None` (ha auto vagy unknown).

- **Benchmark backend matrix:**
  A `run_h3_quality_benchmark.py` `--engine-backend` (repeatable) es `--compare-backends` argumentumot kapott. A case loop a backends listara is iteralodik. Az output `compare_results` tombje `_build_compare_delta`-val generalt evidence-first delta blokkokat ad.

- **Tudatos scope korlatozas:**
  A task nem nyult DB/API schema-hoz, migration-hoz vagy product feature-hoz. A backend selector local tooling override maradt.

## 4) Verifikacio (How tested)

### 4.1 Kotelezo repo gate
- `./scripts/verify.sh --report codex/reports/web_platform/h3_quality_t6_local_tool_backend_selector_and_ab_compare.md` -> PASS

### 4.2 Opcionalis, feladatfuggo ellenorzes
- `python3 -m py_compile scripts/trial_run_tool_core.py scripts/run_trial_run_tool.py scripts/trial_run_tool_gui.py scripts/run_h3_quality_benchmark.py scripts/smoke_h3_quality_t6_local_tool_backend_selector_and_ab_compare.py` -> PASS
- `python3 scripts/smoke_h3_quality_t6_local_tool_backend_selector_and_ab_compare.py` -> PASS

### 4.3 Ajanlott regresszio
- `python3 scripts/smoke_trial_run_tool_cli_core.py` -> PASS
- `python3 scripts/smoke_h3_quality_t2_benchmark_pack_and_quality_summary_harness.py` -> PASS
- `python3 scripts/smoke_trial_run_tool_tkinter_gui.py` -> PASS

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo teszt/ellenorzes |
| -------- | ------: | ------------------------ | ---------- | --------------------------- |
| #1 A local trial-run core/CLI/GUI tud explicit backend selectort kezelni | PASS | `scripts/trial_run_tool_core.py:27,143`; `scripts/run_trial_run_tool.py:113`; `scripts/trial_run_tool_gui.py:250,378` | `VALID_ENGINE_BACKENDS` konstans, `TrialRunConfig.engine_backend`, CLI `--engine-backend`, GUI Combobox | `smoke_h3_quality_t6: cli_backend_selector, gui_backend_selector` |
| #2 A platform start/restart env override bizonyitottan a kert worker backenddel fut | PASS | `scripts/trial_run_tool_core.py:621-625,700,711` | `_engine_backend_env_overrides` helper visszaadja a `WORKER_ENGINE_BACKEND` env-et; `_start_platform_if_requested` es `_restart_platform_if_requested` atadja | `smoke_h3_quality_t6: platform_env_override` |
| #3 A summary/quality_summary kulon jelzi a kert es az effektive visszaigazolt backendet | PASS | `scripts/trial_run_tool_core.py:879,1120-1135` | `requested_engine_backend`, `effective_engine_backend`, `engine_backend_match` explicit mezok a quality_summary-ban es a summary.md-ben | `smoke_h3_quality_t6: quality_summary_backend_fields` |
| #4 A benchmark runner case x backend matrixot tud futtatni | PASS | `scripts/run_h3_quality_benchmark.py:165,169,391-395` | `--engine-backend` (repeatable) es `--compare-backends` argumentumok; a case loop a backends listara is iteralodik | `smoke_h3_quality_t6: benchmark_plan_compare` |
| #5 A `--plan-only` modban is helyesen kibontja a backend x case tervet | PASS | `scripts/run_h3_quality_benchmark.py:410-412` | plan_only modban minden (case, backend) paros bekerul az entries-be | `smoke_h3_quality_t6: benchmark_plan_compare, benchmark_plan_single_backend` |
| #6 A benchmark output gepileg olvashato compare delta blokkot ad | PASS | `scripts/run_h3_quality_benchmark.py:176-262,437,447` | `_build_compare_delta` es `_build_compare_results` evidence-first delta szamitas, hibaturo incomplete_reason-nel | `smoke_h3_quality_t6: compare_delta_block` |
| #7 A task-specifikus smoke zold | PASS | `scripts/smoke_h3_quality_t6_local_tool_backend_selector_and_ab_compare.py` | 7 alteszt: cli, gui, env, quality_summary, benchmark plan, compare delta, single backend | `python3 scripts/smoke_h3_quality_t6_local_tool_backend_selector_and_ab_compare.py` |
| #8 A standard verify wrapper lefut, report + log frissul | PASS | `codex/reports/web_platform/h3_quality_t6_local_tool_backend_selector_and_ab_compare.verify.log` | A standard gate wrapper lefutott | `./scripts/verify.sh --report ...` |

## 6) Advisory notes
- A task tudatosan local tooling scope-ban maradt. A backend selector nem product feature, hanem local tool/runtime override.
- A compare summary additive, evidence-first. Nem allit optimalitast, csak merheto kulonbseget.
- A meglevo `smoke_trial_run_tool_tkinter_gui.py` script kapott egy regresszio fix-et az uj `engine_backend` mezo hozzaadasaval a `GuiFormValues`-hoz.
- A `--compare-backends` flag fix `sparrow_v1` + `nesting_engine_v2` part hasznal; kesobb bovitheto.

## 7) Follow-ups
- Quality profile-ok (`fast_preview`, `quality_default`, `quality_aggressive`) bevezetese a kovetkezo lane-ben.
- A compare delta runtime_sec_delta mezo valodi futassal feltoltheto, jelenleg plan-only modban null.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-03-30T14:01:42+02:00 → 2026-03-30T14:05:10+02:00 (208s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/h3_quality_t6_local_tool_backend_selector_and_ab_compare.verify.log`
- git: `main@e5beb04`
- módosított fájlok (git status): 14

**git diff --stat**

```text
 .../h3_quality_benchmark_harness.md                |  36 +++
 scripts/run_h3_quality_benchmark.py                | 290 ++++++++++++++++-----
 scripts/run_trial_run_tool.py                      |   9 +-
 scripts/smoke_trial_run_tool_tkinter_gui.py        |   6 +
 scripts/trial_run_tool_core.py                     |  49 +++-
 scripts/trial_run_tool_gui.py                      |  24 ++
 6 files changed, 337 insertions(+), 77 deletions(-)
```

**git status --porcelain (preview)**

```text
 M docs/nesting_quality/h3_quality_benchmark_harness.md
A  docs/nesting_quality/nesting_quality_konkret_feladatok.md
 M scripts/run_h3_quality_benchmark.py
 M scripts/run_trial_run_tool.py
 M scripts/smoke_trial_run_tool_tkinter_gui.py
 M scripts/trial_run_tool_core.py
 M scripts/trial_run_tool_gui.py
?? canvases/web_platform/h3_quality_t6_local_tool_backend_selector_and_ab_compare.md
?? codex/codex_checklist/web_platform/h3_quality_t6_local_tool_backend_selector_and_ab_compare.md
?? codex/goals/canvases/web_platform/fill_canvas_h3_quality_t6_local_tool_backend_selector_and_ab_compare.yaml
?? codex/prompts/web_platform/h3_quality_t6_local_tool_backend_selector_and_ab_compare/
?? codex/reports/web_platform/h3_quality_t6_local_tool_backend_selector_and_ab_compare.md
?? codex/reports/web_platform/h3_quality_t6_local_tool_backend_selector_and_ab_compare.verify.log
?? scripts/smoke_h3_quality_t6_local_tool_backend_selector_and_ab_compare.py
```

<!-- AUTO_VERIFY_END -->
