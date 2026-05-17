import json
import os
from typing import Any, Dict, Iterable, List

from .models import Catalog, CatalogItem


class CatalogLoadError(RuntimeError):
    pass


def _default_catalog_path() -> str:
    return os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "catalog.json")
    )


def _load_json(path: str) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError as exc:
        raise CatalogLoadError(f"Catalog file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise CatalogLoadError(f"Catalog JSON invalid in {path}: {exc}") from exc
    except OSError as exc:
        raise CatalogLoadError(f"Catalog file read failed: {path}: {exc}") from exc


def _parse_items(items_raw: Iterable[Dict[str, Any]]) -> Iterable[CatalogItem]:
    for idx, raw_item in enumerate(items_raw):
        if not isinstance(raw_item, dict):
            raise CatalogLoadError(f"Catalog item at index {idx} must be an object.")
        try:
            yield CatalogItem.from_dict(raw_item)
        except ValueError as exc:
            raise CatalogLoadError(f"Catalog item at index {idx} invalid: {exc}") from exc


def load_catalog(path: str = None) -> Catalog:
    catalog_path = path or _default_catalog_path()
    payload = _load_json(catalog_path)

    version_raw = payload.get("version", 1)
    try:
        version = int(version_raw)
    except (TypeError, ValueError) as exc:
        raise CatalogLoadError(f"Catalog version must be an integer, got: {version_raw}") from exc

    items_raw = payload.get("items")
    if not isinstance(items_raw, list):
        raise CatalogLoadError("Catalog root field 'items' must be an array.")

    return Catalog.build(version=version, items=_parse_items(items_raw))


def _catalog_item_to_dict(item: CatalogItem) -> Dict[str, Any]:
    payload = {
        "id": item.id,
        "type": item.type,
        "name": item.name,
        "appearance": item.appearance,
    }
    if item.properties:
        payload.update(item.properties)
    return payload


def save_catalog(catalog: Catalog, path: str = None) -> str:
    catalog_path = path or _default_catalog_path()
    payload = {
        "version": int(catalog.version),
        "items": [_catalog_item_to_dict(item) for item in catalog.items],
    }
    try:
        with open(catalog_path, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    except OSError as exc:
        raise CatalogLoadError(f"Catalog file write failed: {catalog_path}: {exc}") from exc
    return catalog_path


def upsert_catalog_item(catalog: Catalog, item: CatalogItem) -> Catalog:
    next_items: List[CatalogItem] = []
    replaced = False
    for existing in catalog.items:
        if existing.id == item.id:
            next_items.append(item)
            replaced = True
            continue
        next_items.append(existing)
    if not replaced:
        next_items.append(item)
    return Catalog.build(version=catalog.version, items=next_items)
