# canvases/nesting_engine/nesting_engine_backlog.md

> **Mentés helye a repóban:** `canvases/nesting_engine/nesting_engine_backlog.md`
> **TASK_SLUG:** `nesting_engine_backlog`
> **Terület (AREA):** `nesting_engine`

---

# NFP-alapú Nesting Motor Backlog (Fázis 1–3)

## 🎯 Funkció

Ez a canvas a Sparrow-t teljes egészében kiváltó, saját tulajdonú, NFP-alapú 2D irreguláris nesting motor fejlesztési tervét rögzíti. A motor önálló Rust crate-ként épül (`rust/nesting_engine/`), a meglévő Python pipeline (CLI, DXF IO, runner, validator, exporter) újrahasznosításával.

**Stratégiai döntések (nem alkuképes):**

- Saját Rust motor — teljes kontroll, nincs külső licenc kockázat
- NFP (No-Fit Polygon) alapú placement — ipari minőségű, komplex irreguláris alakzatokra alkalmas
- Geometriai offset + feasibility narrow-phase: `i_overlay` (pure Rust)
- Feasibility broad-phase: AABB minimum, opcionális `rstar` gyorsítással, determinisztikus találat-sorrenddel
- Lexikografikus célfüggvény: P0 (0 overlap, 0 out-of-bounds) → P1 (min sheet count) → P2 (max remnant value) → P3 (min cut time proxy)
- Determinisztikus output: azonos input + seed → bit-azonos JSON export

**Nem cél ebben a backlogban:**

- A meglévő `rust/vrs_solver/` módosítása (az regressziós baseline marad)
- GUI, web platform, ERP/MES integráció
- G-kód generálás (a motor JSON-t ad, DXF export poszt-processzálás)
- ESICUP benchmark 95%-os elérése (nem reális hobbi projekt célkitűzés)

---

## 🧠 Fejlesztési részletek

### Repo struktúra (új elemek)

```
rust/
  vrs_solver/              ← MARAD: regressziós baseline, nem módosítjuk
  nesting_engine/          ← ÚJ Rust crate
    Cargo.toml
    src/
      main.rs              ← CLI belépési pont (JSON in → JSON out)
      geometry/            ← polygon, scale policy, i_overlay offset
      nfp/                 ← NFP számítás, NFP cache
      feasibility/         ← can_place(), AABB broad-phase, narrow-phase
      placement/           ← BLF baseline placer, CFR candidate generálás
      search/              ← SA metaheurisztika (Fázis 2)
      multi_bin/           ← multi-sheet allokáció, iteratív stratégia
      export/              ← JSON output contract v2

vrs_nesting/
  runner/
    nesting_engine_runner.py   ← ÚJ Python adapter (mint vrs_solver_runner.py)

docs/
  nesting_engine/
    architecture.md            ← ÚJ: modulok, interfészek, döntések
    io_contract_v2.md          ← ÚJ: input/output JSON séma
    tolerance_policy.md        ← ÚJ: epsilon, touching policy, scale
```

### Meglévő elemek, amelyek újrahasznosíthatók

- `vrs_nesting/dxf/importer.py` — DXF → polygon pipeline (nominális geometria)
- `vrs_nesting/dxf/exporter.py` — nominális DXF export sheet-enként
- `vrs_nesting/run_artifacts/run_dir.py` — run könyvtár kezelés
- `vrs_nesting/validate/solution_validator.py` — validátor (bővítendő v2 contractra)
- `vrs_nesting/cli.py` — CLI belépési pont (új subcommand kell)
- `scripts/check.sh`, `scripts/verify.sh` — gate infrastruktúra
- `rstar` dependency (opcionális) — broad-phase gyorsítás nagy elemszámnál
- Meglévő Codex workflow: canvas + yaml + gate

---

## Fázis 1 — Truth Layer (determinisztikus alap, mérhető baseline)

**Cél:** Legyen egy futó, determinisztikus rendszer, ami a valós DXF készleten mérhető eredményt ad. Még nem NFP — az az alapszint, amihez képest az NFP javulást mérni fogjuk.

### F1-1 — `nesting_engine_crate_scaffold`

