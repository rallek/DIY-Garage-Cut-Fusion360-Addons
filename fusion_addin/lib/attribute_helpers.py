import config


def set_attr(entity, key, value):
    if not entity or not key:
        return False

    try:
        attributes = getattr(entity, "attributes", None)
        if not attributes:
            return False
        attributes.add(config.ATTRIBUTE_GROUP, key, str(value))
        return True
    except Exception:
        return False


def get_attr(entity, key, default=None):
    if not entity or not key:
        return default

    try:
        attributes = getattr(entity, "attributes", None)
        if not attributes:
            return default
        attr = attributes.itemByName(config.ATTRIBUTE_GROUP, key)
        if not attr:
            return default
        return attr.value
    except Exception:
        return default


def clear_attr(entity, key):
    if not entity or not key:
        return False

    try:
        attributes = getattr(entity, "attributes", None)
        if not attributes:
            return False
        attr = attributes.itemByName(config.ATTRIBUTE_GROUP, key)
        if not attr:
            return True
        attr.deleteMe()
        return True
    except Exception:
        return False
