# nesting_engine_baseline_placer_i_overlay_feasibility_fixes

## 🎯 Funkció

A `nesting_engine_baseline_placer` implementáció funkcionális korrekciója és drift-mentesítése:

1) A baseline placer feasibility (narrow-phase) legyen **i_overlay** alapú:
   - containment: candidate ⊆ bin
   - no-overlap: candidate ∩ placed = ∅
   Ez a kódot a már rögzített dokumentációhoz (i_overlay truth layer) igazítja.

2) A `scripts/check.sh` baseline smoke maradjon **bináris hívás** (nesting_engine nest),
   de egészítsük ki egy **második, rövid CLI-smoke**-kal, ami a `nest-v2` subcommandot is futtatja.

3) A dokumentációk legyenek szigorúan összhangban a valósággal:
   - feasibility: i_overlay
   - smoke: bináris + CLI-smoke
   - determinisztika: output canonicalizáció / hash.

## 🧠 Fejlesztési részletek

### Kiinduló állapot (probléma)
- A baseline placer task dokumentációja i_overlay feasibility-t ír, de a kódban jelenleg saját
  segment-intersect + point-in-poly narrow-phase van, nem i_overlay.
- `scripts/check.sh` jelenleg bináris smoke-ot futtat (jó), de a CLI subcommand (`nest-v2`) nincs gate-ben lefedve.
- Emiatt funkcionálisan:
  - a feasibility “truth layer” nincs egységesítve az i_overlay offset világával,
  - a CLI integráció regressziója könnyebben észrevétlen marad.

### Cél állapot (kötelező)
#### 1) i_overlay feasibility (narrow-phase)
A `can_place()`/feasibility ellenőrzés pipeline-ban:
- Broad-phase maradhat: AABB szűrés (opcionálisan rstar, determinisztikus sorrend).
- Narrow-phase kötelező: i_overlay-alapú műveletek:
  - Candidate bin-be containment: candidate ⊆ bin (policy szerinti toleranciával).
  - Candidate no-overlap: candidate ∩ placed = ∅
- A feasibility a solver “truth layer” geometrián fut (inflated), export ettől független.

#### 2) scripts/check.sh: bin smoke + CLI-smoke
- Marad: baseline bin smoke (nesting_engine nest).
- Új: CLI-smoke blokk:
  - futtatja a `vrs_nesting/cli.py` (vagy a repo szerinti CLI entrypoint) `nest-v2` parancsát
  - ugyanazzal a fixture-rel (vagy egy CLI-kompatibilis project fixture-rel)
  - ellenőrzi: exit code + determinisztikus hash (vagy stabil canonical JSON).

#### 3) Dokumentáció frissítés
A baseline placer canvas és backlog legyen pontos:
- feasibility: i_overlay
- smoke: bináris + CLI-smoke (gate-ben)
- rstar szerepe: optional broad-phase (determinista találat-sorrenddel).

### Érintett fájlok
- Kód (feasibility):
  - `rust/nesting_engine/src/feasibility/narrow.rs`
  - (ha kell) `rust/nesting_engine/src/feasibility/mod.rs`
  - (ha kell) `rust/nesting_engine/src/geometry/*` csak minimálisan, IO contract nem változhat
- Smoke:
  - `scripts/check.sh`
- Doksik (szigorú drift-fix):
  - `canvases/nesting_engine/nesting_engine_baseline_placer.md`
  - `canvases/nesting_engine/nesting_engine_backlog.md` (ha a smoke leírás/DoD érintett)

## 🧪 Tesztállapot

### DoD (Definition of Done)
- [ ] A feasibility narrow-phase ténylegesen i_overlay-t használ (containment + no-overlap).
- [ ] A korábbi saját segment/PIP narrow-phase nem marad “aktív” defaultként (legfeljebb fallbackként dokumentálva).
- [ ] `scripts/check.sh` baseline smoke továbbra is a binárist hívja, és PASS.
- [ ] `scripts/check.sh` tartalmaz egy új CLI-smoke blokkot `nest-v2` futtatásra, és PASS.
- [ ] A baseline placer doksik (baseline_placer + backlog) a valós smoke-ot írják le (bin + CLI-smoke),
      és a feasibility részt nem hagyják félreérthetőn.
- [ ] Repo gate lefut:
  `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_baseline_placer_i_overlay_feasibility_fixes.md`
- [ ] Report + checklist elkészül (Report Standard v2).

## 🌍 Lokalizáció

Nem releváns.

## 📎 Kapcsolódások

- `AGENTS.md` (outputs szabály + verify)
- `canvases/nesting_engine/nesting_engine_io_contract_v2.md` (i_overlay választás rögzítve)
- `canvases/nesting_engine/nesting_engine_baseline_placer.md`
- `scripts/check.sh`
- `vrs_nesting/cli.py` (nest-v2 entrypoint)