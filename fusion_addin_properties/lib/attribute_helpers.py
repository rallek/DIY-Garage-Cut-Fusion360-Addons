import properties_config as config


def _resolve_entity_for_attributes(entity):
    if not entity:
        return None
    try:
        native = getattr(entity, "nativeObject", None)
        if native:
            return native
    except Exception:
        pass
    return entity


def set_attr(entity, key, value):
    if not entity or not key:
        return False

    try:
        target = _resolve_entity_for_attributes(entity)
        attributes = getattr(target, "attributes", None)
        if not attributes:
            print(f"set_attr: Keine Attributes-Sammlung fuer Key '{key}'.")
            return False
        attributes.add(config.ATTRIBUTE_GROUP, key, str(value))
        return True
    except Exception as exc:
        print(f"set_attr: Schreiben fehlgeschlagen fuer Key '{key}': {exc}")
        return False


def get_attr(entity, key, default=None):
    if not entity or not key:
        return default

    try:
        target = _resolve_entity_for_attributes(entity)
        attributes = getattr(target, "attributes", None)
        if not attributes:
            return default
        attr = attributes.itemByName(config.ATTRIBUTE_GROUP, key)
        if not attr:
            return default
        return attr.value
    except Exception as exc:
        print(f"get_attr: Lesen fehlgeschlagen fuer Key '{key}': {exc}")
        return default


def clear_attr(entity, key):
    if not entity or not key:
        return False

    try:
        target = _resolve_entity_for_attributes(entity)
        attributes = getattr(target, "attributes", None)
        if not attributes:
            return False
        attr = attributes.itemByName(config.ATTRIBUTE_GROUP, key)
        if not attr:
            return True
        attr.deleteMe()
        return True
    except Exception as exc:
        print(f"clear_attr: Loeschen fehlgeschlagen fuer Key '{key}': {exc}")
        return False
