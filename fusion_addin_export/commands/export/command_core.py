import adsk.core
import adsk.fusion
import csv
import json
import locale
import os
import re

import export_config as config
from shared.catalog import get_type_fields, get_type_label, load_catalog

_ATTRIBUTE_GROUP = "DIYGarageCut.part_metadata"
_ATTR_KEY_TRIM_ALLOWANCE_MM = "trim_allowance_mm"
_ATTR_KEY_GRAIN_DIRECTION = "grain_direction"
_ATTR_KEY_EDGE_FRONT = "edge_front"
_ATTR_KEY_EDGE_BACK = "edge_back"
_ATTR_KEY_EDGE_LEFT = "edge_left"
_ATTR_KEY_EDGE_RIGHT = "edge_right"
_TYPE_FIELD_HAS_GRAIN = "sheet_has_grain"
_TYPE_FIELD_DEFAULT_GRAIN_DIRECTION = "sheet_default_grain_direction"
_TYPE_FIELD_EDGE_THICKNESS = "edge_thickness"

_handlers = []
_active_panel_id = None
_is_started = False
_command_created_handler = None
_ui_lang = "de"
_export_settings_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "export_config.json")
)
_export_settings_cache = None


class _CommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def notify(self, args):
        event_args = adsk.core.CommandCreatedEventArgs.cast(args)
        cmd = event_args.command
        on_execute = _CommandExecuteHandler()
        cmd.execute.add(on_execute)
        _handlers.append(on_execute)


class _CommandExecuteHandler(adsk.core.CommandEventHandler):
    def notify(self, args):
        app = adsk.core.Application.get()
        ui = app.userInterface if app else None
        if not app or not ui:
            print("CSV-Export: App/UI nicht verfuegbar.")
            return

        try:
            _run_export_mode(app, ui)
        except Exception as exc:
            print(f"Export-Command-Fehler: {exc}")
            ui.messageBox(f"CSV-Export fehlgeschlagen:\n{exc}")


def _run_export_mode(app, ui):
    global _ui_lang
    _ui_lang = _detect_ui_lang()

    export_path = _pick_export_path(app, ui)
    if not export_path:
        ui.messageBox("CSV-Export abgebrochen. Es wurde keine Datei geschrieben.")
        print("CSV-Export: Vom Nutzer abgebrochen.")
        return

    catalog = _try_load_catalog()
    rows = _collect_visible_body_rows(app, catalog)
    if not rows:
        ui.messageBox("Keine sichtbaren Bodies gefunden. Es wurde keine CSV erzeugt.")
        print("CSV-Export: Keine sichtbaren Bodies gefunden.")
        return

    _write_csv(export_path, rows)
    ui.messageBox(f"CSV-Export abgeschlossen.\nDatei: {export_path}\nBodies: {len(rows)}")
    print(f"CSV-Export abgeschlossen: {export_path} ({len(rows)} Bodies)")


def _pick_export_path(app, ui):
    try:
        dialog = ui.createFileDialog()
        dialog.isMultiSelectEnabled = False
        dialog.title = "CSV speichern"
        dialog.filter = "CSV-Dateien (*.csv);;Alle Dateien (*.*)"
        dialog.filterIndex = 0
        dialog.initialFilename = _build_default_export_filename(app)
        result = dialog.showSave()
        filename = dialog.filename if getattr(dialog, "filename", None) else ""
        if result == adsk.core.DialogResults.DialogOK and filename:
            return filename
        return None
    except Exception as exc:
        print(f"CSV-Export: Dateidialog fehlgeschlagen: {exc}")
        return None


def _build_default_export_filename(app):
    base_name = "fusion_bodies_export"
    try:
        document = app.activeDocument if app else None
        name = document.name if document else ""
        if name:
            if name.lower().endswith(".f3d"):
                name = name[:-4]
            cleaned = re.sub(r'[<>:"/\\|?*]', "_", name).strip()
            if cleaned:
                base_name = cleaned
    except Exception as exc:
        print(f"CSV-Export: Konnte Dokumentnamen nicht lesen: {exc}")
    return f"{base_name}.csv"


