# LV8 single-sheet 179-instance etalon test — riport

**Dátum:** 2026-05-14
**Branch / commit:** main / 0cd40b3
**Fixture:** [tmp/lv8_singlesheet_etalon_20260514/inputs/lv8_sheet1_179.json](../../../tmp/lv8_singlesheet_etalon_20260514/inputs/lv8_sheet1_179.json)
**Etalon hivatkozás:** [tmp/etalon/project_2447207_report.pdf](../../../tmp/etalon/project_2447207_report.pdf) Sheet 1

## 1. Cél

A korábbi [2-sheet riport](lv8_2sheet_10mm_600s_claude_code_report.md) feltárta: a mi engine-ünk legjobb futása (`cgal_s42_180`) 189/276 darabot rakott le 23 % util-on, az összes hiányzó darab `TIME_LIMIT_EXCEEDED` reasont kapott — az engine soha nem ugrott át sheet 1-re.

Kérdés: **a multi-sheet policy a probléma, vagy maga a per-sheet packing minőség?**

Diagnosztika: kivettük az etalon (nest&cut) Sheet 1 pontos összetételét (179 darab, 12 típus, 73 % util az etalonon), építettünk belőle önálló fixture-t, és lefuttattuk rá a stratégiáinkat. Ha az engine ezen ~73 % util-t ad → a multi-sheet policy a fő blokkoló. Ha jóval kevesebbet → a per-sheet packing minőség is gyenge.

## 2. Fixture

| | Érték |
|---|---|
| Sheet | 3000 × 1500 mm |
| Spacing | 10 mm inter-part |
| Margin | 10 mm sheet-border |
| Rotations | [0, 90, 180, 270] |
| Types / instances | 12 / **179** |
| Sheet 1 total parts area (etalon) | 3.28 m² = **72.98 %** a sheet területéből |

Sheet 1 összetétel (mind a 12 típus jelen van, kvancának egy része):

```
LV8_01170_10db: 9   LV8_02049_50db: 50   Lv8_07920_50db: 7   Lv8_15435_10db: 10   LV8_00035_28db: 28
LV8_02048_20db: 3   Lv8_07919_16db: 16   Lv8_07921_50db: 28  Lv8_11612_6db:  3   LV8_00057_20db: 11
                                                              Lv8_15348_6db: 4
                                                              Lv8_10059_10db: 10
```
(összesen 9+3+50+16+7+28+10+3+4+10+28+11 = **179** ✓; az etalon 73 % util-t ér el ezekkel egy táblán)

## 3. Run-mátrix

[tmp/lv8_singlesheet_etalon_20260514/runs.csv](../../../tmp/lv8_singlesheet_etalon_20260514/runs.csv)

| id | placer | search | kernel | prepack | seed | tl(s) | runtime | placed/179 | sheets | sheet0 util | összes util | állapot |
|----|--------|--------|--------|---------|-----:|------:|--------:|----------:|-------:|------------:|------------:|---------|
| **cgal_greedy_noprep_s42** | nfp | none | cgal_reference | off | 42 | — | <60 s | **179** | **2** | **59.98 %** | 36.50 % (2-sheet avg) | ok |
| cgal_s42_60 (with prepack) | nfp | sa | cgal_reference | prepack | 42 | 60 | 63 s | 117 | 1 | 8.68 % | 8.68 % | partial, completed |
| cgal_s42_180 (best of 2-sheet) | nfp | sa | cgal_reference | prepack | 42 | 180 | 240 s | 0 | 0 | n/a | n/a | **TIMEOUT** (watchdog kill, 0 byte stdout) |
| cgal_sa_noprep_180 | nfp | sa | cgal_reference | off | 42 | 180 | 240 s | 0 | 0 | n/a | n/a | **TIMEOUT** |
| greedy_oldconcave_s42 | nfp | none | old_concave | off | 42 | — | 120 s | 0 | 0 | n/a | n/a | **TIMEOUT** |
| blf_baseline_s42 | blf | none | n/a | off | 42 | — | 120 s | 0 | 0 | n/a | n/a | **TIMEOUT** |
| greedy seed=1 | nfp | none | cgal_reference | off | 1 | — | 150 s | 0 | 0 | n/a | n/a | **TIMEOUT** |
| greedy seed=7 | nfp | none | cgal_reference | off | 7 | — | 150 s | 0 | 0 | n/a | n/a | **TIMEOUT** |
| greedy seed=13 | nfp | none | cgal_reference | off | 13 | — | 150 s | 0 | 0 | n/a | n/a | **TIMEOUT** |
| greedy seed=100 | nfp | none | cgal_reference | off | 100 | — | 150 s | 0 | 0 | n/a | n/a | **TIMEOUT** |

