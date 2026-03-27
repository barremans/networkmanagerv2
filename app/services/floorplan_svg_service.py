# =============================================================================
# Networkmap_Creator
# File:    app/services/floorplan_svg_service.py
# Role:    SVG analyse voor floorplans — detectie van puntlabels + posities
# Version: 1.4.0
# Author:  Barremans
# Changes: 1.4.0 — Correcte positie-detectie voor draw.io SVG:
#                   g elementen met id="M1" etc. bevatten echte SVG coördinaten
#                   _find_svg_g_labels() leest rect/image positie uit g subtree
#                   Geen mxGeometry conversie meer nodig voor draw.io exports
#                   Uniform voor alle draw.io SVG's ongeacht schaal/offset
#          1.3.0 — draw.io mxGeometry parsing (vervangen door 1.4.0 aanpak)
#          1.0.0 — Initiële versie
#
# BELANGRIJK: Geen Qt imports.
# =============================================================================

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path


# ---------------------------------------------------------------------------
# Regex patronen
# ---------------------------------------------------------------------------

# Labels: M1, M2, M12, WO1, WO-1, WP1 — GEEN C-suffix varianten (M1C)
# M1C is het wandcontact-symbool, niet het wandpunt zelf
_POINT_LABEL_RE = re.compile(
    r"^(?:M|WO|WP)\d+$",
    re.IGNORECASE,
)

