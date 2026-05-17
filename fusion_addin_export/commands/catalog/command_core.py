from shared.catalog import CatalogLoadError, filter_items_by_type, load_catalog


_cached_catalog = None


def load_catalog_data(path=None, force_reload=False):
    global _cached_catalog
    if _cached_catalog is not None and not force_reload:
        return _cached_catalog
    _cached_catalog = load_catalog(path=path)
    return _cached_catalog


def get_catalog_item(item_id):
    catalog = load_catalog_data()
    return catalog.get(item_id)


def filter_catalog_items(item_type):
    catalog = load_catalog_data()
    return filter_items_by_type(catalog.items, item_type)


def get_supported_types():
    catalog = load_catalog_data()
    return sorted({item.type for item in catalog.items})


def start():
    try:
        load_catalog_data()
    except CatalogLoadError as exc:
        print(f"Catalog-Init fehlgeschlagen: {exc}")
    return


def stop():
    global _cached_catalog
    _cached_catalog = None
    return
