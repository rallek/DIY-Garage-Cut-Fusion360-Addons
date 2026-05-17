import os
import pathlib
import re
import struct
import tempfile
import urllib.parse
import zlib
import json
import colorsys

import adsk.core
import adsk.fusion

import export_config as config
from shared.catalog import CATALOG_TYPES, CatalogItem, load_catalog, save_catalog, upsert_catalog_item

_handlers = []
_active_panel_id = None
_is_started = False
_command_created_handler = None
_is_syncing = False
_last_selection_label = None

_INPUT_SELECTION = "diygc_catalog_selection"
_INPUT_NEW_ENTRY = "diygc_catalog_new_entry"
_INPUT_ID_VIEW = "diygc_catalog_id_view"
_INPUT_TYPE = "diygc_catalog_type"
_INPUT_NAME = "diygc_catalog_name"
_INPUT_APPEARANCE = "diygc_catalog_appearance"
_INPUT_APPEARANCE_PREVIEW = "diygc_catalog_appearance_preview"
_INPUT_PREVIEW_HINT = "diygc_catalog_preview_hint"
_INPUT_PREVIEW_DEBUG = "diygc_catalog_preview_debug"
_INPUT_SAVE = "diygc_catalog_save"
_INPUT_STATUS = "diygc_catalog_status"
_INPUT_LIST = "diygc_catalog_list"

_APPEARANCE_NONE_LABEL = "(Bitte waehlen)"
_PREVIEW_SIZE = 84
_preview_cache_dir = os.path.abspath(
    os.path.join(tempfile.gettempdir(), "diygc_catalog_preview_cache")
)
_preview_html_dir = os.path.abspath(
    os.path.join(tempfile.gettempdir(), "diygc_catalog_preview_html")
)
_preview_config_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "catalog_preview_config.json")
)
_preview_config_cache = None
_texture_file_index_cache = {}


class _CommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def notify(self, args):
        event_args = adsk.core.CommandCreatedEventArgs.cast(args)
        cmd = event_args.command
        inputs = cmd.commandInputs

        try:
            cmd.okButtonText = "Schliessen"
        except Exception:
            pass

        selection = inputs.addDropDownCommandInput(
            _INPUT_SELECTION,
            "Vorhandene Eintraege",
            adsk.core.DropDownStyles.TextListDropDownStyle,
        )
        selection.listItems.add("(Neu anlegen)", True)

        inputs.addBoolValueInput(_INPUT_NEW_ENTRY, "Neuen Eintrag anlegen", True, "", True)
        id_box = inputs.addTextBoxCommandInput(_INPUT_ID_VIEW, "Interne ID", "-", 1, True)
        id_box.isFullWidth = False

        type_input = inputs.addDropDownCommandInput(
            _INPUT_TYPE,
            "Typ",
            adsk.core.DropDownStyles.TextListDropDownStyle,
        )
        for i, item_type in enumerate(sorted(CATALOG_TYPES)):
            type_input.listItems.add(item_type, i == 0)

        inputs.addStringValueInput(_INPUT_NAME, "Name", "")

        appearance_pick = inputs.addDropDownCommandInput(
            _INPUT_APPEARANCE,
            "Appearance aus Fusion",
            adsk.core.DropDownStyles.TextListDropDownStyle,
        )
        appearance_pick.listItems.add(_APPEARANCE_NONE_LABEL, True)

        preview = inputs.addBrowserCommandInput(
            _INPUT_APPEARANCE_PREVIEW,
            "Vorschau",
            _build_preview_html_url(_ensure_preview_png("none", (160, 160, 160)), "Keine Auswahl"),
            170,
            230,
        )
        preview.isFullWidth = True
        preview_hint = inputs.addTextBoxCommandInput(_INPUT_PREVIEW_HINT, "", "", 1, True)
        preview_hint.isFullWidth = True
        preview_debug = inputs.addTextBoxCommandInput(_INPUT_PREVIEW_DEBUG, "Preview-Debug", "", 8, True)
        preview_debug.isFullWidth = True

        inputs.addBoolValueInput(_INPUT_SAVE, "Speichern", False, "", False)
        status = inputs.addTextBoxCommandInput(_INPUT_STATUS, "", "", 2, True)
        status.isFullWidth = True
        list_box = inputs.addTextBoxCommandInput(_INPUT_LIST, "Kataloguebersicht", "-", 12, True)
        list_box.isFullWidth = True

        _populate_appearance_items(appearance_pick)
        _populate_existing_items(selection)
        _sync_inputs(inputs)

        on_input_changed = _InputChangedHandler()
        cmd.inputChanged.add(on_input_changed)
        _handlers.append(on_input_changed)

        on_execute = _CommandExecuteHandler()
        cmd.execute.add(on_execute)
        _handlers.append(on_execute)


