# Nesting Engine IO Contract v2

## 1. Verzió és kontextus

- Contract azonosito: `nesting_engine_v2`
- Cél: a Python runner es a `rust/nesting_engine` kozti stabil JSON hatarfelulet.
- A v2 fuggetlen a v1 contracttol (`docs/solver_io_contract.md`), nem backward kompatibilis.
- A belso geometry SCALE konverzio (`mm <-> i64`) implementacios reszlet, nem jelenik meg a JSON hataron.

## 2. Input contract (`sample_input_v2.json` szerkezet)

| Mezo | Tipus | Kotelezo | Leiras | Egyseg |
|---|---|---|---|---|
| `version` | string | Igen | Contract verzio, erteke mindig `nesting_engine_v2` | - |
| `seed` | integer (`>=0`) | Igen | Determinisztikus futas seedje | - |
| `time_limit_sec` | integer (`>0`) | Igen | Solver ido limit | sec |
| `sheet` | object | Igen | Tabla beallitasok | - |
| `sheet.width_mm` | number (`>0`) | Igen | Tabla szelesseg | mm |
| `sheet.height_mm` | number (`>0`) | Igen | Tabla magassag | mm |
| `sheet.kerf_mm` | number (`>=0`) | Igen | Vagasi res (kerf) | mm |
| `sheet.margin_mm` | number (`>=0`) | Igen | Biztonsagi tabla margó | mm |
| `sheet.spacing_mm` | number (`>=0`) | Nem | Part-part minimum tavolsag. Ha hianyzik: legacy fallback (`spacing_effective = kerf_mm`) | mm |
| `parts` | array (nem ures) | Igen | Nestelendo alkatresz tipuskeszlet | - |
| `parts[].id` | string | Igen | Egyedi part tipuskod | - |
| `parts[].quantity` | integer (`>0`) | Igen | Gyartando peldanyszam | db |
| `parts[].allowed_rotations_deg` | array&lt;integer&gt; (nem ures) | Igen | Megengedett forgatasok | deg |
| `parts[].outer_points_mm` | array&lt;[number,number]&gt; (`>=3`) | Igen | Kulso kontur pontjai | mm |
| `parts[].holes_points_mm` | array&lt;array&lt;[number,number]&gt;&gt; | Igen | Lyuk konturok listaja, ha nincs lyuk: `[]` | mm |

### Input invariansok

- A koordinatak a tabla helyi koordinatarendszereben vannak.
- `outer_points_mm` kontur: legalabb 3 pont, outer irany CCW.
- `holes_points_mm` konturok: legalabb 3 pont/lyuk, lyuk irany CW.
- Az input geometria nominalis (nem inflated).
- Effective spacing szabalya: `spacing_effective_mm = sheet.spacing_mm (ha van)`, kulonben `sheet.kerf_mm`.

## 3. Output contract (`sample_output_v2.json` szerkezet)

| Mezo | Tipus | Kotelezo | Leiras | Egyseg |
|---|---|---|---|---|
| `version` | string | Igen | Contract verzio, erteke mindig `nesting_engine_v2` | - |
| `seed` | integer | Igen | Input seed echo | - |
| `solver_version` | string | Igen | Solver build/verzio azonosito | - |
| `status` | string (`ok` vagy `partial`) | Igen | Teljes vagy reszleges elhelyezes | - |
| `sheets_used` | integer (`>=0`) | Igen | Felhasznalt tablak szama | db |
| `placements` | array | Igen | Elhelyezett peldanyok | - |
| `placements[].part_id` | string | Igen | Part tipus azonosito | - |
| `placements[].instance` | integer (`>=0`) | Igen | 0-bazisu peldany index ugyanazon `part_id`-n belul | - |
| `placements[].sheet` | integer (`>=0`) | Igen | 0-bazisu tabla index | - |
| `placements[].x_mm` | number | Igen | Elhelyezes X koordinata | mm |
| `placements[].y_mm` | number | Igen | Elhelyezes Y koordinata | mm |
| `placements[].rotation_deg` | integer | Igen | Tenyeges forgatas, az inputban engedelyezettek egyike | deg |
| `unplaced` | array | Igen | El nem helyezett peldanyok | - |
| `unplaced[].part_id` | string | Igen | Part tipus azonosito | - |
| `unplaced[].instance` | integer (`>=0`) | Igen | Peldany index | - |
| `unplaced[].reason` | string | Igen | Elhelyezes sikertelensegenek oka | - |
| `objective` | object | Igen | Cel-fuggveny osszegzes | - |
| `objective.sheets_used` | integer (`>=0`) | Igen | Elsoleges cel metrika (P1) | db |
| `objective.utilization_pct` | number (`0..100`) | Igen | Tabla-kihasznaltsag (diagnosztika) | % |
| `objective.remnant_value_ppm` | integer (`>=0`) | Igen | P2 proxy remnant aggregate score | ppm |
| `objective.remnant_area_score_ppm` | integer (`>=0`) | Igen | P2 komponens: free proxy area score | ppm |
| `objective.remnant_compactness_score_ppm` | integer (`>=0`) | Igen | P2 komponens: strip compactness score | ppm |
| `objective.remnant_min_width_score_ppm` | integer (`>=0`) | Igen | P2 komponens: min usable width proxy score | ppm |
| `meta` | object | Igen | Futasi metaadatok | - |
| `meta.elapsed_sec` | number (`>=0`) | Nem | Python runner-level meres (`runner_meta.json`), nem Rust kernel stdout mezo | sec |
| `meta.determinism_hash` | string | Igen | Determinisztikus hash ertek | - |
| `meta.compaction` | object | Igen | H3-T8 additive compaction evidence blokk | - |
| `meta.compaction.mode` | string (`off` vagy `slide`) | Igen | Aktiv compaction policy mod | - |
| `meta.compaction.applied` | boolean | Igen | Volt-e legalabb egy tenyleges compaction mozgas | - |
| `meta.compaction.moved_items_count` | integer (`>=0`) | Igen | Hany placement kapott uj poziciot a post-pass soran | db |
| `meta.compaction.occupied_extent_before` | object vagy `null` | Igen | Occupied extent a post-pass elott | mm |
| `meta.compaction.occupied_extent_after` | object vagy `null` | Igen | Occupied extent a post-pass utan | mm |
| `_note` | string | Nem | Emberi megjegyzes, illusztracios mintakhoz | - |

