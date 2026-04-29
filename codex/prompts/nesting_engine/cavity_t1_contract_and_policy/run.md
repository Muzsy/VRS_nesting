# DXF Nesting Platform Codex Task - Cavity T1 contract es policy
TASK_SLUG: cavity_t1_contract_and_policy

## Szerep
Senior coding agent vagy. Ez contract/documentation task; implementacios kodot
nem irsz, kiveve ha a repo pattern minimalis dokumentacios scaffoldingot igenyel.

## Cel
Dokumentald a `cavity_plan_v1` szerzodest es a `part_in_part=prepack` worker
policy jelentest ugy, hogy a kovetkezo agentek biztonsagosan implementalhassak
a feature-t.

## Olvasd el eloszor
- `AGENTS.md`
- `docs/codex/overview.md`
- `docs/codex/yaml_schema.md`
- `docs/codex/report_standard.md`
- `docs/qa/testing_guidelines.md`
- `tmp/plans/cavity_first_composite_nesting_fejlesztesi_terv.md`
- `codex/reports/nesting_engine/otszog_bodypad_runtime_root_cause_20260428.md`
- `docs/nesting_engine/io_contract_v2.md`
- `vrs_nesting/config/nesting_quality_profiles.py`
- `vrs_nesting/runner/nesting_engine_runner.py`
- `rust/nesting_engine/src/main.rs`
- `canvases/nesting_engine/cavity_t1_contract_and_policy.md`
- `codex/goals/canvases/nesting_engine/fill_canvas_cavity_t1_contract_and_policy.yaml`

## Engedelyezett modositas
Csak a YAML `outputs` listajaban szereplo dokumentacios es report fajlok.
Ne irj `worker/cavity_prepack.py`-t, ne modosits runtime kodot.

## Szigoru tiltasok
- Ne allitsd, hogy full hole-aware NFP keszul.
- Ne vezesd be a `prepack` Rust CLI erteket.
- Ne allitsd at a `quality_default` profilt.
- Ne hagyj homalyos quantity/instance accounting szabalyokat.

## Elvart ellenorzes
- Dokumentacio pathok es linkek valosak.
- `./scripts/verify.sh --report codex/reports/nesting_engine/cavity_t1_contract_and_policy.md`

## Stop conditions
Allj meg es FAIL reportot irj, ha a jelenlegi IO contract vagy quality profile
allapot nem egyeztetheto ossze a javasolt contracttal kulon dontes nelkul.

## Report nyelve es formatuma
A report magyarul keszuljon. Kulon nevezd meg: nincs implementacios kod; hol
van dokumentalva a schema; hol van dokumentalva a worker prepack vs legacy
engine part-in-part elvalasztas.
