# canvases/nesting_engine/nfp_computation_concave.md

> **Mentés helye a repóban:** `canvases/nesting_engine/nfp_computation_concave.md`
> **TASK_SLUG:** `nfp_computation_concave`
> **Terület (AREA):** `nesting_engine`

---

# NFP Nesting Engine — F2-2: Konkáv NFP (orbitális exact) + determinisztikus, golyóálló fallback + boundary clean

## 🎯 Funkció

Konkáv (irreguláris) polygon-pár **No-Fit Polygon (NFP)** számítása Fázis 2-höz.

**Kötelező stratégia (nem alkuképes):**
1) **Stabil alap (default):** konkáv → **konvex dekompozíció** → konvex NFP (F2-1 Minkowski) → `i_overlay` unió → `boundary_clean`  
2) **Orbitális “exact” mód:** SVGNest/Deepnest jellegű **állapotgép + döntési logika** alapján (nem kódport), **touching group** (Burke 2007 + Luo&Rao 2022) szemlélettel; ha beragad/loop: visszavált stabil alapra.

**Nem cél:**
- F2-3 (IFP/CFR placer)
- F2-4 (SA/GA kereső)
- `rust/vrs_solver/` módosítása
- Python oldali “smart pair / pre-nest” (külön task)

---

## 🧠 Fejlesztési részletek

### Kötelező olvasmány / szabályok (prioritás)

1. `AGENTS.md`
2. `docs/codex/overview.md`
3. `docs/codex/yaml_schema.md`
4. `docs/codex/report_standard.md`
5. `docs/nesting_engine/tolerance_policy.md` (SCALE, TOUCH_TOL)
6. `rust/nesting_engine/src/geometry/types.rs` (Point64, i128 cross, CCW/convex)
7. `rust/nesting_engine/src/nfp/cache.rs` (kulcs rögzített: shape_id + rotation_steps)
8. `rust/nesting_engine/src/nfp/convex.rs` (F2-1 Minkowski)
9. `rust/nesting_engine/tests/nfp_regression.rs` (fixture futtatás)
10. `canvases/nesting_engine/nesting_engine_backlog.md` (F2-2 DoD)

Ha bármelyik hiányzik: STOP, pontos fájlútvonallal jelezni.

---

### Érintett fájlok

**Új (backlog szerint kötelező):**
- `rust/nesting_engine/src/nfp/concave.rs` — konkáv NFP: stabil alap + orbitális exact
- `rust/nesting_engine/src/nfp/boundary_clean.rs` — kimeneti boundary tisztítás (degenerált/önmetsző)

**Módosul (szükséges integráció):**
- `rust/nesting_engine/src/nfp/mod.rs` — belépési pont + error típusok + dispatch
- `rust/nesting_engine/tests/nfp_regression.rs` — konkáv fixture támogatás + determinisztika teszt
- `poc/nfp_regression/README.md` — concave fixture formátum leírás
- `poc/nfp_regression/*.json` — legalább 5 konkáv fixture (touching, slits, lyukak, interlock, multi-contact)
- `codex/codex_checklist/nesting_engine/nfp_computation_concave.md`
- `codex/reports/nesting_engine/nfp_computation_concave.md`
- `codex/reports/nesting_engine/nfp_computation_concave.verify.log` (verify írja)

**Felderítésből rögzített valós DXF inputok (alakzatpár-forrás):**
- `samples/dxf_demo/stock_rect_1000x2000.dxf`
- `samples/dxf_demo/part_arc_spline_chaining_ok.dxf`
- `samples/dxf_demo/part_chain_open_fail.dxf`

**Nem módosul (tilos):**
- `rust/vrs_solver/**`
- `scripts/check.sh`, `scripts/verify.sh` (csak futtatjuk)
- F1/F2-1 cache kulcs: `NfpCacheKey` mezők és típusok

---

### Architektúra és API (backlog + F2-1 kompatibilitás)

#### Publikus belépési pont (javaslat, modulon belül)
- `compute_concave_nfp(a, b, options) -> Result<Polygon64, NfpError>`
- `options` minimálisan: `{ mode: StableDefault | ExactOrbit, max_steps, enable_fallback }`

**Cache kompatibilitás:**
- Nem nyúlunk a `NfpCacheKey`-hez.
- A concave NFP eredmény ugyanúgy `Polygon64` (outer + holes).

---

### Nem alkuképes megkötések (a projekt “hard rules”)

#### 1) Minkowski+dekompozíció a stabil alap, orbitális exact csak “fölötte”
- Default útvonal: **decompose → convex NFP → union → clean**
- Orbitális exact: csak akkor tér vissza exact NFP-vel, ha:
  - nincs loop,
  - nincs invalid boundary,
  - és determinisztikus.

#### 2) Burke 2007 + Luo&Rao 2022 szemlélet: touching group kötelező
- Többszörös érintkezés esetén (3–4 kontakt): **touching group** képzés
- Candidate slide vektorok generálása touching groupból
- Determinisztikus tie-break: ugyanarra a bemenetre bit-azonos output