class _InputChangedHandler(adsk.core.InputChangedEventHandler):
    def notify(self, args):
        global _is_syncing
        if _is_syncing:
            return
        try:
            event_args = adsk.core.InputChangedEventArgs.cast(args)
            changed = event_args.input if event_args else None
            command = event_args.firingEvent.sender if event_args else None
            inputs = command.commandInputs if command else None
            if not inputs:
                return

            changed_id = changed.id if changed else ""
            if changed_id == _INPUT_SAVE:
                if _read_bool(inputs, _INPUT_SAVE, False):
                    _set_bool(inputs, _INPUT_SAVE, False)
                    try:
                        _save_from_inputs(inputs)
                    except Exception as exc:
                        _set_status(inputs, f"Fehler beim Speichern: {exc}")
                return

            _sync_inputs(inputs, changed_id=changed_id)
        except Exception as exc:
            print(f"Catalog-InputChanged-Fehler: {exc}")


class _CommandExecuteHandler(adsk.core.CommandEventHandler):
    def notify(self, args):
        # Speichern erfolgt bewusst ueber den separaten "Speichern"-Button,
        # damit Validierungsfehler den Dialog nicht schliessen.
        return


def _save_from_inputs(inputs):
    catalog = _load_catalog_data()
    is_new = _read_bool(inputs, _INPUT_NEW_ENTRY, True)
    current_id = _read_id_from_view(inputs)
    item_type = _read_dropdown(inputs, _INPUT_TYPE)
    item_name = _read_string(inputs, _INPUT_NAME)
    appearance = _read_dropdown(inputs, _INPUT_APPEARANCE)

    if not item_type or item_type not in CATALOG_TYPES:
        _set_status(inputs, "Fehler: Bitte gueltigen Typ waehlen.")
        return
    if not item_name:
        _set_status(inputs, "Fehler: Name darf nicht leer sein.")
        return
    if not appearance or appearance == _APPEARANCE_NONE_LABEL:
        _set_status(inputs, "Fehler: Bitte Appearance auswaehlen.")
        return

    appearance_obj = _find_appearance_by_name(appearance)

    if is_new:
        item_id = _generate_internal_id(catalog, item_type, item_name)
        if catalog.get(item_id):
            _set_status(inputs, f"Fehler: Interne ID bereits vorhanden: {item_id}")
            return
        base_properties = {}
    else:
        item_id = current_id
        if not item_id:
            _set_status(inputs, "Fehler: Kein bestehender Eintrag ausgewaehlt.")
            return
        existing_item = catalog.get(item_id)
        if not existing_item:
            _set_status(inputs, f"Fehler: Eintrag nicht gefunden: {item_id}")
            return
        base_properties = dict(existing_item.properties or {})

    base_properties.update(_build_appearance_metadata(appearance, appearance_obj))

    item = CatalogItem.from_dict(
        {
            "id": item_id,
            "type": item_type,
            "name": item_name,
            "appearance": appearance,
            **base_properties,
        }
    )
    next_catalog = upsert_catalog_item(catalog, item)
    save_catalog(next_catalog)

    _set_status(inputs, f"Gespeichert: {item.id}")
    _refresh_selection_after_save(inputs, item.id)
    _set_bool(inputs, _INPUT_NEW_ENTRY, False)
    _sync_inputs(inputs)


def _load_catalog_data():
    return load_catalog()


def _populate_existing_items(dropdown, selected_id=None):
    dropdown.listItems.clear()
    dropdown.listItems.add("(Neu anlegen)", selected_id is None)
    catalog = _load_catalog_data()
    for item in sorted(catalog.items, key=lambda x: x.id.lower()):
        label = f"{item.id} | {item.type} | {item.name}"
        dropdown.listItems.add(label, selected_id == item.id)


def _refresh_selection_after_save(inputs, selected_id):
    selection = adsk.core.DropDownCommandInput.cast(inputs.itemById(_INPUT_SELECTION))
    if not selection:
        return
    _populate_existing_items(selection, selected_id=selected_id)


