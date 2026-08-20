"""
polarization_model.py
Version: 0.3
"""

import math

from core.model import Model


class PolarizationModel(Model):

    name = "Polarization"

    description = "Polarization rotation and QBER model"

    version = "0.3"

    inputs = [
        "roll_rms_deg",
        "pitch_rms_deg",
        "yaw_rms_deg",
        "tracking_error_urad",
        "polarization_error_rate",
    ]

    outputs = [
        "polarization_rotation_deg",
        "polarization_visibility",
        "polarization_loss_dB",
        "polarization_qber",
    ]

    def execute(self, state):

        roll = abs(getattr(state, "roll_rms_deg", 0.0))
        pitch = abs(getattr(state, "pitch_rms_deg", 0.0))
        yaw = abs(getattr(state, "yaw_rms_deg", 0.0))

        tracking = getattr(state, "tracking_error_urad", 0.0)

        # --------------------------------------
        # Total polarization rotation
        # --------------------------------------

        beam_wander = getattr(state, "beam_wander_urad", 0.0)
        wave_slope = getattr(state, "wave_slope_deg", 0.0)
        rytov = getattr(state, "rytov_variance", 0.0)
        refraction = getattr(state, "differential_refraction_urad", 0.0)

        rotation = (
            math.sqrt(roll**2 + pitch**2 + yaw**2)
            + tracking * 1e-3
            + beam_wander * 5e-4
            + refraction * 5e-4
            + wave_slope * 0.25
            + rytov * 0.20
        )
        # --------------------------------------
        # Polarization visibility
        # --------------------------------------

        visibility = max(0.0, math.cos(math.radians(rotation)))

        # --------------------------------------
        # Polarization loss
        # --------------------------------------

        polarization_loss = -10.0 * math.log10(max(visibility, 1e-12))

        # --------------------------------------
        # Polarization QBER
        # --------------------------------------

        polarization_qber = (1.0 - visibility) / 2.0

        # --------------------------------------
        # Save outputs
        # --------------------------------------

        state.polarization_rotation_deg = rotation

        state.polarization_visibility = visibility

        state.polarization_loss_dB = polarization_loss

        state.polarization_qber = polarization_qber
        state.polarization_misalignment_loss_dB = polarization_loss
        # ======================================
        # v0.4 Propagation Slice Polarization
        # ======================================

        if state.propagation_slices:

            cumulative_rotation = 0.0

            for s in state.propagation_slices:

                local_roll = getattr(s, "roll_rms_deg", roll)

                local_pitch = getattr(s, "pitch_rms_deg", pitch)

                local_yaw = getattr(s, "yaw_rms_deg", yaw)

                local_tracking = getattr(s, "tracking_error_urad", tracking)

                local_wander = getattr(s, "beam_wander_urad", beam_wander)

                local_refraction = getattr(
                    s, "differential_refraction_urad", refraction
                )

                local_rytov = getattr(s, "rytov_variance", rytov)

                local_wave = getattr(s, "wave_slope_deg", wave_slope)

                local_rotation = (
                    math.sqrt(local_roll**2 + local_pitch**2 + local_yaw**2)
                    + local_tracking * 1e-3
                    + local_wander * 5e-4
                    + local_refraction * 5e-4
                    + local_wave * 0.25
                    + local_rytov * 0.20
                )

                cumulative_rotation += local_rotation

                local_visibility = max(0.0, math.cos(math.radians(cumulative_rotation)))

                local_loss = -10.0 * math.log10(max(local_visibility, 1e-12))

                local_qber = (1.0 - local_visibility) / 2.0

                s.polarization_rotation_deg = cumulative_rotation

                s.polarization_visibility = local_visibility

                s.polarization_loss_dB = local_loss

                s.polarization_qber = local_qber

                s.polarization_misalignment_loss_dB = local_loss

                s.notes = f"Loss={local_loss:.3f} dB, " f"QBER={local_qber:.5f}"

            rx = state.propagation_slices[-1]

            state.polarization_rotation_deg = rx.polarization_rotation_deg

            state.polarization_visibility = rx.polarization_visibility

            state.polarization_loss_dB = rx.polarization_loss_dB

            state.polarization_qber = rx.polarization_qber

            state.polarization_misalignment_loss_dB = (
                rx.polarization_misalignment_loss_dB
            )

            print()
            print("===== POLARIZATION → SLICES =====")

            for s in state.propagation_slices[:5]:

                print(
                    f"Slice {s.slice_id}: "
                    f"Rotation={s.polarization_rotation_deg:.3f} "
                    f"QBER={s.polarization_qber:.6f}"
                )

            print("==============================")
            print()
        # --------------------------------------
        # Console
        # --------------------------------------

        print()

        print("POLARIZATION")

        print("----------------")

        print(f"Rotation : {state.polarization_rotation_deg:.3f} deg")

        print(f"Visibility : {state.polarization_visibility:.6f}")

        print(f"Loss : {state.polarization_loss_dB:.3f} dB")

        print(f"QBER : {state.polarization_qber:.6f}")
        state.debug_message = "Polarization completed"
