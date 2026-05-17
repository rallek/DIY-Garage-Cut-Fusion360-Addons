import colorsys
import json
import locale
import os
import pathlib
import re
import struct
import tempfile
import urllib.parse
import zlib

import adsk.core
import adsk.fusion

import export_config as config
from shared.catalog import (
    Catalog,
    CatalogItem,
    get_all_type_field_alias_keys,
    get_all_type_field_keys,
    get_catalog_types,
    get_type_default_properties,
    get_type_fields,
    get_type_label,
    load_catalog,
    normalize_type_properties,
    save_catalog,
    upsert_catalog_item,
)

_handlers = []
_active_panel_id = None
_is_started = False
_command_created_handler = None
_is_syncing = False
_reopen_after_save = False

_INPUT_SELECTION = "diygc_catalog_selection"
_INPUT_FILTER_TYPE = "diygc_catalog_filter_type"
_INPUT_COPY = "diygc_catalog_copy"
_INPUT_DELETE = "diygc_catalog_delete"
_INPUT_TYPE = "diygc_catalog_type"
_INPUT_NAME = "diygc_catalog_name"
_INPUT_APPEARANCE = "diygc_catalog_appearance"
_INPUT_TYPE_FIELD_PREFIX = "diygc_catalog_type_field_"
_INPUT_APPEARANCE_PREVIEW = "diygc_catalog_appearance_preview"
_INPUT_PREVIEW_HINT = "diygc_catalog_preview_hint"
_INPUT_STATUS = "diygc_catalog_status"

_PREVIEW_SIZE = 84
_preview_cache_dir = os.path.abspath(os.path.join(tempfile.gettempdir(), "diygc_catalog_preview_cache"))
_preview_html_dir = os.path.abspath(os.path.join(tempfile.gettempdir(), "diygc_catalog_preview_html"))
_preview_config_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "catalog_preview_config.json")
)
_preview_config_cache = None
_texture_file_index_cache = {}

_ui_lang = "de"
_selection_id_by_label = {}
_selected_item_id = None
_copy_mode = False
_baseline_snapshot = None
_last_selection_label = None
_type_field_ids = {}
_type_field_label_ids = {}
_type_field_meta_by_key = {}
_label_counter = 0

_STRINGS = {
    "de": {
        "filter_type": "Filter",
        "filter_all_types": "Alle Typen",
        "existing_entries": "Material",
        "create_new": "(Neu anlegen)",
        "copy_entry": "Als neuen Eintrag speichern",
        "delete_entry": "Eintrag löschen",
        "type": "Typ",
        "name": "Name",
        "appearance": "Darstellung",
        "appearance_from_fusion": "Darstellung",
        "preview": "Vorschau",
        "save": "Speichern",
        "status_saved": "Änderungen gespeichert.",
        "status_deleted": "Eintrag gelöscht.",
        "status_delete_requires_existing": "Fehler: Löschen nur bei bestehendem Eintrag möglich.",
        "confirm_delete_title": "Eintrag löschen",
        "confirm_delete_body": "Diesen Eintrag wirklich löschen?",
        "status_invalid_type": "Fehler: Bitte gültigen Typ wählen.",
        "status_invalid_name": "Fehler: Name darf nicht leer sein.",
        "status_invalid_appearance": "Fehler: Bitte Darstellung auswählen.",
        "preview_none": "Keine Auswahl",
        "preview_texture": "Vorschau: Texture-Bild",
        "preview_fallback_texture": "Hinweis: Texture nicht direkt verfügbar (Farb-Fallback).",
        "preview_fallback_color": "Vorschau: Farb-Fallback",
        "preview_error": "Hinweis: Vorschaufehler ({err})",
        "appearance_none": "(Bitte wählen)",
    },
    "en": {
        "filter_type": "Filter",
        "filter_all_types": "All types",
        "existing_entries": "Material",
        "create_new": "(Create new)",
        "copy_entry": "Save as new entry",
        "delete_entry": "Delete entry",
        "type": "Type",
        "name": "Name",
        "appearance": "Appearance",
        "appearance_from_fusion": "Appearance",
        "preview": "Preview",
        "save": "Save",
        "status_saved": "Changes saved.",
        "status_deleted": "Entry deleted.",
        "status_delete_requires_existing": "Error: Delete is only possible for existing entries.",
        "confirm_delete_title": "Delete entry",
        "confirm_delete_body": "Delete this entry?",
        "status_invalid_type": "Error: Please select a valid type.",
        "status_invalid_name": "Error: Name cannot be empty.",
        "status_invalid_appearance": "Error: Please select an appearance.",
        "preview_none": "No selection",
        "preview_texture": "Preview: texture image",
        "preview_fallback_texture": "Hint: texture not directly available (color fallback).",
        "preview_fallback_color": "Preview: color fallback",
        "preview_error": "Hint: preview error ({err})",
        "appearance_none": "(Please select)",
    },
}


