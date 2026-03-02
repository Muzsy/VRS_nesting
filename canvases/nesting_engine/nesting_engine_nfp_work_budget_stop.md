# canvases/nesting_engine/nesting_engine_nfp_work_budget_stop.md

## 🎯 Funkció

A cél: a `--placer nfp` útvonal time_limit stopja is legyen **determinista**.

Jelenleg:
- `rust/nesting_engine/src/placement/nfp_placer.rs::nfp_place` wall-clock ellenőrzést használ (`started_at.elapsed().as_secs() >= time_limit_sec`).
- Ez timeout-határ közelében ugyanúgy driftet okozhat, mint BLF-nél.

Feladat:
- a NFP placer kapjon `StopPolicy`-t (ugyanazt a típust, amit BLF már használ),
- work_budget módban a leállás **műveletszám** alapon történjen (determinista),
- wall_clock módban a jelenlegi viselkedés megmaradhat.

Nem cél:
- algoritmus / CFR / candidate policy változtatás.
- IO contract bővítése.
- perf tuning (csak stop mechanizmus és determinisztika).

## 🧠 Fejlesztési részletek

### 1) API/szignatúra változtatás
- `rust/nesting_engine/src/placement/nfp_placer.rs::nfp_place`
  - jelenleg: `(…, time_limit_sec: u64, started_at: Instant, …)`
  - legyen: `(…, stop: &mut StopPolicy, …)`
- `rust/nesting_engine/src/multi_bin/greedy.rs`
  - NFP ágban a `nfp_place` hívás `time_limit_sec/started_at` helyett `&mut stop`-ot adjon át.

### 2) Hol fogy a work-budget (determinista pontok)
Work_budget módban legyen `stop.consume(1)` a következő, stabil pontokon:
- part instance loop elején (minden példány kísérlet)
- CFR compute előtt (egy consume / CFR)
- candidate loopban, minden `can_place` próbálkozás előtt (egy consume / candidate)
- (opcionális) NFP compute miss ágban (egy consume / compute), ha nagyon finomítani akarod

### 3) Timeout kezelése NFP placerben
Ha `stop.should_stop()` vagy `stop.consume(...)` triggerel:
- `stop.mark_timed_out()` (ha még nem timed_out)
- a current és remaining instance-ek `UnplacedItem.reason = "TIME_LIMIT_EXCEEDED"`
- a függvény térjen vissza determinisztikusan a már elhelyezettekkel + unplaced listával.

### 4) Unit teszt (gyors, determinisztikus)
Fájl: `rust/nesting_engine/src/placement/nfp_placer.rs` (tests)

Új teszt:
- `nfp_budget_stop_is_deterministic` (prefix: `nfp_budget_`)
  - ugyanazzal a bemenettel 2× futtatás
  - `StopPolicy::work_budget_for_test(...)` alacsony budgettel, hogy biztosan stop legyen
  - assert: placed/unplaced struktúra megegyezik (vagy determinism_hash megegyezik, ha van helper)

### 5) Gate
`scripts/check.sh` nesting_engine blokk:
- `cargo test --manifest-path rust/nesting_engine/Cargo.toml nfp_budget_`

### 6) Doksi (kicsi)
`docs/nesting_engine/architecture.md`:
- jelezd, hogy a work_budget stop már BLF **és NFP** útvonalon is érvényes.

## 🧪 Tesztállapot

### DoD
- [x] `nfp_place` `StopPolicy`-t kap és nem használ közvetlen wall-clock time_limit checket
- [x] Work_budget módban determinisztikus consume pontok vannak a NFP placerben
- [x] Új unit teszt zöld: `nfp_budget_stop_is_deterministic`
- [x] `scripts/check.sh` futtatja a `nfp_budget_` célzott tesztet
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_nfp_work_budget_stop.md` PASS

## 🌍 Lokalizáció
Nem releváns.

## 📎 Kapcsolódások
- `rust/nesting_engine/src/multi_bin/greedy.rs` (NFP dispatch + StopPolicy)
- `rust/nesting_engine/src/placement/nfp_placer.rs::nfp_place`
- `rust/nesting_engine/src/placement/blf.rs` (már StopPolicy-s minta)
- `docs/nesting_engine/architecture.md`
- `scripts/check.sh`

## Felderítési snapshot (2026-03-02)

- A `nfp_place` jelenlegi szignatúrája még `time_limit_sec: u64, started_at: Instant` paramétereket használ
  (`rust/nesting_engine/src/placement/nfp_placer.rs`), és több ponton közvetlen
  `started_at.elapsed().as_secs() >= time_limit_sec` check van.
- A fő wall-clock check helyek:
  - instance loop eleje,
  - `all_candidates.is_empty()` ág reason kiválasztása,
  - candidate loop belső `break`,
  - `!placed_this_instance` ág reason kiválasztása.
- A `greedy_multi_sheet` már `StopPolicy`-t épít (`StopPolicy::from_env(...)`), de NFP hívásnál még
  a régi `time_limit_sec/started_at` paramétereket adja át.
- A BLF útvonal mintaként már `&mut StopPolicy`-t használ és deterministic `consume(1)` kapukat futtat
  a belső keresési ciklusokban.
- Tervezett átvezetés:
  - `nfp_place(..., stop: &mut StopPolicy, ...)` szignatúra,
  - `greedy.rs` NFP ágban `&mut stop` átadása,
  - NFP-ben `stop.consume(1)` pontok:
    - instance loop elején,
    - CFR compute előtt (rotation szinten),
    - candidate loopban minden `can_place` előtt,
  - stop triggernél current+remaining instance `TIME_LIMIT_EXCEEDED` reason és determinisztikus
    korai visszatérés.
