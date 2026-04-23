-- DXF Prefilter E3-T4: minimális replacement lineage truth a file_objects domainben.
-- Scope: nullable self-FK replaces_file_object_id az app.file_objects táblában
--        + megfelelő index.
-- Non-scope: UI, feature flag, superseded-file hiding, review workflow,
--            artifact download, külön replacement tábla.
--
-- Modellezési indok:
--   Az replace action canonical route (POST .../files/{file_id}/replace) persisted
--   lineage truth-ot igényel — nem elég response payloadban jelezni.
--   A nullable self-FK a legkisebb helyes V1 lépés: nem kell külön tábla,
--   nem írja felül a régi sort in-place, és a régi preflight run audit érintetlen marad.

alter table app.file_objects
  add column if not exists replaces_file_object_id uuid
    references app.file_objects(id) on delete restrict;

create index if not exists idx_file_objects_replaces_file_object_id
  on app.file_objects(replaces_file_object_id)
  where replaces_file_object_id is not null;