**Leírás:** Új Rust crate létrehozása (`rust/nesting_engine/`), `i_overlay` dependency bekötése, alapvető polygon típusok és scale policy definiálása.

**Érintett fájlok (új):**
- `rust/nesting_engine/Cargo.toml`
- `rust/nesting_engine/src/main.rs`
- `rust/nesting_engine/src/geometry/mod.rs`
- `rust/nesting_engine/src/geometry/types.rs` — Point64, Polygon64, scale policy (SCALE = 1_000_000i64 / mm)
- `rust/nesting_engine/src/geometry/offset.rs` — i_overlay inflate/deflate wrapper
- `docs/nesting_engine/tolerance_policy.md`

**Érintett fájlok (módosul):**
- `scripts/check.sh` — új crate build hozzáadása
- `.github/workflows/repo-gate.yml` — új crate CI build

**DoD:**
- [ ] `cargo build --release` PASS az új crate-re
- [ ] SCALE policy dokumentálva és tesztelve (mm → i64 → mm round-trip)
- [ ] i_overlay offset: outer inflate + hole deflate egy egyszerű téglalapra PASS
- [ ] `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_crate_scaffold.md` PASS

**Kockázat + mitigáció:**
- Az `i_overlay` crate API változhat → pin konkrét verziót a Cargo.toml-ban
- Rollback: az új crate izolált, a meglévő solver nem változik

---

### F1-2 — `nesting_engine_io_contract_v2`

**Leírás:** Az új motor JSON IO contract-jának dokumentálása és példa input/output fájlok létrehozása. Ez az a szerződés, amit a Python runner és a Rust motor közt használunk.

**Érintett fájlok (új):**
- `docs/nesting_engine/io_contract_v2.md`
- `poc/nesting_engine/sample_input_v2.json` — legalább 1 valós DXF alapú minta
- `poc/nesting_engine/sample_output_v2.json` — elvárt output struktúra

**Input contract (v2) kulcsmezők:**
```json
{
  "version": "nesting_engine_v2",
  "seed": 42,
  "time_limit_sec": 60,
  "sheet": { "width_mm": 1000, "height_mm": 2000, "kerf_mm": 0.2, "margin_mm": 5.0 },
  "parts": [
    {
      "id": "part_001",
      "quantity": 10,
      "allowed_rotations_deg": [0, 90, 180, 270],
      "outer_points_mm": [[x, y], ...],
      "holes_points_mm": [[[x, y], ...], ...]
    }
  ]
}
```

**Output contract (v2) kulcsmezők:**
```json
{
  "version": "nesting_engine_v2",
  "seed": 42,
  "solver_version": "0.1.0",
  "sheets_used": 3,
  "placements": [
    { "part_id": "part_001", "instance": 0, "sheet": 0, "x_mm": 10.5, "y_mm": 20.3, "rotation_deg": 90 }
  ],
  "unplaced": [],
  "objective": { "sheets_used": 3, "utilization_pct": 78.4 },
  "meta": { "elapsed_sec": 12.3, "determinism_hash": "abc123" }
}
```

**DoD:**
- [ ] `docs/nesting_engine/io_contract_v2.md` elkészült, minden mező dokumentálva
- [ ] Példa input JSON valid a saját DXF készletből legalább 1 db-ra
- [ ] Példa output JSON struktúrája egyezik a contract-tal
- [ ] `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_io_contract_v2.md` PASS

---

### F1-3 — `nesting_engine_polygon_pipeline`

**Leírás:** A Python DXF importer kimenetéből (nominális polygon + lyukak) az inflated (offsetelt) geometria előállítása a Rust kernel segítségével. A pipeline végén minden part-nak van: nominális polygon (exporthoz) és inflated polygon (solverhez).

**Érintett fájlok (módosul):**
- `vrs_nesting/dxf/importer.py` — nominális geometria már kész, csak validáljuk a kompatibilitást
- `vrs_nesting/geometry/offset.py` — átkötés az új Rust kernelre (subprocess via JSON stdio)

**Érintett fájlok (új):**
- `rust/nesting_engine/src/geometry/pipeline.rs` — inflate_part(nominal, kerf, margin) → inflated
- `docs/nesting_engine/architecture.md` — nominal vs inflated szabály rögzítése

