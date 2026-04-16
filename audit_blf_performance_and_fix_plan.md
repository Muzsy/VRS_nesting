# BLF teljesítmény audit és javítási terv — VRS Nesting

> Készült: 2026-04-16
> Hatókör: a `DXF Nesting alkalmazás – Audit jelentés T1–T8.md` mélyvizsgálati
> blokkja alapján, a **jelenlegi** `/home/muszy/projects/VRS_nesting` repóra
> alkalmazva.
> Módszertan: bizonyítékvezérelt kódaudit. Minden állítás mellett a konkrét
> fájl és sorszám hivatkozva, a repóban futtatható kódból kiolvasható.
> Nem tartalmaz találgatást. A „nem bizonyított” részek külön jelölve.

---

## 1. Executive summary

A korábbi audit végeredménye (Claude_audit) szerint a `nesting_engine`
BLF placerben a falidő **~92 %**-a `can_place()` alatt ég el, és ennek nagy
részét a narrow-phase **brute-force szegmenspár-ellenőrzés** viszi el, miközben
a motor **korlátlan mennyiségű reménytelen jelöltet** próbálgat (egyetlen
part instance >156 000 jelölt, >20 s siker nélkül).

A jelenlegi `main` kódágon:

- a BLF fallback és a grid sweep **változatlan szerkezettel** fut (nincs
  per-part candidate cap, nincs stagnation cutoff),
- a narrow-phase továbbra is **O(outer·other)** szegmenspár-vizsgálatot
  csinál per overlap-jelölt,
- a cavity candidate generátor **továbbra is `3 + 1 + 24 + 24 · holeVertex`**
  anchor pontot állít elő hole-onként, cap nélkül,
- a BLF_PROFILE_V1 és SA_PROFILE_V1 telemetria **már bent van** a kódban,
  tehát a hotspotok mérhetők, de **nincs** rájuk épülő érdemi korlátozás,
- a worker továbbra is **újrapróbálja** a determinisztikus solver timeoutot,
  a trial tool **poll timeoutja pedig nem retry-aware**.

Ez a dokumentum:

1. bizonyítja ezeket a hotspotokat a repo aktuális kódjából,
2. javaslatot ad három lépcsőben (P1 = alacsony kockázat, P2 = közepes,
   P3 = strukturális) a konkrét fájl- és függvényszintű beavatkozásokra,
3. operatív kísérőjavításokat ad a worker/poller oldalra.

---

## 2. Hotspot-bizonyítékok (kódszintű)

### 2.1 Globális NFP → BLF fallback egyetlen lyukas part miatt

`rust/nesting_engine/src/main.rs:431-446`:

```rust
let has_nominal_holes = input
    .parts
    .iter()
    .any(|part| !part.holes_points_mm.is_empty());
let has_hole_collapsed = pipe_resp
    .parts
    .iter()
    .any(|part| part.status == "hole_collapsed");
let effective_placer = if cli.placer == PlacerKind::Nfp
    && (has_nominal_holes || has_hole_collapsed)
{
    eprintln!("warning: --placer nfp fallback to blf ...");
    PlacerKind::Blf
} else {
    cli.placer
};
```

**Tény:** elegendő **egyetlen** part lyukas (vagy pipeline által
„hole_collapsed” állapotba vitt) vetemedést okozni ahhoz, hogy a **teljes**
futás BLF-re váltson, beleértve azokat a partokat is, amelyek az NFP úton
gond nélkül mennének. Ez a korábbi audit „global fallback” megállapítása
a jelenlegi kódban **változatlanul** igaz.

### 2.2 BLF rács-söprés cap nélkül (fő candidate-robbanás)

`rust/nesting_engine/src/placement/blf.rs:332-439`:

- `while ty <= global_ty_max && !found`
- `while tx <= global_tx_max && !found`
- `for (rotation, rotated, rotated_aabb) in &rotation_candidates`

Az egyetlen leállási feltétel a belső `stop.consume(1)` visszatérési értéke
(`StopPolicy` — wall-clock vagy work-budget). **Nincs**:

- per-part candidate-cap,
- per-instance stagnation cutoff (ami ténylegesen **kilépne** a ciklusból
  sikertelen próbálkozások után),
- candidate dedupe vagy bbox-alapú prefilter,
- priorizált anchor-sorrend.

Összehasonlításképp az NFP út explicit cappel dolgozik:
`rust/nesting_engine/src/placement/nfp_placer.rs:27`

```rust
const MAX_CANDIDATES_PER_PART: usize = 4096;
```

