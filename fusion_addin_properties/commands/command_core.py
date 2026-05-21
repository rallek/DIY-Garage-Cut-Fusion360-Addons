import locale
import re

import adsk.core
import adsk.fusion

from shared.catalog import get_catalog_types, get_type_capabilities, get_type_fields, get_type_label, load_catalog

WORKSPACE_ID = "FusionSolidEnvironment"
PRIMARY_PANEL_ID = "SolidModifyPanel"
PANEL_IDS = [
    "SolidModifyPanel",
    "SolidToolsPanel",
    "SolidCreatePanel",
    "SolidScriptsAddinsPanel",
]
CUSTOM_TAB_ID = "SolidTab"
CUSTOM_PANEL_ID = "DIYGarageCut_DIYGarageCutPropertiesAddin_Panel"
CUSTOM_PANEL_NAME = "DIY Garage Cut"
COMMAND_ID = "DIYGarageCut_DIYGarageCutPropertiesAddin_PropertiesCommand"
COMMAND_NAME = "DIYGC Eigenschaften"
COMMAND_TOOLTIP = "Material und Fräszulage für einen Body setzen."
COMMAND_RESOURCES = "./Resources"

ATTRIBUTE_GROUP = "DIYGarageCut.part_metadata"
ATTR_KEY_MATERIAL_ID = "material_id"
ATTR_KEY_TRIM_ALLOWANCE_MM = "trim_allowance_mm"
ATTR_KEY_GRAIN_DIRECTION = "grain_direction"
ATTR_KEY_FRONT_REFERENCE = "front_reference"
ATTR_KEY_EDGE_FRONT = "edge_front"
ATTR_KEY_EDGE_BACK = "edge_back"
ATTR_KEY_EDGE_LEFT = "edge_left"
ATTR_KEY_EDGE_RIGHT = "edge_right"
ATTR_KEY_SURFACE_TOP = "surface_top"
ATTR_KEY_SURFACE_BOTTOM = "surface_bottom"
ATTR_KEY_NOTES = "notes"
_TYPE_FIELD_TRIM_ALLOWANCE = "sheet_default_trim_allowance"
_TYPE_FIELD_HAS_GRAIN = "sheet_has_grain"
_TYPE_FIELD_DEFAULT_GRAIN_DIRECTION = "sheet_default_grain_direction"
_TYPE_FIELD_EDGE_THICKNESS = "edge_thickness"

_INPUT_BODY = "diygc_body_selection"
_INPUT_SIZE = "diygc_size"
_INPUT_FILTER_TYPE = "diygc_filter_type"
_INPUT_MATERIAL = "diygc_material"
_INPUT_TRIM_ALLOWANCE = "diygc_trim_allowance_mm"
_INPUT_GRAIN_DIRECTION = "diygc_grain_direction"
_INPUT_FRONT_FACE = "diygc_front_face"
_INPUT_EDGES_HEADER = "diygc_edges_header"
_INPUT_EDGE_MODE = "diygc_edge_mode"
_INPUT_EDGE_ALL = "diygc_edge_all"
_INPUT_EDGE_FRONT_ENABLED = "diygc_edge_front_enabled"
_INPUT_EDGE_FRONT = "diygc_edge_front"
_INPUT_EDGE_BACK_ENABLED = "diygc_edge_back_enabled"
_INPUT_EDGE_BACK = "diygc_edge_back"
_INPUT_EDGE_LEFT_ENABLED = "diygc_edge_left_enabled"
_INPUT_EDGE_LEFT = "diygc_edge_left"
_INPUT_EDGE_RIGHT_ENABLED = "diygc_edge_right_enabled"
_INPUT_EDGE_RIGHT = "diygc_edge_right"
_INPUT_SURFACE_ALL_TEXT = "diygc_surface_all_text"
_INPUT_TOP_ENABLED = "diygc_top_enabled"
_INPUT_TOP_SURFACE = "diygc_top_surface"
_INPUT_BOTTOM_ENABLED = "diygc_bottom_enabled"
_INPUT_BOTTOM_SURFACE = "diygc_bottom_surface"
_INPUT_NOTES_HEADER = "diygc_notes_header"
_INPUT_NOTES = "diygc_notes"

_handlers = []
_active_panel_id = None
_is_started = False
_command_created_handler = None
_material_entries = []
_material_by_id = {}
_material_label_to_id = {}
_material_id_to_label = {}
_edge_entries = []
_edge_by_id = {}
_edge_label_to_id = {}
_edge_id_to_label = {}
_surface_entries = []
_surface_by_id = {}
_surface_label_to_id = {}
_surface_id_to_label = {}
_body_token = ""
_front_face_token = ""
_front_body_token = ""
_ui_lang = "de"

_STRINGS = {
    "de": {
        "body": "Körper",
        "body_prompt": "Einen Körper auswählen",
        "size": "Bauteilgröße (L x B x Dicke)",
        "filter_type": "Filter",
        "filter_all_types": "Alle Typen",
        "material": "Material",
        "material_none": "(Bitte wählen)",
        "trim_allowance": "Fräszulage (mm)",
        "trim_allowance_tooltip": "Numerischer Wert in mm (z. B. 0,5).",
        "grain_direction": "Maserungsrichtung",
        "grain_none": "Keine",
        "grain_length": "Längs",
        "grain_width": "Quer",
        "front_face": "Vorderkante (Fläche)",
        "edges_section": "Bekantung und Oberflächen",
        "mode": "Modus",
        "mode_none": "Keine",
        "mode_all": "Alle gemeinsam",
        "mode_individual": "Individuell",
        "edge_all": "Kantenmaterial (alle)",
        "edge_none": "(Keine Kante)",
        "edge_front_enabled": "Vorne bekanten",
        "edge_front": "Kante vorne",
        "edge_back_enabled": "Hinten bekanten",
        "edge_back": "Kante hinten",
        "edge_left_enabled": "Links bekanten",
        "edge_left": "Kante links",
        "edge_right_enabled": "Rechts bekanten",
        "edge_right": "Kante rechts",
        "surface_all_text": "Oberfläche (alle)",
        "top_enabled": "Oberseite bearbeiten",
        "top_text": "Oberfläche oben",
        "bottom_enabled": "Unterseite bearbeiten",
        "bottom_text": "Oberfläche unten",
        "notes_section": "Fertigungshinweise",
        "surface_none": "(Keine Oberfläche)",
        "notes": "Fertigungshinweise",
        "face_prompt": "Planare Seitenfläche wählen",
    },
    "en": {
        "body": "Body",
        "body_prompt": "Select a body",
        "size": "Part size (L x W x Thickness)",
        "filter_type": "Filter",
        "filter_all_types": "All types",
        "material": "Material",
        "material_none": "(Please select)",
        "trim_allowance": "Trim allowance (mm)",
        "trim_allowance_tooltip": "Numeric value in mm (e.g. 0.5).",
        "grain_direction": "Grain direction",
        "grain_none": "None",
        "grain_length": "Length",
        "grain_width": "Width",
        "front_face": "Front edge (face)",
        "edges_section": "Edge banding and surfaces",
        "mode": "Mode",
        "mode_none": "None",
        "mode_all": "All together",
        "mode_individual": "Individual",
        "edge_all": "Edge material (all)",
        "edge_none": "(No edge)",
        "edge_front_enabled": "Band front",
        "edge_front": "Front edge",
        "edge_back_enabled": "Band back",
        "edge_back": "Back edge",
        "edge_left_enabled": "Band left",
        "edge_left": "Left edge",
        "edge_right_enabled": "Band right",
        "edge_right": "Right edge",
        "surface_all_text": "Surface (all)",
        "top_enabled": "Edit top side",
        "top_text": "Top surface",
        "bottom_enabled": "Edit bottom side",
        "bottom_text": "Bottom surface",
        "notes_section": "Production notes",
        "surface_none": "(No surface)",
        "notes": "Production notes",
        "face_prompt": "Select planar side face",
    },
}


class _MaterialEntry:
    def __init__(
        self,
        item_id,
        item_type,
        name,
        appearance_name,
        supports_trim_allowance,
        default_trim_allowance_mm,
        supports_grain,
        sheet_has_grain,
        default_grain_direction,
        supports_body_material,
        supports_edges,
        supports_surface,
        surface_entry_mode,
        edge_entry_mode,
    ):
        self.id = item_id
        self.type = item_type
        self.name = name
        self.appearance_name = appearance_name
        self.supports_trim_allowance = supports_trim_allowance
        self.default_trim_allowance_mm = default_trim_allowance_mm
        self.supports_grain = supports_grain
        self.sheet_has_grain = sheet_has_grain
        self.default_grain_direction = default_grain_direction
        self.supports_body_material = supports_body_material
        self.supports_edges = supports_edges
        self.supports_surface = supports_surface
        self.surface_entry_mode = surface_entry_mode
        self.edge_entry_mode = edge_entry_mode


class _EdgeEntry:
    def __init__(self, item_id, name, appearance_name, thickness_mm):
        self.id = item_id
        self.name = name
        self.appearance_name = appearance_name
        self.thickness_mm = thickness_mm


class _SurfaceEntry:
    def __init__(self, item_id, name, appearance_name):
        self.id = item_id
        self.name = name
        self.appearance_name = appearance_name


