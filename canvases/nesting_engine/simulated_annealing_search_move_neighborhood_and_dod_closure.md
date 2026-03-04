# simulated_annealing_search_move_neighborhood_and_dod_closure

## 🎯 Funkció

**Cél (F2-4 lezárás):**
1) Az SA neighborhood bővítése **move/relocate** operátorral (swap, move, rotate teljes).
2) Bizonyító `sa_` unit teszt a move operátorra (perm. invariáns).
3) A backlog szerinti **fő F2-4 report** elkészítése és verify-olása:
   - `codex/reports/nesting_engine/simulated_annealing_search.md`

**Nem cél:**
- Caching / incremental eval / perf tuning (külön task).
- SA paraméter tuning “általános” minőségre.
- IO contract módosítás.

## 🧠 Fejlesztési részletek

### Move (relocate) operátor
- Érintett fájl: `rust/nesting_engine/src/search/sa.rs`
- Implementáld: `apply_move(state, rng)`:
  - válassz `from` és `to` indexet (`from != to`)
  - vedd ki az elemet `from`-ról és szúrd be `to`-ra
  - garantáltan változtasson a sorrenden (n>=2 esetén)
- `apply_neighbor(...)` válasszon a **swap / move / rotate** közül determinisztikusan (PRNG alapján), pl. egyenletes vagy enyhén swap-favor.

### Determinizmus
- A move operátor tisztán integer index-manipuláció, PRNG ugyanaz (SplitMix64).
- Nem érint `rot_choice`-t.

### F2-4 fő report (összefoglaló, DoD closure)
- Új checklist + report:
  - `codex/codex_checklist/nesting_engine/simulated_annealing_search.md`
  - `codex/reports/nesting_engine/simulated_annealing_search.md`
- A záró verify parancs célreportja is ez:
  - `./scripts/verify.sh --report codex/reports/nesting_engine/simulated_annealing_search.md`
- A reportban legyen DoD → Evidence Matrix, ahol explicit hivatkozod:
  - determinisztika teszt: `sa_core_is_deterministic_fixed_seed`
  - SA determinisztika integráció: `sa_search_is_deterministic_tiny_blf_case`
  - javulás: `sa_quality_fixture_improves_sheets_used` + fixture JSON + CLI parancsok
  - time limit/budget: `main.rs::build_sa_search_config` + `sa.rs::ensure_sa_stop_mode`
  - neighborhood: `sa.rs::apply_neighbor` (swap/move/rotate)

## 🧪 Tesztállapot

### DoD
- [ ] `apply_move` implementálva és bekötve `apply_neighbor`-be
- [ ] Új `sa_` unit teszt: `sa_move_neighbor_preserves_permutation` PASS
- [ ] `cargo test --manifest-path rust/nesting_engine/Cargo.toml sa_` PASS (verify logban látszik)
- [ ] F2-4 fő report + checklist elkészült (Report Standard v2 + AUTO_VERIFY + `.verify.log`)
- [ ] `./scripts/verify.sh --report codex/reports/nesting_engine/simulated_annealing_search.md` PASS

## 🌍 Lokalizáció
Nem releváns.

## 📎 Kapcsolódások
- Backlog: `canvases/nesting_engine/nesting_engine_backlog.md` (F2-4)
- SA core: `canvases/nesting_engine/simulated_annealing_search_sa_core_mvp.md`
- CLI+evaluator: `canvases/nesting_engine/simulated_annealing_search_cli_and_evaluator_integration.md`
- Quality fixture: `canvases/nesting_engine/simulated_annealing_search_quality_fixture_benchmark.md`
- Érintett kód:
  - `rust/nesting_engine/src/search/sa.rs`