class _CommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def notify(self, args):
        global _ui_lang, _copy_mode, _baseline_snapshot, _selected_item_id, _last_selection_label, _type_field_ids, _type_field_label_ids, _type_field_meta_by_key, _label_counter
        _ui_lang = _detect_ui_lang()
        _copy_mode = False
        _baseline_snapshot = None
        _selected_item_id = None
        _last_selection_label = None
        _type_field_ids = {}
        _type_field_label_ids = {}
        _type_field_meta_by_key = {}
        _label_counter = 0

        event_args = adsk.core.CommandCreatedEventArgs.cast(args)
        cmd = event_args.command
        inputs = cmd.commandInputs

        try:
            cmd.okButtonText = _t("save")
        except Exception:
            pass
        try:
            cmd.setDialogInitialSize(560, 520)
        except Exception:
            pass
        try:
            cmd.setDialogMinimumSize(500, 420)
        except Exception:
            pass

        _add_field_label(inputs, _t("filter_type"))
        filter_type = inputs.addDropDownCommandInput(
            _INPUT_FILTER_TYPE,
            "",
            adsk.core.DropDownStyles.TextListDropDownStyle,
        )
        _try_set_full_width(filter_type)
        filter_type.listItems.add(_t("filter_all_types"), True)
        for type_id in _sorted_types():
            filter_type.listItems.add(_type_label(type_id), False)

        _add_field_label(inputs, _t("existing_entries"))
        selection = inputs.addDropDownCommandInput(
            _INPUT_SELECTION,
            "",
            adsk.core.DropDownStyles.TextListDropDownStyle,
        )
        _try_set_full_width(selection)
        selection.listItems.add(_t("create_new"), True)

        _add_section_divider(inputs)

        _add_field_label(inputs, _t("type"))
        type_input = inputs.addDropDownCommandInput(
            _INPUT_TYPE,
            "",
            adsk.core.DropDownStyles.TextListDropDownStyle,
        )
        _try_set_full_width(type_input)
        for idx, type_id in enumerate(_sorted_types()):
            type_input.listItems.add(_type_label(type_id), idx == 0)

        _add_field_label(inputs, _t("name"))
        name_input = inputs.addStringValueInput(_INPUT_NAME, "", "")
        _try_set_full_width(name_input)

        _add_field_label(inputs, _t("appearance"))
        appearance_pick = inputs.addDropDownCommandInput(
            _INPUT_APPEARANCE,
            "",
            adsk.core.DropDownStyles.TextListDropDownStyle,
        )
        _try_set_full_width(appearance_pick)
        appearance_pick.listItems.add(_t("appearance_none"), True)

        _add_type_specific_field_inputs(inputs)

        preview = inputs.addBrowserCommandInput(
            _INPUT_APPEARANCE_PREVIEW,
            _t("preview"),
            _build_preview_html_url(_ensure_preview_png("none", (160, 160, 160)), _t("preview_none")),
            98,
            126,
        )
        preview.isFullWidth = True

        preview_hint = inputs.addTextBoxCommandInput(_INPUT_PREVIEW_HINT, "", "", 1, True)
        preview_hint.isFullWidth = True

        copy_btn = inputs.addBoolValueInput(_INPUT_COPY, _t("copy_entry"), True, "", False)
        copy_btn.isFullWidth = False

        delete_btn = inputs.addBoolValueInput(_INPUT_DELETE, _t("delete_entry"), True, "", False)
        delete_btn.isFullWidth = False
        delete_btn.isEnabled = False

        status = inputs.addTextBoxCommandInput(_INPUT_STATUS, "", "", 2, True)
        status.isFullWidth = True

        _populate_appearance_items(appearance_pick)
        _populate_existing_items(selection, filter_type=_read_filter_type(inputs))
        _sync_inputs(inputs, changed_id=None)

        on_input_changed = _InputChangedHandler()
        cmd.inputChanged.add(on_input_changed)
        _handlers.append(on_input_changed)

        on_validate = _ValidateInputsHandler()
        cmd.validateInputs.add(on_validate)
        _handlers.append(on_validate)

        on_execute = _CommandExecuteHandler()
        cmd.execute.add(on_execute)
        _handlers.append(on_execute)

        on_destroy = _CommandDestroyHandler()
        cmd.destroy.add(on_destroy)
        _handlers.append(on_destroy)


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
            if changed_id == _INPUT_DELETE:
                if _read_bool(inputs, _INPUT_DELETE, False):
                    _set_bool(inputs, _INPUT_DELETE, False)
                    _delete_selected_entry(inputs)
                return

            _sync_inputs(inputs, changed_id=changed_id)
        except Exception as exc:
            _set_status(inputs, f"Input-Fehler: {exc}")


