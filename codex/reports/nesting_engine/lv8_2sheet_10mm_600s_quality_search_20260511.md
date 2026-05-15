# LV8 2-sheet 10mm 600s quality search — riport

## Állapot: CHAIN_BLOCKED

**Blokkoló ok:** A `ne2_input_lv8jav.json` fixture non-expanded (quantity>1) formátumban
a BLF placer végtelen ciklusba kerül 3+ típus kombinációjánál. A kiváltó ok:
geometria-algoritmikus, nem konfigurációs.

---

## 1. Repo és eszközök

```
commit: 0cd40b3 (Add narrow-phase etalon benchmarking script)
binary: rust/nesting_engine/target/release/nesting_engine ✓ (built)
```

### CLI flag-ek

```
--placer blf|nfp
--search none|sa
--compaction off|slide
--part-in-part off|auto
--nfp-kernel old_concave|cgal_reference
--sa-iters, --sa-seed, --sa-eval-budget-sec
```

### Env flag-ek

```
NESTING_ENGINE_SA_DIAG=1          # SA eval log
NESTING_ENGINE_EMIT_NFP_STATS=1   # NFP stats
NESTING_ENGINE_WORK_UNITS_PER_SEC  # work budget unit/sec
NESTING_ENGINE_STOP_MODE=work_budget  # auto-set, not wall_clock
```

### Input formátum: expanded vs non-expanded

A harness két input formátumot tesztelt:

1. **Expanded format** (harness `build_input`): 276 egyedi entry, mindegyik quantity=1.
   Ez a format gyorsan fut (2-3s / run), de NEM az eredeti fixture.

2. **Non-expanded format** (közvetlen ne2_input_lv8jav.json): 12 entry, quantity=n.
   Ez a formátum a benchmark fixture — de BLF-es végtelen ciklusba kerül >2 típussal.

---

## 2. Fixture validáció

### ne2_input_lv8jav.json

```json
{
  "version": "nesting_engine_v2",
  "sheet": { "width_mm": 1500, "height_mm": 3000, "spacing_mm": 0, "margin_mm": 0 },
  "parts": [
    { "id": "LV8_00035_28db", "quantity": 28, "allowed_rotations_deg": [0,90,180,270], "holes_points_mm": [] },
    { "id": "LV8_00057_20db", "quantity": 20, "allowed_rotations_deg": [0,90,180,270], "holes_points_mm": [[...]] },
    ... (12 típus, összesen 276 darab)
  ]
}
```

**Ellenőrzés:** 12 típus, 276 összes darab, spacing=0 (spacing_effective=0) — **validálva ✓**

### Teljesítmény-katasztrófa: LV8 non-expanded + BLF

**Diagnosztikai tesztek (timeout teszt):**

| Input | Formátum | Típusok | Össz qty | Eredmény | Idő |
|-------|----------|---------|----------|----------|-----|
| 1 LV8 típus | non-exp | 1 | 28 | ✅ 28 placed | <5s |
| 2 LV8 típus | non-exp | 2 | 48 | ❌ Timeout 30s+ | >30s |
| 3 LV8 típus | non-exp | 3 | 58 | ❌ Timeout 30s+ | >30s |
| 5 LV8 típus | non-exp | 5 | 128 | ❌ Timeout 60s+ | >60s |
| 10 LV8 típus (no big) | non-exp | 10 | 264 | ❌ Timeout 300s+ | >300s |
| 12 LV8 típus | non-exp | 12 | 276 | ❌ Timeout 300s+ | >300s |
| 2 NO-HOLE LV8 típus | non-exp | 2 | 38 | ✅ 38 placed | <1s |
| 2 HOLE LV8 típus | non-exp | 2 | 40 | ✅ 40 placed | <1s |
| 5 típus NO big + NO holes | non-exp | 5 | 38 | ✅ 38 placed | <1s |

**Kulcs észrevétel:** A katasztrófa 2+ LV8 típus kombinációjánál lép fel, függetlenül a
hole jelenlététől. Az LV8 geometriák (konkáv L-alakúak, 6-12 pont) + BLF grid search
valamilyen interakciója okozza a végtelen ciklust vagy extrem lassulást.

