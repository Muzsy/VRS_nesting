# Report — lv8_density_t10b_phase1_cache_stats_timeout_blocker

**Státusz:** PASS_WITH_NOTES

A matrix script javítva, repo gate zöld, unit tesztek 16/16. A blocker oka reprodukálva és
dokumentálva: a `lv8_276` (276 alkatrész, 2 lap) NFP-alapú elhelyezés 180s alatt is timeout-ol
(`runtime ≈ 241s`, SIGKILL), ezért `NEST_NFP_STATS_V1` nem emittálódik. A `sa_guard` kis
fixture mindkét profilban lefut és helyes statot ad. Az LV8 stats megszerzéséhez ≥600s-os
dedikált mérési run szükséges. `phase2a_unblocked: NO` — a Phase 2a LV8 evidence nélkül
nem indítható.

## 1) Meta

- **Task slug:** `lv8_density_t10b_phase1_cache_stats_timeout_blocker`
- **Kapcsolódó canvas:** [canvases/nesting_engine/lv8_density_t10b_phase1_cache_stats_timeout_blocker.md](../../../canvases/nesting_engine/lv8_density_t10b_phase1_cache_stats_timeout_blocker.md)
- **Kapcsolódó goal YAML:** [codex/goals/canvases/nesting_engine/fill_canvas_lv8_density_t10b_phase1_cache_stats_timeout_blocker.yaml](../../goals/canvases/nesting_engine/fill_canvas_lv8_density_t10b_phase1_cache_stats_timeout_blocker.yaml)
- **T10 előzmény-report:** [codex/reports/nesting_engine/lv8_density_t10_phase1_cache_usage_audit_and_benchmark.md](lv8_density_t10_phase1_cache_usage_audit_and_benchmark.md) (PASS_WITH_NOTES)
- **Futás dátuma:** 2026-05-17
- **Branch / commit:** `main`
- **Fókusz terület:** Scripts (Python matrix script timeout-kezelés)

## 2) Scope

### 2.1 Cél

1. T10 blocker oka reprodukálása és dokumentálása.
2. Matrix script bővítése: `--lv8-time-limit-sec`, `--stats-required-families`, `--allow-lv8-timeout-without-stats`.
3. Explicit döntési mezők: `phase2a_unblocked`, `phase2a_ready_source`, `lv8_stats_available`, `sa_guard_stats_available`.
4. Unit tesztek bővítése (9 új teszt).
5. T10B smoke run futtatása és eredmény dokumentálása.

### 2.2 Nem-cél (betartva)

1. Nincs Rust engine módosítás.
2. Nincs NFP cache-key módosítás.
3. Nincs LRU implementáció.
4. Nincs candidate scoring / bbox-growth.
5. Nincs fake stats.

## 3) Változások összefoglalója

### 3.1 Érintett fájlok

- [scripts/experiments/lv8_phase1_cache_usage_matrix.py](../../../scripts/experiments/lv8_phase1_cache_usage_matrix.py)
  — `LV8_FAMILY_PREFIX` konstans; `--lv8-time-limit-sec`, `--stats-required-families`,
  `--allow-lv8-timeout-without-stats` CLI args; `run_matrix()` új kwargs; `compute_decision()`
  új mezők és háromágú döntési logika; `_matrix_md()` `timed_out` oszlop + új fejlécsorok;
  matrix JSON `lv8_time_limit_sec` + `allow_lv8_timeout_without_stats` dokumentáció.
- [tests/test_lv8_phase1_cache_usage_matrix.py](../../../tests/test_lv8_phase1_cache_usage_matrix.py)
  — 9 új teszt hozzáadva (16 összesen, 7 régi megmaradt).
- [codex/reports/nesting_engine/lv8_phase1_cache_usage_result.md](lv8_phase1_cache_usage_result.md)
  — T10B run eredmény és root cause note hozzáadva.
