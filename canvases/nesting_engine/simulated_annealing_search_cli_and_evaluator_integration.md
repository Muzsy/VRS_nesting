# simulated_annealing_search_cli_and_evaluator_integration

## 🎯 Funkció

**Cél:** az F2-4 SA (Simulated Annealing) **bekapcsolhatóvá tétele** a `nesting_engine` CLI-n keresztül, és az SA evaluator integrációja a meglévő pipeline-ba úgy, hogy:

1) Default viselkedés **változatlan** marad (`--search` nélkül = baseline greedy).
2) Új CLI kapcsoló: `nest --search none|sa` (default: `none`).
3) SA módban az evaluator a meglévő `greedy_multi_sheet(...)`-et hívja, de:
   - `PartOrderPolicy::ByInputOrder`-ral,
   - SA state alapján **a bemeneti spec sorrendet** (és opcionálisan a rotációk sorrendjét) módosítja.
4) Determinizmus: fix seed + azonos input → reprodukálható SA kimenet.
5) A gate-ben legyen evidencia: `sa_` prefixű Rust tesztek futnak a `scripts/check.sh`-ból.

**Nem cél:**
- minőségjavulás (benchmark/fixture) bizonyítása (külön task),
- komplex neighborhood (2-opt/insert), caching optimalizációk (külön task),
- output schema módosítás (IO contract törés tilos).

## 🧠 Fejlesztési részletek

### CLI (nest subcommand)
A `rust/nesting_engine/src/main.rs` `run_nest_with_args` parse bővítése:

- `--search none|sa` (és `--search=...`)
- SA paramok (csak `--search sa` esetén értelmezve):
  - `--sa-iters <u64>` (default: `256`)
  - `--sa-temp-start <u64>` (default: `10000`)
  - `--sa-temp-end <u64>` (default: `50`)
  - `--sa-seed <u64>` (default: input.seed)
  - `--sa-eval-budget-sec <u64>` (default: `clamp(1..=time_limit_sec, time_limit_sec/10)`)

Követelmény:
- ismeretlen argumentum esetén a hibaüzenet sorolja fel az új supported flag-eket is.
- `--placer` továbbra is működjön ugyanúgy.

### SA evaluator integráció (Rust)
A `rust/nesting_engine/src/search/sa.rs` bővítése egy “integration” függvénnyel (core maradjon használható):

- `pub struct SaSearchConfig { ... }`
- `pub fn run_sa_search_over_specs(...) -> Result<(MultiSheetResult, Option<NfpPlacerStatsV1>), String>`

Evaluator:
- A state `order` permutációval újrarendezi a `Vec<InflatedPartSpec>` listát.
- `greedy_multi_sheet(..., order_policy = PartOrderPolicy::ByInputOrder)`-t hív.
- Opcionális: rotáció-heurisztika (MVP): a `allowed_rotations_deg` vektort “rotálja” a state `rot_choice` alapján, hogy a placer elsőként más rotációt próbáljon.
- Cost (integer, determinisztikus):
  - elsődleges: `unplaced_count`
  - másodlagos: `sheets_used`
  - harmadlagos: `not_placed = total_instances - placed.len()`
  - (MVP-ben elég; a finomabb metrikák később)

Determinism policy:
- SA módban a process belül **explicit** állítsd be (ha nincs már beállítva):
  - `NESTING_ENGINE_STOP_MODE=work_budget`
  - és stderr-re írj egy egyszeri diagnosztikát: “SA: forcing work_budget stop mode”.
- Ezzel az evaluation budget determinisztikusan “work unit” alapú (nem wall-clock érzékeny).

### Gate / tesztelés (kritikus)
- `scripts/check.sh` bővítése:
  - `cargo test --manifest-path rust/nesting_engine/Cargo.toml sa_`
  - így a már meglévő `sa_core_is_deterministic_fixed_seed` és az új SA-integrációs tesztek biztosan lefutnak CI-ban.

- Új Rust unit teszt (sa_ prefix):
  - `sa_search_is_deterministic_tiny_blf_case`
  - kis 2–3 spec, BLF placerrel, `--search sa` logika nélkül (direkt a `run_sa_search_over_specs` hívásával),
  - 2 futás azonos seed-del → azonos `MultiSheetResult` (placed+unplaced+sheets_used).

## 🧪 Tesztállapot

### DoD
- [ ] `nest --search none` baseline output változatlan (smoke + determinism hash gate zöld)
- [ ] `nest --search sa` működik, és fix seed mellett reprodukálható (unit teszt)
- [ ] `scripts/check.sh` futtatja `cargo test ... sa_` filtert
- [ ] `./scripts/verify.sh --report codex/reports/nesting_engine/simulated_annealing_search_cli_and_evaluator_integration.md` PASS
- [ ] Report Standard v2 + AUTO_VERIFY + `.verify.log` elmentve

## 🌍 Lokalizáció
Nem releváns.

## 📎 Kapcsolódások
- F2-4 canvas: `canvases/nesting_engine/simulated_annealing_search.md`
- SA core: `canvases/nesting_engine/simulated_annealing_search_sa_core_mvp.md`
- Kód:
  - `rust/nesting_engine/src/main.rs`
  - `rust/nesting_engine/src/search/sa.rs`
  - `scripts/check.sh`
- Workflow:
  - `docs/codex/yaml_schema.md`
  - `docs/codex/report_standard.md`
  - `docs/qa/testing_guidelines.md`
