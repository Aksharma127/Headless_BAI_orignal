from typing import List, Dict
import logging
import math
try:
    import numpy as np
except Exception:
    np = None
import statistics

logger = logging.getLogger(__name__)


def calculate_spatial_variance(x_coords: List[float], y_coords: List[float]) -> float:
    if not x_coords or not y_coords or len(x_coords) < 2:
        return float('inf')
    try:
        if np is not None:
            vx = float(np.var(np.array(x_coords)))
            vy = float(np.var(np.array(y_coords)))
        else:
            vx = statistics.pvariance(x_coords)
            vy = statistics.pvariance(y_coords)
        return vx + vy
    except Exception as e:
        logger.exception("Failed spatial variance: %s", e)
        return float('inf')


def calculate_temporal_variance(timestamps: List[float]) -> float:
    if not timestamps or len(timestamps) < 3:
        return float('inf')
    try:
        intervals = [t2 - t1 for t1, t2 in zip(timestamps[:-1], timestamps[1:])]
        if len(intervals) < 2:
            return float('inf')
        if np is not None:
            return float(np.var(np.array(intervals)))
        return float(statistics.pvariance(intervals))
    except Exception as e:
        logger.exception("Failed temporal variance: %s", e)
        return float('inf')


def calculate_frequency(timestamps: List[float]) -> float:
    if not timestamps or len(timestamps) < 2:
        return 0.0
    try:
        span_ms = timestamps[-1] - timestamps[0]
        if span_ms <= 0:
            return float('inf')
        seconds = span_ms / 1000.0
        rate = len(timestamps) / seconds
        return rate
    except Exception as e:
        logger.exception("Failed frequency calc: %s", e)
        return 0.0


SPATIAL_VARIANCE_THRESHOLD = 100.0
TEMPORAL_VARIANCE_THRESHOLD = 50.0
FREQUENCY_THRESHOLD = 10.0


def is_bot(session_id: str, clicks: List[Dict]) -> bool:
    """Decide if session is a bot based on spatial variance, temporal variance and click rate.

    clicks: list of dicts with keys 'x','y','t' (t in ms)
    """
    try:
        if not clicks or len(clicks) < 3:
            return False

        x_coords = [c.get('x', 0) for c in clicks]
        y_coords = [c.get('y', 0) for c in clicks]
        timestamps = [c.get('t', 0) for c in clicks]

        spatial = calculate_spatial_variance(x_coords, y_coords)
        temporal = calculate_temporal_variance(timestamps)
        freq = calculate_frequency(timestamps)

        logger.info("Session %s stats: spatial=%.2f temporal=%.2f freq=%.2f", session_id, spatial, temporal, freq)

        if (spatial < SPATIAL_VARIANCE_THRESHOLD) and (temporal < TEMPORAL_VARIANCE_THRESHOLD) and (freq > FREQUENCY_THRESHOLD):
            logger.info("Session %s flagged as bot", session_id)
            return True
        return False
    except Exception as e:
        logger.exception("Bot detection failed for %s: %s", session_id, e)
        return False
