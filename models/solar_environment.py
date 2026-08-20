"""
solar_environment.py

Solar Environment Model

Computes:

    Solar Elevation

    Solar Azimuth

    Solar Zenith

    Solar Irradiance

    Day/Night Status

Version:
    0.3
"""

import math
import datetime

from core.model import Model


class SolarEnvironmentModel(Model):

    name = "SolarEnvironment"

    description = "Solar geometry and irradiance model"

    version = "0.3"

    inputs = ["tx_latitude_deg", "tx_longitude_deg", "day_of_year", "local_time_hours"]
    outputs = [
        "solar_elevation_deg",
        "solar_azimuth_deg",
        "solar_azimuth_direction",
        "solar_zenith_deg",
        "solar_flux_W_m2",
        "is_daylight",
    ]

    SOLAR_CONSTANT = 1361.0

    # --------------------------------------------------
    # Validation
    # --------------------------------------------------

    def validate(self, state):

        if not (-90 <= state.tx_latitude_deg <= 90):
            raise ValueError("Latitude must be between -90 and 90")

        if not (-180 <= state.tx_longitude_deg <= 180):

            raise ValueError("Longitude must be between -180 and 180")

        return True

    # --------------------------------------------------
    # Execute
    # --------------------------------------------------

    @staticmethod
    def azimuth_to_direction(azimuth_deg):

        directions = [
            "North",
            "North-East",
            "East",
            "South-East",
            "South",
            "South-West",
            "West",
            "North-West",
        ]

        index = int(((azimuth_deg + 22.5) % 360) // 45)

        return directions[index]

    def execute(self, state):

        lat_rad = math.radians(state.tx_latitude_deg)

        month = state.month

        day = state.day

        year = getattr(state, "year", 2026)

        local_time = state.time_of_day_hr

        longitude = state.tx_longitude_deg

        date = datetime.date(year, month, day)

        day_of_year = date.timetuple().tm_yday
        # ==========================================
        # Solar Declination
        #
        # Cooper approximation
        # ==========================================

        decl_deg = 23.45 * math.sin(math.radians(360.0 * (284 + day_of_year) / 365.0))

        decl_rad = math.radians(decl_deg)

        # ==========================================
        # Hour Angle
        # ==========================================

        # Reference longitude for IST
        standard_meridian = 82.5

        # Longitude correction (4 minutes per degree)
        longitude_correction = (longitude - standard_meridian) / 15.0

        solar_time = local_time + longitude_correction

        hour_angle_deg = 15.0 * (solar_time - 12.0)

        hour_angle_rad = math.radians(hour_angle_deg)

        # ==========================================
        # Solar Elevation
        # ==========================================

        sin_elev = math.sin(lat_rad) * math.sin(decl_rad) + math.cos(
            lat_rad
        ) * math.cos(decl_rad) * math.cos(hour_angle_rad)

        sin_elev = max(-1.0, min(1.0, sin_elev))

        elevation_rad = math.asin(sin_elev)

        elevation_deg = math.degrees(elevation_rad)
        print("\nSOLAR INPUTS")
        print("Latitude =", state.tx_latitude_deg)
        print("Longitude =", state.tx_longitude_deg)
        print("Date =", day, month, year)
        print("Time =", local_time)

        # ==========================================
        # Solar Zenith
        # ==========================================

        zenith_deg = 90.0 - elevation_deg

        # ==========================================
        # Solar Azimuth
        # ==========================================

        cos_az = (math.sin(decl_rad) - math.sin(lat_rad) * math.sin(elevation_rad)) / (
            math.cos(lat_rad) * math.cos(elevation_rad) + 1e-12
        )

        cos_az = max(-1.0, min(1.0, cos_az))

        azimuth_deg = math.degrees(math.acos(cos_az))

        if hour_angle_deg > 0:

            azimuth_deg = 360.0 - azimuth_deg
        azimuth_direction = self.azimuth_to_direction(azimuth_deg)

        # ==========================================
        # Irradiance
        # ==========================================

        if elevation_deg > 0:

            air_mass = 1.0 / max(math.sin(elevation_rad), 0.01)

            atmospheric_transmission = 0.7 ** (air_mass**0.678)

            irradiance = (
                self.SOLAR_CONSTANT * atmospheric_transmission * math.sin(elevation_rad)
            )

        else:

            irradiance = 0.0

        is_daylight = elevation_deg > 0

        # ==========================================
        # Save Results
        # ==========================================

        state.solar_elevation_deg = elevation_deg

        state.solar_azimuth_deg = azimuth_deg
        state.solar_azimuth_direction = azimuth_direction

        state.solar_zenith_deg = zenith_deg

        state.solar_flux_W_m2 = irradiance

        state.is_daylight = is_daylight
        # ======================================
        # v0.4 Propagation Slice Solar Environment
        # ======================================

        if state.propagation_slices:

            n = len(state.propagation_slices)

            for s in state.propagation_slices:

                s.solar_elevation_deg = elevation_deg
                s.solar_azimuth_deg = azimuth_deg
                s.solar_azimuth_direction = azimuth_direction
                s.solar_zenith_deg = zenith_deg
                s.solar_flux_W_m2 = irradiance
                s.is_daylight = is_daylight

            print()
            print("===== SOLAR ENVIRONMENT → SLICES =====")
            print("Slices Updated :", n)
            print("======================================")
            print()

        state.debug_message = "Solar environment completed"

        # ==========================================
        # Console Output
        # ==========================================

        print()

        print(f"Solar Elevation: " f"{elevation_deg:.2f} deg")

        print(f"Solar Azimuth: " f"{azimuth_deg:.2f}° " f"({azimuth_direction})")

        print(f"Solar Zenith: " f"{zenith_deg:.2f} deg")

        print(f"Solar Flux: " f"{irradiance:.2f} W/m²")

        print(f"Daylight: " f"{is_daylight}")

        # ==========================================
        # VERIFIER TEXT GENERATION
        # ==========================================
        state.verifier_text["solar"] = f"""
**Solar Elevation**
δ = 23.45 · sin(360 · (284 + n_day) / 365) = {decl_deg:.2f} deg
h_solar = 15 · (t_solar - 12) = {hour_angle_deg:.2f} deg
θ_elev = arcsin(sin(φ) · sin(δ) + cos(φ) · cos(δ) · cos(h_solar)) = {elevation_deg:.2f} deg

**Solar Azimuth**
θ_az = arccos((sin(δ) - sin(φ) · sin(θ_elev)) / (cos(φ) · cos(θ_elev))) = {azimuth_deg:.2f} deg

**Solar Zenith**
θ_zenith = 90 - θ_elev = {zenith_deg:.2f} deg

**Solar Flux**
AM = 1 / sin(θ_elev)
T_atm = 0.7^(AM^0.678)
E = E_0 · T_atm · sin(θ_elev) = {irradiance:.2f} W/m²

**Daylight**
Daylight = θ_elev > 0 = {is_daylight}

**Sun State**
Sun State = {getattr(state, "sun_state", "Unknown")}

**Solar Azimuth Direction**
Direction = {getattr(state, 'solar_azimuth_direction', '')}
"""
