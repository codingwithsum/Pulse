"""
Approximate map centres for the 18 RMC wards.

These are hand-placed centroids near each ward's main landmarks, good enough to
drop a marker in the right neighbourhood. They are NOT official ward boundaries;
swap in RMC's ward GeoJSON when it is available. A non-null latitude/longitude on
CivicLocation always wins over these values.
"""

RAJKOT_CENTER = (22.3039, 70.8022)

WARD_CENTROIDS = {
    1: (22.3350, 70.7650),
    2: (22.3000, 70.7870),
    3: (22.2990, 70.7990),
    4: (22.3250, 70.8000),
    5: (22.3120, 70.8100),
    6: (22.2950, 70.8350),
    7: (22.2960, 70.7800),
    8: (22.2900, 70.7700),
    9: (22.2780, 70.7850),
    10: (22.2700, 70.7650),
    11: (22.2930, 70.7550),
    12: (22.3150, 70.7450),
    13: (22.2930, 70.8000),
    14: (22.2880, 70.8050),
    15: (22.2900, 70.8200),
    16: (22.2700, 70.8300),
    17: (22.2750, 70.8000),
    18: (22.2600, 70.8450),
}


def ward_coords(loc):
    """Return (lat, lng) for a CivicLocation, or None if unknown."""
    if loc.latitude is not None and loc.longitude is not None:
        return float(loc.latitude), float(loc.longitude)
    return WARD_CENTROIDS.get(loc.ward_number)
