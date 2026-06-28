import adsk.core
import adsk.fusion

try:
    from .attributes import _resolve_attr_target
    from .constants import *
    from .edge_surface_model import has_any_surface_value
    from .geometry import _detect_canonical_side_faces, _detect_top_bottom_faces
except ImportError:
    from attributes import _resolve_attr_target
    from constants import *
    from edge_surface_model import has_any_surface_value
    from geometry import _detect_canonical_side_faces, _detect_top_bottom_faces


def _find_appearance_by_name(name):
    app = adsk.core.Application.get()
    if not app:
        raise RuntimeError("Fusion Application nicht verfügbar.")

    wanted = str(name or "").strip().lower()
    if not wanted:
        return None

    def _scan(appearances):
        if not appearances:
            return None
        for idx in range(appearances.count):
            candidate = appearances.item(idx)
            candidate_name = str(getattr(candidate, "name", "") or "").strip().lower()
            if candidate_name == wanted:
                return candidate
        return None

    design = adsk.fusion.Design.cast(app.activeProduct) if app else None
    found = _scan(getattr(design, "appearances", None) if design else None)
    if found:
        return found

    libraries = getattr(app, "materialLibraries", None)
    if not libraries:
        return None
    for li in range(libraries.count):
        library = libraries.item(li)
        found = _scan(getattr(library, "appearances", None))
        if found:
            return found
    return None


def _apply_face_appearance_or_raise(face, appearance, error_prefix):
    try:
        face.appearance = appearance
    except Exception as exc:
        raise RuntimeError(f"{error_prefix}: {exc}") from exc


def _apply_material_appearance_or_raise(body, material_id, material_by_id):
    entry = material_by_id.get(material_id)
    if not entry:
        raise RuntimeError(f"Material '{material_id}' ist nicht im Katalog vorhanden.")

    appearance = _find_appearance_by_name(entry.appearance_name)
    if not appearance:
        raise RuntimeError(
            f"Appearance '{entry.appearance_name}' aus Material '{material_id}' wurde in Fusion nicht gefunden."
        )

    target = _resolve_attr_target(body)
    if not target:
        raise RuntimeError("Body für Appearance-Zuweisung nicht verfügbar.")
    try:
        target.appearance = appearance
    except Exception as exc:
        raise RuntimeError(f"Appearance konnte nicht gesetzt werden: {exc}") from exc


