import os
import re
import sys

import adsk.core
import adsk.fusion

from shared.catalog import get_catalog_types

_COMMANDS_DIR = os.path.dirname(os.path.abspath(__file__))
if _COMMANDS_DIR not in sys.path:
    sys.path.insert(0, _COMMANDS_DIR)

try:
    from .appearances import (
        AppearanceApplier,
        _apply_material_appearance_or_raise,
    )
    from .attributes import (
        _clear_body_attribute_or_raise,
        _diagnose_attribute_context,
        _get_attr,
        _get_entity_token,
        _is_body_likely_read_only,
        _is_truthy_attr,
        _write_body_attribute_or_raise,
    )
    from .catalog_entries import load_catalog_entries
    from .constants import *
    from .edge_surface_model import EdgeSurfaceValueModel, has_any_surface_value
    from .geometry import (
        _axis_vector,
        _canonical_key_axis_and_sign,
        _canonical_key_for_face,
        _cross,
        _detect_canonical_side_faces,
        _dot,
        _edge_axis_info,
        _face_belongs_to_body,
        _face_normal,
        _format_body_size,
        _opposite_canonical_key,
    )
    from .ui_state import UiStateController
    from .input_helpers import (
        _read_bool_input,
        _read_dropdown_value,
        _read_string_input,
        _set_bool_input_value,
        _set_input_value,
    )
    from .localization import _detect_ui_lang, _set_ui_lang, _sorted_types, _t, _type_label