def _collect_visible_body_rows(app, catalog):
    rows = []
    seen_tokens = set()
    design = adsk.fusion.Design.cast(app.activeProduct)
    if not design:
        print("CSV-Export: Kein aktives Fusion-Design.")
        return rows

    root = design.rootComponent
    if root:
        _append_component_bodies(root, rows, seen_tokens, catalog)
        _append_occurrence_bodies_recursive(root.occurrences, rows, seen_tokens, catalog)
    return rows


def _append_component_bodies(component, rows, seen_tokens, catalog):
    try:
        for body in component.bRepBodies:
            _append_body_row_if_visible(body, rows, seen_tokens, catalog)
    except Exception as exc:
        if isinstance(exc, RuntimeError):
            raise
        raise RuntimeError(f"CSV-Export: Component-Bodies konnten nicht gelesen werden: {exc}") from exc


def _append_occurrence_bodies_recursive(occurrences, rows, seen_tokens, catalog):
    try:
        if not occurrences:
            return
        for occ in occurrences:
            try:
                for body in occ.bRepBodies:
                    _append_body_row_if_visible(body, rows, seen_tokens, catalog)
                _append_occurrence_bodies_recursive(occ.childOccurrences, rows, seen_tokens, catalog)
            except Exception as exc:
                if isinstance(exc, RuntimeError):
                    raise
                raise RuntimeError(f"CSV-Export: Occurrence konnte nicht gelesen werden: {exc}") from exc
    except Exception as exc:
        if isinstance(exc, RuntimeError):
            raise
        raise RuntimeError(f"CSV-Export: Occurrence-Liste konnte nicht gelesen werden: {exc}") from exc


def _append_body_row_if_visible(body, rows, seen_tokens, catalog):
    if not body:
        return
    try:
        if not body.isVisible:
            return
        token = body.entityToken or f"id_{id(body)}"
        if token in seen_tokens:
            return
        seen_tokens.add(token)
        rows.append(_body_to_csv_row(body, catalog))
    except Exception as exc:
        if isinstance(exc, RuntimeError):
            raise
        if isinstance(exc, ValueError):
            raise RuntimeError(str(exc)) from exc
        body_name = _safe_body_name(body)
        raise RuntimeError(f"CSV-Export: Body '{body_name}' konnte nicht exportiert werden: {exc}") from exc


def _body_to_csv_row(body, catalog):
    name = _safe_body_name(body)
    catalog_item = _resolve_catalog_material_ref(body, catalog)
    length, width, thickness = _get_dimensions_for_export(body, catalog_item.type)
    material_type = _type_label(catalog_item.type)
    trim_allowance_mm = _resolve_trim_allowance_for_export(body, catalog_item.type)
    grain_direction = _resolve_grain_direction_for_export(body, catalog_item)
    material_name = str(catalog_item.name or "").strip() or "-"
    export_material_name = _build_export_material_name(catalog_item, thickness, width, material_name)
    edge_front = _resolve_edge_export_for_side(body, catalog, _ATTR_KEY_EDGE_FRONT)
    edge_back = _resolve_edge_export_for_side(body, catalog, _ATTR_KEY_EDGE_BACK)
    edge_left = _resolve_edge_export_for_side(body, catalog, _ATTR_KEY_EDGE_LEFT)
    edge_right = _resolve_edge_export_for_side(body, catalog, _ATTR_KEY_EDGE_RIGHT)
    return [
        name,
        length,
        width,
        thickness,
        material_type,
        trim_allowance_mm,
        grain_direction,
        material_name,
        export_material_name,
        edge_front[0],
        edge_front[1],
        edge_front[2],
        edge_back[0],
        edge_back[1],
        edge_back[2],
        edge_left[0],
        edge_left[1],
        edge_left[2],
        edge_right[0],
        edge_right[1],
        edge_right[2],
    ]