**Szabály (kőbe vésve):** solver = inflated geometriával dolgozik; DXF export = mindig nominálisból.

**DoD:**
- [ ] inflate_part() PASS: outer outward, holes inward, kerf+margin alapján
- [ ] HOLE_COLLAPSED diagnosztika: ha lyuk eltűnik az offset után → jelölve, nem FAIL (de logolva)
- [ ] SELF_INTERSECT diagnosztika: ha inflated polygon önmetsző → FAIL + hibakód
- [ ] Determinisztika teszt: azonos input → azonos inflated output (hash)
- [ ] `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_polygon_pipeline.md` PASS

---

### F1-4 — `nesting_engine_baseline_placer`

**Leírás:** Egyszerű, determinisztikus BLF-jellegű (Bottom-Left Fill) construction placer. Nem NFP — rács alapú candidate generálás feasibility modellel:
broad-phase AABB (+ optional rstar), determinisztikus találat-sorrend;
narrow-phase feasibility layer (i_overlay): containment + no-overlap.
Multi-sheet: iteratív "amennyit befér egy táblára" stratégia. Az NFP majd erre épül rá Fázis 2-ben.

**Érintett fájlok (új):**
- `rust/nesting_engine/src/feasibility/mod.rs` — can_place() AABB broad-phase (+ optional rstar) + i_overlay narrow-phase
- `rust/nesting_engine/src/placement/blf.rs` — BLF placer, rács-alapú candidate generálás
- `rust/nesting_engine/src/multi_bin/greedy.rs` — iteratív multi-sheet stratégia
- `vrs_nesting/runner/nesting_engine_runner.py` — Python adapter (mint vrs_solver_runner.py mintájára)

**Érintett fájlok (módosul):**
- `vrs_nesting/cli.py` — új subcommand: `python3 -m vrs_nesting.cli nest-v2 --input ...`
- `scripts/check.sh` — baseline smoke: közvetlen bináris (`nesting_engine nest`) + CLI smoke (`nest-v2`)

**DoD:**
- [ ] can_place() 0 false positive a fixture készleten (nominális tesztek)
- [ ] BLF placer fut és helyez el legalább 1 valós DXF-et hibamentesen
- [ ] Multi-sheet: több tábla esetén minden part elhelyezve vagy unplaced listán
- [ ] Determinizmus: azonos seed → azonos placement JSON (hash ellenőrzés)
- [ ] Python runner: `python3 -m vrs_nesting.runner.nesting_engine_runner --input X --seed S --time-limit T` PASS
- [ ] Gate smoke lefedi mind a bináris (`nesting_engine nest`), mind a CLI (`nest-v2`) futást
- [ ] Benchmark harness: a valós DXF készleten mér sheet count + utilization % (ez a baseline szám)
- [ ] `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_baseline_placer.md` PASS

**Kockázat:** A rács-alapú candidate generálás lassú lehet 1000+ példánynál → time limit paraméter kötelező, solver-bin timeout FAIL helyett partial result-ot ad.

---

### F1-5 — `nesting_engine_stock_pipeline`

**Leírás:** A táblák (stock/sheet) hasznos területének (usable area) determinisztikus kiszámítása a Rust kernelben. A meglévő Python (Shapely) alapú `offset_stock_geometry` kiváltása. A tábla külső kontúrját befelé kell tolni (deflate) a margó (margin) mértékével, míg a táblán lévő esetleges anyaghibákat/lyukakat kifelé kell tolni (inflate). Ez biztosítja a "Truth Layer" teljes determinizmusát az irreguláris táblákra (P0 cél) és a leeső darabokra (remnants) is. Kritikus matematikai szabály (Usable Area definíció): Az eltolás (clearance) mértéke szigorúan `margin_mm ! (kerf_mm / 2.0)`. A stock esetén az outer kontúr befelé, a holes kontúrok kifelé tolódnak ekkora értékkel.

**Tervezett architektúra / contract:**

- `pipeline_io.rs` kiterjesztése: `StockRequest` és `StockResponse` bevezetése a meglévő part request/response mellé.
- Geometria inverz eltolás (Rust): stock offset a part offset inverze:
  - outer: **deflate** (befelé tolás)
  - holes/defects: **inflate** (kifelé tolás)
  - implementáció `i_overlay`-val a `geometry/pipeline.rs` megfelelő ágában
