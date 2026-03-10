# H0 modulhatarok es boundary szerzodes (source of truth)

## 1. Dokumentum szerepe

Ez a dokumentum a web platform H0 modulhatarainak es ownership szerzodesenek explicit source of truth-ja.
A modulhatarokkal kapcsolatos vitaban ez a dokumentum elsoseget elvez a README, roadmap es egyeb osszefoglalo doksikhoz kepest.

Kapcsolodo dokumentumok:
- `docs/web_platform/README.md`
- `docs/web_platform/architecture/dxf_nesting_platform_architektura_es_supabase_schema.md`
- `docs/web_platform/architecture/h0_domain_entitasterkep_es_ownership_matrix.md`
- `docs/web_platform/roadmap/dxf_nesting_platform_h0_reszletes.md`

## 2. Kotelezo boundary alapelvek

1. `definicio != hasznalat != snapshot != artifact != projection`
2. A worker es a nesting engine adapter csak run snapshotbol dolgozhat.
3. A viewer source of truth-a projection adat, nem SVG artifact.
4. A manufacturing es postprocess kulon reteg, nem a nesting truth resze.

### 2.1 Fogalmi szetvalasztas (normativ)

- Definicio: hosszu eletu, verziozott domain allapot (`part_revisions`, `sheet_revisions`, profilverziok).
- Hasznalat: projekt-specifikus alkalmazas (`project_part_requirements`, `project_sheet_inputs`, profil kivalasztas).
- Snapshot: run inditasakor befagyasztott futasi bemenet (`nesting_run_snapshots`).
- Artifact: futasi fajl/blobjellegu kimenet (solver output, SVG, DXF, ZIP).
- Projection: query-zhato, API/viewer fogyasztasra optimalizalt eredmenyadat (`run_layout_*`, `run_metrics`).

## 3. Modul katalogus (H0)

A H0-ban rogzitett fo modulok:
- Platform Core
- Geometry Pipeline
- Nesting Engine Adapter
- Viewer/Reporting
- Manufacturing
- Postprocess
- Decision Layer

## 4. Boundary matrix (ownership + olvasas + output)

| Modul | Ownership (amit birtokol) | Mit olvas | Mit allit elo | Mit NEM birtokolhat |
| --- | --- | --- | --- | --- |
| Platform Core | Projekt, run orchestration, snapshot lifecycle, artifact/projection lifecycle policy | Project/technology/manufacturing valasztasok, geometry es run metaadatok | Run torzs, snapshot trigger, allapotatmenetek | Solver belso logika, geometry parser implementacio |
| Geometry Pipeline | Forras file ingest, geometry revision, canonical derivaltak | Feltoltott forras file metadata, parser policy | `nesting_canonical`, `manufacturing_canonical`, geometry validacios jelentesek | Run scheduling, solver futtatas, viewer query API truth |
| Nesting Engine Adapter | Snapshot->engine input mapping, engine futtatasi contract, solver output normalizalas | Kizarolag run snapshot + geometry derivalt referenciak | Canonical run result, solver artifact, placement nyers output | Elo DB domain allapot olvasas, UI projection mint truth |
| Viewer/Reporting | Projection schema es query modell | Canonical run result + projection feed | `run_layout_*`, `run_metrics`, report view model, viewer input projection | SVG parsing mint truth, solver raw output kozvetlen UI truth |
| Manufacturing | Manufacturing szabalyverziok es cut planning policy | Approved projection + manufacturing profile version | Manufacturing plan adatmodell, gyartasi kontur-policy eredmenyek | Nesting optimalizalo dontesek felulirasa, postprocessor-gepspecifikus emit |
| Postprocess | Gepfuggo export adapterek | Manufacturing plan + postprocessor profile | Machine-ready programok, gepfuggo export artifactok | Nesting truth modositas, manufacturing szabalydefinicio |
| Decision Layer | Run osszehasonlitasi kriteriumok, run valasztasi policy | Run metrics/projection, run metadata | Kivalasztott run pointer, decision audit record | Placement koordinata atiras, geometry vagy solver output atszamolas |

## 5. Source-of-truth matrix