class _CommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def notify(self, args):
        global _ui_lang
        _ui_lang = _detect_ui_lang()

        event_args = adsk.core.CommandCreatedEventArgs.cast(args)
        cmd = event_args.command
        inputs = cmd.commandInputs

        _load_material_entries()

        sel = inputs.addSelectionInput(_INPUT_BODY, _t("body"), _t("body_prompt"))
        sel.addSelectionFilter("Bodies")
        sel.setSelectionLimits(1, 1)
        try:
            sel.isUseCurrentSelections = False
        except Exception:
            pass

        size_box = inputs.addTextBoxCommandInput(_INPUT_SIZE, _t("size"), "-", 1, True)
        size_box.isFullWidth = False

        filter_type = inputs.addDropDownCommandInput(
            _INPUT_FILTER_TYPE,
            _t("filter_type"),
            adsk.core.DropDownStyles.TextListDropDownStyle,
        )
        filter_type.listItems.add(_t("filter_all_types"), True)
        for type_id in _sorted_types():
            filter_type.listItems.add(_type_label(type_id), False)

        material_pick = inputs.addDropDownCommandInput(
            _INPUT_MATERIAL,
            _t("material"),
            adsk.core.DropDownStyles.TextListDropDownStyle,
        )
        _populate_material_dropdown(material_pick, selected_material_id=None, filter_type=None)

        trim_input = inputs.addStringValueInput(_INPUT_TRIM_ALLOWANCE, _t("trim_allowance"), "")
        trim_input.tooltip = _t("trim_allowance_tooltip")
        trim_input.isVisible = False

        grain_pick = inputs.addDropDownCommandInput(
            _INPUT_GRAIN_DIRECTION,
            _t("grain_direction"),
            adsk.core.DropDownStyles.TextListDropDownStyle,
        )
        _populate_grain_direction_dropdown(grain_pick, "none")
        grain_pick.isVisible = False
        front_face = inputs.addSelectionInput(_INPUT_FRONT_FACE, _t("front_face"), _t("face_prompt"))
        front_face.addSelectionFilter("PlanarFaces")
        front_face.setSelectionLimits(0, 1)
        try:
            front_face.isUseCurrentSelections = False
        except Exception:
            pass

        edges_header = inputs.addTextBoxCommandInput(_INPUT_EDGES_HEADER, "", _t("edges_section"), 1, True)
        edges_header.isFullWidth = True

        edge_mode = inputs.addDropDownCommandInput(
            _INPUT_EDGE_MODE, _t("mode"), adsk.core.DropDownStyles.TextListDropDownStyle
        )
        _populate_mode_dropdown(edge_mode, "individual")
        edge_all = inputs.addDropDownCommandInput(
            _INPUT_EDGE_ALL, _t("edge_all"), adsk.core.DropDownStyles.TextListDropDownStyle
        )

        edge_front_enabled = inputs.addBoolValueInput(
            _INPUT_EDGE_FRONT_ENABLED, _t("edge_front_enabled"), True, "", False
        )
        edge_front = inputs.addDropDownCommandInput(
            _INPUT_EDGE_FRONT, _t("edge_front"), adsk.core.DropDownStyles.TextListDropDownStyle
        )
        edge_back_enabled = inputs.addBoolValueInput(
            _INPUT_EDGE_BACK_ENABLED, _t("edge_back_enabled"), True, "", False
        )
        edge_back = inputs.addDropDownCommandInput(
            _INPUT_EDGE_BACK, _t("edge_back"), adsk.core.DropDownStyles.TextListDropDownStyle
        )
        edge_left_enabled = inputs.addBoolValueInput(
            _INPUT_EDGE_LEFT_ENABLED, _t("edge_left_enabled"), True, "", False
        )
        edge_left = inputs.addDropDownCommandInput(
            _INPUT_EDGE_LEFT, _t("edge_left"), adsk.core.DropDownStyles.TextListDropDownStyle
        )
        edge_right_enabled = inputs.addBoolValueInput(
            _INPUT_EDGE_RIGHT_ENABLED, _t("edge_right_enabled"), True, "", False
        )
        edge_right = inputs.addDropDownCommandInput(
            _INPUT_EDGE_RIGHT, _t("edge_right"), adsk.core.DropDownStyles.TextListDropDownStyle
        )
        top_enabled = inputs.addBoolValueInput(_INPUT_TOP_ENABLED, _t("top_enabled"), True, "", False)
        surface_all_text = inputs.addStringValueInput(_INPUT_SURFACE_ALL_TEXT, _t("surface_all_text"), "")
        top_surface = inputs.addDropDownCommandInput(
            _INPUT_TOP_SURFACE, _t("top_text"), adsk.core.DropDownStyles.TextListDropDownStyle
        )
        bottom_enabled = inputs.addBoolValueInput(_INPUT_BOTTOM_ENABLED, _t("bottom_enabled"), True, "", False)
        bottom_surface = inputs.addDropDownCommandInput(
            _INPUT_BOTTOM_SURFACE, _t("bottom_text"), adsk.core.DropDownStyles.TextListDropDownStyle
        )
        notes_header = inputs.addTextBoxCommandInput(_INPUT_NOTES_HEADER, "", _t("notes_section"), 1, True)
        notes_header.isFullWidth = True
        notes = inputs.addTextBoxCommandInput(_INPUT_NOTES, _t("notes"), "", 4, False)
        notes.isFullWidth = True
        _populate_edge_dropdown(edge_all, None)
        _populate_edge_dropdown(edge_front, None)
        _populate_edge_dropdown(edge_back, None)
        _populate_edge_dropdown(edge_left, None)
        _populate_edge_dropdown(edge_right, None)
        _populate_surface_dropdown(top_surface, None)
        _populate_surface_dropdown(bottom_surface, None)

        _set_main_controls_visible(inputs, False)
        _set_edge_controls_visible(inputs, False)
        _set_notes_controls_visible(inputs, False)
        _set_edge_dropdown_enabled_state(inputs)

        on_input_changed = _InputChangedHandler()
        cmd.inputChanged.add(on_input_changed)
        _handlers.append(on_input_changed)

        on_execute = _ExecuteHandler()
        cmd.execute.add(on_execute)
        _handlers.append(on_execute)

        on_validate = _ValidateInputsHandler()
        cmd.validateInputs.add(on_validate)
        _handlers.append(on_validate)


class _InputChangedHandler(adsk.core.InputChangedEventHandler):
    def notify(self, args):
        try:
            event_args = adsk.core.InputChangedEventArgs.cast(args)
            changed = event_args.input
            if not changed:
                return
            command = event_args.firingEvent.sender
            inputs = command.commandInputs if command else None
            if not inputs:
                return

            if changed.id == _INPUT_BODY:
                _refresh_inputs_from_selected_body(inputs)
                return

            if changed.id == _INPUT_FILTER_TYPE:
                filter_type = _read_filter_type(inputs)
                selected_material_id = _read_material_dropdown_value(inputs, raise_on_unknown=False)
                material_pick = adsk.core.DropDownCommandInput.cast(inputs.itemById(_INPUT_MATERIAL))
                _populate_material_dropdown(material_pick, selected_material_id=selected_material_id, filter_type=filter_type)
                _update_trim_allowance_visibility(inputs, selected_material_id)
                _update_grain_direction_visibility(inputs, selected_material_id)
                return

            if changed.id == _INPUT_MATERIAL:
                selected_id = _read_material_dropdown_value(inputs, raise_on_unknown=True)
                if not selected_id:
                    _set_input_value(inputs, _INPUT_TRIM_ALLOWANCE, "")
                    _update_trim_allowance_visibility(inputs, None)
                    _set_grain_direction_dropdown(inputs, "none")
                    _update_grain_direction_visibility(inputs, None)
                    _set_edge_controls_for_material(inputs, None)
                    _set_notes_controls_visible(inputs, False)
                    return
                _update_trim_allowance_visibility(inputs, selected_id)
                _update_grain_direction_visibility(inputs, selected_id)
                _set_edge_controls_for_material(inputs, selected_id)
                _set_notes_controls_visible(inputs, True)
                entry = _material_by_id.get(selected_id)
                if entry and entry.supports_trim_allowance:
                    _set_input_value(inputs, _INPUT_TRIM_ALLOWANCE, _format_trim_allowance(entry.default_trim_allowance_mm))
                if _material_requires_grain_direction(entry):
                    _set_grain_direction_dropdown(inputs, entry.default_grain_direction)
                return

            if changed.id == _INPUT_FRONT_FACE:
                body = _read_selected_body(inputs)
                if not body:
                    _set_front_face_selection(inputs, None)
                    _clear_front_face_memory()
                    _set_edge_controls_visible(inputs, False)
                    return
                _validate_front_face_selection(inputs, body)
                _sync_edge_controls_from_body_attributes(inputs, body)
                _set_edge_dropdown_enabled_state(inputs)
                _apply_edge_appearance_preview(inputs)
                return

            if changed.id in (
                _INPUT_EDGE_FRONT_ENABLED,
                _INPUT_EDGE_BACK_ENABLED,
                _INPUT_EDGE_LEFT_ENABLED,
                _INPUT_EDGE_RIGHT_ENABLED,
                _INPUT_TOP_ENABLED,
                _INPUT_BOTTOM_ENABLED,
            ):
                _set_edge_dropdown_enabled_state(inputs)
                _apply_edge_appearance_preview(inputs)
                _apply_surface_appearance_preview(inputs)
                return

            if changed.id == _INPUT_EDGE_MODE:
                _set_edge_dropdown_enabled_state(inputs)
                _apply_edge_appearance_preview(inputs)
                _apply_surface_appearance_preview(inputs)
                return

            if changed.id in (_INPUT_EDGE_ALL, _INPUT_EDGE_FRONT, _INPUT_EDGE_BACK, _INPUT_EDGE_LEFT, _INPUT_EDGE_RIGHT):
                _apply_edge_appearance_preview(inputs)
                return
            if changed.id in (_INPUT_TOP_SURFACE, _INPUT_BOTTOM_SURFACE):
                _apply_surface_appearance_preview(inputs)
                return
        except Exception as exc:
            print(f"Properties: InputChanged-Fehler: {exc}")


class _ExecuteHandler(adsk.core.CommandEventHandler):
    def notify(self, args):
        app = adsk.core.Application.get()
        ui = app.userInterface if app else None
        if not app or not ui:
            print("Properties: App/UI nicht verfügbar.")
            return
        try:
            event_args = adsk.core.CommandEventArgs.cast(args)
            command = event_args.command if event_args else None
            inputs = command.commandInputs if command else None
            if not inputs:
                ui.messageBox("Properties-Fehler: Keine Command-Inputs verfügbar.")
                return

            body = _read_selected_body(inputs)
            if not body:
                ui.messageBox(f"Bitte im Dialog einen {_t('body').lower()} auswählen.")
                return

            material_id = _read_material_dropdown_value(inputs, raise_on_unknown=True)
            if not material_id:
                ui.messageBox(f"Bitte ein {_t('material').lower()} auswählen.")
                return
            entry = _material_by_id.get(material_id)
            if not entry:
                raise RuntimeError(f"Material '{material_id}' ist nicht im Katalog vorhanden.")

            old_material_id = str(_get_attr(body, ATTR_KEY_MATERIAL_ID, "") or "").strip()
            _write_body_attribute_or_raise(body, ATTR_KEY_MATERIAL_ID, material_id)

            if entry.supports_trim_allowance:
                trim_input = _read_string_input(inputs, _INPUT_TRIM_ALLOWANCE, "")
                trim_allowance_mm = _parse_trim_allowance(trim_input)
                _write_body_attribute_or_raise(body, ATTR_KEY_TRIM_ALLOWANCE_MM, _format_trim_allowance(trim_allowance_mm))
            else:
                _clear_body_attribute_or_raise(body, ATTR_KEY_TRIM_ALLOWANCE_MM)

            if _material_requires_grain_direction(entry):
                grain_direction = _read_grain_direction_dropdown(inputs)
                _write_body_attribute_or_raise(body, ATTR_KEY_GRAIN_DIRECTION, grain_direction)
            else:
                _clear_body_attribute_or_raise(body, ATTR_KEY_GRAIN_DIRECTION)

            if entry.supports_surface:
                surface_values = _read_surface_values_for_mode(inputs)
                _write_or_clear_body_attribute(body, ATTR_KEY_SURFACE_TOP, surface_values.get(ATTR_KEY_SURFACE_TOP, ""))
                _write_or_clear_body_attribute(
                    body, ATTR_KEY_SURFACE_BOTTOM, surface_values.get(ATTR_KEY_SURFACE_BOTTOM, "")
                )
            else:
                _clear_body_attribute_or_raise(body, ATTR_KEY_SURFACE_TOP)
                _clear_body_attribute_or_raise(body, ATTR_KEY_SURFACE_BOTTOM)

            notes = _read_string_input(inputs, _INPUT_NOTES, "").strip()
            _write_or_clear_body_attribute(body, ATTR_KEY_NOTES, notes)

            edge_mode = _read_mode_dropdown(inputs, _INPUT_EDGE_MODE, "none")
            side_faces = None
            edge_values = _read_edge_values_for_mode(inputs, require_material=True) if entry.supports_edges else {}
            has_edge_values = any(str(value or "").strip() for value in edge_values.values())
            if entry.supports_edges and edge_mode == "individual" and has_edge_values:
                side_faces, front_reference = _resolve_side_faces_from_front_selection(inputs, body)
                if not side_faces:
                    raise RuntimeError("Für aktivierte Bekantung bitte zuerst eine Vorderkante auswählen.")
                _write_body_attribute_or_raise(body, ATTR_KEY_FRONT_REFERENCE, front_reference)
                for attr_key, edge_id in edge_values.items():
                    if edge_id:
                        _write_body_attribute_or_raise(body, attr_key, edge_id)
                    else:
                        _clear_body_attribute_or_raise(body, attr_key)
            else:
                _clear_body_attribute_or_raise(body, ATTR_KEY_FRONT_REFERENCE)
                _clear_body_attribute_or_raise(body, ATTR_KEY_EDGE_FRONT)
                _clear_body_attribute_or_raise(body, ATTR_KEY_EDGE_BACK)
                _clear_body_attribute_or_raise(body, ATTR_KEY_EDGE_LEFT)
                _clear_body_attribute_or_raise(body, ATTR_KEY_EDGE_RIGHT)

            if material_id != old_material_id:
                _apply_material_appearance_or_raise(body, material_id)

            if entry.supports_edges and edge_mode == "individual" and side_faces:
                _apply_edge_appearance_from_resolved_faces(body, side_faces, edge_values)
            if entry.supports_surface:
                _apply_surface_appearance_from_body_faces(body, _read_surface_values_for_mode(inputs))

            if _is_body_likely_read_only(body):
                diag = _diagnose_attribute_context(body)
                ui.messageBox(
                    "Eigenschaften gespeichert, aber der Body wirkt schreibgeschützt.\n"
                    "Bitte Ergebnis prüfen.\n\nDiagnose:\n"
                    f"{diag}"
                )
                return

            print(f"Properties gespeichert für Body: {body.name}")
        except Exception as exc:
            print(f"Properties: Execute-Fehler: {exc}")
            ui.messageBox(f"Eigenschaften fehlgeschlagen:\n{exc}")