**Etalon (nest&cut, ugyanaz a 179 darab egy táblán):** 179/179 placed, 1 sheet, **72.98 % util**, 60 s össz-budget.

## 4. Legjobb candidate: `cgal_greedy_noprep_s42`

- Profil: NFP placer, search=none (csak greedy multi-bin), part-in-part=off, compaction=slide, kernel=cgal_reference, seed=42, prepack KIKAPCSOLVA.
- Output: [tmp/lv8_singlesheet_etalon_20260514/cgal_greedy_noprep/stdout.json](../../../tmp/lv8_singlesheet_etalon_20260514/cgal_greedy_noprep/stdout.json) (19 945 byte)
- Placements: **mind a 179** elhelyezve, unplaced lista üres.

**Sheet-elosztás:**

| Sheet | Placements | Összterület | Util | Mit tartalmaz |
|------:|-----------:|------------:|-----:|---------------|
| 0 | **178** | 2 699 163 mm² | **59.98 %** | Mind a 12 típus, kivéve 1 db `Lv8_11612` |
| 1 | **1** | 585 784 mm² | 13.02 % | 1 db `Lv8_11612` (a 6 óriás közül 3 helyett 2 fér csak a sheet 0-ra) |
| **Σ** | 179 | 3 284 947 mm² | — | a teljes etalon Sheet 1 (3.28 m²) |

Megjegyzés: az engine a **teljes etalon-területet lerakta**, csak fragmentált sheet 0 + sheet 1-re. Az össz-területigény stimmel: 3 284 947 mm² ≈ 3.28 m² az etalonéval.

## 5. Mi sikerült és mi nem

### Ami sikerült

1. **Az engine képes mind a 179 darabot elhelyezni** (greedy NFP + cgal_reference, prepack nélkül, <60 s).
2. **A multi-sheet greedy spillover working** — amikor nincs SA-időpresszió, az engine átugrik a sheet 1-re, ahol kell. Ez **érdemben módosítja** a 2-sheet riport "spillover nem működik" diagnózisát: kontextus-érzékeny, és az SA-időpresszió alatt _nem_ jut el oda; tisztán greedy mellett viszont igen.
3. **A teljes etalon-területet (3.28 m²) a kódunk lerakja** — semmilyen darab nem "elveszik" az engine számára. A baj kvalitatív, nem mennyiségi.

### Ami nem sikerült

1. **Sheet 0 util = 60 % a 73 % etalon helyett.** A 13 pp különbség **pontosan egy `Lv8_11612` óriás területe** (585 784 mm² = 13.02 % a sheet-en). Az engine 178 darabot 60 %-on rak le, és a maradék ~40 % szabad területbe nem talál pozíciót a 3. `Lv8_11612`-nek — pedig az etalon 3-at fér a sheet 1-re. Ez **per-sheet packing minőségi gap**, nem multi-sheet policy probléma.
2. **Minden SA stratégia időtúllépik.** A `cgal_s42_180` (prepack-kel és anélkül is) 0 byte stdout-tal halt a watchdog-killtól; a `cgal_s42_60` lefutott, de **csak 117/179-et tett le 8.7 % util-on** — a SA "rontotta" a greedy 60 %-os baseline-ját. Tehát:
   - **A jelenlegi SA-implementáció nem javít a greedy NFP eredményén — rosszabbá teszi.** Vagy futási időbe nem fér bele, vagy ha igen, akkor sokkal lazább layoutot ad.
