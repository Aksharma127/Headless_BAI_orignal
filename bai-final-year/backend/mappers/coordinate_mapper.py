from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)


STANDARD_W = 1920
STANDARD_H = 1080


def normalize_coordinates(x: float, y: float, viewport_w: int, viewport_h: int) -> Optional[tuple]:
    if viewport_w <= 0 or viewport_h <= 0:
        logger.warning("Invalid viewport %s x %s", viewport_w, viewport_h)
        return None
    try:
        scale_x = STANDARD_W / float(viewport_w)
        scale_y = STANDARD_H / float(viewport_h)
        return (x * scale_x, y * scale_y)
    except Exception as e:
        logger.exception("Normalization failed: %s", e)
        return None


def point_in_box(x: float, y: float, box: Dict) -> bool:
    try:
        return (x >= box['x_min']) and (x <= box['x_max']) and (y >= box['y_min']) and (y <= box['y_max'])
    except Exception:
        return False


def map_click_to_section(x: float, y: float, viewport_w: int, viewport_h: int, skeleton: Dict) -> Optional[str]:
    if not skeleton:
        return None
    norm = normalize_coordinates(x, y, viewport_w, viewport_h)
    if norm is None:
        return None
    x_norm, y_norm = norm
    for section_id, box in skeleton.items():
        if point_in_box(x_norm, y_norm, box):
            return section_id
    return None
