"""
weather.py

Weather preprocessing model.

Calculates:

1. Saturation vapor pressure
2. Actual vapor pressure
3. Water vapor density
4. Air density
5. Dew point
6. Visibility quality factor
7. Rain attenuation estimate

Author:
    Maritime QKD Simulator

Version:
    0.3
"""

import math

from core.model import Model


class WeatherModel(Model):

    name = "Weather"

    description = "Weather preprocessing model"

    version = "0.4"

    inputs = [
        "tx_temperature_C",
        "rx_temperature_C",
        "tx_humidity_pct",
        "rx_humidity_pct",
        "tx_pressure_hPa",
        "rx_pressure_hPa",
        "tx_visibility_km",
        "rx_visibility_km",
        "tx_wind_speed_m_s",
        "rx_wind_speed_m_s",
        "tx_rain_rate_mm_hr",
        "rx_rain_rate_mm_hr",
        "time_of_day_hr",
    ]

    outputs = [
        "saturation_vapor_pressure_hPa",
        "vapor_pressure_hPa",
        "dew_point_C",
        "air_density_kg_m3",
        "water_vapor_density_g_m3",
        "visibility_quality_factor",
        "rain_loss_dB_km",
    ]

    # --------------------------------------------------
    # Validation
    # --------------------------------------------------

    def validate(self, state):
        if not state.propagation_slices:
            raise ValueError("Adaptive slicing must run before Weather.")

        return True

    # --------------------------------------------------
    # Execute
    # --------------------------------------------------

    def execute(self, state):

        # =====================================
        # COPY WEATHER TO PROPAGATION SLICES (v0.4)
        # =====================================

        if state.propagation_slices:

            for s in state.propagation_slices:
                print(
                    f"Slice {s.slice_id}: "
                    f"Height={s.beam_height_m:.2f} "
                    f"Ground={s.ground_height_m:.2f} "
                    f"Beam={s.beam_height_m:.2f} "
                    f"Temp={s.temperature_C:.2f} "
                    f"RH={s.humidity_pct:.2f} "
                    f"P={s.pressure_hPa:.2f}"
                )
                base_T = s.temperature_C

                base_RH = s.humidity_pct

                base_P = s.pressure_hPa

                base_VIS = s.visibility_km
                print(f"Slice {s.slice_id}: visibility = {base_VIS}")

                base_wind = s.wind_speed_m_s

                base_RAIN = s.rain_rate_mm_hr

                # =====================================
                # Weather model only copies/interpolates
                # user-defined weather conditions.
                # Any vertical atmospheric variation is
                # computed later by Marine Boundary Layer,
                # MOST, or Refractivity models.
                # =====================================

                slice_T = base_T

                slice_RH = max(0.0, min(100.0, base_RH))

                slice_P = base_P

                slice_VIS = base_VIS

                slice_wind = base_wind
                # Save weather into slice
                s.temperature_C = slice_T
                s.temperature_K = slice_T + 273.15
                s.humidity_pct = max(0.0, min(100.0, slice_RH))

                s.relative_humidity_pct = s.humidity_pct
                s.pressure_hPa = slice_P
                s.visibility_km = slice_VIS
                s.wind_speed_m_s = slice_wind
                s.rain_rate_mm_hr = base_RAIN
                fraction = s.center_m / max(state.link_distance_km * 1000.0, 1.0)

                s.cloud_base_height_m = state.tx_cloud_base_height_m + fraction * (
                    state.rx_cloud_base_height_m - state.tx_cloud_base_height_m
                )
                s.aerosol_alpha = state.tx_aerosol_alpha + fraction * (
                    state.rx_aerosol_alpha - state.tx_aerosol_alpha
                )
                s.cloud_cover_percent = state.tx_cloud_cover_percent + fraction * (
                    state.rx_cloud_cover_percent - state.tx_cloud_cover_percent
                )
                slice_es = 6.112 * math.exp((17.67 * slice_T) / (slice_T + 243.5))

                slice_e = (slice_RH / 100.0) * slice_es
                s.saturation_vapor_pressure_hPa = slice_es
                s.vapor_pressure_hPa = slice_e

                gamma = math.log(max(slice_RH, 1e-6) / 100.0) + (17.67 * slice_T) / (
                    243.5 + slice_T
                )

                slice_dew = (243.5 * gamma) / (17.67 - gamma)

                slice_temp_K = slice_T + 273.15

                slice_density = (slice_P * 100.0) / (287.05 * slice_temp_K)

                slice_vapor_density = 216.7 * slice_e / slice_temp_K

                s.dew_point_C = slice_dew
                s.air_density_kg_m3 = slice_density
                s.water_vapor_density_g_m3 = slice_vapor_density

                s.visibility_quality_factor = min(slice_VIS / 20.0, 1.0)
                if base_RAIN <= 0:
                    s.rain_loss_dB_km = 0.0
                else:
                    s.rain_loss_dB_km = 1.076 * (base_RAIN**0.67)
                s.atmosphere_complete = True

                slice_N = 77.6 * slice_P / slice_temp_K + 3.73e5 * slice_e / (
                    slice_temp_K**2
                )

                s.surface_refractivity_N = slice_N
                s.refractivity_gradient_N_km = -39.0 * (1.0 + slice_RH / 100.0)

                s.sea_state = state.sea_state
                s.wave_height_m = state.wave_height_m
                s.notes = (
                    f"T={slice_T:.1f}°C, "
                    f"RH={slice_RH:.1f}%, "
                    f"P={slice_P:.1f} hPa"
                )
            # Store effective path averages on state using non-legacy attribute names
            state.effective_path_temperature_C = sum(
                s.temperature_C for s in state.propagation_slices
            ) / len(state.propagation_slices)

            state.effective_path_humidity_pct = sum(
                s.humidity_pct for s in state.propagation_slices
            ) / len(state.propagation_slices)

            state.effective_path_pressure_hPa = sum(
                s.pressure_hPa for s in state.propagation_slices
            ) / len(state.propagation_slices)

            state.effective_path_visibility_km = sum(
                s.visibility_km for s in state.propagation_slices
            ) / len(state.propagation_slices)

            state.effective_path_wind_speed_m_s = sum(
                s.wind_speed_m_s for s in state.propagation_slices
            ) / len(state.propagation_slices)

            state.effective_path_rain_rate_mm_hr = sum(
                s.rain_rate_mm_hr for s in state.propagation_slices
            ) / len(state.propagation_slices)

            state.effective_path_cloud_base_height_m = sum(
                s.cloud_base_height_m for s in state.propagation_slices
            ) / len(state.propagation_slices)

            state.effective_path_aerosol_alpha = sum(
                s.aerosol_alpha for s in state.propagation_slices
            ) / len(state.propagation_slices)

            state.dew_point_C = sum(
                s.dew_point_C for s in state.propagation_slices
            ) / len(state.propagation_slices)

            state.air_density_kg_m3 = sum(
                s.air_density_kg_m3 for s in state.propagation_slices
            ) / len(state.propagation_slices)

            state.water_vapor_density_g_m3 = sum(
                s.water_vapor_density_g_m3 for s in state.propagation_slices
            ) / len(state.propagation_slices)

            state.visibility_quality_factor = sum(
                s.visibility_quality_factor for s in state.propagation_slices
            ) / len(state.propagation_slices)

            state.rain_loss_dB_km = sum(
                s.rain_loss_dB_km for s in state.propagation_slices
            ) / len(state.propagation_slices)

            state.surface_refractivity_N = sum(
                s.surface_refractivity_N for s in state.propagation_slices
            ) / len(state.propagation_slices)

            state.refractivity_gradient_N_km = sum(
                s.refractivity_gradient_N_km for s in state.propagation_slices
            ) / len(state.propagation_slices)

            state.atmosphere_complete = True
            state.debug_message = "Weather completed"

            print()
            print("===== WEATHER → SLICES =====")
            print("Slices Updated :", len(state.propagation_slices))
            print("============================")
            print()