def _safe_body_name(body):
    try:
        if body.name:
            return body.name
    except Exception:
        pass
    return "-"


def _get_dimensions_for_export(body, material_type):
    try:
        bbox = body.boundingBox
        min_p = bbox.minPoint
        max_p = bbox.maxPoint
        dims_mm = sorted(
            [
                abs(max_p.x - min_p.x) * 10.0,
                abs(max_p.y - min_p.y) * 10.0,
                abs(max_p.z - min_p.z) * 10.0,
            ]
        )
        # Index 0 = thickness (smallest), 1 = width (middle), 2 = length (largest)
        thickness = dims_mm[0]
        width = dims_mm[1]
        length = dims_mm[2]
        if str(material_type or "").strip() == "bar":
            return _fmt_mm(length), _fmt_mm(width), _fmt_mm(thickness)
        return _fmt_mm(length), _fmt_mm(width), _fmt_mm(thickness)
    except Exception as exc:
        print(f"CSV-Export: BoundingBox-Fehler bei Body: {exc}")
        return "-", "-", "-"


def _fmt_mm(value):
    try:
        numeric = float(value)
        return _format_numeric_for_export(numeric)
    except Exception:
        return "-"


def _safe_name(obj):
    try:
        if obj and obj.name:
            return obj.name
    except Exception:
        pass
    return "-"


def _collect_body_attributes(body):
    out = []
    seen = set()

    targets = [body]
    native = _try_get_native_object(body)
    if native is not None and native is not body:
        targets.append(native)

    for target in targets:
        _append_attribute_rows(target, out, seen)

    tokens = []
    body_token = _get_entity_token(body)
    if body_token:
        tokens.append(body_token)
    native_token = _get_entity_token(native) if native is not None else None
    if native_token and native_token not in tokens:
        tokens.append(native_token)
    for token in tokens:
        for row in _collect_design_fallback_attributes(token):
            marker = (row[0], row[1], row[2])
            if marker in seen:
                continue
            seen.add(marker)
            out.append(row)
    return out


def _append_attribute_rows(entity, out, seen):
    if entity is None:
        return
    attributes = getattr(entity, "attributes", None)
    if attributes is None or attributes.count < 1:
        return
    for i in range(attributes.count):
        attr = attributes.item(i)
        if not attr:
            continue
        group = attr.groupName if attr.groupName else "-"
        name = attr.name if attr.name else "-"
        value = attr.value if attr.value is not None else "-"
        marker = (group, name, value)
        if marker in seen:
            continue
        seen.add(marker)
        out.append(marker)


def _try_get_native_object(entity):
    if entity is None:
        return None
    try:
        return getattr(entity, "nativeObject", None)
    except Exception:
        return None


def _resolve_catalog_material_ref(body, catalog):
    if not catalog:
        raise ValueError("Catalog nicht geladen.")
    body_name = _safe_body_name(body)
    attributes = _collect_body_attributes(body)
    material_id, source = _resolve_catalog_material_id(attributes)
    if not material_id:
        raise ValueError(
            f"Body '{body_name}' hat keine 'material_id' im Attribut-Set "
            f"('{_ATTRIBUTE_GROUP}:material_id')."
        )
    if source == "material_typ":
        raise ValueError(
            f"Body '{body_name}' verwendet Legacy-Key 'material_typ' ohne kanonische 'material_id'. "
            "Bitte Daten auf 'material_id' migrieren."
        )
    item = catalog.get(material_id)
    if not item:
        raise ValueError(
            f"Body '{body_name}' referenziert material_id '{material_id}', "
            "die nicht in catalog.json existiert."
        )
    return item


