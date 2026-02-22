# canvases/nesting_engine/nesting_engine_polygon_pipeline.md

> **Mentés helye a repóban:** `canvases/nesting_engine/nesting_engine_polygon_pipeline.md`
> **TASK_SLUG:** `nesting_engine_polygon_pipeline`
> **Terület (AREA):** `nesting_engine`

---

# NFP Nesting Engine — Polygon pipeline: nominális → inflated geometria

## 🎯 Funkció

A meglévő Python DXF importer (`vrs_nesting/dxf/importer.py`) már előállítja a
nominális polygon + lyukak struktúrát. Ez a task ezt az adatot JSON stdio-n
átadja a Rust kernelnek, amely `inflate_part()` hívással előállítja az inflated
(kerf+margin offsetelt) geometriát. A pipeline végén minden part-hoz kétféle
geometria létezik:

- **nominális** — a DXF eredeti méretei, DXF exporthoz (változatlan)
- **inflated** — kerf+margin offsetelt, a solver feasibility engine-jéhez

Ezen felül: a `scripts/check.sh`-ban az F1-1 task során bevezetett sorrend-hiba
(nesting_engine build a vrs_solver előtt) itt kerül korrigálásra.

**Nem cél:**
- Baseline placer implementálása (az F1-4 task)
- NFP számítás (F2-x task-ok)
- Python DXF importer logikájának megváltoztatása
- A `vrs_solver` bármilyen módosítása

---

## 🧠 Fejlesztési részletek

### Érintett fájlok

**Létrehozandó (új):**
- `rust/nesting_engine/src/geometry/pipeline.rs` — inflate pipeline Rust oldal
- `rust/nesting_engine/src/io/mod.rs` — JSON stdio kezelés (input parse, output serialize)
- `rust/nesting_engine/src/io/pipeline_io.rs` — `PipelineRequest` / `PipelineResponse` struktúrák
- `docs/nesting_engine/architecture.md` — nominális vs. inflated szabály dokumentálva
- `poc/nesting_engine/pipeline_smoke_input.json` — pipeline smoke teszt input
- `poc/nesting_engine/pipeline_smoke_expected.json` — elvárt output struktúra (illustrative)

**Módosuló (meglévő):**
- `rust/nesting_engine/src/main.rs` — pipeline subcommand hozzáadása
- `rust/nesting_engine/Cargo.toml` — ha új dependency szükséges (pl. `serde_json` már megvan)
- `scripts/check.sh` — **sorrend-korrekció**: nesting_engine build kerüljön a vrs_solver build UTÁ NRA

**Nem módosul:**
- `vrs_nesting/dxf/importer.py` (nominális geometria pipeline — érintetlen marad)
- `rust/vrs_solver/` (egyetlen fájl sem)
- `docs/solver_io_contract.md` (v1)
- `docs/nesting_engine/io_contract_v2.md`
- `docs/nesting_engine/json_canonicalization.md`

---

### Architektúra: nominális vs. inflated szabály (kőbe vésett)

```
┌─────────────────────┐       JSON stdio      ┌──────────────────────────┐
│  Python DXF         │  ──────────────────►  │  Rust nesting_engine     │
│  importer           │  PipelineRequest       │  pipeline subcommand     │
│                     │  (nominális points)    │                          │
│  importer.py        │                        │  inflate_part()          │
│  offset.py (v2)     │  ◄──────────────────  │  i_overlay crate         │
└─────────────────────┘  PipelineResponse      └──────────────────────────┘
                         (inflated points)
        │                                               │
        ▼                                               ▼
   DXF export                                   feasibility engine
   (nominális!)                                 (inflated!)
```

**Invariáns (soha nem szeghet meg):**
- A solver feasibility engine CSAK inflated geometriával dolgozik
- DXF export MINDIG nominális geometriából történik
- Ez a különbség soha nem keveredhet

---

### Pipeline subcommand: JSON stdio interface

A `rust/nesting_engine` bináris kap egy új subcommand-ot: `inflate-parts`

```bash
echo '{ PipelineRequest JSON }' | ./rust/nesting_engine/target/release/nesting_engine inflate-parts
```