class _ValidateInputsHandler(adsk.core.ValidateInputsEventHandler):
    def notify(self, args):
        try:
            event_args = adsk.core.ValidateInputsEventArgs.cast(args)
            inputs = event_args.inputs if event_args else None
            if not inputs:
                return
            event_args.areInputsValid = _can_save(inputs)
        except Exception:
            pass


class _CommandExecuteHandler(adsk.core.CommandEventHandler):
    def notify(self, args):
        global _reopen_after_save
        try:
            event_args = adsk.core.CommandEventArgs.cast(args)
            command = event_args.command if event_args else None
            inputs = command.commandInputs if command else None
            if not inputs:
                return
            _save_from_inputs(inputs)
            _reopen_after_save = True
        except Exception as exc:
            app = adsk.core.Application.get()
            ui = app.userInterface if app else None
            if ui:
                ui.messageBox(f"Speichern fehlgeschlagen:\n{exc}")


class _CommandDestroyHandler(adsk.core.CommandEventHandler):
    def notify(self, args):
        global _reopen_after_save
        if not _reopen_after_save:
            return
        _reopen_after_save = False
        try:
            app = adsk.core.Application.get()
            ui = app.userInterface if app else None
            if not ui:
                return
            cmd_def = ui.commandDefinitions.itemById(config.CATALOG_COMMAND_ID)
            if cmd_def:
                cmd_def.execute()
        except Exception as exc:
            print(f"Catalog: Reopen nach Speichern fehlgeschlagen: {exc}")


def _save_from_inputs(inputs):
    global _selected_item_id, _copy_mode, _baseline_snapshot
    if not _is_candidate_valid(inputs, emit_status=True):
        return

    catalog = _load_catalog_data()
    form = _form_snapshot(inputs)
    appearance_obj = _find_appearance_by_name(form["appearance"])

    is_new = _read_bool(inputs, _INPUT_COPY, False) or _selected_item_id is None
    if is_new:
        item_id = _generate_internal_id(catalog, form["type"], form["name"])
        base_properties = {}
    else:
        existing_item = catalog.get(_selected_item_id)
        if not existing_item:
            _set_status(inputs, f"Fehler: Eintrag nicht gefunden: {_selected_item_id}")
            return
        item_id = existing_item.id
        base_properties = dict(existing_item.properties or {})

    for known_key in get_all_type_field_keys():
        base_properties.pop(known_key, None)
    for legacy_key in get_all_type_field_alias_keys():
        base_properties.pop(legacy_key, None)
    base_properties.update(form.get("type_properties", {}))
    base_properties = normalize_type_properties(form["type"], base_properties)
    base_properties.update(_build_appearance_metadata(form["appearance"], appearance_obj))
    item = CatalogItem.from_dict(
        {
            "id": item_id,
            "type": form["type"],
            "name": form["name"],
            "appearance": form["appearance"],
            **base_properties,
        }
    )
    next_catalog = upsert_catalog_item(catalog, item)
    save_catalog(next_catalog)

    _set_status(inputs, _t("status_saved"))
    _selected_item_id = item.id
    _copy_mode = False
    _baseline_snapshot = _item_snapshot(item)
    _set_bool(inputs, _INPUT_COPY, False)
    _refresh_selection_after_save(inputs, item.id)
    _sync_inputs(inputs, changed_id=_INPUT_SELECTION)