- Python kivezetés: a runner egyetlen JSON-ben küldi a nyers **part** és **stock** geometriákat; a Rust motor visszaadja a "nestingre kész" determinisztikus (inflated/deflated) geometriákat.

**Érintett fájlok (módosul):**
- `docs/nesting_engine/io_contract_v2.md` — `StockRequest` és `StockResponse` definiálása
- `rust/nesting_engine/src/io/pipeline_io.rs` — új structok a stock kommunikációhoz
- `rust/nesting_engine/src/geometry/pipeline.rs` — tábla inverz eltolási logikája (outer deflate, holes inflate)
- `vrs_nesting/geometry/offset.py` — átkötés Rust subprocess hívásra a Shapely helyett (stock oldal is)

**DoD:**
- [ ] `StockRequest` és `StockResponse` kiterjesztve a Rust IO rétegben
- [ ] stock_offset() PASS: outer befelé, holes kifelé tolódik a margin/kerf alapján
- [ ] A `vrs_nesting/geometry/offset.py` már nem használja a Shapely-t a stock számításhoz sem
- [ ] Determinisztika teszt: irreguláris tábla (lyukakkal) esetén is bit-azonos kimenet
- [ ] `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_stock_pipeline.md` PASS

---

## Fázis 2 — NFP Motor (mérhetően jobb kihasználtság)

**Cél:** Az NFP cache-re épülő placement váltja ki a BLF rács-alapú megközelítést. Mérhetően jobb eredmény a Fázis 1 baseline-hoz képest.

### F2-1 — `nfp_computation_convex`

**Leírás:** Konvex polygon-pár NFP számítása Minkowski-összeg alapon. Ez a legegyszerűbb eset, de önálló értékű: téglalap + egyszerű konvex alkatrészekre már itt jobb eredményt ad, mint a BLF rács.

**Érintett fájlok (új):**
- `rust/nesting_engine/src/nfp/convex.rs` — Minkowski-összeg konvex esetben
- `rust/nesting_engine/src/nfp/cache.rs` — NFP cache: (shape_id_a, shape_id_b, rotation_deg) → NFP polygon

**DoD:**
- [ ] Két konvex polygon NFP-je helyes (kézzel ellenőrzött tesztesetek)
- [ ] NFP cache hit/miss metrikák logolva
- [ ] Determinisztikus output (azonos input → azonos NFP)
- [ ] `./scripts/verify.sh --report codex/reports/nesting_engine/nfp_computation_convex.md` PASS

---

### F2-2 — `nfp_computation_concave`

**Leírás:** Konkáv (irreguláris) polygon-pár NFP számítása. Az orbit-based módszer: B-t körbeforgatjuk A körül. Ez a projekt legkritikusabb algoritmikus lépése — a valós DXF alkatrészek mind konkávak.

**Érintett fájlok (új):**
- `rust/nesting_engine/src/nfp/concave.rs` — orbit-based NFP konkáv esetben
- `rust/nesting_engine/src/nfp/boundary_clean.rs` — NFP boundary tisztítás (önmetsző élek, degenerált csúcsok)

**DoD:**
- [ ] Legalább 5 kézzel összeállított konkáv tesztpár PASS (touching, slits, lyukak)
- [ ] NFP boundary mindig valid polygon (nincs önmetszés a kimenetben)
- [ ] A valós DXF készlet legalább 3 alakzat-párjára helyes NFP generálódik
- [ ] Regressziós tesztkészlet: fixture fájlok `poc/nfp_regression/` alatt
- [ ] `./scripts/verify.sh --report codex/reports/nesting_engine/nfp_computation_concave.md` PASS

**Kockázat:** A konkáv NFP a projekt legnehezebb algoritmikus feladata. Ha elakad → fallback: konvex hull approximáció az NFP-hez (minőséget csökkent, de biztonságos), a pontos konkáv NFP külön task-ként folytatódik.

---

### F2-3 — `nfp_based_placement_engine`

**Leírás:** A BLF rács-alapú placement kiváltása NFP/IFP/CFR alapú placement-tel. A CFR (Collision-Free Region) = IFP \ NFP-unió — ez adja meg a legális elhelyezési pozíciók halmazát.