except ImportError:
    from appearances import (
        AppearanceApplier,
        _apply_material_appearance_or_raise,
    )
    from attributes import (
        _clear_body_attribute_or_raise,
        _diagnose_attribute_context,
        _get_attr,
        _get_entity_token,
        _is_body_likely_read_only,
        _is_truthy_attr,
        _write_body_attribute_or_raise,
    )
    from catalog_entries import load_catalog_entries
    from constants import *
    from edge_surface_model import EdgeSurfaceValueModel, has_any_surface_value
    from geometry import (
        _axis_vector,
        _canonical_key_axis_and_sign,
        _canonical_key_for_face,
        _cross,
        _detect_canonical_side_faces,
        _dot,
        _edge_axis_info,
        _face_belongs_to_body,
        _face_normal,
        _format_body_size,
        _opposite_canonical_key,
    )
    from ui_state import UiStateController
    from input_helpers import (
        _read_bool_input,
        _read_dropdown_value,
        _read_string_input,
        _set_bool_input_value,
        _set_input_value,
    )
    from localization import _detect_ui_lang, _set_ui_lang, _sorted_types, _t, _type_label

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
_body_ref = None
_body_selection_ref = None
_front_face_token = ""
_front_body_token = ""
class _CommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def notify(self, args):
        _set_ui_lang(_detect_ui_lang())
        _clear_body_selection_memory()
        _clear_front_face_memory()

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
        edges_enabled = inputs.addBoolValueInput(_INPUT_EDGES_ENABLED, _t("edges_enabled"), True, "", False)
        edges_enabled.isVisible = False

        edges_header = inputs.addTextBoxCommandInput(_INPUT_EDGES_HEADER, "", _t("edges_section"), 1, True)
        edges_header.isFullWidth = True

        edge_mode = inputs.addDropDownCommandInput(
            _INPUT_EDGE_MODE, _t("mode"), adsk.core.DropDownStyles.TextListDropDownStyle
        )
        _populate_mode_dropdown(edge_mode, "individual")
        front_face = inputs.addSelectionInput(_INPUT_FRONT_FACE, _t("front_face"), _t("face_prompt"))
        front_face.addSelectionFilter("PlanarFaces")
        front_face.setSelectionLimits(0, 1)
        try:
            front_face.isUseCurrentSelections = False
        except Exception:
            pass
        edge_all = inputs.addDropDownCommandInput(
            _INPUT_EDGE_ALL, _t("edge_all"), adsk.core.DropDownStyles.TextListDropDownStyle
        )
        all_surface = inputs.addDropDownCommandInput(
            _INPUT_ALL_SURFACE, _t("surface_all"), adsk.core.DropDownStyles.TextListDropDownStyle
        )
        all_surface_text = inputs.addStringValueInput(_INPUT_ALL_SURFACE_TEXT, _t("custom_text_value"), "")

        edge_front_enabled = inputs.addBoolValueInput(
            _INPUT_EDGE_FRONT_ENABLED, _t("edge_front_enabled"), True, "", False
        )
        edge_front = inputs.addDropDownCommandInput(
            _INPUT_EDGE_FRONT, _t("edge_front"), adsk.core.DropDownStyles.TextListDropDownStyle
        )
        edge_front_text = inputs.addStringValueInput(_INPUT_EDGE_FRONT_TEXT, _t("custom_text_value"), "")
        edge_back_enabled = inputs.addBoolValueInput(
            _INPUT_EDGE_BACK_ENABLED, _t("edge_back_enabled"), True, "", False
        )
        edge_back = inputs.addDropDownCommandInput(
            _INPUT_EDGE_BACK, _t("edge_back"), adsk.core.DropDownStyles.TextListDropDownStyle
        )
        edge_back_text = inputs.addStringValueInput(_INPUT_EDGE_BACK_TEXT, _t("custom_text_value"), "")
        edge_left_enabled = inputs.addBoolValueInput(
            _INPUT_EDGE_LEFT_ENABLED, _t("edge_left_enabled"), True, "", False
        )
        edge_left = inputs.addDropDownCommandInput(
            _INPUT_EDGE_LEFT, _t("edge_left"), adsk.core.DropDownStyles.TextListDropDownStyle
        )
        edge_left_text = inputs.addStringValueInput(_INPUT_EDGE_LEFT_TEXT, _t("custom_text_value"), "")
        edge_right_enabled = inputs.addBoolValueInput(
            _INPUT_EDGE_RIGHT_ENABLED, _t("edge_right_enabled"), True, "", False
        )
        edge_right = inputs.addDropDownCommandInput(
            _INPUT_EDGE_RIGHT, _t("edge_right"), adsk.core.DropDownStyles.TextListDropDownStyle
        )
        edge_right_text = inputs.addStringValueInput(_INPUT_EDGE_RIGHT_TEXT, _t("custom_text_value"), "")
        swap_left_right = inputs.addBoolValueInput(_INPUT_SWAP_LEFT_RIGHT, _t("swap_left_right"), False, "", False)
        top_enabled = inputs.addBoolValueInput(_INPUT_TOP_ENABLED, _t("top_enabled"), True, "", False)
        surface_all_text = inputs.addStringValueInput(_INPUT_SURFACE_ALL_TEXT, _t("surface_all_text"), "")
        top_surface = inputs.addDropDownCommandInput(
            _INPUT_TOP_SURFACE, _t("top_text"), adsk.core.DropDownStyles.TextListDropDownStyle
        )
        top_surface_text = inputs.addStringValueInput(_INPUT_TOP_SURFACE_TEXT, _t("custom_text_value"), "")
        bottom_enabled = inputs.addBoolValueInput(_INPUT_BOTTOM_ENABLED, _t("bottom_enabled"), True, "", False)
        bottom_surface = inputs.addDropDownCommandInput(
            _INPUT_BOTTOM_SURFACE, _t("bottom_text"), adsk.core.DropDownStyles.TextListDropDownStyle
        )
        bottom_surface_text = inputs.addStringValueInput(_INPUT_BOTTOM_SURFACE_TEXT, _t("custom_text_value"), "")
        swap_surfaces = inputs.addBoolValueInput(_INPUT_SWAP_SURFACES, _t("swap_surfaces"), False, "", False)
        exclude_from_export = inputs.addBoolValueInput(
            _INPUT_EXCLUDE_FROM_EXPORT, _t("exclude_from_export"), True, "", False
        )
        notes_header = inputs.addTextBoxCommandInput(_INPUT_NOTES_HEADER, "", _t("notes_section"), 1, True)
        notes_header.isFullWidth = True
        notes = inputs.addTextBoxCommandInput(_INPUT_NOTES, _t("notes"), "", 4, False)
        notes.isFullWidth = True
        apply_button = inputs.addBoolValueInput(_INPUT_APPLY, _t("apply"), False, "", False)
        apply_button.isVisible = False
        _populate_edge_dropdown(edge_all, None)
        _populate_edge_dropdown(edge_front, None)
        _populate_edge_dropdown(edge_back, None)
        _populate_edge_dropdown(edge_left, None)
        _populate_edge_dropdown(edge_right, None)
        _populate_surface_dropdown(all_surface, None)
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

        on_destroy = _CommandDestroyHandler()
        cmd.destroy.add(on_destroy)
        _handlers.append(on_destroy)


