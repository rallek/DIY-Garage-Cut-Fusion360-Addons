
# DIY Garage Cut Fusion360 Addons

Dieses Repository ist ein Unterrepo von `DIY Garage Cut` und enthält die Fusion-360-Inhalte, mit denen das Hauptprojekt um CAD-nahe Fertigungsdaten erweitert wird.

Die README ist bewusst als Einstieg für spätere Mitwirkende und Nutzer geschrieben. Die fachlich-technischen Projektdetails werden zusätzlich in separaten Markdown-Dateien dokumentiert, damit der Überblick erhalten bleibt.

## Ziel

Dieses Projekt erweitert Fusion 360 um:

- Bauteil-Metadaten für Möbelbau
- Bekantung über Appearances
- Fertigungshinweise über Attributes
- CSV-Export für externe Zuschnittoptimierer
- robuste Datenübergabe an eigene Apps

## Grundidee

Fusion 360 bleibt das CAD-System.

Die Zuschnitt- und Fertigungslogik wird in externen Tools verarbeitet.

Das Add-in dient ausschließlich dazu:
- Fertigungsinformationen im Modell zu hinterlegen
- strukturierte Daten zu exportieren

## Projektdokumentation

Für die inhaltliche und technische Übersicht gibt es zusätzlich:

- [docs/projektuebersicht.md](docs/projektuebersicht.md)
- [docs/github-workflow.md](docs/github-workflow.md)
- [docs/datenmodell.md](docs/datenmodell.md)
- [docs/architektur.md](docs/architektur.md)
- [docs/workflow.md](docs/workflow.md)
- [docs/lastenheft.md](docs/lastenheft.md)
- [docs/roadmap.md](docs/roadmap.md)

## Arbeitsmodell

Wir arbeiten nach einem klaren GitHub-Prozess:

- ein Issue pro Thema
- ein Thread pro Issue
- ein Pull Request pro Issue
- kein direkter Zugriff auf `main`
- Diskussionen und Entscheidungen zuerst im Issue

Die genaue Regelung steht in [docs/github-workflow.md](docs/github-workflow.md) und [CONTRIBUTING.md](CONTRIBUTING.md).

## Architektur

### Physical Material
Technischer Werkstoff:
- MDF
- Multiplex
- Spanplatte
- Massivholz
- Sperrholz

### Appearance
Oberflächen- und Fertigungsinformationen:
- Umleimer
- Furnier
- HPL
- Lack
- Beschichtungen

### Attributes
Zusätzliche Metadaten:
- Notizen
- Bearbeitungshinweise
- Gruppeninformationen
- Exportsteuerung

## Projektstruktur

```text
DIY-Garage-Cut-Fusion360-Addons/
│
├── .github/
│   ├── ISSUE_TEMPLATE/
│   └── pull_request_template.md
│
├── CONTRIBUTING.md
├── docs/
│   ├── github-workflow.md
│   ├── lastenheft.md
│   ├── datenmodell.md
│   ├── workflow.md
│   ├── architektur.md
│   └── roadmap.md
│
├── fusion_addin/
│   ├── commands/
│   │   ├── __init__.py
│   │   └── command_core.py
│   ├── lib/
│   ├── Resources/
│   ├── DIYGarageCutAddin.manifest
│   ├── DIYGarageCutAddin.py
│   └── config.py
│
├── examples/
│   ├── csv/
│   └── screenshots/
│
├── scripts/
├── tests/
│
└── README.md
```

## Lizenz

Es gilt die Projektlizenz aus dem Hauptprojekt, siehe [LICENSE](LICENSE).

## Installation und erster Test (Windows, Anwender)

### 1) Add-in in Fusion 360 einbinden

1. Dieses Repo lokal herunterladen oder klonen.
2. In Fusion 360 auf `Dienstprogramme > Add-Ins` gehen.
3. Im Reiter `Add-Ins` auf `+` (lokales Add-in hinzufuegen) klicken.
4. Fuer den CSV-Export den Ordner `fusion_addin_export` aus diesem Repo auswaehlen.
5. Fuer Eigenschaften den Ordner `fusion_addin_properties` aus diesem Repo auswaehlen.
6. Beide Add-ins markieren, auf `Ausfuehren` klicken und bei Bedarf `Beim Start ausfuehren` aktivieren.