class _ValidateInputsHandler(adsk.core.ValidateInputsEventHandler):
    def notify(self, args):
        event_args = adsk.core.ValidateInputsEventArgs.cast(args)
        if not event_args:
            return
        try:
            inputs = event_args.inputs
            body = _read_selected_body(inputs) if inputs else None
            material_id = _read_material_dropdown_value(inputs, raise_on_unknown=False) if inputs else ""
            event_args.areInputsValid = bool(body and material_id)
        except Exception as exc:
            print(f"Properties: ValidateInputs-Fehler: {exc}")
            event_args.areInputsValid = False


def _load_material_entries():
    global _material_entries, _material_by_id, _edge_entries, _edge_by_id, _surface_entries, _surface_by_id
    catalog = load_catalog()
    entries = []
    edge_entries = []
    surface_entries = []
    for item in catalog.items:
        if not item.id or not item.name:
            raise RuntimeError("Katalog enthält ungültiges Material ohne id/name.")
        if not item.appearance:
            raise RuntimeError(f"Katalog-Eintrag '{item.id}' hat keine Appearance.")
        capabilities = get_type_capabilities(item.type)
        supports_trim = _type_supports_trim_allowance(item.type)
        default_trim = _extract_default_trim_allowance(item, supports_trim)
        supports_grain = _type_supports_grain(item.type)
        sheet_has_grain = _extract_sheet_has_grain(item, supports_grain)
        default_grain_direction = _extract_default_grain_direction(item, supports_grain)
        if capabilities.get("supports_body_material", True):
            entries.append(
                _MaterialEntry(
                    item_id=item.id,
                    item_type=item.type,
                    name=item.name,
                    appearance_name=item.appearance,
                    supports_trim_allowance=supports_trim,
                    default_trim_allowance_mm=default_trim,
                    supports_grain=supports_grain,
                    sheet_has_grain=sheet_has_grain,
                    default_grain_direction=default_grain_direction,
                    supports_body_material=True,
                    supports_edges=bool(capabilities.get("supports_edges")),
                    supports_surface=bool(capabilities.get("supports_surface")),
                    surface_entry_mode=str(capabilities.get("surface_entry_mode", "none")),
                    edge_entry_mode=str(capabilities.get("edge_entry_mode", "none")),
                )
            )
        if item.type == "edge":
            edge_entries.append(
                _EdgeEntry(
                    item_id=item.id,
                    name=item.name,
                    appearance_name=item.appearance,
                    thickness_mm=_extract_edge_thickness(item),
                )
            )
        if item.type == "surface":
            surface_entries.append(
                _SurfaceEntry(
                    item_id=item.id,
                    name=item.name,
                    appearance_name=item.appearance,
                )
            )

    if not entries:
        raise RuntimeError("Katalog enthält keine Einträge.")
    if not edge_entries:
        raise RuntimeError("Katalog enthält keine Einträge vom Typ 'edge'.")

    entries.sort(key=lambda entry: (_type_label(entry.type).lower(), entry.name.lower(), entry.id.lower()))
    edge_entries.sort(key=lambda entry: (entry.name.lower(), entry.id.lower()))
    surface_entries.sort(key=lambda entry: (entry.name.lower(), entry.id.lower()))
    _material_entries = entries
    _material_by_id = {entry.id: entry for entry in entries}
    _edge_entries = edge_entries
    _edge_by_id = {entry.id: entry for entry in edge_entries}
    _surface_entries = surface_entries
    _surface_by_id = {entry.id: entry for entry in surface_entries}


def _type_supports_trim_allowance(type_id):
    for field in get_type_fields(type_id):
        if str(field.get("key", "")).strip() == _TYPE_FIELD_TRIM_ALLOWANCE:
            return True
    return False


def _type_supports_grain(type_id):
    keys = {str(field.get("key", "")).strip() for field in get_type_fields(type_id)}
    return _TYPE_FIELD_HAS_GRAIN in keys and _TYPE_FIELD_DEFAULT_GRAIN_DIRECTION in keys


def _extract_default_trim_allowance(item, supports_trim):
    if not supports_trim:
        return 0.0
    raw = (item.properties or {}).get(_TYPE_FIELD_TRIM_ALLOWANCE)
    if raw in (None, ""):
        return 0.0
    try:
        numeric = float(raw)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(
            f"Katalog-Eintrag '{item.id}' hat ungültige {_TYPE_FIELD_TRIM_ALLOWANCE}: {raw}"
        ) from exc
    if numeric < 0:
        raise RuntimeError(
            f"Katalog-Eintrag '{item.id}' hat negative {_TYPE_FIELD_TRIM_ALLOWANCE}: {raw}"
        )
    return numeric


def _extract_sheet_has_grain(item, supports_grain):
    if not supports_grain:
        return "none"
    raw = str((item.properties or {}).get(_TYPE_FIELD_HAS_GRAIN, "none") or "none").strip().lower()
    if raw not in ("none", "yes", "no"):
        raise RuntimeError(f"Katalog-Eintrag '{item.id}' hat ungültige {_TYPE_FIELD_HAS_GRAIN}: {raw}")
    return raw


def _extract_default_grain_direction(item, supports_grain):
    if not supports_grain:
        return "none"
    raw = str((item.properties or {}).get(_TYPE_FIELD_DEFAULT_GRAIN_DIRECTION, "none") or "none").strip().lower()
    if raw not in ("none", "length", "width"):
        raise RuntimeError(
            f"Katalog-Eintrag '{item.id}' hat ungültige {_TYPE_FIELD_DEFAULT_GRAIN_DIRECTION}: {raw}"
        )
    return raw


def _extract_edge_thickness(item):
    raw = (item.properties or {}).get(_TYPE_FIELD_EDGE_THICKNESS)
    if raw in (None, ""):
        return 0.0
    try:
        numeric = float(raw)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(
            f"Katalog-Eintrag '{item.id}' hat ungültige {_TYPE_FIELD_EDGE_THICKNESS}: {raw}"
        ) from exc
    if numeric < 0:
        raise RuntimeError(
            f"Katalog-Eintrag '{item.id}' hat negative {_TYPE_FIELD_EDGE_THICKNESS}: {raw}"
        )
    return numeric


def _format_material_label(entry):
    return f"{entry.name} [{_type_label(entry.type)}]"


def _refresh_inputs_from_selected_body(inputs):
    body = _read_selected_body(inputs)
    if not body:
        _set_input_value(inputs, _INPUT_SIZE, "-")
        _set_filter_dropdown_value(inputs, None)
        material_pick = adsk.core.DropDownCommandInput.cast(inputs.itemById(_INPUT_MATERIAL))
        _populate_material_dropdown(material_pick, selected_material_id=None, filter_type=None)
        _set_input_value(inputs, _INPUT_TRIM_ALLOWANCE, "")
        _update_trim_allowance_visibility(inputs, None)
        _set_grain_direction_dropdown(inputs, "none")
        _update_grain_direction_visibility(inputs, None)
        _set_front_face_selection(inputs, None)
        _set_mode_dropdown(inputs, _INPUT_EDGE_MODE, "none")
        _set_edge_dropdown_value(inputs, _INPUT_EDGE_ALL, "")
        _set_input_value(inputs, _INPUT_SURFACE_ALL_TEXT, "")
        _set_edge_enabled(inputs, _INPUT_TOP_ENABLED, False)
        _set_edge_enabled(inputs, _INPUT_BOTTOM_ENABLED, False)
        _set_surface_dropdown_value(inputs, _INPUT_TOP_SURFACE, "")
        _set_surface_dropdown_value(inputs, _INPUT_BOTTOM_SURFACE, "")
        _set_input_value(inputs, _INPUT_NOTES, "")
        _set_edge_dropdown_value(inputs, _INPUT_EDGE_FRONT, "")
        _set_edge_dropdown_value(inputs, _INPUT_EDGE_BACK, "")
        _set_edge_dropdown_value(inputs, _INPUT_EDGE_LEFT, "")
        _set_edge_dropdown_value(inputs, _INPUT_EDGE_RIGHT, "")
        _set_edge_enabled(inputs, _INPUT_EDGE_FRONT_ENABLED, False)
        _set_edge_enabled(inputs, _INPUT_EDGE_BACK_ENABLED, False)
        _set_edge_enabled(inputs, _INPUT_EDGE_LEFT_ENABLED, False)
        _set_edge_enabled(inputs, _INPUT_EDGE_RIGHT_ENABLED, False)
        _set_main_controls_visible(inputs, False)
        _set_edge_controls_visible(inputs, False)
        _set_notes_controls_visible(inputs, False)
        _clear_front_face_memory()
        return

    _set_main_controls_visible(inputs, True)
    front_face = _selected_or_restored_front_face(inputs, body)
    if front_face and not _face_belongs_to_body(front_face, body):
        _set_front_face_selection(inputs, None)
        _clear_front_face_memory()

    _set_input_value(inputs, _INPUT_SIZE, _format_body_size(body))
    material_id = str(_get_attr(body, ATTR_KEY_MATERIAL_ID, "") or "").strip()
    trim_allowance = str(_get_attr(body, ATTR_KEY_TRIM_ALLOWANCE_MM, "") or "").strip()
    entry = _material_by_id.get(material_id)
    filter_type = entry.type if entry else _read_filter_type(inputs)

    _set_filter_dropdown_value(inputs, filter_type)
    material_pick = adsk.core.DropDownCommandInput.cast(inputs.itemById(_INPUT_MATERIAL))
    _populate_material_dropdown(material_pick, selected_material_id=material_id or None, filter_type=filter_type)
    _update_trim_allowance_visibility(inputs, material_id or None)
    _update_grain_direction_visibility(inputs, material_id or None)
    _set_edge_controls_for_material(inputs, material_id or None)
    _set_notes_controls_visible(inputs, bool(material_id))

    if entry and entry.supports_trim_allowance:
        if trim_allowance:
            _set_input_value(inputs, _INPUT_TRIM_ALLOWANCE, trim_allowance)
        else:
            _set_input_value(inputs, _INPUT_TRIM_ALLOWANCE, _format_trim_allowance(entry.default_trim_allowance_mm))
    else:
        _set_input_value(inputs, _INPUT_TRIM_ALLOWANCE, "")

    grain_direction = str(_get_attr(body, ATTR_KEY_GRAIN_DIRECTION, "") or "").strip().lower()
    if _material_requires_grain_direction(entry):
        if grain_direction not in ("none", "length", "width"):
            grain_direction = entry.default_grain_direction
        _set_grain_direction_dropdown(inputs, grain_direction)
    else:
        _set_grain_direction_dropdown(inputs, "none")

    _ensure_front_face_from_attributes(inputs, body)
    _set_surface_dropdown_value(inputs, _INPUT_TOP_SURFACE, str(_get_attr(body, ATTR_KEY_SURFACE_TOP, "") or "").strip())
    _set_surface_dropdown_value(
        inputs, _INPUT_BOTTOM_SURFACE, str(_get_attr(body, ATTR_KEY_SURFACE_BOTTOM, "") or "").strip()
    )
    _set_input_value(inputs, _INPUT_NOTES, str(_get_attr(body, ATTR_KEY_NOTES, "") or "").strip())
    _set_input_value(inputs, _INPUT_SURFACE_ALL_TEXT, "")
    _sync_edge_controls_from_body_attributes(inputs, body)
    _set_edge_controls_for_material(inputs, material_id or None)
    _set_notes_controls_visible(inputs, bool(material_id))
    _set_edge_dropdown_enabled_state(inputs)


