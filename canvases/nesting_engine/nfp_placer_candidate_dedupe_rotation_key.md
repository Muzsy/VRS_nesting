# canvases/nesting_engine/nfp_placer_candidate_dedupe_rotation_key.md

> **Mentés helye a repóban:** `canvases/nesting_engine/nfp_placer_candidate_dedupe_rotation_key.md`
> **TASK_SLUG:** `nfp_placer_candidate_dedupe_rotation_key`
> **Terület (AREA):** `nesting_engine`

---

# P0 — NFP placer candidate dedupe legyen rotáció-érzékeny

## 🎯 Funkció

Javítsuk a `nfp_based_placement_engine` NFP placerében a candidate dedupe kulcsot.

**Probléma:**
Jelenleg a jelöltek dedupe-ja csak `(tx, ty)` alapján történik, ami hibás: azonos `(tx,ty)` koordinátán különböző rotációk
különböző geometriát jelentenek, és eltérhet a `can_place()` eredmény. Emiatt előfordulhat, hogy:
- a rossz rotációjú jelölt “elsőként” kerül be,
- a jó rotációjú, ugyanazon `(tx,ty)` jelöltet a dedupe eldobja,
- így a part tévesen “nem fér fel”.

**Elvárt viselkedés:**
- A dedupe kulcs legyen minimum: `(tx, ty, rotation)` (pl. rotation_deg vagy rotation_idx).
- A totális rendezés + first-feasible logika változatlan.

## 🧠 Fejlesztési részletek

### Érintett fájl
- `rust/nesting_engine/src/placement/nfp_placer.rs`

### Felderítés (aktuális állapot)
- A dedupe jelenleg csak `(tx, ty)` kulcsot használ:
  - `seen.insert((candidate.tx, candidate.ty))`
  - helye: `rust/nesting_engine/src/placement/nfp_placer.rs`

### Implementációs elv
- Vezess be egy determinisztikus `CandidateKey`-t vagy dedupe kulcs függvényt:
  - régi: `(tx, ty)`
  - új: `(tx, ty, rot_deg)` **vagy** `(tx, ty, rot_idx)`
- A sort/tie-break logika maradjon a spec szerint (nem nyúlunk hozzá).
- A dedupe után max-cap (4096) maradhat.

### Kötelező regressziós teszt
A `nfp_placer.rs` unit teszt moduljában adj hozzá olyan tesztet, ami:
- kézzel felépít egy candidate listát,
- tartalmaz két jelöltet ugyanazzal `(tx,ty)`-vel, de különböző rotációval,
- lefuttatja ugyanazt a “sort + dedupe” logikát,
- és asserteli, hogy **mindkettő megmarad** a dedupe után.

**Megjegyzés:** ez a teszt a korábbi kóddal determinisztikusan FAIL lenne (mert az egyik jelölt kiesik).

## 🧪 Tesztállapot

### DoD
- [ ] `nfp_placer.rs` dedupe kulcs: `(tx,ty,rotation)`
- [ ] Új unit teszt lefedi a “same (tx,ty), different rotation” esetet és PASS
- [ ] Gate PASS:
  `./scripts/verify.sh --report codex/reports/nesting_engine/nfp_placer_candidate_dedupe_rotation_key.md`

## 🌍 Lokalizáció
Nem releváns.

## 📎 Kapcsolódások
- `canvases/nesting_engine/nfp_based_placement_engine.md`
- `docs/nesting_engine/f2_3_nfp_placer_spec.md` (candidate selection + determinisztika)
- `rust/nesting_engine/src/placement/nfp_placer.rs`
- `AGENTS.md`, `docs/codex/yaml_schema.md`, `docs/codex/report_standard.md`
