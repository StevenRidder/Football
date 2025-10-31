"""
Adjustment Calibration System

Allows user to multiply all adjustment values by a calibration factor.
This is useful when learned values are too small to generate actionable bets.

Default: 1.0 (use learned values as-is)
Aggressive: 50-100x (amplify tiny signals into actionable edges)
"""

# Global calibration multiplier
# Set this to amplify all adjustments
CALIBRATION_MULTIPLIER = 1.0

def set_calibration_multiplier(multiplier: float):
    """Set the global calibration multiplier."""
    global CALIBRATION_MULTIPLIER
    CALIBRATION_MULTIPLIER = max(0.1, min(1000.0, multiplier))  # Clamp between 0.1x and 1000x
    return CALIBRATION_MULTIPLIER

def get_calibration_multiplier() -> float:
    """Get the current calibration multiplier."""
    return CALIBRATION_MULTIPLIER

def apply_calibration(adjustment: float) -> float:
    """Apply calibration multiplier to an adjustment value."""
    return adjustment * CALIBRATION_MULTIPLIER

