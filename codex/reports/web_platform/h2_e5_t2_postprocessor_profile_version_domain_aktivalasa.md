# Report — h2_e5_t2_postprocessor_profile_version_domain_aktivalasa

**Status:** PASS

## 1) Meta

* **Task slug:** `h2_e5_t2_postprocessor_profile_version_domain_aktivalasa`
* **Kapcsolodo canvas:** `canvases/web_platform/h2_e5_t2_postprocessor_profile_version_domain_aktivalasa.md`
* **Kapcsolodo goal YAML:** `codex/goals/canvases/web_platform/fill_canvas_h2_e5_t2_postprocessor_profile_version_domain_aktivalasa.yaml`
* **Futtas datuma:** 2026-03-22
* **Branch / commit:** main
* **Fokusz terulet:** Schema | Service | Routes | Scripts

## 2) Scope

### 2.1 Cel
- Postprocessor profile/version domain minimalis, de valos aktiválása owner-scoped truth-retegkent.
- Owner-scoped CRUD service + route a postprocessor profile es version domainhez.
- A `manufacturing_profile_versions` bovitese nullable `active_postprocessor_profile_version_id` mezovel.
- Owner-konzisztencia biztositasa a manufacturing -> postprocessor refnel.
- A `project_manufacturing_selection` read-path frissitese a postprocessor ref visszaadasaval.
- A `run_snapshot_builder` frissitese valos postprocess selection snapshotolassal.
- Task-specifikus smoke script az invariansok bizonyitasara.

### 2.2 Nem-cel (explicit)
- Machine-neutral exporter.
- Machine-specific adapter.
- Machine-ready artifact / export bundle.
- Postprocessor config alkalmazas a toolpathra.
- Uj project-level postprocess selection tabla.
- Nem letezo `machine_catalog` / `material_catalog` catalog-FK vilag bevezetese.

## 3) Valtozasok osszefoglaloja

### 3.1 Erintett fajlok

* **Migration:**
  * `supabase/migrations/20260322040000_h2_e5_t2_postprocessor_profile_version_domain_aktivalasa.sql`
* **Service:**
  * `api/services/postprocessor_profiles.py`
* **Route:**
  * `api/routes/postprocessor_profiles.py`
* **App registration:**
  * `api/main.py`
* **Selection read-path + snapshot:**
  * `api/services/project_manufacturing_selection.py`
  * `api/routes/project_manufacturing_selection.py`
  * `api/services/run_snapshot_builder.py`
* **Scripts:**
  * `scripts/smoke_h2_e5_t2_postprocessor_profile_version_domain_aktivalasa.py`
* **Codex artefaktok:**
  * `canvases/web_platform/h2_e5_t2_postprocessor_profile_version_domain_aktivalasa.md`
  * `codex/goals/canvases/web_platform/fill_canvas_h2_e5_t2_postprocessor_profile_version_domain_aktivalasa.yaml`
  * `codex/prompts/web_platform/h2_e5_t2_postprocessor_profile_version_domain_aktivalasa/run.md`
  * `codex/codex_checklist/web_platform/h2_e5_t2_postprocessor_profile_version_domain_aktivalasa.md`
  * `codex/reports/web_platform/h2_e5_t2_postprocessor_profile_version_domain_aktivalasa.md`

### 3.2 Miert valtoztak?

* **Migration:** Bevezeti az `app.postprocessor_profiles` (L11) es `app.postprocessor_profile_versions` (L41) owner-scoped truth tablakat, boviti a `manufacturing_profile_versions`-t nullable `active_postprocessor_profile_version_id` mezovel (L95) owner-konzisztencia constrainttel (L73).
* **Service + Route:** Owner-scoped CRUD a postprocessor profile es nested version domainhez, a meglevo H2 CRUD mintakat kovetve (10 endpoint, 10 service fuggveny).
* **Selection + Snapshot:** A read-path visszaadja a postprocessor refet; a snapshot builder valos postprocess selectiont snapshotol aktiv ref eseten.
* **Smoke:** 42/42 assertion bizonyitja a CRUD / owner-boundary / snapshot invariansokat.

## 4) Verifikacio

### 4.1 Kotelezo parancs
* `./scripts/verify.sh --report codex/reports/web_platform/h2_e5_t2_postprocessor_profile_version_domain_aktivalasa.md` -> PASS

