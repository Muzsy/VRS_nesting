# Run: nesting_engine_polygon_pipeline_fixes

Szerep: repo-szabálykövető Codex implementátor.

## Kötelező szabályok (nem opcionális)
- Kezdd az `AGENTS.md` átolvasásával és tartsd be az ott leírt “outputs” és minőségkapu szabályokat.
- Csak olyan fájlokat módosíts / hozz létre, amelyek a goal YAML `outputs:` listáiban szerepelnek.
- Ne találgass fájlneveket/útvonalakat: ha valami hiányzik, jelezd a reportban és állj meg.
- A végén kötelező lefuttatni:  
  `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_polygon_pipeline_fixes.md`

## Inputok
- Canvas: `canvases/nesting_engine/nesting_engine_polygon_pipeline_fixes.md`
- Goal: `codex/goals/canvases/nesting_engine/fill_canvas_nesting_engine_polygon_pipeline_fixes.yaml`

## Feladat
Hajtsd végre a goal YAML lépéseit sorrendben.

### 1) Felderítés
- Nyisd meg és vizsgáld át:
  - `canvases/nesting_engine/nesting_engine_polygon_pipeline.md` (bináris path példa)
  - `rust/nesting_engine/src/geometry/pipeline.rs` (SELF_INTERSECT kezelés + meglévő tesztek)
  - `rust/nesting_engine/src/geometry/offset.rs` (vagy a releváns warning forrása, ha itt van)
- Azonosítsd pontosan:
  1) hol hibás a bináris útvonal a canvasban,
  2) milyen SELF_INTERSECT kezelés van (post-check / early-check),
  3) mi okozza a “never constructed/dead_code” jellegű warningot.

### 2) Canvas javítás
- Javítsd a `canvases/nesting_engine/nesting_engine_polygon_pipeline.md` fájlban a futtatási példák bináris útvonalát repo-relatív módon.
- Csak a hibás path részt módosítsd, mást ne.

### 3) SELF_INTERSECT bizonyíthatóság (unit teszt)
- A `rust/nesting_engine/src/geometry/pipeline.rs` fájlban:
  - Adj hozzá egy új unit tesztet, ami determinisztikusan létrehoz egy önmetsző “bow-tie” outer polygont.
  - Elvárt: a pipeline self_intersect státusszal tér vissza, nem crashel, és a diagnosztikában legyen értelmes detail.
- Ha a jelenlegi logika csak inflate UTÁN ellenőriz, és a teszt instabil, akkor vezess be korai (nominális) self-intersect validációt úgy, hogy:
  - az IO contract ne változzon,
  - a státusz/diganosztika formátum maradjon kompatibilis.

### 4) Warning tisztítás
- A warning forrásától függően minimal-invazívan javíts:
  - ha van enum/ág, ami ténylegesen sosem konstruálódik → távolítsd el és igazítsd a kapcsolódó kódot,
  - vagy ha indokolt → tedd ténylegesen elérhetővé/konstruálttá.
- Cél: verify/build alatt a korábbi félrevezető warning megszűnjön.
- Ne nyúlj a publikus IO szerződéshez.

### 5) Checklist + report
- Hozd létre:
  - `codex/codex_checklist/nesting_engine/nesting_engine_polygon_pipeline_fixes.md`
  - `codex/reports/nesting_engine/nesting_engine_polygon_pipeline_fixes.md`
- A checklist legyen pipálható DoD lista (a fix canvas DoD pontjai alapján).
- A report legyen Report Standard v2 szerint:
  - DoD → Evidence (konkrét fájl + rövid leírás)
  - Advisory (ha van)
  - AUTO_VERIFY blokk előkészítve.

### 6) Minőségkapu futtatása (kötelező)
Futtasd:
```bash
./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_polygon_pipeline_fixes.md