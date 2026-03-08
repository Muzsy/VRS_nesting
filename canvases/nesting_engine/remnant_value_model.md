# remnant_value_model

## 🎯 Funkció

**Cél:** Vezessünk be egy **determinista, integer-only P2 remnant score** modellt a `nesting_engine`-be úgy, hogy:

- az elsődleges cél **változatlanul** a feasibility / el nem helyezett példányok minimalizálása maradjon,
- utána továbbra is a **sheet count** legyen az első valódi optimalizációs cél,
- és csak **azonos unplaced + azonos sheets_used** esetén döntsön a rendszer a **jobb maradékot hagyó** megoldás javára.

Ez a task **nem exact remnant polygon extraction**. Az első F3-3 verzió legyen egy **konzervatív, repo-kompatibilis proxy modell**, ami a meglévő placer-adatokból számolható, determinisztikusan.

## Nem cél

- pontos, polygon-szintű maradék topológia számítása
- remnant inventory / későbbi készletkezelés
- cut-time proxy (az backlog szerint későbbi szint)
- új search mód vagy új placer bevezetése

## Véglegesítés (repo-állapothoz igazítva)

- Ez az F3-3 kör kifejezetten **proxy remnant model** implementáció, nem exact polygon-remnant.
- A célfüggvény sorrend fix marad: `unplaced -> sheets_used -> remnant_value_ppm`.
- A determinism hash canonicalizációs contract változatlan marad.

## 🧠 Fejlesztési részletek

### Kötelező objective contract

Az objective rendezés itt legyen expliciten:

1. **kevesebb unplaced**
2. **kevesebb sheet**
3. **nagyobb `remnant_value_ppm`**
4. döntetlen esetén a meglévő determinisztikus tie-break maradjon

Fontos:
- ne gyengítsd a meglévő feasibility / timeout / partial-result viselkedést,
- a remnant score **csak tie-break / secondary objective** lehet azonos `unplaced` és `sheets_used` mellett.

### Proxy modell (első ipari verzió)

A jelenlegi repóállapothoz igazodva **nem exact free-space polygonból**, hanem a sheetenkénti **occupied envelope** proxyból számolj.

Konzervatív definíció egy használt sheetre:

- `sheet_bbox` = a bin polygon AABB-ja
- `occupied_envelope` = az adott sheeten elhelyezett tételek AABB-uniójának külső burkoló téglalapja
- `right_strip_area` = az occupied envelope jobb oldalán maradó teljes magasságú sáv területe
- `top_strip_area` = az occupied envelope felett maradó, envelope-szélességű sáv területe
- `free_proxy_area` = `right_strip_area + top_strip_area`  
  (ez megegyezik a `sheet_bbox_area - occupied_envelope_area` értékkel ennél a proxy modellnél)

A három komponens legyen integer, ppm skálán (`0..=1_000_000`):

- `remnant_area_score_ppm`
  - `free_proxy_area / sheet_area`
- `remnant_compactness_score_ppm`
  - `max(right_strip_area, top_strip_area) / max(free_proxy_area, 1)`
  - vagyis jutalmazza, ha a maradék inkább **egyben marad**, és nem két vékony, szétesett sávra esik
- `remnant_min_width_score_ppm`
  - `max(right_strip_width, top_strip_height) / min(sheet_width, sheet_height)`
  - vagyis jutalmazza, ha a maradék legalább egy használható méretű dimenzióban nagy

Összesítés egy sheetre:

- `remnant_value_ppm = 500_000 * area + 300_000 * compactness + 200_000 * min_width` ppm-normalizálva, integer-only módon
- a teljes eredmény `remnant_value_ppm` értéke a használt sheetek score-jainak összege legyen

### Minimális invazivitás / szerkezeti irány

A jelenlegi kódstruktúrához igazodva:

- `rust/nesting_engine/src/placement/blf.rs`
  - egészítsd ki a `PlacedItem`-et annyi **belső** envelope-számításhoz szükséges adattal, amennyi kell
  - pl. a lerakott AABB szélesség / magasság mm-ben vagy scaled integerben
  - ezeket **nem kell** JSON exportba kirakni
- `rust/nesting_engine/src/multi_bin/greedy.rs`
  - itt legyen a remnant score számítás és a `MultiSheetResult` bővítése
- `rust/nesting_engine/src/search/sa.rs`
  - az SA cost / lexicographic objective kódját vezesd át úgy, hogy az új secondary objective-ot is figyelembe vegye
- `rust/nesting_engine/src/export/output_v2.rs`
  - az output `objective` blokk kapja meg a remnant mezőket

### JSON output contract bővítés

Az `objective` blokkban jelenjen meg legalább:

```json
"objective": {
  "sheets_used": 1,
  "utilization_pct": 87.5,
  "remnant_value_ppm": 742000,
  "remnant_area_score_ppm": 380000,
  "remnant_compactness_score_ppm": 900000,
  "remnant_min_width_score_ppm": 700000
}
```

A determinism hash contract **ne változzon** emiatt: a hash továbbra is a placement-höz kötött canonical view-ból épüljön.

### Kötelező tesztek

Adj hozzá **targeted `remnant_` prefixű Rust teszteket** legalább ezekre:

1. `remnant_score_prefers_more_compact_proxy_layout`
   - két azonos `sheets_used` eredmény közül a kompaktabb occupied envelope kapjon magasabb `remnant_value_ppm`-et
2. `remnant_score_is_integer_and_deterministic`
   - azonos input → bitazonos score mezők
3. `remnant_objective_is_exposed_in_output_v2`
   - az output JSON `objective` blokk tartalmazza az új mezőket
4. `sa_prefers_higher_remnant_value_when_sheets_tie`
   - ha azonos az unplaced és azonos a sheet count, az SA objective a magasabb remnant score-os layoutot tekintse jobbnak

### Report evidence

A reportban legyen:

- targeted `cargo test --manifest-path rust/nesting_engine/Cargo.toml remnant_`
- legalább 1 kis CLI futás egy meglévő fixture-rel (pl. `poc/nesting_engine/f2_4_sa_quality_fixture_v2.json` vagy más már bent lévő v2 input), ami bizonyítja, hogy az output `objective` blokkban megjelennek az új mezők
- a reportban külön mondd ki, hogy ez az F3-3 verzió **proxy remnant model**, nem exact polygon-remnant modell

## 🧪 Tesztállapot

### DoD
- [ ] `MultiSheetResult` kiterjesztve remnant objective mezőkkel
- [ ] Remnant score integer-only, determinisztikus, ppm skálán számol
- [ ] SA objective kiterjesztve: equal unplaced + equal sheets_used esetén remnant value dönt
- [ ] `objective` JSON blokk tartalmazza a remnant mezőket
- [ ] Targeted `remnant_` Rust tesztek PASS
- [ ] `scripts/check.sh` futtat targeted `remnant_` teszteket is
- [ ] `./scripts/verify.sh --report codex/reports/nesting_engine/remnant_value_model.md` PASS

## 🌍 Lokalizáció
Nem releváns.

## 📎 Kapcsolódások
- Backlog: `canvases/nesting_engine/nesting_engine_backlog.md`
- F3-2: `canvases/nesting_engine/part_in_part_pipeline.md`
- Architektúra: `docs/nesting_engine/architecture.md`
- IO contract: `docs/nesting_engine/io_contract_v2.md`
- Export: `rust/nesting_engine/src/export/output_v2.rs`
- Search: `rust/nesting_engine/src/search/sa.rs`
