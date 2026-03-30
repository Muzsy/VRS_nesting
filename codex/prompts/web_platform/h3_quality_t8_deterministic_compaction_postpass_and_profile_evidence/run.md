# DXF Nesting Platform Codex Task - H3-Quality-T8 deterministic compaction post-pass es profile evidence
TASK_SLUG: h3_quality_t8_deterministic_compaction_postpass_and_profile_evidence

Olvasd el:
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `docs/nesting_quality/nesting_quality_konkret_feladatok.md`
- `vrs_nesting/config/nesting_quality_profiles.py`
- `api/services/run_snapshot_builder.py`
- `rust/nesting_engine/src/main.rs`
- `rust/nesting_engine/src/multi_bin/greedy.rs`
- `rust/nesting_engine/src/placement/blf.rs`
- `rust/nesting_engine/src/export/output_v2.rs`
- `scripts/trial_run_tool_core.py`
- `scripts/run_h3_quality_benchmark.py`
- `docs/nesting_engine/architecture.md`
- `docs/nesting_engine/io_contract_v2.md`
- `docs/nesting_quality/h3_quality_benchmark_harness.md`
- `scripts/check.sh`
- `canvases/web_platform/h3_quality_t8_deterministic_compaction_postpass_and_profile_evidence.md`
- `codex/goals/canvases/web_platform/fill_canvas_h3_quality_t8_deterministic_compaction_postpass_and_profile_evidence.yaml`

Hajtsd vegre a YAML `steps` lepeseit sorrendben.

Kotelezo szabalyok:
- Csak olyan fajlt hozhatsz letre vagy modosithatsz, ami szerepel valamelyik
  YAML step `outputs` listajaban.
- Ez a task nem migration, nem REST schema es nem UI rollout.
- A cel az elso valodi quality uplift T7 utan, nem uj domain reteg.
- A compaction legyen minimal-invaziv post-pass: ne valtoztasson sheetet,
  rotaciot, part sorrendet, placed/unplaced allapotot.
- A feasibility igazsagforras a meglvo `can_place` ut legyen; ne vezess be uj,
  lazabb geometriai shortcutot.
- Ne hasznalj uj random vagy float tie-breaket. A compaction integer-only es
  determinisztikus legyen.
- A determinism hash contractot tilos megvaltoztatni. Az output placementjei
  valtozhatnak determinisztikusan, de a hash tovabbra is a placement canonical
  view-bol epuljon, ne a compaction meta-bol.

Implementacios elvarasok:
- A quality-profile registry kapjon uj `compaction` runtime dimenziot (`off|slide`).
- A snapshot `nesting_engine_runtime_policy` blokk explicit hordozza a compaction modot.
- A Rust CLI tudja a `--compaction off|slide` kapcsolot, default `off`-fal.
- A compaction post-pass a placement eredmenyen fusson, ne uj constructive algo legyen.
- A post-pass csak monoton balra/le mozgasokat csinaljon, es csak akkor, ha a
  mozgas a meglvo feasibility ut alapjan ervenyes.
- Adj additive compaction evidence-t a v2 outputhoz.
- A local quality summary es benchmark compare tegye gepileg olvashatova a
  remnant/extent/compaction kulonbsegeket.
- Keszits kis repo fixture-t es dedikalt smoke-ot a bizonyitashoz.

Targeted minimum bizonyitas:
- `cargo test --manifest-path rust/nesting_engine/Cargo.toml compaction_`
- `python3 scripts/smoke_h3_quality_t8_deterministic_compaction_postpass_and_profile_evidence.py`

A reportban kulon nevezd meg:
- miert most a compaction a legkisebb, de mar valodi quality uplift;
- hogyan mukodik a `compaction off|slide` policy;
- miert marad a megoldas post-pass es nem full local search;
- milyen fixture es smoke bizonyitja a javulast;
- hogyan jelent meg a compaction evidence a quality summary / benchmark outputban.

A vegen futtasd a standard gate-et:
- `./scripts/verify.sh --report codex/reports/web_platform/h3_quality_t8_deterministic_compaction_postpass_and_profile_evidence.md`

Eredmeny:
- Frissitsd a checklistet es a reportot evidence-alapon.
- A reportban legyen DoD -> Evidence matrix es korrekt AUTO_VERIFY blokk.
- Add meg a vegleges fajltartalmakat.
