# canvases/nesting_engine/nesting_engine_spacing_margin_bin_offset_model.md

> **Mentés helye a repóban:** `canvases/nesting_engine/nesting_engine_spacing_margin_bin_offset_model.md`
> **TASK_SLUG:** `nesting_engine_spacing_margin_bin_offset_model`
> **Terület (AREA):** `nesting_engine`

---

# Spacing + margin + kerf kánon frissítés (bin_offset = spacing/2 - margin)

## 🎯 Funkció

A clearance modell véglegesítése és kódban érvényesítése a frissített döntéscsomag szerint:

**Mérvadó definíciók:**
- `spacing_mm` = min távolság **part–part** (nem part–edge)
- `margin_mm` = min távolság **part–bin edge**
- `kerf_mm` = gyártási (pre-baked) geóra ráégetve a projekt elején; **F2-3 matekban nincs**

**F2-3 kánon képletek:**
- `inflate_delta_mm = spacing_mm / 2`
- `bin_offset_mm = (spacing_mm / 2) - margin_mm`

Értelmezés:
- `margin > spacing/2` -> `bin_offset < 0` -> bin deflate (befelé)
- `margin = spacing/2` -> `bin_offset = 0`
- `margin < spacing/2` -> `bin_offset > 0` -> bin inflate (kifelé)

**Cél:** egy-envelope modellben a placer a **felfújt** (inflate_delta) partot rakja a **módosított** binbe (bin_offset),
és ettől teljesül egyszerre:
- part–part ≈ spacing
- part–bin edge ≈ margin
akkor is, ha `margin < spacing/2` (ez kötelező új eset).

## Nem cél (explicit)
- NFP placer / F2-3 placement engine implementálása (külön task).
- Determinizmus hash / canonicalization szabályok módosítása.
- `scripts/validate_nesting_solution.py` spacing-ellenőrzéssé bővítése (külön task lenne).

---

## 🧠 Fejlesztési részletek

### Kontextus: miért kell
Jelenleg több helyen a régi modell él:
- `docs/dxf_nesting_app_4_spacing_margin_implementacio_offsettel_reszletes.md`:
  bin inset = `margin + spacing/2` (régi)
- `vrs_nesting/geometry/offset.py` (Shapely stock fallback):
  `clearance = margin + spacing/2` és mindig deflate
- `rust/nesting_engine/src/geometry/pipeline.rs`:
  `delta_mm = margin_mm + kerf_mm*0.5` (régi, összemossa a fogalmakat)
- `rust/nesting_engine/src/main.rs` (v2 nest):
  bin csak margin-insettel készül, spacing nincs a contractban

Ez nem támogatja a friss kánont, különösen a `margin < spacing/2` esetet.

### Kötelező viselkedés (kód-szintű invariánsok)

#### A) pipeline_v1 (Rust: inflate-parts)
A `PipelineRequest` kapjon **opcionális** `spacing_mm` mezőt.

Szabály:
- ha `spacing_mm` meg van adva -> azt használjuk
- ha nincs -> legacy: `spacing_mm := kerf_mm` (nem kerf-kompenzáció, csak spacing forrás)

Számítás:
- `inflate_delta_mm = spacing_mm/2` (parts)
- `bin_offset_mm = spacing_mm/2 - margin_mm` (stocks outer)

**Partok:**
- part inflate kizárólag `inflate_delta_mm` alapján történik (margin nem vehet részt).

**Stockok (irregular bins / usable area):**
- outer offset: `bin_offset_mm` (negatív -> deflate, pozitív -> inflate)
- hole/defect akadály: **inflate_delta_mm** alapján tágítjuk (margin ne keveredjen bele)
- cél: usable = offset(outer, bin_offset) minus expanded(defects, inflate_delta)

Megjegyzés: a jelenlegi `inflate_outer()` egyszerre offseteli outer+holes azonos deltával, ezért stocknál szét kell választani:
- outer-only offset `bin_offset_mm`-mel
- hole-k külön “akadályként” offsetelve `inflate_delta_mm`-mel

#### B) nesting_engine_v2 (Rust: nest)
A v2 input `sheet` kapjon **opcionális** `spacing_mm` mezőt, és vezessük be az “effective spacing” logikát:

- `spacing_effective_mm = sheet.spacing_mm if present else sheet.kerf_mm` (legacy)