Hinweis: Diese Klicks brauchst du normalerweise nur beim ersten Einrichten. Danach startet das Add-in automatisch mit Fusion 360.

### 2) Wo muss der Button sichtbar sein?

Der Button erscheint **nicht** im Add-in-Dialog selbst.

Er erscheint in der normalen Konstruktionsoberflaeche:

1. In den Workspace `Design` wechseln.
2. In die Registerkarte `Volumenkorper` (Solid) wechseln.
3. Nach dem Button `DIY Garage Cut` in den ueblichen Solid-Panels suchen (je nach Fusion-Version z. B. `Skripte und Add-Ins`, `Erstellen` oder `Werkzeuge`).
4. Wenn moeglich wird der Button von Fusion direkt sichtbar in der Toolbar angezeigt; sonst liegt er im `>>`-Ueberlauf.
5. Klick auf den Button startet den CSV-Export-Dialog.

### 3) Wenn nichts sichtbar ist (Troubleshooting)

1. Pruefen, dass das Add-in im Dialog wirklich auf `Laeuft` steht.
2. Fusion 360 komplett neu starten (nicht nur Fenster schliessen).
3. Sicherstellen, dass als lokaler Add-in-Ordner wirklich `fusion_addin` gewaehlt wurde (darin liegen `DIYGarageCutAddin.py` und `DIYGarageCutAddin.manifest`).
4. In `Design > Volumenkorper` nachsehen, ob der Button rechts im `>>`-Ueberlaufmenue der Toolbar steckt.
5. Falls weiterhin nichts erscheint: Add-in im Dialog stoppen und erneut starten.

## Stand Issue #3: Datenmodell-Grundlage fuer Bauteil-Metadaten

Was wurde gebaut:

- Zentrale Attribut-Konstanten in `fusion_addin/config.py`:
- Namespace/Attribut-Gruppe: `DIYGarageCut.part_metadata`
- Keys: `material_typ`, `kanten_info`, `export_flag`, `notiz`
- Kleine, defensive Helper in `fusion_addin/lib/attribute_helpers.py`:
- `set_attr(entity, key, value)`
- `get_attr(entity, key, default=None)`
- `clear_attr(entity, key)`
- Command-Testweg in `fusion_addin/commands/command_core.py`:
- Bei selektiertem Koerper werden Testwerte geschrieben, wieder gelesen und in einer MessageBox angezeigt.

So testest du es in Fusion 360:

1. Add-in starten (wie oben beschrieben).
2. Im Design-Workspace einen Volumenkoerper auswaehlen.
3. Befehl `DIY Garage Cut` ausfuehren (Toolbar oder Kontextmenue).
4. Erwartung: MessageBox zeigt Namespace und die vier gelesenen Testwerte.
5. Ohne Koerper-Auswahl oder bei falscher Auswahl gibt es eine klare Hinweis-Meldung statt Absturz.

## Stand Issue #4: CSV-Export V1

Was wurde gebaut:

- Export aller sichtbaren Bodies in eine UTF-8-CSV-Datei.
- CSV-Header: `body_name,width_mm,height_mm,depth_mm,material,appearance,attributes`
- Pro Body:
- Name des Bodies
- BoundingBox-Masse in Millimeter (`width_mm`, `height_mm`, `depth_mm`)
- Materialname
- Appearance-Name
- vorhandene Attribute als kompakter Text (`gruppe:key=value;...`)
- Defensives Fehlerverhalten mit `try/except` und Logging ueber `print()`.

So verwendest du den Export:

1. Add-in in Fusion 360 starten (siehe Installationsschritte oben).
2. Sicherstellen, dass sichtbare Bodies im aktiven Design vorhanden sind.
3. Button `DIY Garage Cut` ausfuehren.
4. Speicherort und Dateiname im Dialog waehlen.
5. Erwartung: CSV-Datei wird gespeichert und eine Erfolgsmeldung mit Anzahl exportierter Bodies erscheint.
