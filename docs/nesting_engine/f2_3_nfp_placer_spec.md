# F2-3 — NFP Placer (Rect-bin) Spec

> **Státusz:** normatív specifikáció (source of truth)
>
> **Érvényességi szabály:** ha a kód/tesztek és ez a doksi ellentmondanak egymásnak, az **hibának** számít. A javítás célja mindig a **kód + tesztek + ez a doksi** összhangja. Külső auditok/riportok **nem normatívak** (háttéranyagok).

---

## 0. Cél és scope

### 0.1 Cél

Az F2-3 célja egy **NFP-alapú, determinisztikus placer** bevezetése a nesting engine-be, **rect (axis-aligned téglalap) stock bin** esetén, úgy hogy:

* a BLF baseline **megmarad** (fallback + összehasonlíthatóság),
* az NFP placer determinisztikus kimenetet ad,
* a multi-sheet greedy wrapper szerződését nem töri meg,
* CI-ben mérhető és lezárható DoD (determinism + functional + perf gate) van.

### 0.2 Nem cél (out-of-scope F2-3-ban)

* **Irregular bin / maradék lemezek** (külön backlog)
* **Hole-aware NFP/CFR** (part-in-part NFP placerrel) — külön ticket (F2-3C)
* **Kerf dinamikus kezelése F2-3-ban** (kerf később “part geóra ráégetett” pipeline lépés)
* Optimális (globálisan legjobb) elrendezés; F2-3 elsődlegesen stabil és determinisztikus.

---

## 1. Terminológia

* **Bin / Stock:** az a tábla, amire pakolunk. F2-3-ban: **axis-aligned téglalap**.
* **Part:** a pakolandó alkatrész (polygon outer + opcionális holes).
* **Translation / eltolás:** `(tx, ty)` i64 egységben (µm skála), amely a part lokális koordinátáira adódik.
* **IFP (Inner Fit Polygon):** az eltolások halmaza, ahol a part teljesen a bin belsejében marad.
* **NFP (No Fit Polygon):** az eltolások halmaza, ahol a moving part ütközne egy adott placed parttal.
* **CFR (Collision Free Region):** az eltolások halmaza, ahol a part a binben van **és** nem ütközik a placed partokkal.

Formálisan:

* `U = union(NFP_i)`
* `CFR = IFP \ U`

---

## 2. Determinizmus alapelvek

A teljes F2-3 placernek determinisztikusnak kell lennie:

* A bemenet azonos → a kimenet (placements) azonos.
* A boolean/multipolygon eredmények **kanonizálva és rendezve** vannak.
* A rotációk kanonikus sorrendben futnak.
* A jelölt pontok (candidates) kanonikus sorrendben vannak próbálva.
* A cache kulcs **stabil, seed-mentes**.

---

## 3. Integrációs architektúra

### 3.1 BLF baseline megtartása

* A BLF placer a baseline marad.
* NFP placer új opcióként kerül be.

### 3.2 Választás futásidőben

* **CLI flag**: `--placer blf|nfp` (default: `blf`)
* A JSON v2 IO contract nem változik.

### 3.3 Multi-sheet felelősség

* A multi-sheet “nyiss új sheetet” logika a wrapperben marad.
* A placer egy **single sheet fill** feladatot végez.

### 3.4 Hybrid gating (holes / hole_collapsed)

Még ha `--placer nfp` is van:

* Ha bármely part **holes-os** (nominal vagy inflated) → **BLF**
* Ha bármely part `status == hole_collapsed` → **BLF**

Indok: F2-3-ban a hole-aware NFP/CFR out-of-scope.

---

## 4. Koordinátarendszer és normalizálás

### 4.1 Part referencia és normalizálás

* A placer által használt part-geó **normalizált**: `min_x = 0`, `min_y = 0` a part lokális koordinátáiban.
* A placer eltolása `(tx, ty)` ezt a normalizált partot tolja.

Következmény: a part AABB-ja `x ∈ [0, w]`, `y ∈ [0, h]` (ahol `w = max_x`, `h = max_y`).

### 4.2 Egységek

* Minden koordináta i64 µm skálán (a meglévő mm→µm skálázási konvenció szerint).

---

## 5. Spacing, margin, kerf policy

### 5.1 Kerf

* **Nem része F2-3-nak**: a kerf-et később a part geóra “ráégetjük” egy külön pipeline lépésben.
* F2-3-ban a `kerf_mm` nem jelenik meg a placer matematikájában.

### 5.2 Spacing (part–part távolság)

* A spacing-et **part inflate** kezeli.
* Ajánlott: `inflate_delta = spacing / 2` (ha a spacing a két alkatrész közötti minimális rés). Így két inflált part ütközése pontosan a spacing feltételt kényszeríti.

### 5.3 Margin (part–bin edge távolság)

* A margin a **bin belső téglalapjának zsugorításával** van kezelve.

### 5.4 Bin belső téglalap (inner rect)

Legyen a nyers bin téglalap `B = [bx0..bx1] × [by0..by1]`.

