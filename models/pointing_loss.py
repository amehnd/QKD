"""
pointing_loss.py

Pointing Loss Model

Combines:

    PAT residual error
    FSM residual error
    Beam wander
    Chromatic offset

Computes:

    Pointing Loss

    Coupling Efficiency

    Effective Capture Fraction

Version:
    0.3
"""

import math

from core.model import Model


class PointingLossModel(Model):

    name = "PointingLoss"

    description = "Optical pointing loss model"

    version = "0.3"

    inputs = [
        "tracking_error_urad",
        "fsm_residual_error_urad",
        "beam_wander_urad",
        "beacon_qkd_offset_urad",
        "link_distance_km",
        "spot_diameter_m",
        "rx_aperture_mm",
    ]

    outputs = [
        "total_jitter_urad",
        "pointing_loss_dB",
        "effective_capture_fraction",
        "rx_coupling_efficiency",
    ]

    # --------------------------------------------------
    # Validation
    # --------------------------------------------------

    def validate(self, state):

        if state.link_distance_km <= 0:

            raise ValueError("Invalid range")

        return True

    def _gaussian_pointing(self, beam_radius, beam_offset):
        beam_radius = max(beam_radius, 1e-12)

        return math.exp(-2.0 * (beam_offset / beam_radius) ** 2)

    def _farid_aperture_coefficient(
        self,
        beam_radius,
        receiver_radius,
    ):
        beam_radius = max(beam_radius, 1e-12)

        v = math.sqrt(math.pi) * receiver_radius / (math.sqrt(2.0) * beam_radius)

        A0 = math.erf(v) ** 2

        return A0, v

    def _farid_equivalent_beam_radius(
        self,
        beam_radius,
        receiver_radius,
    ):
        beam_radius = max(beam_radius, 1e-12)

        A0, v = self._farid_aperture_coefficient(
            beam_radius,
            receiver_radius,
        )

        numerator = beam_radius**2 * math.sqrt(math.pi) * math.erf(v)

        denominator = 2.0 * v * math.exp(-(v**2))

        w_eq_sq = numerator / max(denominator, 1e-20)

        return math.sqrt(w_eq_sq)

    def _farid_hranilovic(
        self,
        beam_radius,
        receiver_radius,
        beam_offset,
    ):
        A0, _ = self._farid_aperture_coefficient(
            beam_radius,
            receiver_radius,
        )

        w_eq = self._farid_equivalent_beam_radius(
            beam_radius,
            receiver_radius,
        )

        hp = A0 * math.exp(-2.0 * beam_offset**2 / max(w_eq**2, 1e-20))

        return max(0.0, min(hp, 1.0))

    # --------------------------------------------------
    # Execute
    # --------------------------------------------------

    def execute(self, state):
        pointing_model = getattr(
            state, "pointing_loss_model", "Gaussian Pointing Error Model"
        )

        receiver_radius = state.rx_aperture_m / 2.0
        state.farid_A0 = 0.0
        state.farid_equivalent_beam_radius_m = 0.0

        if not state.propagation_slices:

            # ==========================================
            # Separate random zero-mean jitter from static bias
            # ==========================================

            sigma_jitter_urad = math.sqrt(
                state.tracking_error_urad**2
                + state.fsm_residual_error_urad**2
                + state.beam_wander_urad**2
            )
            bias_offset_urad = abs(state.beacon_qkd_offset_urad)
            total_jitter = math.sqrt(sigma_jitter_urad**2 + bias_offset_urad**2)

            range_m = state.link_distance_km * 1000.0

            sigma_jitter_m = sigma_jitter_urad * 1e-6 * range_m
            bias_offset_m = bias_offset_urad * 1e-6 * range_m
            beam_radius = max(state.beam_radius_m, 1e-6)

            print()
            print("POINTING INPUTS")
            print("----------------")
            print("spot_diameter_m =", state.spot_diameter_m)
            print("beam_radius =", beam_radius)
            print("sigma_jitter_urad =", sigma_jitter_urad)
            print("bias_offset_urad =", bias_offset_urad)

            if beam_radius <= 0:
                coupling = 0.0
            else:
                if pointing_model == "Gaussian Pointing Error Model":
                    denom_factor = 1.0 + 8.0 * (sigma_jitter_m / beam_radius)**2
                    coupling = (1.0 / denom_factor) * math.exp(-2.0 * (bias_offset_m**2) / (beam_radius**2 * denom_factor))
                elif pointing_model == "Farid–Hranilovic Model":
                    A0, _ = self._farid_aperture_coefficient(
                        beam_radius,
                        receiver_radius,
                    )
                    w_eq = self._farid_equivalent_beam_radius(
                        beam_radius,
                        receiver_radius,
                    )
                    beam_offset_m = total_jitter * 1e-6 * range_m
                    coupling = self._farid_hranilovic(
                        beam_radius,
                        receiver_radius,
                        beam_offset_m,
                    )
                    state.farid_A0 = A0
                    state.farid_equivalent_beam_radius_m = w_eq
                else:
                    beam_offset_m = total_jitter * 1e-6 * range_m
                    coupling = self._gaussian_pointing(beam_radius, beam_offset_m)

            coupling = max(0.0, min(coupling, 1.0))

            # ==========================================
            # Effective capture fraction
            # ==========================================

            geometric_capture = getattr(state, "capture_fraction", 1.0)

            effective_capture = geometric_capture * coupling

            # ==========================================
            # Pointing Loss
            # ==========================================

            if coupling > 1e-12:

                pointing_loss_dB = -10.0 * math.log10(coupling)

            else:

                pointing_loss_dB = 120.0

        # ==========================================
        # v0.4 Slice Pointing Model
        # ==========================================

        else:

            previous_loss = 0.0

            for s in state.propagation_slices:

                # Local beam wander already computed
                local_jitter = math.sqrt(
                    s.tracking_error_urad**2
                    + s.fsm_residual_error_urad**2
                    + s.beam_wander_urad**2
                    + state.beacon_qkd_offset_urad**2
                )
                print(
                    f"Slice {s.slice_id}: "
                    f"wander={s.beam_wander_urad:.2f} "
                    f"tracking={state.tracking_error_urad:.2f} "
                    f"fsm={state.fsm_residual_error_urad:.2f} "
                    f"chromatic={state.beacon_qkd_offset_urad:.2f} "
                    f"jitter={local_jitter:.2f}"
                )
                print(
                    "Slice",
                    s.slice_id,
                    "wander =",
                    s.beam_wander_urad,
                    "local jitter =",
                    local_jitter,
                )

                local_offset = local_jitter * 1e-6 * s.slant_distance_m
                print(
                    f"Slice {s.slice_id}: "
                    f"center={s.center_m:.2f} "
                    f"beam_radius={s.beam_radius_m:.6f}"
                )

                beam_radius = max(s.beam_radius_m, 1e-6)
                s.farid_A0 = 0.0
                s.farid_equivalent_beam_radius_m = 0.0

                if pointing_model == "Gaussian Pointing Error Model":

                    local_coupling = self._gaussian_pointing(beam_radius, local_offset)

                elif pointing_model == "Farid–Hranilovic Model":

                    local_coupling = self._farid_hranilovic(
                        beam_radius,
                        receiver_radius,
                        local_offset,
                    )

                    s.farid_A0, _ = self._farid_aperture_coefficient(
                        beam_radius,
                        receiver_radius,
                    )

                    s.farid_equivalent_beam_radius_m = (
                        self._farid_equivalent_beam_radius(
                            beam_radius,
                            receiver_radius,
                        )
                    )

                else:

                    local_coupling = self._gaussian_pointing(beam_radius, local_offset)
                local_coupling = max(0.0, min(local_coupling, 1.0))
                s.rx_coupling_efficiency = local_coupling

                capture_fraction = getattr(
                    s, "capture_fraction", getattr(state, "capture_fraction", 1.0)
                )

                local_capture = capture_fraction * local_coupling
                if local_coupling > 1e-12:

                    local_loss = -10.0 * math.log10(local_coupling)

                else:

                    local_loss = 120.0

                s.total_jitter_urad = local_jitter
                incremental_loss = max(0.0, local_loss - previous_loss)

                s.pointing_loss_dB = incremental_loss
                s.cumulative_pointing_loss_dB = local_loss

                previous_loss = local_loss
                s.rx_coupling_efficiency = local_coupling
                s.effective_capture_fraction = local_capture
                s.beam_offset_m = local_offset
                s.pointing_error_m = local_offset
                s.cumulative_pointing_loss_dB = -10.0 * math.log10(
                    max(local_coupling, 1e-30)
                )
                s.notes = (
                    f"Jitter={local_jitter:.2f} urad, " f"Pointing={local_loss:.2f} dB"
                )
            n = len(state.propagation_slices)
            print()
            print("===== POINTING → SLICES =====")
            print("Slices Updated :", n)
            print("=============================")
            print()

            # ==========================================
            # Save Results
            # ==========================================
            last = state.propagation_slices[-1]

            total_jitter = last.total_jitter_urad

            beam_offset_m = last.beam_offset_m

            coupling = last.rx_coupling_efficiency

            effective_capture = state.capture_fraction * coupling

            pointing_loss_dB = -10.0 * math.log10(max(coupling, 1e-30))
        state.total_jitter_urad = total_jitter
        state.beam_offset_m = beam_offset_m

        state.pointing_error_m = beam_offset_m
        state.pointing_loss_dB = pointing_loss_dB
        state.effective_capture_fraction = effective_capture
        state.rx_coupling_efficiency = coupling

        state.debug_message = "Pointing loss completed"
        if state.propagation_slices:

            state.farid_A0 = state.propagation_slices[-1].farid_A0

            state.farid_equivalent_beam_radius_m = state.propagation_slices[
                -1
            ].farid_equivalent_beam_radius_m

        # ==========================================
        # Console Output
        # ==========================================

        print()

        print(f"Total Jitter: " f"{total_jitter:.2f} urad")

        print(f"Beam Offset: " f"{state.beam_offset_m:.4f} m")

        print(f"Coupling Efficiency: " f"{100.0*coupling:.2f}%")

        print(f"Effective Capture Fraction: " f"{effective_capture:.6f}")

        print(f"Pointing Loss: " f"{pointing_loss_dB:.3f} dB")
        print("\n===== POINTING OUTPUT =====")
        print("Pointing Loss =", state.pointing_loss_dB)
        print("Coupling =", state.rx_coupling_efficiency)
        print("Effective Capture =", state.effective_capture_fraction)
        if pointing_model == "Farid–Hranilovic Model":
            print("A0 =", state.farid_A0)
            print("Equivalent Beam Radius =", state.farid_equivalent_beam_radius_m)
        print("===========================\n")

        # ==========================================
        # VERIFIER TEXT GENERATION
        # ==========================================
        state.verifier_text["track"] = f"""
Roll
θ_roll = {getattr(state, 'roll_rms_deg', 0.0):.4f} deg

Pitch
θ_pitch = {getattr(state, 'pitch_rms_deg', 0.0):.4f} deg

Yaw
θ_yaw = {getattr(state, 'yaw_rms_deg', 0.0):.4f} deg

Ship LOS Jitter
J_ship = √(θ_roll² + θ_pitch² + θ_yaw²) · (π/180) · 10⁶ = {getattr(state, 'ship_los_jitter_urad', 0.0):.4f} µrad

Tracking Error
θ_track_err = max(θ_fsm_err, 1e-12) = {getattr(state, 'tracking_error_urad', 0.0):.4f} µrad

Gimbal Error
θ_gimbal_err = √(J_ship² + σ_bw² + θ_jitter²) · (1 - R_gimbal) = {getattr(state, 'gimbal_tracking_error_urad', 0.0):.4f} µrad

FSM Error
θ_fsm_err = θ_gimbal_err · (1 - R_fsm) = {getattr(state, 'fsm_residual_error_urad', 0.0):.4f} µrad

Pointing Loss
L_point = -10 · log₁₀(η_point) = {pointing_loss_dB:.4f} dB

Coupling Efficiency
η_point = exp(-2 · (θ_total / R_beam)²) = {coupling:.6f}

Effective Capture Fraction
η_eff = η_geo · η_point = {getattr(state, "effective_capture_fraction", 0):.6f}

Total Jitter
θ_total = √(θ_track_err² + θ_bias²) = {total_jitter:.4f} µrad

Beam Offset
Offset = θ_total · L · 10⁻⁶ = {beam_offset_m:.6f} m

Lock Probability
P_lock = exp(-θ_track_err / 200) = {getattr(state, "lock_probability", 0):.4f}

Tracking Probability
P_track = 0.95 · P_lock = {getattr(state, "tracking_probability", 0):.4f}

Acquisition Probability
P_acq = P_lock · η_gimbal = {getattr(state, "acquisition_probability", 0):.4f}

Gimbal Efficiency
η_gimbal = exp(-θ_gimbal_err / 500) = {getattr(state, "gimbal_tracking_efficiency", 0):.4f}

FSM Efficiency
η_fsm = exp(-θ_fsm_err / 50) = {getattr(state, "fsm_tracking_efficiency", 0):.4f}

FSM Stroke
θ_stroke = 3 · |θ_fsm_err| = {getattr(state, 'fsm_stroke_urad', 0.0):.4f} µrad

Acquisition Error
θ_acq_err = {getattr(state, 'acquisition_error_urad', 0.0):.4f} µrad
"""

