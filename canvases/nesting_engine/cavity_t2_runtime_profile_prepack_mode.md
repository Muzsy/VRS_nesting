# Cavity T2 - Runtime profile es prepack policy wiring

## Cel
Vezesd be Python oldalon a `part_in_part=prepack` policy erteket es a
`quality_cavity_prepack` profilt. A workerben csak a policy trace es a Rust CLI
mapping keszuljon: `prepack` eseten worker prepack enabled, engine
`--part-in-part off`. Geometriai packer meg nincs.

## Nem-celok
- Nem cavity geometry packing.
- Nem `cavity_plan.json` artifact persist.
- Nem result normalizer expansion.
- Nem Rust CLI `prepack` tamogatas.
- Nem `quality_default` atallitasa.

## Repo-kontekstus
- `vrs_nesting/config/nesting_quality_profiles.py` a kanonikus quality registry.
- `vrs_nesting/runner/nesting_engine_runner.py` argparse `--part-in-part`
  choices jelenleg `off|auto`.
- `worker/main.py` `_resolve_engine_profile_resolution` es
  `_build_solver_runner_invocation` utvonalon epiti a runner CLI argokat.
- A Rust `PartInPartMode` csak `Off` es `Auto`.

## Erintett fajlok
- `vrs_nesting/config/nesting_quality_profiles.py`
- `worker/main.py`
- `vrs_nesting/runner/nesting_engine_runner.py` csak ha validacio miatt
  szukseges, de Rustnak ne menjen `prepack`.
- `scripts/smoke_cavity_t2_runtime_profile_prepack_mode.py`

## Implementacios lepesek
1. Bovitsd a Python runtime policy validaciot `prepack` ertekkel.
2. Adj hozza `quality_cavity_prepack` profilt:
   `placer=nfp`, `search=sa`, `part_in_part=prepack`, `compaction=slide`.
3. A workerben vezess be audit mezoket:
   requested/effective engine part-in-part, cavity prepack enabled.
4. Biztositsd, hogy a runner/Rust CLI csak `--part-in-part off` erteket kapjon
   prepack policy eseten.
5. Keszits smoke-ot, amely solver futtatas nelkul ellenorzi a mappinget.

## Checklist
- [ ] `quality_cavity_prepack` valid profile.
- [ ] `quality_default` valtozatlan marad.
- [ ] Rust runner nem kap `--part-in-part prepack` argumentumot.
- [ ] Worker trace tartalmazza a prepack enabled/effective mappinget.
- [ ] Nincs geometry packer implementacio.
- [ ] Repo gate reporttal lefutott.

## Tesztterv
- `python3 scripts/smoke_cavity_t2_runtime_profile_prepack_mode.py`
- `python3 scripts/smoke_h3_quality_t7_quality_profiles_and_run_config_integration.py`
- `./scripts/verify.sh --report codex/reports/nesting_engine/cavity_t2_runtime_profile_prepack_mode.md`

## Elfogadasi kriteriumok
- A profile registry es worker mapping egy source of truth elvet kovet.
- Prepack policy mellett a legacy BLF runtime part-in-part ki van kapcsolva.
- Cavity nelkuli futasok CLI argjai visszafele kompatibilisek.

## Rollback
A profile registry es worker mapping diff visszavonhato. Nincs DB migration.

## Kockazatok
- Ha a `prepack` ertek atcsuszik Rust CLI-be, a runner fail-el.
- Ha a trace nem egyertelmu, T4-ben nehez lesz az artifact evidence.

## Vegso reportban kotelezo bizonyitek
- Path/line a profile registry uj modjara.
- Path/line a worker effective CLI mappingre.
- Smoke kimenet, amely igazolja, hogy Rust CLI-be `off` kerul.
