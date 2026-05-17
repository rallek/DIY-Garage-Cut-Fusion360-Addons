# Katalog-Typen erweitern

Stand: 2026-05-17

Dieses Dokument beschreibt, wie du **neue Material-/Artikeltypen** selbst anlegst.

Zentrale Datei:

```text
catalog_type_config.json
```

## Prinzip

- Jeder Typ hat eine `id`, mehrsprachige `labels` und optional `fields`.
- Erlaubte `kind`-Werte sind:
  - `number`
  - `string`
  - `boolean`
  - `enum`
- Feld-Keys sind fachlich eindeutig und **ohne Einheit im Namen**.
- Einheit wird separat über `storage_unit` gepflegt (z. B. `mm`).

## Aufbau

Beispiel eines Typs:

```json
{
  "id": "panel",
  "labels": {
    "de": "Paneel",
    "en": "Panel"
  },
  "fields": [
    {
      "key": "panel_core_thickness",
      "kind": "number",
      "labels": {
        "de": "Kernstärke",
        "en": "Core thickness"
      },
      "min": 0.0,
      "max": 50.0,
      "step": 0.1,
      "default": 0.0,
      "csv": true,
      "quantity": "length",
      "storage_unit": "mm"
    }
  ]
}
```

## Felder erklärt

- `id`: interner Typname (klein, stabil, z. B. `panel`)
- `labels.de` / `labels.en`: Anzeigenamen in der UI
- `fields`: zusätzliche typ-spezifische Felder
- `key`: interner Feldname (stabil, eindeutig, ohne Einheit im Key)
- `kind`: aktuell `number`
- `kind`: einer von `number | string | boolean | enum`
- `min`, `max`, `step`, `default`: Wertebereich und Schrittweite
- Bei `number`: `min`, `max`, `step`, `default`
- Bei `string`: optional `min_length`, `max_length`, `default`
- Bei `boolean`: `default` (`true`/`false`)
- Bei `enum`: `options` (Liste) und `default`
- `csv`: wenn `true`, wird Feld beim Export in `attributes` ergänzt
- `quantity`: fachliche Größe (z. B. `length`)
- `storage_unit`: kanonische Speichereinheit (aktuell meist `mm`)
- `legacy_keys` (optional): alte Feldnamen für Migration

## So gehst du vor

1. `catalog_type_config.json` öffnen.
2. Unter `types` neuen Typ ergänzen.
3. Für optionale Zusatzwerte `fields` definieren.
4. Datei speichern.
5. Fusion/Add-in neu starten.
6. Im Katalogdialog prüfen, ob Typ und Felder sichtbar sind.

## CSV-Verhalten

CSV-Kopfzeile bleibt unverändert.

Zusatzdaten landen in der Spalte `attributes`, z. B.:

```text
DIYGarageCut.catalog:panel_core_thickness=18.0
DIYGarageCut.catalog:panel_core_thickness_unit=mm
DIYGarageCut.context:document_length_unit=mm
```

## Wichtige Hinweise

- Werte werden intern in der konfigurierten `storage_unit` gespeichert.
- UI-Eingaben im Catalog werden validiert (min/max/step).
- Für bestehende Daten können `legacy_keys` genutzt werden, damit alte Feldnamen weiter gelesen werden.
