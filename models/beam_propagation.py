"""
beam_propagation.py

Beam Propagation Model

Updates beam size after turbulence.

FSO/QKD Maritime Simulator v0.4
"""

import math

from core.model import Model


class BeamPropagationModel(Model):

    name = "BeamPropagation"

    description = "Beam propagation including turbulence"

    priority = 17.5

    def validate(self, state):

        if not state.propagation_slices:
            raise ValueError("Adaptive slicing must run before BeamPropagation.")

        return True

    def execute(self, state):
        beam_radius = state.beam_radius_m

        beam_spread = state.beam_spread_factor

        beam_radius *= beam_spread

        beam_diameter = 2.0 * beam_radius

        state.beam_radius_m = beam_radius
        state.beam_diameter_m = beam_diameter
        state.spot_diameter_m = beam_diameter

        rx_radius = state.rx_aperture_m / 2.0

        geometric_loss_model = getattr(
            state, "geometric_loss_model", "Gaussian Beam Theory"
        )

        if geometric_loss_model == "Gaussian Beam Theory":

            capture_fraction = 1.0 - math.exp(-2.0 * (rx_radius / beam_radius) ** 2)

        elif geometric_loss_model == "Friis-like Optical Model":

            beam_diameter = 2.0 * beam_radius

            capture_fraction = min(
                1.0, (state.rx_aperture_m / max(beam_diameter, 1e-12)) ** 2
            )

        elif geometric_loss_model == "Gaussian Coupling Model":

            pointing_error = getattr(state, "pointing_error_m", 0.0)

            capture_fraction = 1.0 - math.exp(-2.0 * (rx_radius / beam_radius) ** 2)

            capture_fraction *= math.exp(
                -2.0 * pointing_error**2 / max(beam_radius**2, 1e-20)
            )

        else:

            capture_fraction = 1.0 - math.exp(-2.0 * (rx_radius / beam_radius) ** 2)
        capture_fraction = max(1e-12, min(capture_fraction, 1.0))

        state.capture_fraction = capture_fraction
        state.receiver_capture_fraction = capture_fraction

        if state.propagation_slices:

            initial_radius = state.tx_aperture_m / 2.0

            divergence = state.tx_beam_divergence_mrad * 1e-3

            current_power = getattr(state, "tx_power_W", 1.0)
            for s in state.propagation_slices:

                spread = max(
                    1.0, getattr(s, "beam_spread_factor", state.beam_spread_factor)
                )

                # Diffraction over this slice
                # Distance from transmitter
                z = s.end_m

                # Beam radius due to diffraction
                current_radius = math.sqrt(initial_radius**2 + (divergence / 2.0 * z) ** 2)

                # Turbulence broadening
                current_radius *= spread
                s.beam_radius_m = current_radius
                s.beam_diameter_m = 2.0 * current_radius
                s.spot_diameter_m = s.beam_diameter_m
                s.beam_spread_factor = spread

                if geometric_loss_model == "Gaussian Beam Theory":

                    local_capture = 1.0 - math.exp(
                        -2.0 * (rx_radius / current_radius) ** 2
                    )

                elif geometric_loss_model == "Friis-like Optical Model":

                    local_beam_diameter = 2.0 * current_radius

                    local_capture = min(
                        1.0,
                        (state.rx_aperture_m / max(local_beam_diameter, 1e-12)) ** 2,
                    )

                elif geometric_loss_model == "Gaussian Coupling Model":

                    pointing_error = getattr(state, "pointing_error_m", 0.0)

                    local_capture = 1.0 - math.exp(
                        -2.0 * (rx_radius / current_radius) ** 2
                    )

                    local_capture *= math.exp(
                        -2.0 * pointing_error**2 / max(current_radius**2, 1e-20)
                    )

                else:

                    local_capture = 1.0 - math.exp(
                        -2.0 * (rx_radius / current_radius) ** 2
                    )

                local_capture = max(1e-12, min(local_capture, 1.0))
                s.capture_fraction = local_capture
                s.geometric_loss_dB = -10.0 * math.log10(s.capture_fraction)
                slice_loss = getattr(s, "atmospheric_loss_dB", 0.0)

                transmission = 10 ** (-slice_loss / 10.0)

                current_power *= transmission

                s.beam_power_W = current_power
                beam_area = math.pi * current_radius**2

                s.beam_area_m2 = beam_area
                s.propagation_distance_m = s.end_m

                s.beam_divergence_rad = divergence
                s.tx_beam_divergence_mrad = divergence * 1e3

                s.beam_waist_m = initial_radius

                if divergence > 0:
                    s.rayleigh_length_m = initial_radius / divergence
                else:
                    s.rayleigh_length_m = 0.0

                if current_radius > 0:
                    s.wavefront_radius_m = s.propagation_distance_m
                else:
                    s.wavefront_radius_m = 0.0

                if current_radius > 0:
                    s.fresnel_number = (state.rx_aperture_m / 2.0) ** 2 / (
                        state.wavelength_nm * 1e-9 * max(s.propagation_distance_m, 1.0)
                    )
                else:
                    s.fresnel_number = 0.0

                s.diffraction_loss_dB = -10.0 * math.log10(
                    max(s.capture_fraction, 1e-12)
                )

                s.beam_irradiance_W_m2 = current_power / max(beam_area, 1e-12)
                s.cumulative_distance_m = s.end_m

                state.average_beam_radius_m = sum(
                    s.beam_radius_m for s in state.propagation_slices
                ) / len(state.propagation_slices)

            state.average_beam_area_m2 = sum(
                s.beam_area_m2 for s in state.propagation_slices
            ) / len(state.propagation_slices)

            state.average_divergence_mrad = sum(
                s.tx_beam_divergence_mrad for s in state.propagation_slices
            ) / len(state.propagation_slices)

            state.maximum_beam_radius_m = max(
                s.beam_radius_m for s in state.propagation_slices
            )

            state.minimum_beam_radius_m = min(
                s.beam_radius_m for s in state.propagation_slices
            )
        state.beam_radius_m = current_radius
        state.beam_diameter_m = 2.0 * current_radius
        state.spot_diameter_m = state.beam_diameter_m
        state.capture_fraction = state.propagation_slices[-1].capture_fraction
        state.receiver_capture_fraction = state.capture_fraction
        state.received_beam_power_W = current_power

        import re
        if "geo" in state.verifier_text:
            state.verifier_text["geo"] = re.sub(
                r'(Beam Radius\n.*= ).*?(\n)', 
                r'\g<1>' + f'{current_radius:.6f} m' + r'\g<2>', 
                state.verifier_text["geo"]
            )
            state.verifier_text["geo"] = re.sub(
                r'(Beam Diameter\n.*= ).*?(\n)', 
                r'\g<1>' + f'{2.0 * current_radius:.6f} m' + r'\g<2>', 
                state.verifier_text["geo"]
            )
            state.verifier_text["geo"] = re.sub(
                r'(Spot Diameter\n.*= ).*?(\n)', 
                r'\g<1>' + f'{2.0 * current_radius:.6f} m' + r'\g<2>', 
                state.verifier_text["geo"]
            )
            state.verifier_text["geo"] = re.sub(
                r'(Capture Fraction\n(?:.*\n)*?.*η .*= ).*?(\n|$)', 
                r'\g<1>' + f'{state.capture_fraction:.6e}' + r'\g<2>', 
                state.verifier_text["geo"]
            )

        print()
        print("===== BEAM PROPAGATION → SLICES =====")
        print("Slices Updated :", len(state.propagation_slices))
        print("Average Radius :", state.average_beam_radius_m)
        print("Maximum Radius :", state.maximum_beam_radius_m)
        print("=====================================")
        print()

        print()
        print("===== BEAM PROPAGATION =====")
        print("Beam Spread =", state.beam_spread_factor)
        print("Beam Diameter =", state.beam_diameter_m)
        print("Capture =", state.capture_fraction)
        print("============================")
        print()

        # ==========================================
        # VERIFIER TEXT GENERATION
        # ==========================================
        state.verifier_text["prop"] = f"""
Propagation Type
Type = {getattr(state, 'propagation_type', '')}

Propagation Direction
Direction = {getattr(state, 'propagation_direction', '')}

Ground Range
L_ground = {getattr(state, 'link_distance_km', 0.0):.4f} km

Elevation Angle
θ_el = {getattr(state, 'beam_elevation_angle_deg', 0.0):.4f} deg

Earth Curvature Drop
Δh_curvature = L² / (2 · R_e) = {getattr(state, 'earth_curvature_drop_m', 0.0):.4f} m

Effective Earth Radius
R_e,eff = k * R_e = {getattr(state, 'effective_earth_radius_m', 0.0):.4f} m

LOS
LOS = {getattr(state, 'los', False)}

Lowest LOS Height
h_los_min = min(h_LOS_i) = {getattr(state, 'lowest_los_height_m', 0.0):.4f} m

Lowest LOS Distance
L_los_min = {getattr(state, 'lowest_los_distance_m', 0.0):.4f} m

Minimum Clearance
Clearance_min = min(h_LOS_i - h_terrain_i) = {getattr(state, 'minimum_clearance_m', 0.0):.4f} m

Slant Range
d_slant = {getattr(state, 'slant_range_m', 0.0):.4f} m

Height Difference
Δh = {getattr(state, 'height_difference_m', 0.0):.4f} m

TX Height
h_TX = {getattr(state, 'tx_height_msl_m', 0.0):.2f} m

RX Height
h_RX = {getattr(state, 'rx_height_msl_m', 0.0):.2f} m

LOS Margin
d_margin = {getattr(state, 'los_margin_m', 0.0):.4f} m

Minimum Height Above Sea
h_sea = {getattr(state, 'minimum_height_above_sea_m', 0.0):.4f} m
"""