A BLF-ben ilyen védelem nincs — csak a megosztott `StopPolicy`
(`rust/nesting_engine/src/multi_bin/greedy.rs:55-193`) fogyasztása.

### 2.3 Stagnáció csak **mérve** van, nem **kikényszerítve**

`rust/nesting_engine/src/placement/blf.rs:484-488`:

```rust
prof.wall_ms_since_last_successful_placement =
    last_success_time.elapsed().as_secs_f64() * 1000.0;
prof.candidates_tested_since_last_success = candidates_since_last_success;
prof.progress_stalled = prof.total_parts_placed < prof.total_parts_requested
    && candidates_since_last_success > 1000;
```

A `progress_stalled` flag **csak a kiírt JSON** része. A grid sweep
semmilyen ponton nem lép ki a `candidates_since_last_success` alapján.
Ugyanezek a számlálók `blf.rs:249, 308, 364, 423` nőnek/nullázódnak,
de **skip-logikához nincsenek kötve**.

### 2.4 Cavity candidate robbanás

`rust/nesting_engine/src/placement/blf.rs:551-591`:

```rust
for step in CAVITY_NUDGE_STEPS { ... }          // 3 lower-left nudge
// center + 1
for step in CAVITY_NUDGE_STEPS {                // 24 center nudge
    for (dx, dy) in CAVITY_NUDGE_DIRS { ... }
}
for vertex in hole {
    for step in CAVITY_NUDGE_STEPS {            // 24 / hole-vertex
        for (dx, dy) in CAVITY_NUDGE_DIRS { ... }
    }
}
```

Egy lyukra: **3 + 1 + 24 + 24 × vertexCount** anchor.
61 vertexes hole → **1492 anchor / hole / rotáció**.

A `collect_cavity_candidates` (`blf.rs:497-549`) **nem** korlátozza a
generált listát, nincs benne `stop.consume()` a generáláskor, és nincs
bbox-fit előszűrés a `rotated_aabb` és a hole bbox között
(a szűrés csak `tx < tx_min || ... || ty > ty_max` alapján zajlik, ami
csak a sheet-korlátokat alkalmazza, nem a hole-specifikus feasibility-t).

### 2.5 `translate_polygon` teljes polygon-allokáció minden jelöltnél

`rust/nesting_engine/src/placement/blf.rs:683-692`:

```rust
fn translate_polygon(poly: &Polygon64, tx: i64, ty: i64) -> Polygon64 {
    Polygon64 {
        outer: poly.outer.iter().map(|p| Point64 { x: p.x + tx, y: p.y + ty }).collect(),
        holes: poly.holes.iter()
            .map(|h| h.iter().map(|p| Point64 { x: p.x + tx, y: p.y + ty }).collect())
            .collect(),
    }
}
```

Hívási helyek: `blf.rs:253` (cavity) és `blf.rs:368` (grid). Minden
jelölt-próbálkozás előtt teljes outer + hole ring-klón készül, még
azelőtt, hogy az AABB-szintű olcsó szűrő elutasítaná.

> **Megjegyzés:** a Claude_audit szerint ez csak ~1.6 % falidő.
> Szerkezetileg javítható ingyen (lásd 3.1/b), de **nem elsődleges** hotspot.

### 2.6 Narrow-phase: O(n·m) szegmenspár-ellenőrzés

`rust/nesting_engine/src/feasibility/narrow.rs:269-286`:

```rust
fn ring_intersects_ring_or_touch(a: &[Point64], b: &[Point64]) -> bool {
    if a.len() < 2 || b.len() < 2 { return false; }
    for i in 0..a.len() {
        let a0 = a[i]; let a1 = a[(i + 1) % a.len()];
        for j in 0..b.len() {
            let b0 = b[j]; let b1 = b[(j + 1) % b.len()];
            if segments_intersect_or_touch(a0, a1, b0, b1) { return true; }
        }
    }
    false
}
```

És `narrow.rs:244-259`:

```rust
fn polygons_intersect_or_touch(a: &Polygon64, b: &Polygon64) -> bool {
    ...
    for ring_a in polygon_rings(a) {
        for ring_b in polygon_rings(b) {
            if ring_intersects_ring_or_touch(ring_a, ring_b) { return true; }
        }
    }
    ...
}
```

**Tény:** minden candidate × minden bbox-szűrésen átjutott placed pár
teljes kereszt-szorzaton végigmegy. Hole-os partoknál a ring-párok száma
a szorzót még tovább növeli. A sorrend: AABB → `poly_strictly_within`
→ `query_overlaps` (R-tree, ez OK) → `polygons_intersect_or_touch`
(brute force). A broad-phase után **nincs** olcsóbb köztes szűrő
(pl. edge-level AABB, separating-axis heurisztika, sweep-line).

