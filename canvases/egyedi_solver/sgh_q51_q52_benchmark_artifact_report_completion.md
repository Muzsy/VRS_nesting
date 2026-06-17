# SGH-Q51-Q52 benchmark artifact report completion

## Cel

A SGH-Q51 es SGH-Q52 benchmark mappakban a mar meglevo input/output/log/summary
artefaktumok melle keszuljon Q47-Q50-hez hasonlo top-level `qXX_report.md`,
valamint SVG/PNG tablatervek minden letezo benchmark outputhoz.

## Nem cel

- Solver benchmark ujrafuttatasbol szarmazo uj eredmeny generalasa.
- Rust, benchmark runner vagy IO contract modositas.
- Meglevo solver output JSON-ok modositas vagy ujrageneralasa.

## Valos repo felderites

- Q51 alatt 4 solver output van: spacing-0 proof, spacing-8 6-big, full276 builder ON/OFF.
- Q52 alatt 8 solver output van: spacing-0 proof, spacing-5/8 bias es builder-only,
  full276 bias/builder-only/off.
- A spacing-0 proof outputok 2 tablat hasznalnak, a tobbi output 3 tablat.

## Feladatlista

- [ ] Goal YAML letrehozasa explicit output listaval.
- [ ] `q51_report.md` es `q52_report.md` letrehozasa a meglevo artefaktumok alapjan.
- [ ] SVG/PNG tablatervek generalasa minden Q51/Q52 outputhoz.
- [ ] Checklist es Codex report kitoltese.
- [ ] Repo gate futtatasa `./scripts/verify.sh --report
  codex/reports/egyedi_solver/sgh_q51_q52_benchmark_artifact_report_completion.md`.

## Kockazat es rollback

- Kockazat: a reportok vagy renderek elternek a summary JSON-oktol. Kezeles:
  csak a meglevo summary/input/output/log fajlokbol szarmazo adatokat hasznalnak.
- Rollback: az uj `q51_report.md`, `q52_report.md`, `renders/` alkonyvtarak,
  valamint a jelen canvas/YAML/checklist/report fajlok torlese visszaallitja az
  elozo allapotot.

## Teszt terv

- `python3 scripts/render_sgh_q51_q52_benchmark_artifacts.py`
- `./scripts/verify.sh --report
  codex/reports/egyedi_solver/sgh_q51_q52_benchmark_artifact_report_completion.md`