**PipelineRequest séma:**
```json
{
  "version": "pipeline_v1",
  "kerf_mm": 0.2,
  "margin_mm": 5.0,
  "parts": [
    {
      "id": "part_001",
      "outer_points_mm": [[0,0],[100,0],[100,50],[0,50]],
      "holes_points_mm": []
    }
  ]
}
```

**PipelineResponse séma:**
```json
{
  "version": "pipeline_v1",
  "parts": [
    {
      "id": "part_001",
      "status": "ok",
      "inflated_outer_points_mm": [[...], ...],
      "inflated_holes_points_mm": [[...], ...],
      "diagnostics": []
    }
  ]
}
```

**`status` értékek:**

| Érték | Jelentés |
|---|---|
| `"ok"` | inflate sikeres, geometria valid |
| `"hole_collapsed"` | legalább 1 lyuk eltűnt az **inflated** geometriából **feasibility okból** (nem FAIL). A **nominális** geometriában a lyuk(ak) exporthoz **megmaradnak**, csak **nesting cavity-ként nem használhatók**. A collapsed hole(oka)t kötelező diagnosztikában rögzíteni. |
| `"self_intersect"` | az inflated outer önmetsző → ez FAIL, a part nem elhelyezhető |
| `"error"` | egyéb Rust-szintű hiba |

**`diagnostics` tömb:**
```json
[
  {
    "code": "HOLE_COLLAPSED",
    "hole_index": 0,
    "nominal_hole_bbox_mm": [10.0, 10.0, 12.0, 12.0],
    "preserve_for_export": true,
    "usable_for_nesting": false,
    "detail": "hole collapsed in inflated geometry; nominal hole preserved for export"
  },
  { "code": "SELF_INTERSECT", "detail": "outer polygon self-intersects after inflate" }
]
```

**Kötelező viselkedés `hole_collapsed` esetben (nem opcionális):**
- A pipeline outputnak **akkor is** vissza kell adnia az `inflated_outer_points_mm`-et (feasibility-hez szükséges).
- Mivel az `inflate_part()` jelenleg `Err(HoleCollapsed{...})`-ot ad, `hole_collapsed` esetben **fallback** szükséges.
- Fallback során outer inflate **lyukak nélkül** (vagy csak a megmaradt lyukakkal, ha később lesz részleges eredmény), hogy legyen inflated geometria a feasibility engine-nek.
- A nominális lyuk információ **nem veszhet el**: `HOLE_COLLAPSED` diagnosztikában kötelező legalább `hole_index`, `nominal_hole_bbox_mm`, `preserve_for_export=true`, `usable_for_nesting=false`.

---

### Rust oldal: `pipeline.rs`

```rust
pub struct InflateRequest {
    pub id: String,
    pub outer_points_mm: Vec<(f64, f64)>,
    pub holes_points_mm: Vec<Vec<(f64, f64)>>,
    pub kerf_mm: f64,
    pub margin_mm: f64,
}

pub struct InflateResult {
    pub id: String,
    pub status: InflateStatus,
    pub inflated_outer: Vec<(f64, f64)>,
    pub inflated_holes: Vec<Vec<(f64, f64)>>,
    pub diagnostics: Vec<Diagnostic>,
}

pub enum InflateStatus { Ok, HoleCollapsed, SelfIntersect, Error(String) }
pub struct Diagnostic { pub code: String, pub hole_index: Option<usize>, pub detail: String }

/// Teljes pipeline: nominális mm → inflated mm
/// A belső scale konverzió (mm→i64→mm) itt történik, kívülről láthatatlan
pub fn run_inflate_pipeline(requests: Vec<InflateRequest>) -> Vec<InflateResult>
```

**Kapcsolat az F1-1 `offset.rs`-sel:** az `inflate_part()` függvényt hívja —
ez már megvan az `offset.rs`-ben, a `pipeline.rs` csak orchestrálja és
JSON-kompatibilis struktúrákba csomagolja.

---

### Determinizmus követelmény

