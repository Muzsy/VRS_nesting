# H0 storage bucket strategia es path policy (H0-E6-T1)

## 1. Cel es scope

Ez a dokumentum a H0 storage source-of-truth policyje:
- rogzitjuk a kanonikus H0 bucket inventoryt;
- rogzitjuk az entitas -> bucket mappinget;
- rogzitjuk a bucketenkenti path naming mintakat;
- rogzitjuk az immutabilitas/overwrite alapelveket;
- elokeszitjuk a H0-E6-T2 hozzaferes-vedelmi (RLS/storage policy) taskot.

Ez a task docs-only: most nem jon letre migracio, bucket provisioning script, RLS policy, upload API vagy worker implementacio.

## 2. Kanonikus H0 bucket inventory

H0-ban a kanonikus bucket inventory legalabb a kovetkezo:
- `source-files`
- `geometry-artifacts`
- `run-artifacts`

| Bucket | H0 statusz | Szerep |
| --- | --- | --- |
| `source-files` | canonical | felhasznaloi feltoltesek es bejovo source file objektumok |
| `geometry-artifacts` | canonical reserved | jovobeli file-backed geometry/viewer/manufacturing artifactok |
| `run-artifacts` | canonical | nesting futasbol keletkezo file/blob output artifactok |

## 3. Entitas -> bucket mapping

- `app.file_objects`
  - alapertelmezett bucket: `source-files`
  - ez a storage-reference + metadata truth a source file vilagban
- `app.run_artifacts`
  - alapertelmezett bucket: `run-artifacts`
  - ez a run output file/blob truth
- `geometry-artifacts`
  - reserved/canonical bucket a jovobeli file-backed geometry artifactokhoz

Explicit hatar:
- az `app.geometry_derivatives` **nem** bucket/path alapu storage-truth;
- az `app.geometry_derivatives` DB-ben tarolt, ujraeloallithato derivalt reteg.

## 4. Path naming policy

Globalis naming elvek:
- minden path `projects/{project_id}/...` prefixszel induljon;
- lower-case, slash-separated, stabilan migralhato szerkezetet hasznaljunk;
- stabil identity ne pusztan az eredeti fajlnev legyen;
- ahol ertelmes, hash-alapu file nev (`{content_hash}`) legyen;
- artifact/path schema legyen audit- es migration-friendly.

### 4.1 `source-files`

Kanonikus minta:
- `projects/{project_id}/files/{file_object_id}/{sanitized_original_name}`

Megjegyzes:
- a stabil technikai identity a `file_object_id`;
- a fajlnev csak emberi olvashatosagi szerepet kap.

### 4.2 `geometry-artifacts`

Kanonikus minta:
- `projects/{project_id}/geometry/{geometry_revision_id}/{artifact_kind}/{content_hash}.{ext}`

Megjegyzes:
- ez a minta jovobeli file-backed geometry artifactokra vonatkozik;
- nem az `app.geometry_derivatives` canonical truth tarolasi mintaja.

### 4.3 `run-artifacts`

Kanonikus minta:
- `projects/{project_id}/runs/{run_id}/{artifact_kind}/{content_hash}.{ext}`

Megjegyzes:
- a run output artifactok bucketje alapertelmezetten `run-artifacts`.

## 5. Immutabilitas es overwrite szabalyok

- Generalt artifactot ne overwrite-oljunk in-place, ha hash/verzio adheto.
- Uj artifact uj pathra menjen (uj hash vagy verzio).
- Source uploadnal a canonical identity ne pusztan a fajlnev legyen.
- A path naming tamogassa az auditot es a kesobbi migrationt.

## 6. Environment es ownership elvek

- Environment szeparacio ne bucket-nev suffix/prefix hackkel tortenjen.
- Environment szeparacio deployment/supabase project szinten tortenjen.
- Project ownership modell (project_id + user ownership) legyen a kesobbi
  RLS/storage policy enforcement alapja.

## 7. Kapcsolat a kovetkezo taskkal (H0-E6-T2)

A H0-E6-T2 erre a dokumentumra epitve vezeti be:
- a tenyleges storage access policyket;
- az RLS enforcementet;
- a service role vs authenticated role gyakorlati jogosultsagi szabalyokat.

H0-E6-T1 nem policy implementacio, hanem naming+bucket source-of-truth lezaras.
