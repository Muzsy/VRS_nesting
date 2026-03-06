# simulated_annealing_search_global_time_limit_hard_cap_p0

## 🎯 Funkció

**P0 follow-up fix (F2-4 DoD closure):**
a `--search sa` útvonal globális `time_limit_sec` korlátját **hard módon** kell betartani, ne csak best-effort jelleggel.

Ez a task a korábbi
`simulated_annealing_search_global_time_limit_guard_p0`
javítás lezárása.

## Miért kell ez?

A jelenlegi megoldás már tartalmaz:

- `time_limit_sec` mezőt a `SaSearchConfig`-ban,
- iter clamp-et,
- wall-clock stop hook-ot.

Viszont a kód alapján még maradt egy korrektness rés:

1. az iter clamp minimum 1 iterációt kényszerít,
2. az SA futás végén van egy külön final greedy evaluation is,

ezért a teljes futás evaluation-száma még mindig túllépheti a globális időkeretet kis limiteknél.

## ✅ Nem cél

- SA minőségjavítás / tuning
- új CLI flag-ek
- SA CLI smoke a gate-ben
- dokumentációs általános rendrakás
- incremental evaluator/cache optimalizálás

## 🔎 Érintett fájlok

- `rust/nesting_engine/src/search/sa.rs`
- `codex/codex_checklist/nesting_engine/simulated_annealing_search_global_time_limit_hard_cap_p0.md`
- `codex/reports/nesting_engine/simulated_annealing_search_global_time_limit_hard_cap_p0.md`

Nem kötelező `main.rs` módosítás, ha a fix teljesen megoldható `sa.rs`-ben.

## 🧠 Megoldási elv

### 1) A hard budget alapja
A teljes SA keresés worst-case evaluation-számát úgy kell kialakítani, hogy a globális budgetből biztosan kijöjjön.

A helyes modell:

- legyen `max_evals = floor(time_limit_sec / eval_budget_sec)`
- az SA eredmény előállításához **nem szabad külön final greedy rerun-t** igényelni
- ezért a teljes search worst-case evaluation-száma:
  - `1` initial evaluation
  - `iters` candidate evaluation

Tehát:
- `max_iters = max_evals.saturating_sub(1)`
- `effective_iters = min(requested_iters, max_iters)`

**Fontos:** itt **0 iteráció megengedett és szükséges**.

### 2) Final greedy rerun megszüntetése
A jelenlegi `run_sa_search_over_specs(...)` a `best_state` végén újra meghívja a placert.
Ezt meg kell szüntetni.

Helyette:
- az evaluator ne csak costot számoljon,
- hanem adja vissza / tegye eltárolhatóvá a hozzá tartozó `MultiSheetResult` + `Option<NfpPlacerStatsV1>` eredményt is,
- és a search a **best already-evaluated resultot** adja vissza.

Így nem kell extra final evaluation.

### 3) Stop hook megtartása
A wall-clock deadline guard maradjon meg defense-in-depth célra.

## 🧪 Tesztelés

### Új `sa_` unit tesztek
1. `sa_iters_clamp_allows_zero_when_only_initial_eval_fits`
   - Példa:
     - `time_limit=1`, `eval_budget=1`, `requested=256` → `effective_iters=0`
     - `time_limit=2`, `eval_budget=1`, `requested=256` → `effective_iters=1`

2. `sa_search_zero_iter_budget_returns_initial_eval_result`
   - Olyan konfigurációval, ahol csak az initial evaluation fér bele.
   - Assert:
     - a függvény nem hibázik,
     - érvényes eredményt ad vissza,
     - nincs szükség extra final rerunra.

3. `sa_search_reuses_best_evaluated_result_without_final_rerun`
   - Közvetett bizonyítás:
     - számláld az evaluator hívásokat,
     - ellenőrizd, hogy total eval count = `1 + effective_iters`, nem több.

### Meglévő tesztek
- a korábbi `sa_` tesztek maradjanak zöldek.

## ✅ DoD

- [ ] Az SA iters clamp megengedi a `0` iterációt.
- [ ] A `run_sa_search_over_specs(...)` nem futtat extra final greedy evaluationt a search végén.
- [ ] A search a már kiértékelt best eredményt reuse-olja visszatéréskor.
- [ ] Új `sa_` tesztek bizonyítják a hard budget logikát.
- [ ] `./scripts/verify.sh --report codex/reports/nesting_engine/simulated_annealing_search_global_time_limit_hard_cap_p0.md` PASS.

## ⚠️ Kockázatok + rollback

Kockázat:
- az evaluator eredmény reuse miatt a `sa.rs` belső struktúrái bonyolultabbak lesznek;
  figyelni kell arra, hogy determinisztikusan ugyanaz az eredmény maradjon kiválasztva tie esetén.

Rollback:
- kizárólag `rust/nesting_engine/src/search/sa.rs` revert.
- baseline és CLI flag-ek érintetlenek maradnak.