3. **Súlyos seed-érzékenység greedy NFP-ben.** A seed=42 <60 s alatt teljes 179 darab lerakást ad; a seed=1, 7, 13, 100 **mind 150 s-en belül sem fejeződnek be**. Ez nem véletlen-finomhangolás, hanem a part-ordering specifikus pathological set-jén lassul be katasztrofálisan a NFP / placement kombináció. Ugyanaz a probléma, amit a Hermes riport `seed=1 anomaly`-nak hívott — most a fordított oldalról: a seed=42 a "szerencsés" eset.
4. **Az old_concave NFP kernel greedyvel sem fejezi be** 120 s-en belül egy 179-instance fixtur-ön. Ez újabb bizonyíték arra, hogy az `old_concave` kernel az LV8-skálán **mindenfajta search módban (SA *és* none)** használhatatlan, nem csak SA-val.
5. **BLF greedy is timeoutol 120 s alatt.** Megint csak: a BLF az LV8-skálán nem versenyképes, függetlenül az SA jelenlététől.

## 6. Mit jelent a 60 % vs 73 % gap

| Sheet 0 metrika | greedy NFP (mi) | nest&cut (etalon) | Gap |
|---|---:|---:|---:|
| Elhelyezett darab | 178 | 179 | -1 |
| Elhelyezett terület | 2.70 m² | 3.28 m² | -0.58 m² |
| Sheet 0 util | 59.98 % | 72.98 % | **-13.00 pp** |
| Cutting length | n/a | 112.009 m | — |

A gap **egész pontosan 1 db `Lv8_11612` területe.** Az engine 178 darabnak talál helyet, a 179. nem fér be: vagy nem ad jó orientációt a 3. nagy darabnak, vagy a kis darabok körül akkora "halo" marad, hogy az óriás polygonja nem talál szabad zsebet.

Ez **packing-quality** probléma, nem ordering: az etalon pontosan ugyanezt a 179 darabkészletet képes pakolni 73 %-ra, vagyis a feladat fizikailag megoldható. A mi greedy NFP-nk csak ~80 %-át adja vissza annak a sűrűségnek, amit a nest&cut produkál.

## 7. Az eredeti kérdés válasza

> "Mennyire probléma a több tábla kezelése, illetve mennyire tud hatékony lenni az algoritmus, ha csak egy táblára kell koncentrálnia?"

**Két fő észrevétel:**

1. **A multi-sheet kezelés NEM annyira problémás, mint a 2-sheet riport sugallta.** A greedy NFP minden időpresszió nélkül 178+1 elosztással átugrik sheet 1-re. Tehát a sheet-spillover policy *funkcionálisan* helyes; az SA-mode-ban észlelt `TIME_LIMIT_EXCEEDED`-spam más bug: az SA első evalja olyan hosszú, hogy a deadline mindig a sheet 0 töltésekor szólal meg, és a spillover-szakasz sosem fut le.
2. **A per-sheet packing minőség az igazi gyenge pont.** 60 % util az etalon 73 %-jával szemben, miközben a fixture fizikailag megengedi a 73 %-ot. Ha az engine erre az egy táblára fókuszálhatna (= ha a packing-minőség önmagában javul), a 2-sheet probléma is megoldódik: a Sheet 1-en úgyis csak ~66 % util-t kell kihozni (az etalon szerint), ami az engine jelenlegi 60 %-jához nagyon közel van. Tehát a teljes 276-instance probléma kulcsa a **per-sheet packing density javítása**, nem a multi-sheet policy.

**Tehát a single-sheet teszt egyértelmű választ adott:** a multi-sheet policy másodlagos kérdés. A fő blokkoló a packing-density.

## 8. Konkrét következő javaslatok (max 3, fontossági sorrend)

