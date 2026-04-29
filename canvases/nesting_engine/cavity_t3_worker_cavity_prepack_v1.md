# Cavity T3 - Pure worker cavity prepack modul v1

## Cel
Implementalj tiszta, DB/API mentes `worker/cavity_prepack.py` modult, amely
base `nesting_engine_v2` inputbol es snapshotbol deterministic
`cavity_plan_v1` sidecart es prepackelt engine inputot epit. Ez meg nem worker
runtime integracio.

## Nem-celok
- Nem worker process bekotes vagy artifact persist.
- Nem result normalizer expansion.
- Nem export/UI.
- Nem filename vagy part_code hardcode.
- Nem child holes prepack v1-ben.

## Repo-kontekstus
- `worker/engine_adapter_input.py` mar epit `nesting_engine_v2` inputot
  `outer_points_mm` es `holes_points_mm` mezokkel.
- `geometry_manifest_jsonb` canonical polygon payloadot hordoz, `hole_rings`
  adatokkal.
- `requirements-dev.txt` tartalmaz Shapely-t, de elobb ellenorizni kell, hogy a
  repo-ban hogyan hasznaljak.
- A v1 cel: lyukas parent virtual top-level part `holes_points_mm=[]` mellett,
  child quantity reservation es deterministic local placement.

## Erintett fajlok
- `worker/cavity_prepack.py`
- `tests/worker/test_cavity_prepack.py` vagy repo-kompatibilis teszt path.
- `scripts/smoke_cavity_t3_worker_cavity_prepack_v1.py`

## Implementacios lepesek
1. Implementald a public fuggvenyt:
   `build_cavity_prepacked_engine_input(snapshot_row, base_engine_input, enabled)`.
2. Hozz letre disabled plan utvonalat, amely byte-szeruen nem modositsa a base
   input szemantikajat.
3. Epits part es geometry indexet valos snapshot mezokbol.
4. Azonosits parent cavity jelolteket `holes_points_mm` alapjan.
5. Szurd a child jelolteket mennyiseg, self-parent kizart, holes unsupported v1
   es allowed rotations szerint.
6. Implementalj deterministic bbox + exact containment checket.
7. Generalj virtual parent instance partokat `quantity=1`, `holes_points_mm=[]`
   szaballyal.
8. Szamold `quantity_delta`, `instance_bases` es diagnostics mezoket.

## Checklist
- [ ] Disabled output kompatibilis a base inputtal.
- [ ] Minden virtual parent `quantity=1`.
- [ ] Top-level solver inputban prepackelt parenteknek nincs hole.
- [ ] Child top-level quantity csokken, nullanal eltunik.
- [ ] Child instance nem duplazodik.
- [ ] Determinisztikus sorrend es tie-breaker.
- [ ] Nincs OTSZOG/NEGYZET/MACSKANYELV hardcode.
- [ ] Repo gate reporttal lefutott.

## Tesztterv
- `python3 -m pytest -q tests/worker/test_cavity_prepack.py`
- `python3 scripts/smoke_cavity_t3_worker_cavity_prepack_v1.py`
- `./scripts/verify.sh --report codex/reports/nesting_engine/cavity_t3_worker_cavity_prepack_v1.md`

## Elfogadasi kriteriumok
- A modul nem hiv API-t, nem ir DB-t, nem ir fajlt.
- A `cavity_plan_v1` minden internal placementhez stabil parent/child/instance
  mappinget ad.
- Ha nincs hole vagy `enabled=false`, a regi run viselkedes valtozatlan.

## Rollback
Az uj modul es teszt/smoke izolaltan visszavonhato; worker runtime meg nem
hasznalja.

## Kockazatok
- Geometriai containment es origin-ref felreertese kesobb normalizer hibahoz
  vezethet.
- Shapely import kornyezeti problema eseten fallback/skip policyt reportolni kell.

## Vegso reportban kotelezo bizonyitek
- Unit teszt lista a quantity, virtual id es deterministic invariantokra.
- Path/line a public API-ra es a no-DB/no-API boundaryra.
