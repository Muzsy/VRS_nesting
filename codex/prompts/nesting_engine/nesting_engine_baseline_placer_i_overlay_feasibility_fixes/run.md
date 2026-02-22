# Run: nesting_engine_baseline_placer_i_overlay_feasibility_fixes

Szerep: repo-szabálykövető Codex implementátor.

## Kötelező szabályok
- Kezdd az `AGENTS.md` átolvasásával.
- Csak olyan fájlokhoz nyúlj, amelyek a goal YAML `outputs:` listáiban szerepelnek.
- IO contractot nem törhetsz: a v2 JSON szerződés és a pipeline input/output formátum marad kompatibilis.
- A végén kötelező a verify:
  ./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_baseline_placer_i_overlay_feasibility_fixes.md

## Inputok
- Canvas: canvases/nesting_engine/nesting_engine_baseline_placer_i_overlay_feasibility_fixes.md
- Goal: codex/goals/canvases/nesting_engine/fill_canvas_nesting_engine_baseline_placer_i_overlay_feasibility_fixes.yaml

## Feladat
Hajtsd végre a goal YAML lépéseit sorrendben.

### 1) Felderítés
- Nyisd meg:
  - rust/nesting_engine/src/feasibility/narrow.rs
  - scripts/check.sh
  - vrs_nesting/cli.py (nest-v2)
  - canvases/nesting_engine/nesting_engine_baseline_placer.md
  - canvases/nesting_engine/nesting_engine_backlog.md
- Pontosítsd:
  - hogyan skáláztok mm → integer koordináta i_overlay-hez (ha már van konvenció, azt kövesd),
  - a CLI-smoke-hoz milyen fixture/project input a legstabilabb (repo-ban meglévő).

### 2) i_overlay feasibility implementáció
- Cseréld le a custom narrow-phase-t i_overlay containment + no-overlap checks-re.
- Követelmények:
  - determinisztikus ellenőrzési sorrend
  - ugyanaz a policy (margin/kerf/tolerance)
  - no crash edge-case-eknél; hibák esetén diagnosztika legyen a meglévő minták szerint.

### 3) scripts/check.sh: CLI-smoke hozzáadása
- Tartsd meg a meglévő baseline bin smoke-ot.
- Adj hozzá egy új CLI-smoke blokkot:
  - hívja a nest-v2 parancsot
  - ellenőrzi az eredményt (exit code + determinisztika)
- A CLI-smoke legyen gyors és stabil.

### 4) Doksik igazítása
- baseline_placer.md: feasibility = i_overlay; smoke = bin + CLI-smoke
- backlog.md: ahol a baseline smoke/DoD leírás van, frissítsd a valós gate-re.

### 5) Checklist + report
- Hozd létre:
  - codex/codex_checklist/nesting_engine/nesting_engine_baseline_placer_i_overlay_feasibility_fixes.md
  - codex/reports/nesting_engine/nesting_engine_baseline_placer_i_overlay_feasibility_fixes.md
- Report Standard v2 szerint, AUTO_VERIFY blokkal.

### 6) Verify futtatás (kötelező)
Futtasd:
```bash
./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_baseline_placer_i_overlay_feasibility_fixes.md