* A part inflate miatt a bin edge-hez is tartani kell a spacing-et (konzervatív, gyártható). Ezért:

**`shrink = margin + spacing/2`**

* A belső bin: `B_in = shrink(B, shrink)`.

Megjegyzés:

* Ha a `spacing/2` nem egész µm, a determinisztikus kerekítés szabályát rögzíteni kell (pl. floor/ceil). A cél a konzervatív (biztonságos) irány.

---

## 6. IFP (Inner Fit Polygon) definíció — Rect bin

### 6.1 IFP típus

* F2-3-ban az IFP **téglalap** a transzlációs térben.
* Reprezentáció: `Polygon64` 4 csúccsal (boolean engine kompatibilitás).

### 6.2 IFP képlet (normalizált part esetén)

Legyen:

* `B_in = [ix0..ix1] × [iy0..iy1]` a belső bin (margin+spacing/2 után)
* a part AABB-ja: `[0..w] × [0..h]`

A megengedett eltolások:

* `tx ∈ [ix0, ix1 - w]`
* `ty ∈ [iy0, iy1 - h]`

Ha `ix1 - w < ix0` vagy `iy1 - h < iy0`, akkor az IFP üres.

---

## 7. Rotációk

### 7.1 Meglévő rotáció opciók támogatása

* A placer támogatja a bemenet által engedélyezett rotációkat (`allowed_rotations_deg`).

### 7.2 Kanonikus sorrend

* A rotáció lista: `unique + sort` növekvő fok szerint.
* A rotációs sorrend része a determinisztikus tie-breaknek.

### 7.3 Rotáció és shape

* A rotált part geót külön “shape”-nek tekintjük (külön `shape_id`).

---

## 8. Touching policy

### 8.1 Alapelv

* **Touching (érintkezés) = infeasible**.
* A tolerancia: `TOUCH_TOL = 1 µm` (i64 = 1).

### 8.2 Következmény

* A CFR határpontjai gyakran touching jellegűek → a jelölt generálásnak belső pontot kell képeznie (nudge).

---

## 9. Boolean policy

### 9.1 Regularized boolean

* A CFR számításban minden boolean (union, difference) **regularized**.
* Non-regularized boundary-megoldások megőrzése **nem cél** (touching úgyis tiltott).

### 9.2 Degeneráció elnyelés

Boolean után kötelező:

* self-intersect / spike / duplikált pont tisztítás,
* 0-területű ring/komponens eldobás,
* minimális területküszöb (konzervatív, determinisztikus),
* kanonizálás és rendezés (lásd 10. fejezet).

---

## 10. CFR mint MultiPolygon + kanonizálás

### 10.1 CFR típusa

* A CFR mindig **MultiPolygon**: `Vec<Polygon64>`.
* Komponenst **tilos** eldobni (“legnagyobb komponens” heurisztika tiltott).

### 10.2 Kanonizálás

Minden CFR komponensre:

* outer ring orientáció rögzítése (projekt konvenció szerint),
* lexikografikusan legkisebb pont megkeresése az outer ringben,
* pointlista rotálása, hogy ezzel induljon,
* hole ringekre ugyanez (konvenció szerint CW/CCW),
* opcionális collinear simplification determinisztikus szabállyal.

### 10.3 Determinisztikus komponens-sorrend

A komponensek rendezési kulcsa (totális rendezés):

1. `min_point (x,y)` lexicographic
2. `abs(area)`
3. `vertex_count`

---

## 11. Candidate selection (jelöltválasztás)

### 11.1 Kiválasztási stratégia

* **First-feasible** determinisztikus próbálási sorrendben.
* Célfüggvény: **min (y, x)** (BLF-hez igazodó).

### 11.2 Alapjelöltek

* Base candidates = CFR komponensek **outer ring vertexei**.

### 11.3 Teljes tie-break sorrend

A jelöltek rendezési kulcsa:

1. `y` növekvő
2. `x` növekvő
3. `rotation_rank`
4. `cfr_component_rank`
5. `vertex_rank_within_component`
6. `nudge_rank`

A rendezett jelölteket sorban próbáljuk, az első `can_place == true` nyer.

---

## 12. Nudge / interior point stratégia

### 12.1 Miért kell

* Touching tiltott → határjelöltek többsége bukik.

### 12.2 Nudge lista (fix, determinisztikus)

* lépések: `s ∈ {1, 2, 4} µm`
* irányok fix sorrendben (8 irány):

  1. `( +s,  0)`
  2. `(  0, +s)`
  3. `( +s, +s)`
  4. `( -s,  0)`
  5. `(  0, -s)`
  6. `( -s, -s)`
  7. `( -s, +s)`
  8. `( +s, -s)`

### 12.3 Candidate halmazképzés

* Minden base vertexhez generáljuk a nudge-olt pontokat.
* Előszűrés: IFP téglalapon kívül eső pontok eldobása.
* Dedupe: `(tx,ty)` párok HashSet-ben (determinista bejárással).

### 12.4 Cap / limit

* `MAX_CANDIDATES_PER_PART_PER_ROT = 4096`
* `MAX_VERTICES_PER_COMPONENT = 512` (kanonikus sorrend első 512)

