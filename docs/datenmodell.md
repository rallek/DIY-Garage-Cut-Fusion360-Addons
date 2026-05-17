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

## sheet

```json
{
  "thickness_mm": 19,
  "default_trim_allowance_mm": 2
}
```

## edge

```json
{
  "thickness_mm": 2
}
```

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