def _resolve_catalog_material_id(attributes):
    # Migration contract: material_id is canonical, material_typ is legacy fallback.
    key_priority = ("material_id", "material_typ")
    key_buckets = {key: [] for key in key_priority}
    for group, key, value in attributes:
        if key not in key_buckets:
            continue
        value_text = str(value).strip() if value is not None else ""
        if value_text in ("", "-"):
            continue
        key_buckets[key].append((str(group or "").strip(), value_text))

    for key in key_priority:
        entries = key_buckets.get(key, [])
        if not entries:
            continue
        for group, value in entries:
            if group == "DIYGarageCut.part_metadata":
                return value, key
        return entries[0][1], key
    return None, None


def _resolve_trim_allowance_for_export(body, material_type):
    if not _material_type_supports_trim_allowance(material_type):
        return ""
    attrs = _collect_body_attributes(body)
    for group, key, value in attrs:
        if group != _ATTRIBUTE_GROUP:
            continue
        if key != _ATTR_KEY_TRIM_ALLOWANCE_MM:
            continue
        value_text = str(value).strip() if value is not None else ""
        if value_text in ("", "-"):
            return ""
        try:
            return _fmt_mm(float(value_text.replace(",", ".")))
        except Exception:
            return value_text
    return ""


def _material_type_supports_trim_allowance(material_type):
    type_name = str(material_type or "").strip()
    if not type_name:
        return False
    for field in get_type_fields(type_name):
        if str(field.get("key", "")).strip() == "sheet_default_trim_allowance":
            return True
    return False


def _resolve_grain_direction_for_export(body, catalog_item):
    if not _material_type_supports_grain(catalog_item.type):
        return "none"
    has_grain = str((catalog_item.properties or {}).get(_TYPE_FIELD_HAS_GRAIN, "none") or "none").strip().lower()
    if has_grain != "yes":
        return "none"
    attrs = _collect_body_attributes(body)
    for group, key, value in attrs:
        if group != _ATTRIBUTE_GROUP:
            continue
        if key != _ATTR_KEY_GRAIN_DIRECTION:
            continue
        value_text = str(value).strip().lower() if value is not None else ""
        if value_text in ("none", "length", "width"):
            return value_text
        return "none"

    default_direction = str((catalog_item.properties or {}).get(_TYPE_FIELD_DEFAULT_GRAIN_DIRECTION, "none") or "none").strip().lower()
    if default_direction in ("none", "length", "width"):
        return default_direction
    return "none"


def _resolve_edge_export_for_side(body, catalog, attr_key):
    attrs = _collect_body_attributes(body)
    edge_id = ""
    for group, key, value in attrs:
        if group != _ATTRIBUTE_GROUP:
            continue
        if key != attr_key:
            continue
        edge_id = str(value or "").strip()
        break

    if not edge_id:
        return ("", "", "")

    edge_item = catalog.get(edge_id)
    if not edge_item:
        raise ValueError(
            f"Body '{_safe_body_name(body)}' referenziert Kantenmaterial '{edge_id}', "
            "das nicht in catalog.json existiert."
        )
    if edge_item.type != "edge":
        raise ValueError(
            f"Body '{_safe_body_name(body)}' referenziert '{edge_id}', "
            "aber der Katalogeintrag ist nicht vom Typ 'edge'."
        )

    thickness = _extract_edge_thickness(edge_item)
    return (
        edge_item.id,
        str(edge_item.name or "").strip(),
        _fmt_mm(thickness),
    )


def _extract_edge_thickness(catalog_item):
    raw = (catalog_item.properties or {}).get(_TYPE_FIELD_EDGE_THICKNESS)
    if raw in (None, ""):
        return 0.0
    try:
        numeric = float(raw)
    except Exception as exc:
        raise ValueError(
            f"Katalogeintrag '{catalog_item.id}' hat ungültige edge_thickness: {raw}"
        ) from exc
    if numeric < 0:
        raise ValueError(
            f"Katalogeintrag '{catalog_item.id}' hat negative edge_thickness: {raw}"
        )
    return numeric


