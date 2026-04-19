# Gépparaméterek audit — tárolás, adatstruktúra, adatfolyam

Dátum: 2026-04-19
Scope: a VRS_nesting repó teljes, gépparaméterekre vonatkozó állapotfelmérése.
Források: `supabase/migrations/*`, `api/services/*`, `worker/*`, `frontend/src/*`.

## 1. Vezetői összefoglaló

Az alkalmazás **nem rendelkezik külön `machines` master katalógussal**. A gépeket
minden helyen egyszerű text mező (`machine_code`) azonosítja, konvenció alapján
(pl. `hypertherm_edge_connect`, `linuxcnc_qtplasmac`). A gépparaméterek
**négy külön domain-ben** élnek, és egy-egy run lezárásakor egy immutable
nesting run snapshotba kristályosodnak ki. A runtime, geometriailag érdemi
paraméterek (kerf, spacing, margin, rotation, thickness) **típusos relációs
oszlopokban** vannak check-constraintekkel; a gép-specifikus postprocess és
manufacturing konfig viszont **`config_jsonb` jsonb blokkban**, szigorú,
kódban kényszerített scope-határokkal.

A frontend a paraméterek töredékét kezeli: csak `spacing` és `margin`
szerkeszthető a run-wizardban, a technology setup / manufacturing / cut-rule /
postprocessor profilokhoz **nincs UI**.

## 2. A paraméterek tárolási rétegei

### 2.1 Nesting-szintű technológiai paraméterek

Migráció: [20260310230000_h0_e2_t3_technology_domain_alapok.sql](../../supabase/migrations/20260310230000_h0_e2_t3_technology_domain_alapok.sql)

Két tábla **azonos oszlopkészlettel**:

- `app.technology_presets` — owner-független, újrahasználható sablonok.
- `app.project_technology_setups` — projektre másolt aktív beállítás,
  `is_default` flaggel egy approved default-ot jelölnek ki projektenként.

Mezők (kivonat):

| Mező | Típus | Constraint | Jelentés |
|---|---|---|---|
| `machine_code` | text | `length > 0` | Gép konvencionális kódja, nincs FK |
| `material_code` | text | `length > 0` | Anyag konvencionális kódja |
| `thickness_mm` | `numeric(10,3)` | `> 0` | Lemezvastagság |
| `kerf_mm` | `numeric(10,3)` | `>= 0` | Vágásrés (solver input) |
| `spacing_mm` | `numeric(10,3)` | `>= 0` | Part-part távolság |
| `margin_mm` | `numeric(10,3)` | `>= 0` | Lap-szél távolság |
| `rotation_step_deg` | int | `> 0, <= 360` | Elforgatási lépcső |
| `allow_free_rotation` | bool | default `false` | Szabad forgatás engedélyezése |
| `lifecycle` | `app.revision_lifecycle` | default `approved` / `draft` | Életciklus állapot |

Indexek: `(material_code, machine_code, thickness_mm)` katalóguskeresésre,
`project_id` + `(project_id, lifecycle)` projektenkénti szűrésre, valamint
egy parciális unique index (`project_id WHERE is_default`) garantálja, hogy
projektenként maximum egy default setup legyen.

### 2.2 Gyártási profilok

Migráció: [20260321233000_h2_e1_t2_project_manufacturing_selection.sql](../../supabase/migrations/20260321233000_h2_e1_t2_project_manufacturing_selection.sql)

Owner-scoped, verziózott truth-réteg:

- `app.manufacturing_profiles` — owner + `profile_code` csoport.
- `app.manufacturing_profile_versions` — verziónként:
  `machine_code` (opcionális), `material_code` (opcionális),
  `thickness_mm` (kötelező), `kerf_mm` (default 0), **`config_jsonb`**
  (szabadon bővülő jsonb), `active_postprocessor_profile_version_id`
  (opcionális FK a postprocessor version felé).
- `app.project_manufacturing_selection` — 1:1 a projekttel, egy aktív
  manufacturing version kiválasztása projekt-szinten.