Az inflate pipeline outputja determinisztikus kell legyen:
- Azonos input JSON → azonos output JSON (byte-szinten)
- Az `i_overlay` crate offset algoritmusa determinisztikus (F1-1-ben igazolt)
- A koordináta round-trip (mm → i64 → mm) az F1-1 scale policy szerint

**Smoke teszt a determinizmusra:**
```bash
echo "$(cat poc/nesting_engine/pipeline_smoke_input.json)" \
  | ./rust/nesting_engine/target/release/nesting_engine inflate-parts > /tmp/out1.json
echo "$(cat poc/nesting_engine/pipeline_smoke_input.json)" \
  | ./rust/nesting_engine/target/release/nesting_engine inflate-parts > /tmp/out2.json
diff /tmp/out1.json /tmp/out2.json   # üresnek kell lennie
```

**Megjegyzés:** a `determinism_hash` (RFC 8785 / JCS) ennél a pipeline lépésnél
még nem szükséges — a hash az F1-4-ben, a teljes placement output szintjén jelenik
meg. A pipeline smoke teszt egyszerű `diff`-el ellenőrizhető.

---

### `scripts/check.sh` sorrend-korrekció

Az F1-1 task során a nesting_engine build lépés a vrs_solver build **elé** kerül,
holott a canvas utasítás szerint utána kellett volna. A gate minden futtatásban
PASS volt (a két build független), de a deklarált sorrenddel ellentétes.

**Szükséges korrekció:**
```bash
# HELYES sorrend a check.sh-ban:
# 1. vrs_solver build  ← marad ahol van
# 2. nesting_engine build  ← kerüljön a vrs_solver UTÁN
```

Ez a módosítás additive (tartalom nem változik, csak sorrend), és a gate
futtatásával azonnal verifikálható.

---

### Kockázat + mitigáció + rollback

| Kockázat | Mitigáció | Rollback |
|---|---|---|
| `i_overlay` offset más eredményt ad mint az F1-1 unit teszt várta | A pipeline smoke teszt megismétli az F1-1 inflate tesztet end-to-end | Nincs state változás — pure function |
| JSON stdio parse hiba (malformed input) | Explicit hibakód és stderr üzenet, exit 1 — a Python oldal ezt kezeli | Python subprocess wrapper try/except |
| check.sh sorrend-korrekció eltöri a gate-et | Csak sorrend változik, tartalom nem — regresszió: vrs_solver build PASS marad | git revert a check.sh változásra |
| `self_intersect` status helyett crash | `InflateStatus::Error` ágban panic helyett graceful error return | Unit teszt az error ágra |

---

## ✅ Pipálható DoD lista

### Felderítés
- [x] `AGENTS.md` elolvasva
- [x] `docs/codex/overview.md` elolvasva
- [x] `docs/codex/yaml_schema.md` elolvasva
- [x] `docs/codex/report_standard.md` elolvasva
- [x] `rust/nesting_engine/src/geometry/offset.rs` megvizsgálva (inflate_part API ismert)
- [x] `rust/nesting_engine/src/geometry/scale.rs` megvizsgálva (SCALE, mm_to_i64 ismert)
- [x] `docs/nesting_engine/io_contract_v2.md` megvizsgálva (nominális mezők neve ismert)
- [x] `docs/nesting_engine/json_canonicalization.md` megvizsgálva (determinism referencia)
- [x] `scripts/check.sh` megvizsgálva (build sorrend azonosítva)

### Implementáció — Rust
- [ ] `rust/nesting_engine/src/io/mod.rs` létrehozva
- [ ] `rust/nesting_engine/src/io/pipeline_io.rs` — `PipelineRequest`, `PipelineResponse`, status enum, diagnostics
- [ ] `rust/nesting_engine/src/geometry/pipeline.rs` — `run_inflate_pipeline()`, `InflateRequest`, `InflateResult`
- [ ] `rust/nesting_engine/src/main.rs` — `inflate-parts` subcommand hozzáadva (stdin JSON → stdout JSON)
- [ ] `cargo test` — pipeline unit tesztek: ok eset, hole_collapsed eset, self_intersect eset, determinizmus

