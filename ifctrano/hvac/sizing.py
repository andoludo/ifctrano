"""Design heat loads for sizing heating components missing from the model.

BIM models rarely carry the output of every radiator or the flow of every
pump. When they do not, emitters are sized for the design heat load of their
space, computed with a simplified EN 12831-1 method:

    load = (sum(A / (R + Rs) * f) + 0.34 * n * V) * (Ti - Te)

with ``A`` and ``R`` the area and thermal resistance of each external boundary
of the space, ``Rs`` the internal and external surface resistances, ``f`` a
temperature correction factor (1 for elements exposed to outdoor air, lower for
floors on ground), ``n`` the air change rate and ``V`` the space volume.
"""

from pydantic import BaseModel, Field
from trano.elements import Space as TranoSpace  # type: ignore
from trano.elements.types import Tilt  # type: ignore

AIR_VOLUMETRIC_HEAT_CAPACITY = 0.34  # Wh/(m3 K), i.e. W per m3/h and K
WATER_SPECIFIC_HEAT_CAPACITY = 4186.0  # J/(kg K)


class DesignConditions(BaseModel):
    """Design conditions used to size components missing from the model."""

    indoor_temperature: float = Field(default=20.0, description="°C")
    outdoor_temperature: float = Field(
        default=-10.0, description="°C, depends on the location of the building"
    )
    air_change_rate: float = Field(default=0.5, description="1/h")
    ground_temperature_factor: float = Field(
        default=0.4, description="Temperature correction factor of floors on ground"
    )
    surface_resistance: float = Field(
        default=0.17, description="m2K/W, internal and external surface resistances"
    )
    supply_temperature: float = Field(default=70.0, description="°C")
    return_temperature: float = Field(default=55.0, description="°C")

    @property
    def temperature_difference(self) -> float:
        return self.indoor_temperature - self.outdoor_temperature

    def water_mass_flow(self, power: float) -> float:
        """Water mass flow rate (kg/s) carrying ``power`` (W) at design temperatures."""
        return power / (
            WATER_SPECIFIC_HEAT_CAPACITY
            * (self.supply_temperature - self.return_temperature)
        )


def design_heat_load(space: TranoSpace, conditions: DesignConditions) -> float:
    """Design heat load of a space in W."""
    transmission = 0.0
    for boundary in space.external_boundaries:
        resistance = (
            boundary.construction.total_thermal_resistance
            + conditions.surface_resistance
        )
        factor = (
            conditions.ground_temperature_factor
            if getattr(boundary, "tilt", None) == Tilt.floor
            else 1.0
        )
        transmission += boundary.surface * factor / resistance
    volume = space.parameters.floor_area * space.parameters.average_room_height
    ventilation = AIR_VOLUMETRIC_HEAT_CAPACITY * conditions.air_change_rate * volume
    return float((transmission + ventilation) * conditions.temperature_difference)
