# simulated_annealing_search_sa_core_mvp

## 🎯 Funkció

**Cél:** az F2-4 SA (Simulated Annealing) bevezetésének első, izolált lépése:  
egy **determinista SA core motor** implementálása Rustban, unit teszttel bizonyítva.

Ez a task **nem** köt SA-t a placerhez/CLI-hez. Csak a motor készül el úgy, hogy a későbbi evaluator
(placer hívás) rá tudjon ülni.

Scope megerosites:
- A wiring ebben a taskban csak annyi, hogy a `search` modul forduljon (`mod search;`).
- Nincs `--search sa` CLI flag, nincs placer evaluator bekotes, nincs output/contract valtozas.

Determinism követelmény:
- fix seed → bit-azonos SA döntéssor → bit-azonos best state
- **float tiltás** az acceptance-ben (integer arányos accept)

## 🧠 Fejlesztési részletek

### Kimenet (új modulok)
- `rust/nesting_engine/src/search/mod.rs`
- `rust/nesting_engine/src/search/sa.rs`

### SA core elv (MVP, determinista)
- PRNG: saját `SplitMix64` (nincs új crate)
- State: minimum
  - `order: Vec<usize>` (permutation)
  - `rot_choice: Vec<u8>` (instance-enként rotáció választás index)
- Neighborhood:
  - `swap(i, j)` (order permutáció)
  - `rotate(k)` (rot_choice[k] ciklikus léptetés, ha >1 opció van)
- Acceptance (integer):
  - ha `delta <= 0` → accept
  - különben `accept_prob = temp / (temp + delta)` (u128 arány)
  - accept ha `(rng % denom) < num`
- Cooling: lineáris `temp_start → temp_end` `iters` lépésen

### Wiring (minimális)
- `rust/nesting_engine/src/main.rs` kapjon `mod search;` deklarációt, hogy a modul forduljon és a tesztek fussanak.
- A motor API-ja legyen olyan, hogy később a CLI taskban egyszerűen rá lehessen kötni az evaluatorra.

## 🧪 Tesztállapot

### DoD
- [ ] `sa_core_is_deterministic_fixed_seed` unit teszt elkészül és PASS
- [ ] `cargo test --manifest-path rust/nesting_engine/Cargo.toml` PASS
- [ ] `./scripts/verify.sh --report codex/reports/nesting_engine/simulated_annealing_search_sa_core_mvp.md` PASS
- [ ] Report Standard v2: AUTO_VERIFY blokk kitöltve + `.verify.log` elmentve

## 🌍 Lokalizáció
Nem releváns.

## 📎 Kapcsolódások
- F2-4 backlog: `canvases/nesting_engine/nesting_engine_backlog.md` (F2-4)
- F2-4 fő canvas: `canvases/nesting_engine/simulated_annealing_search.md` (SA motor szekció)
- Érintett kód:
  - `rust/nesting_engine/src/main.rs`
  - `rust/nesting_engine/src/search/mod.rs`
  - `rust/nesting_engine/src/search/sa.rs`