def _sync_inputs(inputs, changed_id=None):
    global _is_syncing, _last_selection_label
    _is_syncing = True
    try:
        selection = adsk.core.DropDownCommandInput.cast(inputs.itemById(_INPUT_SELECTION))
        if not selection or not selection.selectedItem:
            _refresh_list_overview(inputs)
            return

        selected_text = selection.selectedItem.name or ""
        selected_id = selected_text.split("|", 1)[0].strip() if "|" in selected_text else ""
        selected_item = _load_catalog_data().get(selected_id) if selected_id else None

        is_new_mode = _read_bool(inputs, _INPUT_NEW_ENTRY, True)
        if selected_item and selected_text != _last_selection_label:
            _set_bool(inputs, _INPUT_NEW_ENTRY, False)
            is_new_mode = False

        if not selected_item:
            is_new_mode = True
            _set_bool(inputs, _INPUT_NEW_ENTRY, True)

        should_reload_from_catalog = (
            selected_item
            and not is_new_mode
            and changed_id in (None, _INPUT_SELECTION, _INPUT_NEW_ENTRY)
        )

        if should_reload_from_catalog:
            _set_dropdown(inputs, _INPUT_TYPE, selected_item.type)
            _set_string(inputs, _INPUT_NAME, selected_item.name)
            _set_dropdown(inputs, _INPUT_APPEARANCE, selected_item.appearance)
            _set_id_view(inputs, selected_item.id)
        else:
            if selected_item and not is_new_mode:
                _set_id_view(inputs, selected_item.id)
            else:
                current_name = _read_string(inputs, _INPUT_NAME)
                current_type = _read_dropdown(inputs, _INPUT_TYPE)
                _set_id_view(inputs, _generate_internal_id(_load_catalog_data(), current_type, current_name))

        _refresh_appearance_preview(inputs)
        _refresh_list_overview(inputs)
        _last_selection_label = selected_text
    finally:
        _is_syncing = False


def _set_id_view(inputs, value):
    box = adsk.core.TextBoxCommandInput.cast(inputs.itemById(_INPUT_ID_VIEW))
    if box:
        box.text = value if value else "-"


def _read_id_from_view(inputs):
    box = adsk.core.TextBoxCommandInput.cast(inputs.itemById(_INPUT_ID_VIEW))
    if not box:
        return ""
    value = (box.text or "").strip()
    return "" if value == "-" else value


def _set_status(inputs, message):
    status = adsk.core.TextBoxCommandInput.cast(inputs.itemById(_INPUT_STATUS))
    if status:
        status.text = message or ""


def _refresh_list_overview(inputs):
    box = adsk.core.TextBoxCommandInput.cast(inputs.itemById(_INPUT_LIST))
    if not box:
        return
    try:
        catalog = _load_catalog_data()
        if not catalog.items:
            box.text = "Keine Eintraege vorhanden."
            return
        lines = []
        for item in sorted(catalog.items, key=lambda x: x.id.lower()):
            lines.append(f"{item.id} | {item.type} | {item.name} | {item.appearance}")
        box.text = "\n".join(lines)
    except Exception as exc:
        box.text = f"Katalog kann nicht geladen werden: {exc}"


def _populate_appearance_items(dropdown):
    dropdown.listItems.clear()
    dropdown.listItems.add(_APPEARANCE_NONE_LABEL, True)
    for name in _collect_appearance_names():
        dropdown.listItems.add(name, False)


def _collect_appearance_names():
    seen = set()
    names = []

    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct) if app else None
    if design:
        try:
            appearances = getattr(design, "appearances", None)
            count = appearances.count if appearances else 0
            for i in range(count):
                entry = appearances.item(i)
                name = (entry.name or "").strip() if entry else ""
                if not name:
                    continue
                key = name.lower()
                if key in seen:
                    continue
                seen.add(key)
                names.append(name)
        except Exception as exc:
            print(f"Catalog: Design-Appearances konnten nicht gelesen werden: {exc}")

    if app:
        try:
            libs = getattr(app, "materialLibraries", None)
            lib_count = libs.count if libs else 0
            for li in range(lib_count):
                library = libs.item(li)
                if not library:
                    continue
                appearances = getattr(library, "appearances", None)
                app_count = appearances.count if appearances else 0
                for ai in range(app_count):
                    entry = appearances.item(ai)
                    name = (entry.name or "").strip() if entry else ""
                    if not name:
                        continue
                    key = name.lower()
                    if key in seen:
                        continue
                    seen.add(key)
                    names.append(name)
        except Exception as exc:
            print(f"Catalog: Library-Appearances konnten nicht gelesen werden: {exc}")

    return sorted(names, key=lambda x: x.lower())