| Adatkategoria | Source of truth modul | Canonical tarolo | Nem source-of-truth pelda |
| --- | --- | --- | --- |
| Part/sheet definiciok es reviziok | Platform Core (domain ownership) + Geometry Pipeline (geometry derivalt ownership) | `part_revisions`, `sheet_revisions`, `geometry_revisions`, `geometry_derivatives` | Runhoz mellekelt ideiglenes JSON dump |
| Projekt hasznalat (mennyiseg, prioritas, sheet input) | Platform Core | `project_part_requirements`, `project_sheet_inputs` | UI session state |
| Futasi bemenet | Platform Core | `nesting_run_snapshots` | Elo tablaleolvasas worker oldalon |
| Nester nyers output | Nesting Engine Adapter | Solver artifact + canonical run result | Kozvetlen frontendes parse |
| Viewer allapot | Viewer/Reporting | `run_layout_sheets`, `run_layout_placements`, `run_layout_unplaced`, `run_metrics` | SVG file |
| Gyartasi terv | Manufacturing | manufacturing plan projection/tables | Nesting solver output |
| Gepfuggo kimenet | Postprocess | postprocess artifactok | Manufacturing belso szabalyobjektum |
| Run valasztas/osszehasonlitas | Decision Layer | decision audit + selected run reference | UI temporary filter state |

## 6. Modulonkenti szerzodesek

### 6.1 Platform Core

Purpose:
- Projekt, run es snapshot eletciklus osszefogasa.

Ownership:
- Run inditas, statuszgep, snapshot lefagyasztas trigger.

Inbound inputok:
- Projektbeallitasok, valasztott profilverziok, geometry derivative referencia.

Outbound outputok:
- Snapshot rekord, run statusz valtozas, orchestration esemenyek.

Tiltott felelossegek:
- Nem implemental solver algoritmust.
- Nem parse-ol DXF-et.
- Nem allit elo machine-ready exportot.

### 6.2 Geometry Pipeline

Purpose:
- Forras geometry atalakitas canonical derivaltakka.

Ownership:
- Ingest, validation, `nesting_canonical` es `manufacturing_canonical` eloallitas.

Inbound inputok:
- Feltoltott forras fajlok + parser/validation policy.

Outbound outputok:
- Geometry revision, validation report, canonical derivalt referenciak.

Tiltott felelossegek:
- Nem indit run-t.
- Nem valaszt run gyoztest.
- Nem gyart gepfuggo postprocess outputot.

### 6.3 Nesting Engine Adapter

Purpose:
- Snapshotbol engine-compatible inputot kepez, futtat, normalizal.

Ownership:
- Engine input contract mapping, timeout/retry policy adapter oldalon, canonical run result kepzes.

Inbound inputok:
- Kizarolag `nesting_run_snapshots` + geometry derivalt referenciak.

Outbound outputok:
- Solver artifact, canonical placement output, futasi telemetry.

Tiltott felelossegek:
- Nem olvashat kozvetlenul elo project/technology/domain tablakat.
- Nem tekintheti truth-nak az SVG outputot.
- Nem vegez manufacturing vagy postprocess logikat.

### 6.4 Viewer/Reporting

Purpose:
- Projection adatok publikacioja UI, riport es API celra.

Ownership:
- Projection schema, query endpointhez szukseges strukturalt adatszerkezet.

Inbound inputok:
- Canonical run result, run metadata, artifact referencia.

Outbound outputok:
- Projection tablazatok (`run_layout_*`, `run_metrics`), report feed, optional viewer SVG artifact.

Tiltott felelossegek:
- Nem parserolja vissza truth-kent az SVG-t.
- Nem olvassa kozvetlenul a solver nyers outputjat UI truth helyett.
- Nem irja at a canonical placement truthot.

### 6.5 Manufacturing

Purpose:
- Gyartasi szabalyok alkalmazasa a nesting eredmenyre.

Ownership:
- Manufacturing profile versions, cut policy mapping, gyartasi terv logika.

Inbound inputok:
- Approved run projection + manufacturing profilverzio.

Outbound outputok:
- Manufacturing plan, kontur- es sorrend policy eredmenyek.

