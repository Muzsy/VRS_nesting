# Cavity T8 - Production regression benchmark es rollout dontes

## Cel
A T0-T7 utan jatszd vissza a korabbi hibas production/trial solver inputot
legacy es `quality_cavity_prepack` modban, hasonlitsd ossze a fallbacket,
placed/unplaced countokat, elapsed idot es profile telemetryt. A task vegere
rollout dontesi bizonyitek keszuljon; `quality_default` atallitasa csak kulon
dontessel tortenhet.

## Nem-celok
- Nem core logic implementacio.
- Nem gyors timeout/work_budget tuning.
- Nem warning suppression.
- Nem `quality_default` automatikus atallitasa.
- Nem production adat talalgatasa, ha artifact tovabbra sem elerheto.

## Repo-kontekstus
- T0 adja a letoltheto production `solver_input`/`engine_meta` baseline-t.
- T2 adja a `quality_cavity_prepack` profilt.
- T3-T5 adja a prepackelt inputot es normalizalt projectiont.
- `scripts/run_h3_quality_benchmark.py` mar letezo benchmark harness.
- A root-cause report szerint konkret nevcsoport mapping csak akkor bizonyithato,
  ha a production snapshot letoltheto.

## Erintett fajlok
- `scripts/run_h3_quality_benchmark.py` csak ha cavity mode matrixhoz minimalisan
  boviteni kell.
- `scripts/smoke_cavity_t8_production_regression_benchmark.py`
- `docs/nesting_quality/cavity_prepack_rollout_decision.md`
- `tmp/` alatti letoltott/replay artifactok csak futasi evidence, ne commitold.

## Implementacios lepesek
1. Olvasd be T0 baseline reportjat es a production snapshot pathot.
2. Futtasd legacy modot `part_in_part=auto` vagy a baseline szerinti policyvel.
3. Futtasd `quality_cavity_prepack` modot.
4. Gyujtsd ki: effective placer, fallback warning, nfp stats,
   placed/unplaced count, reasons, elapsed time, BLF/SA profilek.
5. Hasonlitsd ossze part_code csoportok szerint csak akkor, ha a snapshot ezt
   bizonyitja.
6. Ird meg a rollout decision doksit: maradjon kulon profile, vagy kulon taskban
   javasolhato-e `quality_default`.

## Checklist
- [ ] Legacy replay bizonyitott vagy blokkolt allapot explicit.
- [ ] Prepack replay bizonyitott ugyanarra vagy synthetic fallback snapshotra.
- [ ] Nincs globalis BLF fallback prepack modban parent hole miatt.
- [ ] Unplaced okok es countok osszehasonlitva.
- [ ] Rollout dontes nem allit tobbet a bizonyiteknal.
- [ ] Repo gate reporttal lefutott.

## Tesztterv
- `python3 scripts/smoke_cavity_t8_production_regression_benchmark.py`
- Ha relevans: `python3 scripts/run_h3_quality_benchmark.py --plan-only ...`
- Celzott Rust replay commandok `NESTING_ENGINE_EMIT_NFP_STATS=1` mellett.
- `./scripts/verify.sh --report codex/reports/nesting_engine/cavity_t8_production_regression_benchmark.md`

## Elfogadasi kriteriumok
- A reportban legacy vs prepack evidence tablazat van.
- A `quality_default` nem valtozik ebben a taskban.
- Ha production replay nem elerheto, a task FAIL vagy PASS_WITH_NOTES statuszban
  pontosan megnevezi a blokkolot.

## Rollback
Benchmark/doksi/smoke diff visszavonhato. Core logic valtoztatasa tilos; ha
regresszio derul ki, uj fix taskot kell nyitni T2-T6 megfelelo retegre.

## Kockazatok
- Production artifact hozzaferes tovabbra is kulso blokkoloba utkozik.
- Timeout-bound futasoknal determinism hash nem elegendo regresszio bizonyitek.

## Vegso reportban kotelezo bizonyitek
- Legacy es prepack parancsok exit code-dal.
- Telemetry osszehasonlitas: effective placer, fallback, placed/unplaced,
  elapsed, NFP/BLF/SA stats.
- Rollout javaslat bizonyitekhoz kotve.
