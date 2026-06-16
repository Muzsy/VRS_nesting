# SGH-Q47-Q50 benchmark artifact report completion

## Cel

A SGH-Q47, SGH-Q48, SGH-Q49 es SGH-Q50 benchmark mappakban a mar meglevo
input/output/log/summary artefaktumok melle keszuljon Q42-szeru, top-level
`qXX_report.md` osszefoglalo.

## Nem cel

- Benchmark ujrafuttatas vagy solver output ujrageneralas.
- Rust, Python benchmark runner vagy IO contract modositas.
- Solver benchmark ujrafuttatasbol szarmazo uj eredmeny generalasa.

## Valos repo felderites

- Q42 minta: `artifacts/benchmarks/sgh_q42/q42_report.md`,
  `q42_summary.json`, `inputs/`, `outputs/`, `logs/`, `renders/`.
- Q47-Q50 alatt mar leteznek a benchmark inputok, solver output JSON-ok, logok
  es summary JSON-ok.
- A hianyzo paritas a benchmark mappan beluli emberi olvasasu report fajl.

## Feladatlista

- [ ] Goal YAML letrehozasa explicit output listaval.
- [ ] `q47_report.md`, `q48_report.md`, `q49_report.md`, `q50_report.md`
  letrehozasa a meglevo artefaktumok alapjan.
- [ ] SVG/PNG tablatervek generalasa Q47-Q50 A/B outputokra a meglevo solver
  output JSON-okbol es input geometriakbol.
- [ ] Checklist es Codex report kitoltese.
- [ ] Repo gate futtatasa `./scripts/verify.sh --report
  codex/reports/egyedi_solver/sgh_q47_q50_benchmark_artifact_report_completion.md`.

## Kockazat es rollback

- Kockazat: a reportok vagy renderek elternek a summary JSON-oktol. Kezeles:
  csak a meglevo summary/input/output/log fajlokbol szarmazo adatokat
  tartalmaznak, uj merest nem allitanak.
- Rollback: az uj `q47_report.md` ... `q50_report.md`, valamint a jelen
  canvas/YAML/checklist/report fajlok torlese visszaallitja az elozo allapotot.

## Teszt terv

- `./scripts/verify.sh --report
  codex/reports/egyedi_solver/sgh_q47_q50_benchmark_artifact_report_completion.md`
