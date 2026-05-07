
# Datenmodell

## Grundstruktur

Das System verwendet drei Informationsebenen:

| Ebene | Zweck |
|---|---|
| Physical Material | technischer Werkstoff |
| Appearance | Oberflächen- und Fertigungsinformationen |
| Attributes | Zusatzinformationen |

---

# Physical Material

## Beispiele

- MDF
- Multiplex
- Spanplatte
- Birke Multiplex
- KVH

Diese Daten stammen direkt aus Fusion 360.

---

# Appearance

## Kanten

| Appearance | Bedeutung |
|---|---|
| EDGE_ABS_1 | ABS 1 mm |
| EDGE_ABS_2 | ABS 2 mm |
| EDGE_WOOD | Massivholzkante |

## Furnier

| Appearance | Bedeutung |
|---|---|
| VENEER_OAK | Eiche furniert |
| VENEER_WALNUT | Nussbaum furniert |

## Beschichtung

| Appearance | Bedeutung |
|---|---|
| HPL_WHITE | HPL weiß |
| PAINT_BLACK | Lack schwarz |

---

# Attributes

Attribute-Gruppe:

```text
com.furniture.cutlist
```

## Attribute-Felder

| Key | Typ | Beschreibung |
|---|---|---|
| schema_version | string | Datenmodellversion |
| grain | string | Maserungsrichtung |
| note | string | Freitext |
| orientation_override | string | optionale Achsüberschreibung |

## grain

Mögliche Werte:

```text
none
length
width
```

## orientation_override

Mögliche Werte:

```text
auto
swap_length_width
```