def _delete_selected_entry(inputs):
    global _selected_item_id, _copy_mode, _baseline_snapshot
    if _selected_item_id is None:
        _set_status(inputs, _t("status_delete_requires_existing"))
        return

    app = adsk.core.Application.get()
    ui = app.userInterface if app else None
    if not ui:
        return
    result = ui.messageBox(
        _t("confirm_delete_body"),
        _t("confirm_delete_title"),
        adsk.core.MessageBoxButtonTypes.YesNoButtonType,
        adsk.core.MessageBoxIconTypes.WarningIconType,
    )
    if result != adsk.core.DialogResults.DialogYes:
        return

    catalog = _load_catalog_data()
    remaining = [item for item in catalog.items if item.id != _selected_item_id]
    next_catalog = Catalog.build(version=catalog.version, items=remaining)
    save_catalog(next_catalog)

    _selected_item_id = None
    _copy_mode = True
    _baseline_snapshot = None
    _set_status(inputs, _t("status_deleted"))
    selection = adsk.core.DropDownCommandInput.cast(inputs.itemById(_INPUT_SELECTION))
    if selection:
        _populate_existing_items(selection, filter_type=_read_filter_type(inputs))
    _sync_inputs(inputs, changed_id=_INPUT_SELECTION)


def _sync_inputs(inputs, changed_id=None):
    global _is_syncing, _selected_item_id, _copy_mode, _baseline_snapshot, _last_selection_label
    _is_syncing = True
    try:
        selection = adsk.core.DropDownCommandInput.cast(inputs.itemById(_INPUT_SELECTION))
        if not selection or not selection.selectedItem:
            return

        if changed_id == _INPUT_FILTER_TYPE:
            _populate_existing_items(
                selection,
                selected_id=_selected_item_id,
                filter_type=_read_filter_type(inputs),
            )
            changed_id = _INPUT_SELECTION
            _last_selection_label = None

        selected_label = selection.selectedItem.name or ""
        selected_item = _get_item_by_selection_label(selected_label)

        if changed_id == _INPUT_SELECTION and selected_label != _last_selection_label:
            if selected_item:
                _selected_item_id = selected_item.id
                _copy_mode = False
                _baseline_snapshot = _item_snapshot(selected_item)
                _set_type_dropdown(inputs, selected_item.type)
                _set_string(inputs, _INPUT_NAME, selected_item.name)
                _set_dropdown(inputs, _INPUT_APPEARANCE, selected_item.appearance)
                _set_bool(inputs, _INPUT_COPY, False)
                _set_type_specific_form_values(inputs, selected_item.type, selected_item.properties or {})
            else:
                _selected_item_id = None
                _copy_mode = True
                _baseline_snapshot = None
                _set_string(inputs, _INPUT_NAME, "")
                _set_bool(inputs, _INPUT_COPY, False)
                _set_status(inputs, "")
                filter_type = _read_filter_type(inputs)
                if filter_type:
                    _set_type_dropdown(inputs, filter_type)
                _apply_type_defaults_to_inputs(inputs, _read_type_from_dropdown(inputs))

        if changed_id == _INPUT_TYPE:
            _apply_type_defaults_to_inputs(inputs, _read_type_from_dropdown(inputs))

        _update_type_specific_field_visibility(inputs, _read_type_from_dropdown(inputs))
        _refresh_appearance_preview(inputs)
        _update_delete_state(inputs)
        _last_selection_label = selected_label
    finally:
        _is_syncing = False


def _update_delete_state(inputs):
    delete_btn = adsk.core.BoolValueCommandInput.cast(inputs.itemById(_INPUT_DELETE))
    if not delete_btn:
        return
    delete_btn.isEnabled = _selected_item_id is not None and not _read_bool(inputs, _INPUT_COPY, False)


def _can_save(inputs):
    if not _is_candidate_valid(inputs, emit_status=False):
        return False
    if _read_bool(inputs, _INPUT_COPY, False) or _selected_item_id is None:
        return True
    if _baseline_snapshot is None:
        return True
    return _form_snapshot(inputs) != _baseline_snapshot