def _refresh_appearance_preview(inputs):
    browser_input = adsk.core.BrowserCommandInput.cast(inputs.itemById(_INPUT_APPEARANCE_PREVIEW))
    if not browser_input:
        return

    try:
        appearance_name = _read_dropdown(inputs, _INPUT_APPEARANCE)
        if not appearance_name or appearance_name == _APPEARANCE_NONE_LABEL:
            _set_preview_hint(inputs, "")
            _set_preview_debug(inputs, "No appearance selected.")
            browser_input.htmlFileURL = _build_preview_html_url(
                _ensure_preview_png("none", (160, 160, 160)),
                "Keine Auswahl",
            )
            return

        appearance = _find_appearance_by_name(appearance_name)
        texture_file = _find_texture_file_for_appearance(appearance) if appearance else None
        tint = _extract_tint_color_from_appearance(appearance)
        tint_alpha = _estimate_tint_alpha(appearance, tint)
        _set_preview_debug(inputs, _build_preview_debug_text(appearance_name, appearance, texture_file, tint, tint_alpha))

        if texture_file and os.path.exists(texture_file):
            _set_preview_hint(inputs, "Vorschau: Texture-Bild")
            browser_input.htmlFileURL = _build_preview_html_url(
                texture_file,
                appearance_name,
                tint_rgb=tint,
                tint_alpha=tint_alpha,
            )
            return

        color = _extract_color_from_appearance(appearance) if appearance else None
        if color is None:
            color = (110, 130, 170)
        if appearance and _appearance_has_texture(appearance):
            hint = "Hinweis: Texture nicht als PNG verfuegbar (Farb-Fallback)."
        else:
            hint = "Vorschau: Farb-Fallback"
        _set_preview_hint(inputs, hint)
        browser_input.htmlFileURL = _build_preview_html_url(
            _ensure_preview_png(_slugify(appearance_name), color),
            appearance_name,
        )
    except Exception as exc:
        fallback = _ensure_preview_png("preview_error", (160, 160, 160))
        _set_preview_hint(inputs, f"Hinweis: Vorschaufehler ({exc})")
        _set_preview_debug(inputs, f"Preview exception: {exc}")
        try:
            browser_input.htmlFileURL = _build_preview_html_url(fallback, "Preview-Fehler")
        except Exception:
            pass


def _appearance_has_texture(appearance):
    try:
        return bool(getattr(appearance, "hasTexture", False))
    except Exception:
        return False


def _find_appearance_by_name(appearance_name):
    wanted = (appearance_name or "").strip().lower()
    if not wanted:
        return None

    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct) if app else None

    def _scan_appearances(appearances):
        if not appearances:
            return None
        try:
            for i in range(appearances.count):
                entry = appearances.item(i)
                if not entry:
                    continue
                name = (entry.name or "").strip().lower()
                if name != wanted:
                    continue
                return entry
        except Exception:
            return None
        return None

    appearance = _scan_appearances(getattr(design, "appearances", None) if design else None)
    if appearance is not None:
        return appearance

    if app:
        try:
            libs = getattr(app, "materialLibraries", None)
            lib_count = libs.count if libs else 0
            for li in range(lib_count):
                library = libs.item(li)
                if not library:
                    continue
                appearance = _scan_appearances(getattr(library, "appearances", None))
                if appearance is not None:
                    return appearance
        except Exception:
            return None
    return None


def _find_texture_file_for_appearance(appearance):
    if not appearance:
        return None

    maps = _collect_texture_maps_for_appearance(appearance)
    return maps.get("preview")


def _collect_texture_maps_for_appearance(appearance):
    maps = {}
    if not appearance:
        return maps

    seen = set()
    for entry in _iter_appearance_textures(appearance):
        texture = entry.get("texture")
        prop_name = entry.get("prop_name")
        role = _guess_texture_role(prop_name)
        if not texture:
            continue
        marker = id(texture)
        if marker in seen:
            continue
        seen.add(marker)
        path = _extract_texture_file_path(texture)
        if path:
            maps.setdefault(role, path)
            maps.setdefault("preview", path)
    return maps


def _iter_appearance_textures(appearance):
    textures = []
    try:
        properties = getattr(appearance, "appearanceProperties", None)
        count = properties.count if properties else 0
        for i in range(count):
            prop = properties.item(i)
            if not prop:
                continue

            connected_texture = getattr(prop, "connectedTexture", None)
            if connected_texture:
                textures.append(
                    {
                        "texture": connected_texture,
                        "prop_name": (getattr(prop, "name", "") or ""),
                    }
                )

            obj_type = getattr(prop, "objectType", "") or ""
            if "AppearanceTextureProperty" in obj_type:
                value = getattr(prop, "value", None)
                if value:
                    textures.append(
                        {
                            "texture": value,
                            "prop_name": (getattr(prop, "name", "") or ""),
                        }
                    )
    except Exception:
        return []
    return textures