def _populate_material_dropdown(dropdown, selected_material_id=None, filter_type=None):
    global _material_label_to_id, _material_id_to_label
    if not dropdown:
        return

    _material_label_to_id = {}
    _material_id_to_label = {}
    dropdown.listItems.clear()

    none_label = _t("material_none")
    dropdown.listItems.add(none_label, selected_material_id is None)

    selected_found = selected_material_id is None
    for entry in _material_entries:
        if filter_type and entry.type != filter_type:
            continue
        label = _format_material_label(entry)
        _material_label_to_id[label] = entry.id
        _material_id_to_label[entry.id] = label
        is_selected = entry.id == selected_material_id
        dropdown.listItems.add(label, is_selected)
        if is_selected:
            selected_found = True

    if not selected_found and dropdown.listItems.count > 0:
        dropdown.listItems.item(0).isSelected = True


def _set_main_controls_visible(inputs, visible):
    main_ids = (
        _INPUT_SIZE,
        _INPUT_FILTER_TYPE,
        _INPUT_MATERIAL,
        _INPUT_TRIM_ALLOWANCE,
        _INPUT_GRAIN_DIRECTION,
        _INPUT_FRONT_FACE,
    )
    for input_id in main_ids:
        item = inputs.itemById(input_id)
        if item:
            item.isVisible = bool(visible)


def _set_edge_controls_visible(inputs, visible):
    edge_ids = (
        _INPUT_EDGES_HEADER,
        _INPUT_EDGE_MODE,
        _INPUT_EDGE_ALL,
        _INPUT_EDGE_FRONT_ENABLED,
        _INPUT_EDGE_FRONT,
        _INPUT_EDGE_BACK_ENABLED,
        _INPUT_EDGE_BACK,
        _INPUT_EDGE_LEFT_ENABLED,
        _INPUT_EDGE_LEFT,
        _INPUT_EDGE_RIGHT_ENABLED,
        _INPUT_EDGE_RIGHT,
        _INPUT_SURFACE_ALL_TEXT,
        _INPUT_TOP_ENABLED,
        _INPUT_TOP_SURFACE,
        _INPUT_BOTTOM_ENABLED,
        _INPUT_BOTTOM_SURFACE,
    )
    for input_id in edge_ids:
        item = inputs.itemById(input_id)
        if item:
            item.isVisible = bool(visible)
    for enabled_id in (
        _INPUT_EDGE_FRONT_ENABLED,
        _INPUT_EDGE_BACK_ENABLED,
        _INPUT_EDGE_LEFT_ENABLED,
        _INPUT_EDGE_RIGHT_ENABLED,
    ):
        enabled_item = _edge_enabled_input(inputs, enabled_id)
        if enabled_item:
            enabled_item.isEnabled = True


def _set_notes_controls_visible(inputs, visible):
    for input_id in (_INPUT_NOTES_HEADER, _INPUT_NOTES):
        item = inputs.itemById(input_id)
        if item:
            item.isVisible = bool(visible)
            item.isEnabled = bool(visible)


def _set_edge_controls_for_material(inputs, material_id):
    entry = _material_by_id.get(material_id or "")
    visible = bool(entry and entry.supports_edges)
    _set_edge_controls_visible(inputs, visible)
    front_face = _front_face_selection_input(inputs)
    if front_face:
        front_face.isVisible = visible
        front_face.isEnabled = visible
    if not visible:
        _set_mode_dropdown(inputs, _INPUT_EDGE_MODE, "none")
        _clear_front_face_memory()
    _set_edge_dropdown_enabled_state(inputs)


def _front_face_selection_input(inputs):
    return adsk.core.SelectionCommandInput.cast(inputs.itemById(_INPUT_FRONT_FACE))


def _body_selection_input(inputs):
    return adsk.core.SelectionCommandInput.cast(inputs.itemById(_INPUT_BODY))


def _selection_entity_by_input_id(inputs, input_id):
    sel = adsk.core.SelectionCommandInput.cast(inputs.itemById(input_id))
    if not sel or sel.selectionCount < 1:
        return None
    try:
        return sel.selection(0).entity
    except Exception:
        return None


def _same_entity(left, right):
    left_token = _get_entity_token(left) or ""
    right_token = _get_entity_token(right) or ""
    return bool(left_token and right_token and left_token == right_token)


def _set_selection_entity_by_input_id(inputs, input_id, entity):
    sel = adsk.core.SelectionCommandInput.cast(inputs.itemById(input_id))
    if not sel:
        return False
    current = _selection_entity_by_input_id(inputs, input_id)
    if not entity:
        try:
            sel.clearSelection()
            return True
        except Exception:
            return False
    if current and _same_entity(current, entity):
        return True

    previous = current
    try:
        sel.clearSelection()
    except Exception:
        pass
    try:
        ok = sel.addSelection(entity)
        if ok:
            return True
    except Exception as exc:
        print(f"Properties: Auswahl konnte nicht gesetzt werden ({input_id}): {exc}")
    if previous:
        try:
            sel.addSelection(previous)
        except Exception:
            pass
    return False


def _selection_face_by_input_id(inputs, input_id):
    entity = _selection_entity_by_input_id(inputs, input_id)
    face = adsk.fusion.BRepFace.cast(entity)
    if not face:
        return None
    native = adsk.fusion.BRepFace.cast(getattr(face, "nativeObject", None))
    return native if native else face


def _set_selection_face_by_input_id(inputs, input_id, face):
    _set_selection_entity_by_input_id(inputs, input_id, face)


def _selected_front_face(inputs):
    return _selection_face_by_input_id(inputs, _INPUT_FRONT_FACE)


def _set_front_face_selection(inputs, face):
    _set_selection_face_by_input_id(inputs, _INPUT_FRONT_FACE, face)


def _set_body_selection(inputs, body):
    _set_selection_entity_by_input_id(inputs, _INPUT_BODY, body)


def _clear_body_selection_memory():
    global _body_token
    _body_token = ""


def _remember_body_selection(body):
    global _body_token
    _body_token = _get_entity_token(body) or ""


def _clear_front_face_memory():
    global _front_face_token, _front_body_token
    _front_face_token = ""
    _front_body_token = ""


def _remember_front_face_selection(body, face):
    global _front_face_token, _front_body_token
    _front_body_token = _get_entity_token(body) or ""
    _front_face_token = _get_entity_token(face) or ""


def _selected_or_restored_front_face(inputs, body):
    face = _selected_front_face(inputs)
    if face:
        if _face_belongs_to_body(face, body):
            _remember_front_face_selection(body, face)
            return face
        _set_front_face_selection(inputs, None)
        _clear_front_face_memory()
        return None
    return _restore_front_face_from_memory(inputs, body)


def _get_or_derive_front_face(inputs, body):
    face = _selected_or_restored_front_face(inputs, body)
    if face:
        return face
    _ensure_front_face_from_attributes(inputs, body)
    return _selected_or_restored_front_face(inputs, body)


def _restore_body_selection_from_memory(inputs):
    if not _body_token:
        return None
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct) if app else None
    if not design:
        return None
    try:
        entities = design.findEntityByToken(_body_token)
    except Exception:
        return None
    if not entities:
        return None
    for entity in entities:
        candidate = adsk.fusion.BRepBody.cast(entity)
        if not candidate:
            continue
        native = adsk.fusion.BRepBody.cast(getattr(candidate, "nativeObject", None))
        body = native if native else candidate
        _set_body_selection(inputs, candidate)
        _remember_body_selection(body)
        return body
    return None


def _restore_front_face_from_memory(inputs, body):
    if not body:
        return None
    body_token = _get_entity_token(body) or ""
    if not body_token or body_token != _front_body_token or not _front_face_token:
        return None
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct) if app else None
    if not design:
        return None
    try:
        entities = design.findEntityByToken(_front_face_token)
    except Exception:
        return None
    if not entities:
        return None
    for entity in entities:
        candidate = adsk.fusion.BRepFace.cast(entity)
        if not candidate:
            continue
        native = adsk.fusion.BRepFace.cast(getattr(candidate, "nativeObject", None))
        face = native if native else candidate
        if _face_belongs_to_body(face, body):
            _set_front_face_selection(inputs, face)
            return face
    return None


def _format_edge_label(entry):
    thickness = _format_trim_allowance(entry.thickness_mm)
    return f"{entry.name} ({thickness} mm)"


