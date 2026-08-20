"""
ship_motion.py

Ship Motion Model

Approximates motion of a naval vessel
(Shivalik-class size) due to sea state.

Computes:

    Roll RMS

    Pitch RMS

    Yaw RMS

    Angular Rates

    LOS Disturbance

Version:
    0.3
"""

import math

from core.model import Model


class ShipMotionModel(Model):

    name = "ShipMotion"

    description = "Ship motion due to sea state"

    version = "0.3"

    inputs = [
        "sea_state",
        "sig_wave_height_m",
        "wave_period_s",
        "wave_direction_deg",
        "link_distance_km",
    ]

    outputs = [
        "roll_rms_deg",
        "pitch_rms_deg",
        "yaw_rms_deg",
        "roll_rate_deg_s",
        "pitch_rate_deg_s",
        "yaw_rate_deg_s",
        "ship_los_jitter_urad",
    ]

    # --------------------------------------------------
    # Validation
    # --------------------------------------------------

    def validate(self, state):
        if not state.propagation_slices:
            raise ValueError("Adaptive slicing must run before ShipMotion.")

        if getattr(state, "wave_height_m", 0.0) < 0:
            raise ValueError("Invalid wave height")

        return True

    # --------------------------------------------------
    # Execute
    # --------------------------------------------------

    def execute(self, state):
        tx_wind = getattr(state, "tx_wind_speed_m_s", getattr(state, "wind_speed_m_s", 5.0))
        print()
        print("===== SHIP MOTION INPUTS =====")
        print("Sea State =", state.sea_state)
        print("Wave Height =", state.wave_height_m)
        print("Wave Period =", state.wave_period_s)
        print("Wind Speed =", tx_wind)
        print("Wave Direction =", state.wave_direction_deg)
        print("Ship Heading =", state.ship_heading_deg)
        print("==============================")
        print()

        # ==========================================
        # Motion calculation
        # ==========================================

        Hs = max(state.wave_height_m, 0.01)

        T = max(state.wave_period_s, 1.0)

        sea_state = state.sea_state

        tracking_mode = getattr(state, "tracking_mode", "Manual")
        print("Tracking Mode =", tracking_mode)

        relative_wave = abs(state.wave_direction_deg - state.ship_heading_deg) % 360
        if relative_wave > 180:
            relative_wave = 360 - relative_wave

        rx_wind = getattr(state, "rx_wind_speed_m_s", getattr(state, "wind_speed_m_s", 5.0))
        tx_wind_factor = 1.0 + (tx_wind / 30.0)
        rx_wind_factor = 1.0 + (rx_wind / 30.0)

        roll_direction = abs(math.sin(math.radians(relative_wave)))
        pitch_direction = abs(math.cos(math.radians(relative_wave)))
        yaw_direction = 0.5 + 0.5 * roll_direction

        # Transmitter ship motion
        roll_rms_tx = 0.8 * Hs * math.sqrt(T / 6.0) * tx_wind_factor * max(roll_direction, 0.1)
        pitch_rms_tx = 0.45 * Hs * math.sqrt(T / 6.0) * tx_wind_factor * max(pitch_direction, 0.1)
        yaw_rms_tx = 0.25 * Hs * math.sqrt(T / 6.0) * tx_wind_factor * yaw_direction

        # Receiver ship motion
        roll_rms_rx = 0.8 * Hs * math.sqrt(T / 6.0) * rx_wind_factor * max(roll_direction, 0.1)
        pitch_rms_rx = 0.45 * Hs * math.sqrt(T / 6.0) * rx_wind_factor * max(pitch_direction, 0.1)
        yaw_rms_rx = 0.25 * Hs * math.sqrt(T / 6.0) * rx_wind_factor * yaw_direction

        roll_rms = (roll_rms_tx + roll_rms_rx) / 2.0
        pitch_rms = (pitch_rms_tx + pitch_rms_rx) / 2.0
        yaw_rms = (yaw_rms_tx + yaw_rms_rx) / 2.0
        print("roll_direction =", roll_direction)
        print("pitch_direction =", pitch_direction)
        print("yaw_direction =", yaw_direction)

        print("ROLL =", roll_rms)
        print("PITCH =", pitch_rms)
        print("YAW =", yaw_rms)

        # ==========================================
        # Sea State Scaling
        # ==========================================

        if tracking_mode == "Wave":
            sea_factor = 1.0 + 0.10 * sea_state
            roll_rms *= sea_factor
            pitch_rms *= sea_factor
            yaw_rms *= sea_factor
            
            state.roll_rms_deg = roll_rms
            state.pitch_rms_deg = pitch_rms
            state.yaw_rms_deg = yaw_rms
            
        elif tracking_mode == "Manual":
            roll_rms = getattr(state, "roll_rms_deg", 0.0)
            pitch_rms = getattr(state, "pitch_rms_deg", 0.0)
            yaw_rms = getattr(state, "yaw_rms_deg", 0.0)
            
        else:
            state.roll_rms_deg = roll_rms
            state.pitch_rms_deg = pitch_rms
            state.yaw_rms_deg = yaw_rms
        # ==========================================
        # Angular Rates
        #
        # sinusoidal approximation
        # ==========================================

        omega = 2.0 * math.pi / T

        roll_rate = roll_rms * omega

        pitch_rate = pitch_rms * omega

        yaw_rate = yaw_rms * omega

        # ==========================================
        # LOS Disturbance
        #
        # Combine RMS motions
        # ==========================================

        total_deg = math.sqrt(roll_rms**2 + pitch_rms**2 + yaw_rms**2)

        ship_los_jitter_urad = total_deg * math.pi / 180.0 * 1e6

        # ==========================================
        # Pointing displacement at receiver
        # ==========================================

        range_m = state.link_distance_km * 1000.0

        pointing_shift_m = ship_los_jitter_urad * 1e-6 * range_m

        # Always use the final values stored in the state

        total_deg = math.sqrt(roll_rms**2 + pitch_rms**2 + yaw_rms**2)

        ship_los_jitter_urad = total_deg * math.pi / 180.0 * 1e6

        pointing_shift_m = ship_los_jitter_urad * 1e-6 * range_m
        state.roll_rate_deg_s = roll_rate

        state.pitch_rate_deg_s = pitch_rate

        state.yaw_rate_deg_s = yaw_rate

        state.ship_los_jitter_urad = ship_los_jitter_urad

        state.ship_pointing_shift_m = pointing_shift_m
        # ======================================
        # v0.4 Propagation Slice Ship Motion
        # ======================================

        if state.propagation_slices:

            n = len(state.propagation_slices)

            for s in state.propagation_slices:

                s.roll_rms_deg = roll_rms
                s.pitch_rms_deg = pitch_rms
                s.yaw_rms_deg = yaw_rms
                s.total_ship_motion_deg = total_deg
                s.pointing_angle_urad = ship_los_jitter_urad

                s.roll_rate_deg_s = roll_rate
                s.pitch_rate_deg_s = pitch_rate
                s.yaw_rate_deg_s = yaw_rate

                s.ship_los_jitter_urad = ship_los_jitter_urad
                s.ship_pointing_shift_m = ship_los_jitter_urad * 1e-6 * s.center_m

            print()
            print("===== SHIP MOTION → SLICES =====")
            print("Slices Updated :", n)
            print("================================")
            print()
        print("AFTER SHIP MOTION")
        print("Roll =", state.roll_rms_deg)
        print("Pitch =", state.pitch_rms_deg)
        print("Yaw =", state.yaw_rms_deg)

        state.debug_message = "Ship motion completed"
        s.notes = (
            f"Roll={roll_rms:.2f}°, " f"Pitch={pitch_rms:.2f}°, " f"Yaw={yaw_rms:.2f}°"
        )

        # ==========================================
        # Console Output
        # ==========================================

        print()

        print(f"Sea State: " f"{sea_state}")

        print(f"Wave Height: " f"{Hs:.2f} m")

        print(f"Roll RMS: " f"{roll_rms:.2f} deg")

        print(f"Pitch RMS: " f"{pitch_rms:.2f} deg")

        print(f"Yaw RMS: " f"{yaw_rms:.2f} deg")

        print(f"Roll Rate: " f"{roll_rate:.2f} deg/s")

        print(f"Pitch Rate: " f"{pitch_rate:.2f} deg/s")

        print(f"Yaw Rate: " f"{yaw_rate:.2f} deg/s")

        print(f"LOS Jitter: " f"{ship_los_jitter_urad:.0f} urad")

        print(f"Pointing Shift: " f"{pointing_shift_m:.2f} m")
