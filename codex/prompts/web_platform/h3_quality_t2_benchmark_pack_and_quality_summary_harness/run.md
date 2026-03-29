# DXF Nesting Platform Codex Task - H3-Quality-T2 Benchmark pack es quality summary harness
TASK_SLUG: h3_quality_t2_benchmark_pack_and_quality_summary_harness

Olvasd el:
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `scripts/trial_run_tool_core.py`
- `scripts/run_trial_run_tool.py`
- `scripts/smoke_trial_run_tool_cli_core.py`
- `scripts/bench_nesting_engine_f2_3_large_fixture.py`
- `scripts/gen_nesting_engine_real_dxf_quality_fixture.py`
- `scripts/smoke_h1_real_infra_closure.py`
- `samples/dxf_demo/stock_rect_1000x2000.dxf`
- `samples/dxf_demo/part_arc_spline_chaining_ok.dxf`
- `canvases/web_platform/h3_quality_t2_benchmark_pack_and_quality_summary_harness.md`
- `codex/goals/canvases/web_platform/fill_canvas_h3_quality_t2_benchmark_pack_and_quality_summary_harness.yaml`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosithatsz, ami szerepel valamelyik
  YAML step `outputs` listajaban.
- Ez a task benchmark harness task. Nem `nesting_engine_v2` adapter,
  nem dual-engine switch, nem v2 result normalizer, nem H3-E4 task.
- A task maradjon a jelenlegi trial tool + worker truth retegen.
- Ne talalj ki uj backend API endpointot, worker specialis benchmark modot,
  vagy uj persisted quality tablat csak a benchmark miatt.
- A smoke/verify ne igenyeljen live platformot; erre `--plan-only`, fake-transport
  vagy synthetic evidence utat hasznalj.

Implementacios elvarasok:
- Keszits determinisztikus benchmark fixture generatort `ezdxf`-fel.
- A generator legalabb ezt a 3 case-et tamogassa:
  - `triangles_rotation_pair`
  - `circles_dense_pack`
  - `lshape_rect_mix`
- A benchmark manifest explicit, repo-local forras legyen.
- A `scripts/trial_run_tool_core.py` futas vegere irj gepileg olvashato
  `quality_summary.json`-t.
- A quality summary legalabb ezeket a jeleket adja vissza, ha az evidence alapjan
  szamolhato:
  - rotation histogram / nonzero rotation count
  - sheets used
  - solver utilization (ha van)
  - occupied extent es coverage ratio (ha van ismert sheet meret)
  - artifact completeness
- A `signals` blokk maradjon evidence-first; ne gyarts belole feketedoboz
  "quality score"-t.
- Keszits benchmark runnert, ami a manifestbol dolgozik es tud `--plan-only` modot.

A task-specifikus smoke bizonyitsa legalabb:
- a fixture generator determinisztikus ugyanarra a case-re;
- a manifest ervenyes es feloldhato;
- a `quality_summary.json` minimum schema stabil;
- a benchmark runner `--plan-only` modban helyes case-plan-t ad;
- nincs live network/API/Supabase fuggoseg a smoke-hoz.

A reportban kulon nevezd meg:
- miert nem eleg a `summary.md` a kovetkezo quality lane taskokhoz;
- milyen benchmark case-ek kerultek be es mit tudnak bizonyitani;
- mely KPI-k evidence-first es melyeket NEM szabad meg vegso quality score-kent
  ertelmezni;
- hogyan kapcsolodik ez a task a kesobbi `v2 adapter` es `dual-engine` A/B
  osszehasonlitasokhoz.

A vegen futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/web_platform/h3_quality_t2_benchmark_pack_and_quality_summary_harness.md`

Eredmeny:
- Frissitsd a checklistet es a reportot evidence-alapon.
- A reportban legyen DoD -> Evidence matrix es korrekt AUTO_VERIFY blokk.
- Add meg a vegleges fajltartalmakat.