def _populate_mode_dropdown(dropdown, selected_mode):
    if not dropdown:
        return
    dropdown.listItems.clear()
    wanted = str(selected_mode or "none").strip().lower()
    if wanted not in ("none", "all", "individual"):
        wanted = "none"
    options = [
        ("none", _t("mode_none")),
        ("all", _t("mode_all")),
        ("individual", _t("mode_individual")),
    ]
    for value, label in options:
        dropdown.listItems.add(label, value == wanted)


def _read_mode_dropdown(inputs, input_id, fallback):
    label = _read_dropdown_value(inputs, input_id, "")
    mapping = {
        _t("mode_none").lower(): "none",
        _t("mode_all").lower(): "all",
        _t("mode_individual").lower(): "individual",
    }
    mode = mapping.get(label.lower(), fallback)
    if mode not in ("none", "all", "individual"):
        return fallback
    return mode


def _set_mode_dropdown(inputs, input_id, mode):
    dropdown = adsk.core.DropDownCommandInput.cast(inputs.itemById(input_id))
    _populate_mode_dropdown(dropdown, mode)


def _populate_edge_dropdown(dropdown, selected_edge_id=None):
    global _edge_label_to_id, _edge_id_to_label
    if not dropdown:
        return
    _edge_label_to_id = {}
    _edge_id_to_label = {}
    dropdown.listItems.clear()

    none_label = _t("edge_none")
    dropdown.listItems.add(none_label, selected_edge_id is None or selected_edge_id == "")
    selected_found = selected_edge_id in (None, "")
    for entry in _edge_entries:
        label = _format_edge_label(entry)
        _edge_label_to_id[label] = entry.id
        _edge_id_to_label[entry.id] = label
        is_selected = entry.id == selected_edge_id
        dropdown.listItems.add(label, is_selected)
        if is_selected:
            selected_found = True
    if not selected_found and selected_edge_id not in (None, ""):
        unknown_label = f"[Ungültige Kante] {selected_edge_id}"
        _edge_label_to_id[unknown_label] = str(selected_edge_id)
        dropdown.listItems.add(unknown_label, True)
        selected_found = True
    if not selected_found and dropdown.listItems.count > 0:
        dropdown.listItems.item(0).isSelected = True


def _set_edge_dropdown_value(inputs, input_id, edge_id):
    dropdown = adsk.core.DropDownCommandInput.cast(inputs.itemById(input_id))
    _populate_edge_dropdown(dropdown, edge_id or None)


def _read_edge_dropdown_value(inputs, input_id):
    label = _read_dropdown_value(inputs, input_id, "")
    none_label = _t("edge_none")
    if not label or label.lower() == none_label.lower():
        return ""
    edge_id = _edge_label_to_id.get(label, "")
    if not edge_id:
        raise RuntimeError(f"Unbekannter Kanten-Dropdown-Wert: '{label}'")
    return edge_id


def _format_surface_label(entry):
    return str(entry.name or entry.id)


def _populate_surface_dropdown(dropdown, selected_surface_id=None):
    global _surface_label_to_id, _surface_id_to_label
    if not dropdown:
        return
    _surface_label_to_id = {}
    _surface_id_to_label = {}
    dropdown.listItems.clear()

    none_label = _t("surface_none")
    dropdown.listItems.add(none_label, selected_surface_id is None or selected_surface_id == "")
    selected_found = selected_surface_id in (None, "")
    for entry in _surface_entries:
        label = _format_surface_label(entry)
        _surface_label_to_id[label] = entry.id
        _surface_id_to_label[entry.id] = label
        is_selected = entry.id == selected_surface_id
        dropdown.listItems.add(label, is_selected)
        if is_selected:
            selected_found = True
    if not selected_found and selected_surface_id not in (None, ""):
        unknown_label = f"[Ungültige Oberfläche] {selected_surface_id}"
        _surface_label_to_id[unknown_label] = str(selected_surface_id)
        dropdown.listItems.add(unknown_label, True)
        selected_found = True
    if not selected_found and dropdown.listItems.count > 0:
        dropdown.listItems.item(0).isSelected = True


def _set_surface_dropdown_value(inputs, input_id, surface_id):
    dropdown = adsk.core.DropDownCommandInput.cast(inputs.itemById(input_id))
    _populate_surface_dropdown(dropdown, surface_id or None)


def _read_surface_dropdown_value(inputs, input_id):
    label = _read_dropdown_value(inputs, input_id, "")
    none_label = _t("surface_none")
    if not label or label.lower() == none_label.lower():
        return ""
    surface_id = _surface_label_to_id.get(label, "")
    if not surface_id:
        raise RuntimeError(f"Unbekannter Oberflächen-Dropdown-Wert: '{label}'")
    if surface_id and surface_id not in _surface_by_id:
        raise RuntimeError(f"Oberfläche '{surface_id}' ist nicht im Katalog vorhanden.")
    return surface_id


def _edge_enabled_input(inputs, enabled_input_id):
    return adsk.core.BoolValueCommandInput.cast(inputs.itemById(enabled_input_id))


def _is_edge_enabled(inputs, enabled_input_id):
    item = _edge_enabled_input(inputs, enabled_input_id)
    return bool(item and item.value)


def _set_edge_enabled(inputs, enabled_input_id, enabled):
    item = _edge_enabled_input(inputs, enabled_input_id)
    if item:
        item.value = bool(enabled)


def _set_edge_dropdown_enabled_state(inputs):
    header = adsk.core.TextBoxCommandInput.cast(inputs.itemById(_INPUT_EDGES_HEADER))
    section_visible = bool(header and header.isVisible)
    edge_mode = _read_mode_dropdown(inputs, _INPUT_EDGE_MODE, "none")
    body = _read_selected_body(inputs)
    has_front_face = bool(body and _get_or_derive_front_face(inputs, body))

    edge_all = adsk.core.DropDownCommandInput.cast(inputs.itemById(_INPUT_EDGE_ALL))
    if edge_all:
        edge_all.isVisible = False
        edge_all.isEnabled = False

    mapping = {
        _INPUT_EDGE_FRONT_ENABLED: _INPUT_EDGE_FRONT,
        _INPUT_EDGE_BACK_ENABLED: _INPUT_EDGE_BACK,
        _INPUT_EDGE_LEFT_ENABLED: _INPUT_EDGE_LEFT,
        _INPUT_EDGE_RIGHT_ENABLED: _INPUT_EDGE_RIGHT,
    }
    for enabled_id, dropdown_id in mapping.items():
        enabled_item = _edge_enabled_input(inputs, enabled_id)
        dropdown = adsk.core.DropDownCommandInput.cast(inputs.itemById(dropdown_id))
        is_visible = section_visible and edge_mode == "individual"
        is_enabled = is_visible and has_front_face
        if enabled_item:
            enabled_item.isVisible = is_visible
            enabled_item.isEnabled = is_enabled
        if dropdown:
            dropdown.isVisible = is_visible
            dropdown.isEnabled = is_enabled and _is_edge_enabled(inputs, enabled_id)

    surface_all = adsk.core.StringValueCommandInput.cast(inputs.itemById(_INPUT_SURFACE_ALL_TEXT))
    if surface_all:
        surface_all.isVisible = False
        surface_all.isEnabled = False
    top_enabled = _edge_enabled_input(inputs, _INPUT_TOP_ENABLED)
    top_surface = adsk.core.DropDownCommandInput.cast(inputs.itemById(_INPUT_TOP_SURFACE))
    bottom_enabled = _edge_enabled_input(inputs, _INPUT_BOTTOM_ENABLED)
    bottom_surface = adsk.core.DropDownCommandInput.cast(inputs.itemById(_INPUT_BOTTOM_SURFACE))
    material_id = _read_material_dropdown_value(inputs, raise_on_unknown=False)
    entry = _material_by_id.get(material_id or "")
    supports_surface = bool(entry and entry.supports_surface)
    surface_visible = section_visible and edge_mode == "individual" and supports_surface
    if top_enabled:
        top_enabled.isVisible = surface_visible
        top_enabled.isEnabled = surface_visible
    if top_surface:
        top_surface.isVisible = surface_visible
        top_surface.isEnabled = surface_visible and _is_edge_enabled(inputs, _INPUT_TOP_ENABLED)
    if bottom_enabled:
        bottom_enabled.isVisible = surface_visible
        bottom_enabled.isEnabled = surface_visible
    if bottom_surface:
        bottom_surface.isVisible = surface_visible
        bottom_surface.isEnabled = surface_visible and _is_edge_enabled(inputs, _INPUT_BOTTOM_ENABLED)


def _set_filter_dropdown_value(inputs, type_id):
    dd = adsk.core.DropDownCommandInput.cast(inputs.itemById(_INPUT_FILTER_TYPE))
    if not dd:
        return
    wanted = _t("filter_all_types") if not type_id else _type_label(type_id)
    for i in range(dd.listItems.count):
        item = dd.listItems.item(i)
        if str(item.name or "").strip().lower() == wanted.lower():
            item.isSelected = True
            return
    if dd.listItems.count > 0:
        dd.listItems.item(0).isSelected = True


def _update_trim_allowance_visibility(inputs, material_id):
    trim_input = adsk.core.StringValueCommandInput.cast(inputs.itemById(_INPUT_TRIM_ALLOWANCE))
    if not trim_input:
        return
    entry = _material_by_id.get(material_id or "")
    trim_input.isVisible = bool(entry and entry.supports_trim_allowance)


def _populate_grain_direction_dropdown(dropdown, selected_value):
    if not dropdown:
        return
    dropdown.listItems.clear()
    options = [
        ("none", _t("grain_none")),
        ("length", _t("grain_length")),
        ("width", _t("grain_width")),
    ]
    wanted = str(selected_value or "none").strip().lower()
    if wanted not in ("none", "length", "width"):
        wanted = "none"
    for value, label in options:
        dropdown.listItems.add(label, value == wanted)


def _set_grain_direction_dropdown(inputs, value):
    dropdown = adsk.core.DropDownCommandInput.cast(inputs.itemById(_INPUT_GRAIN_DIRECTION))
    _populate_grain_direction_dropdown(dropdown, value)


def _read_grain_direction_dropdown(inputs):
    label = _read_dropdown_value(inputs, _INPUT_GRAIN_DIRECTION, "")
    mapping = {
        _t("grain_none").lower(): "none",
        _t("grain_length").lower(): "length",
        _t("grain_width").lower(): "width",
    }
    value = mapping.get(label.lower(), "none")
    if value not in ("none", "length", "width"):
        return "none"
    return value


def _update_grain_direction_visibility(inputs, material_id):
    dropdown = adsk.core.DropDownCommandInput.cast(inputs.itemById(_INPUT_GRAIN_DIRECTION))
    if not dropdown:
        return
    entry = _material_by_id.get(material_id or "")
    dropdown.isVisible = _material_requires_grain_direction(entry)


def _material_requires_grain_direction(entry):
    if not entry:
        return False
    if not entry.supports_grain:
        return False
    return str(entry.sheet_has_grain or "").strip().lower() == "yes"


def _validate_front_face_selection(inputs, body):
    front_face = _selected_or_restored_front_face(inputs, body)
    if not front_face:
        _clear_front_face_memory()
        return
    if not _face_belongs_to_body(front_face, body):
        _set_front_face_selection(inputs, None)
        _clear_front_face_memory()
        raise RuntimeError("Gewählte Vorderkantenfläche gehört nicht zum ausgewählten Body.")
    _remember_front_face_selection(body, front_face)