- [codex/codex_checklist/nesting_engine/lv8_density_t10b_phase1_cache_stats_timeout_blocker.md](../../codex_checklist/nesting_engine/lv8_density_t10b_phase1_cache_stats_timeout_blocker.md) (új)
- [codex/reports/nesting_engine/lv8_density_t10b_phase1_cache_stats_timeout_blocker.md](lv8_density_t10b_phase1_cache_stats_timeout_blocker.md) (új, ez a fájl)

Nem módosult: Rust fájl, `worker/cavity_validation.py`, `vrs_nesting/`, `lv8_2sheet_claude_search.py`.

## 4) T10 blocker audit

### 4.1 Blocker reprodukálása

T10 smoke eredmény (`--time-limit-sec 60`): `lv8_276` `timed_out=True`, `runtime_sec ≈ 121s`.
T10B smoke eredmény (`--lv8-time-limit-sec 180`): `lv8_276` `timed_out=True`, `runtime_sec ≈ 241s`.

A `runtime_sec ≈ time_limit_sec + 60` mindkét esetben (60+60=120, 180+60=240) → a Python subprocess
`timeout=time_limit_sec + 60` kill-guard lép érvénybe, nem az engine saját timeout-ja. Ez azt
jelenti: a Rust engine `greedy_multi_sheet()` hívása a 276 alkatrészre iterációnként >60s-t vehet
igénybe, és az engine belső timeout-check „elszalad" a subprocess guard felé — vagyis az engine
saját `--time-limit-sec` nem hat elég pontosan, és nem ér oda a `main.rs:627-648` stats-emissziós
pontig.

### 4.2 Miért nem érhető el a stats

A `NEST_NFP_STATS_V1` sort a `main.rs` a `greedy_multi_sheet()` visszatérése *után* írja a stderr-re.
Ha a folyamatot `subprocess.TimeoutExpired` kivált és a kernel SIGKILL-lel leállítja, a stats sor
nem kerül ki. Az engine önmaga sem ér oda a clean exit pathig.

### 4.3 sa_guard oka

A `sa_guard` fixture (kis geometria, kevés alkatrész) `runtime_sec ≈ 0.006s` — triviálisan
gyors, stats mindig elérhető.

### 4.4 Timeout mechanizmus összefoglalója

```
[Python harness]
  subprocess.run(timeout = time_limit_sec + 60)  ← kill guard
  ↓ passes --time-limit-sec to engine
[Rust engine]
  greedy_multi_sheet() iterál
  ha check-point elér → returns → NEST_NFP_STATS_V1 emittálódik
  ha check-point nem ér el → subprocess kill guard triggerel → stats elvész
```

## 5) Implementált javítások

### 5.1 Új CLI paraméterek

| Paraméter | Default | Leírás |
|---|---|---|
| `--lv8-time-limit-sec N` | `time_limit_sec` | `lv8_*` prefix family-ek külön time-limit-et kapnak |
| `--stats-required-families LIST` | all required | Advisory path-hoz szükséges family-ek (pl. `sa_guard`) |
| `--allow-lv8-timeout-without-stats 0\|1` | `0` | Advisory path engedélyezése; kötelező indoklással |

### 5.2 Új döntési mezők (`compute_decision` output)

| Mező | Forrás | Leírás |
|---|---|---|
| `phase2a_unblocked` | új | Kanonikus Phase 2a readiness flag (T10B+) |
| `phase2a_ready_source` | új | `full_required_stats` \| `smoke_stats_plus_lv8_advisory` \| `blocked` |
| `lv8_stats_available` | új | `True` ha az összes `lv8_*` family engine_stats-a elérhető |
| `sa_guard_stats_available` | új | `True` ha sa_guard engine_stats-a elérhető |
| `phase2a_ready` | megtartva | Backward-compat alias = `phase2a_unblocked` |

### 5.3 Háromágú döntési logika