Megjegyzes: a Rust `nest` stdout output `meta` objektuma determinisztikus kimenetre optimalizalt,
ezert csak a `determinism_hash` mezot adja vissza. A futasido (`elapsed_sec`) runner artifact szinten
(`runs/<run_id>/runner_meta.json`) erheto el.

### 3.1 Objective sorrend (normativ)

- A solver objective prioritasa:
  1. kevesebb `unplaced`
  2. kevesebb `sheets_used`
  3. magasabb `objective.remnant_value_ppm`
- Az F3-3 iteracio `remnant_*_ppm` mezoi proxy modellen alapulnak (sheet AABB + occupied envelope),
  nem exact polygon-remnant topologian.
- A `meta.determinism_hash` canonicalization contract valtozatlan; az objective blokk bovulese ezt nem modositja.
- A `meta.compaction` blokk additive evidence: placement metadata, nem objective-prioritas feluliras.
  A hash contract valtozatlanul placement canonical view alapu, nem a compaction evidence-bol kepzett.

### 3.2 Compaction extent payload (`meta.compaction.occupied_extent_*`)

Ha van legalabb 1 placement, az `occupied_extent_before` es `occupied_extent_after` objektum:

- `min_x_mm`
- `min_y_mm`
- `max_x_mm`
- `max_y_mm`
- `width_mm` (`max_x_mm - min_x_mm`)
- `height_mm` (`max_y_mm - min_y_mm`)

Ha nincs placement, ezek a mezok `null`-ok.

## 4. Geometria egyezmenyek (kobe vesett)

```text
1) Koordinata-rendszer: origo = tabla bal-also sarok (0,0), X jobbra, Y felfele.
2) Kontur-irany: outer kontur CCW, hole kontur CW.
3) Egység: JSON hataron kizarolag mm (f64/number).
4) Nominalis vs. inflated: input es output koordinatak nominalis geometriat irnak le.
   A kerf/margin inflate belso solver lepes, nem kulon output mező.
5) Elhelyezesi transzformacio: a part lokal pontjai `rotation_deg` szerint
   forognak, majd `(x_mm, y_mm)` eltolast kapnak.
```

## 5. `unplaced.reason` kodok

| Kod | Jelentes |
|---|---|
| `PART_NEVER_FITS_SHEET` | A part nominalis + belso inflate utan sem fer el a hasznos tabla teruleten. |
| `TIME_LIMIT_EXCEEDED` | A stop policy (wall-clock vagy work-budget) limitet ert el, mielott minden peldany elhelyezheto lett volna. |
| `INSTANCE_CANDIDATE_CAP` | A per-instance candidate cap (`NESTING_ENGINE_BLF_INSTANCE_CANDIDATE_CAP`) limitet erte el. Az instance nem kapott tobb jelolt-probalkozast. Csak akkor aktiv, ha az env var > 0. |

