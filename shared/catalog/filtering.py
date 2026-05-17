from typing import Iterable, List

from .models import CatalogItem


def filter_items_by_type(items: Iterable[CatalogItem], item_type: str) -> List[CatalogItem]:
    normalized_type = (item_type or "").strip()
    return [item for item in items if item.type == normalized_type]