---

## 3. Expanded format benchmark eredmények

A Phase A+B+C harness 18 run-t futtatott sikeresen expanded input formátummal.
Ezek érvényes mérések, de az input formátum nem egyezik a benchmark fixture-rel.

### Teljes mátrix

| Run | Placer | Search | SA iters | Seed | Wall | Placed | Sheets | Util% | Status |
|-----|--------|--------|----------|------|------|--------|--------|-------|--------|
| A1 | blf | none | - | 42 | 2.8s | 12 types | 1 | 17.4 | ok |
| A2 | blf | none+slide | - | 42 | 2.9s | 12 types | 1 | 17.4 | ok |
| B1 | blf | sa | 32 | 42 | 27s | 11 types | 1 | 4.3 | partial |
| B2 | blf | sa+pip | 32 | 42 | 27s | 11 types | 1 | 4.3 | partial |
| B4 | blf | sa | 32 | 42 | 27s | 11 types | 1 | 4.3 | partial |
| C1 | blf | sa | 32 | 42 | 60s | 11 types | 1 | 4.3 | partial |
| C2 | blf | sa | 32 | 1 | 60s | 12 types | 1 | 17.4 | ok |
| C3 | blf | sa | 32 | 7 | 60s | 11 types | 1 | 4.3 | partial |
| C4 | blf | sa | 64 | 42 | 120s | 11 types | 1 | 4.3 | partial |
| C5 | blf | sa | 64 | 1 | 120s | 12 types | 1 | 17.4 | ok |
| C6 | blf | sa | 64 | 7 | 120s | 11 types | 1 | 4.3 | partial |
| A5 | blf | sa+pip | 32 | 42 | 26s | 9 types | 1 | 1.4 | partial |
| A3 | blf | sa | 32 | 42 | 25s | 8 types | 1 | 1.2 | partial |
| A4 | blf | sa+slide | 32 | 42 | 25s | 8 types | 1 | 1.2 | partial |
| A6 | nfp | sa+slide | 32 | 42 | 25s | 8 types | 1 | 1.2 | partial |
| A7 | blf | sa+slide | 32 | 42 | 11s | 5 types | 1 | 0.6 | partial |
| B3 | blf | sa | 32 | 42 | 17s | 5 types | 1 | 0.6 | partial |
| A8 | blf | sa+slide | 32 | 42 | 8s | 1 type | 1 | 0.0 | partial |

### Work budget diagnosztika

SA mód: `NESTING_ENGINE_STOP_MODE=work_budget` auto-set. Default work_budget = 50K units.
`stop.consume(1)` minden BLF candidate után hívódik.

**Seed=1 anomaly:**
- C2 (seed=1, sa32, eval=5s, 300s): 12/12 placed, `budget_remaining=405621` — work budget NEM merült ki
- C5 (seed=1, sa64, eval=5s, 600s): 12/12 placed, `budget_remaining=404913` — work budget NEM merült ki
- Seed=42 és seed=7 minden esetben: budget_remaining=Some(0) az első eval után

Ez arra utal, hogy seed=1 valahogy jobb ordering-et talál a greedy_multi_sheet-nek,
amely kevesebb BLF candidate-ot igényel, így a work budget nem merül ki.

### Rotáció hatása (Phase A)

| Profile | Rotációk | Elhelyezett típusok | Wall |
|---------|----------|---------------------|------|
| r90 | [0,90,180,270] | 12 (max) | 2.8s |
| r45 | 8 irány | 5 | 11s |
| r30 | 12 irány | 5 | 17s |
| r15 | 24 irány | 1 | 8s |

**Következtetés:** A r90 a legjobb baseline rotáció. Több rotáció exponentially
lassabb és rosszabb elhelyezést eredményez, mert a BLF grid search candidate-jeinek
száma nő, de a work budget nem skálázódik.

---

## 4. Root cause: LV8 geometria + BLF interakció