```
1. BLOCKED: blocked_reason nem null, vagy nincs required row
   → phase2a_unblocked=False, source=blocked

2. FULL PATH: cache_stats_available_all_required_runs AND polygon_gate_ok AND not lru
   → phase2a_unblocked=True, source=full_required_stats

3. ADVISORY PATH: stats_required_families stats OK AND allow_lv8_timeout_without_stats
                  AND polygon_gate_ok AND not lru AND not full path
   → phase2a_unblocked=True, source=smoke_stats_plus_lv8_advisory
   (csak explicit --stats-required-families + --allow-lv8-timeout-without-stats 1 esetén)

4. DEFAULT: phase2a_unblocked=False, source=blocked
```

## 6) T10B smoke run eredmény

```bash
python3 scripts/experiments/lv8_phase1_cache_usage_matrix.py \
  --out-root tmp/lv8_density_phase1_cache_usage_t10b \
  --time-limit-sec 60 \
  --lv8-time-limit-sec 180 \
  --seed 42 \
  --include-lv8-179 auto \
  --profiles quality_default_no_sa_shadow,quality_aggressive_no_sa_shadow
```

**exit_code: 3**

| family | profile | timed_out | runtime_sec | engine_stats | valid_polygon_gate |
|---|---|---|---|---|---|
| lv8_276 | quality_default_no_sa_shadow | True | 241.4 | False | True |
| lv8_276 | quality_aggressive_no_sa_shadow | True | 241.4 | False | True |
| sa_guard | quality_default_no_sa_shadow | False | 0.006 | True | True |
| sa_guard | quality_aggressive_no_sa_shadow | False | 0.006 | True | True |
| lv8_179 | quality_default_no_sa_shadow | True | 241.1 | False | True |
| lv8_179 | quality_aggressive_no_sa_shadow | True | 241.1 | False | True |

**`runtime_sec ≈ 241 ≈ 180 + 60`** — a subprocess kill guard lép érvénybe, nem az engine saját timeoutja. A 180s-os engine limit sem elegendő.

## 7) Verifikáció

### 7.1 Célzott ellenőrzések

- `python3 -m py_compile scripts/experiments/lv8_phase1_cache_usage_matrix.py` → **OK**
- `python3 -m pytest tests/test_lv8_phase1_cache_usage_matrix.py` → **16 passed** (7 régi + 9 új)
- Smoke run: exit_code=3, lv8 timed_out, sa_guard OK