Ez a Claude_audit #1 gyökéroka (67.1 % wall) — a kód alapján **változatlan**.

### 2.7 `poly_strictly_within` is drága hole-os partnál

`rust/nesting_engine/src/feasibility/narrow.rs:220-242`:

- minden candidate outer vertexre `point_in_polygon` a bin ellen,
- utána `ring_intersects_polygon_boundaries` (szintén brute force edge-pair
  check az outer vs. bin outer/hole ringjei között),
- majd minden bin-hole első pontjára `point_in_polygon` a candidate-be.

Bin ≠ hole-os a jelenlegi használatban (kód szerint rect bin a `main.rs:519`
körül), ez ma nem domináns faktor. De candidate hole-ok esetén a második
fázisban (`polygons_intersect_or_touch`) a ring-szám sokasodása ide is
beszámít.

### 2.8 Placed state monoton nő — minden további part drágább

`rust/nesting_engine/src/placement/blf.rs:143-144, 289-293`:

```rust
let mut placed_state = PlacedIndex::new();
let mut placed_polygons: Vec<Polygon64> = Vec::new();
...
placed_state.insert(PlacedPart { inflated_polygon: candidate.clone(), aabb: candidate_aabb });
placed_polygons.push(candidate);
```

A `PlacedIndex` belül rstar R-tree-t használ
(`narrow.rs:39-77`), de a narrow-phase nem él spatial acceleration-nel
a szegmensek szintjén — csak az AABB-overlap query-t szűri.

### 2.9 SA alatt minden evaluáció újrafuttatja a teljes greedy/BLF-et

`rust/nesting_engine/src/search/sa.rs:297-316` (evaluate callback):

```rust
|state| {
    on_eval();
    eval_state_cost_with_result(
        state, base_specs, bin, grid_step_mm,
        config.eval_budget_sec, placer_kind,
        part_in_part_mode, compaction_mode,
    )
}
```

`rust/nesting_engine/src/search/sa.rs:389-407`
(`eval_state_cost_with_result`) a blokk végén `greedy_multi_sheet(...)`-et
hív. Vagyis egy drága BLF útvonal nemcsak egyszer, hanem
**SA-iterációnként egyszer** fut le, a `sa_eval_budget_sec`-kel
darabolva. Ez az amplifier.

### 2.10 `sa_eval_budget_sec=60` override „kitölti” az 1200 s-et

`rust/nesting_engine/src/search/sa.rs:179-195` (`clamp_sa_iters_...`):

```rust
let max_evals = time_limit_sec / eval_budget_sec;
let max_iters = max_evals.saturating_sub(1);
requested_iters.min(max_iters)
```

1200 / 60 = 20 eval-slot. A profile default
`rust/nesting_engine/vrs_nesting/config/nesting_quality_profiles.py:41-47`
`sa_eval_budget_sec=1`-et ír elő a `quality_aggressive` profile-ra; a
korábbi auditnál viszont run-level override volt 60. A clamp logika így
pontosan a 20 × 60 s-es „egyenes vonalat” engedi, tehát a teljes
időablak felemésztődik.

### 2.11 Python runner + worker kísérő kockázatok (változatlanok)

- `vrs_nesting/runner/nesting_engine_runner.py:126-137`
  — `subprocess.run(... timeout=time_limit_sec + 5)`, és a kivételnél
  `NestingEngineNonZeroExitError("nesting_engine timed out after ...")`.
  Vagyis determinisztikus timeout ugyanarra az inputra ugyanúgy
  reprodukálódik.
- `worker/main.py:1693-1702` — exception ágon
  `client.requeue_run_with_delay(...)` hívódik, amíg `attempts <
  max_attempts`. A determinisztikus solver timeout így **automatikusan
  megismétlődik**, érdemi eredmény nélkül.
- `scripts/trial_run_tool_core.py:1769-1771` — `effective_poll_timeout
  = time_limit + 120`, ami **nem retry-aware**. A worker requeue után
  a tool még a második attempt közben is tool-oldali timeoutot dob.

---

## 3. Javítási javaslatok (3 lépcső)

**Alapelv:** először a „pazarlás”-t (reménytelen jelöltek) vágjuk le
(alacsony kockázat, nagy nyereség), utána a drága geometriai magot
gyorsítjuk (közepes kockázat), és csak a végén nyúlunk a strukturális
NFP/hole-kezeléshez (nagy kockázat, de tiszta hosszú távú megoldás).