**Érintett fájlok (új/módosul):**
- `rust/nesting_engine/src/nfp/ifp.rs` — Inner-Fit Polygon: konténeren belüli mozgástér
- `rust/nesting_engine/src/nfp/cfr.rs` — CFR: IFP ∩ NFP-komplement(ek)
- `rust/nesting_engine/src/placement/nfp_placer.rs` — NFP-alapú placer (BLF-jelleg CFR-en)

**DoD:**
- [ ] IFP számítás helyes: a CFR-ben lévő pozíciókban can_place() = true
- [ ] NFP-alapú placement mérhetően jobb a Fázis 1 baseline-nál (sheet count vagy utilization %)
- [ ] Futásidő 1000 példánynál < 60 sec (NFP cache segítségével)
- [ ] `./scripts/verify.sh --report codex/reports/nesting_engine/nfp_based_placement_engine.md` PASS

---

### F2-4 — `simulated_annealing_search`

**Leírás:** SA (Simulated Annealing) metaheurisztika a darabok elhelyezési sorrendjének és rotációinak optimalizálására. A kiértékelési függvény: sorrend → NFP placement → sheet count + utilization score.

**Érintett fájlok (új):**
- `rust/nesting_engine/src/search/sa.rs` — SA motor: hőmérséklet, lehűlési ütemterv, neighborhood operátorok (swap, move, rotate)

**DoD:**
- [ ] SA fut determinisztikusan (fix seed → fix eredmény)
- [ ] SA javít a konstrukciós placement-hez képest (mérhető sheet count csökkenés)
- [ ] Time limit betartása: --time-limit sec paraméter kötelező
- [ ] `./scripts/verify.sh --report codex/reports/nesting_engine/simulated_annealing_search.md` PASS

---

## Fázis 3 — Ipari minőség

**Cél:** Production-ready hardening, edge-case kezelés, part-in-part, remnant scoring.

### F3-1 — `arc_spline_polygonization_policy`

**Leírás:** Az ARC/SPLINE kezelés véglegesítése. A meglévő Python importer polygon-izálja az íveket — ezt a policy-t kőbe vésni, tolerancia-értékeket dokumentálni, és a kritikus edge-case-eket tesztelni.

**DoD:**
- [ ] `arc_tolerance_mm` = 0.2 dokumentálva és alkalmazva
- [ ] "Arc-heavy" fixture (sok ív) tesztkészlet `samples/dxf_demo/` alatt
- [ ] 0 self-intersection a polygonizálás után ezeken a fixture-ökön
- [ ] `./scripts/verify.sh --report codex/reports/nesting_engine/arc_spline_polygonization_policy.md` PASS

---

### F3-2 — `part_in_part_pipeline`

**Leírás:** Kis alkatrészek elhelyezése nagy alkatrészek lyukaiba ("Swiss cheese" logika). Jelölt generálás nominális lyukak alapján, validálás inflated geometriával.

**DoD:**
- [ ] Legalább 1 fixture ahol part-in-part demonstrálhatóan javít (kevesebb sheet)
- [ ] Collapsed hole esetén jelölt kizárás (nem crash, hanem graceful degradation)
- [ ] 0 overlap a validátor szerint part-in-part esetén is
- [ ] `./scripts/verify.sh --report codex/reports/nesting_engine/part_in_part_pipeline.md` PASS

---

### F3-3 — `remnant_value_model`

**Leírás:** Maradék-anyag értékelése. Két azonos sheet count melletti megoldás közül az a jobb, amelyik nagyobb, kompaktabb maradékot hagy.

**Remnant score definíció:**
- `area_score` = maradék terület / tábla terület
- `compactness_score` = maradék terület / maradék bbox terület
- `min_width_score` = 1 - (vékony csík büntetés)
- `remnant_value` = w1 * area_score + w2 * compactness_score + w3 * min_width_score

**DoD:**
- [ ] Remnant score számítás implementálva és dokumentálva
- [ ] Az objektív függvény kiterjesztve: P1 (sheet count) → P2 (remnant value)
- [ ] `./scripts/verify.sh --report codex/reports/nesting_engine/remnant_value_model.md` PASS

---

