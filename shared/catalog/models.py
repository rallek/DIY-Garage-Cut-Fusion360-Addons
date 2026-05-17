from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

CATALOG_TYPES = frozenset({
    "sheet",
    "bar",
    "edge",
    "profile",
    "hardware",
    "consumable",
})


@dataclass(frozen=True)
class CatalogItem:
    id: str
    type: str
    name: str
    appearance: str
    properties: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CatalogItem":
        required = ("id", "type", "name", "appearance")
        missing = [field_name for field_name in required if not data.get(field_name)]
        if missing:
            raise ValueError(f"Catalog item missing required fields: {', '.join(missing)}")

        item_type = str(data["type"]).strip()
        if item_type not in CATALOG_TYPES:
            raise ValueError(f"Unsupported catalog type: {item_type}")

        base_fields = {"id", "type", "name", "appearance"}
        extra = {k: v for k, v in data.items() if k not in base_fields}
        return cls(
            id=str(data["id"]).strip(),
            type=item_type,
            name=str(data["name"]).strip(),
            appearance=str(data["appearance"]).strip(),
            properties=extra,
        )


@dataclass(frozen=True)
class Catalog:
    version: int
    items: List[CatalogItem]
    _index: Dict[str, CatalogItem] = field(default_factory=dict)

    @classmethod
    def build(cls, version: int, items: Iterable[CatalogItem]) -> "Catalog":
        item_list = list(items)
        index: Dict[str, CatalogItem] = {}
        for item in item_list:
            if item.id in index:
                raise ValueError(f"Duplicate catalog item id: {item.id}")
            index[item.id] = item
        return cls(version=version, items=item_list, _index=index)

    def by_type(self, item_type: str) -> List[CatalogItem]:
        normalized_type = (item_type or "").strip()
        return [item for item in self.items if item.type == normalized_type]

    def get(self, item_id: str) -> Optional[CatalogItem]:
        return self._index.get((item_id or "").strip())

