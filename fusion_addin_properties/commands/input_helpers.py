import adsk.core


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


def _read_bool_input(inputs, input_id, fallback=False):
    try:
        item = adsk.core.BoolValueCommandInput.cast(inputs.itemById(input_id))
        if not item:
            return fallback
        return bool(item.value)
    except Exception:
        return fallback


def _set_bool_input_value(inputs, input_id, value):
    try:
        item = adsk.core.BoolValueCommandInput.cast(inputs.itemById(input_id))
        if item:
            item.value = bool(value)
    except Exception as exc:
        print(f"Properties: Bool-Input '{input_id}' konnte nicht gesetzt werden: {exc}")


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
