
# Lastenheft

## Projektziel

Entwicklung eines Fusion-360-Add-ins zur Unterstützung des Möbelbaus mit Plattenmaterialien und Konstruktionsvollholz.

Das System soll Fertigungsinformationen direkt im CAD-Modell speichern und per CSV exportieren.

## Hauptanforderungen

### 1. Metadatenverwaltung

Das Add-in soll ermöglichen:

- Bauteile auswählen
- Fertigungsinformationen speichern
- Informationen dauerhaft im Modell hinterlegen

## 2. Kantenlogik

Bekantung soll über Appearances definiert werden.

Beispiele:
- EDGE_ABS_1
- EDGE_ABS_2
- EDGE_WOOD

Die Information soll flächenbezogen gespeichert werden.

## 3. Oberflächenlogik

Furniere und Beschichtungen sollen ebenfalls über Appearances definiert werden.

Beispiele:
- VENEER_OAK
- VENEER_WALNUT
- HPL_WHITE

## 4. Kommentare und Fertigungshinweise

Zusätzliche Informationen sollen als Attributes gespeichert werden.

Beispiele:
- gemeinsam bearbeiten
- Lochbild erzeugen
- CNC-Hinweise
- Sonderbearbeitung

## 5. CSV-Export

Das System soll:
- alle relevanten Bodies analysieren
- Bounding Boxen bestimmen
- Maße exportieren
- Materialinformationen exportieren
- Appearance-Informationen exportieren
- Attribute exportieren

## 6. Zielsystem

Die CSV-Dateien werden in externe Zuschnittsoftware importiert.

Das Importsystem ist flexibel und unterstützt Mapping.

## Nicht-Ziele

Nicht Bestandteil der ersten Version:
- automatische Verschachtelung
- CAM-Generierung
- ERP-Funktionen
- automatische CNC-Erkennung
- Cloud-Synchronisation