def _face_belongs_to_body(face, body):
    face_body = adsk.fusion.BRepBody.cast(getattr(face, "body", None))
    if not face_body:
        return False
    native_face_body = adsk.fusion.BRepBody.cast(getattr(face_body, "nativeObject", None))
    native_body = adsk.fusion.BRepBody.cast(getattr(body, "nativeObject", None))
    if face_body is body or face_body is native_body or native_face_body is body or native_face_body is native_body:
        return True
    face_tokens = {
        _get_entity_token(face_body) or "",
        _get_entity_token(native_face_body) or "",
    }
    body_tokens = {
        _get_entity_token(body) or "",
        _get_entity_token(native_body) or "",
    }
    face_tokens.discard("")
    body_tokens.discard("")
    return bool(face_tokens and body_tokens and (face_tokens & body_tokens))


def _ensure_front_face_from_attributes(inputs, body):
    if _selected_or_restored_front_face(inputs, body):
        return
    front_reference = str(_get_attr(body, ATTR_KEY_FRONT_REFERENCE, "") or "").strip().lower()
    key = _canonical_front_key_from_reference(front_reference)
    if not key:
        return
    if not _has_any_edge_attribute(body):
        return
    canonical_faces = _detect_canonical_side_faces(body)
    face = canonical_faces.get(key)
    _set_front_face_selection(inputs, face)
    if face:
        _remember_front_face_selection(body, face)


def _canonical_front_key_from_reference(front_reference):
    value = str(front_reference or "").strip().lower()
    if value in ("long_pos", "long_neg", "short_pos", "short_neg"):
        return value
    return ""


def _has_any_edge_attribute(body):
    for key in (ATTR_KEY_EDGE_FRONT, ATTR_KEY_EDGE_BACK, ATTR_KEY_EDGE_LEFT, ATTR_KEY_EDGE_RIGHT):
        if str(_get_attr(body, key, "") or "").strip():
            return True
    return False


def _sync_edge_controls_from_body_attributes(inputs, body):
    edge_values_by_attr = {
        ATTR_KEY_EDGE_FRONT: str(_get_attr(body, ATTR_KEY_EDGE_FRONT, "") or "").strip(),
        ATTR_KEY_EDGE_BACK: str(_get_attr(body, ATTR_KEY_EDGE_BACK, "") or "").strip(),
        ATTR_KEY_EDGE_LEFT: str(_get_attr(body, ATTR_KEY_EDGE_LEFT, "") or "").strip(),
        ATTR_KEY_EDGE_RIGHT: str(_get_attr(body, ATTR_KEY_EDGE_RIGHT, "") or "").strip(),
    }
    surface_top = str(_get_attr(body, ATTR_KEY_SURFACE_TOP, "") or "").strip()
    surface_bottom = str(_get_attr(body, ATTR_KEY_SURFACE_BOTTOM, "") or "").strip()

    edge_values = [
        edge_values_by_attr[ATTR_KEY_EDGE_FRONT],
        edge_values_by_attr[ATTR_KEY_EDGE_BACK],
        edge_values_by_attr[ATTR_KEY_EDGE_LEFT],
        edge_values_by_attr[ATTR_KEY_EDGE_RIGHT],
    ]
    edge_non_empty = [value for value in edge_values if value]
    edge_all_equal = len(edge_non_empty) == 4 and len(set(edge_values)) == 1

    surface_any = bool(surface_top or surface_bottom)
    any_edge_data = bool(edge_non_empty)
    any_surface_data = bool(surface_any)

    if not any_edge_data and not any_surface_data:
        mode = "none"
    elif any_edge_data:
        mode = "individual"
    elif surface_any:
        mode = "individual"
    else:
        mode = "none"

    _set_mode_dropdown(inputs, _INPUT_EDGE_MODE, mode)
    _set_edge_dropdown_value(inputs, _INPUT_EDGE_ALL, edge_values[0] if edge_all_equal else "")
    _set_input_value(inputs, _INPUT_SURFACE_ALL_TEXT, "")

    _set_edge_enabled(inputs, _INPUT_EDGE_FRONT_ENABLED, bool(edge_values_by_attr[ATTR_KEY_EDGE_FRONT]))
    _set_edge_enabled(inputs, _INPUT_EDGE_BACK_ENABLED, bool(edge_values_by_attr[ATTR_KEY_EDGE_BACK]))
    _set_edge_enabled(inputs, _INPUT_EDGE_LEFT_ENABLED, bool(edge_values_by_attr[ATTR_KEY_EDGE_LEFT]))
    _set_edge_enabled(inputs, _INPUT_EDGE_RIGHT_ENABLED, bool(edge_values_by_attr[ATTR_KEY_EDGE_RIGHT]))
    _set_edge_dropdown_value(inputs, _INPUT_EDGE_FRONT, edge_values_by_attr[ATTR_KEY_EDGE_FRONT])
    _set_edge_dropdown_value(inputs, _INPUT_EDGE_BACK, edge_values_by_attr[ATTR_KEY_EDGE_BACK])
    _set_edge_dropdown_value(inputs, _INPUT_EDGE_LEFT, edge_values_by_attr[ATTR_KEY_EDGE_LEFT])
    _set_edge_dropdown_value(inputs, _INPUT_EDGE_RIGHT, edge_values_by_attr[ATTR_KEY_EDGE_RIGHT])
    _set_edge_enabled(inputs, _INPUT_TOP_ENABLED, bool(surface_top))
    _set_edge_enabled(inputs, _INPUT_BOTTOM_ENABLED, bool(surface_bottom))


def _read_enabled_edge_values(inputs, require_material=False):
    mapping = {
        ATTR_KEY_EDGE_FRONT: (_INPUT_EDGE_FRONT_ENABLED, _INPUT_EDGE_FRONT),
        ATTR_KEY_EDGE_BACK: (_INPUT_EDGE_BACK_ENABLED, _INPUT_EDGE_BACK),
        ATTR_KEY_EDGE_LEFT: (_INPUT_EDGE_LEFT_ENABLED, _INPUT_EDGE_LEFT),
        ATTR_KEY_EDGE_RIGHT: (_INPUT_EDGE_RIGHT_ENABLED, _INPUT_EDGE_RIGHT),
    }
    values = {}
    for attr_key, (enabled_id, dropdown_id) in mapping.items():
        if not _is_edge_enabled(inputs, enabled_id):
            values[attr_key] = ""
            continue
        edge_id = _read_edge_dropdown_value(inputs, dropdown_id)
        if require_material and not edge_id:
            raise RuntimeError("Für aktivierte Bekantung muss ein Kantenmaterial gewählt werden.")
        values[attr_key] = edge_id
    return values


def _read_edge_values_for_mode(inputs, require_material=False):
    mode = _read_mode_dropdown(inputs, _INPUT_EDGE_MODE, "none")
    if mode == "none":
        return {
            ATTR_KEY_EDGE_FRONT: "",
            ATTR_KEY_EDGE_BACK: "",
            ATTR_KEY_EDGE_LEFT: "",
            ATTR_KEY_EDGE_RIGHT: "",
        }
    if mode == "all":
        return {
            ATTR_KEY_EDGE_FRONT: "",
            ATTR_KEY_EDGE_BACK: "",
            ATTR_KEY_EDGE_LEFT: "",
            ATTR_KEY_EDGE_RIGHT: "",
        }
    return _read_enabled_edge_values(inputs, require_material=require_material)


def _read_surface_values_for_mode(inputs):
    mode = _read_mode_dropdown(inputs, _INPUT_EDGE_MODE, "none")
    if mode != "individual":
        return {ATTR_KEY_SURFACE_TOP: "", ATTR_KEY_SURFACE_BOTTOM: ""}
    return {
        ATTR_KEY_SURFACE_TOP: (
            _read_surface_dropdown_value(inputs, _INPUT_TOP_SURFACE)
            if _is_edge_enabled(inputs, _INPUT_TOP_ENABLED)
            else ""
        ),
        ATTR_KEY_SURFACE_BOTTOM: (
            _read_surface_dropdown_value(inputs, _INPUT_BOTTOM_SURFACE)
            if _is_edge_enabled(inputs, _INPUT_BOTTOM_ENABLED)
            else ""
        ),
    }


def _apply_edge_appearance_preview(inputs):
    body = _read_selected_body(inputs)
    if not body:
        return
    try:
        side_faces, _front_ref = _resolve_side_faces_from_front_selection(inputs, body)
        if not side_faces:
            return
        _apply_edge_appearance_from_resolved_faces(body, side_faces, _read_edge_values_for_mode(inputs))
    except Exception as exc:
        print(f"Properties: Kanten-Preview fehlgeschlagen: {exc}")


def _apply_surface_appearance_preview(inputs):
    body = _read_selected_body(inputs)
    if not body:
        return
    try:
        _apply_surface_appearance_from_body_faces(body, _read_surface_values_for_mode(inputs))
    except Exception as exc:
        print(f"Properties: Oberflächen-Preview fehlgeschlagen: {exc}")


def _apply_edge_appearance_from_resolved_faces(body, side_faces, edge_values):
    attr_to_side = {
        ATTR_KEY_EDGE_FRONT: "front",
        ATTR_KEY_EDGE_BACK: "back",
        ATTR_KEY_EDGE_LEFT: "left",
        ATTR_KEY_EDGE_RIGHT: "right",
    }
    for attr_key, side in attr_to_side.items():
        edge_id = str(edge_values.get(attr_key, "") or "").strip()
        if not edge_id:
            continue
        face = side_faces.get(side)
        if not face:
            continue
        edge_entry = _edge_by_id.get(edge_id)
        if not edge_entry:
            raise RuntimeError(f"Kantenmaterial '{edge_id}' ist nicht im Katalog vorhanden.")
        appearance = _find_appearance_by_name(edge_entry.appearance_name)
        if not appearance:
            raise RuntimeError(
                f"Appearance '{edge_entry.appearance_name}' aus Kantenmaterial '{edge_id}' wurde nicht gefunden."
            )
        try:
            face.appearance = appearance
        except Exception as exc:
            raise RuntimeError(f"Kanten-Appearance konnte nicht gesetzt werden: {exc}") from exc


def _write_or_clear_body_attribute(body, attr_key, value):
    text = str(value or "").strip()
    if text:
        _write_body_attribute_or_raise(body, attr_key, text)
    else:
        _clear_body_attribute_or_raise(body, attr_key)


def _apply_surface_appearance_from_body_faces(body, surface_values):
    face_map = _detect_top_bottom_faces(body)
    mapping = {
        ATTR_KEY_SURFACE_TOP: "top",
        ATTR_KEY_SURFACE_BOTTOM: "bottom",
    }
    for attr_key, face_key in mapping.items():
        surface_id = str(surface_values.get(attr_key, "") or "").strip()
        if not surface_id:
            continue
        face = face_map.get(face_key)
        if not face:
            raise RuntimeError(f"Fläche für Oberfläche '{face_key}' konnte nicht bestimmt werden.")
        surface_entry = _surface_by_id.get(surface_id)
        if not surface_entry:
            raise RuntimeError(f"Oberfläche '{surface_id}' ist nicht im Katalog vorhanden.")
        appearance = _find_appearance_by_name(surface_entry.appearance_name)
        if not appearance:
            raise RuntimeError(
                f"Appearance '{surface_entry.appearance_name}' aus Oberfläche '{surface_id}' wurde nicht gefunden."
            )
        try:
            face.appearance = appearance
        except Exception as exc:
            raise RuntimeError(f"Oberflächen-Appearance konnte nicht gesetzt werden: {exc}") from exc