class _CommandDestroyHandler(adsk.core.CommandEventHandler):
    def notify(self, args):
        _clear_body_selection_memory()
        _clear_front_face_memory()


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
                if not _selected_body_from_input(inputs):
                    _clear_body_selection_memory()
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

            if changed.id == _INPUT_EDGES_ENABLED:
                _update_edge_surface_ui(inputs, restore_front_face=False)
                return

            if changed.id == _INPUT_FRONT_FACE:
                body = _read_selected_body(inputs)
                if not body:
                    _set_front_face_selection(inputs, None)
                    _clear_front_face_memory()
                    _set_edge_controls_visible(inputs, False)
                    return
                _validate_front_face_selection(inputs, body)
                _sync_edge_controls_from_body_attributes(
                    inputs, body, preserve_current_mode=True, preserve_edges_enabled=True
                )
                _set_edge_dropdown_enabled_state(inputs)
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
                return

            if changed.id == _INPUT_SWAP_SURFACES:
                _swap_surface_inputs(inputs)
                _update_edge_surface_ui(inputs)
                return

            if changed.id == _INPUT_SWAP_LEFT_RIGHT:
                _swap_left_right_edge_inputs(inputs)
                _update_edge_surface_ui(inputs)
                return

            if changed.id == _INPUT_EDGE_MODE:
                _update_edge_surface_ui(inputs)
                return

            if changed.id == _INPUT_ALL_SURFACE:
                _update_edge_surface_ui(inputs)
                return

            if changed.id in (_INPUT_EDGE_ALL, _INPUT_EDGE_FRONT, _INPUT_EDGE_BACK, _INPUT_EDGE_LEFT, _INPUT_EDGE_RIGHT):
                _update_edge_surface_ui(inputs)
                return
            if changed.id in (_INPUT_TOP_SURFACE, _INPUT_BOTTOM_SURFACE):
                _update_edge_surface_ui(inputs)
                return
            if changed.id == _INPUT_APPLY:
                _handle_apply_button(inputs)
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
            _save_properties_from_inputs(inputs, ui)
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


def _handle_apply_button(inputs):
    app = adsk.core.Application.get()
    ui = app.userInterface if app else None
    apply_input = adsk.core.BoolValueCommandInput.cast(inputs.itemById(_INPUT_APPLY))
    if apply_input:
        apply_input.value = False
    if not ui:
        print("Properties: App/UI nicht verfügbar.")
        return
    try:
        body = _save_properties_from_inputs(inputs, ui)
        if body:
            _set_body_selection(inputs, body)
            _refresh_inputs_from_selected_body(inputs)
    except Exception as exc:
        print(f"Properties: Anwenden-Fehler: {exc}")
        ui.messageBox(f"Anwenden fehlgeschlagen:\n{exc}")


