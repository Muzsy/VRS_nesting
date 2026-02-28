# canvases/nesting_engine/nesting_engine_f2_3_spec_bin_offset_sync.md

> **Mentés helye a repóban:** `canvases/nesting_engine/nesting_engine_f2_3_spec_bin_offset_sync.md`
> **TASK_SLUG:** `nesting_engine_f2_3_spec_bin_offset_sync`
> **Terület (AREA):** `nesting_engine`

---

# F2-3 spec szinkron a bin_offset (spacing/2 - margin) kánonhoz

## 🎯 Funkció

A `docs/nesting_engine/f2_3_nfp_placer_spec.md` normatív specifikáció frissítése úgy, hogy **konzisztens legyen**
a már bevezetett clearance modellel és a tényleges kóddal:

**Kánon (mérvadó):**
- `spacing_mm` = min távolság **part–part**
- `margin_mm` = min távolság **part–bin edge**
- `kerf_mm` **nem része** az F2-3 mateknak; a v2 IO-ban csak **legacy spacing input forrásként** használható, ha `spacing_mm` hiányzik

**Képletek (mérvadók):**
- `inflate_delta = spacing_effective / 2`
- `bin_offset = (spacing_effective / 2) - margin`

A specben a korábbi `shrink = margin + spacing/2` modell **lecserélendő** a `bin_offset` modellre.

## Nem cél
- F2-3 implementáció (IFP/CFR/NFP placer) – külön task.
- IO contract újabb változtatása (a `spacing_mm` már optional mezőként létezik).

---

## 🧠 Fejlesztési részletek

### Mi a drift / miért kell
A spec jelenleg a 5.4 és 6.2 pontban a `shrink = margin + spacing/2` modellt rögzíti.
A kódban viszont már a `bin_offset = spacing/2 - margin` modell él (bin inflate is támogatott).

Ha a spec marad így, akkor a következő F2-3 implementáció a rossz IFP/CFR matekra fog épülni.

### Kötelező spec módosítások (konkrétan)

#### 1) 3.2 (IO contract) pontosítás
A “JSON v2 IO contract nem változik” mondat legyen lecserélve erre:

- a v2 IO contract **backward kompatibilis**
- `sheet.spacing_mm` **optional**
- `spacing_effective = spacing_mm if present else kerf_mm` (legacy spacing input source)
- kerf F2-3-ban **nem** kerf-kompenzáció, csak legacy spacing input forrás

#### 2) 5. fejezet (Spacing/margin/kerf policy) – bin_offset modellre átírni
- 5.2-ben legyen `spacing_effective` definíció (spacing_mm vs legacy kerf_mm)
- 5.3/5.4: “inner rect shrink” helyett:

**Bin offset (adjusted bin) definíció:**
Legyen a nyers bin `B = [bx0..bx1] × [by0..by1]` (rect).
Definiáljuk:

- `inflate_delta = spacing_effective/2`
- `bin_offset = inflate_delta - margin`

Az “adjusted bin”:

- `B_adj = offset_rect(B, bin_offset)`
  - rect esetén: `[bx0 - bin_offset .. bx1 + bin_offset] × [by0 - bin_offset .. by1 + bin_offset]`

**Margin garancia (magyarázat, röviden):**
A modell célja, hogy ha `offset(part, inflate_delta)` teljesen `B_adj`-ban van, akkor a nominális part biztosan
`offset(B, -margin)`-ban van, tehát part–edge távolság ≈ margin akkor is, ha `margin < spacing/2` (bin inflate).

#### 3) 6.2 (IFP képlet) – B_adj alapján
A `B_in` helyett `B_adj`-ot használd:

- `B_adj = [ax0..ax1] × [ay0..ay1]`
- normalizált part AABB: `[0..w] × [0..h]`

Megengedett eltolások:

- `tx ∈ [ax0, ax1 - w]`
- `ty ∈ [ay0, ay1 - h]`

Üres IFP, ha `ax1 - w < ax0` vagy `ay1 - h < ay0`.

#### 4) Rounding / skálázás
A specben legyen explicit: a mm→µm konverzió determinisztikusan a `mm_to_i64(mm)` szabályt követi (kód szerint `round()`).

---

## 🧪 Tesztállapot

### DoD
- [ ] `docs/nesting_engine/f2_3_nfp_placer_spec.md` 3.2/5/6 fejezetei a bin_offset modell szerint frissítve
- [ ] A specben a `spacing_effective` legacy szabály explicit (spacing_mm hiány → kerf_mm mint spacing input)
- [ ] A spec már támogatja a `margin < spacing/2` esetet (bin inflate)
- [ ] Gate PASS:
  `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_f2_3_spec_bin_offset_sync.md`

---

## 🌍 Lokalizáció
Nem releváns.

## 📎 Kapcsolódások
- `docs/nesting_engine/f2_3_nfp_placer_spec.md`
- `docs/nesting_engine/io_contract_v2.md`
- `rust/nesting_engine/src/main.rs` (rect_bin_bounds)
- `rust/nesting_engine/src/geometry/pipeline.rs` (inflate_delta/bin_offset)
- `AGENTS.md`, `docs/codex/yaml_schema.md`, `docs/codex/report_standard.md`