Minden P1–P2 javaslat:
- **determinisztikus** maradjon (ne vezessen be float/nem-ellenőrzött
  RNG divergenciát a placementbe),
- **kikapcsolható** legyen környezeti változóval, hogy A/B
  regresszió ellenőrizhető legyen,
- **ne érintsen** semmit a `PartInPartMode::Off` / `CompactionMode::Off`
  ághoz tartozó determinisztikus teszteken (`blf.rs:826-1101`).

### 3.1 P1 — „Pazarlás levágása” (alacsony kockázat, nagy nyereség)

#### 3.1.a Per-instance candidate cap + stagnation cutoff a BLF-ben

**Hol:** `rust/nesting_engine/src/placement/blf.rs:332-439` (grid sweep)
és `blf.rs:213-320` (cavity sweep).

**Mit:** vezessünk be két új, env-vel felülírható konstanst:

- `BLF_PER_INSTANCE_CANDIDATE_CAP` (default pl. 200 000)
- `BLF_STAGNATION_CUTOFF_CANDIDATES` (default pl. 20 000)

Ezek **instance-szintűek**, nem globálisak. Ha egy instance-en belül
a `candidates_since_last_success` elér egy küszöböt, vagy a
`cavity_candidates_tested + grid_candidates_tested` elér egy instance-cap-et,
az instance-et a BLF **úgy zárja le**, mint a jelenlegi timeout ágat:
az instance `UnplacedItem { reason: "PART_INSTANCE_CAP_EXHAUSTED" }`-ot
kap, és a `'instance_loop`-on `continue` jön (nem `break`). Így a többi
part instance tovább próbálható.

**Fontos:** a `StopPolicy` jelenlegi `consume(...)` logikája megmarad — ez
csak egy **második, hely-független** biztosíték.

**Bizonyíték a szükségességre:** `blf.rs:487-488` már számolja a
stagnálást, csak nem kényszeríti ki. A Claude_audit szerint 20.7 s alatt
156 623 jelölt tesztelődött siker nélkül egy instance-re. Ennek levágása
már önmagában megakasztja a legdrágább stagnáló ágakat.

**Determinizmus:** a cap deterministically gyorsan választja ki a
„kilépek most” állapotot, mert a jelölt-sorrend fix (rács + cavity
generálási sorrend).

**Kikapcsolás:** `NESTING_ENGINE_BLF_INSTANCE_CAP_DISABLE=1`.

#### 3.1.b `translate_polygon` allokáció megtakarítása olcsó prefilterrel

**Hol:** `blf.rs:367-400` (grid sweep candidate-pipeline).

**Mit:** mielőtt `translate_polygon(...)` lefut, ellenőrizzük
AABB-szinten is, hogy a `(rotated_aabb + (tx,ty))` bbox ütközhet-e
bármelyik `placed_state` AABB-jével. Ha nem, azonnal `continue` — új
polygon nem épül. A `PlacedIndex::query_overlaps(...)`
(`narrow.rs:57-72`) már gyors, itt csak **egy** hívás kell. A teljes
`translate_polygon + can_place_profiled` pipeline így átugorható a
„nyilvánvalóan üres” cellákra.

**Hatás:** a Claude_audit 1.6 % wall-ja erre esett — **nem** ez az elsődleges
hotspot, de:
- allokációk megszűnnek,
- a `can_place` bejövő terhelése csökken,
- a per-instance cap is gyorsabban közelíti a reális „ezzel a cellával
  nincs esélyem” állapotot.

**Determinizmus:** változatlan.

#### 3.1.c Cavity candidate cap + bbox-fit előszűrés

**Hol:** `blf.rs:497-591` (`collect_cavity_candidates` és
`hole_anchor_points`).

**Mit:**

1. **Hole-bbox-fit prefilter:** mielőtt a hole-ra anchor pontokat
   generálunk, ellenőrizzük, hogy a `rotated_aabb` egyáltalán belefér-e
   a `hole_bbox`-ba (`max_x - min_x >= rotated_aabb szélessége &&
   max_y - min_y >= rotated_aabb magassága`). Ha nem, a hole átugorható.
   Ez azonnal kiszűri a reménytelen lyukakat; ma a `ring_bbox` már
   kiszámolódik (`blf.rs:517-521`), csak nincs rá gating.