def _detect_top_bottom_faces(body):
    axis_info = _edge_axis_info(body)
    if not axis_info:
        return {}
    best = {}
    faces = getattr(body, "faces", None)
    if not faces:
        return best
    for i in range(faces.count):
        face = adsk.fusion.BRepFace.cast(faces.item(i))
        if not face:
            continue
        normal = _face_normal(face)
        dominant_idx, dominant_value = _dominant_axis(normal)
        if dominant_idx != axis_info["thickness_idx"] or abs(dominant_value) < 0.9:
            continue
        key = "top" if dominant_value >= 0 else "bottom"
        score = abs(dominant_value) + float(getattr(face, "area", 0.0))
        existing = best.get(key)
        if not existing or score > existing[0]:
            best[key] = (score, face)
    return {key: value[1] for key, value in best.items()}


def _resolve_side_faces_from_front_selection(inputs, body):
    front_face = _get_or_derive_front_face(inputs, body)
    if not front_face:
        return {}, ""
    if not _face_belongs_to_body(front_face, body):
        raise RuntimeError("Gewählte Vorderkantenfläche gehört nicht zum ausgewählten Body.")
    axis_info = _edge_axis_info(body)
    if not axis_info:
        raise RuntimeError("Bauteilachsen konnten nicht bestimmt werden.")
    front_key = _canonical_key_for_face(body, front_face, axis_info)
    if not front_key:
        raise RuntimeError("Vorderkantenfläche ist keine gültige Seitenfläche.")

    canonical_faces = _detect_canonical_side_faces(body)
    side_faces = {"front": front_face}
    back_key = _opposite_canonical_key(front_key)
    if back_key in canonical_faces:
        side_faces["back"] = canonical_faces[back_key]

    remaining = [key for key in canonical_faces.keys() if key not in (front_key, back_key)]
    if len(remaining) >= 2:
        front_vec = _axis_vector(*_canonical_key_axis_and_sign(front_key, axis_info))
        up_vec = _axis_vector(axis_info["thickness_idx"], 1)
        right_vec = _cross(up_vec, front_vec)
        scored = []
        for key in remaining:
            face = canonical_faces[key]
            normal = _face_normal(face)
            if normal is None:
                continue
            score = _dot((normal.x, normal.y, normal.z), right_vec)
            scored.append((score, face))
        if scored:
            scored.sort(key=lambda item: item[0])
            side_faces["left"] = scored[0][1]
            side_faces["right"] = scored[-1][1]
    return side_faces, front_key


def _detect_canonical_side_faces(body):
    axis_info = _edge_axis_info(body)
    if not axis_info:
        return {}
    best = {}
    faces = getattr(body, "faces", None)
    if not faces:
        return best
    for i in range(faces.count):
        face = adsk.fusion.BRepFace.cast(faces.item(i))
        if not face:
            continue
        key = _canonical_key_for_face(body, face, axis_info)
        if not key:
            continue
        score = abs(_dominant_axis(_face_normal(face))[1]) + float(getattr(face, "area", 0.0))
        existing = best.get(key)
        if not existing or score > existing[0]:
            best[key] = (score, face)
    return {key: value[1] for key, value in best.items()}


def _canonical_key_for_face(body, face, axis_info=None):
    axis_info = axis_info or _edge_axis_info(body)
    if not axis_info:
        return None
    normal = _face_normal(face)
    if normal is None:
        return None
    dominant_idx, dominant_value = _dominant_axis(normal)
    if dominant_idx is None or dominant_idx == axis_info["thickness_idx"]:
        return None
    if abs(dominant_value) < 0.9:
        return None
    if dominant_idx == axis_info["long_idx"]:
        return "long_pos" if dominant_value >= 0 else "long_neg"
    if dominant_idx == axis_info["short_idx"]:
        return "short_pos" if dominant_value >= 0 else "short_neg"
    return None


def _opposite_canonical_key(key):
    mapping = {
        "long_pos": "long_neg",
        "long_neg": "long_pos",
        "short_pos": "short_neg",
        "short_neg": "short_pos",
    }
    return mapping.get(key, "")


def _canonical_key_axis_and_sign(key, axis_info):
    if key.startswith("long_"):
        axis_idx = axis_info["long_idx"]
    else:
        axis_idx = axis_info["short_idx"]
    sign = 1 if key.endswith("_pos") else -1
    return axis_idx, sign


def _axis_vector(axis_idx, sign):
    vec = [0.0, 0.0, 0.0]
    if axis_idx is None or axis_idx < 0 or axis_idx > 2:
        return tuple(vec)
    vec[axis_idx] = 1.0 if sign >= 0 else -1.0
    return tuple(vec)


def _cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _dot(a, b):
    return (a[0] * b[0]) + (a[1] * b[1]) + (a[2] * b[2])


def _edge_axis_info(body):
    try:
        bbox = body.boundingBox
        if not bbox:
            return None
        dx = abs(bbox.maxPoint.x - bbox.minPoint.x)
        dy = abs(bbox.maxPoint.y - bbox.minPoint.y)
        dz = abs(bbox.maxPoint.z - bbox.minPoint.z)
        dims = [dx, dy, dz]
        order = sorted(range(3), key=lambda idx: dims[idx], reverse=True)
        if len(order) < 3:
            return None
        return {
            "long_idx": order[0],
            "short_idx": order[1],
            "thickness_idx": order[2],
        }
    except Exception:
        return None


def _face_normal(face):
    try:
        point = getattr(face, "pointOnFace", None)
        evaluator = getattr(face, "evaluator", None)
        if not point or not evaluator:
            return None
        ok, normal = evaluator.getNormalAtPoint(point)
        if not ok or not normal:
            return None
        return normal
    except Exception:
        return None


def _dominant_axis(vector):
    if vector is None:
        return None, 0.0
    try:
        components = [float(vector.x), float(vector.y), float(vector.z)]
    except Exception:
        return None, 0.0
    idx = max(range(3), key=lambda i: abs(components[i]))
    return idx, components[idx]


def _write_body_attribute_or_raise(body, key, value):
    ok, reason = _set_attr(body, key, value)
    if ok:
        return
    hint = ""
    if _is_body_likely_read_only(body):
        hint = " Der Body wirkt schreibgeschützt."
    raise RuntimeError(f"Attribut '{key}' konnte nicht gespeichert werden ({reason}).{hint}")


def _clear_body_attribute_or_raise(body, key):
    ok, reason = _clear_attr(body, key)
    if ok:
        return
    raise RuntimeError(f"Attribut '{key}' konnte nicht gelöscht werden ({reason}).")


def _resolve_attr_target(entity):
    if not entity:
        return None
    try:
        native = getattr(entity, "nativeObject", None)
        if native:
            return native
    except Exception:
        pass
    return entity


def _set_attr(entity, key, value):
    if not entity or not key:
        return False, "ungültige Eingabe"

    targets = []
    try:
        native = getattr(entity, "nativeObject", None)
        if native:
            targets.append(native)
    except Exception:
        pass
    targets.append(entity)

    last_error = "kein Zielobjekt"
    seen = set()
    for target in targets:
        if not target:
            continue
        marker = id(target)
        if marker in seen:
            continue
        seen.add(marker)
        try:
            attrs = getattr(target, "attributes", None)
            if attrs is None:
                last_error = "keine Attributes-Sammlung"
                continue
            attrs.add(ATTRIBUTE_GROUP, key, str(value))
            return True, ""
        except Exception as exc:
            last_error = str(exc)
            print(f"Properties: set_attr fehlgeschlagen ({key}) auf Target: {exc}")

    token = _get_entity_token(entity)
    if token:
        ok, reason = _set_design_level_attr(token, key, value)
        if ok:
            return True, ""
        last_error = reason
    return False, last_error


def _clear_attr(entity, key):
    if not entity or not key:
        return False, "ungültige Eingabe"

    targets = []
    try:
        native = getattr(entity, "nativeObject", None)
        if native:
            targets.append(native)
    except Exception:
        pass
    targets.append(entity)

    last_error = "kein Zielobjekt"
    seen = set()
    for target in targets:
        if not target:
            continue
        marker = id(target)
        if marker in seen:
            continue
        seen.add(marker)
        try:
            attrs = getattr(target, "attributes", None)
            if attrs is None:
                last_error = "keine Attributes-Sammlung"
                continue
            attr = attrs.itemByName(ATTRIBUTE_GROUP, key)
            if not attr:
                return True, ""
            attr.deleteMe()
            return True, ""
        except Exception as exc:
            last_error = str(exc)
            print(f"Properties: clear_attr fehlgeschlagen ({key}) auf Target: {exc}")

    token = _get_entity_token(entity)
    if token:
        ok, reason = _clear_design_level_attr(token, key)
        if ok:
            return True, ""
        last_error = reason
    return False, last_error


def _get_attr(entity, key, default=None):
    if not entity or not key:
        return default
    try:
        target = _resolve_attr_target(entity)
        attrs = getattr(target, "attributes", None)
        if attrs is None:
            token = _get_entity_token(entity)
            if token:
                return _get_design_level_attr(token, key, default)
            return default
        attr = attrs.itemByName(ATTRIBUTE_GROUP, key)
        if attr:
            return attr.value
        token = _get_entity_token(entity)
        if token:
            return _get_design_level_attr(token, key, default)
        return default
    except Exception:
        token = _get_entity_token(entity)
        if token:
            return _get_design_level_attr(token, key, default)
        return default


def _read_material_dropdown_value(inputs, raise_on_unknown):
    label = _read_dropdown_value(inputs, _INPUT_MATERIAL, "")
    none_label = _t("material_none")
    if not label or label.lower() == none_label.lower():
        return ""
    material_id = _material_label_to_id.get(label, "")
    if not material_id and raise_on_unknown:
        raise RuntimeError(f"Unbekannter Material-Dropdown-Wert: '{label}'")
    return material_id


def _read_filter_type(inputs):
    display = _read_dropdown_value(inputs, _INPUT_FILTER_TYPE, "").lower()
    if not display or display == _t("filter_all_types").lower():
        return None
    for type_id in get_catalog_types():
        if display == _type_label(type_id).lower():
            return type_id
    return None


def _parse_trim_allowance(raw_value):
    raw = str(raw_value or "").strip()
    if not raw:
        raise RuntimeError("Fräszulage fehlt.")
    # Strict input: complete string must be a number, optional with trailing "mm".
    # Examples: "0,5", "0.5", "0,5 mm", ".5mm"
    match = re.fullmatch(r"\s*([+-]?(?:\d+(?:[.,]\d+)?|[.,]\d+))\s*(mm)?\s*", raw, re.IGNORECASE)
    if not match:
        raise RuntimeError(f"Fräszulage hat ein ungültiges Format: '{raw_value}'")
    numeric = float(match.group(1).replace(",", "."))
    if numeric < 0:
        raise RuntimeError("Fräszulage muss >= 0 sein.")
    return numeric


