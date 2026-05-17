# Architektur

Stand: 2026-05-17 18:45 UTC

## Prinzip

Fusion 360:
- CAD
- Metadaten

DIY Garage Cut:
- Optimierung
- Rohmaße
- Produktion

Fusion berechnet keinen Zuschnitt.

---

# Addins

## DIYGarageCutExportAddin

Verantwortlich für:
- CSV-Export
- Validierung
- Analyse
- Katalogverwaltung

```text
fusion_addin_export/
├── commands/
│   ├── export/
│   ├── validate/
│   └── catalog/
```

## DIYGarageCutPropertiesAddin

Verantwortlich für:
- Material
- Kanten
- Fräszulage
- Hinweise

```text
fusion_addin_properties/
├── commands/
│   └── part_properties/
```

---

# Shared

```text
shared/
├── catalog/
├── attributes/
├── csv_export/
└── fusion_helpers/
```

---

# Katalog

```text
catalog.json
catalog_type_config.json
```

Typen:
- sheet
- bar
- edge
- profile
- hardware
- consumable

Typ-spezifische Felder:
- kommen aus `catalog_type_config.json`
- werden im Catalog-Dialog dynamisch angezeigt
- werden bei CSV in `attributes` berücksichtigt

---

# Export

CSV enthält nur:
- Maße
- Material
- Kanten
- Hinweise

Keine:
- Optimierung
- Rohmaßberechnung
- QR-Logik
