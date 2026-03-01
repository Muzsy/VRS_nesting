# canvases/nesting_engine/nesting_engine_timeout_bound_determinism_policy.md

# Timeout-bound determinism policy + benchmark jelölés

## 🎯 Funkció

A cél: a determinisztika-elvárás és a time_limit (wall-clock) viszonya legyen explicit és dokumentált, és a benchmark eszközök külön kategóriaként kezeljék a timeout-bound futásokat.

Miért:
- wall-clock limit mellett (különösen határ közelében) előfordulhat, hogy runonként 1-2 iteráció/placement különbség kijön scheduler/CPU drift miatt,
- ez nem “random bug”, hanem timeout-truncation jelenség.

Nem cél:
- algoritmikus fix (work-budget) bevezetése (az külön középtávú task),
- IO contract mezők bővítése,
- gate szigorítása timeoutos fixture-re.

## 🧠 Fejlesztési részletek

### 1) Doksi: determinisztika garancia pontosítása

Érintett doksik:
- `docs/nesting_engine/io_contract_v2.md`
- `docs/qa/testing_guidelines.md`
- `docs/nesting_engine/architecture.md`

Kötelező tartalom:
- definíció: “timeout-bound futás” (pl. van `TIME_LIMIT_EXCEEDED` unplaced reason, vagy a futás eléri a time_limit-et)
- determinism garancia: **azonos input + azonos seed + nem timeout-bound** esetén elvárt
- timeout-bound eset: **best-effort** (hash drift megengedett), és ezt a report/benchmark külön jelölje
- megjegyzés: a time_limit ellenőrzés wall-clock, durvább checkpointokkal (nem minden belső iterációban), így a limit környékén drift természetes

### 2) Benchmark script: timeout-bound jelölés

Érintett fájl:
- `scripts/bench_nesting_engine_f2_3_large_fixture.py`

Kötelező módosítás:
- az input JSON-ból olvassa ki: `time_limit_sec`
- run output JSON-ból derítse ki: timeout-bound-e a futás
  - `timeout_bound=true`, ha:
    - bármely `unplaced[].reason == "TIME_LIMIT_EXCEEDED"`, vagy
    - a mért `runtime_sec >= time_limit_sec` (kerekítési toleranciával)
- az összefoglalóban a `determinism_stable` mellé írjon ki még egy flaget:
  - `timeout_bound_present` (ha bármely run timeout-bound)
- ha determinism nem stabil és timeout-bound igaz → a script ezt “timeout-bound drift” kategóriába sorolja (ne algoritmikus regresszióként).

### 3) Report + checklist
- Report Standard v2 + AUTO_VERIFY.
- DoD->Evidence: konkrét doksi szakaszok + bench script új mezői.

## 🧪 Tesztállapot

### DoD
- [x] `io_contract_v2.md` tartalmaz explicit determinism vs timeout policy szöveget (TIME_LIMIT_EXCEEDED említéssel)
- [x] `testing_guidelines.md` kimondja: determinism gate-et csak “komfortosan limit alatt” futó fixture-re
- [x] `architecture.md` tartalmaz time_limit / timeout-bound viselkedés fejezetet + középtávú work-budget irányt (csak említés)
- [x] `bench_nesting_engine_f2_3_large_fixture.py` jelöli a timeout-bound futásokat és ezt beleírja az outputba
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_timeout_bound_determinism_policy.md` PASS

## 🌍 Lokalizáció
Nem releváns.

## 📎 Kapcsolódások
- `docs/nesting_engine/io_contract_v2.md` (TIME_LIMIT_EXCEEDED reason)
- `docs/qa/testing_guidelines.md`
- `docs/nesting_engine/architecture.md`
- `scripts/bench_nesting_engine_f2_3_large_fixture.py`
- `rust/nesting_engine/src/multi_bin/greedy.rs`, `rust/nesting_engine/src/placement/blf.rs` (wall-clock limit checkpointok)

## Felderítési snapshot (2026-03-01)

- `docs/nesting_engine/io_contract_v2.md` jelenleg tartalmazza a `TIME_LIMIT_EXCEEDED` reason kódot, de nincs explicit policy arra, hogy timeout-bound futásnál a hash drift best-effort kategória.
- `docs/qa/testing_guidelines.md` általánosan beszél determinisztikáról, de nem mondja ki, hogy a determinism gate-et timeout-határtól biztonságosan távoli fixture-re kell tenni.
- `docs/nesting_engine/architecture.md` jelenleg csak rotációs determinism policy-t rögzít; nincs külön timeout-bound viselkedés szekció.
- `scripts/bench_nesting_engine_f2_3_large_fixture.py` summary jelenleg csak `determinism_stable`-t és hash-listát ad, de nincs `timeout_bound_present` / timeout-bound drift jelölés.

## Pontos módosítási terv

1. `docs/nesting_engine/io_contract_v2.md`
   - új policy bekezdés a `TIME_LIMIT_EXCEEDED` reason köré:
     - timeout-bound definíció,
     - determinism garancia csak nem-timeout futásra,
     - timeout-bound esetben best-effort jelleg.

2. `docs/qa/testing_guidelines.md`
   - determinism gate szabály pontosítása:
     - gate fixture legyen "komfortosan" limit alatt,
     - benchmark/report kötelezően jelölje a timeout-bound állapotot.

3. `docs/nesting_engine/architecture.md`
   - új szekció:
     - wall-clock checkpointos limitelés miatti határközeli drift magyarázata,
     - középtávú irány: determinisztikus work-budget (csak irányelv, nem implementáció).

4. `scripts/bench_nesting_engine_f2_3_large_fixture.py`
   - inputból `time_limit_sec` beolvasás;
   - run-szinten `timeout_bound` jel számítás:
     - `unplaced[].reason == "TIME_LIMIT_EXCEEDED"` vagy `runtime_sec >= time_limit_sec - tolerance`;
   - summary-be:
     - `timeout_bound_present`,
     - `determinism_class` (`stable` / `timeout_bound_drift` / `unstable`);
   - log: timeout-bound instabilitás külön WARN kategóriában.