## 6. `determinism_hash` szamitasi mod (normativ hivatkozas)

A `meta.determinism_hash` mezo szamitasi szabalyai normativan itt vannak rogzitve:
`docs/nesting_engine/json_canonicalization.md`.

Ebben a dokumentumban nincs canonicalization-szabaly duplikacio: a hash-kepzeshez a
fenti normativ dokumentum kovetese kotelezo. A jelenlegi contract verzioja
valtozatlanul `nesting_engine.hash_view.v1`.

### 6.1 Determinizmus es timeout-bound policy (normativ)

Definicio: egy futas **timeout-bound**, ha az alabbiak barmelyike igaz:

- az output `unplaced[]` tombjeben van legalabb egy `reason == "TIME_LIMIT_EXCEEDED"` elem, vagy
- a futas a `time_limit_sec` hatart eleri (wall-clock alapon).

Normativ elvaras:

- Azonos input + azonos seed + nem-timeout-bound futas eseten a `meta.determinism_hash` stabilitasa elvart.
- Timeout-bound futas eseten a hash stabilitas **best-effort**: kisebb run-to-run elteres megengedett.
- A timeout-bound stop forrasa lehet:
  - wall-clock limit (`time_limit_sec`), vagy
  - determinisztikus work-budget cutoff (ha a solver ilyen stop modban fut).

Megjegyzes:

- A `time_limit_sec` ellenorzese wall-clock jellegu, jellemzoen durvabb checkpointokkal.
- Ezert a limit-hatar kozeleben termeszetes lehet, hogy ket futas kozott 1-2 placement elteres jelenik meg.
- Az ilyen eset benchmark/report oldalon kulon timeout-bound kategoriakent kezelendo, nem automatikus algoritmikus regressziokent.

### 6.2 Repo gate evidence (PR)

- A PR merge gate a `.github/workflows/repo-gate.yml` workflow, ami a `scripts/check.sh`-t futtatja.
- A `check.sh` determinism hardening reszekent fut:
  - `cargo test --manifest-path rust/nesting_engine/Cargo.toml determinism_`
  - `RUNS=10 ./scripts/smoke_nesting_engine_determinism.sh`
- A determinism smoke a teljes `nest` stdout JSON byte-azonossagat ellenorzi es
  Python oldalon ujraszamolja a canonical hash-view SHA-256 erteket.

## 7. Pipeline preprocessing contract (pipeline_v1)

Ez a szekcio a `nesting_engine inflate-parts` stdin/stdout JSON contractjat rogziti,
nem a `nest` solver endpointet.

### 7.1 Request (`PipelineRequest`)

| Mezo | Tipus | Kotelezo | Leiras |
|---|---|---|---|
| `version` | string | Igen | Erteke: `pipeline_v1` |
| `kerf_mm` | number (`>=0`) | Igen | Vagasi res (kerf) |
| `margin_mm` | number (`>=0`) | Igen | Kiegeszito margó |
| `spacing_mm` | number (`>=0`) | Nem | Part-part minimum tavolsag. Ha hianyzik: legacy fallback (`spacing_effective = kerf_mm`) |
| `parts` | array&lt;PartRequest&gt; | Nem (default `[]`) | Part preprocessing bemenet |
| `stocks` | array&lt;StockRequest&gt; | Nem (default `[]`) | Stock preprocessing bemenet |

`PartRequest`:

| Mezo | Tipus | Kotelezo | Leiras |
|---|---|---|---|
| `id` | string | Igen | Part azonosito |
| `outer_points_mm` | array&lt;[number,number]&gt; (`>=3`) | Igen | Nominalis outer kontur |
| `holes_points_mm` | array&lt;array&lt;[number,number]&gt;&gt; | Igen | Nominalis hole konturok (`[]` ha nincs) |

`StockRequest`:

| Mezo | Tipus | Kotelezo | Leiras |
|---|---|---|---|
| `id` | string | Igen | Stock azonosito |
| `outer_points_mm` | array&lt;[number,number]&gt; (`>=3`) | Igen | Nominalis stock outer kontur |
| `holes_points_mm` | array&lt;array&lt;[number,number]&gt;&gt; | Igen | Nominalis stock hole/defect konturok (`[]` ha nincs) |

### 7.2 Response (`PipelineResponse`)

| Mezo | Tipus | Kotelezo | Leiras |
|---|---|---|---|
| `version` | string | Igen | Input `version` echo |
| `parts` | array&lt;PartResponse&gt; | Nem (default `[]`) | Part preprocess eredmenyek |
| `stocks` | array&lt;StockResponse&gt; | Nem (default `[]`) | Stock preprocess eredmenyek |