def _is_candidate_valid(inputs, emit_status):
    type_id = _read_type_from_dropdown(inputs)
    if not type_id:
        if emit_status:
            _set_status(inputs, _t("status_invalid_type"))
        return False
    name = _read_string(inputs, _INPUT_NAME)
    if not name:
        if emit_status:
            _set_status(inputs, _t("status_invalid_name"))
        return False
    appearance = _read_dropdown(inputs, _INPUT_APPEARANCE)
    if not appearance or appearance == _t("appearance_none"):
        if emit_status:
            _set_status(inputs, _t("status_invalid_appearance"))
        return False
    type_values = _read_type_specific_values(inputs, type_id)
    try:
        normalize_type_properties(type_id, type_values)
    except ValueError as exc:
        if emit_status:
            _set_status(inputs, f"Fehler: {exc}")
        return False
    return True


def _load_catalog_data():
    return load_catalog()


def _populate_existing_items(dropdown, selected_id=None, filter_type=None):
    global _selection_id_by_label
    _selection_id_by_label = {}
    dropdown.listItems.clear()
    create_new_label = _t("create_new")
    dropdown.listItems.add(create_new_label, selected_id is None)
    has_selected = selected_id is None

    catalog = _load_catalog_data()
    for item in sorted(catalog.items, key=lambda x: ((x.name or "").lower(), _type_label(x.type).lower(), (x.id or "").lower())):
        if filter_type and item.type != filter_type:
            continue
        label = f"{item.name} [{_type_label(item.type)}]"
        if label in _selection_id_by_label:
            label = f"{label} · {item.id}"
        _selection_id_by_label[label] = item.id
        is_selected = selected_id == item.id
        dropdown.listItems.add(label, is_selected)
        has_selected = has_selected or is_selected
    if not has_selected and dropdown.listItems.count > 0:
        dropdown.listItems.item(0).isSelected = True


def _refresh_selection_after_save(inputs, selected_id):
    selection = adsk.core.DropDownCommandInput.cast(inputs.itemById(_INPUT_SELECTION))
    if not selection:
        return
    _populate_existing_items(selection, selected_id=selected_id, filter_type=_read_filter_type(inputs))


def _get_item_by_selection_label(label):
    item_id = _selection_id_by_label.get(label)
    if not item_id:
        return None
    return _load_catalog_data().get(item_id)


def _get_selected_item(inputs):
    selection = adsk.core.DropDownCommandInput.cast(inputs.itemById(_INPUT_SELECTION))
    if not selection or not selection.selectedItem:
        return None
    return _get_item_by_selection_label(selection.selectedItem.name or "")


def _item_snapshot(item):
    type_props = get_type_default_properties(item.type)
    type_props.update(_extract_type_properties(item.type, item.properties or {}))
    return {
        "type": item.type,
        "name": item.name,
        "appearance": item.appearance,
        "type_properties": type_props,
    }


def _form_snapshot(inputs):
    type_id = _read_type_from_dropdown(inputs)
    return {
        "type": type_id,
        "name": _read_string(inputs, _INPUT_NAME),
        "appearance": _read_dropdown(inputs, _INPUT_APPEARANCE),
        "type_properties": _read_type_specific_values(inputs, type_id),
    }


def _populate_appearance_items(dropdown):
    dropdown.listItems.clear()
    dropdown.listItems.add(_t("appearance_none"), True)
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
        except Exception:
            pass

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
        except Exception:
            pass
    return sorted(names, key=lambda x: x.lower())