def _save_properties_from_inputs(inputs, ui):
    body = _read_selected_body(inputs)
    if not body:
        ui.messageBox(f"Bitte im Dialog einen {_t('body').lower()} auswählen.")
        return None

    material_id = _read_material_dropdown_value(inputs, raise_on_unknown=True)
    if not material_id:
        ui.messageBox(f"Bitte ein {_t('material').lower()} auswählen.")
        return None
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

    edge_model = _edge_surface_model(inputs)
    edge_section_enabled = _is_edges_enabled(inputs)
    edge_mode = _read_mode_dropdown(inputs, _INPUT_EDGE_MODE, "none") if edge_section_enabled else "none"
    surface_values = {ATTR_KEY_SURFACE_TOP: "", ATTR_KEY_SURFACE_BOTTOM: ""}

    if entry.supports_surface and edge_section_enabled:
        surface_values = edge_model.read_surface_values_for_mode()
        edge_model.validate_custom_text_values(surface_values)
        _write_or_clear_body_attribute(body, ATTR_KEY_SURFACE_TOP, surface_values.get(ATTR_KEY_SURFACE_TOP, ""))
        _write_or_clear_body_attribute(body, ATTR_KEY_SURFACE_BOTTOM, surface_values.get(ATTR_KEY_SURFACE_BOTTOM, ""))
        edge_model.write_custom_text_attributes(body, surface_values)
    else:
        _clear_body_attribute_or_raise(body, ATTR_KEY_SURFACE_TOP)
        _clear_body_attribute_or_raise(body, ATTR_KEY_SURFACE_BOTTOM)
        _clear_body_attribute_or_raise(body, ATTR_KEY_SURFACE_TOP_CUSTOM_TEXT)
        _clear_body_attribute_or_raise(body, ATTR_KEY_SURFACE_BOTTOM_CUSTOM_TEXT)

    notes = _read_string_input(inputs, _INPUT_NOTES, "").strip()
    _write_or_clear_body_attribute(body, ATTR_KEY_NOTES, notes)
    _write_body_attribute_or_raise(
        body,
        ATTR_KEY_EXCLUDE_FROM_EXPORT,
        "true" if _read_bool_input(inputs, _INPUT_EXCLUDE_FROM_EXPORT, False) else "false",
    )

    side_faces = None
    edge_values = (
        edge_model.read_edge_values_for_mode(require_material=True) if entry.supports_edges and edge_section_enabled else {}
    )
    edge_model.validate_custom_text_values(edge_values)
    has_edge_values = any(str(value or "").strip() for value in edge_values.values())
    if entry.supports_edges and edge_mode == "all":
        _clear_body_attribute_or_raise(body, ATTR_KEY_FRONT_REFERENCE)
        edge_model.write_all_mode_edge_attributes(body)
    elif entry.supports_edges and edge_mode == "individual" and has_edge_values:
        side_faces, front_reference = _resolve_side_faces_from_front_selection(inputs, body)
        if not side_faces:
            raise RuntimeError("Für aktivierte Bekantung bitte zuerst eine Vorderkante auswählen.")
        _write_body_attribute_or_raise(body, ATTR_KEY_FRONT_REFERENCE, front_reference)
        for attr_key, edge_id in edge_values.items():
            if edge_id:
                _write_body_attribute_or_raise(body, attr_key, edge_id)
            else:
                _clear_body_attribute_or_raise(body, attr_key)
        edge_model.write_custom_text_attributes(body, edge_values)
    else:
        _clear_body_attribute_or_raise(body, ATTR_KEY_FRONT_REFERENCE)
        _clear_body_attribute_or_raise(body, ATTR_KEY_EDGE_FRONT)
        _clear_body_attribute_or_raise(body, ATTR_KEY_EDGE_BACK)
        _clear_body_attribute_or_raise(body, ATTR_KEY_EDGE_LEFT)
        _clear_body_attribute_or_raise(body, ATTR_KEY_EDGE_RIGHT)
        _clear_body_attribute_or_raise(body, ATTR_KEY_EDGE_FRONT_CUSTOM_TEXT)
        _clear_body_attribute_or_raise(body, ATTR_KEY_EDGE_BACK_CUSTOM_TEXT)
        _clear_body_attribute_or_raise(body, ATTR_KEY_EDGE_LEFT_CUSTOM_TEXT)
        _clear_body_attribute_or_raise(body, ATTR_KEY_EDGE_RIGHT_CUSTOM_TEXT)

    if material_id != old_material_id:
        _apply_material_appearance_or_raise(body, material_id, _material_by_id)

    if entry.supports_edges and edge_mode == "individual" and side_faces:
        _appearance_applier().apply_edge_appearance_from_resolved_faces(body, side_faces, edge_values)
    elif entry.supports_edges and (edge_mode == "individual" or not edge_section_enabled):
        _appearance_applier().reset_canonical_side_face_appearances(body)
    if entry.supports_surface and entry.supports_edges:
        _appearance_applier().apply_surface_appearance_from_body_faces(
            body,
            surface_values,
            include_edges=entry.supports_edges and edge_mode == "all",
            allow_missing_empty_faces=not has_any_surface_value(surface_values),
        )
    elif entry.supports_surface:
        _appearance_applier().apply_global_surface_appearance_to_body_faces(body, surface_values)

    if _is_body_likely_read_only(body):
        diag = _diagnose_attribute_context(body)
        ui.messageBox(
            "Eigenschaften gespeichert, aber der Body wirkt schreibgeschützt.\n"
            "Bitte Ergebnis prüfen.\n\nDiagnose:\n"
            f"{diag}"
        )
        return body

    print(f"Properties gespeichert für Body: {body.name}")
    return body