def _format_trim_allowance(value):
    numeric = float(value)
    if abs(numeric - round(numeric)) < 1e-9:
        return str(int(round(numeric)))
    return f"{numeric:.3f}".rstrip("0").rstrip(".")


def _find_appearance_by_name(name):
    app = adsk.core.Application.get()
    if not app:
        raise RuntimeError("Fusion Application nicht verfügbar.")

    wanted = str(name or "").strip().lower()
    if not wanted:
        return None

    def _scan(appearances):
        if not appearances:
            return None
        for idx in range(appearances.count):
            candidate = appearances.item(idx)
            candidate_name = str(getattr(candidate, "name", "") or "").strip().lower()
            if candidate_name == wanted:
                return candidate
        return None

    design = adsk.fusion.Design.cast(app.activeProduct) if app else None
    found = _scan(getattr(design, "appearances", None) if design else None)
    if found:
        return found

    libraries = getattr(app, "materialLibraries", None)
    if not libraries:
        return None
    for li in range(libraries.count):
        library = libraries.item(li)
        found = _scan(getattr(library, "appearances", None))
        if found:
            return found
    return None


def _apply_material_appearance_or_raise(body, material_id):
    entry = _material_by_id.get(material_id)
    if not entry:
        raise RuntimeError(f"Material '{material_id}' ist nicht im Katalog vorhanden.")

    appearance = _find_appearance_by_name(entry.appearance_name)
    if not appearance:
        raise RuntimeError(
            f"Appearance '{entry.appearance_name}' aus Material '{material_id}' wurde in Fusion nicht gefunden."
        )

    target = _resolve_attr_target(body)
    if not target:
        raise RuntimeError("Body für Appearance-Zuweisung nicht verfügbar.")
    try:
        target.appearance = appearance
    except Exception as exc:
        raise RuntimeError(f"Appearance konnte nicht gesetzt werden: {exc}") from exc


def _read_selected_body(inputs):
    try:
        body_entity = _selection_entity_by_input_id(inputs, _INPUT_BODY)
        body = adsk.fusion.BRepBody.cast(body_entity)
        if not body:
            return _restore_body_selection_from_memory(inputs)

        native = adsk.fusion.BRepBody.cast(getattr(body, "nativeObject", None))
        resolved = native if native else body
        _remember_body_selection(resolved)
        return resolved
    except Exception as exc:
        print(f"Properties: Körperauswahl konnte nicht gelesen werden: {exc}")
    return None


def _is_body_likely_read_only(body):
    try:
        if getattr(body, "isReadOnly", False):
            return True
    except Exception:
        pass
    try:
        if getattr(body, "assemblyContext", None):
            native = getattr(body, "nativeObject", None)
            if native is None:
                return True
    except Exception:
        pass
    return False


def _get_entity_token(entity):
    try:
        token = getattr(entity, "entityToken", None)
        if token:
            return str(token)
    except Exception:
        pass
    return None


def _get_design_attrs_collection():
    try:
        app = adsk.core.Application.get()
        design = adsk.fusion.Design.cast(app.activeProduct) if app else None
        if not design:
            return None
        root = getattr(design, "rootComponent", None)
        if root:
            attrs = getattr(root, "attributes", None)
            if attrs is not None:
                return attrs
        return getattr(design, "attributes", None)
    except Exception:
        return None


def _build_design_attr_name(token, key):
    return f"body_token::{token}::{key}"


def _set_design_level_attr(token, key, value):
    attrs = _get_design_attrs_collection()
    if attrs is None:
        return False, "keine Design-Attributes"
    try:
        attrs.add(ATTRIBUTE_GROUP, _build_design_attr_name(token, key), str(value))
        return True, ""
    except Exception as exc:
        print(f"Properties: Design-Attr set fehlgeschlagen ({key}): {exc}")
        return False, str(exc)


def _get_design_level_attr(token, key, default=None):
    attrs = _get_design_attrs_collection()
    if not attrs:
        return default
    try:
        attr = attrs.itemByName(ATTRIBUTE_GROUP, _build_design_attr_name(token, key))
        return attr.value if attr else default
    except Exception:
        return default


def _clear_design_level_attr(token, key):
    attrs = _get_design_attrs_collection()
    if attrs is None:
        return False, "keine Design-Attributes"
    try:
        attr = attrs.itemByName(ATTRIBUTE_GROUP, _build_design_attr_name(token, key))
        if not attr:
            return True, ""
        attr.deleteMe()
        return True, ""
    except Exception as exc:
        return False, str(exc)


def _diagnose_attribute_context(body):
    parts = []
    try:
        body_type = body.objectType if body else "-"
        parts.append(f"BodyType={body_type}")
    except Exception:
        parts.append("BodyType=<Fehler>")

    try:
        body_attrs = getattr(body, "attributes", None)
        parts.append(f"BodyAttrs={'ja' if body_attrs is not None else 'nein'}")
    except Exception:
        parts.append("BodyAttrs=<Fehler>")

    try:
        native = getattr(body, "nativeObject", None) if body else None
        native_type = native.objectType if native else "-"
        parts.append(f"NativeType={native_type}")
        native_attrs = getattr(native, "attributes", None) if native else None
        parts.append(f"NativeAttrs={'ja' if native_attrs is not None else 'nein'}")
    except Exception:
        parts.append("NativeAttrs=<Fehler>")

    try:
        app = adsk.core.Application.get()
        design = adsk.fusion.Design.cast(app.activeProduct) if app else None
        root = getattr(design, "rootComponent", None) if design else None
        root_attrs = getattr(root, "attributes", None) if root else None
        parts.append(f"RootAttrs={'ja' if root_attrs is not None else 'nein'}")
    except Exception:
        parts.append("RootAttrs=<Fehler>")

    return ", ".join(parts)


def _read_string_input(inputs, input_id, fallback):
    try:
        string_item = adsk.core.StringValueCommandInput.cast(inputs.itemById(input_id))
        if string_item:
            value = (string_item.value or "").strip()
            return value if value else fallback

        text_item = adsk.core.TextBoxCommandInput.cast(inputs.itemById(input_id))
        if not text_item:
            return fallback
        value = (text_item.text or "").strip()
        return value if value else fallback
    except Exception:
        return fallback


def _set_input_value(inputs, input_id, value):
    try:
        string_item = adsk.core.StringValueCommandInput.cast(inputs.itemById(input_id))
        if string_item:
            string_item.value = str(value if value is not None else "")
            return
        text_item = adsk.core.TextBoxCommandInput.cast(inputs.itemById(input_id))
        if text_item:
            text_item.text = str(value if value is not None else "")
    except Exception as exc:
        print(f"Properties: Input '{input_id}' konnte nicht gesetzt werden: {exc}")


def _read_dropdown_value(inputs, input_id, fallback):
    try:
        dd = adsk.core.DropDownCommandInput.cast(inputs.itemById(input_id))
        if not dd or not dd.selectedItem:
            return fallback
        value = (dd.selectedItem.name or "").strip()
        return value if value else fallback
    except Exception:
        return fallback


def _format_body_size(body):
    try:
        bbox = body.boundingBox
        if not bbox:
            return "-"
        dx = abs(bbox.maxPoint.x - bbox.minPoint.x)
        dy = abs(bbox.maxPoint.y - bbox.minPoint.y)
        dz = abs(bbox.maxPoint.z - bbox.minPoint.z)
        dims_mm = sorted([dx * 10.0, dy * 10.0, dz * 10.0], reverse=True)
        return f"{dims_mm[0]:.1f} x {dims_mm[1]:.1f} x {dims_mm[2]:.1f} mm"
    except Exception as exc:
        print(f"Properties: Größe konnte nicht berechnet werden: {exc}")
        return "-"


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


def _type_label(type_id):
    return get_type_label(type_id, _ui_lang)


def _sorted_types():
    type_ids = [
        type_id
        for type_id in get_catalog_types()
        if get_type_capabilities(type_id).get("supports_body_material", True)
    ]
    return sorted(type_ids, key=lambda type_id: _type_label(type_id).lower())


def _get_or_create_panel(workspace):
    global _active_panel_id

    primary = workspace.toolbarPanels.itemById(PRIMARY_PANEL_ID)
    if primary:
        _active_panel_id = PRIMARY_PANEL_ID
        return primary

    for panel_id in PANEL_IDS:
        candidate = workspace.toolbarPanels.itemById(panel_id)
        if candidate:
            _active_panel_id = panel_id
            return candidate

    tab = workspace.toolbarTabs.itemById(CUSTOM_TAB_ID)
    if not tab:
        return None

    panel = tab.toolbarPanels.itemById(CUSTOM_PANEL_ID)
    if panel:
        _active_panel_id = CUSTOM_PANEL_ID
        return panel

    panel = tab.toolbarPanels.add(CUSTOM_PANEL_ID, CUSTOM_PANEL_NAME, "", False)
    _active_panel_id = CUSTOM_PANEL_ID
    return panel


def start():
    global _command_created_handler, _is_started
    if _is_started:
        return

    app = adsk.core.Application.get()
    ui = app.userInterface
    cmd_def = ui.commandDefinitions.itemById(COMMAND_ID)
    if not cmd_def:
        cmd_def = ui.commandDefinitions.addButtonDefinition(
            COMMAND_ID, COMMAND_NAME, COMMAND_TOOLTIP, COMMAND_RESOURCES
        )

    _command_created_handler = _CommandCreatedHandler()
    cmd_def.commandCreated.add(_command_created_handler)
    _handlers.append(_command_created_handler)

    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    if not workspace:
        ui.messageBox("Properties: Workspace nicht gefunden.")
        return

    panel = _get_or_create_panel(workspace)
    if not panel:
        ui.messageBox("Properties: Panel 'Ändern' konnte nicht aufgelöst werden.")
        return

    control = panel.controls.itemById(COMMAND_ID)
    if not control:
        control = panel.controls.addCommand(cmd_def)
    if control:
        try:
            control.isPromotedByDefault = True
            control.isPromoted = True
            control.isVisible = True
        except Exception:
            pass

    _is_started = True
    print(f"Properties: Command registriert in Panel '{_active_panel_id}'.")


def stop():
    global _command_created_handler, _is_started, _active_panel_id
    app = adsk.core.Application.get()
    ui = app.userInterface

    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    if workspace and _active_panel_id:
        panel = workspace.toolbarPanels.itemById(_active_panel_id)
        if panel:
            control = panel.controls.itemById(COMMAND_ID)
            if control:
                control.deleteMe()

    cmd_def = ui.commandDefinitions.itemById(COMMAND_ID)
    if cmd_def and _command_created_handler:
        try:
            cmd_def.commandCreated.remove(_command_created_handler)
        except Exception:
            pass
        _command_created_handler = None
    if cmd_def:
        cmd_def.deleteMe()

    _handlers.clear()
    _is_started = False
    _active_panel_id = None