2. **Per-hole anchor cap:** `BLF_CAVITY_ANCHOR_CAP_PER_HOLE` (default pl.
   256). A `hole_anchor_points` először a **legígéretesebb** pontokat
   tegye be (lower-left anchor + center), és a vertex-köré nudge-rétegeket
   csak a cap-ig adja hozzá. A CAVITY_NUDGE_STEPS / CAVITY_NUDGE_DIRS
   sorrend determinisztikus (`blf.rs:17-27`), így a cap determinisztikus
   kiválasztást ad.

3. **Opcionálisan:** a `collect_cavity_candidates` végén összesített cap a
   teljes listára is (`BLF_CAVITY_TOTAL_CANDIDATES_CAP`, pl. 4096, az
   NFP MAX_CANDIDATES_PER_PART-jához hasonlóan).

**Hatás:** 61 vertexes hole × 1 rotáció × 8 rotáció =
1492 × 8 = ~12 000 anchor. 256 cap mellett ez ~20× csökkentés, miközben
a lower-left + center + első-két nudge-réteg mindig bent marad, vagyis a
„tényleges cavity-fit” esélye alig csökken.

**Determinizmus:** változatlan, mert a sorrend determinisztikus.

#### 3.1.d Worker-oldali retry-gátló a determinisztikus timeoutra

**Hol:** `worker/main.py:1693-1702`.

**Mit:** az exception branch különböztesse meg a determinisztikus
solver-timeoutot (a `NestingEngineNonZeroExitError` üzenetéből
detektálható: `"nesting_engine timed out after"` — ez fix string a
`vrs_nesting/runner/nesting_engine_runner.py:134-137`-ben). Ha ez a
kivétel, **ne** menjen `requeue_run_with_delay`-re — helyette rögtön
`complete_run_failed_and_dequeue` egy explicit
`reason="solver_deterministic_timeout"` üzenettel.

**Hatás:** megszűnik a 2. és 3. futás, ami ugyanúgy timeoutol. A run
gyorsan terminális állapotba megy, a trial tool nem áll le félúton,
a platform naplója tisztább lesz.

**Kockázat:** alacsony — csak az üzenetet kell detektálni és az ágat
megkülönböztetni. Unit-teszt fedezi a detekciót.

#### 3.1.e Trial tool poll-timeout legyen retry-aware

**Hol:** `scripts/trial_run_tool_core.py:1769-1771`.

**Mit:** a képlet helyett

```python
effective_poll_timeout = effective_time_limit + 120.0
```

használjuk:

```python
max_attempts = config.worker_max_attempts or 3
retry_delay_s = config.worker_retry_delay_s or 30
runner_grace_s = 5.0
safety_buffer_s = 120.0
effective_poll_timeout = (
    max_attempts * (effective_time_limit + runner_grace_s)
    + (max_attempts - 1) * retry_delay_s
    + safety_buffer_s
)
```

**Feltételezés:** a worker retry-modell aktuális értékei olvashatók
(ha a 3.1.d bekerül és a determinisztikus timeouton nincs retry, akkor
`max_attempts=1` is érvényes default lesz). Amíg a 3.1.d nem megy be,
ez a módosítás önmagában is **elkerüli a fals tool-timeoutot**.

**Kockázat:** alacsony. Csak a figyelőablak nő, a kliens semmi mást
nem változtat.

### 3.2 P2 — A narrow-phase költségének érdemi csökkentése

#### 3.2.a Edge-level AABB prefilter `polygons_intersect_or_touch` elé

**Hol:** `rust/nesting_engine/src/feasibility/narrow.rs:244-286`.

**Mit:** két lépcső:

1. **Ring-szintű AABB prefilter:** `ring_intersects_ring_or_touch`
   előtt számoljuk ki mindkét ring AABB-ját (a candidate ringek
   AABB-je egyszer, a placed ringek AABB-je **placed-állapotba
   eltárolható**). Ha nincs AABB-overlap, skip.

2. **Edge-szintű coarse check:** minden ringhez egy
   **edge-AABB lista** kerül (once, placed oldalon), és a
   `ring_intersects_ring_or_touch` belsejében a candidate edge AABB-t
   vetjük össze a másik oldal edge AABB-ivel; csak a match-elő edge-párok
   mennek pontos `segments_intersect_or_touch`-ra.

**Hatás:** a Claude_audit-ban a 5.8 Md szegmenspár-check nagy része
ilyen olcsó AABB-szűréssel kiejthető. Ez a „cheaper narrow-phase
prefilter” irány, amit a Claude_audit is említett #2 javításként.

**Kockázat:** közepes. Ugyanazt a _döntést_ kell hoznia a kódnak, mint
ma (determinizmus!). Kellenek regressziós tesztek:

