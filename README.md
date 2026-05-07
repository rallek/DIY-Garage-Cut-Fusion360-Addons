
# Fusion Furniture Tools

Fusion 360 Add-in und Export-Skripte für Möbelbau, Zuschnittoptimierung und Fertigungsinformationen.

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
fusion-furniture-tools/
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

Zunächst private Entwicklung.
Später eventuell Open Source.
