import adsk.fusion

try:
    from .attributes import _get_entity_token
except ImportError:
    from attributes import _get_entity_token


def _format_body_size(body):
    try:
        bbox = body.boundingBox
        if not bbox:
            return "-"
        dx = abs(bbox.maxPoint.x - bbox.minPoint.x)
        dy = abs(bbox.maxPoint.y - bbox.minPoint.y)
        dz = abs(bbox.maxPoint.z - bbox.minPoint.z)
        dims_mm = sorted([dx * 10.0, dy * 10.0, dz * 10.0], reverse=True)
        return f"{dims_mm[0]:.1f} x {dims_mm[1]:.1f} x {dims_mm[2]:.1f} mm"
    except Exception as exc:
        print(f"Properties: Größe konnte nicht berechnet werden: {exc}")
        return "-"


def _face_belongs_to_body(face, body):
    face_body = adsk.fusion.BRepBody.cast(getattr(face, "body", None))
    if not face_body:
        return False
    native_face_body = adsk.fusion.BRepBody.cast(getattr(face_body, "nativeObject", None))
    native_body = adsk.fusion.BRepBody.cast(getattr(body, "nativeObject", None))
    if face_body is body or face_body is native_body or native_face_body is body or native_face_body is native_body:
        return True
    face_tokens = {
        _get_entity_token(face_body) or "",
        _get_entity_token(native_face_body) or "",
    }
    body_tokens = {
        _get_entity_token(body) or "",
        _get_entity_token(native_body) or "",
    }
    face_tokens.discard("")
    body_tokens.discard("")
    return bool(face_tokens and body_tokens and (face_tokens & body_tokens))


def _detect_top_bottom_faces(body):
    axis_info = _edge_axis_info(body)
    if not axis_info:
        return {}
    best = {}
    faces = getattr(body, "faces", None)
    if not faces:
        return best
    for i in range(faces.count):
        face = adsk.fusion.BRepFace.cast(faces.item(i))
        if not face:
            continue
        normal = _face_normal(face)
        dominant_idx, dominant_value = _dominant_axis(normal)
        if dominant_idx != axis_info["thickness_idx"] or abs(dominant_value) < 0.9:
            continue
        key = "top" if dominant_value >= 0 else "bottom"
        score = abs(dominant_value) + float(getattr(face, "area", 0.0))
        existing = best.get(key)
        if not existing or score > existing[0]:
            best[key] = (score, face)
    return {key: value[1] for key, value in best.items()}


def _detect_canonical_side_faces(body):
    axis_info = _edge_axis_info(body)
    if not axis_info:
        return {}
    best = {}
    faces = getattr(body, "faces", None)
    if not faces:
        return best
    for i in range(faces.count):
        face = adsk.fusion.BRepFace.cast(faces.item(i))
        if not face:
            continue
        key = _canonical_key_for_face(body, face, axis_info)
        if not key:
            continue
        score = abs(_dominant_axis(_face_normal(face))[1]) + float(getattr(face, "area", 0.0))
        existing = best.get(key)
        if not existing or score > existing[0]:
            best[key] = (score, face)
    return {key: value[1] for key, value in best.items()}


def _canonical_key_for_face(body, face, axis_info=None):
    axis_info = axis_info or _edge_axis_info(body)
    if not axis_info:
        return None
    normal = _face_normal(face)
    if normal is None:
        return None
    dominant_idx, dominant_value = _dominant_axis(normal)
    if dominant_idx is None or dominant_idx == axis_info["thickness_idx"]:
        return None
    if abs(dominant_value) < 0.9:
        return None
    if dominant_idx == axis_info["long_idx"]:
        return "long_pos" if dominant_value >= 0 else "long_neg"
    if dominant_idx == axis_info["short_idx"]:
        return "short_pos" if dominant_value >= 0 else "short_neg"
    return None


def _opposite_canonical_key(key):
    mapping = {
        "long_pos": "long_neg",
        "long_neg": "long_pos",
        "short_pos": "short_neg",
        "short_neg": "short_pos",
    }
    return mapping.get(key, "")


def _canonical_key_axis_and_sign(key, axis_info):
    if key.startswith("long_"):
        axis_idx = axis_info["long_idx"]
    else:
        axis_idx = axis_info["short_idx"]
    sign = 1 if key.endswith("_pos") else -1
    return axis_idx, sign


def _axis_vector(axis_idx, sign):
    vec = [0.0, 0.0, 0.0]
    if axis_idx is None or axis_idx < 0 or axis_idx > 2:
        return tuple(vec)
    vec[axis_idx] = 1.0 if sign >= 0 else -1.0
    return tuple(vec)


def _cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _dot(a, b):
    return (a[0] * b[0]) + (a[1] * b[1]) + (a[2] * b[2])


def _edge_axis_info(body):
    try:
        bbox = body.boundingBox
        if not bbox:
            return None
        dx = abs(bbox.maxPoint.x - bbox.minPoint.x)
        dy = abs(bbox.maxPoint.y - bbox.minPoint.y)
        dz = abs(bbox.maxPoint.z - bbox.minPoint.z)
        dims = [dx, dy, dz]
        order = sorted(range(3), key=lambda idx: dims[idx], reverse=True)
        if len(order) < 3:
            return None
        return {
            "long_idx": order[0],
            "short_idx": order[1],
            "thickness_idx": order[2],
        }
    except Exception:
        return None


def _face_normal(face):
    try:
        point = getattr(face, "pointOnFace", None)
        evaluator = getattr(face, "evaluator", None)
        if not point or not evaluator:
            return None
        ok, normal = evaluator.getNormalAtPoint(point)
        if not ok or not normal:
            return None
        return normal
    except Exception:
        return None


def _dominant_axis(vector):
    if vector is None:
        return None, 0.0
    try:
        components = [float(vector.x), float(vector.y), float(vector.z)]
    except Exception:
        return None, 0.0
    idx = max(range(3), key=lambda i: abs(components[i]))
    return idx, components[idx]
