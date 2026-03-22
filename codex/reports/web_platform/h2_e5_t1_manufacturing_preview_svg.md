# Report — h2_e5_t1_manufacturing_preview_svg

**Status:** PASS

## 1) Meta

* **Task slug:** `h2_e5_t1_manufacturing_preview_svg`
* **Kapcsolodo canvas:** `canvases/web_platform/h2_e5_t1_manufacturing_preview_svg.md`
* **Kapcsolodo goal YAML:** `codex/goals/canvases/web_platform/fill_canvas_h2_e5_t1_manufacturing_preview_svg.yaml`
* **Futtas datuma:** 2026-03-22
* **Branch / commit:** main
* **Fokusz terulet:** Schema | Service | Scripts

## 2) Scope

### 2.1 Cel
- `manufacturing_preview_svg` artifact kind bevezetese + legacy bridge frissites.
- Dedikalt manufacturing preview generator service, amely persisted plan truth + manufacturing_canonical derivative alapjan per-sheet preview SVG-t general.
- A preview gyartasi meta-informaciot hordoz (entry/lead/cut-order), nem csak layoutot.
- Task-specifikus smoke script az invariansok bizonyitasara.

### 2.2 Nem-cel (explicit)
- Postprocessor profile/version aktivacio.
- Machine-neutral vagy machine-specific export artifact.
- H1 `sheet_svg` viewer artifact ujratervezese.
- `api/routes/runs.py` nagy redesignja vagy uj dedikalt preview endpoint.
- Worker automatikus bekotes.
- Frontend redesign.

## 3) Valtozasok osszefoglaloja

### 3.1 Erintett fajlok

* **Migration:**
  * `supabase/migrations/20260322033000_h2_e5_t1_manufacturing_preview_svg.sql`
* **Service:**
  * `api/services/manufacturing_preview_generator.py`
* **Scripts:**
  * `scripts/smoke_h2_e5_t1_manufacturing_preview_svg.py`
* **Codex artefaktok:**
  * `canvases/web_platform/h2_e5_t1_manufacturing_preview_svg.md`
  * `codex/goals/canvases/web_platform/fill_canvas_h2_e5_t1_manufacturing_preview_svg.yaml`
  * `codex/prompts/web_platform/h2_e5_t1_manufacturing_preview_svg/run.md`
  * `codex/codex_checklist/web_platform/h2_e5_t1_manufacturing_preview_svg.md`
  * `codex/reports/web_platform/h2_e5_t1_manufacturing_preview_svg.md`

### 3.2 Miert valtoztak?

* **Migration:** Bevezeti a `manufacturing_preview_svg` artifact kind enum erteket es frissiti a legacy `legacy_artifact_type_to_kind` / `artifact_kind_to_legacy_type` bridge fuggvenyeket, hogy a generic artifact list + signed URL flow konzisztensen kezelje az uj tipust.
* **Service:** Implementalja a manufacturing preview generatort, amely persisted plan truth (run_manufacturing_plans + run_manufacturing_contours) es manufacturing_canonical derivative contour geometria alapjan per-sheet preview SVG-ket general. A render tartalmazza: contour pathokat outer/inner megkulonboztetest, entry markert, lead-in/lead-out jelolest, cut-order review infot.
* **Smoke:** 39 teszteset bizonyitja a fo invariansokat (artifact letrejon, meta-info jelen van, manufacturing_canonical geometry-t hasznal, outer/inner vizualis elkuulonitest, idempotens, nincs write korabbi truthba, nincs export/postprocess).

## 4) Verifikacio

### 4.1 Kotelezo parancs
* `./scripts/verify.sh --report codex/reports/web_platform/h2_e5_t1_manufacturing_preview_svg.md` -> PASS (218s, 56/56 pytest, mypy 0 issues)

### 4.2 Opcionalis parancsok
* `python3 -m py_compile api/services/manufacturing_preview_generator.py scripts/smoke_h2_e5_t1_manufacturing_preview_svg.py` -> PASS
* `python3 scripts/smoke_h2_e5_t1_manufacturing_preview_svg.py` -> PASS (39/39)

