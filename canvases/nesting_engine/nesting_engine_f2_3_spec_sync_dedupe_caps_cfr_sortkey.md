# canvases/nesting_engine/nesting_engine_f2_3_spec_sync_dedupe_caps_cfr_sortkey.md

> **Mentés helye a repóban:** `canvases/nesting_engine/nesting_engine_f2_3_spec_sync_dedupe_caps_cfr_sortkey.md`
> **TASK_SLUG:** `nesting_engine_f2_3_spec_sync_dedupe_caps_cfr_sortkey`
> **Terület (AREA):** `nesting_engine`

---

# F2-3 spec sync: candidate dedupe + cap semantics + CFR sort-key (ring_hash tie-break)

## 🎯 Funkció

A `docs/nesting_engine/f2_3_nfp_placer_spec.md` normatív specifikáció frissítése úgy, hogy **1:1-ben egyezzen**
a jelenlegi F2-3 NFP placer implementációval az alábbi pontokon:

1) **Candidate dedupe kulcs**
- Spec jelenleg: `HashSet` dedupe csak `(tx,ty)` alapján (12.3).
- Kód jelenleg: determinisztikus dedupe **(tx, ty, rotation_idx)** alapján, seed-mentes rendezett halmazzal.
  - Kód referencia: `rust/nesting_engine/src/placement/nfp_placer.rs::sort_and_dedupe_candidates` (BTreeSet insert kulcs)

2) **Candidate cap semantics**
- Spec jelenleg: `MAX_CANDIDATES_PER_PART_PER_ROT = 4096` (12.4).
- Kód jelenleg: `MAX_CANDIDATES_PER_PART = 4096` **partonként összesen (összes rotáció együtt)**.
  - Kód referencia: `rust/nesting_engine/src/placement/nfp_placer.rs::MAX_CANDIDATES_PER_PART`

3) **CFR komponens-rendezés totális kulcsa**
- Spec jelenleg: kulcs = `(min_point, abs(area), vertex_count)` (10.3) – ez nem totális (egyezésnél döntetlen).
- Kód jelenleg: totális kulcs = `(min_point, abs_area, vertex_count, ring_hash)` (ring_hash tie-break).
  - Kód referencia: `rust/nesting_engine/src/nfp/cfr.rs::{build_sort_key, compare_sort_keys, ring_hash_u64}`

Cél: a spec ne sugalljon olyan implementációt, ami ellentmond a determinisztika-hardening P0 fixeknek.

## Nem cél
- Kódváltoztatás a placerben / CFR-ben (itt **csak spec sync**).
- Új algoritmus, új cap értékek, új tie-break bevezetése.
- IO contract módosítás.

---

## 🧠 Fejlesztési részletek

### Mi a drift (konkrétan)
A spec jelenleg az alábbi fejezetekben tér el a valós implementációtól:

- **10.3 Determinisztikus komponens-sorrend**
  - Spec: 3 elemű kulcs → nem totális.
  - Kód: 4 elemű kulcs `ring_hash` tie-breakkel → totális.

- **12.3 Candidate halmazképzés**
  - Spec: dedupe `(tx,ty)` HashSet-ben.
  - Kód: dedupe `(tx,ty,rotation_idx)` rendezett halmazban, hogy azonos pozícióban több rotáció **megmaradhasson**.

- **12.4 Cap / limit**
  - Spec: 4096 / rotáció.
  - Kód: 4096 / part instance összesen (rotációk együtt), a dedupe után, determinisztikus “first N” policy-val.

### Kötelező spec módosítások

#### 1) 10.3: CFR komponens-sorrend totális kulcsa
Frissítsd a 10.3-at erre:

Rendezési kulcs (totális):
1. `min_point (x,y)` lexicographic
2. `abs(area)`
3. `vertex_count`
4. `ring_hash` (tie-break, seed-mentes, kanonizált ringekből)

Plusz rövid megjegyzés:
- a `ring_hash` kizárólag tie-break (nem célfüggvény), és a kódban komponensenként egyszer kerül kiszámításra (decorated sort pattern).

#### 2) 12.3: Dedupe policy pontosítása
Frissítsd a 12.3-at:

- A jelöltek rendezése (11.3 tie-break szerint) után történik a dedupe.
- Dedupe kulcs: `(tx, ty, rotation_idx)` (vagy ezzel ekvivalens “rotation context index”).
- Dedupe adatszerkezet: seed-mentes, determinisztikus (rendezett halmaz / BTreeSet jelleg).

Indok (1–2 mondat):
- azonos `(tx,ty)` mellett több rotáció jelöltet **nem** dobunk el.

#### 3) 12.4: Cap / limit átnevezése és semantics
Frissítsd a 12.4-et:

- `MAX_CANDIDATES_PER_PART = 4096` (összes rotáció együtt, part instance szinten)
- `MAX_VERTICES_PER_COMPONENT = 512` (marad)
- Cap alkalmazás: a dedupe után, a determinisztikusan rendezett jelöltekből az első N.

### Érintett fájlok
- `docs/nesting_engine/f2_3_nfp_placer_spec.md`
- Kód referenciák (csak hivatkozás, nem módosítjuk ebben a taskban):
  - `rust/nesting_engine/src/placement/nfp_placer.rs`
  - `rust/nesting_engine/src/nfp/cfr.rs`

---

## 🧪 Tesztállapot

### DoD
- [ ] `docs/nesting_engine/f2_3_nfp_placer_spec.md` 10.3 frissítve: totális komponens-sorrend `ring_hash` tie-breakkel
- [ ] `docs/nesting_engine/f2_3_nfp_placer_spec.md` 12.3 frissítve: dedupe kulcs `(tx,ty,rotation_idx)` + determinisztikus set policy
- [ ] `docs/nesting_engine/f2_3_nfp_placer_spec.md` 12.4 frissítve: `MAX_CANDIDATES_PER_PART = 4096` (part-szint, rotációk együtt) + cap alkalmazás sorrendje
- [ ] Gate PASS:
  `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_f2_3_spec_sync_dedupe_caps_cfr_sortkey.md`

---

## 🌍 Lokalizáció
Nem releváns.

## 📎 Kapcsolódások
- `docs/nesting_engine/f2_3_nfp_placer_spec.md`
- `rust/nesting_engine/src/placement/nfp_placer.rs::sort_and_dedupe_candidates` + `MAX_CANDIDATES_PER_PART`
- `rust/nesting_engine/src/nfp/cfr.rs::{build_sort_key, compare_sort_keys, ring_hash_u64}`
- `AGENTS.md`, `docs/codex/yaml_schema.md`, `docs/codex/report_standard.md`