def _guess_texture_role(prop_name):
    name = (prop_name or "").strip().lower()
    if any(token in name for token in ("rough", "gloss")):
        return "roughness"
    if any(token in name for token in ("bump", "normal", "relief", "height")):
        return "bump"
    if any(token in name for token in ("base", "color", "diffuse", "albedo", "bild")):
        return "color"
    return "other"


def _extract_texture_file_path(texture):
    if not texture:
        return None

    try:
        props = getattr(texture, "properties", None)
        if props:
            by_id = props.itemById("unifiedbitmap_Bitmap")
            if by_id:
                path = _resolve_image_path_candidate(getattr(by_id, "value", None))
                if path:
                    return path

            for i in range(props.count):
                prop = props.item(i)
                if not prop:
                    continue
                path = _resolve_image_path_candidate(getattr(prop, "value", None))
                if path:
                    return path
    except Exception:
        pass

    for attr_name in ("imageFile", "fileName", "filename", "path", "texturePath"):
        try:
            path = _resolve_image_path_candidate(getattr(texture, attr_name, None))
            if path:
                return path
        except Exception:
            continue
    return None


def _resolve_image_path_candidate(value):
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None

    raw_lower = raw.lower()
    if raw_lower.startswith("file://"):
        parsed = urllib.parse.urlparse(raw)
        candidate = urllib.parse.unquote(parsed.path or "")
        if candidate.startswith("/") and len(candidate) > 2 and candidate[2] == ":":
            candidate = candidate[1:]
        candidate = candidate.replace("/", "\\")
        if os.path.exists(candidate):
            return candidate

    direct = raw.replace("/", "\\")
    if os.path.exists(direct):
        return direct

    basename_candidate = os.path.basename(direct)
    if basename_candidate:
        from_index = _lookup_texture_basename(basename_candidate)
        if from_index:
            return from_index

    match = re.search(r"([A-Za-z]:[\\/][^|;]+?\.(?:png|jpg|jpeg|bmp|tif|tiff))", raw, re.IGNORECASE)
    if match:
        candidate = match.group(1).replace("/", "\\")
        if os.path.exists(candidate):
            return candidate
    return None


def _extract_color_from_appearance(appearance):
    try:
        properties = getattr(appearance, "appearanceProperties", None)
        count = properties.count if properties else 0
        for i in range(count):
            prop = properties.item(i)
            if not prop:
                continue
            obj_type = getattr(prop, "objectType", "") or ""
            if "ColorProperty" not in obj_type:
                continue
            color = getattr(prop, "value", None)
            if not color:
                continue
            return (
                max(0, min(255, int(getattr(color, "red", 0)))),
                max(0, min(255, int(getattr(color, "green", 0)))),
                max(0, min(255, int(getattr(color, "blue", 0)))),
            )
    except Exception:
        return None
    return None


def _extract_tint_color_from_appearance(appearance):
    if not appearance:
        return None
    wanted_tokens = ("tint", "beiz", "abtoen", "abtön", "stain", "dye")
    fallback = None
    try:
        properties = getattr(appearance, "appearanceProperties", None)
        count = properties.count if properties else 0
        for i in range(count):
            prop = properties.item(i)
            if not prop:
                continue
            obj_type = getattr(prop, "objectType", "") or ""
            if "ColorProperty" not in obj_type:
                continue
            color = getattr(prop, "value", None)
            if not color:
                continue
            rgb = (
                max(0, min(255, int(getattr(color, "red", 0)))),
                max(0, min(255, int(getattr(color, "green", 0)))),
                max(0, min(255, int(getattr(color, "blue", 0)))),
            )
            prop_name = (getattr(prop, "name", "") or "").strip().lower()
            if any(token in prop_name for token in wanted_tokens):
                return rgb
            if fallback is None:
                fallback = rgb
    except Exception:
        return None
    return fallback


def _estimate_tint_alpha(appearance, tint_rgb):
    if not appearance or not tint_rgb:
        return None

    if not _is_tint_enabled(appearance):
        return 0.0

    explicit = _extract_tint_amount(appearance)
    if explicit is not None:
        # Fusion wirkt bei Holztoenung deutlich staerker als ein linearer Alpha-Wert.
        # Nichtlineare Abbildung: 0.30 -> ~0.85
        mapped = 1.0 - ((1.0 - _clamp(0.0, 1.0, explicit)) ** 5)
        return _clamp(0.25, 0.95, mapped)

    r, g, b = [channel / 255.0 for channel in tint_rgb]
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    alpha = 0.50 + (0.40 * s) + (0.20 * (1.0 - v))
    return _clamp(0.35, 0.95, alpha)