def _refresh_appearance_preview(inputs):
    browser_input = adsk.core.BrowserCommandInput.cast(inputs.itemById(_INPUT_APPEARANCE_PREVIEW))
    if not browser_input:
        return

    try:
        appearance_name = _read_dropdown(inputs, _INPUT_APPEARANCE)
        if not appearance_name or appearance_name == _t("appearance_none"):
            _set_preview_hint(inputs, "")
            browser_input.htmlFileURL = _build_preview_html_url(
                _ensure_preview_png("none", (160, 160, 160)),
                _t("preview_none"),
            )
            return

        appearance = _find_appearance_by_name(appearance_name)
        texture_file = _find_texture_file_for_appearance(appearance) if appearance else None
        if texture_file and os.path.exists(texture_file):
            tint = _extract_tint_color_from_appearance(appearance)
            tint_alpha = _estimate_tint_alpha(appearance, tint)
            _set_preview_hint(inputs, _t("preview_texture"))
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
        hint = _t("preview_fallback_texture") if appearance and _appearance_has_texture(appearance) else _t("preview_fallback_color")
        _set_preview_hint(inputs, hint)
        browser_input.htmlFileURL = _build_preview_html_url(
            _ensure_preview_png(_slugify(appearance_name), color),
            appearance_name,
        )
    except Exception as exc:
        fallback = _ensure_preview_png("preview_error", (160, 160, 160))
        _set_preview_hint(inputs, _t("preview_error").format(err=exc))
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

    def _scan(appearances):
        if not appearances:
            return None
        try:
            for i in range(appearances.count):
                entry = appearances.item(i)
                if not entry:
                    continue
                name = (entry.name or "").strip().lower()
                if name == wanted:
                    return entry
        except Exception:
            return None
        return None

    hit = _scan(getattr(design, "appearances", None) if design else None)
    if hit:
        return hit

    if app:
        try:
            libs = getattr(app, "materialLibraries", None)
            lib_count = libs.count if libs else 0
            for li in range(lib_count):
                library = libs.item(li)
                if not library:
                    continue
                hit = _scan(getattr(library, "appearances", None))
                if hit:
                    return hit
        except Exception:
            return None
    return None


def _find_texture_file_for_appearance(appearance):
    maps = _collect_texture_maps_for_appearance(appearance)
    return maps.get("preview")


def _collect_texture_maps_for_appearance(appearance):
    maps = {}
    if not appearance:
        return maps
    seen = set()
    for entry in _iter_appearance_textures(appearance):
        texture = entry.get("texture")
        if not texture:
            continue
        marker = id(texture)
        if marker in seen:
            continue
        seen.add(marker)
        role = _guess_texture_role(entry.get("prop_name"))
        path = _extract_texture_file_path(texture)
        if path:
            maps.setdefault(role, path)
            maps.setdefault("preview", path)
    return maps


def _iter_appearance_textures(appearance):
    out = []
    try:
        properties = getattr(appearance, "appearanceProperties", None)
        count = properties.count if properties else 0
        for i in range(count):
            prop = properties.item(i)
            if not prop:
                continue
            prop_name = (getattr(prop, "name", "") or "")
            connected = getattr(prop, "connectedTexture", None)
            if connected:
                out.append({"texture": connected, "prop_name": prop_name})
            obj_type = getattr(prop, "objectType", "") or ""
            if "AppearanceTextureProperty" in obj_type:
                value = getattr(prop, "value", None)
                if value:
                    out.append({"texture": value, "prop_name": prop_name})
    except Exception:
        return []
    return out


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

    if raw.lower().startswith("file://"):
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
    if not appearance:
        return None
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
            if color:
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
        mapped = 1.0 - ((1.0 - _clamp(0.0, 1.0, explicit)) ** 5)
        return _clamp(0.25, 0.95, mapped)

    r, g, b = [channel / 255.0 for channel in tint_rgb]
    _, s, v = colorsys.rgb_to_hsv(r, g, b)
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


def _add_type_specific_field_inputs(inputs):
    global _type_field_ids, _type_field_label_ids, _type_field_meta_by_key
    _type_field_ids = {}
    _type_field_label_ids = {}
    _type_field_meta_by_key = {}
    for type_id in _sorted_types():
        fields = get_type_fields(type_id)
        for field in fields:
            field_key = field.get("key")
            if not field_key:
                continue
            input_id = f"{_INPUT_TYPE_FIELD_PREFIX}{field_key}"
            _type_field_ids[field_key] = input_id
            _type_field_meta_by_key[field_key] = dict(field)
            label = _add_field_label(inputs, _field_label(field))
            _type_field_label_ids[field_key] = label.id if label else None

            kind = field.get("kind")
            ctrl = None
            if kind == "number":
                ctrl = inputs.addStringValueInput(
                    input_id,
                    "",
                    _format_number_for_input(field.get("default", 0.0)),
                )
            elif kind == "string":
                ctrl = inputs.addStringValueInput(input_id, "", str(field.get("default", "")))
            elif kind == "boolean":
                ctrl = inputs.addBoolValueInput(input_id, "", True, "", bool(field.get("default", False)))
            elif kind == "enum":
                dd = inputs.addDropDownCommandInput(
                    input_id,
                    "",
                    adsk.core.DropDownStyles.TextListDropDownStyle,
                )
                options = list(field.get("options", []))
                default_value = str(field.get("default", options[0] if options else ""))
                for option in options:
                    dd.listItems.add(str(option), str(option) == default_value)
                ctrl = dd
            if ctrl:
                _try_set_full_width(ctrl)
                ctrl.isVisible = False
            if label:
                label.isVisible = False


