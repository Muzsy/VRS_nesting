# canvases/nesting_engine/nesting_engine_deterministic_work_budget_stop.md

## 🎯 Funkció

Valódi technikai fix a timeout-bound BLF nondeterminizmusra:

- Bevezetünk egy **determinista work-budget stop policy-t** a BLF + multi-sheet greedy útvonalon.
- Cél: ha a futás “limit közelében” áll meg, akkor az eredmény **ne wall-clock pillanatfüggő** legyen (23 vs 24 placed), hanem **determinista** ugyanarra az inputra.

Keret:
- Nem bővítjük az IO contractot (marad `unplaced.reason == TIME_LIMIT_EXCEEDED`).
- A wall-clock `time_limit_sec` megmarad **safety guard**-nak, de a “mikor álljunk meg” elsődlegesen work-budget alapon történhet.
- Az új viselkedés **kapcsolható** (env), hogy ne legyen váratlan globális behavior change.

## 🧠 Fejlesztési részletek

### 1) Stop mode design

Új koncepció: `StopPolicy` (Rust, a nesting_engine-ben)

- `StopMode::WallClock` (default) – jelenlegi viselkedés.
- `StopMode::WorkBudget` – determinisztikus stop:
  - `work_budget_units` fogyasztása determinisztikus pontokon (pl. minden inner “attempt”/can_place próbánál)
  - ha elfogy → TIME_LIMIT_EXCEEDED
  - hard wall-clock guard: `time_limit_sec + hard_grace_sec` (ha ezt eléri → megáll, best-effort)

Konfiguráció env varokkal (csak a binary futásnál, unit tesztben direkt konstruktorral):
- `NESTING_ENGINE_STOP_MODE=wall_clock|work_budget` (default wall_clock)
- `NESTING_ENGINE_WORK_UNITS_PER_SEC=<u64>` (csak work_budget módban; default pl. 50000)
- `NESTING_ENGINE_HARD_TIMEOUT_GRACE_SEC=<u64>` (default pl. 60)

### 2) Hol épül be (kód)

- `rust/nesting_engine/src/multi_bin/greedy.rs`
  - `StopPolicy::from_env(time_limit_sec, started_at)`
  - a sheet-loop és a placer-hívás előtt ellenőriz:
    - work_budget módban: ha budget 0 → megáll
    - wall-clock módban: marad a jelenlegi
  - BLF placer hívás: `blf_place(..., &mut stop)`

- `rust/nesting_engine/src/placement/blf.rs`
  - `blf_place(..., stop: &mut StopPolicy)` új szignatúra (kizárólag greedy.rs hívja)
  - belső keresési ciklusokban determinisztikus `stop.consume(1)` kapuk:
    - `while ty` / `while tx` / rotáció loop elején
  - ha stop triggel:
    - a **jelenlegi** instance + a még hátralévők mind `TIME_LIMIT_EXCEEDED`
    - break a további keresésből (ne fusson tovább feleslegesen)

### 3) Doksiszinkron (kicsi)
- `docs/nesting_engine/io_contract_v2.md`:
  - `TIME_LIMIT_EXCEEDED` lehet wall-clock vagy work-budget stop következménye.
- `docs/nesting_engine/architecture.md`:
  - StopMode rövid leírás + miért szükséges.

### 4) Célzott unit teszt
`rust/nesting_engine/src/placement/blf.rs` testmodul:

- `blf_budget_stop_is_deterministic()` (prefix: `blf_budget_`)
  - ugyanazzal a bemenettel kétszer futtatja a BLF-et `StopMode::WorkBudget` módban
  - assert: placed/unplaced lista **azonos** (nem használ wall-clock döntést)
  - a hard wall-clock guardot úgy állítjuk be, hogy a tesztben biztosan ne érje el (pl. nagy time_limit + nagy grace)

### 5) Gate
`scripts/check.sh` nesting_engine blokk:
- adj hozzá célzott tesztfuttatást:
  - `cargo test --manifest-path rust/nesting_engine/Cargo.toml blf_budget_`

## 🧪 Tesztállapot

### DoD
- [x] `greedy.rs` StopPolicy-t használ, és BLF-et `&mut stop`-pal hívja
- [x] `blf.rs` belső loopokban work-budget consume kapuk vannak
- [x] Új unit teszt: `blf_budget_stop_is_deterministic` zöld
- [x] `scripts/check.sh` futtatja a `blf_budget_` célzott tesztet
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_deterministic_work_budget_stop.md` PASS

## 🌍 Lokalizáció
Nem releváns.

## 📎 Kapcsolódások
- `rust/nesting_engine/src/multi_bin/greedy.rs`
- `rust/nesting_engine/src/placement/blf.rs`
- `docs/nesting_engine/io_contract_v2.md`
- `docs/nesting_engine/architecture.md`
- `scripts/check.sh`
- BLF timeout drift benchmark: `poc/nesting_engine/real_dxf_quality_500_outer_only_v2.json`

## Felderítési snapshot (2026-03-02)

- Drift-gyanus wall-clock checkpointok:
  - `greedy.rs`: sheet-loop elején és round után (`elapsed >= time_limit_sec`) megállás.
  - `blf.rs`: part/instance elején és `!found` után `TIME_LIMIT_EXCEEDED` döntés.
- Emiatt limit-határ közelében run-to-run eltérés kijöhet (ugyanaz a keresési út eltérő pillanatban vágódik le).
- Determinisztikus consume pontok a BLF-ben:
  - `while ty` ciklus eleje,
  - `while tx` ciklus eleje,
  - rotációs candidate loop eleje.
- Ezeken a pontokon `consume(1)` mellett a stop döntés függetleníthető a pillanatnyi wall-clock állapottól.
