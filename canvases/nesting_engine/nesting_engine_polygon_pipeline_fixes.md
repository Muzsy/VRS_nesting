# nesting_engine_polygon_pipeline_fixes

## 🎯 Funkció

A `nesting_engine_polygon_pipeline` feladat utólagos javítása és “bizonyíthatóvá” tétele a repo szabályai szerint.

Célok:
1) Javítsuk a polygon pipeline canvasban a hibás futtatási útvonalat (bináris path).
2) Tegyük explicit, automatikusan tesztelt (unit) módon bizonyíthatóvá a `SELF_INTERSECT` kezelést.
3) Szüntessük meg a félrevezető / felesleges warningot (pl. “never constructed” enum ág), hogy a gate tiszta legyen.
4) Futtassuk a repo minőségkaput (`./scripts/verify.sh --report ...`) és frissítsük a report/checklist artefaktokat.

## 🧠 Fejlesztési részletek

### Kontextus (miért kell)
- A `canvases/nesting_engine/nesting_engine_polygon_pipeline.md` jelenleg hibás bináris útvonalat mutat (nem a `rust/nesting_engine/target/...` alól).
- A pipeline-ban létezik `SELF_INTERSECT` post-check, de nincs rá célzott pipeline unit teszt (elfogadási kritérium szintjén ez hiány).
- A verify logban megjelent (korábban) olyan warning, ami arra utal, hogy van “SelfIntersection” jellegű ág/enum, ami sosem jön létre — ez félrevezető, tisztítandó.

### Várt viselkedés
1) **Canvas parancs**: a példákban a bináris helyesen legyen megadva (repo relatív útvonal).
2) **SELF_INTERSECT**:
   - Legyen egy unit teszt, ami determinisztikusan előállít egy önmetsző (pl. “bow-tie”) outer polygont.
   - A pipeline ezt “self_intersect” státusszal kezelje (ne crash), és adjon diagnosztikát.
3) **Warning tisztítás**:
   - Ha van olyan enum/ág, ami sosem konstruálódik, azt vagy tényleg konstruáljuk (ha értelmes), vagy távolítsuk el és igazítsuk a match/handling részt.
   - Minimal-invazív: ne változtassunk IO contractot, csak belső kezelést és tesztet.

### Érintett komponensek
- Canvas javítás:
  - `canvases/nesting_engine/nesting_engine_polygon_pipeline.md`
- Pipeline + tesztek:
  - `rust/nesting_engine/src/geometry/pipeline.rs`
- Warning tisztítás (ha releváns a kódbázisban):
  - `rust/nesting_engine/src/geometry/offset.rs` *(vagy ahol a “never constructed” ág van)*
- Codex artefaktok:
  - `codex/codex_checklist/nesting_engine/nesting_engine_polygon_pipeline_fixes.md`
  - `codex/reports/nesting_engine/nesting_engine_polygon_pipeline_fixes.md`
  - `codex/reports/nesting_engine/nesting_engine_polygon_pipeline_fixes.verify.log` *(autó)*

## 🧪 Tesztállapot

### DoD (Definition of Done)
- [ ] A polygon pipeline canvasban a futtatási példa **helyes bináris útvonalat** használ.
- [ ] Van új unit teszt `SELF_INTERSECT` esetre, és az determinisztikusan PASS/FAIL.
- [ ] A `SELF_INTERSECT` eset nem crashel, és diagnosztikát ad (státusz + detail).
- [ ] A korábbi “never constructed” jellegű warning megszűnik vagy indokoltan dokumentálva van.
- [ ] Repo gate lefut: `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_polygon_pipeline_fixes.md`
- [ ] Report + checklist kitöltve (PASS/FAIL evidenciával).

## 🌍 Lokalizáció

Nem releváns.

## 📎 Kapcsolódások

- `AGENTS.md` (Codex outputs szabály + verify kötelező)
- `docs/codex/yaml_schema.md` (YAML séma)
- `canvases/nesting_engine/nesting_engine_polygon_pipeline.md` (eredeti feladat)
- `codex/goals/canvases/nesting_engine/fill_canvas_nesting_engine_polygon_pipeline.yaml` (eredeti goal)
- `codex/prompts/nesting_engine/nesting_engine_polygon_pipeline/run.md` (eredeti futtatási prompt)