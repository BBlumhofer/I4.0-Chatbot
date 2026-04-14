from dataclasses import dataclass


@dataclass
class Position:
    """ Data class containing position coordinates in meters. """
    x: float
    y: float
    z: float
    unit: str = "mm"


@dataclass
class Orientation:
    """ Data class containing angles coordinates in degrees. """
    a: float
    b: float
    c: float
    unit: str = "°"