def _load_material_entries():
    global _material_entries, _material_by_id, _edge_entries, _edge_by_id, _surface_entries, _surface_by_id
    _material_entries, _edge_entries, _surface_entries = load_catalog_entries(_type_label)
    _material_by_id = {entry.id: entry for entry in _material_entries}
    _edge_by_id = {entry.id: entry for entry in _edge_entries}
    _surface_by_id = {entry.id: entry for entry in _surface_entries}

def _edge_surface_model(inputs):
    return EdgeSurfaceValueModel(
        inputs,
        _read_mode_dropdown,
        _read_edge_dropdown_value,
        _read_surface_dropdown_value,
        _read_string_input,
        _write_body_attribute_or_raise,
        _clear_body_attribute_or_raise,
        _surface_by_id,
    )

def _ui_state(inputs):
    return UiStateController(
        inputs,
        _material_by_id,
        _read_selected_body,
        _read_material_dropdown_value,
        _read_mode_dropdown,
        _set_mode_dropdown,
        _read_surface_dropdown_value,
        _read_edge_dropdown_value,
        _selected_front_face,
        _selected_or_restored_front_face,
        _restore_body_selection_from_memory,
        _set_input_value,
    )

def _appearance_applier():
    return AppearanceApplier(_material_by_id, _edge_by_id, _surface_by_id, _get_attr)





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
        _set_edges_enabled_visible(inputs, False)
        _set_edges_enabled_value(inputs, False)
        _set_front_face_selection(inputs, None)
        _set_mode_dropdown(inputs, _INPUT_EDGE_MODE, "none")
        _set_edge_dropdown_value(inputs, _INPUT_EDGE_ALL, "")
        _set_surface_dropdown_value(inputs, _INPUT_ALL_SURFACE, "")
        _set_input_value(inputs, _INPUT_SURFACE_ALL_TEXT, "")
        _set_edge_enabled(inputs, _INPUT_TOP_ENABLED, False)
        _set_edge_enabled(inputs, _INPUT_BOTTOM_ENABLED, False)
        _set_surface_dropdown_value(inputs, _INPUT_TOP_SURFACE, "")
        _set_surface_dropdown_value(inputs, _INPUT_BOTTOM_SURFACE, "")
        _clear_custom_text_inputs(inputs)
        _set_input_value(inputs, _INPUT_NOTES, "")
        _set_bool_input_value(inputs, _INPUT_EXCLUDE_FROM_EXPORT, False)
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
    _set_edges_enabled_visible(inputs, bool(entry and (entry.supports_edges or entry.supports_surface)))
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
    _set_surface_dropdown_value(inputs, _INPUT_ALL_SURFACE, "")
    _set_input_value(inputs, _INPUT_ALL_SURFACE_TEXT, "")
    _set_surface_dropdown_value(inputs, _INPUT_TOP_SURFACE, str(_get_attr(body, ATTR_KEY_SURFACE_TOP, "") or "").strip())
    _set_surface_dropdown_value(
        inputs, _INPUT_BOTTOM_SURFACE, str(_get_attr(body, ATTR_KEY_SURFACE_BOTTOM, "") or "").strip()
    )
    _set_input_value(inputs, _INPUT_TOP_SURFACE_TEXT, str(_get_attr(body, ATTR_KEY_SURFACE_TOP_CUSTOM_TEXT, "") or "").strip())
    _set_input_value(
        inputs,
        _INPUT_BOTTOM_SURFACE_TEXT,
        str(_get_attr(body, ATTR_KEY_SURFACE_BOTTOM_CUSTOM_TEXT, "") or "").strip(),
    )
    _set_input_value(inputs, _INPUT_NOTES, str(_get_attr(body, ATTR_KEY_NOTES, "") or "").strip())
    _set_bool_input_value(inputs, _INPUT_EXCLUDE_FROM_EXPORT, _is_truthy_attr(_get_attr(body, ATTR_KEY_EXCLUDE_FROM_EXPORT, "")))
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
    _ui_state(inputs).set_main_controls_visible(visible)