### Implementáció — Poc fájlok
- [ ] `poc/nesting_engine/pipeline_smoke_input.json` — valid JSON, legalább 2 part (1 lyukkal, 1 anélkül)
- [ ] `poc/nesting_engine/pipeline_smoke_expected.json` — illustrációs, `_note` mezővel jelölve

### Implementáció — Dokumentáció és check.sh
- [ ] `docs/nesting_engine/architecture.md` — nominális vs. inflated szabály, pipeline ábra
- [ ] `scripts/check.sh` sorrend korrigálva: nesting_engine build a vrs_solver UTÁN

### Ellenőrzés
- [ ] `cargo build --release --manifest-path rust/nesting_engine/Cargo.toml` PASS
- [ ] `cargo test --manifest-path rust/nesting_engine/Cargo.toml` PASS (pipeline tesztek benne)
- [ ] `cargo build --release --manifest-path rust/vrs_solver/Cargo.toml` PASS (regresszió)
- [ ] Pipeline smoke determinizmus: két egymást követő `inflate-parts` futás azonos outputot ad (`diff` üres)
- [ ] `python3 -m json.tool poc/nesting_engine/pipeline_smoke_input.json` PASS

### Gate
- [ ] `./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_polygon_pipeline.md` PASS

---

## 🧪 Tesztállapot

**Kötelező gate:**
```
./scripts/verify.sh --report codex/reports/nesting_engine/nesting_engine_polygon_pipeline.md
```

**Task-specifikus ellenőrzések:**
```bash
# Rust tesztek
cargo test --manifest-path rust/nesting_engine/Cargo.toml

# Regresszió: vrs_solver build
cargo build --release --manifest-path rust/vrs_solver/Cargo.toml

# Pipeline smoke determinizmus
echo "$(cat poc/nesting_engine/pipeline_smoke_input.json)" \
  | ./rust/nesting_engine/target/release/nesting_engine inflate-parts > /tmp/pipe_out1.json
echo "$(cat poc/nesting_engine/pipeline_smoke_input.json)" \
  | ./rust/nesting_engine/target/release/nesting_engine inflate-parts > /tmp/pipe_out2.json
diff /tmp/pipe_out1.json /tmp/pipe_out2.json

# JSON validáció
python3 -m json.tool poc/nesting_engine/pipeline_smoke_input.json > /dev/null
```

**Elfogadási kritériumok:**
- Pipeline `ok` eset: `rect_100x50` inflated bbox ≥ `102×52mm` (kerf=0.2, margin=5 → delta=5.1mm kétoldalon)
- Pipeline `hole_collapsed` eset: kis lyuk (pl. 2×2mm) 5mm delta után eltűnik → status=`hole_collapsed`, nem crash
- Pipeline `self_intersect` eset: extrém vékony alak → status=`self_intersect`, nem crash
- Determinizmus: `diff /tmp/pipe_out1.json /tmp/pipe_out2.json` üres

---

## 🌍 Lokalizáció

Nem releváns.

---

## 📎 Kapcsolódások

**Szülő dokumentum:**
- `canvases/nesting_engine/nesting_engine_backlog.md` — F1-3 task

**Előző task outputjai — elolvasandó implementáció előtt:**
- `rust/nesting_engine/src/geometry/offset.rs` — `inflate_part()`, `OffsetError` (F1-1)
- `rust/nesting_engine/src/geometry/scale.rs` — `SCALE`, `mm_to_i64()` (F1-1)
- `rust/nesting_engine/src/geometry/types.rs` — `Point64`, `Polygon64` (F1-1)
- `docs/nesting_engine/tolerance_policy.md` — CCW/CW, touching policy (F1-1)
- `docs/nesting_engine/io_contract_v2.md` — nominális mezőnevek (F1-2)
- `docs/nesting_engine/json_canonicalization.md` — determinism referencia (F1-2)

**Következő task (F1-4):**
- `canvases/nesting_engine/nesting_engine_baseline_placer.md`

**Codex workflow:**
- `AGENTS.md`, `docs/codex/overview.md`, `docs/codex/yaml_schema.md`, `docs/codex/report_standard.md`
