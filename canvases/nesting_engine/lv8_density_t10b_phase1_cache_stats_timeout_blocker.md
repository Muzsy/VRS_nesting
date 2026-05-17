# LV8 Density T10B — Phase 1 cache stats timeout blocker fix

## 🎯 Funkció

A T10 task repo gate-je zöld lett, de a T10 saját döntési mezői szerint a Phase 2a még **nem indítható**:

```text
phase2a_ready: NO
cache_stats_available_all_required_runs: NO
next_task_recommendation: benchmark blocker javítandó
```

A blocker oka: a `scripts/experiments/lv8_phase1_cache_usage_matrix.py` smoke futásban a required LV8 runok timeouttal álltak meg, ezért a harness nem tudta kiolvasni a `NEST_NFP_STATS_V1` sort, és az `engine_stats.available=false`, `parse_error=missing_stats_line` lett.

A T10B célja **nem algoritmikus fejlesztés**, hanem a Phase 1 mérési útvonal javítása úgy, hogy a T10 cache-usage döntése megismételhetően, hamis eredmény nélkül zárható legyen. T10B után a Phase 2a csak akkor indulhat, ha az új T10B report explicit `phase2a_unblocked: YES` döntést hoz.

---

## Előfeltételek

Kötelező reportok:

```text
codex/reports/nesting_engine/lv8_density_t10_phase1_cache_usage_audit_and_benchmark.md
codex/reports/nesting_engine/lv8_phase1_cache_usage_result.md
```

Elfogadott T10 státusz:

```text
PASS_WITH_NOTES
```

Kötelező T10 döntési mezők:

```text
phase2a_ready: NO
cache_stats_available_all_required_runs: NO
next_task_recommendation: benchmark blocker javítandó
```

Ha ezek a mezők nem így szerepelnek, T10B ne módosítson kódot; készíts `BLOCKED` reportot, és írd le, hogy a T10B feltételei nem állnak fenn.

---

## Valós repo-kiindulópontok

### T10 matrix script

```text
scripts/experiments/lv8_phase1_cache_usage_matrix.py
```

Jelenleg a required family-ként kezelt `lv8_276` és `sa_guard` runokat ugyanazzal a `--time-limit-sec` értékkel futtatja. A 60s smoke paraméter mellett az LV8 runok timeoutolhatnak, így nincs stats sor.

### Alapharness

```text
scripts/experiments/lv8_2sheet_claude_search.py
```

A T04/T05/T08 után ez már:

- `NESTING_ENGINE_EMIT_NFP_STATS=1` értéket állít,
- stderr file-ból parse-olja a `NEST_NFP_STATS_V1` sort,
- `engine_stats` blokkot ír `summary.json`-be,
- polygon-aware validation gate-et futtat.

A hiányzó stats oka nem parse-kód hiány, hanem hogy timeout/killed run esetén a solver nem jut el a végső stats-emisszióig.

### T10 report evidence

```text
codex/reports/nesting_engine/lv8_density_t10_phase1_cache_usage_audit_and_benchmark.md
codex/reports/nesting_engine/lv8_phase1_cache_usage_result.md
```

Ezeket kötelező forrásként kell használni, nem szabad újraértelmezni a T10 státuszt.

---

## Scope

### Engedélyezett módosítások

```text
scripts/experiments/lv8_phase1_cache_usage_matrix.py
tests/test_lv8_phase1_cache_usage_matrix.py
codex/codex_checklist/nesting_engine/lv8_density_t10b_phase1_cache_stats_timeout_blocker.md
codex/reports/nesting_engine/lv8_density_t10b_phase1_cache_stats_timeout_blocker.md
codex/reports/nesting_engine/lv8_density_t10b_phase1_cache_stats_timeout_blocker.verify.log
codex/reports/nesting_engine/lv8_phase1_cache_usage_result.md
```

### Feltételesen módosítható

Csak akkor módosítható, ha a matrix-script szintű javítás nem elég, és a reportban konkrét bizonyíték szerepel, hogy a harness timeout policy hibás:

```text
scripts/experiments/lv8_2sheet_claude_search.py
```

### Tilos

```text
- Rust production engine módosítás
- NFP cache-key módosítás
- LRU implementáció
- Candidate scoring / bbox-growth bevezetése
- Lookahead / beam / LNS módosítás
- SA hard-cut
- quality_default / quality_aggressive átírása no-SA-ra
- Fake vagy kézzel gyártott benchmark summary
```

---

## Elvárt javítási irány

