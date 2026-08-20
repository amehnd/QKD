from pydantic import BaseModel


class SimulationInput(BaseModel):

    link_distance_km: float = 10.0
    wavelength_nm: float = 1550.0
    visibility_km: float = 10.0
    humidity_pct: float = 80.0
