PASS_WITH_NOTES

## 1) Meta
- Task slug: `h1_e1_t2_file_hash_es_metadata_kezeles`
- Kapcsolodo canvas: `canvases/web_platform/h1_e1_t2_file_hash_es_metadata_kezeles.md`
- Kapcsolodo goal YAML: `codex/goals/canvases/web_platform/fill_canvas_h1_e1_t2_file_hash_es_metadata_kezeles.yaml`
- Futas datuma: `2026-03-15`
- Branch / commit: `main @ 9805f04 (dirty working tree)`
- Fokusz terulet: `API + Ingest metadata + Smoke`

## 2) Scope

### 2.1 Cel
- A `complete_upload` metadata truth server-side hardeningje H0 `app.file_objects` mezokre.
- A kanonikus source bucket rakeroszakolasa a DB-truth-ra kliens bucket override helyett.
- Szerveroldali `file_name`, `byte_size`, `sha256`, `mime_type` eloallitas a tenyleges storage objektumbol.
- Sikertelen storage objektum letoltes eseten metadata insert blokkolasa.
- Task-specifikus smoke evidence hozzaadasa metadata override tampering es missing-object scenariora.

### 2.2 Nem-cel
- Uj domain migracio.
- Geometry import pipeline (`geometry_revisions`, derivativak) bekotese.
- Duplicate policy/merge workflow teljes implementalasa.
- Run/snapshot/worker retegek funkcionalis bovites.

## 3) Valtozasok osszefoglalasa

### 3.1 Erintett fajlok
- **Task artefaktok:**
  - `canvases/web_platform/h1_e1_t2_file_hash_es_metadata_kezeles.md`
  - `codex/goals/canvases/web_platform/fill_canvas_h1_e1_t2_file_hash_es_metadata_kezeles.yaml`
  - `codex/prompts/web_platform/h1_e1_t2_file_hash_es_metadata_kezeles/run.md`
  - `codex/codex_checklist/web_platform/h1_e1_t2_file_hash_es_metadata_kezeles.md`
  - `codex/reports/web_platform/h1_e1_t2_file_hash_es_metadata_kezeles.md`
- **API / service:**
  - `api/services/file_ingest_metadata.py`
  - `api/routes/files.py`
  - `api/services/dxf_validation.py`
  - `api/config.py`
- **Smoke:**
  - `scripts/smoke_h1_e1_t2_file_hash_es_metadata_kezeles.py`

### 3.2 Miert valtoztak?
- Az upload complete flow eddig kliens metadata mezoket tudott DB truth-kent elfogadni (`storage_bucket`, `byte_size`, `mime_type`, `sha256`, `file_name`), ami ingest oldalon tamperelheto volt.
- A valtozasok celja, hogy a forrasobjektum metadataja mindig a tenyleges storage objektumbol legyen szamolva, es a source bucket kanonikus maradjon.
- A smoke script endpoint-szinten bizonyitja a metadata-hardening viselkedest.

## 4) Verifikacio (How tested)

### 4.1 Kotelezo parancs
- `./scripts/verify.sh --report codex/reports/web_platform/h1_e1_t2_file_hash_es_metadata_kezeles.md` -> PASS

### 4.2 Opcionális, feladatfuggo ellenorzes
- `python3 -m py_compile api/services/file_ingest_metadata.py api/routes/files.py api/services/dxf_validation.py api/config.py scripts/smoke_h1_e1_t2_file_hash_es_metadata_kezeles.py` -> PASS
- `python3 scripts/smoke_h1_e1_t2_file_hash_es_metadata_kezeles.py` -> PASS

### 4.3 Ha valami kimaradt
- Nincs kihagyott kotelezo ellenorzes.

## 5) DoD -> Evidence Matrix

