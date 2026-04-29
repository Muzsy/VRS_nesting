# DXF Nesting Platform Codex Task - Cavity T2 runtime profile prepack mode
TASK_SLUG: cavity_t2_runtime_profile_prepack_mode

## Szerep
Senior coding agent vagy. Runtime policy wiringet vegzel, nem geometriat
packelsz.

## Cel
Add hozza Python oldalon a `part_in_part=prepack` policyt es a
`quality_cavity_prepack` profilt. Prepack modban a worker trace jelezze a
prepack engedelyezeset, a Rust runner pedig csak `--part-in-part off` erteket
kapjon.

## Olvasd el eloszor
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `docs/nesting_quality/cavity_prepack_quality_policy.md`, ha T1 mar lefutott
- `vrs_nesting/config/nesting_quality_profiles.py`
- `worker/main.py`
- `vrs_nesting/runner/nesting_engine_runner.py`
- `rust/nesting_engine/src/main.rs`
- `rust/nesting_engine/src/multi_bin/greedy.rs`
- `canvases/nesting_engine/cavity_t2_runtime_profile_prepack_mode.md`
- `codex/goals/canvases/nesting_engine/fill_canvas_cavity_t2_runtime_profile_prepack_mode.yaml`

## Engedelyezett modositas
Csak a YAML `outputs` listaja. Ne nyulj `worker/cavity_prepack.py`-hoz es ne
modosits Rust CLI parseren `prepack` tamogatasert.

## Szigoru tiltasok
- `quality_default` nem valtozhat.
- Rust subprocess nem kaphat `--part-in-part prepack` argumentumot.
- Prepack es legacy BLF part-in-part nem lehet egyszerre enabled.
- Nincs geometry packer.

## Elvart parancsok
- `python3 scripts/smoke_cavity_t2_runtime_profile_prepack_mode.py`
- `python3 scripts/smoke_h3_quality_t7_quality_profiles_and_run_config_integration.py`
- `./scripts/verify.sh --report codex/reports/nesting_engine/cavity_t2_runtime_profile_prepack_mode.md`

## Stop conditions
Allj meg, ha a policy mapping csak Rust CLI bovites mellett lenne megoldhato,
vagy ha a workerben nincs egyertelmu hely a requested/effective mapping
audit mezoknek.

## Report nyelve es formatuma
A report magyarul keszuljon. Evidence-ben szerepeljen a profile registry,
worker mapping, runner CLI output es a smoke eredmeny.
