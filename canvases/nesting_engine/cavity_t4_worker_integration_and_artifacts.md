# Cavity T4 - Worker integracio es cavity_plan artifact

## Cel
Kossd be a T3 prepack modult a worker `nesting_engine_v2` input eloallitas utan.
Prepack policy eseten a worker a prepackelt `solver_input_snapshot.json`-t irja,
melle `cavity_plan.json` sidecart persistaljon es artifactkent regisztraljon.

## Nem-celok
- Nem cavity packer algoritmus fejlesztese.
- Nem result normalizer expansion, csak crash elkerules ha szukseges.
- Nem export/UI.
- Nem Rust engine modositas.

## Repo-kontekstus
- `worker/main.py` jelenleg a base solver inputot `input_dir /
  solver_input_snapshot.json` pathra irja es `solver_input` artifactkent
  regisztralja.
- `persist_raw_output_artifacts` a runner output run_dirbol persistal raw
  artifactokat.
- `engine_meta.json` mar tartalmaz backend/profile truth mezoket.
- T2 utan a worker tudja, mikor `cavity_prepack_enabled`.

## Erintett fajlok
- `worker/main.py`
- `worker/cavity_prepack.py` csak import/API illesztes erejeig.
- `worker/raw_output_artifacts.py` csak ha a real artifact persist pattern ezt
  igenyli.
- `scripts/smoke_cavity_t4_worker_integration_and_artifacts.py`

## Implementacios lepesek
1. A base `build_nesting_engine_input_from_snapshot` utan hivd meg a T3 modult
   prepack policy eseten.
2. A solver input hash a tenylegesen futtatott prepackelt payloadbol keszuljon.
3. Ird ki `input_dir/cavity_plan.json` fajlt es uploadold
   `runs/<run_id>/inputs/cavity_plan.json` storage keyre.
4. Regisztralj `artifact_type=cavity_plan` vagy a repo legacy metadata
   kompatibilis megfelelojet.
5. Logolj es engine_meta-ba vagy metrics metadata-ba tegyel audit mezoket:
   enabled, virtual parent count, internal placements count, removed holes count.
6. Legacy/non-prepack modban a solver input es artifact viselkedes maradjon
   valtozatlan, legfeljebb disabled plan artifact ha a contract ezt keri.

## Checklist
- [ ] Prepack policy eseten `cavity_plan.json` letrejon.
- [ ] Solver input snapshot a futtatott prepackelt payload.
- [ ] Artifact rekordbol a cavity plan visszakeresheto.
- [ ] Engine CLI `--part-in-part off` marad prepack mellett.
- [ ] Non-prepack futas regresszio nelkul mukodik.
- [ ] Repo gate reporttal lefutott.

## Tesztterv
- `python3 scripts/smoke_cavity_t4_worker_integration_and_artifacts.py`
- `python3 scripts/smoke_h1_e5_t1_engine_adapter_input_mapping_h1_minimum.py`
- `python3 scripts/smoke_h1_e5_t2_solver_process_futtatas_h1_minimum.py`
- `./scripts/verify.sh --report codex/reports/nesting_engine/cavity_t4_worker_integration_and_artifacts.md`

## Elfogadasi kriteriumok
- A run artifactok kozott latszik a cavity plan.
- A solver inputban prepackelt parentek holes nelkul mennek tovabb.
- A futas reprodukalhato `solver_input_snapshot.json` + `cavity_plan.json`
  parossal.

## Rollback
Worker integracio es artifact persist diff visszavonhato; T3 modul onmagaban
megmaradhat vagy kulon revertelheto.

## Kockazatok
- A hash a base inputbol szamolodik, mikozben a runner prepackelt payloadot futtat.
- Artifact bucket/path mismatch ujra letoltesi hibat okozhat.

## Vegso reportban kotelezo bizonyitek
- Path/line a prepack call site-ra.
- Path/line a cavity_plan upload es artifact registration reszre.
- Smoke output a tenyleges input/artifact parossal.