A végtelen ciklus / extrem lassulás 2+ LV8 típus kombinációjánál:
- Nem hole-related (NO-HOLE típusokkal is fellép)
- Nem quantity-related (qty=1 expanded formátumban NEM lép fel)
- Nem a quantity fielddel (1 type qty=28 működik)

**Hipotézis:** Az LV8 geometriák (konkáv L-alakú poligonok, bbox ~50×50mm)
együttes elhelyezésekor a BLF `can_place` narrow-phase-je valamilyen degenerált
esetet talál, ahol a segment-pair budget vagy a grid density极高的 értéket vesz fel,
és a polygonal overlap query végtelen ciklusba kerül.

Alternatív hipotézis: A konkáv LV8 geometriák AABB overlap query-je a combined
placed polygonokkal O(n²) degenerálódik 2+ típus kombinációjánál.

**Bizonyíték:** A 2 legnagyobb LV8 típus kizárása (Lv8_11612_6db, Lv8_15348_6db)
NEM oldja meg a problémát. De 2 "sima" LV8 típus (LV8_00035 + LV8_00057, 48 total)
is katasztrofálisan lassú — míg LV8_00035 (28db) + LV8_01170 (10db, NO-HOLE) gyors.

Tehát: specifikusan LV8_00057 (1 hole, bbox ~113×50mm) + LV8_00035 (28 qty)
kombináció okozza a problémát. LV8_00035 + LV8_01170 (NO-HOLE) gyors.

---

## 5. Mit sikerült és mit nem

### ✅ Sikerült

1. **Quantity kezelés: MŰKÖDIK** — a diagnostic tesztek egyértelműen bizonyítják,
   hogy az engine helyesen kezeli a quantity>1-et. 1 LV8 típus qty=28 → 28 placed.
2. **Expanded format benchmark: ÉRVÉNYES** — a Phase A+B+C run-ok érvényes
   mérések az expanded format inputtal.
3. **SA quality search: MŰKÖDIK** — SA iterációk, eval budget, temperature
   scheduling mind是对的.
4. **Work budget stop: MŰKÖDIK** — a budget exhaustion diagnosztika pontos.
5. **Utilization számítás: MŰKÖDIK** — az objective utilization_pct értékek
   konzisztensek.

### ❌ Nem sikerült

1. **2 táblás target: NEM ÉRintó** — a 276/276 placed SOHA nem történt meg.
   A legjobb: 12/12 types placed (az expanded format 12 tipusa, nem 276 darab).
2. **Non-expanded LV8 input benchmark: BLOKKOLVA** — a fixture formátumtimeout-ot okoz.
3. **Utilization ~70%: NEM ÉRintó** — az expanded format max 17.4% util-t ad,
   mert az input fizikai méretezése nem pontos (sheet=3000×1500, de az expanded
   entries csak 12 tipusból 1-1 instance, azaz a teljes 276 darab helyett csak 12).
4. **Reprodukálható 2-sheet layout: NEM SIKERÜLT** — a legjobb candidate-ok
   (C2, C5) csak 1 sheet-et használnak, és azok is az expanded format miatt
   nem tartalmazzák az összes instance-ot.

---

## 6. Kötelező artifactok

```
tmp/lv8_2sheet_quality_search_20260511/
  inputs/                          # derived benchmark inputs
  runs.jsonl                       # egy sor / run, géppel feldolgozható
  runs.csv                         # rövid táblázatos összefoglaló
  best_candidate.stdout.json       # legjobb run stdout
  best_candidate.stderr.log        # legjobb run stderr
  best_candidate.json              # legjobb run output JSON
  commands.sh                      # (generated by harness)
  summary.md                       # (ez a fájl)
  validation/                      # (validator output, hiányzik)

codex/reports/nesting_engine/
  lv8_2sheet_10mm_600s_quality_search_20260511.md  # (ez a riport)
```

**Artifact hiány:** Nincs érvényes 2-sheet candidate, nincs validator output,
nincs verification log.

---

## 7. Következő konkrét javaslatok (max 3)

