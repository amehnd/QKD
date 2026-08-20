"""
refractivity.py

Marine Optical Refractivity Model

Computes:

    Refractive Index Profile

    Refractive Index Gradient

    Ray Curvature

    Beam Bending Angle

    Effective Elevation Bias

Used by:

    chromatic_refraction.py
    pointing_loss.py
    future ray tracing engine

Version:
    0.3
"""

import math

from core.model import Model


class RefractivityModel(Model):

    name = "Refractivity"

    description = "Marine optical refractivity model"

    version = "0.3"

    inputs = [
        "link_distance_km",
        "surface_refractivity_N",
        "refractivity_gradient_N_km",
        "effective_earth_radius_factor",
        "tx_height_msl_m",
        "surface_refractivity_N",
        "refractivity_gradient_N_km",
        "effective_earth_radius_factor",
        "rx_height_msl_m",
    ]

    outputs = [
        "surface_refractive_index",
        "dn_dz",
        "ray_curvature_1_m",
        "ray_bending_angle_urad",
        "effective_elevation_bias_urad",
    ]

    # --------------------------------------------------
    # Validation
    # --------------------------------------------------

    def validate(self, state):
        if not state.propagation_slices:

            raise ValueError("Evaporation Duct must run before Refractivity.")

        if state.link_distance_km <= 0:

            raise ValueError("Invalid link distance")

        return True

    # --------------------------------------------------
    # Execute
    # --------------------------------------------------

    def execute(self, state):

        N0 = state.surface_refractivity_N

        gradient = state.refractivity_gradient_N_km

        range_m = state.link_distance_km * 1000.0

        Re = 6371000.0

        k_factor = getattr(state, "effective_earth_radius_factor", 1.333)

        Re_eff = Re * k_factor

        tx_h = state.tx_height_msl_m

        rx_h = state.rx_height_msl_m
        height_km = (tx_h + rx_h) / 2.0 / 1000.0

        modified_M = N0 + 157.0 * height_km

        # optical horizon

        horizon_tx = math.sqrt(2 * Re_eff * tx_h)

        horizon_rx = math.sqrt(2 * Re_eff * rx_h)

        optical_horizon = horizon_tx + horizon_rx

        # earth curvature drop

        curvature_drop = range_m**2 / (2 * Re_eff)

        los = range_m <= optical_horizon

        # ==========================================
        # Surface Refractive Index
        #
        # n = 1 + N × 1e-6
        # ==========================================

        n0 = 1.0 + N0 * 1e-6

        # ==========================================
        # dn/dz
        #
        # Convert N/km to n/m
        # ==========================================

        dn_dz = gradient * 1e-6 / 1000.0

        # ==========================================
        # Ray Curvature
        #
        # First-order approximation
        #
        # κ = -(1/n) dn/dz
        # ==========================================

        ray_curvature = -(1.0 / n0) * dn_dz

        # ==========================================
        # Bending Angle
        #
        # θ ≈ κ × L
        # ==========================================

        bending_angle_rad = ray_curvature * range_m

        bending_angle_urad = bending_angle_rad * 1e6

        # ==========================================
        # Effective Elevation Bias
        #
        # Total angular shift
        # ==========================================

        elevation_bias_urad = bending_angle_urad

        # ==========================================
        # Curved Path Height Shift
        #
        # y = κL²/2
        # ==========================================

        # ==========================================
        # Store Profile
        # ==========================================

        profile_z = []

        profile_n = []

        z = 0.0

        max_height = max(state.tx_height_msl_m, state.rx_height_msl_m, 100.0)

        while z <= max_height:

            n = n0 + dn_dz * z

            profile_z.append(z)

            profile_n.append(n)

            z += 1.0

        # ==========================================
        # PROPAGATION SLICE REFRACTIVITY (v0.4)
        # ==========================================

        total_bending = 0.0
        beam_shift_m = 0.0
        if state.propagation_slices:

            for s in state.propagation_slices:

                # Local refractivity
                # Simple atmospheric refractivity (engineering)
                temp_K = s.temperature_C + 273.15

                e = (
                    s.vapor_pressure_hPa
                    if hasattr(s, "vapor_pressure_hPa")
                    else (
                        s.humidity_pct
                        / 100.0
                        * 6.112
                        * math.exp(
                            (17.67 * s.temperature_C) / (s.temperature_C + 243.5)
                        )
                    )
                )

                local_N = 77.6 * s.pressure_hPa / temp_K + 3.73e5 * e / (temp_K**2)
                s.refractivity_N = local_N

                # Local refractive index
                local_n = 1.0 + local_N * 1e-6

                # Local gradient
                previous_N = local_N

                if s.slice_id > 1:

                    previous_N = getattr(
                        state.propagation_slices[s.slice_id - 2],
                        "refractivity_N",
                        local_N,
                    )

                local_dn_dz = ((local_N - previous_N) / max(s.length_m, 1.0)) * 1e-6

                # Local curvature
                local_curvature = -(1.0 / local_n) * local_dn_dz

                # Local bending
                local_bending = local_curvature * s.length_m * 1e6

                total_bending += local_bending

                # Store inside slice
                s.refractivity_N = local_N

                s.refractive_index = local_n

                s.dn_dz = local_dn_dz

                s.ray_curvature_1_m = local_curvature

                s.ray_bending_urad = local_bending
                s.ray_bending_rad = local_curvature * s.length_m

                height = max(s.height_above_surface_m, 0.0)

                s.modified_refractivity_M = local_N + 157.0 * height / 1000.0
                s.modified_refractivity_gradient_N_km = s.dn_dz * 1e9
                s.optical_horizon_km = optical_horizon / 1000.0

                s.line_of_sight_available = los

                s.notes = (
                    f"N={local_N:.2f}, "
                    f"n={local_n:.7f}, "
                    f"Bending={local_bending:.2f} urad"
                )

            state.average_refractivity_N = sum(
                s.refractivity_N for s in state.propagation_slices
            ) / max(len(state.propagation_slices), 1)

            state.average_refractive_index = sum(
                s.refractive_index for s in state.propagation_slices
            ) / max(len(state.propagation_slices), 1)

            state.average_ray_curvature_1_m = sum(
                s.ray_curvature_1_m for s in state.propagation_slices
            ) / max(len(state.propagation_slices), 1)
            print()
            print("===== REFRACTIVITY → SLICES =====")

            for s in state.propagation_slices[:5]:

                print(
                    f"Slice {s.slice_id}: "
                    f"N={s.refractivity_N:.2f} "
                    f"n={s.refractive_index:.7f} "
                    f"Bend={s.ray_bending_urad:.2f}"
                )

            print("==============================")
            print()

            beam_shift_m = 0.0

            for s in state.propagation_slices:

                s.beam_refraction_shift_m = 0.5 * s.ray_curvature_1_m * s.length_m**2

                beam_shift_m += s.beam_refraction_shift_m

        # ==========================================
        # Save Results
        # ==========================================
        state.beam_refraction_shift_m = beam_shift_m

        state.surface_refractive_index = n0
        state.refractivity_N = N0
        state.modified_refractivity_M = modified_M
        state.dn_dz = dn_dz

        state.ray_curvature_1_m = ray_curvature

        state.effective_elevation_bias_urad = elevation_bias_urad

        state.beam_refraction_shift_m = beam_shift_m
        state.optical_horizon_km = optical_horizon / 1000
        state.line_of_sight_available = los

        # Geometry model already computes Earth curvature.
        # Do NOT overwrite it here.
        # state.earth_curvature_drop_m = curvature_drop

        state.refractive_index_profile_z_m = profile_z

        state.refractive_index_profile = profile_n

        # ==========================================
        # Integrated Slice Results
        # ==========================================

        if state.propagation_slices:

            state.ray_bending_angle_urad = total_bending
            state.effective_elevation_bias_urad = total_bending

        else:

            state.ray_bending_angle_urad = bending_angle_urad
            state.effective_elevation_bias_urad = elevation_bias_urad
        for s in state.propagation_slices:
            s.cumulative_bending_urad = total_bending

        state.debug_message = "Refractivity completed"

        # ==========================================
        # Console Output
        # ==========================================

        print()

        print(f"Surface Refractive Index: " f"{n0:.8f}")

        print(f"dn/dz: " f"{dn_dz:.3e} 1/m")

        print(f"Ray Curvature: " f"{ray_curvature:.3e} 1/m")

        print(f"Ray Bending Angle: " f"{state.ray_bending_angle_urad:.2f} urad")

        print(f"Beam Refraction Shift: " f"{beam_shift_m:.3f} m")

        print(f"Elevation Bias: " f"{state.effective_elevation_bias_urad:.2f} urad")
