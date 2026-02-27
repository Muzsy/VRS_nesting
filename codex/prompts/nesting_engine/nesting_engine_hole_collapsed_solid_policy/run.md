# Run: nesting_engine_hole_collapsed_solid_policy

Szerep: repo-szabálykövető Codex implementátor.

## Kötelező szabályok (nem opcionális)
- Kezdd az `AGENTS.md` átolvasásával és tartsd be az ott leírt “outputs” és minőségkapu szabályokat.
- Csak olyan fájlokat módosíts / hozz létre, amelyek a goal YAML `outputs:` listáiban szerepelnek.
- Ne találgass fájlneveket/útvonalakat: ha valami hiányzik, jelezd a reportban és állj meg.
- A végén kötelező lefuttatni:
  `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_hole_collapsed_solid_policy.md`

## Inputok
- Canvas: `canvases/nesting_engine/nesting_engine_hole_collapsed_solid_policy.md`
- Goal: `codex/goals/canvases/nesting_engine/fill_canvas_nesting_engine_hole_collapsed_solid_policy.yaml`

## Feladat
Hajtsd végre a goal YAML lépéseit sorrendben.

### Fókusz / policy (ne térj el)
A HOLE_COLLAPSED célja:
- export/gyártási geometria: nominális holes megmarad (pipeline diagnosztika: preserve_for_export=true)
- nesting: holes soha nem léteznek (inflated_holes_points_mm mindig üres), így nincs cavity/part-in-part
- elhelyezhetőség: outer-only nesting-envelope továbbra is működjön (inflated_outer_points_mm nem üres)

### Ellenőrzések a végén (reportban is tüntesd fel)
- Új unit teszt lefedi a “detect path” HOLE_COLLAPSED esetet.
- main.rs defense-in-depth: hole_collapsed esetén holes=[] kerül a placerbe.
- docs/nesting_engine/tolerance_policy.md szinkronban van a valós policy-vel.
- Gate: `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_hole_collapsed_solid_policy.md`