### F3-4 — `full_pipeline_determinism_hardening`

**Leírás:** Teljes pipeline determinizmus garancia: fix sorrendezések, fix epsilon szabályok, fix koordináta-kerekítés. Touching policy rögzítése (touching = infeasible, konzervatív oldal).

**DoD:**
- [ ] 10 egymást követő futás azonos seed-del: bit-azonos JSON output
- [ ] Touching policy dokumentálva: `touching = infeasible` (konzervatív)
- [ ] CI determinism gate: automatikus ellenőrzés minden PR-nál
- [ ] `./scripts/verify.sh --report codex/reports/nesting_engine/full_pipeline_determinism_hardening.md` PASS

---

## ✅ Pipálható összesítő DoD lista

### Fázis 1 — Truth Layer
- [ ] F1-1: `nesting_engine_crate_scaffold` — új Rust crate, i_overlay, scale policy
- [ ] F1-2: `nesting_engine_io_contract_v2` — JSON IO contract dokumentálva + példák
- [ ] F1-3: `nesting_engine_polygon_pipeline` — nominal → inflated pipeline
- [ ] F1-4: `nesting_engine_baseline_placer` — BLF placer + Python runner + benchmark harness
- [ ] F1-5: `nesting_engine_stock_pipeline` — determinisztikus stock offset (inverz infláció) a Rust kernelben

### Fázis 2 — NFP Motor
- [ ] F2-1: `nfp_computation_convex` — konvex NFP + cache
- [ ] F2-2: `nfp_computation_concave` — konkáv NFP + boundary clean
- [ ] F2-3: `nfp_based_placement_engine` — CFR/IFP/NFP alapú placer
- [ ] F2-4: `simulated_annealing_search` — SA metaheurisztika

### Fázis 3 — Ipari minőség
- [ ] F3-1: `arc_spline_polygonization_policy` — ARC/SPLINE policy véglegesítés
- [ ] F3-2: `part_in_part_pipeline` — lyukba helyezés
- [ ] F3-3: `remnant_value_model` — maradék értékelés
- [ ] F3-4: `full_pipeline_determinism_hardening` — teljes determinizmus garancia

---

## 🧪 Tesztállapot

**Fázis 1 gate (minden F1 task után kötelező):**
- `./scripts/verify.sh --report codex/reports/nesting_engine/<TASK_SLUG>.md` PASS
- 0 overlap / 0 out-of-bounds a fixture készleten
- Determinizmus: azonos seed → azonos output hash

**Fázis 2 gate:**
- Fázis 1 kapuk nem sérülnek
- NFP-alapú placement mérhetően jobb a baseline-nál (sheet count vagy utilization %)
- NFP regressziós tesztkészlet PASS (`poc/nfp_regression/`)

**Fázis 3 gate:**
- Industrial fixture suite 100% PASS
- Bit-azonos output 10 egymást követő futásban (fix seed)
- Saját DXF készleten sheet count javulás dokumentálva a baseline-hoz képest

---

## 🌍 Lokalizáció

Nem releváns (belső motor + JSON contract).

---

## 📎 Kapcsolódások

**Research dokumentumok (source of truth a tervezéshez):**
- `docs/egyedi_solver/docs/00_executive_summary_and_architecture.md`
- `docs/egyedi_solver/docs/01_phase_1_truth_layer.md`
- `docs/egyedi_solver/docs/02_phase_2_single_bin_packing_and_compaction.md`

**Meglévő repo elemek (újrahasznosítandó):**
- `vrs_nesting/dxf/importer.py` — DXF import pipeline
- `vrs_nesting/dxf/exporter.py` — DXF export
- `vrs_nesting/runner/vrs_solver_runner.py` — runner minta
- `rust/vrs_solver/` — regressziós baseline (nem módosítjuk)
- `rstar` (opcionális) — broad-phase gyorsítás nagy elemszámnál
- `docs/codex/overview.md`, `AGENTS.md` — Codex workflow szabályok

**Következő lépés (első végrehajtandó task):**
- Canvas: `canvases/nesting_engine/nesting_engine_crate_scaffold.md`
- Goal YAML: `codex/goals/canvases/nesting_engine/fill_canvas_nesting_engine_crate_scaffold.yaml`
