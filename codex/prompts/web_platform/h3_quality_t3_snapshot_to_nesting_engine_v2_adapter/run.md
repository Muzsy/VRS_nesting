# DXF Nesting Platform Codex Task - H3-Quality-T3 Snapshot -> nesting_engine_v2 adapter
TASK_SLUG: h3_quality_t3_snapshot_to_nesting_engine_v2_adapter

Olvasd el:
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `worker/engine_adapter_input.py`
- `worker/main.py`
- `vrs_nesting/runner/nesting_engine_runner.py`
- `docs/nesting_engine/io_contract_v2.md`
- `scripts/validate_nesting_solution.py`
- `scripts/smoke_h1_e5_t1_engine_adapter_input_mapping_h1_minimum.py`
- `scripts/smoke_platform_determinism_rotation.sh`
- `canvases/web_platform/h3_quality_t3_snapshot_to_nesting_engine_v2_adapter.md`
- `codex/goals/canvases/web_platform/fill_canvas_h3_quality_t3_snapshot_to_nesting_engine_v2_adapter.yaml`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosithatsz, ami szerepel valamelyik
  YAML step `outputs` listajaban.
- Ez a task adapter-task. Nem worker backend switch, nem dual-engine rollout,
  nem viewer/result normalizer v2 task, es nem H3-E4 domain task.
- A `worker/main.py` backend-futtato agat ebben a taskban ne allitsd at a
  `nesting_engine_runner`-re.
- A v2 builder fail-fast legyen ott, ahol a snapshot vilag nem kepezheto le
  vesztesegmentesen vagy egyertelmuen a v2 input contractra.

Implementacios elvarasok:
- A `worker/engine_adapter_input.py` kapjon explicit `nesting_engine_v2` buildert.
- A builder a snapshot `solver_config_jsonb` mezokbol kepezze a `seed`,
  `time_limit_sec`, `sheet.kerf_mm`, `sheet.spacing_mm`, `sheet.margin_mm`
  mezoket.
- A v2 builder rotation policy-ja mar ne a v1 0/90/180/270 korlatot kovesse:
  `rotation_step_deg` alapjan explicit teljes veges halmazt kepezzen.
- `allow_free_rotation=true` most is fail-fast legyen.
- A `parts` a geometry manifest `polygon.outer_ring` / `hole_rings` truth-jabol
  epuljenek, ne bbox-only adapter keszuljon.
- A `sheet` mappingnel ne legyen csendes veszteseges fallback. Ha a snapshot tobb,
  egymastol eltero sheet typust hordoz, legyen explicit hiba.
- Keszits canonical hash helper(eke)t a v2 inputhoz, hogy a smoke bizonyitani tudja
  a determinizmust.

A smoke bizonyitsa legalabb:
- sikeres snapshot -> v2 input mapping;
- `version == nesting_engine_v2`;
- 45 fokos rotation step eseten helyes teljes rotaciohalmaz keletkezik;
- a canonical hash ket futasnal azonos;
- `allow_free_rotation=true` kontrollalt hibaval megall;
- multi-sheet / hianyzo geometry / ures parts kontrollalt hibaval megall.

A reportban kulon nevezd meg:
- miert marad ez a task single-sheet-family adapter preview, nem teljes backend rollout;
- hogyan ter el a v2 builder rotation policy-ja a jelenlegi v1 buildertol;
- mely snapshot mezo mely v2 input mezore lett lekotve;
- hogy a task tudatosan NEM kapcsolja meg at a worker runtime backendet.

A vegen futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/web_platform/h3_quality_t3_snapshot_to_nesting_engine_v2_adapter.md`

Eredmeny:
- Frissitsd a checklistet es a reportot evidence-alapon.
- A reportban legyen DoD -> Evidence matrix es korrekt AUTO_VERIFY blokk.
- Add meg a vegleges fajltartalmakat.