`PartResponse` statusok:
- `ok`
- `hole_collapsed`
- `self_intersect`
- `error`

`StockResponse`:

| Mezo | Tipus | Kotelezo | Leiras |
|---|---|---|---|
| `id` | string | Igen | Stock azonosito |
| `status` | string | Igen | `ok` / `self_intersect` / `error` |
| `usable_outer_points_mm` | array&lt;[number,number]&gt; | Igen | Hasznalhato outer kontur mm-ben |
| `usable_holes_points_mm` | array&lt;array&lt;[number,number]&gt;&gt; | Igen | Hasznalhato hole konturok mm-ben |
| `diagnostics` | array&lt;Diagnostic&gt; | Igen | Diagnosztikak (`SELF_INTERSECT`, `OFFSET_ERROR`) |

### 7.3 Normativ offset szabaly (`stocks`)

- `spacing_effective_mm = spacing_mm (ha van), kulonben kerf_mm` (legacy)
- `inflate_delta_mm = spacing_effective_mm / 2`
- `bin_offset_mm = spacing_effective_mm / 2 - margin_mm`
- Part preprocess szabaly:
  - part outer/hole inflate: `inflate_delta_mm`
- Stock preprocess szabaly:
  - outer kontur: `offset(stock_outer, bin_offset_mm)` (negativ = deflate, pozitiv = inflate)
  - hole/defect konturok: inflate `inflate_delta_mm` alapjan (margin nem resze)
- Ha nominalis stock self-intersect, akkor a status kotelezoen `self_intersect` (reject, nincs auto-fix).

## 8. v1 <-> v2 osszehasonlitas

| Aspektus | v1 (`docs/solver_io_contract.md`) | v2 (`docs/nesting_engine/io_contract_v2.md`) |
|---|---|---|
| Contract azonosito | `contract_version: v1` | `version: nesting_engine_v2` |
| Scope | Altalanos solver boundary | Kifejezetten `nesting_engine` boundary |
| Idolimit mezo | `time_limit_s` | `time_limit_sec` |
| Tabla leiras | `stocks[]` (width/height/shape opciok) | `sheet` (width/height/kerf/margin/spacing opcionális) |
| Part geometria | `outer_points` / `holes_points` (opcionalis) | `outer_points_mm` / `holes_points_mm` (explicit mm) |
| Kimeneti placement mezok | `instance_id`, `sheet_index`, `x`, `y` | `instance`, `sheet`, `x_mm`, `y_mm` |
| Objective | opcionális `metrics` | kotelezo `objective` |
| Determinizmus hash | nincs definialva | kotelezo `meta.determinism_hash` normativ szaballyal |
| Kompatibilitas | aktiv v1 contract | kulonallo v2 contract |

## 9. Additive cavity prepack policy (worker-side, v1)

Ez a szekcio normativan rogziti, hogy a cavity-first/composite modell elso
iteracioja additive worker-side policy, nem uj Rust IO contract.

### 9.1 Fontos scope-hatar

- A solver input/output contract verzioja valtozatlanul `nesting_engine_v2`.
- A cavity plan nem a `nesting_engine_v2` JSON-ba epitett uj mezo, hanem kulon
  sidecar artifact:
  - `<run_dir>/cavity_plan.json`
  - `runs/<run_id>/inputs/cavity_plan.json`

### 9.2 `part_in_part=prepack` policy jelentese

- `part_in_part=prepack` worker policy ertek.
- Rust CLI jelenleg csak `off|auto` erteket fogad, ezert prepack modban az
  effective engine CLI `--part-in-part off`.
- Normativ szabaly: prepack es legacy engine runtime `--part-in-part auto`
  ugyanazon runban nem aktiv egyszerre.

### 9.3 Top-level input invarians prepack modban

Ha prepack aktiv:
- parent composite virtual top-level part:
  - `quantity=1`
  - `holes_points_mm=[]`
  - `outer_points_mm` a parent kulso konturja
- child top-level `quantity` csokken az internal placement darabszammal
- child `quantity=0` eseten child nem megy top-level solver inputba

### 9.4 Result normalizer kovetelmeny

Prepack eseten a normalizernek:
- virtual parent ID-kat vissza kell mapelnie valodi parent revision ID-kra
- internal child placementeket abszolut sheet placementte kell expanzionalnia
- top-level child instanceeket offsetelnie kell (`top_level_instance_base`)

Ha `cavity_plan` hianyzik vagy `enabled=false`, legacy normalizer viselkedes
kotelezo.

### 9.5 Nem-cel deklaracio

- Ez a contract NEM allit full hole-aware NFP kepesseget.
- Ez a contract NEM oldja meg a manufacturing cut-ordert.
