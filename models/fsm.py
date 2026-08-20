"""
fsm.py

Fast Steering Mirror Model

Computes:

    Required FSM Stroke

    Required FSM Bandwidth

    Residual FSM Error

    Tracking Suppression

    Coupling Penalty

Version:
    0.3
"""

import math

from core.model import Model


class FSMModel(Model):

    name = "FSM"

    description = "Fine steering mirror model"

    version = "0.3"

    inputs = [
        "gimbal_tracking_error_urad",
        "beam_wander_urad",
        "beacon_qkd_offset_urad",
        "greenwood_frequency_Hz",
        "tracking_wavelength_nm",
        "quantum_wavelength_nm",
    ]

    outputs = [
        "fsm_stroke_urad",
        "fsm_bandwidth_Hz",
        "fsm_residual_error_urad",
        "fsm_tracking_efficiency",
        "fsm_coupling_penalty_dB",
    ]

    # --------------------------------------------------
    # Validation
    # --------------------------------------------------

    def validate(self, state):

        if not state.propagation_slices:
            raise ValueError("Gimbal must run before FSM.")

        return True

    # --------------------------------------------------
    # Execute
    # --------------------------------------------------

    def execute(self, state):

        # ==========================================
        # Disturbance Sources
        # ==========================================

        gimbal_error = abs(state.gimbal_tracking_error_urad)

        beam_wander = abs(state.beam_wander_urad)

        chromatic_offset = abs(state.beacon_qkd_offset_urad)

        # ==========================================
        # Combined Jitter
        # ==========================================

        total_disturbance = math.sqrt(
            gimbal_error**2 + beam_wander**2 + chromatic_offset**2
        )

        # ==========================================
        # FSM Stroke
        #
        # 3 sigma margin
        # ==========================================

        fsm_stroke = 3.0 * total_disturbance

        # ==========================================
        # Required Bandwidth
        #
        # Greenwood driven
        # ==========================================

        greenwood = max(state.greenwood_frequency_Hz, 1.0)

        bandwidth = 5.0 * greenwood

        # ==========================================
        # Tracking Efficiency
        #
        # Simple closed-loop model
        # ==========================================

        efficiency = bandwidth / (bandwidth + greenwood)

        efficiency = min(efficiency, 0.99)

        # ==========================================
        # Residual Error
        # ==========================================

        residual_error = total_disturbance * (1.0 - efficiency)

        # ==========================================
        # Coupling Penalty
        #
        # Approximation
        # ==========================================

        coupling_penalty = 4.343 * (residual_error / max(total_disturbance, 1e-9))

        coupling_penalty = max(0.0, coupling_penalty)

        # ==========================================
        # v0.4 Slice FSM Model
        # ==========================================

        if getattr(state, "propagation_slices", None):
            weighted_stroke = 0.0
            weighted_bandwidth = 0.0
            weighted_residual = 0.0
            weighted_efficiency = 0.0
            weighted_penalty = 0.0

            total_length = 0.0

            for s in state.propagation_slices:

                local_gimbal = abs(s.gimbal_tracking_error_urad)
                local_wander = abs(s.beam_wander_urad)
                local_chromatic = abs(state.beacon_qkd_offset_urad)

                local_disturbance = math.sqrt(
                    local_gimbal**2 + local_wander**2 + local_chromatic**2
                )

                local_stroke = 3.0 * local_disturbance

                local_greenwood = max(s.greenwood_frequency_Hz, 1.0)

                local_bandwidth = 5.0 * local_greenwood

                local_efficiency = local_bandwidth / (local_bandwidth + local_greenwood)

                local_efficiency = max(0.0, min(local_efficiency, 0.99))

                local_residual = local_disturbance * (1.0 - local_efficiency)

                if local_disturbance > 1e-9:

                    local_penalty = 4.343 * (local_residual / local_disturbance)

                else:

                    local_penalty = 0.0

                s.fsm_stroke_urad = local_stroke
                s.fsm_bandwidth_Hz = local_bandwidth
                s.fsm_residual_error_urad = local_residual
                s.fsm_tracking_efficiency = local_efficiency
                s.fsm_coupling_penalty_dB = local_penalty
                s.fsm_suppression_ratio = local_efficiency

                s.fsm_closed_loop = True

                s.fsm_settling_time_s = 4.0 / max(local_bandwidth, 1e-6)

                s.corrected_pointing_error_urad = local_residual

                s.fsm_margin_urad = local_stroke - local_disturbance
                s.notes = (
                    f"FSM Residual={local_residual:.2f} urad, "
                    f"Eff={100*local_efficiency:.1f}%"
                )

                weighted_stroke += local_stroke * s.length_m

                weighted_bandwidth += local_bandwidth * s.length_m

                weighted_residual += local_residual * s.length_m

                weighted_efficiency += local_efficiency * s.length_m

                weighted_penalty += local_penalty * s.length_m

                total_length += s.length_m
            fsm_stroke = weighted_stroke / max(total_length, 1.0)

            bandwidth = weighted_bandwidth / max(total_length, 1.0)

            residual_error = weighted_residual / max(total_length, 1.0)

            efficiency = weighted_efficiency / max(total_length, 1.0)

            coupling_penalty = weighted_penalty / max(total_length, 1.0)
            state.average_fsm_residual_urad = sum(
                s.fsm_residual_error_urad for s in state.propagation_slices
            ) / len(state.propagation_slices)

            state.maximum_fsm_residual_urad = max(
                s.fsm_residual_error_urad for s in state.propagation_slices
            )

            state.minimum_fsm_residual_urad = min(
                s.fsm_residual_error_urad for s in state.propagation_slices
            )

            state.average_fsm_bandwidth_Hz = sum(
                s.fsm_bandwidth_Hz for s in state.propagation_slices
            ) / len(state.propagation_slices)

            print()
            print("===== FSM → SLICES =====")
            print("Slices Updated :", len(state.propagation_slices))
            print("Average Residual :", state.average_fsm_residual_urad)
            print("Maximum Residual :", state.maximum_fsm_residual_urad)
            print("Average Bandwidth :", state.average_fsm_bandwidth_Hz)
            print("========================")
            print()

        # ==========================================
        # Save Results
        # ==========================================

        state.fsm_stroke_urad = fsm_stroke

        state.fsm_bandwidth_Hz = bandwidth

        state.fsm_residual_error_urad = residual_error

        state.fsm_tracking_efficiency = efficiency

        state.fsm_coupling_penalty_dB = coupling_penalty

        state.debug_message = "FSM completed"

        # ==========================================
        # Console Output
        # ==========================================

        print()

        print(f"Gimbal Error: " f"{gimbal_error:.1f} urad")

        print(f"Beam Wander: " f"{beam_wander:.1f} urad")

        print(f"Chromatic Offset: " f"{chromatic_offset:.3f} urad")

        print(f"FSM Stroke: " f"{fsm_stroke:.1f} urad")

        print(f"FSM Bandwidth: " f"{bandwidth:.1f} Hz")

        print(f"Tracking Efficiency: " f"{100.0*efficiency:.1f} %")

        print(f"Residual Error: " f"{residual_error:.2f} urad")

        print(f"Coupling Penalty: " f"{coupling_penalty:.2f} dB")