### 7.2 Automatikus blokk

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-05-17T12:28:08+02:00 → 2026-05-17T12:31:26+02:00 (198s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/nesting_engine/lv8_density_t10b_phase1_cache_stats_timeout_blocker.verify.log`
- git: `main@de81a1d`
- módosított fájlok (git status): 9

**git diff --stat**

```text
 .../lv8_phase1_cache_usage_result.md               |  48 +++-
 .../experiments/lv8_phase1_cache_usage_matrix.py   | 143 +++++++++--
 tests/test_lv8_phase1_cache_usage_matrix.py        | 285 +++++++++++++++++++++
 3 files changed, 456 insertions(+), 20 deletions(-)
```

**git status --porcelain (preview)**

```text
 M codex/reports/nesting_engine/lv8_phase1_cache_usage_result.md
 M scripts/experiments/lv8_phase1_cache_usage_matrix.py
 M tests/test_lv8_phase1_cache_usage_matrix.py
?? canvases/nesting_engine/lv8_density_t10b_phase1_cache_stats_timeout_blocker.md
?? codex/codex_checklist/nesting_engine/lv8_density_t10b_phase1_cache_stats_timeout_blocker.md
?? codex/goals/canvases/nesting_engine/fill_canvas_lv8_density_t10b_phase1_cache_stats_timeout_blocker.yaml
?? codex/prompts/nesting_engine/lv8_density_t10b_phase1_cache_stats_timeout_blocker/
?? codex/reports/nesting_engine/lv8_density_t10b_phase1_cache_stats_timeout_blocker.md
?? codex/reports/nesting_engine/lv8_density_t10b_phase1_cache_stats_timeout_blocker.verify.log
```

<!-- AUTO_VERIFY_END -->

## 8) DoD → Evidence Matrix

| DoD pont | Státusz | Bizonyíték |
|---|---|---|
| #1 T10 blocker oka reprodukálva és dokumentálva | PASS | 4.1–4.4 szekció; `runtime_sec ≈ 241s = 180+60 kill guard` |
| #2 Matrix script explicit kezeli timeout/missing stats esetet | PASS | `timed_out`, `engine_stats_available=False` sorok megmaradnak; `lv8_stats_available` explicit mező |
| #3 Readiness döntés LV8 és SA guard külön jelölt | PASS | `lv8_stats_available`, `sa_guard_stats_available` mezők; `phase2a_ready_source` |
| #4 Script output JSON/MD tartalmazza T10B új mezőket | PASS | `phase2a_unblocked`, `phase2a_ready_source`, `lv8_stats_available`, `sa_guard_stats_available` a JSON-ban és MD-ben |
| #5 Unit tesztek lefedik új CLI és döntési logikát | PASS | `python3 -m pytest tests/test_lv8_phase1_cache_usage_matrix.py` → 16 passed |
| #6 Lefutott legalább egy T10B smoke matrix | PASS | exit_code=3, eredmény a 6) szekcióban és `lv8_phase1_cache_usage_result.md`-ben |
| #7 Report végén döntési mezők | PASS | 9) szekció alatt |
| #8 `./scripts/verify.sh --report …` zöld | PASS | AUTO_VERIFY blokk a 7.2 alatt |

## 9) Döntési mezők

```text
phase2a_unblocked: NO
phase2a_ready_source: blocked
lv8_stats_available: NO
sa_guard_stats_available: YES
next_task_recommendation: long LV8 benchmark szükséges (≥600s, vagy advisory döntés)
```

**Indoklás:** A `lv8_276` 276 alkatrészes NFP elhelyezés 180s alatt sem fejezi be a
`greedy_multi_sheet()` ciklusát → stats nem emittálható. Az `sa_guard` kis fixture mindig
stats-ot ad, de az nem elégséges evidence a Phase 2a indításához — a Phase 2a benchmark
célja éppen az LV8 mérés. Az advisory path (`smoke_stats_plus_lv8_advisory`) csak akkor
használható, ha explicit döntés születik arról, hogy az LV8 stats nélküli sa_guard-only
evidence elegendő. Ez a jelenlegi Phase 2a scope-ban nem indokolt.

**Következő lépés:** Hosszú LV8 benchmark futtatása ≥600s (vagy a harness engine time-limit
emelése), hogy a `greedy_multi_sheet()` befejezhessen és emittálhassa a stats sort. Alternatíva:
az advisory path explicit engedélyezése `--stats-required-families sa_guard --allow-lv8-timeout-without-stats 1` paraméterekkel, kötelező döntési dokumentációval.

## 10) Advisory notes (max 5)

1. A `phase2a_ready` mező T10B-től `phase2a_unblocked` aliasa. A T10 consumeRek a régi
   mezőre támaszkodnak — nincs breaking change.
2. A `--lv8-time-limit-sec` paraméter a helyes irány, de a Rust engine belső timeout-check
   pontosságától függ. Ha az engine iteráció-szintű check-et vezet be, a stats 180s-nál is
   megjelenhet. Ez Rust-szintű javítást igényelne (T10B scope-on kívül).
3. Az advisory path (`smoke_stats_plus_lv8_advisory`) implementálva és tesztelt, de jelenleg
   `phase2a_unblocked: NO` döntéssel nem aktivált. Ha a Phase 2a sürgős és az LV8 stats
   megszerzése késik, ez az advisory path előzetes jóváhagyással aktiválható.
4. `lv8_179` szintén timeout-ol — az `include-lv8-179 auto` mode automatikusan kezeli
   (optional fixture, nem required), de az advisory döntésnél figyelembe kell venni.
5. A `cache_usage_matrix.md` `timed_out` oszlopot tartalmaz T10B-től — ez teszi láthatóvá
   a timeout eseteket az első pillantásra.