def _set_edge_controls_visible(inputs, visible):
    _ui_state(inputs).set_edge_controls_visible(visible)


def _set_notes_controls_visible(inputs, visible):
    _ui_state(inputs).set_notes_controls_visible(visible)


def _edges_enabled_input(inputs):
    return _ui_state(inputs).edges_enabled_input()


def _is_edges_enabled(inputs):
    return _ui_state(inputs).is_edges_enabled()


def _set_edges_enabled_value(inputs, enabled):
    _ui_state(inputs).set_edges_enabled_value(enabled)


def _set_edges_enabled_visible(inputs, visible):
    _ui_state(inputs).set_edges_enabled_visible(visible)


def _render_edge_surface_ui(inputs, restore_front_face=True):
    _ui_state(inputs).render_edge_surface_ui(restore_front_face=restore_front_face)


def _update_edge_surface_ui(inputs, restore_front_face=True):
    _ui_state(inputs).update_edge_surface_ui(restore_front_face=restore_front_face)


def _clear_custom_text_inputs(inputs):
    _ui_state(inputs).clear_custom_text_inputs()


def _set_edge_controls_for_material(inputs, material_id):
    _ui_state(inputs).set_edge_controls_for_material(material_id)


def _selected_body_from_input(inputs):
    entity = _selection_entity_by_input_id(inputs, _INPUT_BODY)
    body = adsk.fusion.BRepBody.cast(entity)
    if not body:
        return None
    native = adsk.fusion.BRepBody.cast(getattr(body, "nativeObject", None))
    return native if native else body


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
    global _body_token, _body_ref, _body_selection_ref
    _body_token = ""
    _body_ref = None
    _body_selection_ref = None


def _remember_body_selection(body, selection_entity=None):
    global _body_token, _body_ref, _body_selection_ref
    _body_token = _get_entity_token(body) or ""
    _body_ref = body
    _body_selection_ref = selection_entity or body


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
    if _body_ref:
        _set_body_selection(inputs, _body_selection_ref or _body_ref)
        return _body_ref
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
    text_label = _t("custom_text")
    _edge_label_to_id[text_label] = CUSTOM_TEXT_VALUE
    dropdown.listItems.add(text_label, selected_edge_id == CUSTOM_TEXT_VALUE)
    if selected_edge_id == CUSTOM_TEXT_VALUE:
        selected_found = True
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
    text_label = _t("custom_text")
    _surface_label_to_id[text_label] = CUSTOM_TEXT_VALUE
    dropdown.listItems.add(text_label, selected_surface_id == CUSTOM_TEXT_VALUE)
    if selected_surface_id == CUSTOM_TEXT_VALUE:
        selected_found = True
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


def _swap_surface_inputs(inputs):
    top_value = _read_surface_dropdown_value(inputs, _INPUT_TOP_SURFACE)
    bottom_value = _read_surface_dropdown_value(inputs, _INPUT_BOTTOM_SURFACE)
    top_text = _read_string_input(inputs, _INPUT_TOP_SURFACE_TEXT, "")
    bottom_text = _read_string_input(inputs, _INPUT_BOTTOM_SURFACE_TEXT, "")
    _set_surface_dropdown_value(inputs, _INPUT_TOP_SURFACE, bottom_value)
    _set_surface_dropdown_value(inputs, _INPUT_BOTTOM_SURFACE, top_value)
    _set_input_value(inputs, _INPUT_TOP_SURFACE_TEXT, bottom_text)
    _set_input_value(inputs, _INPUT_BOTTOM_SURFACE_TEXT, top_text)


