# codex/prompts/nesting_engine/nesting_engine_offset_py_rust_bridge/run.md

Szerep: **VRS_nesting task runner (canvas+YAML+verify fegyelmezett végrehajtás)**

Feladat:
A cél a Fázis 1 / F1-3 tényleges lezárása: a Python `vrs_nesting/geometry/offset.py` part inflációja alapértelmezetten a Rust kernel `inflate-parts` JSON stdin/stdout subcommandját használja, és a Shapely csak explicit fallback lehet.

Kötelező működési szabályok:
- Kövesd az `AGENTS.md` és a kapcsolódó codex szabálydoksik előírásait (yaml_schema, report/checklist standard).
- Ne találgass fájlokat/parancsokat: mindent a repóból igazolj.
- Csak a YAML step `outputs` listájában szereplő fájlokat hozhatod létre/módosíthatod.
- Minden változtatás után futtasd a verify gate-et; a végén kötelezően zöld legyen.

Inputok:
- Canvas: `canvases/nesting_engine/nesting_engine_offset_py_rust_bridge.md`
- Goal YAML: `codex/goals/canvases/nesting_engine/fill_canvas_nesting_engine_offset_py_rust_bridge.yaml`

Végrehajtás:
1) Olvasd be a fenti canvas + YAML tartalmát, és futtasd végig a step-eket sorrendben.
2) A Python-Rust bridge implementáció előtt azonosítsd a repóban, hogyan hívják a `nesting_engine` binárist:
   - keresd meg a smoke script-eket / runner-eket / dokumentációt, ami már hívja,
   - ne inventálj új útvonalat.
3) Implementáld a bridge-et `vrs_nesting/geometry/offset.py`-ben:
   - Rust default,
   - Shapely fallback csak explicit engedéllyel,
   - stabil hibakezelés,
   - SELF_INTERSECT → fail,
   - HOLE_COLLAPSED → ne crash.
4) Frissítsd a teszteket úgy, hogy a Rust útvonal meghívása unit szinten igazolható legyen (subprocess mock/monkeypatch).
5) Készítsd el a checklistet és a reportot.
6) Futtasd:
   `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_offset_py_rust_bridge.md`
   és mentsd a verify logot:
   `codex/reports/nesting_engine/nesting_engine_offset_py_rust_bridge.verify.log`

Kimenetek (kötelezően frissülnek/létrejönnek):
- `canvases/nesting_engine/nesting_engine_offset_py_rust_bridge.md`
- `vrs_nesting/geometry/offset.py`
- `tests/test_geometry_offset.py` (vagy a repóban talált megfelelő, de csak ha az outputs pontosan erre mutat)
- `codex/codex_checklist/nesting_engine/nesting_engine_offset_py_rust_bridge.md`
- `codex/reports/nesting_engine/nesting_engine_offset_py_rust_bridge.md`
- `codex/reports/nesting_engine/nesting_engine_offset_py_rust_bridge.verify.log`

Ha bármelyik stepnél ellentmondást találsz (pl. a Rust JSON contract más, mint amit a canvas első verziója állít), akkor először a canvas-t frissítsd a valósághoz, és csak utána implementálj.