#### 3) SVGNest/Deepnest: állapotgép és döntési logika, nem kódport
- Cél: a “next translation vector” kiválasztási logika és loop guard mintázat átvétele
- Tilos: kódszerkezet / változónevek / konkrét implementáció “átmásolása”

#### 4) i128 minden orientáció/cross alapú döntésnél
- `SCALE=1_000_000` mellett i64 szorzás overflow-zhat → csendes hibák
- Minden turn/orientation, collinear merge, angle compare: i128

#### 5) f64 alapú point-in-polygon kerülendő
- Nincs `geo`-s f64 PIP a core döntésekben
- Ha kell PIP: integer winding / ray-cast saját implementációval Point64-on

#### 6) boundary_clean nem opcionális
- Kimeneti NFP **mindig valid polygon**: nincs önmetszés, nincs 0 hossz él, nincs duplikált csúcs
- Canonicalizáció: fix kezdőpont, fix irány (outer CCW), collinear merge

---

### Stabil alap: Konvex dekompozíció + Minkowski + unió

**Cél:** olyan NFP, ami nem ragad és determinisztikus.

Implementációs elv:
1. `decompose_to_convex(Polygon64)` (ear-clipping jelleg, integer alapokon)
2. minden konvex darabpárra: `compute_convex_nfp(part_a, part_b)` (F2-1)
3. union: `i_overlay` boolean union a rész-NFP-kre
4. `boundary_clean` a végén

Megjegyzés: a dekompozíció lehet egyszerű (trianguláció), majd később optimalizálható (merge),
de a determinisztika kötelező már MVP-ben.

---

### Orbitális exact: állapotgép vázlat (implementálandó minimum)

**Állapot:**
- B aktuális transzlációja (Point64)
- aktuális kontaktok / touching group signature
- visited set (hash) + step counter

**Loop guard / dead-end szabály:**
- ha nincs legális candidate vektor → fallback stabil alapra
- ha visited ismétlődik → fallback stabil alapra
- max_steps túllépés → fallback stabil alapra

**Determinista tie-break:**
- candidate vektorok rendezése: (szög/irány, majd lex(dx,dy), majd kontakt indexek)
- mindig az első legális vektor

**Kimenet:**
- B anchor pontjának pályája → boundary pontok
- `boundary_clean` → canonical ring

---

## 🧪 Tesztállapot

### DoD (backlog szerint)

- [ ] Legalább 5 kézzel összeállított konkáv tesztpár PASS (touching, slits, lyukak)
- [ ] NFP boundary mindig valid polygon (nincs önmetszés a kimenetben)
- [ ] Valós DXF készlet legalább 3 alakzat-párjára helyes NFP generálódik
- [ ] Regressziós tesztkészlet: fixture fájlok `poc/nfp_regression/` alatt
- [ ] `./scripts/verify.sh --report codex/reports/nesting_engine/nfp_computation_concave.md` PASS

### Minimális tesztterv (konkrét)

1) `rust/nesting_engine/tests/nfp_regression.rs`:
- concave fixture-ek futtatása
- **determinism check**: kétszer számolva azonos canonical ring
- **validity check**: boundary_clean után nincs self-intersection (a repo meglévő eszközeivel, vagy i_overlay validate)

2) Fixture-ek (legalább 5):
- `concave_touching_group.json`
- `concave_slit.json`
- `concave_hole_pocket.json`
- `concave_interlock_c.json`
- `concave_multi_contact.json`

3) Valós DXF 3 pár:
- a repóban már meglévő valós fixture készletből kiválasztva (pontos útvonalakat a felderítő step rögzíti a canvas „Kapcsolódások” részébe)
  - Pár #1: `samples/dxf_demo/stock_rect_1000x2000.dxf` × `samples/dxf_demo/part_arc_spline_chaining_ok.dxf`
  - Pár #2: `samples/dxf_demo/stock_rect_1000x2000.dxf` × `samples/dxf_demo/part_chain_open_fail.dxf`
  - Pár #3: `samples/dxf_demo/part_arc_spline_chaining_ok.dxf` × `samples/dxf_demo/part_chain_open_fail.dxf`

---

## 🌍 Lokalizáció

Nem releváns.

---

## 📎 Kapcsolódások

- Backlog: `canvases/nesting_engine/nesting_engine_backlog.md` (F2-2)
- F2-1: `canvases/nesting_engine/nfp_computation_convex.md` + `rust/nesting_engine/src/nfp/convex.rs`
- Cache: `rust/nesting_engine/src/nfp/cache.rs` (kulcs rögzített)
- Gate: `./scripts/verify.sh` + `docs/codex/report_standard.md`
- Külső mankók (csak elvi referencia): SVGNest/Deepnest állapotgép mintázat; Burke 2007; Luo&Rao 2022
- Valós DXF forrásfájlok: `samples/dxf_demo/stock_rect_1000x2000.dxf`, `samples/dxf_demo/part_arc_spline_chaining_ok.dxf`, `samples/dxf_demo/part_chain_open_fail.dxf`
