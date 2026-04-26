"""
    linear model used to either :
    1) find what motor duration is mapped to a target distance
    2) find what motor duration is mapped to a target angle
"""


class LinearModel:
    def __init__(self, slope: float, intercept: float):
        self.slope = slope
        self.intercept = intercept


# ---- MEASURED VALUES ---- #

# Camera calibration (px to mm)
CALIBRATION_MM = 200.0
CALIBRATION_PX = 68.00
PX_PER_MM = CALIBRATION_PX / (CALIBRATION_MM)

# Distance model: y_pixels = slope * x_seconds + intercept
FORWARD_MODEL = LinearModel(62.86, -5.97)
BACKWARD_MODEL = LinearModel(70.65, -6.22)

# Rotation model: y_degrees = slope * x_seconds + intercept
POSITIVE_MODEL = LinearModel(244.8, -17.6)
NEGATIVE_MODEL = LinearModel(241.2, -19.3)

# ---- UTILS FUNCTIONS ---- #

# linear regression model for distance
def duration_for_distance(distance_mm: float) -> float:
    pixels = abs(distance_mm) * PX_PER_MM
    model = FORWARD_MODEL if distance_mm >= 0 else BACKWARD_MODEL
    return max(0.0, (pixels - model.intercept) / model.slope)

# linear regression model for angle
def duration_for_angle(angle: float) -> float:
    model = POSITIVE_MODEL if angle >= 0 else NEGATIVE_MODEL
    return max(0.0, (abs(angle) - model.intercept) / model.slope)