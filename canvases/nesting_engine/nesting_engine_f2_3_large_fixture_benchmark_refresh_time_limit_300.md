# canvases/nesting_engine/nesting_engine_f2_3_large_fixture_benchmark_refresh_time_limit_300.md

# F2-3 benchmark report refresh: time_limit_sec=300 (large 500/1000)

## 🎯 Funkció
A cél: a large benchmark report frissítése a már javított large fixture-ek alapján, hogy a report
ne állítson fals “1000/NFP nondeterminism” eredményt.

Keret:
- `runs/` marad gitignore (a bench JSON lokális artifact), de a reportban a táblázat és a determinism összegzés legyen naprakész.
- Nem módosítunk algoritmust, csak újramérünk + dokumentálunk.

## 🧠 Fejlesztési részletek

### Miért kell
A large fixture-ek `time_limit_sec` mezője 300-ra lett emelve, emiatt a korábbi 30s time-limit melletti
hash-drift meg kell szűnjön (ha a drift valóban truncation miatt volt).

Állapot snapshot (2026-03-01):
- `scripts/gen_nesting_engine_large_fixture.py` defaultja `300`, és van `--time-limit-sec` felülírás.
- `poc/nesting_engine/f2_3_large_500_noholes_v2.json` és `...1000...` jelenleg `time_limit_sec=300`.
- A jelenlegi report még a korábbi (30s limit melletti) 1000/NFP `determinism_stable=false` eredményt tartalmazza, ezért frissítés szükséges.

### Mit kell lefuttatni (kötelező)
Release build + benchmark futtatás:

- `cargo build --release --manifest-path rust/nesting_engine/Cargo.toml`

Majd:

- `python3 scripts/bench_nesting_engine_f2_3_large_fixture.py --placer both --runs 5 --input poc/nesting_engine/f2_3_large_500_noholes_v2.json`
- `python3 scripts/bench_nesting_engine_f2_3_large_fixture.py --placer both --runs 5 --input poc/nesting_engine/f2_3_large_1000_noholes_v2.json`

Elvárás:
- 1000/NFP esetben `placed_count=1000` (ha a solver ezt el tudja helyezni), és `determinism_stable=true`.
- A reportban a “time-limit root cause” megjegyzést frissíteni kell: 30s → 300s és az új eredményekkel.

### Érintett fájlok
- `codex/reports/nesting_engine/nesting_engine_f2_3_large_fixture_benchmark.md` (FRISSÍTÉS)
- (verify által) `codex/reports/nesting_engine/nesting_engine_f2_3_large_fixture_benchmark.verify.log`

## 🧪 Tesztállapot

### DoD
- [x] A report táblázata friss mérési medianokkal kitöltve (500/1000 × BLF/NFP)
- [x] 1000/NFP: `determinism_stable=true` a reportban (ha így mérhető)
- [x] A reportban explicit: a korábbi drift oka 30s truncation volt, 300s alatt stabil
- [x] `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_f2_3_large_fixture_benchmark.md` PASS

## 🌍 Lokalizáció
Nem releváns.

## 📎 Kapcsolódások
- `scripts/gen_nesting_engine_large_fixture.py`
- `poc/nesting_engine/f2_3_large_500_noholes_v2.json`
- `poc/nesting_engine/f2_3_large_1000_noholes_v2.json`
- `scripts/bench_nesting_engine_f2_3_large_fixture.py`
- `codex/reports/nesting_engine/nesting_engine_f2_3_large_fixture_benchmark.md`
