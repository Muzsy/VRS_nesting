# canvases/nesting_engine/nesting_engine_nfp_work_budget_validation_timeout.md

## 🎯 Funkció

Bench-szintű validálás, hogy az NFP placer `work_budget` stop mellett is determinisztikus timeout-bound helyzetben.

Két szcenárió ugyanarra a fixture-re:
A) kényszerített timeout (kicsi work-budget) → TIME_LIMIT_EXCEEDED, de hash stabil
B) normál budget (default) → teljes lefutás, hash stabil, placed/sheets stabil

Input fixture (már létezik):
- `poc/nesting_engine/f2_3_large_1000_noholes_v2.json`
- `time_limit_sec=300`, `parts=1000`

Futtatandó parancsok:
```bash
cargo build --release --manifest-path rust/nesting_engine/Cargo.toml
python3 scripts/bench_nesting_engine_f2_3_large_fixture.py --placer nfp --runs 5 --stop-mode work_budget --work-units-per-sec 200 --hard-timeout-grace-sec 60 --input poc/nesting_engine/f2_3_large_1000_noholes_v2.json
python3 scripts/bench_nesting_engine_f2_3_large_fixture.py --placer nfp --runs 2 --stop-mode work_budget --work-units-per-sec 50000 --hard-timeout-grace-sec 60 --input poc/nesting_engine/f2_3_large_1000_noholes_v2.json
```

## 🧠 Fejlesztési részletek

### Szcenárió A — timeout kényszerítés work_budget-dzsel
- `--stop-mode work_budget`
- `--work-units-per-sec 200` (kicsi)
- `--hard-timeout-grace-sec 60`
- `--placer nfp --runs 5`

Elvárás:
- `timeout_bound_present=true`
- `determinism_stable=true` (hash stabil)
- placed < 1000 (várható), unplaced reason: TIME_LIMIT_EXCEEDED

### Szcenárió B — normál budget (regresszió-ellenőrzés)
- `--stop-mode work_budget`
- `--work-units-per-sec 50000` (default)
- `--hard-timeout-grace-sec 60`
- `--placer nfp --runs 2` (nem kell 5, ez hosszabb)

Elvárás:
- `timeout_bound_present=false`
- `determinism_stable=true`
- placed=1000 és sheets stabil (várhatóan 98, ha ugyanaz a baseline)

### Report
Új report (külön a korábbi benchmarkoktól):
- `codex/reports/nesting_engine/nesting_engine_nfp_work_budget_validation_timeout.md`
Tartalmazzon:
- pontos parancsok
- 2 soros összefoglaló táblázat (A/B)
- konklúzió: timeout-bound drift megszűnik work_budget módban, és normál futás nem regresszált.

## 🧪 Tesztállapot

### DoD
- [ ] mindkét futás lefut és a reportban ott a mérési összegzés
- [ ] A szcenárió: timeout_bound_present=true és determinism_stable=true
- [ ] B szcenárió: timeout_bound_present=false és determinism_stable=true
- [ ] `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_nfp_work_budget_validation_timeout.md` PASS

## 🌍 Lokalizáció
Nem releváns.

## 📎 Kapcsolódások
- `poc/nesting_engine/f2_3_large_1000_noholes_v2.json`
- `scripts/bench_nesting_engine_f2_3_large_fixture.py` (stop-mode CLI + timeout-bound jelölés)
- `rust/nesting_engine/src/placement/nfp_placer.rs` (StopPolicy consume pontok)
- `rust/nesting_engine/src/multi_bin/greedy.rs` (StopPolicy from env)