def _material_type_supports_grain(material_type):
    type_name = str(material_type or "").strip()
    if not type_name:
        return False
    keys = {str(field.get("key", "")).strip() for field in get_type_fields(type_name)}
    return _TYPE_FIELD_HAS_GRAIN in keys and _TYPE_FIELD_DEFAULT_GRAIN_DIRECTION in keys


def _build_export_material_name(catalog_item, thickness, width, material_name):
    mode = _get_csv_material_name_mode()
    if mode == "material":
        return material_name

    thickness_label = _compact_dimension_label(thickness)
    width_label = _compact_dimension_label(width)
    type_id = str(getattr(catalog_item, "type", "") or "").strip().lower()
    if type_id == "bar":
        if _is_export_dim_value(thickness_label) and _is_export_dim_value(width_label):
            return f"{material_name} {thickness_label}x{width_label}"
        return material_name
    if type_id == "sheet":
        if _is_export_dim_value(thickness_label):
            return f"{material_name} {thickness_label}"
        return material_name
    return material_name


def _is_export_dim_value(value):
    text = str(value or "").strip()
    if not text:
        return False
    if text == "-":
        return False
    return True


def _compact_dimension_label(value):
    text = str(value or "").strip()
    if not text or text == "-":
        return text
    normalized = text.replace(",", ".")
    try:
        numeric = float(normalized)
    except Exception:
        return text
    if abs(numeric - round(numeric)) < 1e-9:
        return str(int(round(numeric)))
    return text


def _write_csv(path, rows):
    header = [
        "body_name",
        "length_mm",
        "width_mm",
        "thickness_mm",
        "material_type",
        "trim_allowance_mm",
        "grain_direction",
        "material",
        "material_name",
        "edge_front_id",
        "edge_front_name",
        "edge_front_thickness_mm",
        "edge_back_id",
        "edge_back_name",
        "edge_back_thickness_mm",
        "edge_left_id",
        "edge_left_name",
        "edge_left_thickness_mm",
        "edge_right_id",
        "edge_right_name",
        "edge_right_thickness_mm",
    ]
    with open(path, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file, delimiter=_get_csv_delimiter())
        writer.writerow(header)
        decimal_separator = _get_csv_decimal_separator()
        decimals = _get_csv_decimals()
        decimal_mode = _get_csv_decimal_mode()
        for row in rows:
            writer.writerow(
                _format_csv_row_for_numeric_format(row, decimal_separator, decimals, decimal_mode)
            )


def _get_entity_token(entity):
    try:
        token = getattr(entity, "entityToken", None)
        if token:
            return str(token)
    except Exception:
        pass
    return None


def _collect_design_fallback_attributes(token):
    try:
        app = adsk.core.Application.get()
        design = adsk.fusion.Design.cast(app.activeProduct) if app else None
        if not design:
            return []

        attrs = None
        root = getattr(design, "rootComponent", None)
        if root:
            attrs = getattr(root, "attributes", None)
        if attrs is None:
            attrs = getattr(design, "attributes", None)
        if attrs is None or attrs.count < 1:
            return []

        prefix = f"body_token::{token}::"
        mapped = []
        for i in range(attrs.count):
            attr = attrs.item(i)
            if not attr:
                continue
            name = attr.name or ""
            if not name.startswith(prefix):
                continue
            key = name[len(prefix):]
            val = attr.value if attr.value is not None else "-"
            mapped.append((attr.groupName if attr.groupName else "-", key, val))
        return mapped
    except Exception as exc:
        print(f"CSV-Export: Design-Fallback-Attribute konnten nicht gelesen werden: {exc}")
        return []


def _try_load_catalog():
    try:
        return load_catalog()
    except Exception as exc:
        raise RuntimeError(f"Catalog konnte nicht geladen werden: {exc}") from exc


