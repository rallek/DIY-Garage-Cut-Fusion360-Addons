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
surface
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
surface_top
surface_bottom
edge_front_custom_text
edge_back_custom_text
edge_left_custom_text
edge_right_custom_text
surface_top_custom_text
surface_bottom_custom_text

notes

exclude_from_export
```

---

# front_reference

Werte:

```text
long_pos
long_neg
short_pos
short_neg
```

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

## Exportformat (konfigurierbar)

Datei:

```text
export_config.json
```

Schlüssel:

- `csv_delimiter`: Feldtrennzeichen.
- `csv_decimal_separator`: Dezimaltrennzeichen (`.` oder `,`).
- `csv_decimals`: Anzahl Nachkommastellen für numerische CSV-Spalten.
- `csv_decimal_mode`:
- `fixed`: immer feste Nachkommastellen.
- `trim`: Nachkommastellen nur bei Bedarf.
- `csv_material_name_mode`:
- `material`: `material_name` entspricht `material`.
- `typed_dimensions`: materialbezogene Bezeichnung je Typ.
- Regel `bar`: `material` + Leerzeichen + `thickness_mm` + `x` + `width_mm`.
- Regel `sheet`: `material` + Leerzeichen + `thickness_mm`.

Numerische CSV-Spalten:

```text
length_mm
width_mm
thickness_mm
trim_allowance_mm
edge_front_thickness_mm
edge_back_thickness_mm
edge_left_thickness_mm
edge_right_thickness_mm
```

Zusätzliche Spalte:

```text
material_name
```

Kanten-Exportspalten:

```text
edge_front_name
edge_front_thickness_mm
edge_back_name
edge_back_thickness_mm
edge_left_name
edge_left_thickness_mm
edge_right_name
edge_right_thickness_mm
surface_top_name
surface_bottom_name
notes
```

## Oberflächen und Fertigungshinweise

`surface_top` und `surface_bottom` verweisen auf Katalogeinträge vom Typ `surface`.

Für Kanten und Oberflächen kann statt eines Katalogeintrags der Sonderwert `__text__` gespeichert werden. Dann muss das zugehörige `*_custom_text`-Attribut gefüllt sein. Beim CSV-Export wird dieser Freitext als Name ausgegeben. Bei Kanten ist die exportierte Dicke in diesem Fall `0`.

Im Modus `Alle gemeinsam` wird eine gemeinsame Oberflächenauswahl auf `surface_top` und `surface_bottom` geschrieben. Für die vier Kanten wird derselbe Name als Freitext-Kante gespeichert; die Kantenstärke bleibt dabei `0`.

Der CSV-Export transportiert bewusst das fachliche Ergebnis, nicht den UI-Modus. Vier identische Freitext-Kanten mit Dicke `0` sind deshalb im CSV nicht von einer Eingabe über `Alle gemeinsam` zu unterscheiden.

Für Materialtypen mit Oberflächenunterstützung, aber ohne Kantenunterstützung, wird die gemeinsame Oberfläche im Dialog ebenfalls über `surface_top` und `surface_bottom` gespeichert. Die Modell-Visualisierung behandelt diese Auswahl als globale Oberfläche und setzt die Appearance auf alle Faces des Bodys, nicht nur auf erkannte Ober-/Unterseiten.

Breaking Change zu Issue #16: Alte Attribute wie `surface_top_text`, `surface_bottom_text` oder `finish_*` sind nicht mehr Teil des Datenvertrags und werden nicht migriert oder als Fallback gelesen. Bestehende Testmodelle müssen mit den neuen Feldern erneut gespeichert werden.

`notes` ist ein separater freier Fertigungshinweis und gehört nicht zur strukturierten Oberflächenauswahl.

`material_name` ist für nachgelagerte Zuschnittsysteme gedacht und kann über `csv_material_name_mode` vom reinen Materialnamen auf eine dimensionsangereicherte Bezeichnung umgestellt werden.
