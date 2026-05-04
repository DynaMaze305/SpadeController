"""
    linear model used to either :
    1) find what motor duration is mapped to a target distance
    2) find what motor duration is mapped to a target angle

    values are stored in motion_models.json so they survive restarts and
    can be updated at runtime through the `calibrate` command
"""
import json
import logging
import os

logger = logging.getLogger("motion_models")

# path to the persistent json holding the calibration values
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "motion_models.json")

# fallback values used when the json file is missing
# slope is mm/s, intercept is mm. previous px-domain values were converted
# with mm_per_px = 200/68 ≈ 2.9412 (calibration block was {px=68, mm=200}).
DEFAULTS = {
    "forward":  {"slope": 184.88, "intercept": -17.56},
    "backward": {"slope": 207.79, "intercept": -18.29},
    "positive": {"slope": 201.54, "intercept": -18.9},
    "negative": {"slope": 218.08, "intercept": -16.0},
    "ratio_forward": 1.01,
    "ratio_backward": 1.01,
}

# keys accepted by the calibrate command
LINEAR_KEYS = ("forward", "backward", "positive", "negative")
RATIO_KEYS = ("ratio_forward", "ratio_backward")


class LinearModel:
    def __init__(self, slope: float, intercept: float):
        self.slope = slope
        self.intercept = intercept


# in-memory cache of the json content
_config = None


# write the config to disk in an atomic way
def _save(config: dict) -> None:
    tmp_path = CONFIG_PATH + ".tmp"
    with open(tmp_path, "w") as f:
        json.dump(config, f, indent=2)
    os.replace(tmp_path, CONFIG_PATH)


# read the config from disk, fall back to defaults if missing or broken
def _load() -> dict:
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r") as f:
                return {**DEFAULTS, **json.load(f)}
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to load {CONFIG_PATH}: {e}. Using defaults.")

    # first run: create the file with default values
    config = dict(DEFAULTS)
    try:
        _save(config)
    except OSError as e:
        logger.warning(f"Failed to write defaults to {CONFIG_PATH}: {e}")
    return config


# lazy access to the cached config
def _cfg() -> dict:
    global _config
    if _config is None:
        _config = _load()
    return _config


# return the LinearModel for "forward", "backward", "positive" or "negative"
def get_linear(name: str) -> LinearModel:
    entry = _cfg()[name]
    return LinearModel(entry["slope"], entry["intercept"])


# return the right/left ratio for forward or backward motion
def get_ratio(backward: bool) -> float:
    cfg = _cfg()
    return cfg["ratio_backward"] if backward else cfg["ratio_forward"]


# update one calibration entry and write the json to disk
def update(key: str, values: list) -> str:
    cfg = _cfg()

    # linear models : 2 floats (slope, intercept)
    if key in LINEAR_KEYS:
        if len(values) != 2:
            raise ValueError(f"{key} expects 2 values (slope, intercept), got {len(values)}")
        cfg[key] = {"slope": values[0], "intercept": values[1]}

    # left/right ratios : 1 float
    elif key in RATIO_KEYS:
        if len(values) != 1:
            raise ValueError(f"{key} expects 1 value, got {len(values)}")
        cfg[key] = values[0]

    else:
        raise ValueError(f"unknown calibration key: {key}")

    _save(cfg)
    return f"updated {key} -> {values}"


# linear regression model for distance: model is in mm/s and mm units,
# so we feed distance_mm directly without any pixel conversion
def duration_for_distance(distance_mm: float) -> float:
    model = get_linear("forward" if distance_mm >= 0 else "backward")
    return max(0.0, (abs(distance_mm) - model.intercept) / model.slope)


# linear regression model for angle
def duration_for_angle(angle: float) -> float:
    model = get_linear("positive" if angle >= 0 else "negative")
    return max(0.0, (abs(angle) - model.intercept) / model.slope)