### 4.4 Automatikus blokk

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-03-22T17:20:23+01:00 → 2026-03-22T17:24:01+01:00 (218s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/h2_e5_t1_manufacturing_preview_svg.verify.log`
- git: `main@87cbe83`
- módosított fájlok (git status): 9

**git status --porcelain (preview)**

```text
?? api/services/manufacturing_preview_generator.py
?? canvases/web_platform/h2_e5_t1_manufacturing_preview_svg.md
?? codex/codex_checklist/web_platform/h2_e5_t1_manufacturing_preview_svg.md
?? codex/goals/canvases/web_platform/fill_canvas_h2_e5_t1_manufacturing_preview_svg.yaml
?? codex/prompts/web_platform/h2_e5_t1_manufacturing_preview_svg/
?? codex/reports/web_platform/h2_e5_t1_manufacturing_preview_svg.md
?? codex/reports/web_platform/h2_e5_t1_manufacturing_preview_svg.verify.log
?? scripts/smoke_h2_e5_t1_manufacturing_preview_svg.py
?? supabase/migrations/20260322033000_h2_e5_t1_manufacturing_preview_svg.sql
```

<!-- AUTO_VERIFY_END -->

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo teszt/ellenorzes |
| -------- | ------: | ------------------------ | ---------- | --------------------------- |
| #1 `manufacturing_preview_svg` artifact kind letezik | PASS | `supabase/migrations/20260322033000_h2_e5_t1_manufacturing_preview_svg.sql:L11-L24` | ALTER TYPE app.artifact_kind ADD VALUE 'manufacturing_preview_svg' | Migration |
| #2 Bridge fuggvenyek kezelik | PASS | `supabase/migrations/20260322033000_h2_e5_t1_manufacturing_preview_svg.sql:L28-L66` | legacy_artifact_type_to_kind es artifact_kind_to_legacy_type frissitve | Migration |
| #3 Dedikalt preview generator service | PASS | `api/services/manufacturing_preview_generator.py:L74-L199` | generate_manufacturing_preview() public entry point | Smoke Test 1 |
| #4 Generator persisted plan truth + mfg_canonical alapjan dolgozik | PASS | `api/services/manufacturing_preview_generator.py:L102-L117` | Plans + contours + derivatives betoltese | Smoke Test 3 |
| #5 Preview gyartasi meta-informaciot hordoz | PASS | `api/services/manufacturing_preview_generator.py:L503-L555` | SVG render: entry marker, lead-in/out, cut-order label, contour-kind data attribs | Smoke Test 2 |
| #6 Artifact canonical run-artifacts bucketbe kerul | PASS | `api/services/manufacturing_preview_generator.py:L64` | _STORAGE_BUCKET = "run-artifacts" | Smoke Test 12 |
| #7 Filename + metadata policy stabil | PASS | `api/services/manufacturing_preview_generator.py:L157-L168` | Deterministic filename, hash-based storage path, required metadata fields | Smoke Test 11 |
| #8 Artifact persistence idempotens | PASS | `api/services/manufacturing_preview_generator.py:L140-L143` | delete_existing_preview_artifacts() before insert | Smoke Test 5 |
| #9 Nem ir vissza korabbi truth tablaba | PASS | `api/services/manufacturing_preview_generator.py:L17-L19` | Docstring boundary; only writes run_artifacts | Smoke Test 6 |
| #10 Nem nyit export/postprocessor/frontend scope-ot | PASS | `api/services/manufacturing_preview_generator.py:L20-L22` | No postprocess/export/frontend | Smoke Test 7 |
| #11 Task-specifikus smoke script | PASS | `scripts/smoke_h2_e5_t1_manufacturing_preview_svg.py` | 39 teszteset, 12 test szekcios | Smoke PASS (39/39) |
| #12 Checklist + report evidence-alapon kitoltve | PASS | Jelen dokumentum + checklist | Evidence matrix es DoD kipipalva | N/A |
| #13 verify.sh PASS | PASS | `codex/reports/web_platform/h2_e5_t1_manufacturing_preview_svg.verify.log` | PASS, 56/56 pytest, mypy 0 issues, 218s | `./scripts/verify.sh --report ...` |

## 6) IO contract / mintak
Nem relevans — nincs Sparrow IO vagy POC minta valtozas.

## 7) Doksi szinkron
Nem relevans — ez a task kizarolag implementacios artefaktokat szallit.

## 8) Advisory notes

1. A preview a persisted truth-bol epul: a `run_manufacturing_plans`, `run_manufacturing_contours` es `manufacturing_canonical` derivative contour geometria az egyetlen forras. A H1 `sheet_svg` minta nem forras.
2. Az `manufacturing_preview_svg` artifact kind az enum bovitese `ALTER TYPE ... ADD VALUE` segitsegevel tortenik. A bridge fuggvenyek (`legacy_artifact_type_to_kind`, `artifact_kind_to_legacy_type`) frissulnek.
3. A deterministic SVG render hash-alapu canonical storage path-ot hasznal (`projects/{project_id}/runs/{run_id}/manufacturing_preview_svg/{digest}.svg`). A metadata policy tartalmazza: `filename`, `sheet_index`, `size_bytes`, `content_sha256`, `legacy_artifact_type`, `preview_scope`.
4. Ez a task preview scope-ban marad: nem szallit machine-neutral exportot, postprocessor adaptert, worker auto-behuzast vagy preview-specifikus frontend oldalt.
5. Az SVG nem valodi toolpath/machine-ready geometria — gepfuggetlen review preview.

## 9) Follow-ups
- H2-E5-T2: Postprocessor profile/version domain aktivacio.
- H2-E5-T3: Machine-neutral exporter (manufacturing planbol generikus export).
- Kesobbi task: preview-specifikus frontend viewer, ha szukseges.