def _is_tint_enabled(appearance):
    try:
        properties = getattr(appearance, "appearanceProperties", None)
        count = properties.count if properties else 0
        for i in range(count):
            prop = properties.item(i)
            if not prop:
                continue
            obj_type = getattr(prop, "objectType", "") or ""
            if "BoolProperty" not in obj_type and "BooleanProperty" not in obj_type:
                continue
            name = (getattr(prop, "name", "") or "").strip().lower()
            if not any(token in name for token in ("tint", "ton", "beiz", "stain", "dye")):
                continue
            return bool(getattr(prop, "value", False))
    except Exception:
        return True
    return True


def _extract_tint_amount(appearance):
    try:
        properties = getattr(appearance, "appearanceProperties", None)
        count = properties.count if properties else 0
        for i in range(count):
            prop = properties.item(i)
            if not prop:
                continue
            obj_type = getattr(prop, "objectType", "") or ""
            if "FloatProperty" not in obj_type:
                continue
            name = (getattr(prop, "name", "") or "").strip().lower()
            if not any(token in name for token in ("tint", "ton", "beiz", "stain", "dye", "amount", "strength", "intensity", "menge")):
                continue
            try:
                value = float(getattr(prop, "value", 0.0))
            except Exception:
                continue
            if value > 1.0:
                value = value / 100.0
            return _clamp(0.0, 1.0, value)
    except Exception:
        return None
    return None


def _clamp(min_value, max_value, value):
    return max(min_value, min(max_value, value))


def _set_preview_hint(inputs, message):
    hint = adsk.core.TextBoxCommandInput.cast(inputs.itemById(_INPUT_PREVIEW_HINT))
    if hint:
        hint.text = message or ""


def _set_preview_debug(inputs, message):
    box = adsk.core.TextBoxCommandInput.cast(inputs.itemById(_INPUT_PREVIEW_DEBUG))
    if box:
        box.text = message or ""


def _build_preview_debug_text(appearance_name, appearance, texture_file, tint_rgb, tint_alpha):
    lines = []
    lines.append(f"appearance={appearance_name}")
    lines.append(f"found={bool(appearance)}")
    lines.append(f"texture_file={texture_file or '-'}")
    lines.append(f"texture_exists={bool(texture_file and os.path.exists(texture_file))}")
    lines.append(f"hasTexture={_appearance_has_texture(appearance) if appearance else False}")
    lines.append(f"tint_rgb={tint_rgb or '-'}")
    lines.append(f"tint_alpha={f'{tint_alpha:.4f}' if isinstance(tint_alpha, float) else '-'}")
    lines.append(f"tint_enabled={_is_tint_enabled(appearance) if appearance else False}")
    explicit = _extract_tint_amount(appearance) if appearance else None
    lines.append(f"tint_amount_explicit={f'{explicit:.4f}' if isinstance(explicit, float) else '-'}")
    color = _extract_color_from_appearance(appearance) if appearance else None
    lines.append(f"base_color={color or '-'}")
    for prop_line in _collect_appearance_property_debug_lines(appearance):
        lines.append(prop_line)
    return "\n".join(lines)


def _collect_appearance_property_debug_lines(appearance, max_lines=18):
    if not appearance:
        return []
    out = ["-- matched properties --"]
    tokens = ("tint", "ton", "beiz", "stain", "dye", "color", "rough", "texture", "bild", "bitmap", "base")
    try:
        properties = getattr(appearance, "appearanceProperties", None)
        count = properties.count if properties else 0
        taken = 0
        for i in range(count):
            prop = properties.item(i)
            if not prop:
                continue
            name = (getattr(prop, "name", "") or "").strip()
            lname = name.lower()
            if not any(t in lname for t in tokens):
                continue
            obj_type = getattr(prop, "objectType", "") or ""
            val = _property_debug_value(prop)
            out.append(f"{name} [{obj_type.split('::')[-1]}] = {val}")
            taken += 1
            if taken >= max_lines:
                break
    except Exception as exc:
        out.append(f"debug-prop-read-error: {exc}")
    return out


def _property_debug_value(prop):
    try:
        obj_type = getattr(prop, "objectType", "") or ""
        value = getattr(prop, "value", None)
        if "ColorProperty" in obj_type and value:
            return f"RGB({getattr(value, 'red', 0)},{getattr(value, 'green', 0)},{getattr(value, 'blue', 0)})"
        if "FloatProperty" in obj_type and value is not None:
            return f"{float(value):.6f}"
        if "BoolProperty" in obj_type or "BooleanProperty" in obj_type:
            return str(bool(value))
        text = str(value)
        if len(text) > 120:
            text = text[:117] + "..."
        return text
    except Exception as exc:
        return f"<err:{exc}>"


