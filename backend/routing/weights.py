from dataclasses import dataclass
from typing import Dict

@dataclass
class RouteWeights:
    """Scoring weights for a route request. All values between 0.0 and 1.0."""
    safety: float = 0.5
    accessibility: float = 0.5
    environment: float = 0.5
    comfort: float = 0.5

    def validate(self):
        for name, val in self.__dict__.items():
            if not (0.0 <= val <= 1.0):
                raise ValueError(f'Weight {name}={val} must be between 0.0 and 1.0')

    @classmethod
    def from_dict(cls, d: Dict) -> 'RouteWeights':
        """Build from a dict, clamping all values to [0, 1]."""
        return cls(
            safety        = max(0.0, min(1.0, float(d.get('safety', 0.5)))),
            accessibility = max(0.0, min(1.0, float(d.get('accessibility', 0.5)))),
            environment   = max(0.0, min(1.0, float(d.get('environment', 0.5)))),
            comfort       = max(0.0, min(1.0, float(d.get('comfort', 0.5)))),
        )

PRESETS = {
    'default':     RouteWeights(0.5, 0.5, 0.5, 0.5),
    'safer':       RouteWeights(safety=0.9, accessibility=0.6, environment=0.4, comfort=0.6),
    'accessible':  RouteWeights(safety=0.7, accessibility=0.95, environment=0.4, comfort=0.8),
    'greener':     RouteWeights(safety=0.5, accessibility=0.5, environment=0.95, comfort=0.6),
    'comfortable': RouteWeights(safety=0.5, accessibility=0.6, environment=0.5, comfort=0.9),
}