- a jelenlegi `narrow.rs:431-609` tesztek **mind** zöldek legyenek,
- új teszt a „touching after rounding” és „1 micron gap” esetekre,
  biztosítva, hogy az AABB-prefilter nem engedi át tévedésből.

#### 3.2.b Placed polygonokra edge-spatial index

**Hol:** `narrow.rs:39-77` (`PlacedIndex`).

**Mit:** a `PlacedIndex` ma csak polygon-szintű AABB R-tree-t tart. Egy
opcionális második réteg: minden placed polygon insertálásakor számoljuk
ki az edge-lista AABB-jeit, és tároljuk **placed-per** R-tree-ben
(`rstar::RTree<EdgeEnvelope>` — hasonlóan a `PlacedPartEnvelope`-hoz).
Narrow-phase-ben a candidate edge-jei pontosan **azokkal** az edge-ekkel
kerülnek összevetésre, amelyek AABB-je ütközik.

**Hatás:** az O(n·m) szegmenspár-vizsgálat gyakorlatilag
O((n+m)·log(m) + hit) lesz a ritkán ütköző párok ellen.

**Kockázat:** közepes-magas. Nagyobb memória-footprint. Plusz unit-tesztek
kellenek, hogy az új edge-tree-t egyenértékűnek bizonyítsák a régi
brute-force logikával (determinisztikus I/O ugyanaz).

**Feltétel:** csak akkor menjen be, ha a 3.2.a önmagában nem elég.

#### 3.2.c Sweep-line az outer-ring legdrágább pár-check-jére

**Hol:** új modul, pl. `rust/nesting_engine/src/feasibility/sweep.rs`.

**Mit:** Bentley–Ottmann-szerű sweep két ringen — csak abban az esetben
hívódik meg, ha (a) az AABB-prefilter ütközést jelez, (b) a ringméret
kellően nagy (pl. > 64 edge), (c) `NESTING_ENGINE_SWEEP_ENABLE=1`.

**Hatás:** „nehéz” inputokon (DXF-ből jövő, 61–78 vertexes kontúrok)
aszimptotikus nyereség. Kisebb ringeken a 3.2.a prefilter + brute force
gyorsabb (kisebb konstansok), ezért csak küszöb felett kapcsoljon be.

**Kockázat:** legmagasabb a P2-n belül. Csak akkor menjen, ha a 3.2.a/3.2.b
telemetria-adataiból bizonyítható, hogy a maradék hotspot ringméret-skálázódás.

### 3.3 P3 — Strukturális javítás: a BLF fallback szűkítése

#### 3.3.a Szelektív NFP/BLF per-part (ne global fallback)

**Hol:** `rust/nesting_engine/src/main.rs:431-446` és
`rust/nesting_engine/src/multi_bin/greedy.rs:637-781`.

**Mit:** az `effective_placer` helyett a `greedy_multi_sheet` kapjon egy
**per-part** placer-választást. A „hole-free” részhalmaz NFP-vel, a
„hole-ful” részhalmaz BLF-fel menjen. Az `NfpCache` marad
`greedy.rs:649`-ben, csak a hole-mentes specekre használódik.

**Hatás:** a jelenlegi worst-case
„egyetlen lyukas part miatt a hole-mentes 100 part is BLF-en megy”
megszűnik. Az NFP út gyors candidate-cappel dolgozik (4096), így a
hole-mentes többség **nem** ragad be.

**Kockázat:** magas. A determinisztikus sorrendi döntések megváltoznak
(pl. `PartOrderPolicy::ByArea` hogyan keveri a két placer placementjeit
ugyanarra a sheet-re?). Külön task-canvast és alapos regressziós
keresztteszt-mátrixot igényel a `canvases/nesting_engine/` alatt
(a repo-szabály szerint).

**Előfeltétel:** sikeres P1 és a P2.a legalább.

#### 3.3.b Hole-aware NFP vagy IFP-alapú cavity-kitöltés

**Hol:** új modul a `rust/nesting_engine/src/nfp/`-ben.

**Mit:** a Bennell–Song Minkowski-sum alapú NFP kiterjesztése
holes + slits támogatására, vagy külön IFP (inner-fit polygon) pipeline,
ami a placed polygonok holes-listájából generál „jogos” cavity-
kitöltési vektorokat, NEM 1492-anchor-es nudge-cloud-dal.

**Hatás:** a jelenlegi 2.4 cavity-robbanás szerkezeti oka tűnik el.

**Kockázat:** a legnagyobb — algoritmus-szintű kutatás + új
geometriai kernel.