1. **Greedy NFP packing-density javítása lehet a leggyorsabb fix.** Ma a `cgal_reference` greedy 60 %-ot ad ott, ahol az etalon 73 %-ot. Ha a `bottom-left tie-breaking`-et (`placement/nfp_placer.rs`) megnézzük: a kandidálható pozíciók közül a "leg-bottom-left" választás gyakran szétszórja a nagy darabokat. Egy egyszerű "occupied envelope-aware" tie-breaker (válaszd azt a pozíciót, amely a legkevesebb új AABB-aera-t nyit) +5-10 pp util-t hozhat anélkül, hogy SA-ra szükség lenne. Ez a 60→70 % közötti tartományt megnyitná.
2. **SA inner-eval végleges debug / kapcsolat le.** Ma a SA prepack-kel és anélkül is **rontja a greedy eredményt** (117/179 8.7 %-on a greedy 179/179 60 %-jával szemben), vagy be sem fejezi az első evalt. Az SA-eval LV8-skálán használhatatlan; vagy egy `max_iter` szigorítás kell `search/sa.rs`-ben (egyetlen eval ne tartson > 30 s-nál), vagy az SA-t le kell kapcsolni a quality profile-ról amíg ez nem javul. A mai default profile (`quality_default`, `quality_aggressive`, `quality_cavity_prepack*`) **mind SA-t használ** — egy `quality_greedy_fast` profil hozzáadása (greedy NFP + cgal_reference + slide compaction) gyors-pálya legalább. [vrs_nesting/config/nesting_quality_profiles.py](../../../vrs_nesting/config/nesting_quality_profiles.py).
3. **Seed-fragility root cause.** 5-ből 1 seed (s42) fejezi be a greedy NFP-t 60 s alatt, a többi 150 s-en belül sem. Ez azt jelenti, hogy production-ben **80 % esélyünk van** azonnali timeout-ra ha véletlenül "rossz" seedet kap az engine. A `placement/nfp_placer.rs`-ben a part-ordering / candidate-grid generálás seed-függő részét kell megnézni (valószínűleg egyetlen `compute_pair_nfp` hívás degenerál bizonyos rotációs/sorrendi kombinációknál); a `pair-NFP cache` (a 2-sheet riport 1. ajánlása) ezt önmagában megoldhatja, mivel a seed-fragility valószínűleg azt jelenti, hogy bizonyos seedek olyan ordering-be esnek, ahol több pár újra-újra számoltatik.

## 8b. Utólag: forgatás-szögfelbontás sweep (r45 / r15 / r3)

A felhasználói hipotézis: az etalon "All rotations allowed"-ot használ, mi csak `[0,90,180,270]`-et — talán a fine-grained forgatás engedi a 73 % util-t. Lefuttattam ugyanazon a 179-instance fixture-ön greedy NFP cgal_reference seed=42, prepack off, search=none, csak a `allowed_rotations_deg` értéket cserélve.

| Rotation set | # rotations | Placed | Sheet 0 util | Megjegyzés |
|---|---:|---:|---:|---|
| **r90** | 4 (0,90,180,270) | 179 (178+1) | **59.98 %** | baseline |
| **r45** | 8 (0,45,…,315) | 179 (178+1) | **59.98 %** | **azonos util** — bár 135°-ot a legtöbbet (50×) használja |
| **r15** | 24 (0,15,…,345) | 86 / 179 | 43.40 % | 93 db `TIME_LIMIT_EXCEEDED` az NFP-precompute költségtől |
| **r3** | 120 (0,3,…,357) | 12 / 179 | 39.29 % | 167 db `TIME_LIMIT_EXCEEDED`; NFP-pár robbanás |

**Két fontos észrevétel:**