def _load_export_settings():
    global _export_settings_cache
    if _export_settings_cache is not None:
        return _export_settings_cache

    settings = {
        "csv_delimiter": ";",
        "csv_decimal_separator": ".",
        "csv_decimals": 1,
        "csv_decimal_mode": "fixed",
        "csv_material_name_mode": "material",
    }
    try:
        if os.path.exists(_export_settings_path):
            with open(_export_settings_path, "r", encoding="utf-8") as handle:
                loaded = json.load(handle)
            if isinstance(loaded, dict):
                if "csv_delimiter" in loaded:
                    settings["csv_delimiter"] = loaded.get("csv_delimiter")
                if "csv_decimal_separator" in loaded:
                    settings["csv_decimal_separator"] = loaded.get("csv_decimal_separator")
                if "csv_decimals" in loaded:
                    settings["csv_decimals"] = loaded.get("csv_decimals")
                if "csv_decimal_mode" in loaded:
                    settings["csv_decimal_mode"] = loaded.get("csv_decimal_mode")
                if "csv_material_name_mode" in loaded:
                    settings["csv_material_name_mode"] = loaded.get("csv_material_name_mode")
    except Exception as exc:
        print(f"CSV-Export: export_config.json konnte nicht gelesen werden: {exc}")

    _export_settings_cache = settings
    return settings


def _get_csv_delimiter():
    raw = _load_export_settings().get("csv_delimiter", ";")
    text = str(raw or "").strip()
    if text in ("\\t", "tab"):
        return "\t"
    if len(text) == 1:
        return text
    return ";"


def _get_csv_decimal_separator():
    raw = _load_export_settings().get("csv_decimal_separator", ".")
    text = str(raw or "").strip()
    if text in (".", ","):
        return text
    return "."


def _get_csv_decimals():
    raw = _load_export_settings().get("csv_decimals", 1)
    try:
        value = int(raw)
    except Exception:
        return 1
    if value < 0:
        return 0
    if value > 6:
        return 6
    return value


def _get_csv_decimal_mode():
    raw = _load_export_settings().get("csv_decimal_mode", "fixed")
    text = str(raw or "").strip().lower()
    if text in ("fixed", "trim"):
        return text
    return "fixed"


def _get_csv_material_name_mode():
    raw = _load_export_settings().get("csv_material_name_mode", "material")
    text = str(raw or "").strip().lower()
    if text in ("material", "typed_dimensions"):
        return text
    return "material"


def _format_csv_row_for_numeric_format(row, decimal_separator, decimals, decimal_mode):
    # Numeric export columns by contract:
    # 1=length_mm, 2=width_mm, 3=thickness_mm, 5=trim_allowance_mm
    # 11/14/17/20=edge_*_thickness_mm
    numeric_indices = {1, 2, 3, 5, 11, 14, 17, 20}
    out = list(row)
    for idx in numeric_indices:
        if idx >= len(out):
            continue
        out[idx] = _format_csv_numeric_cell(out[idx], decimal_separator, decimals, decimal_mode)
    return out


def _format_csv_numeric_cell(value, decimal_separator, decimals, decimal_mode):
    text = str(value or "").strip()
    if not text:
        return text
    normalized = text.replace(",", ".")
    try:
        numeric = float(normalized)
    except Exception:
        return text

    return _format_numeric_for_export(
        numeric,
        decimal_separator=decimal_separator,
        decimals=decimals,
        decimal_mode=decimal_mode,
    )


def _format_numeric_for_export(numeric, decimal_separator=None, decimals=None, decimal_mode=None):
    if decimal_separator is None:
        decimal_separator = _get_csv_decimal_separator()
    if decimals is None:
        decimals = _get_csv_decimals()
    if decimal_mode is None:
        decimal_mode = _get_csv_decimal_mode()

    if decimal_mode == "fixed":
        formatted = f"{float(numeric):.{int(decimals)}f}"
    else:
        formatted = f"{float(numeric):.{int(decimals)}f}".rstrip("0").rstrip(".")
        if formatted == "-0":
            formatted = "0"

    if decimal_separator == ",":
        return formatted.replace(".", ",")
    return formatted


