
# Architektur

## Grundprinzip

Fusion 360 dient ausschließlich als:
- CAD-System
- Geometriequelle
- Metadatenträger

Die eigentliche Produktionslogik liegt außerhalb von Fusion.

---

# Komponenten

## 1. Fusion Add-in

Verantwortlich für:
- UI
- Attributverwaltung
- Benutzerinteraktion

## 2. Exportskript

Verantwortlich für:
- Geometrieanalyse
- CSV-Erzeugung
- Datennormalisierung

## 3. Externe Zuschnittsoftware

Verantwortlich für:
- Optimierung
- Kalkulation
- Materialverbrauch
- Produktionsplanung

---

# Datenfluss

```text
Fusion 360
    ↓
Add-in / Export
    ↓
CSV
    ↓
Zuschnittsoftware
```

---

# Erweiterbarkeit

Spätere Erweiterungen:
- CNC-Informationen
- Bohrbilder
- Gruppierungslogik
- Fertigungsreihenfolgen
- Stücklisten
- ERP-Anbindung

---

# Designprinzipien

## Einfachheit vor Automatisierung

Der Workflow soll:
- robust
- nachvollziehbar
- wartbar
sein.

Keine komplexe automatische Geometrieerkennung in V1.

## Sichtbare Metadaten

Kanten und Oberflächen sollen visuell erkennbar sein.

## Lose Kopplung

CSV bleibt die zentrale Austauschschicht.
