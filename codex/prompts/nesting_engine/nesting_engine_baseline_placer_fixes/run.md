# Run: nesting_engine_baseline_placer_fixes

Szerep: repo-szabálykövető Codex implementátor (dokumentáció + task-definíció javító).

## Kötelező szabályok
- Kezdd az `AGENTS.md` átolvasásával, és tartsd be az ottani “outputs” szabályt.
- Csak olyan fájlokat módosíts / hozz létre, amelyek a goal YAML `outputs:` listáiban szerepelnek.
- Ne inventálj új útvonalakat/fájlokat. Ha valami hiányzik, jelezd és állj meg.
- Ez a task NEM baseline placer implementáció. Csak backlog + baseline task definíció (canvas/yaml/run) javítás.

## Inputok
- Canvas: `canvases/nesting_engine/nesting_engine_baseline_placer_fixes.md`
- Goal: `codex/goals/canvases/nesting_engine/fill_canvas_nesting_engine_baseline_placer_fixes.yaml`

## Feladat
Hajtsd végre a goal YAML lépéseit sorrendben.

### 1) Szabályok + fájlok megnyitása
- Olvasd el `AGENTS.md`.
- Nyisd meg:
  - `canvases/nesting_engine/nesting_engine_backlog.md`
  - `canvases/nesting_engine/nesting_engine_baseline_placer.md`
  - `codex/goals/canvases/nesting_engine/fill_canvas_nesting_engine_baseline_placer.yaml`
  - `codex/prompts/nesting_engine/nesting_engine_baseline_placer/run.md`
  - `canvases/nesting_engine/nesting_engine_io_contract_v2.md` (terminológia ellenőrzéshez)

### 2) Backlog drift javítás (kötelező)
A `canvases/nesting_engine/nesting_engine_backlog.md` fájlban:
- cseréld a nesting_engine ágon a releváns “Clipper2” említéseket “i_overlay”-re,
- a baseline placer résznél a “jagua-rs” szöveget írd át erre a modellre:
  - broad-phase: AABB (+ optional rstar), determinisztikus találat-sorrend
  - narrow-phase: feasibility layer (i_overlay): containment + no-overlap
- Ne írj át struktúrát, csak a pontatlan terminológiát és a baseline placer bekezdés pontosságát.

### 3) Baseline placer canvas pontosítás (kötelező)
A `canvases/nesting_engine/nesting_engine_baseline_placer.md` fájlban:
- Feasibility részt állítsd át:
  - Broad-phase: AABB lista minimum, optional rstar R-tree, találatok id szerint rendezve.
  - Narrow-phase: i_overlay containment (candidate ⊆ bin) és no-overlap (candidate ∩ placed = ∅).
  - Rögzítsd: a placer inflated geometrián dönt (solver truth).
- Egységesítsd a can_place API jelölést a YAML-lel (ugyanazt a paraméterezést használják).

### 4) Baseline placer YAML javítás (kötelező)
A `codex/goals/canvases/nesting_engine/fill_canvas_nesting_engine_baseline_placer.yaml` fájlban:
- Add hozzá az outputs listákhoz (ahol releváns):
  - `vrs_nesting/cli.py` (CLI subcommand)
  - `scripts/check.sh` (baseline smoke)
- Javíts minden hibás parancs-snippetet:
  - NE legyen dupla pipe vagy redundáns `nest` hívás.
- Cseréld ki az elavult hivatkozásokat (Clipper2/jagua) az i_overlay feasibility modellre.
- Ellenőrizd, hogy a YAML lépései ténylegesen lefedik a backlogban elvártakat (CLI + smoke + i_overlay).

### 5) Baseline placer run.md javítás (kötelező)
A `codex/prompts/nesting_engine/nesting_engine_baseline_placer/run.md` fájlban:
- Tedd bele explicit, hogy a task része:
  - új CLI subcommand a `vrs_nesting/cli.py`-ben (pl. `nest-v2`)
  - `scripts/check.sh` baseline smoke bővítés
- Írd át a feasibility részt i_overlay modellre.
- Hagyd meg a standard verify/gate lépést a repo konvenciói szerint (ne találd ki máshogy).

### 6) Konzisztencia zárás
A végén ellenőrizd:
- backlog ↔ baseline placer canvas ↔ YAML ↔ run.md terminológia:
  - NINCS “Clipper2” nesting_engine ágon,
  - NINCS “jagua-rs” baseline placerben (helyette feasibility layer i_overlay),
  - CLI subcommand és scripts/check.sh smoke mindenhol szerepel és a YAML outputs engedi.

## Kimenet elvárás (a végén írd le röviden)
- Pontosan mely fájlok módosultak (csak az engedélyezettek).
- Mely “Clipper2/jagua” említések lettek lecserélve és hol.
- A YAML outputs-ban hol került be `vrs_nesting/cli.py` és `scripts/check.sh`.