---

## 13. HoleCollapsed policy

### 13.1 Nem fatális

* `hole_collapsed` **nem fatális**: a part nesting geója degradál.

### 13.2 Nesting geó: outer-only

* `hole_collapsed` esetén a nesting geó **mindig** holes nélküli (`holes=[]`).

### 13.3 Hybrid gating

* `hole_collapsed` esetén a placer **BLF** (nem NFP).

---

## 14. NFP cache

### 14.1 Cache cél

* NFP compute drága → ismétlések elkerülése.

### 14.2 Kulcs

* `shape_id_a`: kanonizált geometria stabil u64 hash (placed part)
* `shape_id_b`: kanonizált geometria stabil u64 hash (moving part, rotáció után)
* `rotation_steps_b`: `deg` (implicit 1° step) i16-ben

### 14.3 shape_id definíció

* Canonicalize után u64 hash a pontlistákból.
* **Seed-mentes** (nem RandomState).

### 14.4 Scope

* Cache **multi-sheet scope**: a full run során él (nem sheetenként reset).

### 14.5 Compute mód

* Lazy compute: csak akkor számolunk, ha kell.

### 14.6 Méretkorlát

* `MAX_ENTRIES` felett determinisztikus “clear all” (nem LRU).

---

## 15. Multi-sheet szerződés (wrapper kompatibilitás)

### 15.1 Wrapper stop-condition

* A wrapper akkor áll le, ha egy körben `placed_this_round == 0`.

### 15.2 Placer kötelezettség

A placer sheet-fill futásban:

* végigjárja a remaining partokat,
* minden part összes engedélyezett rotációját megpróbálja,
* ha egy part nem fér, **nem áll le**, csak skipeli,
* `0 placed` csak akkor igaz, ha **egyik part sem** helyezhető el.

### 15.3 Kötelező regressziós fixture

* Olyan input, ahol az első N part nem fér, de egy későbbi igen.
* Elvárás: legalább 1 part felkerül a sheetre.

---

## 16. DoD / Gates (CI és lokál)

### 16.1 Fixture készlet (minimum)

* **F0 Sanity**: 1–2 part, biztosan felmegy
* **F1 Wrapper contract**: első pár nem fér, későbbi igen
* **F2 Touching stress**: nudge nélkül bukna, nudgéval megy
* **F3 Rotation coverage**: csak 90°-kal fér fel

Megjegyzés: holes-os fixture-t az NFP placer gate nem futtat (3B gating), az BLF-hez külön maradhat.

### 16.2 Determinism gate

* NFP módban ugyanaz a fixture **3 futás** → output hash azonos.

### 16.3 Functional gate

* Minden fixture hozza a minimum elvárt placed countot (F1-ben >= 1).

### 16.4 Performance gate

* NFP módban időlimit fixture csomagra (CI-hez hangolva).
* Kötelező stat log:

  * NFP compute count
  * cache hit/miss
  * boolean op count (ha mérhető)

### 16.5 “No worse than BLF” alapelv (basic fixtures)

* A kijelölt basic fixture készleten az NFP placer nem lehet rosszabb a BLF-nél minimum elhelyezett darabszámban.

---

## 17. Logging / auditálhatóság

Futáskor a log/eredmény fejlécben rögzítendő:

* placer: `blf` vagy `nfp` (ha gating miatt BLF lett, az is)
* touching policy: forbidden
* boolean: regularized
* holes policy: gated
* nudge: enabled ({1,2,4} µm)

---

## 18. Nem normatív háttéranyagok

Az alábbi anyagok háttérként megőrzendők, de **nem normatívak**:

* `deep-research-report.md`
* `deep-research-report_critics.md`
* `f2_3_nfp_placer_architecture_and_strategy.md`
* `VRS_nesting_F2-3_audit.md`

---

## 19. Kapcsolódó backlog / jövőbeli ticketek

* **F2-3C**: hole-aware NFP/CFR (part-in-part NFP placerrel)
* **Irregular bins**: determinisztikus stock offset + IFP általánosítása
* **Kerf-baked pipeline step**: kerf ráégetése part geóra, F2-3 egyszerűsítése

---

## 20. Rövid összefoglaló (policy döntések)

* Placer választás: CLI flag, BLF baseline megmarad.
* IFP: AABB téglalap a transzlációs térben (rect bin).
* Part ref: normalizált (minx=miny=0).
* Margin: bin shrink, Spacing: part inflate (+ bin shrink spacing/2).
* Holes/hole_collapsed: **BLF gate**, hole-aware NFP/CFR külön ticket.
* Touching: tiltott, nudge kötelező.
* CFR: MultiPolygon, canonicalize + sort, regularized boolean.
* Candidate selection: first-feasible, min(y,x), determinisztikus tie-break.
* Cache: geometry-hash shape_id, rotation_steps=deg, multi-sheet scope, hard cap.
* Wrapper contract: placer exhaustive pass, 0 placed csak ha senki sem fér.
* DoD: fixtures F0–F3 + determinism + functional + perf.
