import json
import os
from typing import Any, Dict, Iterable, List, Optional, Set

SUPPORTED_FIELD_KINDS = frozenset({"number", "string", "boolean", "enum"})


_DEFAULT_TYPE_CONFIG = {
    "version": 1,
    "types": [
        {
            "id": "sheet",
            "labels": {"de": "Platte", "en": "Sheet"},
            "fields": [
                {
                    "key": "sheet_default_trim_allowance",
                    "kind": "number",
                    "labels": {"de": "Standard-Fräszugabe", "en": "Default trim allowance"},
                    "min": 0.0,
                    "max": 5.0,
                    "step": 0.1,
                    "default": 0.0,
                    "csv": True,
                    "quantity": "length",
                    "storage_unit": "mm",
                    "legacy_keys": ["default_trim_allowance_mm"],
                }
            ],
        },
        {
            "id": "bar",
            "labels": {"de": "Stab", "en": "Bar"},
            "fields": [],
        },
        {
            "id": "edge",
            "labels": {"de": "Kante", "en": "Edge"},
            "fields": [
                {
                    "key": "edge_thickness",
                    "kind": "number",
                    "labels": {"de": "Materialdicke", "en": "Edge thickness"},
                    "min": 0.0,
                    "max": 10.0,
                    "step": 0.1,
                    "default": 0.0,
                    "csv": True,
                    "quantity": "length",
                    "storage_unit": "mm",
                    "legacy_keys": ["thickness_mm"],
                }
            ],
        },
        {
            "id": "profile",
            "labels": {"de": "Profil", "en": "Profile"},
            "fields": [],
        },
        {
            "id": "hardware",
            "labels": {"de": "Beschlag", "en": "Hardware"},
            "fields": [],
        },
        {
            "id": "consumable",
            "labels": {"de": "Verbrauchsmaterial", "en": "Consumable"},
            "fields": [],
        },
    ],
}

_cached_config = None


def _default_config_path() -> str:
    return os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "catalog_type_config.json")
    )