class AppearanceApplier:
    def __init__(self, material_by_id, edge_by_id, surface_by_id, get_attr):
        self._material_by_id = material_by_id
        self._edge_by_id = edge_by_id
        self._surface_by_id = surface_by_id
        self._get_attr = get_attr

    def apply_edge_appearance_from_resolved_faces(self, body, side_faces, edge_values):
        attr_to_side = {
            ATTR_KEY_EDGE_FRONT: "front",
            ATTR_KEY_EDGE_BACK: "back",
            ATTR_KEY_EDGE_LEFT: "left",
            ATTR_KEY_EDGE_RIGHT: "right",
        }
        base_appearance = self.body_material_appearance(body)
        for attr_key, side in attr_to_side.items():
            face = side_faces.get(side)
            if not face:
                continue
            edge_id = str(edge_values.get(attr_key, "") or "").strip()
            if not edge_id or edge_id == CUSTOM_TEXT_VALUE:
                _apply_face_appearance_or_raise(
                    face, base_appearance, "Kanten-Appearance konnte nicht zurückgesetzt werden"
                )
                continue
            edge_entry = self._edge_by_id.get(edge_id)
            if not edge_entry:
                raise RuntimeError(f"Kantenmaterial '{edge_id}' ist nicht im Katalog vorhanden.")
            appearance = _find_appearance_by_name(edge_entry.appearance_name)
            if not appearance:
                raise RuntimeError(
                    f"Appearance '{edge_entry.appearance_name}' aus Kantenmaterial '{edge_id}' wurde nicht gefunden."
                )
            try:
                face.appearance = appearance
            except Exception as exc:
                raise RuntimeError(f"Kanten-Appearance konnte nicht gesetzt werden: {exc}") from exc

    def reset_canonical_side_face_appearances(self, body):
        appearance = self.body_material_appearance(body)
        for face in _detect_canonical_side_faces(body).values():
            _apply_face_appearance_or_raise(
                face, appearance, "Kanten-Appearance konnte nicht zurückgesetzt werden"
            )

    def apply_surface_appearance_from_body_faces(
        self, body, surface_values, include_edges=False, allow_missing_empty_faces=False
    ):
        face_map = _detect_top_bottom_faces(body)
        base_appearance = self.body_material_appearance(body)
        has_surface_value = has_any_surface_value(surface_values)
        mapping = {
            ATTR_KEY_SURFACE_TOP: "top",
            ATTR_KEY_SURFACE_BOTTOM: "bottom",
        }
        for attr_key, face_key in mapping.items():
            surface_id = str(surface_values.get(attr_key, "") or "").strip()
            face = face_map.get(face_key)
            if not face:
                if allow_missing_empty_faces and not has_surface_value:
                    continue
                raise RuntimeError(f"Fläche für Oberfläche '{face_key}' konnte nicht bestimmt werden.")
            if not surface_id or surface_id == CUSTOM_TEXT_VALUE:
                _apply_face_appearance_or_raise(
                    face, base_appearance, "Oberflächen-Appearance konnte nicht zurückgesetzt werden"
                )
                continue
            surface_entry = self._surface_by_id.get(surface_id)
            if not surface_entry:
                raise RuntimeError(f"Oberfläche '{surface_id}' ist nicht im Katalog vorhanden.")
            appearance = _find_appearance_by_name(surface_entry.appearance_name)
            if not appearance:
                raise RuntimeError(
                    f"Appearance '{surface_entry.appearance_name}' aus Oberfläche '{surface_id}' wurde nicht gefunden."
                )
            _apply_face_appearance_or_raise(face, appearance, "Oberflächen-Appearance konnte nicht gesetzt werden")

        if include_edges:
            all_surface_id = str(surface_values.get(ATTR_KEY_SURFACE_TOP, "") or "").strip()
            appearance = self.surface_appearance_or_base(all_surface_id, base_appearance)
            for face in _detect_canonical_side_faces(body).values():
                _apply_face_appearance_or_raise(
                    face, appearance, "Kanten-Oberflächen-Appearance konnte nicht gesetzt werden"
                )

    def apply_global_surface_appearance_to_body_faces(self, body, surface_values):
        surface_id = str((surface_values or {}).get(ATTR_KEY_SURFACE_TOP, "") or "").strip()
        if not surface_id:
            surface_id = str((surface_values or {}).get(ATTR_KEY_SURFACE_BOTTOM, "") or "").strip()
        appearance = self.surface_appearance_or_base(surface_id, self.body_material_appearance(body))
        faces = getattr(body, "faces", None)
        if not faces:
            raise RuntimeError("Globale Oberfläche konnte nicht gesetzt werden: Body hat keine Faces.")
        for index in range(faces.count):
            face = adsk.fusion.BRepFace.cast(faces.item(index))
            if face:
                _apply_face_appearance_or_raise(
                    face, appearance, "Globale Oberflächen-Appearance konnte nicht gesetzt werden"
                )

    def surface_appearance_or_base(self, surface_id, base_appearance):
        if not surface_id or surface_id == CUSTOM_TEXT_VALUE:
            return base_appearance
        surface_entry = self._surface_by_id.get(surface_id)
        if not surface_entry:
            raise RuntimeError(f"Oberfläche '{surface_id}' ist nicht im Katalog vorhanden.")
        appearance = _find_appearance_by_name(surface_entry.appearance_name)
        if not appearance:
            raise RuntimeError(
                f"Appearance '{surface_entry.appearance_name}' aus Oberfläche '{surface_id}' wurde nicht gefunden."
            )
        return appearance

    def body_material_appearance(self, body):
        material_id = str(self._get_attr(body, ATTR_KEY_MATERIAL_ID, "") or "").strip()
        entry = self._material_by_id.get(material_id)
        if entry and entry.appearance_name:
            appearance = _find_appearance_by_name(entry.appearance_name)
            if appearance:
                return appearance
        try:
            target = _resolve_attr_target(body)
            appearance = getattr(target, "appearance", None) if target else None
            if appearance:
                return appearance
        except Exception:
            pass
        raise RuntimeError("Material-Appearance zum Zurücksetzen der Oberfläche wurde nicht gefunden.")
