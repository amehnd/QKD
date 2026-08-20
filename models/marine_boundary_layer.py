"""
marine_boundary_layer.py

Marine Boundary Layer Model

Computes vertical atmospheric profiles
above the sea surface using MOST outputs.

Outputs:

    Temperature profile

    Humidity profile

    Pressure profile

    Surface refractivity

    Refractivity gradient

    Initial Cn² estimate

Version:
    0.3
"""

import math


from core.model import Model


class MarineBoundaryLayerModel(Model):

    name = "MarineBoundaryLayer"

    description = "Marine boundary layer profile model"

    version = "0.3"

    inputs = [
        "propagation_slices",
        "marine_BL_height_m",
        "temperature_scale_K",
        "humidity_scale",
    ]

    outputs = ["surface_refractivity_N", "refractivity_gradient_N_km", "Cn2_m2_3"]

    # --------------------------------------------------
    # Constants
    # --------------------------------------------------

    G = 9.80665

    RD = 287.05

    LAPSE_RATE = 0.0065

    # --------------------------------------------------
    # Validation
    # --------------------------------------------------

    def validate(self, state):

        if not state.propagation_slices:

            raise ValueError("Adaptive slicing must run before MarineBoundaryLayer.")

        if state.marine_BL_height_m <= 0:

            raise ValueError("Marine boundary layer height invalid")

        return True

    # --------------------------------------------------
    # Saturation Vapor Pressure
    # --------------------------------------------------

    def saturation_vapor_pressure(self, T_C):

        return 6.112 * math.exp((17.67 * T_C) / (T_C + 243.5))

    # --------------------------------------------------
    # Refractivity
    # --------------------------------------------------

    def refractivity(self, P_hPa, T_K, e_hPa):

        return 77.6 * (P_hPa / T_K) + 3.73e5 * (e_hPa / (T_K**2))

    # --------------------------------------------------
    # Execute
    # --------------------------------------------------

    def execute(self, state):

        T0_C = (state.tx_temperature_C + state.rx_temperature_C) / 2.0
        RH0 = (state.tx_humidity_pct + state.rx_humidity_pct) / 2.0
        P0 = (state.tx_pressure_hPa + state.rx_pressure_hPa) / 2.0

        H = state.marine_BL_height_m

        theta_star = state.temperature_scale_K

        humidity_scale = state.humidity_scale

        zeta = state.stability_parameter

        # ==========================================
        # Build Vertical Profiles
        # ==========================================

        profile_heights = []

        temperature_profile = []

        humidity_profile = []

        pressure_profile = []

        refractivity_profile = []

        max_height = min(H, 1000.0)

        step = 5.0

        z = 0.0

        while z <= max_height:

            # --------------------------
            # Temperature
            # --------------------------

            stability_term = theta_star * math.log(max(z + 1.0, 1.0))

            Tz_C = T0_C - self.LAPSE_RATE * z + stability_term

            # --------------------------
            # Humidity
            # --------------------------

            RHz = RH0 - 5.0 * humidity_scale * math.log(max(z + 1.0, 1.0))

            RHz = max(0.0, min(RHz, 100.0))

            # --------------------------
            # Pressure
            # --------------------------

            Tz_K = Tz_C + 273.15

            Pz = P0 * (1.0 - self.LAPSE_RATE * z / (T0_C + 273.15)) ** 5.255

            # --------------------------
            # Vapor Pressure
            # --------------------------

            es = self.saturation_vapor_pressure(Tz_C)

            e = (RHz / 100.0) * es

            # --------------------------
            # Refractivity
            # --------------------------

            N = self.refractivity(Pz, Tz_K, e)

            profile_heights.append(z)

            temperature_profile.append(Tz_C)

            humidity_profile.append(RHz)

            pressure_profile.append(Pz)

            refractivity_profile.append(N)

            z += step

        # ==========================================
        # Surface Refractivity
        # ==========================================

        N0 = refractivity_profile[0]

        # ==========================================
        # Refractivity Gradient
        # ==========================================

        if len(refractivity_profile) >= 2:

            dN = refractivity_profile[1] - refractivity_profile[0]

            dz = step

            gradient = (dN / dz) * 1000.0

        else:

            gradient = 0.0

        # ==========================================
        # Initial Cn² Estimate
        #
        # Marine optical path estimate
        # ==========================================

        base_cn2 = 1e-15
        tx_wind = getattr(state, "tx_wind_speed_m_s", getattr(state, "wind_speed_m_s", 5.0))
        rx_wind = getattr(state, "rx_wind_speed_m_s", getattr(state, "wind_speed_m_s", 5.0))
        wind_path = (tx_wind + rx_wind) / 2.0
        wind_factor = 1.0 + wind_path / 5.0

        tx_rh = getattr(state, "tx_humidity_pct", getattr(state, "relative_humidity_pct", 80.0))
        rx_rh = getattr(state, "rx_humidity_pct", getattr(state, "relative_humidity_pct", 80.0))
        humidity_path = (tx_rh + rx_rh) / 2.0
        humidity_factor = 0.5 + 0.5 * humidity_path / 100.0

        tx_temp = getattr(state, "tx_temperature_C", getattr(state, "temperature_C", 25.0))
        rx_temp = getattr(state, "rx_temperature_C", getattr(state, "temperature_C", 25.0))
        temp_path = (tx_temp + rx_temp) / 2.0
        temp_diff = abs(state.sea_surface_temperature_C - temp_path)

        temp_factor = 1.0 + temp_diff / 5.0

        wave_factor = 1.0 + state.wave_height_m / 5.0

        stability_factor = math.exp(-abs(zeta))

        Cn2 = (
            base_cn2
            * wind_factor
            * humidity_factor
            * temp_factor
            * wave_factor
            * stability_factor
        )

        # ==========================================
        # Land / Sea Effect
        # ==========================================

        sea_fraction = getattr(state, "sea_percentage", 100.0) / 100.0
        land_fraction = getattr(state, "land_percentage", 0.0) / 100.0

        # Sea increases marine turbulence,
        # land decreases it.

        surface_factor = 1.0 * sea_fraction + 0.6 * land_fraction

        Cn2 *= surface_factor

        # ==========================================
        # Save Results
        # ==========================================

        state.surface_refractivity_N = N0

        state.refractivity_gradient_N_km = gradient

        state.Cn2_m2_3 = Cn2

        # Store full profiles

        state.profile_heights_m = profile_heights

        state.temperature_profile_C = temperature_profile

        state.humidity_profile_pct = humidity_profile

        state.pressure_profile_hPa = pressure_profile

        state.refractivity_profile_N = refractivity_profile
        state.surface_vapor_pressure_hPa = e

        state.debug_message = "Marine boundary layer completed"
        # ==========================================
        # COPY MARINE PARAMETERS TO PROPAGATION SLICES (v0.4)
        # ==========================================

        if state.propagation_slices:

            for s in state.propagation_slices:

                # Height-dependent Cn²
                wind_factor = 1.0 + s.wind_speed_m_s / 5.0

                humidity_factor = 0.5 + 0.5 * s.relative_humidity_pct / 100.0

                sea_temp = getattr(
                    s, "sea_surface_temperature_C", state.sea_surface_temperature_C
                )

                temp_diff = abs(sea_temp - s.temperature_C)
                temp_factor = 1.0 + temp_diff / 5.0

                wave_factor = 1.0 + s.wave_height_m / 5.0

                stability = getattr(s, "stability_parameter", zeta)

                stability_factor = math.exp(-abs(stability))

                if s.is_sea:
                    local_surface_factor = 1.0

                elif s.coastal:
                    local_surface_factor = 0.8

                else:
                    local_surface_factor = 0.6
                slice_cn2 = (
                    base_cn2
                    * wind_factor
                    * humidity_factor
                    * temp_factor
                    * wave_factor
                    * stability_factor
                    * local_surface_factor
                )
                s.marine_BL_height_m = state.marine_BL_height_m

                height = getattr(s, "height_above_surface_m", s.beam_height_m)

                s.Cn2 = slice_cn2 * math.exp(-height / max(s.marine_BL_height_m, 1.0))
                s.Cn2_m2_3 = s.Cn2
                # Refractivity
                s.refractivity_N = N0 + gradient * (s.beam_height_m / 1000.0)
                s.refractivity_gradient_N_km = gradient

                s.modified_refractivity_M = s.refractivity_N + 0.157 * s.beam_height_m
                # Marine properties

                s.sea_state = state.sea_state
                s.wave_height_m = state.wave_height_m

                s.stability_parameter = zeta
                s.air_sea_temperature_difference_C = (
                    state.sea_surface_temperature_C - s.temperature_C
                )
                s.surface_factor = surface_factor
                s.surface_refractivity_N = N0
                s.modified_refractivity_gradient = gradient
                s.surface_vapor_pressure_hPa = e
                s.profile_height_m = s.beam_height_m
                s.marine_layer_fraction = min(
                    1.0, height / max(s.marine_BL_height_m, 1.0)
                )
            state.average_cn2_m2_3 = sum(s.Cn2 for s in state.propagation_slices) / max(
                len(state.propagation_slices), 1
            )

            state.average_refractivity_N = sum(
                s.refractivity_N for s in state.propagation_slices
            ) / max(len(state.propagation_slices), 1)

            state.average_modified_refractivity_M = sum(
                s.modified_refractivity_M for s in state.propagation_slices
            ) / max(len(state.propagation_slices), 1)
            print()
            print("===== MARINE → SLICES =====")

            for s in state.propagation_slices[:5]:

                print(
                    f"Slice {s.slice_id}: "
                    f"Cn2={s.Cn2:.2e} "
                    f"T={s.temperature_C:.1f}C "
                    f"Wind={s.wind_speed_m_s:.1f}m/s "
                    f"N={s.refractivity_N:.2f}"
                )

            print("===========================")
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

        print(f"Surface Refractivity: " f"{N0:.2f}")

        print(f"Refractivity Gradient: " f"{gradient:.2f} N/km")

        print(f"Cn² Estimate: " f"{Cn2:.3e}")

        print(f"Profile Points: " f"{len(profile_heights)}")
