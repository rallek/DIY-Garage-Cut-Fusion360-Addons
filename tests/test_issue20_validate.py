import os
import sys
import types
import unittest
import importlib.util


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ADDIN_DIR = os.path.join(ROOT_DIR, "fusion_addin_export")
for path in (ADDIN_DIR, ROOT_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)


adsk_module = types.ModuleType("adsk")
adsk_core = types.ModuleType("adsk.core")
adsk_fusion = types.ModuleType("adsk.fusion")


class _Application:
    @staticmethod
    def get():
        return None


class _Design:
    @staticmethod
    def cast(value):
        return value


class _EventHandler:
    pass


adsk_core.Application = _Application
adsk_core.CommandCreatedEventHandler = _EventHandler
adsk_core.CommandEventHandler = _EventHandler
adsk_fusion.Design = _Design
adsk_module.core = adsk_core
adsk_module.fusion = adsk_fusion
sys.modules.setdefault("adsk", adsk_module)
sys.modules.setdefault("adsk.core", adsk_core)
sys.modules.setdefault("adsk.fusion", adsk_fusion)


def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


commands_pkg = types.ModuleType("commands")
commands_pkg.__path__ = []
export_pkg = types.ModuleType("commands.export")
validate_pkg = types.ModuleType("commands.validate")
sys.modules["commands"] = commands_pkg
sys.modules["commands.export"] = export_pkg
sys.modules["commands.validate"] = validate_pkg

export_core = _load_module(
    "commands.export.command_core",
    os.path.join(ADDIN_DIR, "commands", "export", "command_core.py"),
)
export_pkg.command_core = export_core
validate_core = _load_module(
    "commands.validate.command_core",
    os.path.join(ADDIN_DIR, "commands", "validate", "command_core.py"),
)
validate_pkg.command_core = validate_core


class _FakeAttribute:
    def __init__(self, group, name, value):
        self.groupName = group
        self.name = name
        self.value = value


class _FakeAttributes:
    def __init__(self, rows):
        self._rows = [_FakeAttribute(*row) for row in rows]
        self.count = len(self._rows)

    def item(self, index):
        return self._rows[index]


class _FakeBody:
    def __init__(self, name, attrs):
        self.name = name
        self.isVisible = True
        self.entityToken = f"token-{name}"
        self.attributes = _FakeAttributes(attrs)


class _FakeCatalogItem:
    def __init__(self, item_id, item_type, name, properties=None):
        self.id = item_id
        self.type = item_type
        self.name = name
        self.properties = properties or {}


class _FakeCatalog:
    def __init__(self, items):
        self._items = {item.id: item for item in items}

    def get(self, item_id):
        return self._items.get(item_id)


class Issue20ValidateTests(unittest.TestCase):
    def test_excluded_body_is_not_reported_as_issue(self):
        body = _body("helper", exclude_from_export="true")
        result = _analyze([body], _FakeCatalog([]))

        self.assertEqual(result.excluded_count, 1)
        self.assertEqual(result.issue_count, 0)
        self.assertEqual(result.ready_count, 0)

    def test_missing_material_is_reported(self):
        body = _body("side")
        result = _analyze([body], _FakeCatalog([]))

        self.assertEqual(result.issue_count, 1)
        self.assertIn("Material", result.issues_by_body[0][1][0])

    def test_invalid_edge_uses_readable_label(self):
        body = _body(
            "side",
            material_id="sheet.white",
            trim_allowance_mm="1.0",
            edge_front="missing.edge",
        )
        catalog = _FakeCatalog([_FakeCatalogItem("sheet.white", "sheet", "White")])

        result = _analyze([body], catalog)

        self.assertEqual(result.issue_count, 1)
        message = "\n".join(result.issues_by_body[0][1])
        self.assertIn("Kante vorne", message)
        self.assertNotIn("edge_front", message)

    def test_surface_on_unsupported_type_is_reported(self):
        body = _body(
            "fitting",
            material_id="hinge",
            surface_top="surface.oil",
        )
        catalog = _FakeCatalog([_FakeCatalogItem("hinge", "hardware", "Hinge")])

        result = _analyze([body], catalog)

        self.assertEqual(result.issue_count, 1)
        self.assertIn("Oberflaeche oben", "\n".join(result.issues_by_body[0][1]))

    def test_non_csv_catalog_field_does_not_block_export_readiness(self):
        body = _body(
            "side",
            material_id="sheet.white",
            trim_allowance_mm="1.0",
        )
        catalog = _FakeCatalog(
            [
                _FakeCatalogItem(
                    "sheet.white",
                    "sheet",
                    "White",
                    properties={"sheet_has_grain": "invalid-non-export-value"},
                )
            ]
        )

        result = _analyze([body], catalog)

        self.assertEqual(result.issue_count, 0)
        self.assertEqual(result.ready_count, 1)


def _body(name, **attrs):
    rows = [
        ("DIYGarageCut.part_metadata", key, value)
        for key, value in attrs.items()
    ]
    return _FakeBody(name, rows)


def _analyze(bodies, catalog):
    targets = [validate_core._BodyAnalysisTarget(body, ["Root"]) for body in bodies]
    return validate_core._analyze_bodies(targets, catalog)


if __name__ == "__main__":
    unittest.main()