# Ruimer patroon voor tekst-scan (inclusief C-suffix, later gefilterd)
_TEXT_TOKEN_RE = re.compile(
    r"\b(?:M|WO|WP)[-_]?[A-Z0-9]+\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Publieke API
# ---------------------------------------------------------------------------

def load_svg_text(svg_path: str | Path) -> str:
    path = Path(svg_path)
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            return path.read_text(encoding="utf-8-sig")
        except Exception:
            return ""
    except Exception:
        return ""


def detect_point_labels(svg_path: str | Path) -> list[str]:
    """
    Detecteer wandpuntlabels uit een SVG bestand.
    Ondersteunt draw.io SVG (g[id=M1] elementen) en standaard SVG (<text>).
    """
    path = Path(svg_path)
    if not path.exists() or not path.is_file():
        return []

    labels: set[str] = set()

    try:
        tree = ET.parse(path)
        root = tree.getroot()

        # draw.io SVG: g elementen met label-id EN content attribuut
        if root.get("content"):
            labels.update(_find_svg_g_label_ids(root))
            # Fallback: ook mxCell values scannen
            if not labels:
                labels.update(_extract_drawio_labels_from_content(root))
        else:
            for elem in root.iter():
                labels.update(_extract_candidate_labels_from_element(elem))

    except ET.ParseError:
        raw = load_svg_text(path)
        labels.update(_extract_candidate_labels_from_text(raw))

    return _sort_point_labels(labels)


def detect_point_positions(svg_path: str | Path) -> dict[str, tuple[float, float]]:
    """
    Detecteer wandpuntlabels met hun x/y coördinaten in SVG-ruimte.
    Geeft {label: (x, y)} terug voor overlay plaatsing.

    draw.io SVG:
        Leest de SVG g[id="M1"] elementen direct — echte gerenderde posities.
        Geen coördinatenconversie nodig. Werkt uniform voor alle draw.io exports.

    Standaard SVG:
        Leest <text> x/y attributen met transform-offset.
    """
    path = Path(svg_path)
    if not path.exists() or not path.is_file():
        return {}

    try:
        tree = ET.parse(path)
        root = tree.getroot()

        if root.get("content"):
            return _parse_drawio_svg_positions(root)
        else:
            result: dict[str, tuple[float, float]] = {}
            _collect_svg_text_positions(root, result, 0.0, 0.0)
            return result

    except ET.ParseError:
        return {}


def has_detectable_points(svg_path: str | Path) -> bool:
    return len(detect_point_labels(svg_path)) > 0


# ---------------------------------------------------------------------------
# draw.io SVG — label detectie via g[id] elementen
# ---------------------------------------------------------------------------

def _find_svg_g_label_ids(root: ET.Element) -> set[str]:
    """
    Zoek g elementen met id="M1" etc. in de SVG.
    Draw.io exporteert wandpunten als <g id="M1">...</g>.
    """
    labels: set[str] = set()
    for elem in root.iter():
        tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        if tag == "g":
            eid = elem.get("id", "")
            norm = _normalize_point_label(eid)
            if _is_point_label(norm):
                labels.add(norm)
    return labels


def _extract_drawio_labels_from_content(root: ET.Element) -> set[str]:
    """Fallback: labels uit mxCell value attributen in embedded content."""
    labels: set[str] = set()
    try:
        content = root.get("content", "")
        mx = ET.fromstring(content)
        for cell in mx.iter("mxCell"):
            value = (cell.get("value") or "").strip()
            norm = _normalize_point_label(value)
            if _is_point_label(norm):
                labels.add(norm)
    except Exception:
        pass
    return labels


# ---------------------------------------------------------------------------
# draw.io SVG — positie detectie via g[id] elementen
# ---------------------------------------------------------------------------

def _parse_drawio_svg_positions(root: ET.Element) -> dict[str, tuple[float, float]]:
    """
    Lees posities direct uit de SVG g[id="M1"] elementen.

    Draw.io exporteert elk wandpunt als <g id="M1">...</g> met daarin
    rect/image elementen op de echte SVG coördinaten. Geen conversie nodig.

    Globale translate(0, offset) van de root g wordt meegenomen.
    """
    result: dict[str, tuple[float, float]] = {}

    # Globale translate van de wrapper g
    global_tx, global_ty = _get_global_translate(root)

    for elem in root.iter():
        tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        if tag != "g":
            continue
        eid = elem.get("id", "")
        norm = _normalize_point_label(eid)
        if not _is_point_label(norm):
            continue
        if norm in result:
            continue

        cx, cy = _find_center_from_subtree(elem)
        if cx is not None:
            result[norm] = (cx + global_tx, cy + global_ty)

    return result


def _get_global_translate(root: ET.Element) -> tuple[float, float]:
    """
    Haal de globale translate op van de eerste wrapper g met transform.
    Draw.io voegt typisch translate(0, 0.5) toe als render-offset.
    """
    for elem in root.iter():
        tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        if tag == "g":
            t = elem.get("transform", "")
            if t:
                tx, ty = _parse_transform_offset(t)
                return tx, ty
    return 0.0, 0.0


def _find_center_from_subtree(
    elem: ET.Element,
    depth: int = 0,
) -> tuple[float | None, float | None]:
    """
    Zoek de eerste rect of image in de subtree en geef het centrum terug.
    """
    if depth > 8:
        return None, None

    tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag

    if tag in ("rect", "image"):
        x_str = elem.get("x")
        y_str = elem.get("y")
        if x_str is not None and y_str is not None:
            try:
                x = float(x_str)
                y = float(y_str)
                w = float(elem.get("width", "0") or "0")
                h = float(elem.get("height", "0") or "0")
                return x + w / 2, y + h / 2
            except (ValueError, TypeError):
                pass

    for child in elem:
        cx, cy = _find_center_from_subtree(child, depth + 1)
        if cx is not None:
            return cx, cy

    return None, None


# ---------------------------------------------------------------------------
# Standaard SVG — positie detectie via <text> elementen
# ---------------------------------------------------------------------------

def _collect_svg_text_positions(
    elem: ET.Element,
    result: dict[str, tuple[float, float]],
    offset_x: float,
    offset_y: float,
):
    own_tx, own_ty = _parse_transform_offset(elem.get("transform", ""))
    cx = offset_x + own_tx
    cy = offset_y + own_ty

    tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag

    if tag in ("text", "tspan"):
        raw = "".join(elem.itertext()).strip()
        if " " not in raw:
            label = _normalize_point_label(raw)
            if _is_point_label(label) and label not in result:
                try:
                    x = float(elem.get("x", "0") or "0") + cx
                    y = float(elem.get("y", "0") or "0") + cy
                except (ValueError, TypeError):
                    x, y = cx, cy
                result[label] = (x, y)

    for child in elem:
        _collect_svg_text_positions(child, cx, cy, offset_x, offset_y)


# ---------------------------------------------------------------------------
# Standaard SVG — label detectie via tekstelementen
# ---------------------------------------------------------------------------

def _extract_candidate_labels_from_element(elem: ET.Element) -> set[str]:
    found: set[str] = set()
    text_value = _normalized_text("".join(elem.itertext()))
    if text_value:
        found.update(_extract_candidate_labels_from_text(text_value))
    for attr_name, attr_value in elem.attrib.items():
        attr_name_l = attr_name.lower()
        attr_value_n = _normalized_text(attr_value)
        if not attr_value_n:
            continue
        if (attr_name_l.endswith("id") or attr_name_l.endswith("label")
                or attr_name_l.endswith("name")):
            found.update(_extract_candidate_labels_from_text(attr_value_n))
    return found


def _extract_candidate_labels_from_text(text: str) -> set[str]:
    found: set[str] = set()
    for token in _TEXT_TOKEN_RE.findall(text or ""):
        norm = _normalize_point_label(token)
        if _is_point_label(norm):
            found.add(norm)
    stripped = (text or "").strip()
    if " " not in stripped:
        full = _normalize_point_label(stripped)
        if _is_point_label(full):
            found.add(full)
    return found


# ---------------------------------------------------------------------------
# Normalisatie / validatie / sortering
# ---------------------------------------------------------------------------

def _normalized_text(value: str) -> str:
    if not value:
        return ""
    return " ".join(value.strip().split())


def _normalize_point_label(label: str) -> str:
    if not label:
        return ""
    return label.strip().upper().replace(" ", "").replace("\u2013", "-").replace("\u2014", "-")


def _is_point_label(label: str) -> bool:
    if not label or len(label) < 2:
        return False
    return _POINT_LABEL_RE.match(label) is not None


def _parse_transform_offset(transform: str) -> tuple[float, float]:
    if not transform:
        return 0.0, 0.0
    m = re.search(r"translate\(([^,)]+)(?:,\s*([^)]*))?\)", transform)
    if m:
        try:
            tx = float(m.group(1).strip())
            ty = float(m.group(2).strip()) if m.group(2) and m.group(2).strip() else 0.0
            return tx, ty
        except (ValueError, TypeError):
            pass
    m = re.search(
        r"matrix\(\s*[^,]+,\s*[^,]+,\s*[^,]+,\s*[^,]+,\s*([^,]+),\s*([^)]+)\)",
        transform,
    )
    if m:
        try:
            return float(m.group(1)), float(m.group(2))
        except (ValueError, TypeError):
            pass
    return 0.0, 0.0


def _sort_point_labels(labels: set[str]) -> list[str]:
    return sorted(labels, key=_natural_sort_key)


def _natural_sort_key(label: str):
    parts = re.split(r"(\d+)", label)
    return [int(p) if p.isdigit() else p for p in parts]