Tiltott felelossegek:
- Nem valtoztathatja meg a nesting placement truthot.
- Nem general kozvetlen gepfuggo NC outputot (az a Postprocess reteg felelossege).

### 6.6 Postprocess

Purpose:
- Gepfuggo export allomanyok eloallitasa.

Ownership:
- Postprocessor profile, gepfuggo transzformacios adapter.

Inbound inputok:
- Manufacturing plan + postprocessor profile version.

Outbound outputok:
- Machine-ready artifactok (pl. G-code/NC varians, gepfuggo bundle).

Tiltott felelossegek:
- Nem definial manufacturing szabalyokat.
- Nem nyul vissza run projection truthhoz.

### 6.7 Decision Layer

Purpose:
- Runok osszehasonlitasa es valasztasi dontesek auditja.

Ownership:
- Decision kriteriumok, score policy, selected-run allapot.

Inbound inputok:
- Run metrics/projection, run statuszok, domain policy.

Outbound outputok:
- Kivalasztott run referencia, decision audit rekord.

Tiltott felelossegek:
- Nem modosit placement koordinatakat.
- Nem indit manufacturing/postprocess pipeline-t explicit policy nelkul.

## 7. Handoff contractok (boundary interfeszek)

### 7.1 Geometry Pipeline -> Nesting Engine Adapter

Contract minimum:
- Stabil geometry derivative azonosito (`nesting_canonical`)
- Geometria verzio metadata (forras revision + tolerance policy)
- Validacios statusz (`approved`/`rejected`)

Tiltas:
- Engine adapter nem kerdezhet vissza elo parser/allapot tablakat.

### 7.2 Nesting Engine Adapter -> Run Results / Projection

Contract minimum:
- Canonical placement lista
- Unplaced lista okkal
- Aggregalt futasi metrikak
- Artifact manifest hivatkozasok

Tiltas:
- Viewer truth nem szarmazhat kozvetlen SVG parse-bol.

### 7.3 Manufacturing -> Postprocess

Contract minimum:
- Manufacturing plan canonical representation
- Kontur/sorrend/pierce policy eredmeny
- Postprocessor profilverzio referencia

Tiltas:
- Postprocess nem implementalhat gyartasi policy dontest ad-hoc.

### 7.4 Decision Layer -> Run selection / comparison

Contract minimum:
- Osszehasonlitasi metrika snapshot
- Dontesi score + indoklas
- Selected run pointer

Tiltas:
- Decision layer nem irhat at solver outputot vagy projection truthot.

## 8. Tilos coupling lista

- Solver kozvetlen olvasas elo domain tablakbol.
- Viewer SVG parse mint platform truth.
- Manufacturing profil logika beemelese a solver adapterbe.
- Postprocess gepfuggo kod beemelese manufacturing policy modulba.
- Decision score es placement geometriamodositas egy modulban.

## 9. Anti-pattern lista

- Solver-kozpontu architektura, ahol minden domain felelosseg az engine korul van.
- Elo DB-bol ad-hoc solver input, snapshot nelkul.
- Artifact/projection osszemosasa.
- Manufacturing truth es nesting truth osszemosasa.

## 10. H0/H1 kovetkezmenyek

H0 kovetkezmeny:
- A schema, API es worker contracts csak ezen boundary-kkel kompatibilis iranyban bovitheto.
- Uj endpoint vagy worker lepest csak ownership tisztazott modullal lehet bevezetni.

H1 kovetkezmeny:
- A feature implementacio nem kerulheti meg a snapshot-first modellt.
- Viewer featurek projection-first alapon epulhetnek, SVG csak render artifact lehet.
- Manufacturing/Postprocess bovitese nem torheti meg a nesting truth stabilitast.

## 11. Dontesi szabaly konfliktus eseten

Ha ket dokumentum ellentmond, modulhatar, ownership es source-of-truth temaban ez a dokumentum az ervenyes.
A tobbi dokumentum rovid hivatkozassal erre kell visszamutasson.

Domain entitas-tipus, aggregate root, es definition/usage/demand/snapshot/result/export szeparacio
kerdesben a `h0_domain_entitasterkep_es_ownership_matrix.md` az elsosegi forras.