| DoD pont | Statusz | Bizonyitek (path + line) | Magyarazat | Kapcsolodo ellenorzes |
| --- | --- | --- | --- | --- |
| A `complete_upload` a DB-be irt `storage_bucket` erteket nem a kliens requestbol veszi, hanem a kanonikus source bucketbol. | PASS | `api/routes/files.py:207`; `api/routes/files.py:228` | A route explicit `settings.storage_bucket` erteket hasznal, a kliens `storage_bucket` mezo csak backward-compat input marad. | `python3 scripts/smoke_h1_e1_t2_file_hash_es_metadata_kezeles.py` |
| A `complete_upload` a DB-be irt `file_name` erteket a kanonikus `storage_path` basename-jebol kepzi. | PASS | `api/services/file_ingest_metadata.py:28`; `api/routes/files.py:211`; `api/routes/files.py:230` | A filename a `storage_path` basename-bol kepzodik, nem kliens inputbol. | `python3 scripts/smoke_h1_e1_t2_file_hash_es_metadata_kezeles.py` |
| A `complete_upload` szerveroldalon szamolja a `byte_size` erteket a tenyleges storage objektumbol. | PASS | `api/services/file_ingest_metadata.py:91`; `api/services/file_ingest_metadata.py:98`; `api/routes/files.py:233` | `byte_size` a letoltott blob hosszabol jon. | `python3 scripts/smoke_h1_e1_t2_file_hash_es_metadata_kezeles.py` |
| A `complete_upload` szerveroldalon szamolja a `sha256` erteket a tenyleges storage objektumbol. | PASS | `api/services/file_ingest_metadata.py:106`; `api/routes/files.py:234` | A hash `hashlib.sha256(blob).hexdigest()` szerint kerul DB-be. | `python3 scripts/smoke_h1_e1_t2_file_hash_es_metadata_kezeles.py` |
| A `complete_upload` szerveroldalon allitja elo a `mime_type` truth-ot determinisztikus szaballyal. | PASS | `api/services/file_ingest_metadata.py:10`; `api/services/file_ingest_metadata.py:40`; `api/routes/files.py:231` | A mime type extension map + `mimetypes` fallback + `application/octet-stream` fallback szerint jon. | `python3 scripts/smoke_h1_e1_t2_file_hash_es_metadata_kezeles.py` |
| Sikertelen object letoltes eseten nem jon letre felrevezeto `app.file_objects` rekord. | PASS | `api/services/file_ingest_metadata.py:66`; `api/routes/files.py:215`; `api/routes/files.py:223`; `scripts/smoke_h1_e1_t2_file_hash_es_metadata_kezeles.py:278` | Letoltesi hiba eseten HTTP 400, insert nem fut le. A smoke explicit ellenorzi, hogy missing object eseten nincs uj sor. | `python3 scripts/smoke_h1_e1_t2_file_hash_es_metadata_kezeles.py` |
| A route legfeljebb backward-compat request parsing miatt fogad legacy metadata mezoket, de azok nem irjak felul a szerver truth-ot. | PASS | `api/routes/files.py:38`; `api/routes/files.py:44`; `api/routes/files.py:49`; `api/routes/files.py:51`; `api/routes/files.py:206`; `api/routes/files.py:215` | A model tartja a legacy inputokat, de payloadba csak a szerveroldalrol szamolt metadata kerul. | `python3 scripts/smoke_h1_e1_t2_file_hash_es_metadata_kezeles.py` |
| Keszul task-specifikus smoke script, amely bizonyitja, hogy a hamis kliensoldali metadata ellenere a szerveroldali truth kerul a DB-be. | PASS | `scripts/smoke_h1_e1_t2_file_hash_es_metadata_kezeles.py:1`; `scripts/smoke_h1_e1_t2_file_hash_es_metadata_kezeles.py:213`; `scripts/smoke_h1_e1_t2_file_hash_es_metadata_kezeles.py:248` | A smoke tampered inputtal hivja `complete_upload`-ot, majd a response + stored row mezoket validalja. | `python3 scripts/smoke_h1_e1_t2_file_hash_es_metadata_kezeles.py` |
| A checklist es report evidence-alapon ki van toltve. | PASS | `codex/codex_checklist/web_platform/h1_e1_t2_file_hash_es_metadata_kezeles.md:1`; `codex/reports/web_platform/h1_e1_t2_file_hash_es_metadata_kezeles.md:1` | Task-specifikus checklist es report letrejott, DoD matrix kitoltve. | Kezi ellenorzes |
| `./scripts/verify.sh --report codex/reports/web_platform/h1_e1_t2_file_hash_es_metadata_kezeles.md` PASS. | PASS | `codex/reports/web_platform/h1_e1_t2_file_hash_es_metadata_kezeles.verify.log:1`; `codex/reports/web_platform/h1_e1_t2_file_hash_es_metadata_kezeles.md:79` | A kotelezo gate wrapperrel lefutott, az AUTO_VERIFY blokk PASS eredmenyt tartalmaz. | `./scripts/verify.sh --report ...` |

## 6) Advisory notes
- A helper most az ures (`0` byte) letoltott objektumot is hibakent kezeli; ez upload oldalon elvart, de ha a jovoben null-byte file tamogatas kell, explicit policy dontes szukseges.
- A mime determinisztikus mapping jelenleg extension-kozpontu; ha tartalomalapu MIME detektalas lesz igeny, kulon policy task javasolt.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-03-15T22:24:05+01:00 → 2026-03-15T22:27:33+01:00 (208s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/web_platform/h1_e1_t2_file_hash_es_metadata_kezeles.verify.log`
- git: `main@9805f04`
- módosított fájlok (git status): 11

**git diff --stat**

```text
 api/config.py                  |  5 ++++-
 api/routes/files.py            | 35 +++++++++++++++++++++++------------
 api/services/dxf_validation.py | 15 ++++++---------
 3 files changed, 33 insertions(+), 22 deletions(-)
```

**git status --porcelain (preview)**

```text
 M api/config.py
 M api/routes/files.py
 M api/services/dxf_validation.py
?? api/services/file_ingest_metadata.py
?? canvases/web_platform/h1_e1_t2_file_hash_es_metadata_kezeles.md
?? codex/codex_checklist/web_platform/h1_e1_t2_file_hash_es_metadata_kezeles.md
?? codex/goals/canvases/web_platform/fill_canvas_h1_e1_t2_file_hash_es_metadata_kezeles.yaml
?? codex/prompts/web_platform/h1_e1_t2_file_hash_es_metadata_kezeles/
?? codex/reports/web_platform/h1_e1_t2_file_hash_es_metadata_kezeles.md
?? codex/reports/web_platform/h1_e1_t2_file_hash_es_metadata_kezeles.verify.log
?? scripts/smoke_h1_e1_t2_file_hash_es_metadata_kezeles.py
```

<!-- AUTO_VERIFY_END -->
