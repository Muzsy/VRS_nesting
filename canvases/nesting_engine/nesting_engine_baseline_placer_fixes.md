# nesting_engine_baseline_placer_fixes

## 🎯 Funkció

A `nesting_engine_baseline_placer` task (canvas + YAML + runner) és a kapcsolódó backlog dokumentáció javítása úgy, hogy:

1) Kötelezően bekerüljön a `vrs_nesting/cli.py` CLI subcommand (pl. `nesttool nest-v2 <project.json>`).
2) Kötelezően bekerüljön a `scripts/check.sh` baseline smoke futás.
3) A “jagua/clipper2” terminológia és elvárások összhangban legyenek a valós kóddal: **offset + feasibility műveletek = i_overlay**, broad-phase = AABB (+ opcionális rstar).
4) A task leírása (canvas/YAML/run.md) legyen egységes, végrehajtható és repo-szabályos (YAML outputs ne legyen lyukas).
5) A baseline placer taskban szereplő parancs-snippet és API jelölések (pl. dupla pipe, can_place aláírás) legyenek konzisztensen javítva.

## 🧠 Fejlesztési részletek

### Kiinduló állapot / problémák
- A backlog (canvases/nesting_engine/nesting_engine_backlog.md) több helyen elavult: „Clipper2” és „jagua-rs” említések nem tükrözik a nesting_engine jelenlegi valóságát (i_overlay).
- A baseline placer task három fájlja (canvas/yaml/run.md) jelenleg nem tartalmazza kötelezően:
  - `vrs_nesting/cli.py` módosítását (CLI subcommand),
  - `scripts/check.sh` baseline smoke módosítását,
  ezért a backlog szerinti DoD nem teljesíthető.
- YAML-ben és/vagy dokumentumban előfordulhat félrevezető parancs (pl. dupla pipe), és a can_place API jelölése eltérhet.

### Cél állapot (kötelező)
1) **Backlog terminológia tiszta:**
   - minden nesting_engine ágon a „Clipper2” említés legyen lecserélve **i_overlay**-re, ahol offset/narrow-phase szerepel.
   - „jagua-rs” helyett a baseline placerben legyen „feasibility layer (i_overlay)”, és opcionálisan `rstar` broad-phase.
2) **Baseline placer task (3 fájl) összhang:**
   - A baseline_placer canvasban legyen egyértelmű: broad-phase = AABB (+ optional rstar), narrow-phase = i_overlay containment + no-overlap.
   - A baseline_placer YAML `outputs` listája tartalmazza a CLI és smoke érintett fájlokat:
     - `vrs_nesting/cli.py`
     - `scripts/check.sh`
   - A run.md utasításai tartalmazzák a CLI futtatást és a smoke-gate elvárást.
3) **Konszolidáció / konzisztencia fixek:**
   - Parancs-snippet hibák (pl. dupla pipe) javítva.
   - can_place API jelölés egységesítve (canvas és YAML ugyanazt mondja).

### Érintett fájlok (módosítás)
- Backlog:
  - `canvases/nesting_engine/nesting_engine_backlog.md`
- Baseline placer task:
  - `canvases/nesting_engine/nesting_engine_baseline_placer.md`
  - `codex/goals/canvases/nesting_engine/fill_canvas_nesting_engine_baseline_placer.yaml`
  - `codex/prompts/nesting_engine/nesting_engine_baseline_placer/run.md`

## 🧪 Tesztállapot

### DoD (Definition of Done)
- [ ] A backlogban a nesting_engine ágon a “Clipper2” említések i_overlay-re cserélve, és a “jagua-rs” baseline placer kontextusban feasibility layer (i_overlay) + optional rstar szövegre tisztítva.
- [ ] A baseline_placer canvas kimondja: broad-phase AABB (+ optional rstar), narrow-phase i_overlay containment + no-overlap, determinisztikus találat-sorrenddel.
- [ ] A baseline_placer YAML `outputs` listája tartalmazza: `vrs_nesting/cli.py` és `scripts/check.sh`.
- [ ] A baseline_placer run.md tartalmazza a CLI subcommand használatát és a scripts/check.sh baseline smoke elvárást.
- [ ] A baseline_placer YAML/run.md parancs-snippet hibák (pl. dupla pipe) javítva.
- [ ] A can_place API jelölés egységes (canvas ↔ YAML).

## 🌍 Lokalizáció

Nem releváns.

## 📎 Kapcsolódások

- `AGENTS.md` (outputs szabály + gate)
- `canvases/nesting_engine/nesting_engine_io_contract_v2.md` (i_overlay bevezetés rögzítve)
- `canvases/nesting_engine/nesting_engine_backlog.md` (drift javítandó)
- `canvases/nesting_engine/nesting_engine_baseline_placer.md` (task align)