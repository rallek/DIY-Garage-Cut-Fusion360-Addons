try:
    from .constants import *
except ImportError:
    from constants import *


class EdgeSurfaceValueModel:
    def __init__(
        self,
        inputs,
        read_mode_dropdown,
        read_edge_dropdown_value,
        read_surface_dropdown_value,
        read_string_input,
        write_body_attribute_or_raise,
        clear_body_attribute_or_raise,
        surface_by_id,
    ):
        self.inputs = inputs
        self._read_mode_dropdown = read_mode_dropdown
        self._read_edge_dropdown_value = read_edge_dropdown_value
        self._read_surface_dropdown_value = read_surface_dropdown_value
        self._read_string_input = read_string_input
        self._write_body_attribute_or_raise = write_body_attribute_or_raise
        self._clear_body_attribute_or_raise = clear_body_attribute_or_raise
        self._surface_by_id = surface_by_id

    def _read_mode(self):
        return self._read_mode_dropdown(self.inputs, _INPUT_EDGE_MODE, "none")

    def read_enabled_edge_values(self, require_material=False):
        mapping = {
            ATTR_KEY_EDGE_FRONT: (_INPUT_EDGE_FRONT_ENABLED, _INPUT_EDGE_FRONT),
            ATTR_KEY_EDGE_BACK: (_INPUT_EDGE_BACK_ENABLED, _INPUT_EDGE_BACK),
            ATTR_KEY_EDGE_LEFT: (_INPUT_EDGE_LEFT_ENABLED, _INPUT_EDGE_LEFT),
            ATTR_KEY_EDGE_RIGHT: (_INPUT_EDGE_RIGHT_ENABLED, _INPUT_EDGE_RIGHT),
        }
        values = {}
        for attr_key, (_enabled_id, dropdown_id) in mapping.items():
            edge_id = self._read_edge_dropdown_value(self.inputs, dropdown_id)
            if require_material and edge_id == CUSTOM_TEXT_VALUE:
                self.require_custom_text_for_attr(attr_key)
            values[attr_key] = edge_id
        return values

    def read_edge_values_for_mode(self, require_material=False):
        mode = self._read_mode()
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
        return self.read_enabled_edge_values(require_material=require_material)

    def read_surface_values_for_mode(self):
        mode = self._read_mode()
        if mode == "all":
            value = self._read_surface_dropdown_value(self.inputs, _INPUT_ALL_SURFACE)
            return {ATTR_KEY_SURFACE_TOP: value, ATTR_KEY_SURFACE_BOTTOM: value}
        if mode != "individual":
            return {ATTR_KEY_SURFACE_TOP: "", ATTR_KEY_SURFACE_BOTTOM: ""}
        return {
            ATTR_KEY_SURFACE_TOP: self._read_surface_dropdown_value(self.inputs, _INPUT_TOP_SURFACE),
            ATTR_KEY_SURFACE_BOTTOM: self._read_surface_dropdown_value(self.inputs, _INPUT_BOTTOM_SURFACE),
        }

    def require_custom_text_for_attr(self, attr_key):
        text = self.read_custom_text_for_attr(attr_key)
        if not text:
            raise RuntimeError("Für Auswahl 'Text' muss ein Freitext eingetragen werden.")
        return text

    def read_custom_text_for_attr(self, attr_key):
        if attr_key in (ATTR_KEY_SURFACE_TOP, ATTR_KEY_SURFACE_BOTTOM) and self._read_mode() == "all":
            return self._read_string_input(self.inputs, _INPUT_ALL_SURFACE_TEXT, "").strip()
        input_id = custom_text_input_for_attr(attr_key)
        if not input_id:
            return ""
        return self._read_string_input(self.inputs, input_id, "").strip()

    def validate_custom_text_values(self, values):
        for attr_key, value in (values or {}).items():
            if value == CUSTOM_TEXT_VALUE:
                self.require_custom_text_for_attr(attr_key)

    def write_custom_text_attributes(self, body, values):
        for attr_key, custom_attr_key in custom_text_attr_mapping().items():
            if (values or {}).get(attr_key) == CUSTOM_TEXT_VALUE:
                self._write_body_attribute_or_raise(body, custom_attr_key, self.require_custom_text_for_attr(attr_key))
            else:
                self._clear_body_attribute_or_raise(body, custom_attr_key)

    def write_all_mode_edge_attributes(self, body):
        text = self.all_mode_surface_export_name()
        edge_attrs = (
            (ATTR_KEY_EDGE_FRONT, ATTR_KEY_EDGE_FRONT_CUSTOM_TEXT),
            (ATTR_KEY_EDGE_BACK, ATTR_KEY_EDGE_BACK_CUSTOM_TEXT),
            (ATTR_KEY_EDGE_LEFT, ATTR_KEY_EDGE_LEFT_CUSTOM_TEXT),
            (ATTR_KEY_EDGE_RIGHT, ATTR_KEY_EDGE_RIGHT_CUSTOM_TEXT),
        )
        for edge_attr, custom_attr in edge_attrs:
            if text:
                self._write_body_attribute_or_raise(body, edge_attr, CUSTOM_TEXT_VALUE)
                self._write_body_attribute_or_raise(body, custom_attr, text)
            else:
                self._clear_body_attribute_or_raise(body, edge_attr)
                self._clear_body_attribute_or_raise(body, custom_attr)

    def all_mode_surface_export_name(self):
        surface_id = self._read_surface_dropdown_value(self.inputs, _INPUT_ALL_SURFACE)
        if not surface_id:
            return ""
        if surface_id == CUSTOM_TEXT_VALUE:
            return self.require_custom_text_for_attr(ATTR_KEY_SURFACE_TOP)
        surface_entry = self._surface_by_id.get(surface_id)
        if not surface_entry:
            raise RuntimeError(f"Oberfläche '{surface_id}' ist nicht im Katalog vorhanden.")
        return str(surface_entry.name or "").strip()


def custom_text_input_for_attr(attr_key):
    mapping = {
        ATTR_KEY_EDGE_FRONT: _INPUT_EDGE_FRONT_TEXT,
        ATTR_KEY_EDGE_BACK: _INPUT_EDGE_BACK_TEXT,
        ATTR_KEY_EDGE_LEFT: _INPUT_EDGE_LEFT_TEXT,
        ATTR_KEY_EDGE_RIGHT: _INPUT_EDGE_RIGHT_TEXT,
        ATTR_KEY_SURFACE_TOP: _INPUT_TOP_SURFACE_TEXT,
        ATTR_KEY_SURFACE_BOTTOM: _INPUT_BOTTOM_SURFACE_TEXT,
    }
    return mapping.get(attr_key, "")


def custom_text_attr_mapping():
    return {
        ATTR_KEY_EDGE_FRONT: ATTR_KEY_EDGE_FRONT_CUSTOM_TEXT,
        ATTR_KEY_EDGE_BACK: ATTR_KEY_EDGE_BACK_CUSTOM_TEXT,
        ATTR_KEY_EDGE_LEFT: ATTR_KEY_EDGE_LEFT_CUSTOM_TEXT,
        ATTR_KEY_EDGE_RIGHT: ATTR_KEY_EDGE_RIGHT_CUSTOM_TEXT,
        ATTR_KEY_SURFACE_TOP: ATTR_KEY_SURFACE_TOP_CUSTOM_TEXT,
        ATTR_KEY_SURFACE_BOTTOM: ATTR_KEY_SURFACE_BOTTOM_CUSTOM_TEXT,
    }


def has_any_surface_value(surface_values):
    return any(str(value or "").strip() for value in (surface_values or {}).values())