**Ajánlott módszer:** külön `canvases/nesting_engine/hole_aware_nfp.md`
canvas + POC a `poc/` alatt, és csak akkor kerüljön mainstream-be, ha
a P1/P2 után még mindig a cavity-költség dominál.

---

## 4. Operatív kísérőjavítások (SA amplifier + monitorozás)

### 4.1 SA budget-hard-limit boundary védelem

**Hol:** `rust/nesting_engine/src/search/sa.rs:179-195`.

**Mit:** a clamp helyett vezessünk be egy **soft ceiling**-et, hogy
`sa_eval_budget_sec × max_iters` **ne tudja pontosan kitölteni** a
`time_limit_sec`-et. Pl. legyen tartalék 5 %, vagy a
`NESTING_ENGINE_SA_SAFETY_MARGIN_FRAC=0.05` env-vel kikényszeríthető.

Azaz a kód legyen:

```rust
let reserve_sec = (time_limit_sec as f64 * safety_margin).ceil() as u64;
let usable_time_sec = time_limit_sec.saturating_sub(reserve_sec).max(1);
let max_evals = usable_time_sec / eval_budget_sec;
let max_iters = max_evals.saturating_sub(1);
requested_iters.min(max_iters)
```

**Hatás:** a korábbi 1200 / 60 = 20 eval „határig ég” jelenség eltűnik —
lesz tartalék az output-serializálásra és a worker finalizálására is.

**Kockázat:** alacsony, de a `SA_PROFILE_V1` metrikákban a
`sa_eval_count` csökkenhet → frissíteni kell az SA-hoz kapcsolódó
regressziós teszteket (`sa.rs:655, 730, 744, 774, 803, 926` környékén
futó testek).

### 4.2 BLF_PROFILE_V1 + SA_PROFILE_V1 telemetria kiterjesztése

**Hol:** `blf.rs:38-95` (a struct már létezik) + `sa.rs:229-231`.

**Mit:** a jelenlegi `BlfProfileV1` már mér mindent, amit az audit
kért, de hiányzik:

- `instance_cap_hits` (hány instance-t vágott le a 3.1.a szerinti cap),
- `cavity_hole_bbox_fit_skipped` (hány hole-t szűrt ki a 3.1.c.1),
- `cavity_anchor_cap_applied` (hány hole-ra alkalmaztuk a cap-et).

Ezek a jövőben bizonyítani fogják, hogy a cap-ek hol hatnak ténylegesen,
és nem „csak fantáziaoptimum”-ok.

**Kockázat:** gyakorlatilag nulla — csak új `u64` mezők.

---

## 5. Mit bizonyít, és mit nem, ez az audit

**Bizonyított:**

1. A global NFP → BLF fallback a 2.1-ben hivatkozott kód miatt **ma is**
   aktív lehet egyetlen lyukas partra.
2. A BLF rács- és cavity-sweepjében **nincs** per-instance cap /
   stagnation cutoff (2.2, 2.3).
3. A `translate_polygon` allokáció **a can_place előtt** fut le (2.5).
4. A narrow-phase ma is **brute force O(n·m)** szegmenspár-check, edge-
   vagy sweep-szintű gyorsítóstruktúra nélkül (2.6).
5. A cavity candidate generátor cap nélküli (2.4).
6. Az SA evaluation minden iterációnál **teljes** greedy/BLF
   futtatást jelent (2.9).
7. Az `sa_eval_budget_sec × max_iters` képlet miatt az SA a teljes
   `time_limit_sec`-et kitöltheti (2.10).
8. A worker determinisztikus solver-timeout esetén **újrapróbálkozik**
   (2.11), a trial tool poll-timeoutja nem retry-aware.

**Nem bizonyított** (ehhez további mérés/futás kell):

1. **Pontosan** hány százalékot vág le a P1 csomag a végfutási időből.
   A Claude_audit 156 623-as stagnation-mérése erős jelzés, de a
   jelenlegi inputra csak a cap bekötésével és egy kontrollált
   futással igazolható.
2. A P2.a AABB prefilter **pontos** hit-rate-je hole-s geometriára.
3. Hogy a `poly_strictly_within` és a `polygons_intersect_or_touch`
   aránya valós inputon ma is kb. ugyanaz, mint a Claude_audit-ban
   mérve. A `BLF_PROFILE_V1` már gyűjti ezt (`blf.rs:269-280`,
   `blf.rs:384-395`), csak új mérésből derülne ki a jelenlegi szám.

---

## 6. Javasolt ütemezés (task-rendben)