### 4.2 Opcionalis parancsok
* `python3 -m py_compile api/services/postprocessor_profiles.py api/routes/postprocessor_profiles.py scripts/smoke_h2_e5_t2_postprocessor_profile_version_domain_aktivalasa.py` -> PASS
* `python3 scripts/smoke_h2_e5_t2_postprocessor_profile_version_domain_aktivalasa.py` -> PASS (42/42)

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo teszt/ellenorzes |
| -------- | ------: | ------------------------ | ---------- | --------------------------- |
| #1 Letezik `app.postprocessor_profiles` | PASS | `supabase/migrations/...sql:11` | `create table if not exists app.postprocessor_profiles` owner-scoped, RLS-sel | smoke 1: profile CRUD (8 assert) |
| #2 Letezik `app.postprocessor_profile_versions` | PASS | `supabase/migrations/...sql:41` | `create table if not exists app.postprocessor_profile_versions` owner-scoped, verziozott | smoke 2: version CRUD (7 assert) |
| #3 Owner-scoped CRUD service + route | PASS | `api/services/postprocessor_profiles.py:71-460`, `api/routes/postprocessor_profiles.py:143-370` | 10 service fn + 10 route endpoint, owner_user_id szures mindenhol | smoke 1+2+3 (19 assert) |
| #4 `manufacturing_profile_versions` nullable `active_postprocessor_profile_version_id` | PASS | `supabase/migrations/...sql:95` | `add column if not exists active_postprocessor_profile_version_id uuid` nullable FK | smoke 5: aktiv ref snapshot |
| #5 Manufacturing -> postprocessor owner-konzisztens | PASS | `supabase/migrations/...sql:69-76` | `fk_postprocessor_profile_versions_profile_owner` composite FK `(id, owner_user_id)` | smoke 3: owner boundary (4 assert) |
| #6 Selection read-path visszaadja postprocessor refet | PASS | `api/services/project_manufacturing_selection.py:385,399`, `api/routes/project_manufacturing_selection.py:38,84-90,106` | GET response tartalmazza `active_postprocessor_profile_version_id` | smoke 5: ppv id snapshotted |
| #7 Snapshot builder valos postprocess selection | PASS | `api/services/run_snapshot_builder.py:612-655` | `_build_manufacturing_manifest` feloldja az aktiv postprocessor refet, snapshotol meta-t | smoke 5: 7 assert |
| #8 `includes_postprocess` csak aktiv ref eseten true | PASS | `api/services/run_snapshot_builder.py:760` | `includes_postprocess = bool(manufacturing_manifest_jsonb.get("postprocess_selection_present"))` | smoke 4+5+6: false/true/false |
| #9 Nincs export / adapter / machine-ready scope | PASS | source scan | `machine_ready`, `export_bundle`, `adapter_run` nem talalhato | smoke 7: 5 assert |
| #10 Nincs nem letezo catalog-FK vilag | PASS | migration + source scan | `machine_catalog`, `material_catalog` nem talalhato | smoke 8: 4 assert |
| #11 Task-specifikus smoke script | PASS | `scripts/smoke_h2_e5_t2_postprocessor_profile_version_domain_aktivalasa.py` | 9 test csoport, 42/42 PASS | smoke futtas output |
| #12 Checklist es report evidence-alapon | PASS | `codex/codex_checklist/.../h2_e5_t2_...md`, `codex/reports/.../h2_e5_t2_...md` | Minden DoD pont evidence-cel kitoltve | jelen report |
| #13 verify.sh PASS | PASS | verify.sh output | `./scripts/verify.sh --report ...` PASS | verify.sh futtas |

## 8) Advisory notes

- A postprocessor domain minimalis truth-reteg: profil + verzio + owner-scoped CRUD. Nincs config alkalmazas, nincs export pipeline.
- A manufacturing -> postprocessor ref nullable, tehat a meglevo manufacturing flow teljesen valtozatlanul mukodik, ha nincs postprocessor kivalasztva.
- A snapshot builder csak aktiv (`is_active=true`) postprocessor verziot snapshotol; inaktiv ref eseten `postprocess_selection_present=false`.

## 9) Follow-ups

- H2-E6+ scope: postprocessor config alkalmazas a toolpathra (adapter / exporter).
- H2-E6+ scope: project-level postprocess selection tabla, ha kulon project-szintu kivalasztas kell.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-03-22T18:12:13+01:00 → 2026-03-22T18:15:55+01:00 (222s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/h2_e5_t2_postprocessor_profile_version_domain_aktivalasa.verify.log`
- git: `main@2795f93`
- módosított fájlok (git status): 14

**git diff --stat**

```text
 api/main.py                                     |  2 +
 api/routes/project_manufacturing_selection.py   | 11 +++++
 api/services/project_manufacturing_selection.py | 30 ++++++++++++-
 api/services/run_snapshot_builder.py            | 57 ++++++++++++++++++++++---
 4 files changed, 93 insertions(+), 7 deletions(-)
```

**git status --porcelain (preview)**

```text
 M api/main.py
 M api/routes/project_manufacturing_selection.py
 M api/services/project_manufacturing_selection.py
 M api/services/run_snapshot_builder.py
?? api/routes/postprocessor_profiles.py
?? api/services/postprocessor_profiles.py
?? canvases/web_platform/h2_e5_t2_postprocessor_profile_version_domain_aktivalasa.md
?? codex/codex_checklist/web_platform/h2_e5_t2_postprocessor_profile_version_domain_aktivalasa.md
?? codex/goals/canvases/web_platform/fill_canvas_h2_e5_t2_postprocessor_profile_version_domain_aktivalasa.yaml
?? codex/prompts/web_platform/h2_e5_t2_postprocessor_profile_version_domain_aktivalasa/
?? codex/reports/web_platform/h2_e5_t2_postprocessor_profile_version_domain_aktivalasa.md
?? codex/reports/web_platform/h2_e5_t2_postprocessor_profile_version_domain_aktivalasa.verify.log
?? scripts/smoke_h2_e5_t2_postprocessor_profile_version_domain_aktivalasa.py
?? supabase/migrations/20260322040000_h2_e5_t2_postprocessor_profile_version_domain_aktivalasa.sql
```

<!-- AUTO_VERIFY_END -->
