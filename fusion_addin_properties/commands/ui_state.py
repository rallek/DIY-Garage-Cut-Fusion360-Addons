import adsk.core

try:
    from .constants import *
except ImportError:
    from constants import *


class UiStateController:
    def __init__(
        self,
        inputs,
        material_by_id,
        read_selected_body,
        read_material_dropdown_value,
        read_mode_dropdown,
        set_mode_dropdown,
        read_surface_dropdown_value,
        read_edge_dropdown_value,
        selected_front_face,
        selected_or_restored_front_face,
        restore_body_selection_from_memory,
        set_input_value,
    ):
        self.inputs = inputs
        self._material_by_id = material_by_id
        self._read_selected_body = read_selected_body
        self._read_material_dropdown_value = read_material_dropdown_value
        self._read_mode_dropdown = read_mode_dropdown
        self._set_mode_dropdown = set_mode_dropdown
        self._read_surface_dropdown_value = read_surface_dropdown_value
        self._read_edge_dropdown_value = read_edge_dropdown_value
        self._selected_front_face = selected_front_face
        self._selected_or_restored_front_face = selected_or_restored_front_face
        self._restore_body_selection_from_memory = restore_body_selection_from_memory
        self._set_input_value = set_input_value

    def set_main_controls_visible(self, visible):
        main_ids = (
            _INPUT_SIZE,
            _INPUT_FILTER_TYPE,
            _INPUT_MATERIAL,
            _INPUT_TRIM_ALLOWANCE,
            _INPUT_GRAIN_DIRECTION,
            _INPUT_EDGES_ENABLED,
            _INPUT_EXCLUDE_FROM_EXPORT,
        )
        for input_id in main_ids:
            item = self.inputs.itemById(input_id)
            if item:
                item.isVisible = bool(visible)

    def set_edge_controls_visible(self, visible):
        edge_ids = (
            _INPUT_EDGES_HEADER,
            _INPUT_EDGE_MODE,
            _INPUT_FRONT_FACE,
            _INPUT_EDGE_ALL,
            _INPUT_ALL_SURFACE,
            _INPUT_ALL_SURFACE_TEXT,
            _INPUT_EDGE_FRONT_ENABLED,
            _INPUT_EDGE_FRONT,
            _INPUT_EDGE_FRONT_TEXT,
            _INPUT_EDGE_BACK_ENABLED,
            _INPUT_EDGE_BACK,
            _INPUT_EDGE_BACK_TEXT,
            _INPUT_EDGE_LEFT_ENABLED,
            _INPUT_EDGE_LEFT,
            _INPUT_EDGE_LEFT_TEXT,
            _INPUT_EDGE_RIGHT_ENABLED,
            _INPUT_EDGE_RIGHT,
            _INPUT_EDGE_RIGHT_TEXT,
            _INPUT_SWAP_LEFT_RIGHT,
            _INPUT_SURFACE_ALL_TEXT,
            _INPUT_TOP_ENABLED,
            _INPUT_TOP_SURFACE,
            _INPUT_TOP_SURFACE_TEXT,
            _INPUT_BOTTOM_ENABLED,
            _INPUT_BOTTOM_SURFACE,
            _INPUT_BOTTOM_SURFACE_TEXT,
            _INPUT_SWAP_SURFACES,
        )
        for input_id in edge_ids:
            item = self.inputs.itemById(input_id)
            if item:
                item.isVisible = bool(visible)
        for enabled_id in (
            _INPUT_EDGE_FRONT_ENABLED,
            _INPUT_EDGE_BACK_ENABLED,
            _INPUT_EDGE_LEFT_ENABLED,
            _INPUT_EDGE_RIGHT_ENABLED,
        ):
            enabled_item = self.edge_enabled_input(enabled_id)
            if enabled_item:
                enabled_item.isEnabled = True

    def set_notes_controls_visible(self, visible):
        for input_id in (_INPUT_NOTES_HEADER, _INPUT_NOTES, _INPUT_APPLY):
            item = self.inputs.itemById(input_id)
            if item:
                item.isVisible = bool(visible)
                item.isEnabled = bool(visible)

    def edges_enabled_input(self):
        return adsk.core.BoolValueCommandInput.cast(self.inputs.itemById(_INPUT_EDGES_ENABLED))

    def is_edges_enabled(self):
        item = self.edges_enabled_input()
        return bool(item and item.value)

    def set_edges_enabled_value(self, enabled):
        item = self.edges_enabled_input()
        if item:
            item.value = bool(enabled)

    def set_edges_enabled_visible(self, visible):
        item = self.edges_enabled_input()
        if item:
            item.isVisible = bool(visible)
            item.isEnabled = bool(visible)

    def selected_material_entry(self):
        material_id = self._read_material_dropdown_value(self.inputs, raise_on_unknown=False)
        return self._material_by_id.get(material_id or "")

    def edge_surface_ui_state(self):
        body = self._read_selected_body(self.inputs)
        entry = self.selected_material_entry()
        supports_edges = bool(entry and entry.supports_edges)
        supports_surface = bool(entry and entry.supports_surface)
        supports_any = supports_edges or supports_surface
        checkbox_visible = bool(body and supports_any)
        section_visible = checkbox_visible and self.is_edges_enabled()
        mode = self._read_mode_dropdown(self.inputs, _INPUT_EDGE_MODE, "none")
        if section_visible and supports_surface and not supports_edges:
            mode = "all"
            self._set_mode_dropdown(self.inputs, _INPUT_EDGE_MODE, mode)
        elif section_visible and mode == "none":
            mode = "individual" if supports_edges else "all"
            self._set_mode_dropdown(self.inputs, _INPUT_EDGE_MODE, mode)
        mode_visible = section_visible and supports_edges
        return {
            "body": body,
            "entry": entry,
            "supports_edges": supports_edges,
            "supports_surface": supports_surface,
            "checkbox_visible": checkbox_visible,
            "section_visible": section_visible,
            "mode": mode,
            "mode_visible": mode_visible,
        }

    def set_input_visibility(self, input_id, visible, enabled=None):
        item = self.inputs.itemById(input_id)
        if not item:
            return
        item.isVisible = bool(visible)
        item.isEnabled = bool(visible if enabled is None else enabled)

    def render_edge_surface_ui(self, restore_front_face=True):
        state = self.edge_surface_ui_state()
        checkbox_visible = state["checkbox_visible"]
        section_visible = state["section_visible"]
        mode = state["mode"]
        mode_visible = state["mode_visible"]
        supports_edges = state["supports_edges"]
        supports_surface = state["supports_surface"]
        body = state["body"]

        self.set_edges_enabled_visible(checkbox_visible)
        self.set_input_visibility(_INPUT_EDGES_HEADER, section_visible)
        self.set_input_visibility(_INPUT_EDGE_MODE, mode_visible)

        front_visible = section_visible and mode == "individual" and supports_edges
        self.set_input_visibility(_INPUT_FRONT_FACE, front_visible)
        if restore_front_face and front_visible and body:
            self._selected_or_restored_front_face(self.inputs, body)
        front_ready = bool(self._selected_front_face(self.inputs)) if front_visible else False

        self.set_input_visibility(_INPUT_EDGE_ALL, False)
        self.set_input_visibility(_INPUT_SURFACE_ALL_TEXT, False)

        all_surface_visible = section_visible and mode == "all" and supports_surface
        self.set_input_visibility(_INPUT_ALL_SURFACE, all_surface_visible)
        all_surface_is_custom = (
            all_surface_visible and self._read_surface_dropdown_value(self.inputs, _INPUT_ALL_SURFACE) == CUSTOM_TEXT_VALUE
        )
        self.set_input_visibility(_INPUT_ALL_SURFACE_TEXT, all_surface_is_custom)

        edge_visible = section_visible and mode == "individual" and supports_edges and front_ready
        for enabled_id, dropdown_id, text_id in (
            (_INPUT_EDGE_FRONT_ENABLED, _INPUT_EDGE_FRONT, _INPUT_EDGE_FRONT_TEXT),
            (_INPUT_EDGE_BACK_ENABLED, _INPUT_EDGE_BACK, _INPUT_EDGE_BACK_TEXT),
            (_INPUT_EDGE_LEFT_ENABLED, _INPUT_EDGE_LEFT, _INPUT_EDGE_LEFT_TEXT),
            (_INPUT_EDGE_RIGHT_ENABLED, _INPUT_EDGE_RIGHT, _INPUT_EDGE_RIGHT_TEXT),
        ):
            self.set_input_visibility(enabled_id, False)
            self.set_edge_enabled(enabled_id, bool(self._read_edge_dropdown_value(self.inputs, dropdown_id)))
            self.set_input_visibility(dropdown_id, edge_visible)
            edge_is_custom = edge_visible and self._read_edge_dropdown_value(self.inputs, dropdown_id) == CUSTOM_TEXT_VALUE
            self.set_input_visibility(text_id, edge_is_custom)
        self.set_input_visibility(_INPUT_SWAP_LEFT_RIGHT, edge_visible)

        surface_visible = section_visible and mode == "individual" and supports_surface and (
            not supports_edges or front_ready
        )
        for enabled_id, dropdown_id, text_id in (
            (_INPUT_TOP_ENABLED, _INPUT_TOP_SURFACE, _INPUT_TOP_SURFACE_TEXT),
            (_INPUT_BOTTOM_ENABLED, _INPUT_BOTTOM_SURFACE, _INPUT_BOTTOM_SURFACE_TEXT),
        ):
            self.set_input_visibility(enabled_id, False)
            self.set_edge_enabled(enabled_id, bool(self._read_surface_dropdown_value(self.inputs, dropdown_id)))
            self.set_input_visibility(dropdown_id, surface_visible)
            surface_is_custom = (
                surface_visible and self._read_surface_dropdown_value(self.inputs, dropdown_id) == CUSTOM_TEXT_VALUE
            )
            self.set_input_visibility(text_id, surface_is_custom)
        self.set_input_visibility(_INPUT_SWAP_SURFACES, surface_visible)

    def update_edge_surface_ui(self, restore_front_face=True):
        body = self._read_selected_body(self.inputs)
        try:
            self.render_edge_surface_ui(restore_front_face=restore_front_face)
        finally:
            if body:
                self._restore_body_selection_from_memory(self.inputs)

    def clear_custom_text_inputs(self):
        for input_id in (
            _INPUT_EDGE_FRONT_TEXT,
            _INPUT_EDGE_BACK_TEXT,
            _INPUT_EDGE_LEFT_TEXT,
            _INPUT_EDGE_RIGHT_TEXT,
            _INPUT_TOP_SURFACE_TEXT,
            _INPUT_BOTTOM_SURFACE_TEXT,
            _INPUT_ALL_SURFACE_TEXT,
        ):
            self._set_input_value(self.inputs, input_id, "")

    def set_edge_controls_for_material(self, _material_id):
        self.render_edge_surface_ui()

    def edge_enabled_input(self, enabled_input_id):
        return adsk.core.BoolValueCommandInput.cast(self.inputs.itemById(enabled_input_id))

    def is_edge_enabled(self, enabled_input_id):
        item = self.edge_enabled_input(enabled_input_id)
        return bool(item and item.value)

    def set_edge_enabled(self, enabled_input_id, enabled):
        item = self.edge_enabled_input(enabled_input_id)
        if item:
            item.value = bool(enabled)

    def set_edge_dropdown_enabled_state(self, restore_front_face=True):
        self.render_edge_surface_ui(restore_front_face=restore_front_face)
