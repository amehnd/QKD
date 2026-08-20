"""
pat.py

Pointing Acquisition and Tracking Model

Combines:

    Geometry
    Ship Motion
    Gimbal
    FSM
    Turbulence
    Chromatic Refraction

Computes:

    Acquisition Time

    Lock Probability

    Tracking Probability

    PAT Status

    Total Residual Error

Version:
    0.3
"""

import math

from core.model import Model


class PATModel(Model):

    name = "PAT"

    description = "Pointing Acquisition and Tracking"

    version = "0.3"

    inputs = [
        "gimbal_tracking_error_urad",
        "fsm_residual_error_urad",
        "beam_wander_urad",
        "beacon_qkd_offset_urad",
        "ship_los_jitter_urad",
        "link_distance_km",
    ]

    outputs = [
        "acquisition_time_s",
        "lock_probability",
        "tracking_probability",
        "tracking_error_urad",
    ]

    # -------------------------------------------------
    # Validation
    # -------------------------------------------------

    def validate(self, state):

        if state.link_distance_km <= 0:

            raise ValueError("Invalid range")

        return True

    # -------------------------------------------------
    # Execute
    # -------------------------------------------------

    def execute(self, state):

        # =============================================
        # Combined residual error
        # =============================================

        total_error = math.sqrt(
            state.gimbal_tracking_error_urad**2
            + state.fsm_residual_error_urad**2
            + state.beam_wander_urad**2
            + state.beacon_qkd_offset_urad**2
        )

        # =============================================
        # Acquisition Time
        #
        # GPS
        # +
        # Coarse PAT
        # +
        # Fine PAT
        # =============================================

        gps_time = 1.0

        coarse_time = 2.0 + state.ship_los_jitter_urad / 50000.0

        fine_time = 1.0 + total_error / 1000.0

        acquisition_time = gps_time + coarse_time + fine_time

        # =============================================
        # Lock Probability
        #
        # Logistic approximation
        # =============================================

        rx_fov = getattr(state, "rx_fov_urad", 5000.0)
        lock_probability = 1.0 - math.exp(-0.5 * (rx_fov / max(total_error, 1e-9))**2)

        lock_probability = max(0.0, min(1.0, lock_probability))

        # =============================================
        # Tracking Probability
        #
        # Depends on lock and FSM
        # =============================================

        tracking_probability = lock_probability * state.fsm_tracking_efficiency

        tracking_probability = max(0.0, min(1.0, tracking_probability))

        # ==========================================
        # v0.4 Slice PAT Model
        # ==========================================

        if state.propagation_slices:

            acquisition_sum = 0.0
            lock_sum = 0.0
            tracking_sum = 0.0
            error_sum = 0.0

            for s in state.propagation_slices:

                local_error = math.sqrt(
                    state.gimbal_tracking_error_urad**2
                    + state.fsm_residual_error_urad**2
                    + s.beam_wander_urad**2
                    + state.beacon_qkd_offset_urad**2
                )

                local_coarse = 2.0 + s.ship_los_jitter_urad / 50000.0

                local_fine = 1.0 + local_error / 1000.0

                local_acquisition = 1.0 + local_coarse + local_fine

                rx_fov = getattr(state, "rx_fov_urad", 5000.0)
                local_lock = 1.0 - math.exp(-0.5 * (rx_fov / max(local_error, 1e-9))**2)

                local_lock = max(0.0, min(local_lock, 1.0))

                local_tracking = local_lock * s.fsm_tracking_efficiency

                local_tracking = max(0.0, min(local_tracking, 1.0))

                s.acquisition_time_s = local_acquisition
                s.lock_probability = local_lock
                s.tracking_probability = local_tracking
                s.tracking_error_urad = local_error

                acquisition_sum += local_acquisition
                lock_sum += local_lock
                tracking_sum += local_tracking
                error_sum += local_error

            n = len(state.propagation_slices)

            rx = state.propagation_slices[-1]

            acquisition_time = rx.acquisition_time_s
            lock_probability = rx.lock_probability
            tracking_probability = rx.tracking_probability
            total_error = rx.tracking_error_urad

            print()
            print("===== PAT → SLICES =====")
            print("Slices Updated :", n)
            print("========================")
            print()

        # =============================================
        # Save Results
        # =============================================

        state.acquisition_time_s = acquisition_time

        state.lock_probability = lock_probability

        state.tracking_probability = tracking_probability

        state.tracking_error_urad = total_error

        state.debug_message = "PAT completed"

        # =============================================
        # Console Output
        # =============================================

        print()

        print(f"Acquisition Time: " f"{acquisition_time:.2f} s")

        print(f"Lock Probability: " f"{100*lock_probability:.1f}%")

        print(f"Tracking Probability: " f"{100*tracking_probability:.1f}%")

        print(f"Residual Tracking Error: " f"{total_error:.2f} urad")