> Minden lépcsőt külön `canvases/nesting_engine/<slug>.md` +
> `codex/goals/canvases/nesting_engine/fill_canvas_<slug>.yaml` +
> `codex/reports/nesting_engine/<slug>.md` csomaggal érdemes
> ütemezni, a repo AGENTS.md-ben rögzített workflow szerint.

| Prior | Task slug javaslat | Fájlok (kulcs) |
|-------|--------------------|----------------|
| P1 | `blf_per_instance_cap_and_stagnation_cutoff` | `blf.rs:332-439`, új env-konstansok |
| P1 | `blf_cavity_anchor_cap_and_bbox_fit` | `blf.rs:497-591` |
| P1 | `blf_translate_polygon_aabb_prefilter` | `blf.rs:367-400` |
| P1 | `worker_deterministic_timeout_no_retry` | `worker/main.py:1693-1702`, `nesting_engine_runner.py:134-137` |
| P1 | `trial_tool_retry_aware_poll_timeout` | `trial_run_tool_core.py:1769-1771` |
| P2 | `narrow_phase_edge_aabb_prefilter` | `narrow.rs:244-286` |
| P2 | `placed_index_edge_rtree` | `narrow.rs:39-77` |
| P2 | `sa_budget_safety_margin` | `sa.rs:179-195` |
| P2 | `blf_profile_cap_metrics` | `blf.rs:38-95` |
| P3 | `per_part_placer_selection_instead_of_global_fallback` | `main.rs:431-446`, `greedy.rs:637-781` |
| P3 | `hole_aware_nfp_or_ifp_cavity` | új modul `rust/nesting_engine/src/nfp/` alatt |

A P1 csomag alacsony kockázattal, determinizmus-megőrzéssel ad
mérhető gyorsulást a Claude_audit-ban bizonyított stagnálás-ágon.
A P2 a legnagyobb falidő-részt célozza (~67 %). A P3 strukturális
lépés, és csak akkor szükséges, ha a P1+P2 után is hole-os
inputokon jelentkezik a timeout.

---

## 7. Hivatkozott kódhelyek (gyűjtemény)

- `rust/nesting_engine/src/main.rs:431-446` — NFP→BLF global fallback.
- `rust/nesting_engine/src/placement/blf.rs:129-495` — BLF main loop,
  per-instance stagnation telemetria (nem enforced).
- `rust/nesting_engine/src/placement/blf.rs:497-591` —
  cavity candidate generator és hole anchor cloud.
- `rust/nesting_engine/src/placement/blf.rs:683-692` — `translate_polygon`.
- `rust/nesting_engine/src/placement/nfp_placer.rs:27` —
  `MAX_CANDIDATES_PER_PART = 4096` (NFP van cap, BLF nincs).
- `rust/nesting_engine/src/feasibility/narrow.rs:79-214` — `can_place`
  és `can_place_profiled`.
- `rust/nesting_engine/src/feasibility/narrow.rs:244-286` — narrow-phase
  brute-force.
- `rust/nesting_engine/src/multi_bin/greedy.rs:55-193` — StopPolicy
  (wall-clock és work-budget), egységnyi consume-költség.
- `rust/nesting_engine/src/multi_bin/greedy.rs:637-781` —
  `greedy_multi_sheet` és sheet-ről-sheet-re továbbgyűrűző placed-state.
- `rust/nesting_engine/src/search/sa.rs:179-316` — SA config, clamp,
  eval callback.
- `rust/nesting_engine/src/search/sa.rs:389-407` —
  `eval_state_cost_with_result`, greedy_multi_sheet hívás evaluationként.
- `vrs_nesting/config/nesting_quality_profiles.py:41-47` —
  `quality_aggressive` profile default `sa_eval_budget_sec=1`.
- `vrs_nesting/runner/nesting_engine_runner.py:126-137` — solver
  subprocess timeout és hibaüzenet.
- `worker/main.py:1693-1702` — retry/requeue ág.
- `worker/main.py:198` — `WORKER_RETRY_DELAY_S` default 30.
- `scripts/trial_run_tool_core.py:1769-1804` — poll-timeout képlet.

---

*Ez a dokumentum kizárólag a jelenleg a repo `main` ágán található kód
 alapján készült. A „jövőbeli” hatásbecslések (3.1, 3.2 blokkban szereplő
 percentuális hivatkozások) a korábbi Claude_audit méréseiből idéznek,
 nem új mérésekből — minden ilyen szám **más** futási kontextusra
 vonatkozott, és a P1 javaslatok elfogadása után új, kontrollált
 kontrollfutás kell a validálásra.*