def _build_preview_html_url(image_path, title, tint_rgb=None, tint_alpha=None):
    os.makedirs(_preview_html_dir, exist_ok=True)
    img_uri = pathlib.Path(image_path).as_uri() if image_path and os.path.exists(image_path) else ""
    safe_title = _escape_html(title or "")
    tint_style = ""
    if tint_rgb is not None and (tint_alpha is None or tint_alpha > 0.0):
        r, g, b = tint_rgb
        alpha = _clamp(0.0, 1.0, 0.35 if tint_alpha is None else tint_alpha)
        tint_style = f"<div class='tint' style='background: rgba({r},{g},{b},{alpha:.4f});'></div>"
    html = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <style>
    body {{ margin: 0; padding: 8px; background: #f3f3f3; font-family: Arial, sans-serif; }}
    .box {{
      width: 120px; height: 120px; border: 1px solid #bbb; background: #ddd;
      display: flex; align-items: center; justify-content: center; overflow: hidden; position: relative;
    }}
    img {{ width: 100%; height: 100%; object-fit: cover; }}
    .tint {{ position: absolute; inset: 0; mix-blend-mode: normal; pointer-events: none; }}
    .cap {{ margin-top: 6px; color: #444; font-size: 11px; }}
  </style>
</head>
<body>
  <div class="box">{"<img src='" + img_uri + "' alt='preview' />" if img_uri else ""}{tint_style}</div>
  <div class="cap">{safe_title}</div>
</body>
</html>
"""
    token = _slugify(title or "preview")
    html_path = os.path.join(_preview_html_dir, f"preview_{token}.html")
    with open(html_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(html)
    return pathlib.Path(html_path).as_uri()


def _escape_html(text):
    text = str(text or "")
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def _build_appearance_metadata(appearance_name, appearance_obj):
    data = {
        "appearance_resolved_name": appearance_name,
    }
    if appearance_obj:
        try:
            data["appearance_id"] = str(getattr(appearance_obj, "id", "") or "")
        except Exception:
            pass
        try:
            data["appearance_has_texture"] = bool(getattr(appearance_obj, "hasTexture", False))
        except Exception:
            data["appearance_has_texture"] = False
    else:
        data["appearance_has_texture"] = False

    texture_maps = _collect_texture_maps_for_appearance(appearance_obj) if appearance_obj else {}
    for key, value in texture_maps.items():
        if value:
            data[f"appearance_texture_{key}"] = value
    if texture_maps.get("preview"):
        data["preview_texture"] = texture_maps["preview"]
    return data


def _load_preview_config():
    global _preview_config_cache
    if _preview_config_cache is not None:
        return _preview_config_cache

    default_roots = [
        r"%LOCALAPPDATA%\Autodesk\Common\Material Library\5.0.0\slib\resource\1\Mats",
    ]
    config = {
        "material_texture_roots": default_roots,
    }
    try:
        if os.path.exists(_preview_config_path):
            with open(_preview_config_path, "r", encoding="utf-8") as handle:
                loaded = json.load(handle)
            if isinstance(loaded, dict):
                roots = loaded.get("material_texture_roots")
                if isinstance(roots, list) and roots:
                    config["material_texture_roots"] = [str(item) for item in roots if str(item).strip()]
    except Exception as exc:
        print(f"Catalog: Preview-Konfiguration konnte nicht geladen werden: {exc}")

    _preview_config_cache = config
    return config


def _resolve_texture_roots():
    config = _load_preview_config()
    roots = []
    for raw in config.get("material_texture_roots", []):
        expanded = os.path.expandvars(str(raw)).strip()
        if not expanded:
            continue
        normalized = os.path.abspath(expanded)
        if os.path.isdir(normalized):
            roots.append(normalized)
    return roots


def _build_texture_index(root):
    index = {}
    try:
        for dirpath, _, filenames in os.walk(root):
            for name in filenames:
                lower = name.lower()
                if not lower.endswith((".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff")):
                    continue
                index.setdefault(lower, os.path.join(dirpath, name))
    except Exception as exc:
        print(f"Catalog: Texture-Index fehlgeschlagen ({root}): {exc}")
    return index


def _lookup_texture_basename(filename):
    lower = (filename or "").strip().lower()
    if not lower:
        return None

    for root in _resolve_texture_roots():
        if root not in _texture_file_index_cache:
            _texture_file_index_cache[root] = _build_texture_index(root)
        path = _texture_file_index_cache[root].get(lower)
        if path and os.path.exists(path):
            return path
    return None


def _ensure_preview_png(token, rgb):
    try:
        os.makedirs(_preview_cache_dir, exist_ok=True)
    except Exception:
        return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "Resources", "64x64.png"))

    safe = re.sub(r"[^a-z0-9_]+", "_", (token or "none").lower()).strip("_") or "none"
    path = os.path.join(_preview_cache_dir, f"appearance_{safe}_{rgb[0]}_{rgb[1]}_{rgb[2]}.png")
    if os.path.exists(path):
        return path

    png_bytes = _build_solid_png(_PREVIEW_SIZE, _PREVIEW_SIZE, rgb)
    with open(path, "wb") as handle:
        handle.write(png_bytes)
    return path


def _build_solid_png(width, height, rgb):
    def _chunk(name, data):
        return (
            struct.pack("!I", len(data))
            + name
            + data
            + struct.pack("!I", zlib.crc32(name + data) & 0xFFFFFFFF)
        )

    row = bytes([rgb[0], rgb[1], rgb[2], 255]) * width
    raw = b"".join(b"\x00" + row for _ in range(height))
    ihdr = struct.pack("!IIBBBBB", width, height, 8, 6, 0, 0, 0)
    idat = zlib.compress(raw, 9)
    return b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", idat) + _chunk(b"IEND", b"")


def _generate_internal_id(catalog, item_type, item_name):
    item_type_norm = (item_type or "item").strip().lower()
    slug = _slugify(item_name)
    base = f"{item_type_norm}.{slug or 'item'}"
    if not catalog.get(base):
        return base
    suffix = 2
    while True:
        candidate = f"{base}_{suffix}"
        if not catalog.get(candidate):
            return candidate
        suffix += 1


def _slugify(text):
    if not text:
        return "item"
    text = text.strip().lower()
    text = (
        text.replace("ä", "ae")
        .replace("ö", "oe")
        .replace("ü", "ue")
        .replace("ß", "ss")
    )
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return text or "item"


def _read_string(inputs, input_id):
    item = adsk.core.StringValueCommandInput.cast(inputs.itemById(input_id))
    if not item:
        return ""
    return (item.value or "").strip()


def _set_string(inputs, input_id, value):
    item = adsk.core.StringValueCommandInput.cast(inputs.itemById(input_id))
    if item:
        item.value = value or ""


def _read_bool(inputs, input_id, fallback):
    item = adsk.core.BoolValueCommandInput.cast(inputs.itemById(input_id))
    if not item:
        return fallback
    return bool(item.value)


def _set_bool(inputs, input_id, value):
    item = adsk.core.BoolValueCommandInput.cast(inputs.itemById(input_id))
    if item:
        item.value = bool(value)


def _read_dropdown(inputs, input_id):
    dd = adsk.core.DropDownCommandInput.cast(inputs.itemById(input_id))
    if not dd or not dd.selectedItem:
        return ""
    return (dd.selectedItem.name or "").strip()


def _set_dropdown(inputs, input_id, wanted):
    dd = adsk.core.DropDownCommandInput.cast(inputs.itemById(input_id))
    if not dd:
        return
    wanted_norm = (wanted or "").strip().lower()
    for i in range(dd.listItems.count):
        item = dd.listItems.item(i)
        if (item.name or "").strip().lower() == wanted_norm:
            item.isSelected = True
            return

    if wanted and wanted_norm != _APPEARANCE_NONE_LABEL.lower():
        dd.listItems.add(wanted, True)
        return

    if dd.listItems.count > 0:
        dd.listItems.item(0).isSelected = True


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

    cmd_def = ui.commandDefinitions.itemById(config.CATALOG_COMMAND_ID)
    if not cmd_def:
        cmd_def = ui.commandDefinitions.addButtonDefinition(
            config.CATALOG_COMMAND_ID,
            config.CATALOG_COMMAND_NAME,
            config.CATALOG_COMMAND_TOOLTIP,
            config.CATALOG_COMMAND_RESOURCES,
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

    control = panel.controls.itemById(config.CATALOG_COMMAND_ID)
    if not control:
        control = panel.controls.addCommand(cmd_def)

    if control:
        try:
            control.isPromotedByDefault = True
            control.isPromoted = False
        except Exception:
            pass


def stop():
    global _active_panel_id, _is_started, _command_created_handler
    app = adsk.core.Application.get()
    ui = app.userInterface
    cmd_def = ui.commandDefinitions.itemById(config.CATALOG_COMMAND_ID)

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
            control = panel.controls.itemById(config.CATALOG_COMMAND_ID)
            if control:
                control.deleteMe()

    if cmd_def:
        cmd_def.deleteMe()

    _handlers.clear()
    _active_panel_id = None
    _is_started = False
