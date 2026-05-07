
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
│   ├── lib/
│   ├── Resources/
│   ├── manifest.json
│   └── FusionFurnitureTools.py
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
