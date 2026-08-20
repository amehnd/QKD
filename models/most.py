"""
most.py

Monin-Obukhov Similarity Theory (MOST)

Computes marine surface layer stability
parameters for maritime optical propagation.

Outputs:

    Friction Velocity

    Monin-Obukhov Length

    Stability Parameter

    Temperature Scale

    Humidity Scale

Used by:

    marine_boundary_layer.py
    evaporation_duct.py
    turbulence.py

Version:
    0.3
"""

import math

from core.model import Model


class MOSTModel(Model):

    name = "MOST"

    description = "Marine atmospheric stability model"

    version = "0.3"

    inputs = [
        "temperature_C",
        "sea_surface_temperature_C",
        "relative_humidity_pct",
        "wind_speed_m_s",
        "pressure_hPa",
    ]

    outputs = [
        "friction_velocity_m_s",
        "monin_obukhov_length_m",
        "stability_parameter",
        "temperature_scale_K",
        "humidity_scale",
    ]

    # --------------------------------------------------
    # Constants
    # --------------------------------------------------

    KAPPA = 0.40

    G = 9.80665

    CP = 1004.67

    RHO_AIR = 1.225

    # --------------------------------------------------
    # Validation
    # --------------------------------------------------

    def validate(self, state):

        if not state.propagation_slices:

            raise ValueError("Adaptive slicing must run before MOST.")

        if state.wind_speed_m_s < 0:

            raise ValueError("Wind speed invalid")

        if state.pressure_hPa <= 0:

            raise ValueError("Pressure invalid")

        return True

    # --------------------------------------------------
    # Execute
    # --------------------------------------------------

    def execute(self, state):

        t_avg = (getattr(state, "tx_temperature_C", getattr(state, "temperature_C", 25.0)) + getattr(state, "rx_temperature_C", getattr(state, "temperature_C", 25.0))) / 2.0
        air_temp = t_avg + 273.15

        sea_temp = state.sea_surface_temperature_C + 273.15

        w_avg = (getattr(state, "tx_wind_speed_m_s", getattr(state, "wind_speed_m_s", 5.0)) + getattr(state, "rx_wind_speed_m_s", getattr(state, "wind_speed_m_s", 5.0))) / 2.0
        wind = max(w_avg, 0.1)

        rh_avg = (getattr(state, "tx_humidity_pct", getattr(state, "relative_humidity_pct", 80.0)) + getattr(state, "rx_humidity_pct", getattr(state, "relative_humidity_pct", 80.0))) / 2.0
        rh = rh_avg

        # ==========================================
        # Drag Coefficient
        #
        # Smith (1980) style approximation
        # ==========================================

        Cd = 1.0e-3 * (0.75 + 0.067 * wind)

        # ==========================================
        # Friction Velocity
        # ==========================================

        u_star = math.sqrt(Cd) * wind

        # ==========================================
        # Temperature Difference
        # ==========================================

        delta_T = sea_temp - air_temp

        # ==========================================
        # Sensible Heat Flux
        # ==========================================

        Ch = 1.2e-3

        heat_flux = self.RHO_AIR * self.CP * Ch * wind * delta_T

        # ==========================================
        # Temperature Scale
        # ==========================================

        if u_star > 0:

            theta_star = -heat_flux / (self.RHO_AIR * self.CP * u_star)

        else:

            theta_star = 0.0

        # ==========================================
        # Humidity Scale
        #
        # Approximation
        # ==========================================

        humidity_scale = rh / 100.0 - 0.80

        # ==========================================
        # Monin-Obukhov Length
        # ==========================================

        denominator = self.KAPPA * self.G * theta_star

        if abs(denominator) < 1e-12:

            L = 1e9

        else:

            L = -(u_star**3) * air_temp / denominator

        # ==========================================
        # Stability Parameter
        #
        # z/L at 10 m
        # ==========================================

        z_ref = 10.0

        if abs(L) > 1e-6:

            zeta = z_ref / L

        else:

            zeta = 0.0

        # ==========================================
        # v0.4 Slice MOST Model
        # ==========================================

        if state.propagation_slices:

            for s in state.propagation_slices:

                local_air = s.temperature_C + 273.15
                local_sea = (
                    getattr(
                        s, "sea_surface_temperature_C", state.sea_surface_temperature_C
                    )
                    + 273.15
                )

                local_wind = max(s.wind_speed_m_s, 0.1)

                local_rh = s.relative_humidity_pct

                # Drag coefficient
                local_Cd = 1.0e-3 * (0.75 + 0.067 * local_wind)
                s.drag_coefficient = local_Cd

                local_u = math.sqrt(local_Cd) * local_wind

                delta_T = local_sea - local_air
                s.air_sea_temperature_difference_C = local_sea - local_air

                heat_flux = self.RHO_AIR * self.CP * 1.2e-3 * local_wind * delta_T
                s.sensible_heat_flux_W_m2 = heat_flux

                if local_u > 0:

                    local_theta = -heat_flux / (self.RHO_AIR * self.CP * local_u)

                else:

                    local_theta = 0.0

                local_humidity = local_rh / 100.0 - 0.80

                denominator = self.KAPPA * self.G * local_theta

                if abs(denominator) < 1e-12:

                    local_L = 1e9

                else:

                    local_L = -(local_u**3) * local_air / denominator

                if abs(local_L) > 1e-6:

                    local_zeta = 10.0 / local_L

                else:

                    local_zeta = 0.0

                s.friction_velocity_m_s = local_u
                s.u_star = local_u
                s.monin_obukhov_length_m = local_L
                s.temperature_scale_K = local_theta
                s.humidity_scale = local_humidity
                s.stability_parameter = local_zeta
                if local_zeta < -0.05:
                    s.stability_regime = "Unstable"

                elif local_zeta > 0.05:
                    s.stability_regime = "Stable"

                else:
                    s.stability_regime = "Neutral"

            n = len(state.propagation_slices)

            rx = state.propagation_slices[-1]

            u_star = rx.friction_velocity_m_s
            L = rx.monin_obukhov_length_m
            theta_star = rx.temperature_scale_K
            humidity_scale = rx.humidity_scale
            zeta = rx.stability_parameter

            print()
            print("===== MOST → SLICES =====")

            for s in state.propagation_slices[:5]:

                print(
                    f"Slice {s.slice_id}: "
                    f"u*={s.friction_velocity_m_s:.3f} "
                    f"L={s.monin_obukhov_length_m:.1f} "
                    f"ζ={s.stability_parameter:.3f} "
                    f"{s.stability_regime}"
                )

        print("=========================")
        print()
        # =====================================
        # PATH AVERAGES
        # =====================================

        state.average_friction_velocity_m_s = sum(
            s.friction_velocity_m_s for s in state.propagation_slices
        ) / max(len(state.propagation_slices), 1)

        state.average_monin_obukhov_length_m = sum(
            s.monin_obukhov_length_m for s in state.propagation_slices
        ) / max(len(state.propagation_slices), 1)

        state.average_stability_parameter = sum(
            s.stability_parameter for s in state.propagation_slices
        ) / max(len(state.propagation_slices), 1)

        state.stable_slices = sum(
            1 for s in state.propagation_slices if s.stability_regime == "Stable"
        )

        state.neutral_slices = sum(
            1 for s in state.propagation_slices if s.stability_regime == "Neutral"
        )

        state.unstable_slices = sum(
            1 for s in state.propagation_slices if s.stability_regime == "Unstable"
        )

        state.sensible_heat_flux_W_m2 = heat_flux
        state.drag_coefficient = Cd
        state.air_sea_temperature_difference_C = delta_T
        state.u_star = u_star

        # ==========================================
        # Save Results
        # ==========================================

        state.friction_velocity_m_s = u_star

        state.monin_obukhov_length_m = L

        state.temperature_scale_K = theta_star

        state.humidity_scale = humidity_scale

        state.stability_parameter = zeta

        state.debug_message = "MOST completed"

        # ==========================================
        # Console Output
        # ==========================================

        print()

        print(f"Wind Speed: " f"{wind:.2f} m/s")

        print(f"Friction Velocity: " f"{u_star:.4f} m/s")

        print(f"Monin-Obukhov Length: " f"{L:.2f} m")

        print(f"Temperature Scale: " f"{theta_star:.4f} K")

        print(f"Humidity Scale: " f"{humidity_scale:.4f}")

        print()
        print("Stable Slices   :", state.stable_slices)
        print("Neutral Slices  :", state.neutral_slices)
        print("Unstable Slices :", state.unstable_slices)