def _field_label(field):
    labels = field.get("labels", {})
    if _ui_lang == "en":
        base = str(labels.get("en", field.get("key", "")))
    else:
        base = str(labels.get("de", field.get("key", "")))
    if field.get("kind") == "number":
        unit = str(field.get("storage_unit", "") or "").strip()
        if unit:
            return f"{base} ({unit})"
    return base


def _extract_type_properties(type_id, properties):
    out = {}
    source = dict(properties or {})
    for field in get_type_fields(type_id):
        key = field.get("key")
        if not key:
            continue
        if key in source:
            out[key] = source[key]
    return out


def _read_type_specific_values(inputs, type_id):
    values = {}
    for field in get_type_fields(type_id):
        key = field.get("key")
        if not key:
            continue
        input_id = _type_field_ids.get(key)
        if not input_id:
            continue
        kind = field.get("kind")
        if kind == "number":
            item = adsk.core.StringValueCommandInput.cast(inputs.itemById(input_id))
            if not item:
                continue
            value = _parse_number_input(item.value)
            values[key] = value
            continue
        if kind == "string":
            item = adsk.core.StringValueCommandInput.cast(inputs.itemById(input_id))
            values[key] = (item.value or "") if item else ""
            continue
        if kind == "boolean":
            item = adsk.core.BoolValueCommandInput.cast(inputs.itemById(input_id))
            values[key] = bool(item.value) if item else False
            continue
        if kind == "enum":
            dd = adsk.core.DropDownCommandInput.cast(inputs.itemById(input_id))
            values[key] = (dd.selectedItem.name or "") if dd and dd.selectedItem else ""
            continue
    return values


def _set_type_specific_form_values(inputs, type_id, properties):
    defaults = get_type_default_properties(type_id)
    source = dict(defaults)
    source.update(_extract_type_properties(type_id, properties))
    for field in get_type_fields(type_id):
        key = field.get("key")
        if not key:
            continue
        input_id = _type_field_ids.get(key)
        if not input_id:
            continue
        value = source.get(key, field.get("default", 0.0))
        kind = field.get("kind")
        if kind == "number":
            item = adsk.core.StringValueCommandInput.cast(inputs.itemById(input_id))
            if not item:
                continue
            try:
                numeric = float(value)
            except Exception:
                numeric = float(field.get("default", 0.0))
            item.value = _format_number_for_input(numeric)
            continue
        if kind == "string":
            item = adsk.core.StringValueCommandInput.cast(inputs.itemById(input_id))
            if item:
                item.value = str(value or "")
            continue
        if kind == "boolean":
            item = adsk.core.BoolValueCommandInput.cast(inputs.itemById(input_id))
            if item:
                item.value = bool(value)
            continue
        if kind == "enum":
            dd = adsk.core.DropDownCommandInput.cast(inputs.itemById(input_id))
            if not dd:
                continue
            wanted = str(value or field.get("default", "")).strip().lower()
            hit = False
            for i in range(dd.listItems.count):
                option = dd.listItems.item(i)
                if (option.name or "").strip().lower() == wanted:
                    option.isSelected = True
                    hit = True
                    break
            if not hit and dd.listItems.count > 0:
                dd.listItems.item(0).isSelected = True


def _apply_type_defaults_to_inputs(inputs, type_id):
    if not type_id:
        return
    _set_type_specific_form_values(inputs, type_id, {})


def _update_type_specific_field_visibility(inputs, type_id):
    visible_keys = {field.get("key") for field in get_type_fields(type_id)}
    for field_key, input_id in _type_field_ids.items():
        ctrl = inputs.itemById(input_id)
        label_id = _type_field_label_ids.get(field_key)
        label = inputs.itemById(label_id) if label_id else None
        should_show = field_key in visible_keys
        if ctrl:
            ctrl.isVisible = should_show
        if label:
            label.isVisible = should_show