def _swap_left_right_edge_inputs(inputs):
    left_value = _read_edge_dropdown_value(inputs, _INPUT_EDGE_LEFT)
    right_value = _read_edge_dropdown_value(inputs, _INPUT_EDGE_RIGHT)
    left_text = _read_string_input(inputs, _INPUT_EDGE_LEFT_TEXT, "")
    right_text = _read_string_input(inputs, _INPUT_EDGE_RIGHT_TEXT, "")
    _set_edge_dropdown_value(inputs, _INPUT_EDGE_LEFT, right_value)
    _set_edge_dropdown_value(inputs, _INPUT_EDGE_RIGHT, left_value)
    _set_input_value(inputs, _INPUT_EDGE_LEFT_TEXT, right_text)
    _set_input_value(inputs, _INPUT_EDGE_RIGHT_TEXT, left_text)


def _read_surface_dropdown_value(inputs, input_id):
    label = _read_dropdown_value(inputs, input_id, "")
    none_label = _t("surface_none")
    if not label or label.lower() == none_label.lower():
        return ""
    surface_id = _surface_label_to_id.get(label, "")
    if not surface_id:
        raise RuntimeError(f"Unbekannter Oberflächen-Dropdown-Wert: '{label}'")
    if surface_id and surface_id not in _surface_by_id:
        if surface_id == CUSTOM_TEXT_VALUE:
            return surface_id
        raise RuntimeError(f"Oberfläche '{surface_id}' ist nicht im Katalog vorhanden.")
    return surface_id


def _edge_enabled_input(inputs, enabled_input_id):
    return _ui_state(inputs).edge_enabled_input(enabled_input_id)


def _set_edge_enabled(inputs, enabled_input_id, enabled):
    _ui_state(inputs).set_edge_enabled(enabled_input_id, enabled)


def _set_edge_dropdown_enabled_state(inputs, restore_front_face=True):
    _ui_state(inputs).set_edge_dropdown_enabled_state(restore_front_face=restore_front_face)


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


