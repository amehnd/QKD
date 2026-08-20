"""
evaporation_duct.py

Marine Evaporation Duct Model

Computes:

    Evaporation Duct Height

    Modified Refractivity Profile

    Duct Strength

    Super Refraction

    Effective Earth Radius Factor

Based on:

    NPS style evaporation duct
    Paulus-Jeske approximation

Used by:

    refractivity.py
    chromatic_refraction.py
    raytrace.py (future)

Version:
    0.3
"""

import math


from core.model import Model


class EvaporationDuctModel(Model):

    name = "EvaporationDuct"

    description = "Marine evaporation duct model"

    version = "0.3"

    inputs = [
        "sea_surface_temperature_C",
        "propagation_slices",
    ]

    outputs = [
        "duct_height_m",
        "duct_strength",
        "m_deficit",
        "super_refraction",
        "effective_earth_radius_factor",
    ]

    # --------------------------------------------------
    # Validation
    # --------------------------------------------------

    def validate(self, state):

        if not state.propagation_slices:

            raise ValueError("Marine Boundary Layer must run before Evaporation Duct.")

        if state.wind_speed_m_s < 0:

            raise ValueError("Wind speed invalid")

        return True

    # --------------------------------------------------
    # Execute
    # --------------------------------------------------

    def execute(self, state):
        t_tx = getattr(state, "tx_temperature_C", getattr(state, "temperature_C", 25.0))
        t_rx = getattr(state, "rx_temperature_C", getattr(state, "temperature_C", 25.0))
        air_temp = (t_tx + t_rx) / 2.0

        sea_temp = state.sea_surface_temperature_C

        rh_tx = getattr(state, "tx_humidity_pct", getattr(state, "relative_humidity_pct", 80.0))
        rh_rx = getattr(state, "rx_humidity_pct", getattr(state, "relative_humidity_pct", 80.0))
        rh = (rh_tx + rh_rx) / 2.0

        w_tx = getattr(state, "tx_wind_speed_m_s", getattr(state, "wind_speed_m_s", 5.0))
        w_rx = getattr(state, "rx_wind_speed_m_s", getattr(state, "wind_speed_m_s", 5.0))
        wind = max((w_tx + w_rx) / 2.0, 0.1)

        gradient = state.refractivity_gradient_N_km

        zeta = state.stability_parameter

        # ==========================================
        # Air-Sea Temperature Difference
        # ==========================================

        delta_t = sea_temp - air_temp

        # ==========================================
        # Duct Height Approximation
        #
        # Engineering NPS approximation
        # ==========================================

        duct_height = 12.0 + 1.5 * delta_t + 0.05 * rh - 0.7 * wind

        dew_point_C = state.dew_point_C

        water_vapor_density_g_m3 = state.water_vapor_density_g_m3

        # Stability correction

        if zeta < 0:

            duct_height *= 1.2

        else:

            duct_height *= 0.8

        # ==========================================
        # Land / Sea Effect
        # ==========================================

        sea_fraction = getattr(state, "sea_percentage", 100.0) / 100.0
        land_fraction = getattr(state, "land_percentage", 0.0) / 100.0

        # Evaporation ducts are strongest over sea
        # Weakest over land

        surface_factor = 1.0 * sea_fraction + 0.5 * land_fraction

        duct_height *= surface_factor

        duct_height = max(1.0, min(duct_height, 40.0))

        # ==========================================
        # Modified Refractivity Deficit
        #
        # Approximation
        # ==========================================

        m_deficit = abs(gradient) * duct_height / 1000.0

        # ==========================================
        # Duct Strength Classification
        # ==========================================

        if m_deficit < 1:

            duct_strength = 0.0

        elif m_deficit < 5:

            duct_strength = 1.0

        elif m_deficit < 10:

            duct_strength = 2.0

        else:

            duct_strength = 3.0

        # ==========================================
        # Super Refraction Check
        # ==========================================

        super_refraction = gradient < -79.0

        # ==========================================
        # Effective Earth Radius Factor
        #
        # Standard atmosphere:
        # k = 4/3
        # ==========================================

        if gradient >= -79:

            k_factor = 4.0 / 3.0

        else:

            denom = max(157.0 + gradient, 1.0)

            k_factor = 157.0 / denom

        k_factor = max(0.5, min(k_factor, 20.0))
        # ==========================================
        # Build M Profile
        #
        # Future ray tracing support
        # ==========================================

        profile_heights = []

        modified_refractivity = []

        max_height = max(50.0, duct_height * 3.0)

        z = 0.0

        while z <= max_height:

            M = state.surface_refractivity_N + 0.157 * z + gradient * z / 1000.0

            if z < duct_height:

                M -= m_deficit * math.exp(-z / max(duct_height, 1.0))

            profile_heights.append(z)

            modified_refractivity.append(M)

            z += 1.0

        # ==========================================
        # Save Results
        # ==========================================

        state.duct_height_m = duct_height

        state.m_deficit = m_deficit

        state.duct_strength = duct_strength

        state.water_vapor_density_g_m3 = water_vapor_density_g_m3
        state.super_refraction = super_refraction

        state.effective_earth_radius_factor = k_factor

        state.modified_refractivity_profile_M = modified_refractivity

        state.modified_refractivity_heights_m = profile_heights

        state.debug_message = "Evaporation duct completed"
        # =====================================
        # COPY EVAPORATION DUCT TO SLICES (v0.4)
        # =====================================

        if state.propagation_slices:

            for s in state.propagation_slices:

                air_temp = s.temperature_C

                sea_temp = getattr(
                    s, "sea_surface_temperature_C", state.sea_surface_temperature_C
                )

                rh = s.relative_humidity_pct

                wind = max(s.wind_speed_m_s, 0.1)

                gradient = getattr(
                    s, "refractivity_gradient_N_km", state.refractivity_gradient_N_km
                )
                zeta = getattr(s, "stability_parameter", state.stability_parameter)

                delta_t = sea_temp - air_temp

                duct = 12.0 + 1.5 * delta_t + 0.05 * rh - 0.7 * wind

                if zeta < 0:

                    duct *= 1.2

                else:

                    duct *= 0.8

                if s.is_sea:
                    surface_factor = 1.0

                elif s.coastal:
                    surface_factor = 0.75

                else:
                    surface_factor = 0.5
                duct *= surface_factor

                duct = max(1.0, min(duct, 40.0))

                m_deficit = abs(gradient) * duct / 1000.0

                if m_deficit < 1:

                    strength = 0.0

                elif m_deficit < 5:

                    strength = 1.0

                elif m_deficit < 10:

                    strength = 2.0

                else:

                    strength = 3.0

                super_refraction = gradient < -79.0

                if gradient >= -79:

                    k = 4.0 / 3.0

                else:

                    denom = max(157.0 + gradient, 1.0)

                    k = 157.0 / denom

                k = max(0.5, min(k, 20.0))

                local_height = max(
                    getattr(s, "height_above_surface_m", s.beam_height_m), 0.0
                )

                decay = math.exp(-local_height / max(duct, 1.0))
                s.duct_decay_factor = decay
                s.duct_decay = decay

                s.modified_refractivity_M = (
                    s.surface_refractivity_N
                    + 0.157 * local_height
                    + gradient * local_height / 1000.0
                    - m_deficit * decay
                )

                s.duct_height_m = duct
                s.m_deficit = m_deficit
                s.modified_refractivity_deficit = m_deficit
                s.duct_strength = strength
                s.super_refraction = super_refraction
                s.effective_earth_radius_factor = k
                s.sea_surface_temperature_C = sea_temp
                s.surface_factor = surface_factor

                s.notes = f"Duct={duct:.1f} m, " f"M={s.modified_refractivity_M:.2f}"
            state.average_duct_height_m = sum(
                s.duct_height_m for s in state.propagation_slices
            ) / max(len(state.propagation_slices), 1)

            state.average_modified_refractivity_M = sum(
                s.modified_refractivity_M for s in state.propagation_slices
            ) / max(len(state.propagation_slices), 1)

            state.average_effective_earth_radius_factor = sum(
                s.effective_earth_radius_factor for s in state.propagation_slices
            ) / max(len(state.propagation_slices), 1)
            state.duct_height_m = state.average_duct_height_m

            state.modified_refractivity_M = state.average_modified_refractivity_M

            state.effective_earth_radius_factor = (
                state.average_effective_earth_radius_factor
            )
            print()

            print("===== EVAP DUCT → SLICES =====")

            for s in state.propagation_slices[:5]:

                print(
                    f"Slice {s.slice_id}: "
                    f"Duct={s.duct_height_m:.2f} m  "
                    f"M={s.modified_refractivity_M:.2f}  "
                    f"k={s.effective_earth_radius_factor:.2f}"
                )

            print("==============================")
            print()
        # ==========================================
        # Console Output
        # ==========================================
        print()
        print("LAND / SEA EFFECT")
        print("------------------")
        print("Land % =", state.land_percentage)
        print("Sea %  =", state.sea_percentage)
        print("Surface Factor =", surface_factor)

        print()

        print(f"Duct Height: " f"{duct_height:.2f} m")

        print(f"M Deficit: " f"{m_deficit:.2f}")

        print(f"Duct Strength: " f"{duct_strength:.1f}")

        print(f"Super Refraction: " f"{super_refraction}")

        print(f"Effective Earth Radius k: " f"{k_factor:.3f}")
