# canvases/nesting_engine/simulated_annealing_search.md

## 🎯 Funkció

F2-4 cél: determinisztikus (fix seed → fix eredmény) **Simulated Annealing** keresés bevezetése, ami a
konstrukciós placer (BLF/NFP) eredményét próbálja javítani.

Kritikus keret:
- SA determinisztikus legyen (PRNG fix seed, totális tie-breakek, stabil schedule).
- Nem törjük a meglévő `nest` CLI viselkedést: SA csak új flaggel aktiválható.
- Nem bővítjük az IO contractot (marad `nesting_engine_v2`).

## 🧠 Fejlesztési részletek

### 1) CLI integráció (minimál invazív)
- `nest` subcommand kap új opciót:
  - `--search none|sa` (default: none)
  - `--sa-iters <N>` (default: determinisztikus N a `time_limit_sec` alapján)
  - `--sa-temp-start <u64>` `--sa-temp-end <u64>` (defaultok fixek)
  - `--sa-eval-time-limit-sec <u64>` (default: clamp(1..=time_limit_sec, time_limit_sec/10))

### 2) Mi az SA állapot (state)
Az SA-hoz *muszáj* legyen order-érzékeny értékelés.

Probléma: a jelenlegi placerek **belsőleg rendeznek** (`nominal_bbox_area` szerint), így a “sorrend” nem változtat semmit.

Megoldás (F2-4 része):
- bevezetünk egy **PartOrderPolicy**-t:
  - `ByArea` (default, jelenlegi viselkedés)
  - `ByInputOrder` (SA módhoz)
- SA evaluation a specifikált input-order szerint futtatja a place-t (nem írja felül a placer belső sort).

Felderites megerosites:
- `blf_place` jelenleg minden futas elejen area szerint rendez (`ordered.sort_by(...)`), ez elnyomja a bemeneti sorrend valtoztatasat.
- `nfp_place` ugyanigy area szerint rendez, ezert SA state-ben az order mutacio onmagaban nem hat.
- `greedy_multi_sheet` minden sheet-roundban ujraepiti a `remaining_specs` listat es tovabbadja a placernek, igy explicit order-policy nelkul a default belso rendezes marad aktiv.
- Kovetkezmeny: SA-hoz kulon `PartOrderPolicy` kell, ahol `ByArea` tartja a mai defaultot, `ByInputOrder` pedig engedi az SA altal javasolt sorrend ervenyesuleset.

### 3) SA motor (Rust, új modul)
Új modulok:
- `rust/nesting_engine/src/search/mod.rs`
- `rust/nesting_engine/src/search/sa.rs`

SA algoritmus (determinista):
- PRNG: saját `SplitMix64` (nincs új crate).
- Neighbor operátorok:
  - `swap(i,j)` (order)
  - `rotate(i)` (a part allowed_rotations egyik eleme; az evaluationnél a rotációt “fixáljuk” úgy, hogy
    az adott instance allowed_rotations_deg listája 1 elemű legyen)
- Acceptance (determinista, float nélküli):
  - ha `delta_cost <= 0` → accept
  - különben `accept_prob = temp / (temp + delta_cost)` (u128 arány), accept ha `rng % denom < num`
- Cooling: lineáris `temp_start → temp_end` N iteráción.

### 4) Evaluation (placer hívás)
- SA minden candidate state-re meghívja az existing place pipeline-t:
  - input: ugyanaz a `bin`, ugyanaz az inflated polygon készlet (pipeline már lefutott)
  - `greedy_multi_sheet(..., order_policy=ByInputOrder, placer_kind=Nfp)` (vagy BLF is opció)
- Cost függvény (lexikografikus, integer):
  1) `sheets_used` (min)
  2) `unplaced_count` (min) — nagy büntetés
  3) `utilization_per_mille` (max) → costba invertálva

### 5) Tesztek / gate (minimum)
- Rust unit test a SA motor determinisztikájára (fake evaluatorral):
  - `sa_core_is_deterministic_fixed_seed` (prefix: `sa_core_`)
- CLI smoke (nem feltétlen gate-be azonnal):
  - reportban bizonyíték: ugyanazzal a seed-del 2× futtatás azonos `determinism_hash`.

### 6) Doksik
- `docs/nesting_engine/architecture.md`:
  - F2-4 SA arch blokk (state, evaluator, determinisztika).

## 🧪 Tesztállapot

### DoD
- [ ] Új `--search sa` útvonal működik, default viselkedést nem töri
- [ ] SA core determinisztikus (unit test: `sa_core_...` PASS)
- [ ] SA fut determinisztikusan fix seed-del (reportban 2× hash egyezés evidenciával)
- [ ] `./scripts/verify.sh --report codex/reports/nesting_engine/simulated_annealing_search.md` PASS

Megjegyzés: “SA javít a konstrukcióhoz képest” bizonyítékhoz valószínűleg kell egy order-érzékeny fixture.
Ha első körben nincs ilyen, a report legyen PASS_WITH_NOTES és következő taskban jön a “quality fixture”.

## 🌍 Lokalizáció
Nem releváns.

## 📎 Kapcsolódások
- `canvases/nesting_engine/nesting_engine_backlog.md` (F2-4 DoD)
- `rust/nesting_engine/src/main.rs`
- `rust/nesting_engine/src/multi_bin/greedy.rs`
- `rust/nesting_engine/src/placement/blf.rs`
- `rust/nesting_engine/src/placement/nfp_placer.rs`
- `docs/nesting_engine/architecture.md`
- meglévő fixture-ek: `poc/nesting_engine/f2_3_f0_sanity_noholes_v2.json` (smoke-hoz)
