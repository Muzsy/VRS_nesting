# VRS Nesting Codex Task — NFP Nesting Engine: F2-2 Konkáv NFP (stabil alap + orbitális exact) + boundary clean
TASK_SLUG: nfp_computation_concave

## 1) Kötelező olvasnivaló (prioritási sorrend)

Olvasd el és tartsd be, ebben a sorrendben:

1. `AGENTS.md`
2. `docs/codex/overview.md`
3. `docs/codex/yaml_schema.md`
4. `docs/codex/report_standard.md`
5. `docs/nesting_engine/tolerance_policy.md` — SCALE=1_000_000, touching policy
6. `rust/nesting_engine/src/geometry/types.rs` — Point64, i128 cross helper, CCW/convex
7. `rust/nesting_engine/src/nfp/cache.rs` — NfpCacheKey: (shape_id_a, shape_id_b, rotation_steps_b) rögzített
8. `rust/nesting_engine/src/nfp/convex.rs` — compute_convex_nfp() (F2-1 Minkowski)
9. `rust/nesting_engine/tests/nfp_regression.rs` — meglévő fixture runner
10. `canvases/nesting_engine/nesting_engine_backlog.md` — F2-2 DoD + kockázat
11. `canvases/nesting_engine/nfp_computation_concave.md` — task specifikáció
12. `codex/goals/canvases/nesting_engine/fill_canvas_nfp_computation_concave.yaml` — végrehajtási lépések

Ha bármelyik fájl nem létezik: állj meg, és írd le pontosan mit kerestél és hol.

---

## 2) Cél

F2-2 konkáv NFP implementálása úgy, hogy:

- Default útvonal **golyóálló és determinisztikus**:
  konkáv → konvex dekompozíció → konvex Minkowski (F2-1) → i_overlay union → boundary_clean
- Opcionális orbitális “exact” réteg:
  SVGNest/Deepnest mintázatú állapotgép (nem kódport), Burke 2007 + Luo&Rao 2022 (touching group)
  döntési logikával, loop guarddal, és automatikus fallbackkal.
- Kimenet **mindig** boundary_clean után tér vissza (vagy hiba).
- f64 alapú point-in-polygon használata tilos a core döntésekben.
- i128 kötelező minden orientáció/cross alapú döntéshez.

---

## 3) Nem cél

- IFP/CFR és NFP placer (F2-3)
- SA/GA kereső (F2-4)
- `rust/vrs_solver/**` bármilyen módosítása
- scripts wrapper módosítása

---

## 4) Kritikus implementációs megszorítások (nem alkuképes)

### 4.1 — Minkowski+dekompozíció a stabil alap (default)

A feladat nem állhat meg az orbitális algoritmus instabilitása miatt.
A stabil alap útvonalat előbb implementáld és zöldítsd a fixture-ökkel.
Az orbitális exact csak “fölötte” jön, és dead-end/loop esetén visszavált.

### 4.2 — Touching group kötelező

Többszörös érintkezés (3–4 kontakt) esetén touching group nélkül a döntés
nem determinisztikus és könnyen loopol. A concave exact rétegben
touching group képzést kötelező megvalósítani.

### 4.3 — i128 cross product (overflow védelem)

SCALE=1_000_000 mellett i64 szorzás overflow-zhat. Minden turn/orientation,
kollinearitás és rendezési döntés i128-on.

### 4.4 — boundary_clean kötelező

A kimeneti NFP boundary:
- nincs önmetszés,
- nincs degenerált él/csúcs,
- canonical ring (fix irány + fix start).

Ha nem javítható: hiba (NotSimpleOutput).

### 4.5 — f64 PIP kerülendő

Ne húzz be f64-alapú PIP-t (pl. geo crate), mert visszahozza az epsilon problémát.
Ha PIP kell: integer winding/ray casting saját segédfüggvénnyel Point64-on.

---

## 5) DoD (backlog szerint)

- [ ] Legalább 5 kézzel összeállított konkáv tesztpár PASS (touching, slits, lyukak)
- [ ] NFP boundary mindig valid polygon (nincs önmetszés a kimenetben)
- [ ] Valós DXF készlet legalább 3 alakzat-párjára helyes NFP generálódik (a felderítésben rögzítve)
- [ ] Regressziós tesztkészlet: `poc/nfp_regression/` alatt
- [ ] `./scripts/verify.sh --report codex/reports/nesting_engine/nfp_computation_concave.md` PASS

---

## 6) Végrehajtás

Hajtsd végre a YAML `steps` lépéseit sorrendben.

Szabályok:
- Csak olyan fájlt hozhatsz létre / módosíthatsz, ami szerepel valamely step `outputs` listájában.
- A minőségkaput kizárólag wrapperrel futtasd:
  `./scripts/verify.sh --report codex/reports/nesting_engine/nfp_computation_concave.md`

A végén add meg a létrehozott/módosított fájlok teljes tartalmát, fájlonként külön blokkokban.