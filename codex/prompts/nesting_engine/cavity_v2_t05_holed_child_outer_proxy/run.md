# Cavity v2 T05 — Lyukas child támogatása outer-only proxyval
TASK_SLUG: cavity_v2_t05_holed_child_outer_proxy

## Szerep
Senior Python coding agent vagy. Egy kemény kizárást távolítasz el, és egy informatív diagnosztikát vezetsz be.

## Cél
A `_candidate_children()` függvényből eltávolítod a `child_has_holes_unsupported_v1` melletti `continue`-t. A lyukas child outer proxy fittel részt vehet cavity elhelyezésben.

## Olvasd el először
- `AGENTS.md`
- `canvases/nesting_engine/cavity_v2_t05_holed_child_outer_proxy.md`
- `codex/goals/canvases/nesting_engine/fill_canvas_cavity_v2_t05_holed_child_outer_proxy.yaml`
- `worker/cavity_prepack.py` (TELJES fájl — különösen _candidate_children ~sor 235-265 és _rotation_shapes ~sor 223-232)
- `tests/worker/test_cavity_prepack.py`

## Engedélyezett módosítás
- `worker/cavity_prepack.py`
- `tests/worker/test_cavity_prepack.py`

## Szigorú tiltások
- **Tilos a lyukas child `holes_points_mm` adatát módosítani a `_PartRecord`-ban.**
- Tilos a `_rotation_shapes()` logikáját módosítani — az már outer-only proxy.
- Tilos a solid child behavior-t megváltoztatni.
- Tilos v2 entry point-ot implementálni (az T06).
- Tilos a `build_cavity_prepacked_engine_input()` v1 main flow-ját érdemben módosítani.

## Végrehajtandó lépések (YAML steps sorrendben)

### Step 1: Kontextus olvasás
Olvasd el a `_candidate_children()` függvényt. Azonosítsd pontosan, hol van a `continue` utasítás.

### Step 2: _candidate_children() módosítása
Az érintett blokk (pontos sorok keresése):
```bash
grep -n "child_has_holes_unsupported_v1" worker/cavity_prepack.py
```
A `continue` törlése, diagnostic kód cseréje `child_has_holes_outer_proxy_used`-ra (hole_count mezővel).

A `_rotation_shapes()` megjegyzés frissítése (sor 224 körül):
```python
# outer-only proxy: holes excluded from fit geometry; exact holes preserved in part record for export.
```

### Step 3: Új tesztek
Három teszt a canvas spec szerint. A `_rect()` és `_snapshot_for_parts()` helperek a meglévő tesztfájlból másolhatók.

```bash
python3 -m pytest -q tests/worker/test_cavity_prepack.py
```
Minden meglévő tesztnek zöldnek kell maradnia.

### Step 4: Checklist és report
### Step 5: Repo gate
```bash
./scripts/verify.sh --report codex/reports/nesting_engine/cavity_v2_t05_holed_child_outer_proxy.md
```

## Tesztelési parancsok
```bash
python3 -m pytest -q tests/worker/test_cavity_prepack.py
python3 -m pytest -q tests/worker/test_cavity_prepack.py -k "holed_child"
```

## Ellenőrzési pontok
- [ ] `continue` eltávolítva a `_candidate_children()`-ből lyukas child esetén
- [ ] `child_has_holes_outer_proxy_used` kód emittálódik
- [ ] Lyukas child bekerülhet `internal_placements`-be (ha geometriailag fér)
- [ ] A `_PartRecord.holes_points_mm` megmarad (nem törölve)
- [ ] Meglévő solid child tesztek mind zöldek
- [ ] `_rotation_shapes()` megjegyzés frissítve

## Elvárt végső jelentés
Magyar nyelvű report. DoD→Evidence mátrix. `child_has_holes_unsupported_v1` kód eltűnésének és `child_has_holes_outer_proxy_used` megjelenésének fájl:sor bizonyítéka.

## Hiba esetén
Ha lyukas child mégsem fér be a tesztben geometriailag (pl. cavity túl kicsi), ellenőrizd a teszt fixture méreteit. A cavity területe legalább 4x nagyobb legyen a child outer területénél.