A T10B elsődleges javítási iránya a **matrix script mérési protokolljának pontosítása**, nem engine refaktor.

A scriptnek tudnia kell külön kezelni:

1. **fast stats smoke** — rövid, required stats sanity run olyan fixture-ön, ami biztosan befejeződik;
2. **LV8 advisory / long evidence run** — LV8 run hosszabb vagy konfigurálható time limit mellett;
3. **readiness döntés** — Phase 2a csak akkor indul, ha legalább egy olyan required mérési út teljesül, amely valódi engine_stats-ot és polygon gate-et ad, és az LV8 sorok hiánya nem marad néma.

### Preferált CLI-bővítések

A meglévő CLI mellé adj hozzá explicit paramétereket:

```text
--lv8-time-limit-sec N              # default: same as --time-limit-sec
--stats-required-families LIST      # default: sa_guard,lv8_276 vagy documented safer default
--allow-lv8-timeout-without-stats 0|1
--probe-mode smoke|long|mixed       # optional, ha egyszerűbbé teszi a logikát
```

A pontos név lehet más, de a reportban dokumentálni kell.

### Readiness logika

A T10B végén legyen világos különbség:

```text
phase2a_unblocked: YES | NO
phase2a_ready_source: full_required_stats | smoke_stats_plus_lv8_advisory | blocked
cache_stats_available_all_required_runs: YES | NO
lv8_stats_available: YES | NO
sa_guard_stats_available: YES | NO
```

Ha nincs LV8 stats, de a task mégis `phase2a_unblocked: YES` döntést hoz, akkor kötelező indoklás kell arról, miért elég a Phase 2a implementáció megkezdéséhez. Ha nincs erős indok, maradjon `NO`.

---

## Kötelező tesztek

Bővítsd a meglévő:

```text
tests/test_lv8_phase1_cache_usage_matrix.py
```

minimum ezekkel:

- külön `lv8_time_limit_sec` átadás tesztje;
- `stats_required_families` döntési logika tesztje;
- timeoutos LV8 row nem tünteti el a blocker információt;
- `phase2a_unblocked` csak explicit feltételek mellett lehet true;
- nincs regresszió a korábbi T10 hit-rate / fixture-missing / clear_all döntési tesztekben.

---

## Kötelező smoke futás

A task végén legalább egy gyors smoke futás kell. Példa:

```bash
python3 scripts/experiments/lv8_phase1_cache_usage_matrix.py \
  --out-root tmp/lv8_density_phase1_cache_usage_t10b \
  --time-limit-sec 60 \
  --lv8-time-limit-sec 180 \
  --seed 42 \
  --include-lv8-179 auto \
  --profiles quality_default_no_sa_shadow,quality_aggressive_no_sa_shadow
```

Ha a környezetben az LV8 továbbra sem ad stats sort, a report legyen `PASS_WITH_NOTES` vagy `BLOCKED`, de ne állítsa, hogy Phase 2a teljesen ready.

---

## DoD

T10B akkor tekinthető késznek, ha:

1. A T10 blocker oka reprodukálva és dokumentálva van.
2. A matrix script explicit kezeli a timeout miatt hiányzó stats esetet.
3. A readiness döntés nem csak `cache_stats_available_all_required_runs` boolean, hanem külön jelöli LV8 és SA guard stats állapotát.
4. A script output JSON/MD tartalmazza a T10B új döntési mezőit.
5. A unit tesztek lefedik az új CLI és döntési logikát.
6. Lefutott legalább egy T10B smoke matrix.
7. A report végén szerepel:

```text
phase2a_unblocked: YES | NO
phase2a_ready_source: ...
lv8_stats_available: YES | NO
sa_guard_stats_available: YES | NO
next_task_recommendation: T11 indulhat | T10B tovább javítandó | long LV8 benchmark szükséges
```

8. `./scripts/verify.sh --report codex/reports/nesting_engine/lv8_density_t10b_phase1_cache_stats_timeout_blocker.md` zöld.

---

## Kimeneti report elvárás

Készíts reportot:

```text
codex/reports/nesting_engine/lv8_density_t10b_phase1_cache_stats_timeout_blocker.md
```

A report státusza lehet:

- `PASS` — a blocker megoldva és `phase2a_unblocked: YES`.
- `PASS_WITH_NOTES` — a script javítva, repo gate zöld, de LV8 long evidence még hiányzik; ilyenkor T11 csak külön döntéssel indulhat.
- `BLOCKED` — a környezet vagy harness miatt nem volt valódi mérés.
- `FAIL` — DoD vagy repo gate bukott.