def _set_preview_hint(inputs, message):
    hint = adsk.core.TextBoxCommandInput.cast(inputs.itemById(_INPUT_PREVIEW_HINT))
    if hint:
        hint.text = message or ""


def _add_field_label(inputs, text):
    global _label_counter
    _label_counter += 1
    label_id = f"diygc_lbl_{_slugify(text)}_{_label_counter}"
    lbl = inputs.addTextBoxCommandInput(label_id, "", _escape_html(text), 1, True)
    lbl.isFullWidth = True
    return lbl


def _add_section_divider(inputs):
    divider_id = f"diygc_sep_{_label_counter}"
    try:
        sep = inputs.addSeparatorCommandInput(divider_id, "")
        sep.isFullWidth = True
        return sep
    except Exception:
        box = inputs.addTextBoxCommandInput(divider_id, "", "------------------------------", 1, True)
        box.isFullWidth = True
        return box


def _try_set_full_width(input_obj):
    try:
        input_obj.isFullWidth = True
    except Exception:
        pass


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
    body {{ margin: 0; padding: 6px; background: #f3f3f3; font-family: Arial, sans-serif; }}
    .box {{
      width: 72px; height: 72px; border: 1px solid #bbb; background: #ddd;
      display: flex; align-items: center; justify-content: center; overflow: hidden; position: relative;
    }}
    img {{ width: 100%; height: 100%; object-fit: cover; }}
    .tint {{ position: absolute; inset: 0; mix-blend-mode: normal; pointer-events: none; }}
    .cap {{ margin-top: 4px; color: #444; font-size: 11px; }}
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
    data = {"appearance_resolved_name": appearance_name}
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

    config = {
        "material_texture_roots": [
            r"%LOCALAPPDATA%\Autodesk\Common\Material Library\5.0.0\slib\resource\1\Mats",
        ]
    }
    try:
        if os.path.exists(_preview_config_path):
            with open(_preview_config_path, "r", encoding="utf-8") as handle:
                loaded = json.load(handle)
            if isinstance(loaded, dict):
                roots = loaded.get("material_texture_roots")
                if isinstance(roots, list) and roots:
                    config["material_texture_roots"] = [str(item) for item in roots if str(item).strip()]
    except Exception:
        pass

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
    except Exception:
        return index
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
    if wanted and wanted_norm != _t("appearance_none").lower():
        dd.listItems.add(wanted, True)
        return
    if dd.listItems.count > 0:
        dd.listItems.item(0).isSelected = True


def _set_type_dropdown(inputs, type_id):
    _set_dropdown(inputs, _INPUT_TYPE, _type_label(type_id))


def _read_filter_type(inputs):
    display = _read_dropdown(inputs, _INPUT_FILTER_TYPE).lower()
    if not display or display == _t("filter_all_types").lower():
        return None
    for type_id in get_catalog_types():
        if display == _type_label(type_id).lower():
            return type_id
    return None


def _read_type_from_dropdown(inputs):
    display = _read_dropdown(inputs, _INPUT_TYPE).lower()
    for type_id in get_catalog_types():
        if display == _type_label(type_id).lower():
            return type_id
    return None


def _set_status(inputs, message):
    status = adsk.core.TextBoxCommandInput.cast(inputs.itemById(_INPUT_STATUS))
    if status:
        status.text = message or ""


def _type_label(type_id):
    return get_type_label(type_id, _ui_lang)


def _sorted_types():
    return sorted(get_catalog_types())


def _clamp(min_value, max_value, value):
    return max(min_value, min(max_value, value))


def _format_number_for_input(value):
    try:
        numeric = float(value)
    except Exception:
        numeric = 0.0
    text = f"{numeric:g}"
    if _ui_lang == "de":
        return text.replace(".", ",")
    return text


def _parse_number_input(text):
    raw = str(text or "").strip()
    if not raw:
        raise ValueError("leer")
    cleaned = raw.replace(" ", "")
    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")
    match = re.search(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", cleaned)
    if not match:
        raise ValueError(f"keine Zahl: {raw}")
    return float(match.group(0))


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


def _t(key):
    return _STRINGS.get(_ui_lang, _STRINGS["de"]).get(key, key)


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
