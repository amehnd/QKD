"""
gimbal.py

Maritime Gimbal Tracking Model

Computes:

    Azimuth Angle

    Elevation Angle

    Tracking Rates

    Tracking Accelerations

    Required Bandwidth

    Residual Pointing Error

Version:
    0.3
"""

import math

from core.model import Model


class GimbalModel(Model):

    name = "Gimbal"

    description = "Coarse tracking gimbal model"

    version = "0.3"

    inputs = [
        "link_distance_km",
        "tx_height_msl_m",
        "rx_height_msl_m",
        "roll_rms_deg",
        "pitch_rms_deg",
        "yaw_rms_deg",
        "roll_rate_deg_s",
        "pitch_rate_deg_s",
        "yaw_rate_deg_s",
        "effective_elevation_bias_urad",
    ]

    outputs = [
        "gimbal_azimuth_deg",
        "gimbal_elevation_deg",
        "gimbal_rate_deg_s",
        "gimbal_acceleration_deg_s2",
        "gimbal_bandwidth_Hz",
        "gimbal_tracking_error_urad",
    ]

    # --------------------------------------------------
    # Validation
    # --------------------------------------------------

    def validate(self, state):

        if not state.propagation_slices:
            raise ValueError("BeamPropagation must run before Gimbal.")

        return True

    # --------------------------------------------------
    # Execute
    # --------------------------------------------------

    def execute(self, state):

        range_m = state.link_distance_km * 1000.0

        tx_h = state.tx_height_msl_m

        rx_h = state.rx_height_msl_m

        # ==========================================
        # Geometry
        # ==========================================

        delta_h = rx_h - tx_h

        elevation_rad = math.atan2(delta_h, range_m)

        elevation_deg = math.degrees(elevation_rad)

        # ==========================================
        # Refraction Bias
        # ==========================================

        elevation_deg += state.effective_elevation_bias_urad / 1e6 * 180.0 / math.pi

        # ==========================================
        # Azimuth from Geometry Model
        # ==========================================

        azimuth_deg = getattr(state, "bearing_deg", 0.0)
        # ==========================================
        # Required Tracking Rate
        # ==========================================

        total_rate = math.sqrt(
            state.roll_rate_deg_s**2
            + state.pitch_rate_deg_s**2
            + state.yaw_rate_deg_s**2
        )

        # ==========================================
        # Angular Acceleration
        #
        # Engineering estimate
        # ==========================================

        accel = 2.0 * math.pi * total_rate

        # ==========================================
        # Required Servo Bandwidth
        #
        # Rule:
        #
        # BW > 3× dominant frequency
        # ==========================================

        dominant_frequency = total_rate / 10.0

        bandwidth = max(1.0, 3.0 * dominant_frequency)

        # ==========================================
        # Residual Tracking Error
        #
        # Assume closed-loop suppression
        # ==========================================

        ship_motion_urad = (
            math.sqrt(
                state.roll_rms_deg**2 + state.pitch_rms_deg**2 + state.yaw_rms_deg**2
            )
            * math.pi
            / 180.0
            * 1e6
        )

        suppression_ratio = bandwidth / (bandwidth + dominant_frequency)

        residual_error = ship_motion_urad * (1.0 - suppression_ratio)

        # ==========================================
        # v0.4 Slice Gimbal Model
        # ==========================================

        if getattr(state, "propagation_slices", None):

            elevation_sum = 0.0
            rate_sum = 0.0
            accel_sum = 0.0
            bandwidth_sum = 0.0
            residual_sum = 0.0

            for s in state.propagation_slices:

                local_elevation = elevation_deg

                local_elevation += s.ray_bending_urad / 1e6 * 180.0 / math.pi

                local_rate = math.sqrt(
                    s.roll_rate_deg_s**2 + s.pitch_rate_deg_s**2 + s.yaw_rate_deg_s**2
                )

                local_accel = 2.0 * math.pi * local_rate

                local_frequency = local_rate / 10.0

                local_bandwidth = max(1.0, 3.0 * local_frequency)

                local_motion = (
                    math.sqrt(s.roll_rms_deg**2 + s.pitch_rms_deg**2 + s.yaw_rms_deg**2)
                    * math.pi
                    / 180.0
                    * 1e6
                )

                suppression = local_bandwidth / (local_bandwidth + local_frequency)

                local_residual = local_motion * (1.0 - suppression)

                s.gimbal_azimuth_deg = azimuth_deg
                s.gimbal_elevation_deg = local_elevation
                s.gimbal_rate_deg_s = local_rate
                s.gimbal_acceleration_deg_s2 = local_accel
                s.gimbal_bandwidth_Hz = local_bandwidth
                s.gimbal_tracking_error_urad = local_residual
                s.gimbal_pointing_error_rad = local_residual * 1e-6

                s.gimbal_pointing_error_deg = local_residual * 1e-6 * 180.0 / math.pi

                s.gimbal_tracking_quality = max(0.0, 1.0 - local_residual / 1000.0)

                s.gimbal_settling_time_s = 4.0 / max(local_bandwidth, 1e-6)

                s.gimbal_closed_loop = True
                s.notes = f"Gimbal Error={local_residual:.2f} urad"

                elevation_sum += local_elevation
                rate_sum += local_rate
                accel_sum += local_accel
                bandwidth_sum += local_bandwidth
                residual_sum += local_residual

            n = len(state.propagation_slices)
            state.average_gimbal_error_urad = (
                sum(s.gimbal_tracking_error_urad for s in state.propagation_slices) / n
            )

            state.maximum_gimbal_error_urad = max(
                s.gimbal_tracking_error_urad for s in state.propagation_slices
            )

            state.minimum_gimbal_error_urad = min(
                s.gimbal_tracking_error_urad for s in state.propagation_slices
            )

            state.average_gimbal_bandwidth_Hz = (
                sum(s.gimbal_bandwidth_Hz for s in state.propagation_slices) / n
            )

            elevation_deg = elevation_sum / n
            total_rate = rate_sum / n
            accel = accel_sum / n
            bandwidth = bandwidth_sum / n
            residual_error = residual_sum / n

            print()
            print("===== GIMBAL → SLICES =====")
            print("Slices Updated :", n)
            print("Average Error :", state.average_gimbal_error_urad)
            print("Maximum Error :", state.maximum_gimbal_error_urad)
            print("Average BW :", state.average_gimbal_bandwidth_Hz)
            print("===========================")
            print()

        # ==========================================
        # Save Results
        # ==========================================

        state.gimbal_azimuth_deg = azimuth_deg

        state.gimbal_elevation_deg = elevation_deg

        state.gimbal_rate_deg_s = total_rate

        state.gimbal_acceleration_deg_s2 = accel

        state.gimbal_bandwidth_Hz = bandwidth

        state.gimbal_tracking_error_urad = residual_error

        state.debug_message = "Gimbal completed"

        # ==========================================
        # Console Output
        # ==========================================

        print()

        print(f"Azimuth: " f"{azimuth_deg:.3f} deg")

        print(f"Elevation: " f"{elevation_deg:.3f} deg")

        print(f"Tracking Rate: " f"{total_rate:.3f} deg/s")

        print(f"Acceleration: " f"{accel:.3f} deg/s²")

        print(f"Bandwidth: " f"{bandwidth:.3f} Hz")

        print(f"Residual Error: " f"{residual_error:.0f} urad")