def _to_float(value: Any, fallback: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _normalize_field(raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not isinstance(raw, dict):
        return None
    key = str(raw.get("key", "")).strip()
    if not key:
        return None
    kind = str(raw.get("kind", "")).strip().lower()
    if kind not in SUPPORTED_FIELD_KINDS:
        return None
    labels = raw.get("labels")
    if not isinstance(labels, dict):
        labels = {}
    legacy_keys_raw = raw.get("legacy_keys")
    legacy_keys: List[str] = []
    if isinstance(legacy_keys_raw, list):
        for entry in legacy_keys_raw:
            key_name = str(entry or "").strip()
            if key_name and key_name != key and key_name not in legacy_keys:
                legacy_keys.append(key_name)
    quantity = str(raw.get("quantity", "number") or "number").strip().lower()
    storage_unit = str(raw.get("storage_unit", "") or "").strip()
    result = {
        "key": key,
        "kind": kind,
        "labels": {"de": str(labels.get("de", key)), "en": str(labels.get("en", key))},
        "csv": bool(raw.get("csv", False)),
        "quantity": quantity,
        "storage_unit": storage_unit,
        "legacy_keys": legacy_keys,
    }
    if kind == "number":
        min_value = _to_float(raw.get("min"), 0.0)
        max_value = _to_float(raw.get("max"), min_value)
        if max_value < min_value:
            max_value = min_value
        step = _to_float(raw.get("step"), 0.1)
        if step <= 0.0:
            step = 0.1
        default = _to_float(raw.get("default"), min_value)
        default = max(min_value, min(max_value, default))
        result.update(
            {
                "min": min_value,
                "max": max_value,
                "step": step,
                "default": default,
            }
        )
        return result

    if kind == "string":
        min_length = int(_to_float(raw.get("min_length"), 0.0))
        max_length = int(_to_float(raw.get("max_length"), 1024.0))
        if max_length < min_length:
            max_length = min_length
        default = str(raw.get("default", ""))
        if len(default) < min_length:
            default = default + (" " * (min_length - len(default)))
        if len(default) > max_length:
            default = default[:max_length]
        result.update(
            {
                "min_length": min_length,
                "max_length": max_length,
                "default": default,
            }
        )
        return result

    if kind == "boolean":
        result.update({"default": bool(raw.get("default", False))})
        return result

    options_raw = raw.get("options")
    options: List[str] = []
    if isinstance(options_raw, list):
        for entry in options_raw:
            text = str(entry or "").strip()
            if text and text not in options:
                options.append(text)
    if not options:
        options = ["value"]
    default = str(raw.get("default", options[0]))
    if default not in options:
        default = options[0]
    result.update({"options": options, "default": default})
    return result


def _normalize_type(raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not isinstance(raw, dict):
        return None
    type_id = str(raw.get("id", "")).strip()
    if not type_id:
        return None
    labels = raw.get("labels")
    if not isinstance(labels, dict):
        labels = {}
    fields_raw = raw.get("fields")
    fields: List[Dict[str, Any]] = []
    seen_keys = set()
    if isinstance(fields_raw, list):
        for entry in fields_raw:
            field = _normalize_field(entry)
            if not field:
                continue
            if field["key"] in seen_keys:
                continue
            seen_keys.add(field["key"])
            fields.append(field)
    return {
        "id": type_id,
        "labels": {"de": str(labels.get("de", type_id)), "en": str(labels.get("en", type_id))},
        "fields": fields,
    }


def _normalize_config(config_data: Dict[str, Any]) -> Dict[str, Any]:
    raw_types = config_data.get("types")
    normalized_types: List[Dict[str, Any]] = []
    seen = set()
    if isinstance(raw_types, list):
        for entry in raw_types:
            type_def = _normalize_type(entry)
            if not type_def:
                continue
            type_id = type_def["id"]
            if type_id in seen:
                continue
            seen.add(type_id)
            normalized_types.append(type_def)
    if not normalized_types:
        normalized_types = [_normalize_type(entry) for entry in _DEFAULT_TYPE_CONFIG["types"]]
        normalized_types = [entry for entry in normalized_types if entry]
    return {"version": 1, "types": normalized_types}


def _load_config_from_file(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        raw = json.load(handle)
    if not isinstance(raw, dict):
        raise ValueError("Type config root must be an object.")
    return _normalize_config(raw)


def load_type_config(path: str = None, reload: bool = False) -> Dict[str, Any]:
    global _cached_config
    if _cached_config is not None and not reload and not path:
        return _cached_config

    loaded = None
    config_path = path or _default_config_path()
    if os.path.exists(config_path):
        try:
            loaded = _load_config_from_file(config_path)
        except Exception:
            loaded = None
    if loaded is None:
        loaded = _normalize_config(_DEFAULT_TYPE_CONFIG)

    if not path:
        _cached_config = loaded
    return loaded


def get_catalog_types() -> List[str]:
    config = load_type_config()
    return [entry["id"] for entry in config["types"]]


def get_type_definition(type_id: str) -> Optional[Dict[str, Any]]:
    wanted = (type_id or "").strip()
    if not wanted:
        return None
    config = load_type_config()
    for entry in config["types"]:
        if entry["id"] == wanted:
            return entry
    return None


def get_type_fields(type_id: str) -> List[Dict[str, Any]]:
    type_def = get_type_definition(type_id)
    if not type_def:
        return []
    return list(type_def.get("fields", []))


def get_type_label(type_id: str, lang: str = "de") -> str:
    type_def = get_type_definition(type_id)
    if not type_def:
        return type_id
    labels = type_def.get("labels", {})
    if lang == "en":
        return str(labels.get("en", type_id))
    return str(labels.get("de", type_id))


def get_all_type_field_keys() -> Set[str]:
    keys: Set[str] = set()
    for type_id in get_catalog_types():
        for field in get_type_fields(type_id):
            key = field.get("key")
            if key:
                keys.add(key)
    return keys


def get_all_type_field_alias_keys() -> Set[str]:
    keys: Set[str] = set()
    for type_id in get_catalog_types():
        for field in get_type_fields(type_id):
            for legacy_key in field.get("legacy_keys", []):
                keys.add(str(legacy_key))
    return keys


def get_type_default_properties(type_id: str) -> Dict[str, Any]:
    defaults: Dict[str, Any] = {}
    for field in get_type_fields(type_id):
        key = field.get("key")
        if not key:
            continue
        defaults[key] = field.get("default")
    return defaults


def get_csv_field_keys(type_id: str) -> List[str]:
    keys: List[str] = []
    for field in get_type_fields(type_id):
        if field.get("csv"):
            key = field.get("key")
            if key:
                keys.append(key)
    return keys


def get_csv_fields(type_id: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for field in get_type_fields(type_id):
        if field.get("csv"):
            out.append(dict(field))
    return out


def normalize_type_properties(type_id: str, properties: Dict[str, Any]) -> Dict[str, Any]:
    cleaned = dict(properties or {})
    fields = get_type_fields(type_id)
    alias_to_key: Dict[str, str] = {}
    for field in fields:
        key = field["key"]
        for alias in field.get("legacy_keys", []):
            alias_to_key[str(alias)] = key
    for alias, key in alias_to_key.items():
        if key in cleaned:
            continue
        if alias in cleaned:
            cleaned[key] = cleaned.get(alias)
    for alias in alias_to_key:
        cleaned.pop(alias, None)

    for field in fields:
        key = field["key"]
        if key not in cleaned:
            continue
        value = cleaned.get(key)
        kind = field["kind"]
        if kind == "number":
            try:
                numeric = float(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"'{key}' must be numeric.") from exc
            min_value = float(field["min"])
            max_value = float(field["max"])
            if numeric < min_value or numeric > max_value:
                raise ValueError(f"'{key}' must be between {min_value:g} and {max_value:g}.")
            step = float(field["step"])
            rounded_steps = round((numeric - min_value) / step)
            snapped = min_value + rounded_steps * step
            decimals = max(0, len(str(step).split(".")[1]) if "." in str(step) else 0)
            cleaned[key] = round(snapped, decimals)
            continue

        if kind == "string":
            text = str(value or "")
            min_length = int(field.get("min_length", 0))
            max_length = int(field.get("max_length", 1024))
            if len(text) < min_length:
                raise ValueError(f"'{key}' is too short.")
            if len(text) > max_length:
                raise ValueError(f"'{key}' is too long.")
            cleaned[key] = text
            continue

        if kind == "boolean":
            if isinstance(value, bool):
                cleaned[key] = value
            elif isinstance(value, str):
                lowered = value.strip().lower()
                if lowered in ("true", "1", "yes", "ja"):
                    cleaned[key] = True
                elif lowered in ("false", "0", "no", "nein"):
                    cleaned[key] = False
                else:
                    raise ValueError(f"'{key}' must be boolean.")
            else:
                cleaned[key] = bool(value)
            continue

        if kind == "enum":
            options = list(field.get("options", []))
            candidate = str(value or "")
            if candidate not in options:
                raise ValueError(f"'{key}' must be one of: {', '.join(options)}.")
            cleaned[key] = candidate
            continue
    return cleaned