A `nest` útvonal:
- part inflate: `inflate_delta_mm = spacing_effective/2`
  - a pipeline requestben spacing_mm-t explicit add át (ha van), különben hagyd legacy-n
- bin: a rect bin a `bin_offset_mm = spacing_effective/2 - margin_mm` alapján készüljön:
  - `min_x = 0.0 - bin_offset_mm`
  - `max_x = width_mm + bin_offset_mm`
  - ugyanígy Y
  - clamp: ha túl nagy negatív offset miatt invertálódna, legyen determinisztikus minimum (max>=min)

#### C) Python offset (vrs_nesting/geometry/offset.py)
- A “kerf=spacing hack” maradhat, de legyen egyértelmű: nem kerf-kompenzáció, csak legacy spacing forrás.
- A Rust requestekbe (pipeline_v1) ha van `spacing_mm`, add át explicit mezőként is.
- A Shapely stock fallback modell:
  - `bin_offset = spacing/2 - margin` outerre (lehet pozitív is)
  - defects/hole akadály tágítás: `inflate_delta = spacing/2` (margin nélkül)
  - usable = outer_offset(bin_offset) minus expanded_holes(inflate_delta)

### Érintett valós fájlok
- Rust:
  - `rust/nesting_engine/src/io/pipeline_io.rs`
  - `rust/nesting_engine/src/geometry/pipeline.rs`
  - `rust/nesting_engine/src/main.rs`
- Python:
  - `vrs_nesting/geometry/offset.py`
  - `tests/test_geometry_offset.py`
- Doksik / POC:
  - `docs/dxf_nesting_app_4_spacing_margin_implementacio_offsettel_reszletes.md`
  - `docs/nesting_engine/io_contract_v2.md`
  - `poc/nesting_engine/sample_input_v2.json`
  - (opcionális, de ajánlott konzisztenciához) `poc/nesting_engine/pipeline_smoke_input.json`, `poc/nesting_engine/pipeline_smoke_expected.json`

---

## 🧪 Tesztállapot

### DoD (kötelező)
- [ ] `pipeline_v1` támogatja `spacing_mm` mezőt (optional), legacy fallback: spacing=kerf ha spacing hiányzik.
- [ ] Part inflate a pipeline-ban kizárólag `inflate_delta=spacing/2` alapján megy (margin nem keveredik bele).
- [ ] Stock usable outer offset: `bin_offset=spacing/2 - margin` (pozitív eset: outer nő).
- [ ] Stock defects/hole akadály: `inflate_delta=spacing/2` alapján tágul (margin nélkül).
- [ ] `nesting_engine_v2` input: `sheet.spacing_mm` optional, effective spacing fallback `kerf_mm`-ből.
- [ ] `nest` rect-bin számítás `bin_offset` alapján történik, és van explicit unit teszt a `margin < spacing/2` esetre.
- [ ] Python shapely stock fallback `bin_offset`-ot támogatja (pozitív esetet is), és a tesztek frissülnek.
- [ ] Doksi szinkron:
  - `docs/dxf_nesting_app_4_...` képletek frissítve az új kánonra
  - `docs/nesting_engine/io_contract_v2.md` frissítve (új `spacing_mm` mezők + normatív offset szabályok)
- [ ] Repo gate: `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_spacing_margin_bin_offset_model.md` PASS

### Kockázat + mitigáció + rollback
- Kockázat: `bin_offset > 0` (inflate) irregular stocknál self-intersect / artefaktok.
  - Mitigáció: cleanup / largest component policy maradjon determinisztikus; self-intersect továbbra is reject.
- Kockázat: contract bővítés (`spacing_mm`) több helyen érint.
  - Rollback: `PipelineRequest.spacing_mm` és `NestSheet.spacing_mm` eltávolítása + régi `delta=margin+kerf/2` visszaállítása (külön commitben).

---

## 🌍 Lokalizáció
Nincs UI lokalizáció.

## 📎 Kapcsolódások
- `AGENTS.md`
- `docs/codex/overview.md`, `docs/codex/yaml_schema.md`, `docs/codex/report_standard.md`
- `docs/dxf_nesting_app_4_spacing_margin_implementacio_offsettel_reszletes.md`
- `docs/nesting_engine/io_contract_v2.md`
- `rust/nesting_engine/src/geometry/pipeline.rs`
- `rust/nesting_engine/src/main.rs`
- `vrs_nesting/geometry/offset.py`
- `tests/test_geometry_offset.py`