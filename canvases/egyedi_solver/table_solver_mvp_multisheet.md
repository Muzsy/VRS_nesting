# Tablas MVP solver + multi-sheet ciklus

## 🎯 Funkcio
Ez a task a tablas MVP solver alapot es a multi-sheet iteraciot rogzitit, hogy a strip slicing helyett tablaalapu placement pipeline keszulhessen.

## 🧠 Fejlesztesi reszletek
### Scope
- Benne van:
  - Rust solver workspace letrehozas (`rust/vrs_solver`).
  - Instance szintu placement output contract implementalasa.
  - Multi-sheet iteracio es unplaced jeloles.
- Nincs benne:
  - Halado objective/metaheurisztika.
  - UI vagy vizualis preview.
  - Vegleges teljesitmeny optimalizacio.

### Erintett fajlok
- `rust/vrs_solver`
- `NINCS: vrs_nesting/nesting/instances.py`
- `vrs_nesting/runner/vrs_solver_runner.py`
- `codex/codex_checklist/egyedi_solver/table_solver_mvp_multisheet.md`
- `codex/reports/egyedi_solver/table_solver_mvp_multisheet.md`

### DoD
- [ ] Solver ad instance-szintu placement kimenetet.
- [ ] Minden placement in-bounds a tabla geometrian.
- [ ] Multi-sheet ciklus fut, es helyesen kezeli az unplaced elemeket.
- [ ] `PART_NEVER_FITS_STOCK` diagnosztika elerheto.
- [ ] Verify gate zold reporttal.

### Kockazat + mitigacio + rollback
- Kockazat: candidate keresesi ter tul nagy, runtime instabil.
- Mitigacio: deterministic pruning, max candidate limit, idokeret.
- Rollback: solver integracio feature flaggel kapcsolhato, fallback jelenlegi Sparrow flow.

## 🧪 Tesztallapot
- Kotelezo gate: `./scripts/verify.sh --report codex/reports/egyedi_solver/table_solver_mvp_multisheet.md`
- Task-specifikus ellenorzes a vegrehajto runban:
  - Reprodukalt placement azonos seed mellett.
  - Multi-sheet fixture ellenorzes.

## 🌍 Lokalizacio
Nem relevans.

## 📎 Kapcsolodasok
- `codex/reports/egyedi_solver_backlog.md`
- `tmp/egyedi_solver/tablas_optimalizacios_algoritmus_jagua_rs_integracio_reszletes_rendszerleiras.md`
- `tmp/egyedi_solver/mvp_terv_tablas_nesting_fix_w_h_alakos_tabla_alap_a_meglevo_vrs_nesting_repora_epitve.md`
- `docs/codex/overview.md`
- `vrs_nesting/runner/sparrow_runner.py`
- `scripts/check.sh`