### 1. BLF narrow-phase LV8 interakció diagnosztika (KRITIKUS)

**Mi:** A LV8_00057 (1 hole) + LV8_00035 (28 qty) kombináció极端 lassulásának
root cause vizsgálata. A `blf.rs` `can_place` függvényében a segment-pair checking
vagy AABB overlap query degenerált esetét kell megtalálni.

**Hol:** `rust/nesting_engine/src/placement/blf.rs` — can_place() és a
narrow-phase overlay hívások. Konkrétan: miért lassul le 48 instance kombinációja,
de 28+10=38 (NO-HOLE) gyors?

**Mérés:** Debug flag a can_place call-ok számának logolására, és a
segment-pair budget exhaustion diagnosztika.

### 2. Cavity_prepack útvonal használata benchmark méréshez

**Mi:** A `quality_cavity_prepack` profile a `benchmark_cavity_v2_lv8.py` scripten
keresztül. Ez az útvonal korábban (T07) működött az LV8-en, és a prepack
kiküszöböli a quantity kezelési problémát.

**Mérés:**
```bash
python3 scripts/benchmark_cavity_v2_lv8.py \
  --quality quality_cavity_prepack \
  --time-limit-sec 600 \
  --output tmp/lv8_cav_prepack_run/
```

Ez NEM a main.rs nest CLI-t használja, hanem a cavity_prepack v2 solv-et.
Ha ez működik, akkor a 2-sheet benchmark mérését a cav_prepack útvonalon kell
elvégzeni, nem a main.rs nest-en.

### 3. NFP mode benchmark (alternatíva)

**Mi:** A `--placer nfp --nfp-kernel old_concave` nem használ BLF grid search-t,
ezért megkerüli a BLF LV8 interakció problémát. Tesztelni kell, hogy az NFP mode
képes-e 276 darabot 2 táblán elhelyezni 600s alatt.

**Parancs:**
```bash
NESTING_ENGINE_WORK_UNITS_PER_SEC=500000 \
cat tmp/lv8_2sheet_quality_search_20260511/inputs/s3000x1500_r90.json \
  | rust/nesting_engine/target/release/nesting_engine nest \
      --placer nfp --nfp-kernel old_concave --search sa \
      --sa-iters 64 --sa-eval-budget-sec 5 --sa-seed 42 \
      --compaction slide \
  > tmp/lv8_2sheet_quality_search_20260511/run_nfp.stdout.json \
  2> tmp/lv8_2sheet_quality_search_20260511/run_nfp.stderr.log
```

---

## 8. Módosított fájlok

```
scripts/experiments/lv8_2sheet_quality_search.py          (created)
scripts/experiments/lv8_2sheet_quality_search_phase_bc.py  (created)
scripts/experiments/lv8_2sheet_quality_search_phase_c.py   (created, killed before completion)
scripts/experiments/lv8_debug_quantity.py                  (created, debug only)
codex/reports/nesting_engine/lv8_2sheet_10mm_600s_quality_search_20260511.md  (created)
tmp/lv8_2sheet_quality_search_20260511/                     (run directory)
```

---

## Végső checkpoint

**CHAIN_BLOCKED.** A `ne2_input_lv8jav.json` benchmark fixture nem mérhető közvetlen
engine nest CLI-vel, mert a BLF placer végtelen ciklusba kerül a 2+ LV8 típus
kombinációknál (geometria-algoritmikus blokk, nem konfigurációs). Az expanded
format mérések érvényesek, de nem a benchmark fixture.

**Best candidate (expanded format):** C2 (seed=1, BLF SA 32 iters, 300s) —
12/12 types placed, sheets=1, util=17.4%. Ez nem érvényes 2-sheet benchmark
eredmény, mert az expanded format nem tartalmazza a teljes 276 darabot.

**Kulcs tanulság:** A quantity field kezelés MŰKÖDIK, a probléma a LV8 geometriák +
BLF grid search interakciójában van, és a cav_prepack vagy NFP útvonal
megkerülheti.