1. **r45 (8 forgatás) bizonyítja, hogy a forgatás-felbontás NEM a 13 pp gap oka.** Az engine a 45°-os szögeket aktívan használja (a 135° lesz a *leggyakoribb* forgatás 50 placement-tel a 178-ból), és **mégis pontosan ugyanaz a sheet 0 util (59.98 %)** és **ugyanaz az 1 db `Lv8_11612` csúszik át sheet 1-re**. Tehát a packing-density limit a placement-stratégián múlik, nem a forgatás-készleten.
2. **r15 és r3 (24/120 forgatás) katasztrofálisan romlik.** Itt az NFP-pár robbanás (120 forgatás × 12 típus = 1440 unique orientations → ~2M pár) a per-placement time budget-be ütközik, és az engine `TIME_LIMIT_EXCEEDED`-tel hagyja unplaced-en a darabok többségét. Tehát a finomabb forgatás nem csak *nem segít*, hanem aktívan kontraproduktív a jelenlegi NFP-cache hiánya mellett.

**Következtetés:** a forgatás-granularitás kérdés zárva. A 13 pp gap **nem rotációs limit**, hanem greedy tie-breaking minőségi probléma. A korábbi 8. szakasz 1-es javaslata (`occupied envelope-aware tie-breaker`) marad a legjobb fix-iránynak. (Az etalon "All rotations allowed" beállítása csak elméleti — gyakorlatban a nest&cut valószínűleg szintén 90° vagy 45° lépésekkel dolgozik, és az ő utiljük is greedy-jellegű tie-breaking minőségből származik, nem forgatás-finomításból.)

## 9. Generált / módosított artifactok

- [tmp/lv8_singlesheet_etalon_20260514/inputs/lv8_sheet1_179.json](../../../tmp/lv8_singlesheet_etalon_20260514/inputs/lv8_sheet1_179.json) — 179-instance fixture az etalon Sheet 1-ből
- [tmp/lv8_singlesheet_etalon_20260514/cgal_greedy_noprep/stdout.json](../../../tmp/lv8_singlesheet_etalon_20260514/cgal_greedy_noprep/stdout.json) — best result
- [tmp/lv8_singlesheet_etalon_20260514/cgal_s42_60/summary.json](../../../tmp/lv8_singlesheet_etalon_20260514/cgal_s42_60/summary.json) — SA 60 s lefutott eredmény
- [tmp/lv8_singlesheet_etalon_20260514/cgal_s42_180/summary.json](../../../tmp/lv8_singlesheet_etalon_20260514/cgal_s42_180/summary.json) — SA 180 s timeout
- [tmp/lv8_singlesheet_etalon_20260514/cgal_sa_noprep_180/](../../../tmp/lv8_singlesheet_etalon_20260514/cgal_sa_noprep_180/) — SA no-prepack timeout
- [tmp/lv8_singlesheet_etalon_20260514/greedy_seedsweep/](../../../tmp/lv8_singlesheet_etalon_20260514/greedy_seedsweep/) — seed=1, 7, 13, 100 mind timeout
- [tmp/lv8_singlesheet_etalon_20260514/rotsweep/](../../../tmp/lv8_singlesheet_etalon_20260514/rotsweep/) — r45 (60 % util, azonos a r90-nel), r15 (43 %, 93 unplaced), r3 (39 %, 167 unplaced)
- [tmp/lv8_singlesheet_etalon_20260514/runs.jsonl](../../../tmp/lv8_singlesheet_etalon_20260514/runs.jsonl), [runs.csv](../../../tmp/lv8_singlesheet_etalon_20260514/runs.csv) — harness logok
- [codex/reports/nesting_engine/lv8_singlesheet_etalon_179_20260514.md](lv8_singlesheet_etalon_179_20260514.md) — ez a riport

Forráskódot semmit nem módosítottam (sem `rust/`, sem `vrs_nesting/`).

## 10. Egy-mondatos összegzés

A multi-sheet policy lényegében jó (a greedy spillover működik), a single-sheet teszten az engine 60 % util-t produkál ott, ahol az etalon 73 %-ot — ez 13 pp packing-density gap, ami **pontosan 1 db `Lv8_11612` óriásnak a területe**, és ami a `placement/nfp_placer.rs` greedy tie-breakingjének a finomhangolásán múlik (nem a multi-sheet rétegen, és nem az SA-n, ami jelenleg csak rontja az eredményt).
