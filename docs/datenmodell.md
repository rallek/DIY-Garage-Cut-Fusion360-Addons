# Datenmodell

Stand: 2026-05-17 18:45 UTC

# catalog.json

## Typen

```text
sheet
bar
edge
profile
hardware
consumable
```

## Basisfelder

```json
{
  "id": "",
  "type": "",
  "name": "",
  "appearance": ""
}
```

## Typ-spezifische Felder (konfigurierbar)

Konfiguration:

```text
catalog_type_config.json
```

Regel:
- Felder werden pro `type` in der Konfiguration definiert.
- `catalog.json` speichert nur die Felder, die für den jeweiligen Typ relevant sind.

## Vertragsregeln (kurz)

- Feld-Keys sind fachlich eindeutig und ohne Einheit im Namen.
- Einheiten stehen in der Typ-Konfiguration (`storage_unit`, z. B. `mm`), nicht im Key.
- Katalogwerte werden intern in einer kanonischen Einheit gespeichert (aktuell Länge: `mm`).
- CSV gibt Einheit explizit mit aus (`..._unit`), zusätzlich kann die Fusion-Dokumenteinheit ausgegeben werden.
- Erlaubte `kind`-Werte: `number`, `string`, `boolean`, `enum`.

### Standard: sheet

```json
{
  "sheet_default_trim_allowance": 0.0
}
```

Bereich:
- `0.0` bis `5.0`
- Schrittweite `0.1`

### Standard: edge

```json
{
  "edge_thickness": 0.0
}
```

Bereich:
- `0.0` bis `10.0`
- Schrittweite `0.1`

---

# Body-Attribute

Namespace:

```text
DGC.part_metadata
```

## Felder

```text
material_id
trim_allowance_mm

front_reference

edge_front
edge_back
edge_left
edge_right

notes

exclude_from_export
```

---

# front_reference

Werte:

```text
long_side
short_side
```

`Richtung tauschen` ist nur UI-Logik.
Kein zusätzliches CSV-Feld.

---

# Appearance

Nur Visualisierung.
Nie führende Datenquelle.

---

# CSV-Bezug

Entscheidung (2026-05-19):
- Keine Sammelspalte `attributes` im Zielvertrag.
- Relevante Felder werden als eigene CSV-Spalten geführt.
- `attributes` war nur Übergang/Debug und ist nicht Teil des stabilen Datenvertrags.

CSV-Header ist damit explizit fachlich aufgebaut (z. B. Maße, Material, Fräszulage, Kanten, Hinweise), statt Key/Value-Textsammlung.

Katalog-/Typ-Informationen bleiben intern strukturierte Quelle (`catalog.json` + `catalog_type_config.json`) und werden bei Bedarf gezielt in eigene Spalten projiziert.
