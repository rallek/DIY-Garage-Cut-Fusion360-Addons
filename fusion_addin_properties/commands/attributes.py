import adsk.core
import adsk.fusion

try:
    from .constants import ATTRIBUTE_GROUP
except ImportError:
    from constants import ATTRIBUTE_GROUP


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


def _is_truthy_attr(value):
    return str(value or "").strip().lower() in ("true", "1", "yes", "ja", "on")