Owner-konzisztencia FK-kel kényszerített (`manufacturing_profile_id, owner_user_id`).
Külön SECURITY DEFINER függvény: `app.owns_manufacturing_profile_version(uuid)`.

### 2.3 Postprocessor profilok

Migráció: [20260322040000_h2_e5_t2_postprocessor_profile_version_domain_aktivalasa.sql](../../supabase/migrations/20260322040000_h2_e5_t2_postprocessor_profile_version_domain_aktivalasa.sql)

Itt él a **gép-specifikus export konfiguráció**:

| Mező | Típus | Jelentés |
|---|---|---|
| `adapter_key` | text, default `generic` | Adapter kulcs (pl. `hypertherm_edge_connect`, `linuxcnc_qtplasmac`) |
| `output_format` | text, default `json` | Kimeneti formátum |
| `schema_version` | text, default `v1` | Config schema verzió |
| `config_jsonb` | jsonb | Gép-specifikus beállítások |

A `config_jsonb` tartalmát a kód szigorúan szűkíti
([api/services/machine_specific_adapter.py:37-41](../../api/services/machine_specific_adapter.py#L37-L41)):
megengedett top-level blokkok `program_format`, `motion_output`,
`coordinate_mapping`, `command_map`, `lead_output`, `artifact_packaging`,
`capabilities`, `fallbacks`, `export_guards`, `process_mapping`.

Konkrét gép-specifikus adaptereket a
[api/services/machine_specific_adapter.py](../../api/services/machine_specific_adapter.py)
két targetre támogat:

1. **Hypertherm Edge Connect** (H2-E5-T4): `adapter_key = hypertherm_edge_connect`,
   `output_format = basic_plasma_eia_rs274d`, kiterjesztés `.txt`.
2. **LinuxCNC / QtPlasmaC** (H2-E5-T5): `adapter_key = linuxcnc_qtplasmac`,
   `output_format = basic_manual_material_rs274ngc`, kiterjesztés `.ngc`.

### 2.4 Vágási szabályok (cut rules)

Migrációk:
- [20260322010000_h2_e3_t1_cut_rule_set_model.sql](../../supabase/migrations/20260322010000_h2_e3_t1_cut_rule_set_model.sql)
- [20260322013000_h2_e3_t2_cut_contour_rules_model.sql](../../supabase/migrations/20260322013000_h2_e3_t2_cut_contour_rules_model.sql)

`app.cut_rule_sets` — fejléc: `owner_user_id`, `name`, `version_no`,
és opcionális matcher-kulcsok (`machine_code`, `material_code`, `thickness_mm`).

`app.cut_contour_rules` — kontúr-szintű paraméterek:

| Mező | Típus | Jelentés |
|---|---|---|
| `contour_kind` | text, `outer`/`inner` | Szerepkör |
| `feature_class` | text, default `default` | Feature osztály (pl. `hole_small`, `slot`) |
| `lead_in_type` | text, `none`/`line`/`arc` | Lead-in típus |
| `lead_in_length_mm` | `numeric(10,3)` | Hossz |
| `lead_in_radius_mm` | `numeric(10,3)` | Ívsugár |
| `lead_out_type` | text, `none`/`line`/`arc` | Lead-out típus |
| `lead_out_length_mm` | `numeric(10,3)` | Hossz |
| `lead_out_radius_mm` | `numeric(10,3)` | Ívsugár |
| `entry_side_policy` | text | Belépés oldal policy (default `auto`) |
| `min/max_contour_length_mm` | `numeric(10,3)` | Kontúrhossz-szűrő |
| `pierce_count` | int | Lyukasztások száma |
| `cut_direction` | text, default `cw` | Vágásirány |
| `sort_order` | int | Rule sorrend |
| `enabled` | bool | Aktiválás |
| `metadata_jsonb` | jsonb | Szabadon bővülő kiegészítés |

Owner-scope öröklődik a `cut_rule_set_id → cut_rule_sets.owner_user_id`
láncon keresztül, RLS az `exists(...)` mintára.

### 2.5 Lap geometria

Migráció: [20260311000000_h0_e2_t5_sheet_definition_revision_es_project_input_alapok.sql](../../supabase/migrations/20260311000000_h0_e2_t5_sheet_definition_revision_es_project_input_alapok.sql)

Nem „gép” paraméter szigorú értelemben, de a solver szempontjából
elválaszthatatlan:

- `app.sheet_definitions` — owner + `code` + `current_revision_id`.
- `app.sheet_revisions` — `width_mm`, `height_mm`, `grain_direction`,
  `lifecycle`, `source_label`, `source_checksum_sha256`, `revision_no`.
- `app.project_sheet_inputs` — projekt ↔ sheet_revision binding,
  `required_qty`, `placement_priority` (0-100), `is_default`.

### 2.6 Projekt-szintű default-ok

Migráció: [20260310223000_h0_e2_t2_profiles_projects_project_settings.sql](../../supabase/migrations/20260310223000_h0_e2_t2_profiles_projects_project_settings.sql)

`app.project_settings` csak:
- `default_units` (check: `mm`, `cm`, `m`, `in`),
- `default_rotation_step_deg` (`> 0, <= 360`),
- `notes`.

## 3. Adatfolyam: hogyan jutnak el a paraméterek a solverig és a postprocesszig

```
 ┌───────────────────────────────────────────────────────────────────┐
 │                        UI (frontend/src/)                          │
 │  NewRunPage.tsx — csak: spacing_mm, margin_mm                      │
 │  (kerf/rotation/machine/material UI nincs)                         │
 └───────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
 ┌───────────────────────────────────────────────────────────────────┐
 │              DB truth-rétegek (owner-scoped, RLS-elt)              │
 │                                                                    │
 │  project_technology_setups ─── nesting runtime (kerf/spacing/      │
 │                                margin/rotation/thickness)          │
 │                                                                    │
 │  manufacturing_profile_versions ─── gyártási kontextus             │
 │    └─ config_jsonb (jsonb)                                         │
 │    └─ active_postprocessor_profile_version_id ─┐                   │
 │                                                 ▼                   │
 │                             postprocessor_profile_versions         │
 │                              ├─ adapter_key                        │
 │                              ├─ output_format                      │
 │                              └─ config_jsonb (jsonb, bounded)      │
 │                                                                    │
 │  cut_rule_sets + cut_contour_rules ─── per-kontúr vágási params    │
 └───────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
 ┌───────────────────────────────────────────────────────────────────┐
 │     api/services/run_snapshot_builder.py                          │
 │                                                                    │
 │  _select_technology_setup()      — L194-218                        │
 │  _build_manufacturing_manifest() — L558+                           │
 │                                                                    │
 │  Kimenet: nesting_run_snapshots sor, immutable:                    │
 │    ├─ technology_manifest_jsonb    (L750-762)                      │
 │    │    machine_code, material_code, thickness_mm, kerf_mm,        │
 │    │    spacing_mm, margin_mm, rotation_step_deg, ...              │
 │    ├─ solver_config_jsonb          (L766-780)                      │
 │    │    kerf_mm, spacing_mm, margin_mm, rotation_step_deg,         │
 │    │    allow_free_rotation, time_limit_s, quality_profile, ...    │
 │    └─ manufacturing_manifest_jsonb  (H2-E5-T2 selection copy)      │
 └───────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
 ┌───────────────────────────────────────────────────────────────────┐
 │                          Worker réteg                              │
 │                                                                    │
 │  worker/engine_adapter_input.py:305-357                            │
 │    solver_config_jsonb → sheet.kerf_mm/spacing_mm/margin_mm        │
 │    solver_config_jsonb.rotation_step_deg → allowed_rotations_deg   │
 │                                                                    │
 │  worker/main.py:356-357, 1054-1096                                 │
 │    coalesce fallback: spacing=2.0, margin=5.0 (hardcoded)          │
 └───────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
 ┌───────────────────────────────────────────────────────────────────┐
 │               Manufacturing plan és export rétegek                 │
 │                                                                    │
 │  api/services/manufacturing_plan_builder.py                        │
 │   → run_manufacturing_plans + run_manufacturing_contours           │
 │        (per-run perszisztált plan + kontúr, cut_rules eredmény)    │
 │                                                                    │
 │  api/services/machine_neutral_exporter.py                          │
 │   → run_artifacts (kind=manufacturing_plan_json)                   │
 │                                                                    │
 │  api/services/machine_specific_adapter.py                          │
 │   → run_artifacts (kind=machine_program, Hypertherm / QtPlasmaC)   │
 └───────────────────────────────────────────────────────────────────┘
```

### Kulcshelyek a kódban

- [api/services/run_snapshot_builder.py:194-218](../../api/services/run_snapshot_builder.py#L194-L218)
  — technology setup kiválasztás (approved, `is_default` preferálva).
- [api/services/run_snapshot_builder.py:720-780](../../api/services/run_snapshot_builder.py#L720-L780)
  — `technology_manifest_jsonb` + `solver_config_jsonb` előállítás.
- [worker/engine_adapter_input.py:313-357](../../worker/engine_adapter_input.py#L313-L357)
  — snapshot solver_config → engine v2 input.
- [worker/main.py:356-357](../../worker/main.py#L356-L357),
  [1054-1096](../../worker/main.py#L1054-L1096) — fallback default értékek.
- [api/services/machine_specific_adapter.py:895-970](../../api/services/machine_specific_adapter.py#L895-L970)
  — config_jsonb betöltése + boundary validáció.

## 4. Megállapítások

### 4.1 Erősségek

1. **Típusos, validált runtime paraméterek.** A `kerf_mm`, `spacing_mm`,
   `margin_mm`, `thickness_mm`, `rotation_step_deg` mind `numeric(10,3)`
   vagy `integer`, check-constraintekkel (`>= 0`, `> 0`, intervallumok).
   Nem JSONB-be vannak szórva, ahol már nehéz lenne sémát kikényszeríteni.
2. **Immutable run snapshot.** A `run_snapshot_builder` beforrasztja a
   run indulásakor aktuális értékeket, így a run auditálható és
   reprodukálható a későbbi profilváltozásoktól függetlenül.
3. **Domain-szeparáció.** Nesting runtime (kerf/spacing/margin) ↔
   manufacturing kontextus (machine/material/thickness) ↔ postprocess
   output (adapter_key/output_format) ↔ per-kontúr vágási szabályok —
   nem keverednek össze egy nagy JSON-be.
4. **Verziózott profilok.** Mind a manufacturing, mind a postprocessor,
   mind a cut rule set oldalon `version_no` + `lifecycle` van, így
   változástörténet megmarad.
5. **Szűkített `config_jsonb` határ.** A postprocessor `config_jsonb`
   tartalmát nem a séma, hanem a kód (`_validate_config_boundary`)
   kényszeríti ki explicit whitelisttel — ez megakadályozza, hogy az
   adapter határán kívül szivárogjanak be szabályok.

### 4.2 Gyengeségek / megfigyelések

1. **Nincs `machines` master katalógus.** A `machine_code` négy külön
   táblában (`technology_presets`, `project_technology_setups`,
   `manufacturing_profile_versions`, `cut_rule_sets`) szabad szöveg,
   FK nélkül. Új gép felvitelekor a konvenciót manuálisan kell
   tartani; elírás csendes eltérést okozhat. Hasonló a `material_code`.
2. **UI gyenge a paraméterkezelésben.** A
   [frontend/src/pages/NewRunPage.tsx:45-46](../../frontend/src/pages/NewRunPage.tsx#L45-L46)
   csak `spacing` és `margin` mezőt mutat. Nincs oldal:
    - technology setup szerkesztésére,
    - manufacturing profile + version kezelésére,
    - postprocessor profile kezelésére,
    - cut rule set / cut contour rules kezelésére.
   A teljes profil-adminisztráció csak API-n keresztül működik.
3. **Hardcoded worker default.** [worker/main.py:356-357](../../worker/main.py#L356-L357)
   `coalesce(..., 2.0)` és `coalesce(..., 5.0)`
   spacing/margin fallback. Ez rejtetten elfedheti, ha a snapshot
   rossz adattal indult, és „némán" beépül egy nem projektspecifikus
   default.
4. **Párhuzamos `config_jsonb` szemantika.**
   `manufacturing_profile_versions.config_jsonb` és
   `postprocessor_profile_versions.config_jsonb` két külön, dokumentáltan
   szétválasztott tartalmi határt hordoz, de a séma szintjén
   megkülönböztethetetlen `jsonb default '{}'::jsonb`. A határt csak
   a kód (`machine_specific_adapter._validate_config_boundary`) őrzi.
5. **Nincs validálás a `machine_code` / `material_code` referenciakonzisztenciára.**
   Egy projekt `project_technology_setups.machine_code` értéke
   „hypertherm-edge-connect" lehet, míg a hozzá rendelt
   `manufacturing_profile_versions.machine_code` „hypertherm_edge_connect"
   — tipográfiai eltérés nem bukik el a rendszerből.
6. **`technology_presets` → `project_technology_setups` másolás
   állapotfixálása.** A setup mezőket lemásolja a preset-ből, de
   nem tárolja, melyik preset-verzióból származik — ha a preset
   később módosul, nem látszik a divergencia.
7. **A `cut_rule_sets.machine_code` / `material_code` / `thickness_mm`
   nullable.** Ez rugalmas matchinget enged (fallback általánosabb rule
   setre), de az egyezés-sorrendet a dokumentáció alapján kell
   érvényesíteni — nem sémával, hanem matcher-kódban.

### 4.3 Hol nincs gépparaméter

A `run_strategy_profile_versions`, `scoring_profile_versions` és
`run_batches` NEM tárolnak gépparamétereket — ezek kimondottan
nesting stratégia / értékelés / batch-futtatás mentén bontanak, nem
gép-kontextusban.

## 5. Javaslatok

1. **Vezessünk be egy `app.machines` katalógust.** Egyszerű tábla
   (`id`, `owner_user_id`, `code`, `display_name`, `category`, …) és
   FK-ra kényszeríteni a `machine_code` mezőket a négy érintett táblában.
   Ugyanígy érdemes lehet `app.materials` is.
2. **Projekt-szintű UI a teljes paraméter-stackhez.** A jelenlegi
   wizard csak spacing/margin-t kezel; a technology setup, manufacturing
   selection, postprocessor profile kiválasztás mind az API-ra tolja a
   terhet, ami operatívan törékeny. Egy „Project manufacturing
   configuration" oldal felszámolná ezt.
3. **Worker hardcoded default eltávolítása vagy explicit log.** A
   `coalesce(..., 2.0/5.0)` helyett vagy legyen hard-fail (ha a
   snapshotban nincs kerf/spacing/margin, akkor hiba, mert a solver
   inputja nem determinisztikus), vagy legalább strukturált
   figyelmeztetés a run logjában.
4. **`config_jsonb` séma-formalizálás.** A jelenlegi kód-oldali
   whitelist helyett érdemes lenne JSON Schema vagy pydantic modellt
   perzisztálni (pl. `schema_version`-höz kötve) és az insert előtt
   validálni. Így a határ deklaratív, és támogatást ad UI-szintű
   form-generáláshoz is.
5. **Technology preset-setup lineage.** Érdemes eltárolni, melyik
   preset-rev(verzió)-ből lett másolva a setup, hogy divergencia
   detektálható legyen.

## 6. Kapcsolódó dokumentumok

- [docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md](../web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md)
- [docs/web_platform/roadmap/dxf_nesting_platform_h1_reszletes.md](../web_platform/roadmap/dxf_nesting_platform_h1_reszletes.md)
- [docs/solver_io_contract.md](../solver_io_contract.md)
- [docs/nesting_engine/](../nesting_engine/)
- [docs/sparrow_modul/](../sparrow_modul/)
