# LV8 packing density — fejlesztési terv (v2.1)

**Készült:** 2026-05-15
**Branch / commit:** main / 0cd40b3
**Szerző-kontextus:** Akos Muller iterációs nesting-engine fejlesztés
**Státusz:** PROPOSAL — implementáció előtti tervdokumentum, **agent-delegálható task-kártyákra bontva**

## Revíziók

| Verzió | Dátum | Változások |
|---|---|---|
| v1 | 2026-05-15 (reggel) | Első kiadás: 5 fázis (tie-breaker → cache → 1-step lookahead → full-layout beam → ILS), SA-deprecation kategorikus |
| v2 | 2026-05-15 (este) | Külső szakmai review nyomán: új Phase 0 (mérési higiénia), sorrend-csere (cache → scoring → lookahead → beam → ILS), multi-komponens scoring, critical-part fókusz, LNS terminológia |
| v2.1 | 2026-05-15 (késő este) | Második külső szakmai review nyomán, **kód-ellenőrzött korrekciókkal**: (1) Phase 0.3 polygon-validátor átfogalmazva "AABB-only" → "egyetlen mandatóris CAM-grade gate létrehozása"; (2) **Phase 1 teljesen átírva: nem új cache, hanem a meglévő `nfp/cache.rs` audit + hardening** (a kódellenőrzés igazolta a meglévő `NfpCache` SHA256-shape_id-alapú struktúrát); (3) Phase 2 felosztva 2a / 2b / 2c-re finomabb A/B mérhetőség kedvéért; (4) criticality_score precizálva (geometria-forrás konzisztens, holes kezelt, top-K profile-param a median × 4 helyett); (5) **új Phase 3.5: `nfp_place_starting_from` mint önálló infrastruktúra-fázis**; (6) Phase 4 critical-beam pszeudokódja javítva (`critical_queue.contains()` check, nem ordering-első-K); (7) Phase 5 LNS `accept_worse` valószínűséggel kombinálva (kontrollált random walk-elkerülés); (8) hatás-táblázat szétválasztva acceptance gate / target / expected effect három oszlopra |
| **v2.2 (ez)** | **2026-05-15 (éjszaka)** | Implementáció-előtti döntéshozatal három nyitott kérdésre: (a) **Phase 0 shadow run 3. fixture-családja: [`poc/nesting_engine/f2_4_sa_quality_fixture_v2.json`](../../../poc/nesting_engine/f2_4_sa_quality_fixture_v2.json)** (kód-ellenőrzött, létezik) — kis-synthetic / SA guard céllal; (b) **Phase 1.0 cache path discovery spike** mint kötelező 0.5-1 napos al-lépés a Phase 1 elején (nem külön projektfázis); (c) **`quality_beam_lns_explore` automatikus prob-accept-worse beállítása** `(2.0, 0.05)`-tal a konzervatív `quality_beam_lns`-szel szemben (0, 0) — minden report kötelezően jelöli melyik profile-lal készült. |

## 0. Olvasási útmutató

Ez a doksi 7 fázisban (Phase 0, 1, 2, 3, 3.5, 4, 5) javasolt fejlesztést ír le, amely az LV8-skálájú benchmark `cgal_reference` greedy 60 % sheet-util-ját az ipari etalon (nest&cut) ~73 %-os szintjére közelíti. A fázisok függetlenül szállíthatók és gate-elhetők, **agent-delegálható task-méretben**. Mindegyiknél megadom: **a kódbeli helyét, a cserélendő/új blokkokat, az indoklást a meglévő mérési adatokra hivatkozva, a regressziós felületet, és a várt mérhető hatást három szinten szétválasztva (acceptance gate / target / expected effect).**

**Fontos elv:** az algoritmikus fejlesztések előtt **a mérési pipeline tisztítása** áll (Phase 0). Algoritmikus A/B-mérés csak akkor hiteles, ha (a) a baseline reprodukálható konfundáló változók nélkül, (b) a teljesítmény-metrikák instrumentáltak, és (c) a validitás-gate **egyetlen, kötelező, polygon-aware** út, nem több párhuzamos.

**Delegálási elv:** minden fázis önálló, lezárt PR-ként szállítható, saját teszt-suite-tal, saját report-tal. A `nfp_place_starting_from` mint közös infrastruktúra Phase 3.5-ben külön task, hogy Phase 4 és 5 párhuzamosan szállíthatóak legyenek.

## 1. Háttér és indok

### 1.1 A jelenlegi engine állapota

A három legfrissebb riport adatai alapján ([2-sheet](lv8_2sheet_10mm_600s_claude_code_report.md), [quality_search](lv8_2sheet_10mm_600s_quality_search_20260511.md), [single-sheet etalon](lv8_singlesheet_etalon_179_20260514.md)):

| Mérés | Engine eredmény | Etalon (nest&cut) | Gap |
|---|---:|---:|---:|
| 276-instance / 2 sheet | 189 / 276, 23 % util, 1 sheet | 276 / 276, 69.5 % util, 2 sheet | -87 darab |
| 179-instance / 1 sheet | 178 / 179, **60 % util**, 2 sheet | 179 / 179, **73 % util**, 1 sheet | **-13 pp util** |
| Forgatás-felbontás r45 | azonos 60 % util mint r90 | n/a | nem segít |
| Forgatás-felbontás r15 | 47 % util (rosszabb) | n/a | aktívan kontraproduktív |

### 1.2 A 13 pp gap diagnosztizálása

A 13 pp gap **pontosan 1 db `Lv8_11612` óriás területe** (585 784 mm² = 13.02 % a sheet-en). Az engine a 3 óriásból csak 2-t fér rá a sheet 0-ra, mert:

1. A `Lv8_11612` bbox-a 2522 × 733 mm; egymás mellett párhuzamosan 3 darab a 1500 mm-es táblára nem fér (3 × 743 = 2229 mm).
2. 3 óriás csak akkor fér 1 táblára, ha *interlocking* (különböző orientációjú, egymás konkáv-zsebeibe illesztett) pozíciókban vannak. Ez a `Lv8_11612` ~32 %-os bbox-kitöltési arányát kihasználja.
3. A jelenlegi greedy bottom-left tie-breaker ([nfp_placer.rs:1713-1726](../../../rust/nesting_engine/src/placement/nfp_placer.rs#L1713-L1726)) sosem választaná az interlocking pozíciókat, mert azokat egy alacsonyabb `ty` értékű (bottom-left-ebb) candidate mindig elnyomja.
4. Több forgatás (r45/r15/r3) nem segít: a greedy a finomabb szöget szorosabb *lokális* fit-re használja, és ezzel **növeli** a fragmentációt — r15-tel sheet 0 util **47 %-ra esik**, és **3 sheet** kell mind a 179 darab elhelyezéséhez.

A diagnózis tehát egyértelmű: **a packing minőségi gap a placement-stratégián múlik, nem geometrián / kernel-választáson / forgatás-felbontáson.**

### 1.3 Az irodalmi alap

A javasolt fejlesztési irány az irregular 2D packing standard practice-ével konzisztens:

- **NFP-alapú placement** mainstream irány irregular nestingre (Bennell-Oliveira 2008 tutorial; 2022-es state-of-the-art review).
- **Pair-NFP cache** klasszikus optimalizáció többiterációs nestingben (Burke et al.). A korai SA+NFP munkák explicit cache-t használtak, mert a *computational geometry evaluation* volt a leglassabb komponens.
- **Multi-component candidate scoring** (envelope-growth + contact + fragmentation) a Bennell-Oliveira tutorial-ban explicit ajánlott — a régi SA+NFP munkák convex-hull-area scoring-ot használtak, amiből a mi bbox-growth-unk leegyszerűsítés.
- **Beam search** Bennell-Song (irregular shape packing problem) az ipari benchmark-okon versenyképes eredménnyel.
- **LNS** Imamichi-Yagiura-Nagamochi NFP + iterated local search-t kombinál; több best-known eredményt frissített. Klasszikus destroy/repair szemantika (Shaw 1998, Pisinger-Ropke 2010).

### 1.4 A 2-sheet bug és a packing density összefüggése

A [2-sheet riport](lv8_2sheet_10mm_600s_claude_code_report.md) szerint a teljes 276-instance run minden unplaced darabja `TIME_LIMIT_EXCEEDED` reasont kapott, és minden placement sheet 0-ra került — az engine sosem ugrott át sheet 1-re. Ez **nem önálló bug**, hanem a packing-density gap és az SA inner-eval kombinációjának következménye: az SA első evalja olyan lassú, hogy a `time_limit_sec` deadline mindig a sheet 0 töltése közben szólal meg. Ha a sheet 0 packing density jó, a 276 darabból egy táblára ~200 fér, a maradék ~76 sheet 1-re, és a deadline sosem ott fog tüzelni, ahol most.

**Vagyis a packing density javítása dupla nyereség**: (a) közelít az etalonhoz egyenként-sheet metrikán, (b) a teljes 276-os benchmark `valid` (276/276) PASS gate-jét is megnyitja.

## 2. Architektúra-térkép — érintett kódterület

| Modul | Felelősség | Releváns függvények |
|---|---|---|
| [`rust/nesting_engine/src/placement/nfp_placer.rs`](../../../rust/nesting_engine/src/placement/nfp_placer.rs) | Egy táblás greedy NFP placement | `nfp_place()` [L649](../../../rust/nesting_engine/src/placement/nfp_placer.rs#L649), `sort_and_dedupe_candidates()` [L1709](../../../rust/nesting_engine/src/placement/nfp_placer.rs#L1709), `append_candidates()` [L1845](../../../rust/nesting_engine/src/placement/nfp_placer.rs#L1845), `order_parts_for_policy()` [L1676](../../../rust/nesting_engine/src/placement/nfp_placer.rs#L1676) |
| [`rust/nesting_engine/src/placement/blf.rs`](../../../rust/nesting_engine/src/placement/blf.rs) | BLF placer + típusok | `PlacementResult`, `PlacedItem` [L119-136](../../../rust/nesting_engine/src/placement/blf.rs#L119-L136) |
| [`rust/nesting_engine/src/multi_bin/greedy.rs`](../../../rust/nesting_engine/src/multi_bin/greedy.rs) | Több táblás greedy + stop policy | `MultiSheetResult` [L197](../../../rust/nesting_engine/src/multi_bin/greedy.rs#L197), `OccupiedExtentI64` [L231](../../../rust/nesting_engine/src/multi_bin/greedy.rs#L231), `NfpCache` használat [L646](../../../rust/nesting_engine/src/multi_bin/greedy.rs#L646), [L736](../../../rust/nesting_engine/src/multi_bin/greedy.rs#L736) |
| [`rust/nesting_engine/src/nfp/cache.rs`](../../../rust/nesting_engine/src/nfp/cache.rs) | **NFP cache (létezik)** — `NfpCacheKey` SHA256 shape_id-vel | `NfpCache` [L41](../../../rust/nesting_engine/src/nfp/cache.rs#L41), `NfpCacheKey` [L24-31](../../../rust/nesting_engine/src/nfp/cache.rs#L24-L31), `shape_id()` [L101](../../../rust/nesting_engine/src/nfp/cache.rs#L101), `MAX_ENTRIES = 10_000` [L16](../../../rust/nesting_engine/src/nfp/cache.rs#L16), `clear_all()` [L72](../../../rust/nesting_engine/src/nfp/cache.rs#L72) |
| [`rust/nesting_engine/src/search/sa.rs`](../../../rust/nesting_engine/src/search/sa.rs) | Simulated annealing search | `eval_state_cost_with_result()` [L450](../../../rust/nesting_engine/src/search/sa.rs#L450), `run_sa_search_over_specs()` [L232](../../../rust/nesting_engine/src/search/sa.rs#L232) |
| [`rust/nesting_engine/src/nfp/concave.rs`](../../../rust/nesting_engine/src/nfp/concave.rs) | OldConcave NFP kernel | `compute_stable_concave_nfp()` [L226-313](../../../rust/nesting_engine/src/nfp/concave.rs#L226-L313) |
| [`rust/nesting_engine/src/feasibility/`](../../../rust/nesting_engine/src/feasibility/) | `can_place`, narrow-phase, AABB | (modulszintű) — **polygon-aware logika létezik itt** |
| [`worker/cavity_validation.py`](../../../worker/cavity_validation.py) | Polygon-aware cavity validation | `validate_cavity_plan_v2()` — **CAM-grade validáció elérhető** |
| [`vrs_nesting/config/nesting_quality_profiles.py`](../../../vrs_nesting/config/nesting_quality_profiles.py) | Quality-profile registry | `_QUALITY_PROFILE_REGISTRY` [L38-69](../../../vrs_nesting/config/nesting_quality_profiles.py#L38-L69) |
| [`scripts/experiments/lv8_2sheet_claude_search.py`](../../../scripts/experiments/lv8_2sheet_claude_search.py) | LV8 benchmark harness | full file |
| [`scripts/experiments/lv8_2sheet_claude_validate.py`](../../../scripts/experiments/lv8_2sheet_claude_validate.py) | **Jelenlegi AABB-only LV8 validator script** | full file (~conservative, nem CAM-grade) |

Két fontos invariáns:

- A `PlacementResult` (`{placed, unplaced}`) az engine output kontraktusa.
- A `NestSheet` fixture-séma változatlan.

## 3. Fejlesztési fázisok

**Sorrendiségi indoklás:**

- **Phase 0** mérési higiénia.
- **Phase 1** a meglévő NFP cache **auditja és keményítése** (nem új cache építése).
- **Phase 2** algoritmikus nyereség, lépcsőzött scoring (2a / 2b / 2c).
- **Phase 3** critical-part lookahead.
- **Phase 3.5** `nfp_place_starting_from` mint **önálló infrastruktúra-fázis** — Phase 4 és 5 előfeltétele.
- **Phase 4** critical-only beam.
- **Phase 5** LNS refinement.

| Fázis | Funkció | Becslés idő | Várt util-növekedés | Függőség |
|------:|---|---:|---:|---|
| **0** | Mérési higiénia: SA off, NFP diag gate, mandatóris polygon-aware gate, instrumentáció | 3-4 nap | 0 (mérési stabilitás) | nincs |
| **1** | **NfpCache audit + hardening** (létező `cache.rs` használat-audit, LRU-csere ha kell, stats export) | 2-3 nap | nincs közvetlen util-haszon | Phase 0 |
| **2a** | bbox-growth scoring MVP | 1-2 nap | +2-3 pp | Phase 1 |
| **2b** | + extent_penalty | 1 nap | további +1 pp | Phase 2a |
| **2c** | + contact_bonus (opt-in, runtime-cap-pal) | 2-3 nap | további +1-2 pp | Phase 2b |
| **3** | Critical-part lookahead 1-step | 3-4 nap | további +2-3 pp | Phase 1, 2 |
| **3.5** | **`nfp_place_starting_from` infrastruktúra** (önálló fázis) | 3-4 nap | 0 (infrastruktúra) | Phase 1 |
| **4** | Critical-only beam (csak critical_queue elemen aktív) | 3-4 nap | további +3-5 pp | Phase 1, 2, 3, 3.5 |
| **5** | LNS refinement, accept-equal + opcionális prob-accept-worse | 5-6 nap | további +3-8 pp | Phase 3.5 (kötelező) |

---

### Phase 0 — Mérési higiénia és instrumentáció

**Célja:** algoritmikus fejlesztés előtt minden konfundáló változó eltávolítása. Az új mérési baseline reprodukálható, instrumentált, **egyetlen kötelező CAM-grade validációs gate-en megy át**.

**0.1 SA eltávolítása a default quality path-ból + shadow run protokoll**

A [vrs_nesting/config/nesting_quality_profiles.py:38-69](../../../vrs_nesting/config/nesting_quality_profiles.py#L38-L69)-ban a `quality_default` és `quality_aggressive` `"search": "sa"` mezőjét `"search": "none"`-ra cseréljük. A `quality_cavity_prepack*` profile-okat deprecated-jelölővel a registry-ben hagyjuk, de a default registry-listából kivesszük.

**Shadow run protokoll (kötelező, nem opcionális):**
- 1 hetes párhuzamos futtatás **3 konkrét reprezentatív fixture-családon**:
  1. **LV8 család:**
     - `tmp/lv8_singlesheet_etalon_20260514/inputs/lv8_sheet1_179.json` (179-instance single-sheet subset)
     - `tests/fixtures/nesting_engine/ne2_input_lv8jav.json` (276-instance full 2-sheet benchmark)
  2. **web_platform / contract_freeze család:** az aktuális contract-freeze regression fixture-ek, melyeket a [`codex/goals/canvases/web_platform/`](../../goals/canvases/web_platform/) canvas-ok aktívan használnak (a konkrét fixture-listát a Phase 0 első nappal egyeztetjük a benchmark-suite mai állapotából).
  3. **Kis-synthetic / SA guard család:**
     - **Elsődleges választás:** [`poc/nesting_engine/f2_4_sa_quality_fixture_v2.json`](../../../poc/nesting_engine/f2_4_sa_quality_fixture_v2.json) — meglévő, kis méretű SA-quality fixture (a repo-ban már szerepel és a harness-szel futtatható).
     - **Fallback (csak ha az elsődleges nem reprezentatív vagy nem futtatható a mai harness-szel):** új ad-hoc `tmp/shadow_small_synthetic_sa_guard.json` fixture, ami célzottan a SA-előny lehetőségét védi (kis példányszám, SA-konvergencia-friendly geometria).
- A régi (`search=sa`) és új (`search=none`) profile-ok eredményeit mind summary.json-ben rögzítjük, **per fixture-családonként külön**.
- Deprecation warning a logba, ha downstream caller még a régi profile-t használja.
- **Hard-cut kritérium:** a shadow run **mindhárom** fixture-családon azt mutatja, hogy a no-SA *jobb vagy egyenlő* placed_instances ÉS *jobb vagy egyenlő* util_pct értéket ad. Ha bármelyik család regresszióval rendelkezik (akár a kis-synthetic-en), a hard-cut elhalasztva és a Phase 0 scope bővítve egy "SA-retention sub-profile" definíciójával.

**Indoklás:** a SA empirikusan a greedy 60 %-ot **lerontja** 8.7 %-ra ([single-sheet riport 4. szakasz](lv8_singlesheet_etalon_179_20260514.md)). A shadow run megerősíti, hogy ez nem LV8-specifikus.

**0.2 NFP diagnostic stderr env-gate**

A [`rust/nesting_engine/src/nfp/concave.rs:226-313`](../../../rust/nesting_engine/src/nfp/concave.rs#L226-L313)-ben minden `[CONCAVE NFP DIAG]` `eprintln!` egy `if std::env::var_os("NESTING_ENGINE_NFP_DIAG").is_some() { ... }` mögé kerül. Default: csendes.

**Indoklás:** a 2-sheet riport szerint 240 s alatt ~10 MB stderr halmozódik. A [`scripts/experiments/lv8_2sheet_claude_search.py:175-181`](../../../scripts/experiments/lv8_2sheet_claude_search.py#L175-L181) ezt jelenleg `/dev/null`-ba dobással kerüli ki — ez a workaround a Phase 0 után el kell tűnjön.

**0.3 Egyetlen kötelező CAM-grade benchmark-validation gate**

**Pontos helyzet:** a polygon-aware validációs logika **több helyen létezik** a repo-ban:
- `feasibility::can_place` (engine narrow-phase, polygon-aware)
- `worker.cavity_validation.validate_cavity_plan_v2` (polygon-aware overlap/clearance/boundary check)
- `i_overlay` boolean ops a CFR-ben

A probléma viszont: **a jelenlegi LV8 benchmark harness által hívott validator-script** ([`scripts/experiments/lv8_2sheet_claude_validate.py`](../../../scripts/experiments/lv8_2sheet_claude_validate.py)) **AABB-only** ("conservative validator"), és a 2-sheet riport [L141-154](lv8_2sheet_10mm_600s_claude_code_report.md#L141-L154) szerint LV8 konkáv L-alakokra nem definitív (41 boundary "violation", 167 AABB-overlap pair, 101 spacing — egyik sem CAM-grade verdict).

**A feladat tehát nem új validátor írása, hanem az egységesítés:**
- Egyetlen, kötelező, polygon-aware validációs gate definiálása **minden LV8 (és általában >= 50 instance LV8-jellegű) benchmark run végén**.
- Implementáció-választás: vagy (a) drop-in csere a meglévő `lv8_2sheet_claude_validate.py`-n keresztül a `worker.cavity_validation`-re, vagy (b) új vékony Rust CLI a `feasibility::can_place` köré, amely `{overlap_count, clearance_count, boundary_count}`-ot ad vissza per sheet.
- Az integráció kötelező a `summary.json` `valid` mezőjének definíciójában: `valid = true` csak akkor, ha mind a quantity-gate, mind a polygon-validation gate igaz.
- A meglévő `lv8_2sheet_claude_validate.py` (AABB-only) `legacy_aabb_validator: true` mezővel megmarad mint *kiegészítő* diagnosztikai eszköz, de a binding gate definíciójában nem szerepel.

**Indoklás:** mielőtt bármilyen util-növekedést mérünk, kell egy egységes, CAM-grade verdict-fa, különben a "67 %-os util" claim AABB-only `valid` mellett valójában lehet 90 % polygon-overlap. A v2 itt pontatlan volt ("AABB-only validátor van"); a v2.1 helyes fogalmazása: "egyetlen kötelező polygon-aware gate kell, a meglévő logikákra építve".

**0.4 Engine instrumentáció**

A meglévő [`NfpPlacerStatsV1`](../../../rust/nesting_engine/src/placement/nfp_placer.rs#L344) bővítése (vagy új `NfpPlacerStatsV2`):

```rust
pub struct NfpPlacerStatsV2 {
    // (existing v1 fields)
    pub nfp_compute_count: u64,
    pub nfp_cache_hit_count: u64,       // ÚJ — a meglévő NfpCache stats().hits-ből
    pub nfp_cache_miss_count: u64,      // ÚJ — a meglévő NfpCache stats().misses-ből
    pub nfp_cache_entries_end: u64,     // ÚJ — a meglévő NfpCache stats().entries-ből
    pub nfp_cache_clear_all_events: u64,// ÚJ — clear_all() hányszor tüzelt (LRU-átállásig fontos)
    pub can_place_call_count: u64,      // ÚJ
    pub candidate_generate_count: u64,  // ÚJ
    pub sheet_spillover_count: u64,     // ÚJ — multi_bin szintű
    pub per_part_wall_ns: Vec<(String, u64)>,  // ÚJ — per-part-id idő-bontás
}
```

A statisztikák a `solver_stdout.json`-be kerülnek (`engine_stats: {...}`), és a [`lv8_2sheet_claude_search.py`](../../../scripts/experiments/lv8_2sheet_claude_search.py) `summary.json`-jában is rögzítve.

**0.5 Új baseline-mérés**

Minden Phase 0 sub-task után, *implementáció előtt*, baseline újra-mérés:
- LV8 sheet1 fixture (179 instance), greedy NFP r90 seed=42, `quality_default` (új, search=none).
- Várt eredmény: 178/179 placed, sheet 0 util ~60 %, wall ~190 s.
- A stats output és a polygon-aware `valid` verdict kerüljön be a riportba; ez lesz a Phase 1+ A/B baseline.

**Acceptance gate / target / expected effect:**

| | Phase 0 |
|---|---|
| **Acceptance gate** | Snapshot-tesztek 0 diff, shadow run lezárult, `valid` gate polygon-aware, stats summary.json-ben |
| **Target** | LV8 sheet1 baseline reproduktív sigmával < 5 % wall, mandatóris CAM-grade verdict minden runen |
| **Expected effect** | 0 pp util-változás, mérési zaj megszüntetése, ~10-20 s wall-megtakarítás stderr-spam kiiktatásával |

**Regressziós felület:** alacsony.

---

### Phase 1 — NfpCache audit + hardening

**Helye:** a már létező [`rust/nesting_engine/src/nfp/cache.rs`](../../../rust/nesting_engine/src/nfp/cache.rs) **auditálása és keményítése** — nem új cache építése.

**A meglévő struktúra (kód-ellenőrzött):**

```rust
// rust/nesting_engine/src/nfp/cache.rs:24-31
pub struct NfpCacheKey {
    pub shape_id_a: u64,
    pub shape_id_b: u64,
    pub rotation_steps_b: i16,
    pub nfp_kernel: NfpKernel,
}

// L101 — shape_id az inflated, canonicalized polygonból SHA256-tal
pub fn shape_id(poly: &Polygon64) -> u64 { ... }

// L16, L64-67 — MAX_ENTRIES=10000, és clear_all() ha tele
pub const MAX_ENTRIES: usize = 10_000;
impl NfpCache {
    pub fn insert(&mut self, key: NfpCacheKey, nfp: Polygon64) {
        if self.store.len() >= MAX_ENTRIES { self.clear_all(); }   // NEM LRU
        ...
    }
}
```

A `multi_bin/greedy.rs:646` egyszer hoz létre `nfp_cache: NfpCache::new()`-t a teljes multi-sheet run elején, és a `:736`-nél minden sheet-iterációban átadja. **A cache lifetime tehát már multi-sheet scope** (ezt is verifikáltuk).

**Phase 1 valódi feladatai (audit + hardening, nem from-scratch):**

**1.0 Cache path discovery spike (0.5-1 nap, kötelező első al-lépés)**

A teljes 3-napos audit + hardening megkezdése előtt **rövid spike** a tényleges használati-kép feltérképezésére. Ezzel megelőzzük, hogy a Phase 1 valódi scope-ja csak az implementáció közben derüljön ki.

A spike outputja **rövid, gépiesen ellenőrizhető Markdown jelentés** ([`tmp/phase1_spike_cache_path_discovery.md`](../../../tmp/phase1_spike_cache_path_discovery.md)) a következő fix struktúrával:

```markdown
# Phase 1.0 cache path discovery spike — output

## NFP call graph
- list every fn that COULD call NFP computation
- mark which of those actually go through NfpCache::get_or_insert
- mark which BYPASS the cache (if any)

## Per-kernel cache usage
- OldConcave path: cache-passing? where (file:line)?
- cgal_reference path: cache-passing? where (file:line)?
- reduced_convolution path (if active): cache-passing?

## shape_id origin verification
- Is the polygon passed to shape_id() inflated or nominal?
- Test: two NfpCache::insert calls with same part_id but different spacing_mm:
  do they produce different shape_ids? (Y/N + measurement)

## LRU vs clear_all decision input
- LV8 fixture run: clear_all_events count
- contract_freeze fixture run: clear_all_events count
- f2_4_sa_quality_fixture_v2.json run: clear_all_events count
- Decision: LRU needed now? (Y/N + reasoning)

## pipeline_version field need (audit answer)
- Are there two pipelines (e.g., raw fixture vs cavity_prepack_v2)
  that produce IDENTICAL inflated polygons but DIFFERENT downstream NFP?
- If yes: pipeline_version field is REQUIRED.
- If no: not needed.

## Phase 1 full audit revised estimate
- Original estimate: 3 days
- Revised estimate based on spike findings: X days
- Specific risks discovered: ...
```

**Acceptance a spike-ra:**
- Jelentés a megadott struktúrával létezik.
- Minden NFP-hívási út besorolva (cache-hit/miss mérhető vagy bypass).
- Minden kernel állapota (cache-szal/nélkül) dokumentálva.
- Az LRU-vs-clear_all döntés konkrét mérési számokkal indokolva.
- Phase 1 új scope-becslése (max +1-2 nap, ha bug-okat talál).

Ha a spike azt mutatja, hogy **minden tiszta** (mindenhol cache, shape_id inflated, clear_all_events = 0 mind a 3 fixture-on, nincs pipeline-divergence), akkor a maradék ~2 nap a stats-bővítésre és a tesztekre fókuszálódik. Ha bármi nem-tiszta, a Phase 1 scope automatikusan +1-2 nap.

**1.1 Használat-audit:**
Ellenőrizni, hogy minden NFP-hívási úton hívott-e a cache. Konkrét hívások:
- `compute_nfp_lib()` [`nfp_placer.rs:1786`](../../../rust/nesting_engine/src/placement/nfp_placer.rs#L1786) — cache check + insert
- `compute_stable_concave_nfp()` [`nfp/concave.rs:226`](../../../rust/nesting_engine/src/nfp/concave.rs#L226) — végpont vagy belső hívás?
- A `cgal_reference` provider [`nfp/cgal_reference_provider.rs`](../../../rust/nesting_engine/src/nfp/cgal_reference_provider.rs) — cache-szal vagy nélküle?

**Acceptance:** új unit teszt, ami egy szintetikus 2-part fixture-en a 3. NFP-hívás cache-hit-et generál, függetlenül attól, hogy melyik kernel.

**1.2 shape_id inflated-geometry verifikáció:**
A `shape_id()` jelenleg a Polygon64-en operál. Ellenőrizni:
- Az `inflated_polygon` (spacing-inflációval) van-e a polygonon, amit hash-elünk, vagy a `nominal` polygon?
- Két különböző `spacing_mm`-mel létrejövő `inflated_polygon` különböző shape_id-t kap-e?

**Acceptance:** új unit teszt: ugyanazon a part-id-n a spacing-változás más shape_id-t ad. Ha ez **nem** igaz, akkor egy `pipeline_version` mező kerül a `NfpCacheKey`-be (verzión tagolva: `enum PipelineVersion { V1, V2_CavityPrepack }`), vagy `spacing_um` explicit mezőként.

**1.3 LRU átállás (a `clear_all` cseréje, ha a benchmark mutatja, hogy fontos):**
A jelenlegi `clear_all` viselkedés: amint a cache 10 000 bejegyzéssel telik, **mindent kidob**. LV8 fixture-en kis méretű (~1152 unique pair, 12 type × 4 rot), nem éri el a határt. **De más fixture-ön elérheti.**

**Acceptance:**
- Új stats counter `clear_all_events` méri, hányszor tüzelt a clear_all egy run alatt.
- Phase 0 baseline és más fixture-ek mérése után döntés: ha `clear_all_events > 0` valamelyik fixture-en, LRU-ra átállítjuk (`hashlink::LruCache` vagy custom). Ha mindig 0, marad clear_all (egyszerűbb).

**1.4 Stats export bővítés:**
A `NfpCache::stats()` jelenleg `{hits, misses, entries}`. Bővítjük:
```rust
pub struct CacheStats {
    pub hits: u64,
    pub misses: u64,
    pub entries: usize,
    pub clear_all_events: u64,    // ÚJ
    pub peak_entries: usize,      // ÚJ — max(entries) over the run
}
```
A stats a `NfpPlacerStatsV2`-be megy és summary.json-ben rögzítve.

**Indoklás:**
- A v2-ben javasolt új `pair_cache.rs` **felesleges**: a meglévő `cache.rs` SHA256-shape_id-vel az "inflated polygon hash" funkcionalitást már lefedi, csak a használat-pattern és LRU-stratégia auditra szorul.
- A v2-ben javasolt `spacing_um` mező **felesleges**: ha a shape_id az inflated polygonból jön, a spacing automatikusan megjelenik a hash-ben.
- A `pipeline_version` mező **feltételes**: csak akkor jön be a kulcsba, ha a cache-audit kimutatja, hogy ugyanabból a part-id-ből különböző pipeline-ágakon (pl. cavity_prepack v1 vs v2) **azonos inflated polygon** generálódik. Akkor a polygon-hash nem elég, és egy verzió-szegregáló mező kell.

**Env-gate:**
- `NESTING_ENGINE_CACHE_LRU=0|1` (csak ha 1.3 alapján kell)

**Acceptance gate / target / expected effect:**

| | Phase 1 |
|---|---|
| **Acceptance gate** | Audit-jelentés a 1.1-1.2 lépésekről, új unit-tesztek zöldek, snapshot-tesztek 0 diff, stats export `summary.json`-ben |
| **Target** | Cache hit rate ≥ 80 % a 2. placement-tól kezdve LV8 fixture-en, clear_all_events = 0 az LV8 fixture-en |
| **Expected effect** | LV8 sheet1 wall time 192 s → 80-100 s (a meglévő cache hatékonyabb kihasználásától); 0 pp util-változás |

**Regressziós felület:** alacsony. A cache audit feltétele a "látható-de-nem-rossz" — vagy mind hívva van (jó), vagy van ahol nem (akkor javítva). Bug-bevezetés esélye minimális.

---

### Phase 2 — Multi-komponens candidate scoring (lépcsőzött)

**Helye:** [`nfp_placer.rs:1709-1726`](../../../rust/nesting_engine/src/placement/nfp_placer.rs#L1709-L1726) — `sort_and_dedupe_candidates`.

**Jelenlegi:** pure lex `(ty, tx)` ordering = bottom-left fill.

**Lépcsőzött bevezetés három sub-fázisban:**

#### Phase 2a — bbox-growth MVP

```rust
fn score_candidate_bbox_growth(
    candidate_aabb: &Aabb,
    placed_extent: &OccupiedExtentI64,
) -> i128 {
    let new_min_x = candidate_aabb.min_x.min(placed_extent.min_x);
    let new_max_x = candidate_aabb.max_x.max(placed_extent.max_x);
    let new_min_y = candidate_aabb.min_y.min(placed_extent.min_y);
    let new_max_y = candidate_aabb.max_y.max(placed_extent.max_y);
    let w = (new_max_x - new_min_x) as i128;
    let h = (new_max_y - new_min_y) as i128;
    w.saturating_mul(h).saturating_add(w + h)
}
```

Env-gate: `NESTING_ENGINE_TIE_BREAKER=bbox_growth`.

**Acceptance gate / target / expected effect (Phase 2a):**

| | Phase 2a |
|---|---|
| **Acceptance gate** | Snapshot-tesztek 0 diff (env-off), új unit teszt zöld, runtime overhead ≤ +10 % vs Phase 1, LV8 sheet1 util ≥ **62 %** |
| **Target** | LV8 sheet1 util **63 %** (+3 pp baseline-hoz) |
| **Expected effect** | +2-3 pp util |

#### Phase 2b — + extent_penalty

```rust
fn score_candidate_bbox_growth_with_extent(...) -> i128 {
    let bbox = score_candidate_bbox_growth(...);
    let extent_pen = (new_max_x - bin_aabb.min_x).max(0) as i128
                   + (new_max_y - bin_aabb.min_y).max(0) as i128;
    bbox.saturating_add(extent_pen.saturating_mul(EXTENT_WEIGHT))
}
```

`EXTENT_WEIGHT = 1` default (env-tunable: `NESTING_ENGINE_TIE_BREAKER_EXTENT_W`).

Env-gate: `NESTING_ENGINE_TIE_BREAKER=bbox_growth_extent`.

**Indoklás:** a `Lv8_11612` óriás 2522 mm magas. Ha a 2. óriás placement-je 2532 mm-re extendálja a layoutot, a 3. óriás max 488 mm-es szegmensbe kerülhet. Az `extent_penalty` ezt **direkt bünteti**, nem várja meg, hogy a bbox-area-ban megjelenjen.

**Acceptance gate / target / expected effect (Phase 2b):**

| | Phase 2b |
|---|---|
| **Acceptance gate** | Phase 2a acceptance + 2b sub-cumulative LV8 sheet1 util ≥ **63.5 %** |
| **Target** | LV8 sheet1 util **64 %** (cumulative) |
| **Expected effect** | további +0.5-1 pp |

**Phase 2b csak akkor marad bekapcsolva**, ha a 2a baseline-hoz képest legalább 0.5 pp javulást ad runtime-overhead nélkül. Ellenkező esetben default-off, env-en be lehet kapcsolni.

#### Phase 2c — + contact_bonus (opt-in)

**Csak akkor implementáljuk, ha Phase 2a + 2b nem hoz elég util-emelkedést a Phase 3 előfeltételéhez** (Phase 3 várt baseline-ja: 64-65 % util).

```rust
fn contact_length_bonus(
    candidate_polygon: &Polygon64,
    placed_polygons: &[&Polygon64],
    bin: &Polygon64,
) -> i128 {
    // A candidate inflated polygon perimeterje, amely "érintkezik" placed polygonokkal
    // vagy a bin szélével (≤ EPS_CONTACT_MM distance).
    // Implementáció: edge-pair AABB pre-reject + i-overlay distance query.
    // Cost: O(candidate_edges × nearby_placed_edges)
}
```

**Hard runtime cap (kötelező):** ha a contact_bonus számítása > 50 ms egy placement-re, fallback-eljük a Phase 2b score-ra. Ez egy `contact_bonus_timeout_count` counterben mérve.

Env-gate: `NESTING_ENGINE_TIE_BREAKER=bbox_growth_extent_contact`.

**Acceptance gate / target / expected effect (Phase 2c):**

| | Phase 2c |
|---|---|
| **Acceptance gate** | Phase 2b acceptance + runtime overhead ≤ +20 % vs Phase 2b, contact_bonus_timeout_count ≤ 5 % per run, LV8 sheet1 util ≥ **65 %** |
| **Target** | LV8 sheet1 util **66 %** (cumulative) |
| **Expected effect** | további +1-2 pp |

**Phase 2 összes tesztelés:**
- Unit: 3 darab szintetikus fixture, ahol mindhárom scoring más candidate-et választ; assert választás-különbség.
- Integration: LV8 sheet1 fixture, Phase 2a → 2b → 2c sorrendben kumulatív mérés.
- A/B mérés (Phase 0 instrumentációval): candidate_dedup_count, can_place_call_count konzisztensek a sub-fázisokban (a scoring csak a sorrendet változtatja).

---

### Phase 3 — Critical-part-focused lookahead

**Helye:** [`nfp_placer.rs:649+`](../../../rust/nesting_engine/src/placement/nfp_placer.rs#L649) — `nfp_place` fő loopjának belső blokkjában.

**Critical-part definíció (precízen):**

```rust
fn criticality_score(spec: &InflatedPartSpec) -> f64 {
    // 1. bbox_area és polygon_area UGYANABBÓL a geometriából (mindkettő inflated):
    let bbox_area = (spec.inflated_bbox.max_x - spec.inflated_bbox.min_x) as f64
                   * (spec.inflated_bbox.max_y - spec.inflated_bbox.min_y) as f64;

    // 2. polygon_area = outer_area - holes_area (a meglévő spec.nominal_area_mm2
    //    értelemszerűen ezt kell, hogy adja; auditra szorul)
    let poly_area = spec.inflated_net_area_mm2;   // ÚJ field, ha még nincs

    // 3. Rotációfüggő bbox: az allowed_rotations_deg-en a min bbox-area-t használjuk
    //    (mert a part ezt fogja választani placement-kor, ha mérete számít)
    let bbox_area_min_rot = spec.allowed_rotations_deg.iter()
        .map(|&deg| rotated_bbox_area(&spec.inflated_polygon, deg))
        .fold(f64::INFINITY, f64::min);

    let bbox_fill_ratio = poly_area / bbox_area_min_rot;
    bbox_area_min_rot * (1.0 - bbox_fill_ratio)
}
```

**Critical-queue építés profile-paraméterrel** (nem magic number):

```rust
const ENV_CRITICAL_TOP_K_TYPES: &str = "NESTING_ENGINE_CRITICAL_TOP_K_TYPES";       // default: 3
const ENV_CRITICAL_TOP_K_INSTANCES: &str = "NESTING_ENGINE_CRITICAL_TOP_K_INSTANCES"; // default: 20

fn build_critical_queue(ordered: &[InflatedPartSpec]) -> VecDeque<(usize, u32)> {
    let top_k_types = env_var_usize(ENV_CRITICAL_TOP_K_TYPES, 3);
    let top_k_instances = env_var_usize(ENV_CRITICAL_TOP_K_INSTANCES, 20);

    let mut scored: Vec<(f64, usize)> = ordered.iter().enumerate()
        .map(|(idx, s)| (criticality_score(s), idx))
        .collect();
    scored.sort_by(|a, b| b.0.partial_cmp(&a.0).unwrap());

    let mut queue = VecDeque::new();
    for &(_, part_idx) in scored.iter().take(top_k_types) {
        let qty = ordered[part_idx].quantity;
        for instance in 0..qty {
            queue.push_back((part_idx, instance));
            if queue.len() >= top_k_instances {
                return queue;
            }
        }
    }
    queue
}
```

**LV8 fixture-en a default `top_k_types=3, top_k_instances=20`** a 3 db `Lv8_11612` + 4 db `Lv8_15348` + ~13 db egyéb top-area-critical part-ot kapja be (~14 instance). Más fixture-ön a profile-ban override-olható.

**Lookahead implementáció:**

```rust
fn select_with_critical_lookahead(
    candidates: &[Candidate],
    placed_for_nfp: &[PlacedPart],
    critical_queue: &VecDeque<(usize, u32)>,
    current_position: (usize, u32),
    base_specs: &[InflatedPartSpec],
    bin: &Polygon64,
    nfp_cache: &mut NfpCache,            // a meglévő cache, nem új
) -> Option<Candidate> {
    let next_critical = critical_queue.iter()
        .find(|&&(pi, ii)| (pi, ii) > current_position)
        .copied();

    let Some((next_pi, _)) = next_critical else {
        return candidates.first().cloned();    // fallback pure bottom-left
    };

    let next_part = &base_specs[next_pi];

    let mut best: Option<(i128, &Candidate)> = None;
    for cand in candidates.iter().take(LOOKAHEAD_CANDIDATE_CAP) {
        let mut placed_temp = placed_for_nfp.to_vec();
        place_into(&mut placed_temp, cand, /* part info */);
        let next_can_fit = quick_feasibility(next_part, &placed_temp, bin, nfp_cache);
        let penalty = if next_can_fit { 0 } else { CRITICAL_BLOCK_PENALTY };
        let local_score = score_candidate_multi(cand, /* ... */);
        let combined = local_score.saturating_add(penalty);
        if best.as_ref().map_or(true, |(s, _)| combined < *s) {
            best = Some((combined, cand));
        }
    }
    best.map(|(_, c)| c.clone())
}

const LOOKAHEAD_CANDIDATE_CAP: usize = 16;
const CRITICAL_BLOCK_PENALTY: i128 = 1_000_000_000;
```

**Env-gate:** `NESTING_ENGINE_LOOKAHEAD=off|critical_1step`

**Acceptance gate / target / expected effect:**

| | Phase 3 |
|---|---|
| **Acceptance gate** | Snapshot 0 diff (off), unit teszt zöld (szintetikus 2-giant fixture), runtime overhead ≤ +30 % vs Phase 2c (Phase 1 cache hit-tel), LV8 sheet1 util ≥ **65 %** |
| **Target** | LV8 sheet1 util **67 %** (cumulative) |
| **Expected effect** | további +2-3 pp |

---

### Phase 3.5 — `nfp_place_starting_from` infrastructure (új, önálló fázis)

**Indoklás a kiemelésre:** mind Phase 4 (critical-only beam → greedy folytatás), mind Phase 5 (LNS repair) használja ezt a fn-t. A v1 80-soros becslése irreális; valós méret **200-300 sor + 5 unit teszt**. Ezért **önálló fázis**, hogy:
- Phase 4 és Phase 5 párhuzamosan szállíthatóvá váljon
- A state-rekonstrukció külön teszt-suite-ot kapjon
- Egy delegált agent kártyája ne legyen overloadelt egy mellékhajtással

**Helye:** új `pub fn` a [`nfp_placer.rs`](../../../rust/nesting_engine/src/placement/nfp_placer.rs)-ben.

**Szignatúra:**

```rust
pub fn nfp_place_starting_from(
    initial_placements: Vec<PlacedItem>,     // részben kész layout
    remaining_parts: Vec<InflatedPartSpec>,  // a folytatandó parts
    base_specs: &[InflatedPartSpec],          // (eredeti specifikációk lookup-hoz)
    bin_polygon: &Polygon64,
    stop: &mut StopPolicy,
    cache: &mut NfpCache,                    // a meglévő cache
    stats: &mut NfpPlacerStatsV2,
    order_policy: PartOrderPolicy,
) -> PlacementResult
```

**State-rekonstrukció lépései** (~200-300 LOC):
1. `placed_state: PlacedIndex` rebuild az `initial_placements`-ből (spatial index).
2. `placed_for_nfp: Vec<PlacedPart>` rebuild a placements-ből.
3. `placed: Vec<PlacedItem>` = clone of `initial_placements`.
4. `unplaced: Vec<UnplacedItem>` = empty.
5. A meglévő `nfp_place` fő loopjának fent-startoló (`remaining_parts`-ot iteráló) verzióját futtatni.

**Kötelező tesztek:**

```rust
// rust/nesting_engine/tests/nfp_place_starting_from.rs

#[test]
fn empty_prefix_equivalence() {
    // nfp_place_starting_from(empty, parts, ...) == nfp_place(parts, ...)
    let result_normal = nfp_place(&parts, ...);
    let result_resumed = nfp_place_starting_from(vec![], parts.clone(), ...);
    assert_eq!(result_normal.placed, result_resumed.placed);
    assert_eq!(result_normal.unplaced, result_resumed.unplaced);
}

#[test]
fn prefix_continuation_determinism() {
    // Run nfp_place; split halfway; verify resumed gives same end-state.
    let full = nfp_place(&parts, ...);
    let split_idx = full.placed.len() / 2;
    let prefix = full.placed[..split_idx].to_vec();
    let remaining_parts = compute_remaining_after_prefix(&parts, &prefix);
    let resumed = nfp_place_starting_from(prefix, remaining_parts, ...);
    // The last (len/2) placements should match.
    assert_eq!(full.placed[split_idx..], resumed.placed[split_idx..]);
}

#[test]
fn empty_remaining_returns_initial() {
    // nfp_place_starting_from(prefix, empty, ...) == { placed: prefix, unplaced: empty }
    ...
}

#[test]
fn lv8_sheet1_starting_from_3_giants_completes() {
    // Manuálisan-elhelyezett 3 Lv8_11612 + folytatás greedyvel
    ...
}

#[test]
fn stats_counters_continue_correctly() {
    // nfp_compute_count, cache_hit/miss valid a folytatás után
    ...
}
```

**Env-gate:** nincs — ez infrastruktúra, nem viselkedés-változtatás. A `pub fn nfp_place` változatlan marad.

**Acceptance gate / target / expected effect:**

| | Phase 3.5 |
|---|---|
| **Acceptance gate** | Mind az 5 unit teszt zöld, snapshot-tesztek 0 diff, `pub fn nfp_place` aláírása és viselkedése változatlan |
| **Target** | Egy újrahasznosítható infrastruktúra Phase 4 és Phase 5 számára |
| **Expected effect** | 0 pp util-változás (infrastruktúra-fázis) |

**Regressziós felület:** közepes. A state-rekonstrukció rögtön szivároghat (PlacedIndex spatial-index inicializálás, NFP cache continuity). Ezért **dedikált unit teszt-suite**, nem inline teszt Phase 4 vagy 5-ben.

---

### Phase 4 — Critical-only beam search (precíz pszeudokóddal)

**Helye:** új top-level fn [`nfp_placer.rs`](../../../rust/nesting_engine/src/placement/nfp_placer.rs)-ben: `nfp_place_critical_beam`.

**v2 hibája:** a v2 pszeudokódja `ordered.iter()` első K placement-jén ment végig, ami csak akkor "critical-only", ha az `order_parts_for_policy` mindig giant-first-et ad. **Helyesen** a beam **csak akkor aktív, ha az aktuális instance a `critical_queue` tagja**, és a horizon **critical placementeket** számol, nem absolute placement-eket.

**Helyes pszeudokód:**

```rust
pub fn nfp_place_critical_beam(
    parts: &[InflatedPartSpec],
    bin_polygon: &Polygon64,
    grid_step_mm: f64,
    stop: &mut StopPolicy,
    cache: &mut NfpCache,
    stats: &mut NfpPlacerStatsV2,
    order_policy: PartOrderPolicy,
    beam_width: usize,           // default 4
    critical_horizon: usize,     // default 20
) -> PlacementResult {
    let ordered = order_parts_for_policy(parts, order_policy);
    let critical_queue = build_critical_queue(&ordered);
    let critical_set: HashSet<(usize, u32)> = critical_queue.iter().cloned().collect();

    let mut beam: Vec<BeamState> = vec![BeamState::empty(bin_polygon)];
    let mut critical_placements_done = 0usize;

    'main_loop: for (part_idx, part) in ordered.iter().enumerate() {
        for instance in 0..part.quantity {
            let is_critical = critical_set.contains(&(part_idx, instance));

            if is_critical && critical_placements_done < critical_horizon {
                // BEAM SEARCH branch — minden beam state-re top-B child generálva
                let mut all_children: Vec<BeamState> = Vec::new();
                for state in &beam {
                    let cands = generate_candidates_for_state(part, state, ...);
                    for cand in cands.iter().take(BEAM_CANDIDATES_PER_PARENT) {
                        if let Some(child) = state.try_with(cand, part, instance) {
                            all_children.push(child);
                        }
                    }
                }
                all_children.sort_by_key(|s| s.score);
                all_children.truncate(beam_width);

                if all_children.is_empty() {
                    // Nincs valid placement egyik beam state-en sem
                    for s in &mut beam {
                        s.unplaced.push(UnplacedItem { /* part info */ reason: "NO_FIT".into() });
                    }
                } else {
                    beam = all_children;
                    critical_placements_done += 1;
                }
            } else {
                // GREEDY branch — a top-1 beam state-ben pure greedy placement
                let best_state = beam.iter_mut()
                    .min_by_key(|s| s.score)
                    .expect("beam non-empty");
                let cands = generate_candidates_for_state(part, best_state, ...);
                if let Some(c) = cands.first() {
                    best_state.commit(c, part, instance);
                }
            }

            if stop.consume(1) { break 'main_loop; }
        }
    }

    // Visszaadjuk a legjobb beam state-t — vagy ha greedy-only volt a futás vége,
    // a single beam state-et.
    let best = beam.into_iter().min_by_key(|s| s.score)
        .expect("at least one beam state must survive");
    PlacementResult { placed: best.placed, unplaced: best.unplaced }
}
```

**Megjegyzés:** a fenti pszeudokód a beam fő részét adja. A pure-greedy continuation után a **Phase 3.5 `nfp_place_starting_from`-ot is hívhatja** a beam-blokk után (ha úgy egyszerűbb), de a fenti integrált verzió is működik.

**Indoklás:**
- LV8 fixture-en a default `top_k_types=3` a 3 db `Lv8_11612` + 4 db `Lv8_15348` + ~13 db egyéb top-area-critical part = ~14 critical instance. A beam ezeken 4× szélesen megy, 14 × 4 × 8 = 448 extra eval = ~3-5 % overhead a teljes ~18 000 eval-os greedy futáshoz képest.
- A "nem-kritikus" placement-eken pure greedy → a beam-haszon **csak** ott jelentkezik, ahol a packing tényleg számít.

**Env-gate:**
- `NESTING_ENGINE_BEAM_MODE=off|critical`
- `NESTING_ENGINE_BEAM_WIDTH=4`
- `NESTING_ENGINE_BEAM_HORIZON=20` (max critical placement)

**Acceptance gate / target / expected effect:**

| | Phase 4 |
|---|---|
| **Acceptance gate** | Snapshot 0 diff (off), unit teszt zöld (szintetikus 3-giant fixture beam B=2 nyer pure greedyvel szemben), runtime overhead ≤ +20 % vs Phase 3, LV8 sheet1 util ≥ **68 %** |
| **Target** | LV8 sheet1 util **70-72 %** (cumulative) |
| **Expected effect** | további +3-5 pp |

---

### Phase 5 — LNS refinement (prob-accept-worse-szal)

**Helye:** új modul [`rust/nesting_engine/src/search/local.rs`](../../../rust/nesting_engine/src/search/local.rs).

**v2 hibája:** a `accept_worse_threshold_pct` önmagában minden ≤ küszöb-romlást **determinisztikusan** elfogad → kontrollálatlan random walk-ká csúszhat.

**Helyes v2.1 elfogadási logika:**

```rust
pub struct LnsConfig {
    pub time_limit: Duration,
    pub destroy_k_min: usize,                    // 5 default
    pub destroy_k_max: usize,                    // 30 default
    pub accept_equal: bool,                      // true default (ILS standard)
    pub accept_worse_threshold_pct: f64,         // 0.0 default (off)
    pub accept_worse_probability: f64,           // 0.0 default (off)
    pub max_iter_without_improvement: usize,     // 20 default
}

fn should_accept(
    new_score: i128, cur_score: i128, best_score: i128,
    config: &LnsConfig, rng: &mut SplitMix64,
) -> bool {
    if new_score < cur_score {
        return true;
    }
    if new_score == cur_score && config.accept_equal {
        return true;
    }
    if config.accept_worse_threshold_pct > 0.0 && config.accept_worse_probability > 0.0 {
        let delta_pct = ((new_score - cur_score) as f64 / cur_score as f64) * 100.0;
        if delta_pct < config.accept_worse_threshold_pct {
            // SA-Boltzmann egyszerűsítés: küszöbön belül valószínűségileg fogadunk el
            let r = (rng.next_u64() as f64) / (u64::MAX as f64);
            return r < config.accept_worse_probability;
        }
    }
    false
}
```

**Két különálló env**:
- `NESTING_ENGINE_LNS_ACCEPT_WORSE_PCT=2` — küszöb (0 = off)
- `NESTING_ENGINE_LNS_ACCEPT_WORSE_PROB=0.05` — valószínűség (0 = off)

**Defaults:** mindkét érték 0 (LNS pure improvement-only + accept-equal). Az opt-in `(2, 0.05)` = "fogadj el ≤ 2 % rosszabb megoldást 5 % valószínűséggel" — kontrollált noise level, nem random walk.

**Destroy/repair operátorok (multi-strategy):**

```rust
enum DestroyStrategy {
    WorstNeighborhood,      // a legtöbb air-gap-ű k darab kivétele
    Random,                 // uniform random k darab
    ClusterByPartType,      // egy type-ból k összes (vagy random subset)
}

fn pick_destroy_strategy(rng: &mut SplitMix64) -> DestroyStrategy {
    // round-robin vagy random
    match rng.next_u64() % 3 {
        0 => DestroyStrategy::WorstNeighborhood,
        1 => DestroyStrategy::Random,
        _ => DestroyStrategy::ClusterByPartType,
    }
}
```

**Repair = `nfp_place_starting_from`** (Phase 3.5 infrastruktúra).

```rust
pub fn refine_layout_lns(
    initial: PlacementResult,
    base_specs: &[InflatedPartSpec],
    bin: &Polygon64,
    cache: &mut NfpCache,
    config: LnsConfig,
    rng: &mut SplitMix64,
) -> PlacementResult {
    let mut best = initial.clone();
    let mut current = initial;
    let deadline = Instant::now() + config.time_limit;
    let mut iters_no_improve = 0usize;

    while Instant::now() < deadline {
        let k = sample_destroy_k(&config, rng);
        let strategy = pick_destroy_strategy(rng);
        let (kept, removed) = destroy(&current, strategy, k, rng);

        let reinserted = nfp_place_starting_from(
            kept, removed, base_specs, bin, /* stop, */ cache, /* stats, */
            PartOrderPolicy::ByArea,
        );

        let new_score = score_result(&reinserted);
        let cur_score = score_result(&current);
        let best_score = score_result(&best);

        if should_accept(new_score, cur_score, best_score, &config, rng) {
            current = reinserted;
            if new_score < best_score {
                best = current.clone();
                iters_no_improve = 0;
            } else {
                iters_no_improve += 1;
            }
        } else {
            iters_no_improve += 1;
        }

        if iters_no_improve >= config.max_iter_without_improvement {
            current = best.clone();
            iters_no_improve = 0;
        }
    }
    best
}
```

**Indoklás:**
- A küszöb + valószínűség kombináció a klasszikus SA-Boltzmann (`exp(-Δ/T)`) **egyszerű, monoton helyettesítője**. Két paraméter (küszöb és prob) elég a tuning-hoz, nem kell teljes hőmérséklet-schedule.
- A multi-strategy destroy (worst / random / cluster) az LNS irodalom standard receptje, és diverzifikálja a perturbációt — a pure worst-neighborhood beragadhat lokális optimumokon.

**Env-gate:**
- `NESTING_ENGINE_LNS_TIME_SEC=0` (default off)
- `NESTING_ENGINE_LNS_TIME_SEC=60` (Phase 5 aktív, 60 s budget)
- `NESTING_ENGINE_LNS_ACCEPT_WORSE_PCT=N`, `_PROB=N` (opt-in prob-accept)

**Acceptance gate / target / expected effect:**

| | Phase 5 |
|---|---|
| **Acceptance gate** | Snapshot 0 diff (off), unit teszt zöld (LNS 1 destroy/repair > greedy baseline a szintetikus fixture-ön), LV8 sheet1 util ≥ **71 %** |
| **Target** | LV8 sheet1 util **73-75 %** (cumulative), LV8 276-instance 276/276 placed valid PASS |
| **Expected effect** | további +3-8 pp; 276/276 PASS biztosított |

**Regressziós felület:** új modul, új quality profile-ok. Az LNS RNG-deterministicitása a fixture `seed` mezőjén múlik.

---

## 4. SA fejlesztés visszavonása (v2.1 finomítás)

### 4.1 Pontos indoklás

**Helyes megfogalmazás:** Az SA mint algoritmus **nem alkalmatlan** nestingre (Burke-Kendall 2006 SA+NFP explicit precedens). A probléma a **mi konkrét eval-architektúránk**: az [`eval_state_cost_with_result`](../../../rust/nesting_engine/src/search/sa.rs#L450) minden szomszéd-állapotot **teljes greedy újraindítással** értékel ki. LV8-on per-eval 200 s, 100 SA-iter = 5.5 óra.

| Tény | Forrás | Implikáció |
|---|---|---|
| SA per-eval > 180 s LV8 prepacken | [2-sheet report L184-198](lv8_2sheet_10mm_600s_claude_code_report.md), `cgal_s42_180` 0 byte stdout 240 s watchdog után | 100 eval = 5 óra minimum |
| SA per-eval 60 s tl, 117/179 placed, 8.7 % util | [single-sheet report 4. szakasz](lv8_singlesheet_etalon_179_20260514.md) | SA *rontja* a greedy 60 %-os baseline-ját |
| 600 s tl rosszabb mint 180 s tl | [2-sheet report L199-203](lv8_2sheet_10mm_600s_claude_code_report.md) | `eval_budget_sec` skálázódik `time_limit_sec`-cel |
| `time_limit_sec` csak SA-evalok közt érvényesül | [sa.rs:368](../../../rust/nesting_engine/src/search/sa.rs#L368) | A deadline sosem tüzel az első eval végéig |

Az LNS (Phase 5) **ugyanazt** a state-space-t járja be, de **inkrementális** módon: csak k-darab re-placement, nem teljes újraindítás. 20-40× olcsóbb.

### 4.2 Mit nem dobunk el

- A mi **eval-architektúránk** (full re-greedy per neighbor) marad deprecated.
- Az **SA-style acceptance** (Boltzmann `exp(-Δ/T)` egyszerűsített prob-accept-worse) az LNS keretén belül opcionális (Phase 5 prob-accept-worse mechanizmus).
- Ha valaha inkrementális eval-architektúrát építünk, az SA mint algoritmus újra elérhető lesz.

### 4.3 Migrációs útvonal

1. **Phase 0:** `quality_default` és `quality_aggressive` `"search": "none"`-ra, shadow run protokoll a kockázat-mitigációra.
2. **Phase 5:** új profile-ok `quality_greedy_lns`, `quality_beam_lns`.
3. **`search/sa.rs` továbbra is buildelődik**, ADR-0002 dokumentálja, modul-szintű deprecation comment.
4. **Hosszabb távon (6+ hónap):** eltávolítás, ha inkrementális eval-t építünk és újra-érdemesnek tűnik.

## 5. Tesztelési és rollout-stratégia

### 5.1 Tesztelési invariánsok

Mindegyik fázis:
1. **Snapshot-tesztek 0 diff** env-gate off-on.
2. **Új unit teszt** a felelős függvény viselkedésére.
3. **Új integrációs teszt** LV8 sheet1 fixture-en, util-threshold checkkel.
4. **Hosszú-futás mérés** a harness-szel és a **Phase 0 polygon-aware validátorral**, run-mátrix-ban dokumentálva.

### 5.2 Quality profile gate-ek

| Profile | Mai → Phase 0 → … | Mikor használni |
|---|---|---|
| `quality_default` | nfp+sa → **nfp+none+slide** | Phase 0 után új default |
| `quality_scored_2a` | + bbox_growth | Phase 2a után új |
| `quality_scored_2b` | + extent_penalty | Phase 2b után új |
| `quality_scored_2c` | + contact_bonus (opt-in) | Phase 2c után új |
| `quality_lookahead` | + critical_1step | Phase 3 után új |
| `quality_beam_b4` | + critical-only beam B=4 horizon=20 | Phase 4 után új |
| `quality_beam_lns` | + LNS 60s, accept_equal, **prob-accept-worse OFF** | Phase 5 után új, **konzervatív, default LV8-szintre** |
| `quality_beam_lns_explore` | + LNS 120s, accept_equal, **prob-accept-worse ON (pct=2.0, prob=0.05)** | Phase 5 után új, **kísérleti, etalon-szintű minőséghez** |
| ~~`quality_cavity_prepack*`~~ | ~~sa-based~~ | Phase 0 után deprecated |

**A két LNS-profile konkrét konfigurációja** (a `quality_profile_registry`-ben hardcode-olva, hogy ne kelljen env-en állítgatni):

```python
"quality_beam_lns": {
    "placer": "nfp", "search": "none", "compaction": "slide",
    "tie_breaker": "bbox_growth_extent",   # Phase 2b
    "lookahead": "critical_1step",         # Phase 3
    "beam_mode": "critical",               # Phase 4
    "beam_width": 4, "beam_horizon": 20,
    "lns_time_sec": 60,                    # Phase 5
    "lns_accept_equal": True,
    "lns_accept_worse_pct": 0.0,           # konzervatív: OFF
    "lns_accept_worse_prob": 0.0,          # konzervatív: OFF
},
"quality_beam_lns_explore": {
    "placer": "nfp", "search": "none", "compaction": "slide",
    "tie_breaker": "bbox_growth_extent_contact",  # Phase 2c is bekapcsolva
    "lookahead": "critical_1step",
    "beam_mode": "critical",
    "beam_width": 4, "beam_horizon": 20,
    "lns_time_sec": 120,                          # hosszabb budget
    "lns_accept_equal": True,
    "lns_accept_worse_pct": 2.0,                  # kísérleti: ON
    "lns_accept_worse_prob": 0.05,                # kísérleti: ON
},
```

**Kötelező riport-protokoll:** minden mérési riport / summary.json **explicit jelölje**, melyik profile-lal futott. A konzervatív `quality_beam_lns` és a kísérleti `quality_beam_lns_explore` **eredményeit tilos összevonni vagy aggregálni**, mert az `explore` profile prob-accept-worse miatt magasabb varianciájú. Reproducibility ellenőrzés: ugyanaz a profile + seed kombináció determinisztikus eredményt kell, hogy adjon (a `SplitMix64` szempontból).

### 5.3 Env-gate stratégia

- `NESTING_ENGINE_NFP_DIAG=1` (Phase 0, opt-in diag)
- `NESTING_ENGINE_CACHE_LRU=0|1` (Phase 1, ha kell)
- `NESTING_ENGINE_TIE_BREAKER=lex|bbox_growth|bbox_growth_extent|bbox_growth_extent_contact` (Phase 2)
- `NESTING_ENGINE_LOOKAHEAD=off|critical_1step` (Phase 3)
- `NESTING_ENGINE_CRITICAL_TOP_K_TYPES=3` + `_INSTANCES=20` (Phase 3, profile-tunable)
- `NESTING_ENGINE_BEAM_MODE=off|critical` + `_BEAM_WIDTH=4` + `_BEAM_HORIZON=20` (Phase 4)
- `NESTING_ENGINE_LNS_TIME_SEC=N` + `_LNS_ACCEPT_WORSE_PCT=N` + `_LNS_ACCEPT_WORSE_PROB=N` (Phase 5)

### 5.4 Benchmark gate-ek (a teljes ciklus után)

1. **LV8 sheet1 (179 instance) `quality_beam_lns`:** sheet 0 util ≥ 70 %, 1 sheet, **polygon-aware CAM-grade valid**.
2. **LV8 teljes (276 instance) `quality_beam_lns`:** placed_instances = 276, sheets_used ≤ 2, util ≥ 65 % aggregate, **polygon-aware valid**.
3. **Regresszió-mérés**: web_platform/contract_freeze és más fixture-családokon util nem csökken több mint 2 pp-pel.

## 6. Becsült összesített hatás (három-szintű táblázat)

### 6.1 Acceptance gate (kötelező, binding teszt-küszöb)

| Fázis | LV8 sheet1 util | LV8 276 placed | Runtime overhead | Egyéb |
|---|---:|---:|---:|---|
| 0 | 60 % baseline | 189 baseline | -10 s | polygon-aware valid, stats export |
| 1 | 60 % | 189 | 1.5-2× gyorsabb | cache audit-jelentés |
| 2a | ≥ 62 % | ≥ 195 | ≤ +10 % vs P1 | snapshot 0 diff |
| 2b | ≥ 63.5 % | ≥ 200 | ≤ +5 % vs P2a | snapshot 0 diff |
| 2c | ≥ 65 % | ≥ 210 | ≤ +20 % vs P2b | contact_bonus_timeout_count ≤ 5 % |
| 3 | ≥ 65 % | ≥ 220 | ≤ +30 % vs P2c | snapshot 0 diff |
| 3.5 | (infrastructure) | (infrastructure) | (infrastructure) | 5 unit teszt zöld |
| 4 | ≥ 68 % | ≥ 250 | ≤ +20 % vs P3 | beam unit teszt zöld |
| 5 | ≥ 71 % | **276** | ≤ +60 % vs P4 (LNS-budget miatt) | LNS unit teszt zöld |

### 6.2 Target (aspirációs)

| Fázis | LV8 sheet1 util target | LV8 276 placed target |
|---|---:|---:|
| 0 | 60 % | 189 (no change) |
| 1 | 60 % | 189 |
| 2a | 63 % | 200 |
| 2b | 64 % | 215 |
| 2c | 66 % | 230 |
| 3 | 67 % | 250 |
| 4 | 70-72 % | 276 |
| 5 | 73-78 % | 276 |

### 6.3 Expected effect (várt, nem garantált)

| Fázis | LV8 sheet1 util expected |
|---|---:|
| 0 | 60 % (mérési zaj megszüntetése) |
| 1 | 60 % (cache hatékonyabb kihasználása → 2× gyorsabb) |
| 2a | 62-63 % |
| 2b | 63-64 % |
| 2c | 64-66 % |
| 3 | 65-67 % |
| 4 | 68-72 % |
| 5 | 71-78 % (a target tetejét csak a `_explore` profile-lal) |

**Megjegyzés:** a P5-után **expected effect 73-78 % csak a `quality_beam_lns_explore` (prob-accept-worse on) profile-lal várható**. A `quality_beam_lns` (accept-equal-only) konzervatív, várható 71-73 %.

## 7. Becsült összes munkaerő

| Fázis | Engineering nap | Külön teszt-nap | Mérés-nap | Összesen |
|---|---:|---:|---:|---:|
| 0 | 2.5 | 1 | 0.5 | 4 |
| 1.0 (spike) | 0.5-1 | 0 | 0 | 0.5-1 |
| 1 (audit + harden) | 1.5 | 1 | 0.5 | 3 |
| 2a | 1 | 0.5 | 0.5 | 2 |
| 2b | 0.5 | 0.5 | 0.5 | 1.5 |
| 2c (opt-in) | 2 | 1 | 0.5 | 3.5 |
| 3 | 3 | 1.5 | 0.5 | 5 |
| 3.5 (infrastruktúra) | 3 | 2 | 0.5 | 5.5 |
| 4 | 3 | 1.5 | 1 | 5.5 |
| 5 | 4 | 1.5 | 1 | 6.5 |
| SA migration / ADR-0002 | 0.5 | 0 | 0 | 0.5 |
| **Σ** | 21.5-22 | 10.5 | 5.5 | **~37.5-38 nap** |

A P0+1+2(a-c)+3+3.5 (≈25 nap) elég a 276/276 PASS-hoz, ha a Phase 4 vagy 5 majd erre ráteszi az utolsó 5-10 pp-t.

Phase 2c és Phase 5 prob-accept-worse mindkettő **opt-in**, ha P2a+2b+3 elég jó eredményt ad, ezek a sub-fázisok elhagyhatók a kritikus pályáról.

## 8. Kockázatok és mitigáció

| Kockázat | Valószínűség | Hatás | Mitigáció |
|---|---|---|---|
| `quality_default` SA→none viselkedés-változást okoz downstream caller-nél | közepes | közepes | **Phase 0 shadow run protokoll: 1 hét 3 fixture-családon párhuzamosan**, deprecation warning logba, hard-cut csak ha a no-SA jobb vagy egyenlő |
| Phase 1 audit során a meglévő cache hibásan használt-out-ot talál | közepes | közepes (időbecslés-növekedés) | audit-jelentés Phase 1 elején, ha hibás use-pattern, javítás +1-2 nap |
| `multi-score` scoring más fixture-ön regressziót okoz | közepes | közepes | env-gate default-off; A/B teszt a teljes benchmark-suite-on Phase 2 után |
| Cache LRU-átállás bug | alacsony (csak ha aktív) | közepes | unit teszt minden új strategy-re, snapshot-tesztek változatlanok |
| Cache rejtett-bug spacing/pipeline változásnál | alacsony (shape_id véd) | magas | unit teszt: spacing-változás cache_miss-t ad; ha nem → pipeline_version field hozzáadása |
| `critical-only beam` ad-hoc heurisztika túl-illeszkedik LV8-ra | közepes | közepes | Phase 4 mérése MIN. 3 fixture-családon (LV8, contract_freeze, synthetic) |
| `nfp_place_starting_from` state-rekonstrukció szivároghat | magas | magas | **Phase 3.5 mint külön fázis, dedikált 5-teszt suite**, snapshot-tesztek változatlanok |
| LNS prob-accept-worse kontrollálatlan random walk | alacsony (prob default 0) | magas | default off; csak opt-in env-en aktiválható; max iter without improvement védi az alsó határt |
| Cavity-prepack interakció a beam search-csel | magas | közepes | Phase 4 első mérése prepack OFF; ha alap-eredmény jó, prepack interakció külön ADR-ben tisztázva |
| Profile-param magic-number override-elhetetlen | alacsony | alacsony | minden critical-queue és LNS paraméter env-en + quality_profile registry-n állítható |

## 9. Mit szállít minden fázis konkrétan

| Fázis | Új fájlok | Módosított fájlok | Új tesztek | Új ADR / report |
|---|---|---|---|---|
| 0 | `scripts/experiments/lv8_polygon_validator.py` (vagy hasonló unifikáló script) | `vrs_nesting/config/nesting_quality_profiles.py`, `nfp/concave.rs` (diag gate), `placement/nfp_placer.rs` (stats v2), harness | unit a stats-counter-ekre, integration `quality_default` baseline, shadow run jelentés | report: `lv8_phase0_baseline_and_validation.md` |
| 1 | — (`nfp/cache.rs` audit) | `nfp/cache.rs` (stats bővítés, opcionális LRU), `nfp_placer.rs` (stats továbbadás) | audit-jelentés mint unit teszt-form (cache használat verifikálva minden NFP úton), opcionális LRU-teszt | report: `lv8_phase1_cache_audit_result.md` |
| 2a | — | `nfp_placer.rs` (`score_candidate_bbox_growth` fn) | `tests/tie_breaker_bbox_growth.rs`, integration LV8 sheet1 | report: `lv8_phase2a_bbox_scoring_result.md` |
| 2b | — | `nfp_placer.rs` (extent_penalty komponens) | `tests/tie_breaker_extent.rs` | report: `lv8_phase2b_extent_scoring_result.md` |
| 2c | — | `nfp_placer.rs` (contact_bonus, fallback, timeout-counter) | `tests/tie_breaker_contact.rs` | report: `lv8_phase2c_contact_scoring_result.md` |
| 3 | — | `nfp_placer.rs` (`build_critical_queue`, `select_with_critical_lookahead`) | `tests/critical_lookahead.rs` | report: `lv8_phase3_lookahead_result.md` |
| 3.5 | — | `nfp_placer.rs` (`pub fn nfp_place_starting_from` + state-rekonstrukció) | `tests/nfp_place_starting_from.rs` (5 teszt) | report: `lv8_phase3_5_starting_from_infrastructure.md` |
| 4 | — | `nfp_placer.rs` (`nfp_place_critical_beam`, `BeamState`) | `tests/critical_beam_b4.rs` | report: `lv8_phase4_beam_result.md` |
| 5 | `search/local.rs` | `vrs_nesting/config/nesting_quality_profiles.py` (új profile-ok) | `tests/lns_refine.rs` (include accept_worse prob teszt) | report: `lv8_phase5_lns_result.md`, ADR: `ADR-0002-sa-deprecation-for-lv8-scale.md` |

## 10. Kapcsolódó dokumentumok

- [LV8 2-sheet 10mm 600s claude code report](lv8_2sheet_10mm_600s_claude_code_report.md) — 23 % util / 189 placed diagnosztika
- [LV8 single-sheet etalon 179 report](lv8_singlesheet_etalon_179_20260514.md) — 60 % util / 178 placed sheet 0 + 1 spillover
- [ADR-0001 BLF not quality solver](../../decisions/ADR-0001-blf-not-quality-solver.md)
- (jövőbeli) [ADR-0002 SA deprecation](../../decisions/ADR-0002-sa-deprecation-for-lv8-scale.md)

---

## Lezárás

A v2.1-es terv **7 fázisra (0, 1, 2a-c, 3, 3.5, 4, 5)** bontva, **kód-ellenőrzött kiindulóponttal** (a meglévő `NfpCache` SHA256-shape_id-alapú struktúrája igazolva, audit + hardening megkapja a Phase 1-et új-építés helyett), **delegálható task-méretű PR-ekre szabva**.

**P0+1+2(a-c)+3+3.5 (~25 nap)** önmagában elég a 276/276 PASS-hoz a Phase 4-cel együtt. **P4+5 (~12 nap)** a "kompetitív etalon-szint" zónába visz, opt-in prob-accept-worse mechanizmusszal.

**Kulcs változások a v2-höz képest:**
1. **Phase 0.3 polygon-validátor** átfogalmazva: nem "AABB-only", hanem "egyetlen kötelező CAM-grade gate létrehozása a meglévő logikára építve".
2. **Phase 1 teljesen átírva**: nem új `pair_cache.rs`, hanem a létező `nfp/cache.rs` **audit + hardening** (a SHA256-shape_id már implicit lefedi a spacing-változást).
3. **Phase 2 felosztva 2a / 2b / 2c-re** finomabb mérhetőséggel; 2c opt-in runtime-cap-pal.
4. **Criticality_score precizálva**: konzisztens geometria-forrás, holes kezelt, **profile-param top-K** (`NESTING_ENGINE_CRITICAL_TOP_K_TYPES=3, _INSTANCES=20`) a magic-number median × 4 helyett.
5. **Új Phase 3.5**: `nfp_place_starting_from` **önálló infrastruktúra-fázis**, 5 dedikált unit teszt, ezzel Phase 4 és 5 párhuzamosan szállíthatóvá válik.
6. **Phase 4 critical-beam pszeudokódja javítva**: a beam csak akkor aktív, ha az aktuális instance `critical_queue.contains((part_idx, instance))`; a horizon **critical placement-számolós**, nem absolute placement-számolós.
7. **Phase 5 LNS accept_worse** valószínűséggel kombinálva (`_ACCEPT_WORSE_PCT` + `_ACCEPT_WORSE_PROB` két különálló env), default mindkettő 0 → semmilyen random walk-kockázat kontroll nélkül.
8. **Hatás-táblázat** szétválasztva acceptance gate / target / expected effect három szintre (delegálás-biztonsági okból).

**Implementáció-előtti döntések (v2.2 kiegészítések):**
1. **Phase 0 shadow run 3. fixture-családja**: meglévő [`poc/nesting_engine/f2_4_sa_quality_fixture_v2.json`](../../../poc/nesting_engine/f2_4_sa_quality_fixture_v2.json) — kód-ellenőrzött, elsődleges; fallback csak ha nem reprezentatív.
2. **Phase 1.0 cache path discovery spike**: kötelező 0.5-1 napos al-lépés a Phase 1 elején, **gépiesen ellenőrizhető fix-strukturájú jelentéssel** ([`tmp/phase1_spike_cache_path_discovery.md`](../../../tmp/phase1_spike_cache_path_discovery.md)).
3. **`quality_beam_lns_explore` automatikus prob-accept-worse**: `(pct=2.0, prob=0.05)`, míg a konzervatív `quality_beam_lns` `(0, 0)`. A két profile reportjai **kötelezően külön jelölve**, soha nem aggregálva.

**Legfontosabb következő implementációs lépés:** Phase 0 (mérési higiénia + polygon-aware gate + stats export) → Phase 1.0 spike → Phase 1 (cache audit + hardening) → Phase 2a (bbox-growth scoring) A/B mérés. Ez ~9.5-10 nap, és gyorsan megmondja, hogy a 60 % → 62-63 % realisztikus-e, mielőtt nagyobb fázisok elkezdődnek.