def _detect_ui_lang():
    app = adsk.core.Application.get()
    candidates = []
    try:
        prefs = getattr(app, "preferences", None)
        gp = getattr(prefs, "generalPreferences", None) if prefs else None
        for attr in ("userLanguage", "language"):
            val = getattr(gp, attr, None)
            if val is not None:
                candidates.append(str(val))
    except Exception:
        pass

    try:
        loc = locale.getdefaultlocale()
        if loc and loc[0]:
            candidates.append(loc[0])
    except Exception:
        pass

    for candidate in candidates:
        cand = (candidate or "").lower()
        if "de" in cand:
            return "de"
        if "en" in cand:
            return "en"
    return "de"


def _type_label(type_id):
    return get_type_label(type_id, _ui_lang)


def _get_or_create_panel(workspace):
    global _active_panel_id

    primary = workspace.toolbarPanels.itemById(config.PRIMARY_PANEL_ID)
    if primary:
        _active_panel_id = config.PRIMARY_PANEL_ID
        return primary

    for panel_id in config.PANEL_IDS:
        candidate = workspace.toolbarPanels.itemById(panel_id)
        if candidate:
            _active_panel_id = panel_id
            return candidate

    tab = workspace.toolbarTabs.itemById(config.CUSTOM_TAB_ID)
    if not tab:
        return None

    panel = tab.toolbarPanels.itemById(config.CUSTOM_PANEL_ID)
    if panel:
        _active_panel_id = config.CUSTOM_PANEL_ID
        return panel

    panel = tab.toolbarPanels.add(config.CUSTOM_PANEL_ID, config.CUSTOM_PANEL_NAME, "", False)
    _active_panel_id = config.CUSTOM_PANEL_ID
    return panel


def start():
    global _active_panel_id, _is_started, _command_created_handler
    if _is_started:
        return

    app = adsk.core.Application.get()
    ui = app.userInterface

    cmd_def = ui.commandDefinitions.itemById(config.COMMAND_ID)
    if not cmd_def:
        cmd_def = ui.commandDefinitions.addButtonDefinition(
            config.COMMAND_ID,
            config.COMMAND_NAME,
            config.COMMAND_TOOLTIP,
            config.COMMAND_RESOURCES,
        )

    _command_created_handler = _CommandCreatedHandler()
    cmd_def.commandCreated.add(_command_created_handler)
    _handlers.append(_command_created_handler)
    _is_started = True

    workspace = ui.workspaces.itemById(config.WORKSPACE_ID)
    if not workspace:
        return

    panel = _get_or_create_panel(workspace)
    if not panel:
        return

    control = panel.controls.itemById(config.COMMAND_ID)
    if not control:
        control = panel.controls.addCommand(cmd_def)

    if control:
        try:
            control.isPromotedByDefault = True
            control.isPromoted = True
        except Exception:
            pass


def stop():
    global _active_panel_id, _is_started, _command_created_handler
    app = adsk.core.Application.get()
    ui = app.userInterface
    cmd_def = ui.commandDefinitions.itemById(config.COMMAND_ID)

    if cmd_def and _command_created_handler:
        try:
            cmd_def.commandCreated.remove(_command_created_handler)
        except Exception:
            pass
        _command_created_handler = None

    workspace = ui.workspaces.itemById(config.WORKSPACE_ID)
    if workspace:
        panel = workspace.toolbarPanels.itemById(_active_panel_id) if _active_panel_id else None
        if panel:
            control = panel.controls.itemById(config.COMMAND_ID)
            if control:
                control.deleteMe()

    if cmd_def:
        cmd_def.deleteMe()

    _handlers.clear()
    _active_panel_id = None
    _is_started = False