def _sync_edge_controls_from_body_attributes(
    inputs, body, preserve_current_mode=False, preserve_edges_enabled=False
):
    edge_values_by_attr = {
        ATTR_KEY_EDGE_FRONT: str(_get_attr(body, ATTR_KEY_EDGE_FRONT, "") or "").strip(),
        ATTR_KEY_EDGE_BACK: str(_get_attr(body, ATTR_KEY_EDGE_BACK, "") or "").strip(),
        ATTR_KEY_EDGE_LEFT: str(_get_attr(body, ATTR_KEY_EDGE_LEFT, "") or "").strip(),
        ATTR_KEY_EDGE_RIGHT: str(_get_attr(body, ATTR_KEY_EDGE_RIGHT, "") or "").strip(),
    }
    surface_top = str(_get_attr(body, ATTR_KEY_SURFACE_TOP, "") or "").strip()
    surface_bottom = str(_get_attr(body, ATTR_KEY_SURFACE_BOTTOM, "") or "").strip()
    edge_custom_values = [
        str(_get_attr(body, ATTR_KEY_EDGE_FRONT_CUSTOM_TEXT, "") or "").strip(),
        str(_get_attr(body, ATTR_KEY_EDGE_BACK_CUSTOM_TEXT, "") or "").strip(),
        str(_get_attr(body, ATTR_KEY_EDGE_LEFT_CUSTOM_TEXT, "") or "").strip(),
        str(_get_attr(body, ATTR_KEY_EDGE_RIGHT_CUSTOM_TEXT, "") or "").strip(),
    ]

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

    all_edges_are_custom = len(edge_non_empty) == 4 and set(edge_values) == {CUSTOM_TEXT_VALUE}
    all_edge_custom_equal = bool(edge_custom_values[0]) and len(set(edge_custom_values)) == 1
    all_surface_equal = bool(surface_top) and surface_top == surface_bottom
    if all_surface_equal and all_edges_are_custom and all_edge_custom_equal:
        mode = "all"
    elif any_edge_data:
        mode = "individual"
    elif surface_any:
        mode = "individual"
    else:
        mode = "individual"
    if preserve_current_mode:
        current_mode = _read_mode_dropdown(inputs, _INPUT_EDGE_MODE, "none")
        if current_mode in ("all", "individual"):
            mode = current_mode
    if not preserve_edges_enabled:
        _set_edges_enabled_value(inputs, bool(any_edge_data or any_surface_data))

    _set_mode_dropdown(inputs, _INPUT_EDGE_MODE, mode)
    _set_edge_dropdown_value(inputs, _INPUT_EDGE_ALL, edge_values[0] if edge_all_equal else "")
    _set_surface_dropdown_value(inputs, _INPUT_ALL_SURFACE, surface_top if mode == "all" else "")
    _set_input_value(
        inputs,
        _INPUT_ALL_SURFACE_TEXT,
        str(_get_attr(body, ATTR_KEY_SURFACE_TOP_CUSTOM_TEXT, "") or "").strip() if mode == "all" else "",
    )
    _set_input_value(inputs, _INPUT_SURFACE_ALL_TEXT, "")

    _set_edge_enabled(inputs, _INPUT_EDGE_FRONT_ENABLED, bool(edge_values_by_attr[ATTR_KEY_EDGE_FRONT]))
    _set_edge_enabled(inputs, _INPUT_EDGE_BACK_ENABLED, bool(edge_values_by_attr[ATTR_KEY_EDGE_BACK]))
    _set_edge_enabled(inputs, _INPUT_EDGE_LEFT_ENABLED, bool(edge_values_by_attr[ATTR_KEY_EDGE_LEFT]))
    _set_edge_enabled(inputs, _INPUT_EDGE_RIGHT_ENABLED, bool(edge_values_by_attr[ATTR_KEY_EDGE_RIGHT]))
    _set_edge_dropdown_value(inputs, _INPUT_EDGE_FRONT, edge_values_by_attr[ATTR_KEY_EDGE_FRONT])
    _set_edge_dropdown_value(inputs, _INPUT_EDGE_BACK, edge_values_by_attr[ATTR_KEY_EDGE_BACK])
    _set_edge_dropdown_value(inputs, _INPUT_EDGE_LEFT, edge_values_by_attr[ATTR_KEY_EDGE_LEFT])
    _set_edge_dropdown_value(inputs, _INPUT_EDGE_RIGHT, edge_values_by_attr[ATTR_KEY_EDGE_RIGHT])
    _set_input_value(inputs, _INPUT_EDGE_FRONT_TEXT, str(_get_attr(body, ATTR_KEY_EDGE_FRONT_CUSTOM_TEXT, "") or "").strip())
    _set_input_value(inputs, _INPUT_EDGE_BACK_TEXT, str(_get_attr(body, ATTR_KEY_EDGE_BACK_CUSTOM_TEXT, "") or "").strip())
    _set_input_value(inputs, _INPUT_EDGE_LEFT_TEXT, str(_get_attr(body, ATTR_KEY_EDGE_LEFT_CUSTOM_TEXT, "") or "").strip())
    _set_input_value(inputs, _INPUT_EDGE_RIGHT_TEXT, str(_get_attr(body, ATTR_KEY_EDGE_RIGHT_CUSTOM_TEXT, "") or "").strip())
    _set_edge_enabled(inputs, _INPUT_TOP_ENABLED, bool(surface_top))
    _set_edge_enabled(inputs, _INPUT_BOTTOM_ENABLED, bool(surface_bottom))





def _write_or_clear_body_attribute(body, attr_key, value):
    text = str(value or "").strip()
    if text:
        _write_body_attribute_or_raise(body, attr_key, text)
    else:
        _clear_body_attribute_or_raise(body, attr_key)





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


def _read_selected_body(inputs):
    try:
        body_entity = _selection_entity_by_input_id(inputs, _INPUT_BODY)
        body = adsk.fusion.BRepBody.cast(body_entity)
        if not body:
            return _restore_body_selection_from_memory(inputs)

        native = adsk.fusion.BRepBody.cast(getattr(body, "nativeObject", None))
        resolved = native if native else body
        _remember_body_selection(resolved, body)
        return resolved
    except Exception as exc:
        print(f"Properties: Körperauswahl konnte nicht gelesen werden: {exc}")
    return None


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
