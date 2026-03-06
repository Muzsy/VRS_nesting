# simulated_annealing_search_global_time_limit_guard_p0

## 🎯 Funkció

**P0 fix (F2-4 DoD):** az SA (`--search sa`) útvonal **tartsa be** a bemeneti `time_limit_sec` globális időkorlátot,
ne csak az egyes SA-evaluációk (greedy) `eval_budget_sec` limitjét.

Backlog DoD hivatkozás:
- `canvases/nesting_engine/nesting_engine_backlog.md` → F2-4: *“Time limit betartása: --time-limit sec paraméter kötelező”*

**Probléma (kód alapján):**
- SA evaluation már budget-elt (`eval_budget_sec`), de az SA core iterációszáma (`iters`) nincs globálisan korlátozva,
  így worst-case a teljes futás túlfuthat a `time_limit_sec`-en.

## ✅ Nem cél

- SA minőség/perf tuning, caching optimalizációk.
- Új CLI flag-ek bevezetése, meglévő flag-nevek átnevezése.
- SA CLI end-to-end smoke hozzáadása a `scripts/check.sh`-hoz (ez P1 külön task).
- IO contract módosítása (`nesting_engine_v2` marad).

## 🔎 Érintett fájlok (valós, repo-ban létező)

- `rust/nesting_engine/src/search/sa.rs`
  - `run_sa_core(...)`
  - `run_sa_search_over_specs(...)`
  - `SaSearchConfig`
- `rust/nesting_engine/src/main.rs`
  - `build_sa_search_config(...)`
  - `run_nest(...)` (SA branch)
- Gate:
  - `scripts/check.sh` már futtat: `cargo test ... sa_` (új `sa_` tesztek ide illeszkedjenek)

## 🧠 Megoldási elv (determinista + safety guard)

### 1) Determinisztikus iteráció-cap (elsődleges)
A globális time-limit betartásához **determinista** felső korlátot vezetünk be az SA iterációkra úgy, hogy
worst-case se lehessen túlfutni, ha minden evaluation “kifutja” a saját budgetjét.

Megfigyelés:
- A `run_sa_core` a futás során legalább:
  - **1×** initial evaluation (loop előtt),
  - **iters×** candidate evaluation (minden iterációban),
- A `run_sa_search_over_specs` a végén még:
  - **1×** final greedy placement evaluation (best_state-ből).
Tehát worst-case evaluation hívások száma ~ `iters + 2`.

**Kötelező cap formula (documentálandó a kódban kommentben):**
- `max_evals = floor(time_limit_sec / eval_budget_sec)`
- `max_iters = max_evals.saturating_sub(2)`
- `effective_iters = min(requested_iters, max(1, max_iters))`
  - Megjegyzés: ha extrém kicsi limit miatt `max_iters == 0`, akkor best-effort: `effective_iters = 1`,
    és a safety guard (lásd lent) védi, hogy ne szaladjon el a futás.

**Hol legyen érvényesítve:**
- Defense-in-depth:
  - `main.rs::build_sa_search_config` állítsa be a `SaSearchConfig.time_limit_sec` mezőt, és default iters esetén is használja a cap-et.
  - `sa.rs::run_sa_search_over_specs` újra-clampeli (ha valaha más call-site lenne).

### 2) Safety wall-clock guard (másodlagos)
Az SA core kapjon egy “stop hook” mechanizmust, amit az SA integráció **deadline**-nel használ:

- `deadline = Instant::now() + Duration::from_secs(time_limit_sec)`
- Minden iteráció elején: ha `Instant::now() >= deadline` → break, best-effort best_state megtartásával.

Ezzel akkor is megáll a futás, ha a runtime overhead / scheduler drift miatt a determinista cap ellenére közel kerül a limithez.
Ez megfelel a repo-ban már dokumentált “timeout-bound best-effort” szemléletnek.

## 🧪 Tesztelés

### Új unit tesztek (mind `sa_` prefix, hogy a `scripts/check.sh` futtassa)
1) `sa_iters_are_clamped_by_time_limit_and_eval_budget()`
   - Pure függvény teszt: adott `time_limit_sec`, `eval_budget_sec`, `requested_iters` → elvárt `effective_iters`.
   - Példák:
     - `time_limit=60`, `eval_budget=6`, `requested=256` → `effective_iters=8` (10 eval slot → 8 iters + 2 overhead eval)
     - `time_limit=60`, `eval_budget=1`, `requested=256` → `effective_iters=58`

2) `sa_core_stop_hook_can_short_circuit_before_first_iter()`
   - A stop hook (closure) képes még az első iteráció előtt megállítani a loopot.
   - Assert: `final_state == initial_state` és `best_state == initial_state`.

### Meglévő tesztek frissítése
- A `SaSearchConfig` új mezőt kap (`time_limit_sec`), ezért a meglévő SA tesztekben ezt fel kell venni,
  és olyan értéket adni, hogy ne legyen véletlen clamp (pl. 300 sec).

## ✅ DoD (Definition of Done)

- [ ] `SaSearchConfig` tartalmaz globális `time_limit_sec` mezőt, és ez be van kötve a CLI input `time_limit_sec` mezőjére.
- [ ] `run_sa_search_over_specs` determinisztikusan clampeli az iters-t a fenti “iters+2 eval” formula alapján.
- [ ] `run_sa_core` támogat stop hook-ot (deadline) és best-effort módon korán kilép.
- [ ] Új `sa_` unit tesztek zöldek, és lefutnak a `scripts/check.sh` által (`cargo test ... sa_`).
- [ ] `./scripts/verify.sh --report codex/reports/nesting_engine/simulated_annealing_search_global_time_limit_guard_p0.md` PASS.

## ⚠️ Kockázatok + rollback

Kockázat:
- Ha a wall-clock guard aktiválódik limit közelében, timeout-bound környezetben előfordulhat “best-effort drift”.
  Ez elfogadott a repo policy szerint, de a determinisztika teszteket nem szabad timeout-határ közelében futtatni.

Rollback:
- Revert: `rust/nesting_engine/src/search/sa.rs` + `rust/nesting_engine/src/main.rs` változások.
- A baseline (`--search none`) ág érintetlen marad.