"""
design_optimizer.py

Design Mode Optimizer

Automatically sizes:

    TX Aperture

    RX Aperture

    Beam Divergence

    Beacon Power

    Gimbal Bandwidth

    FSM Bandwidth

to achieve user targets.

Version:
    0.3
"""

import math

from core.model import Model


class DesignOptimizerModel(Model):

    name = "DesignOptimizer"

    description = "System sizing optimizer"

    version = "0.3"

    inputs = [
        "target_range_km",
        "target_skr_bps",
        "target_qber",
        "sea_state",
        "visibility_km",
        "wind_speed_m_s",
    ]

    outputs = [
        "recommended_tx_aperture_mm",
        "recommended_rx_aperture_mm",
        "recommended_divergence_mrad",
        "recommended_beacon_power_W",
        "recommended_gimbal_bandwidth_Hz",
        "recommended_fsm_bandwidth_Hz",
        "predicted_availability_percent",
        "link_margin_dB",
        "availability_day_percent",
        "availability_night_percent",
        "recommended_detector_type",
        "recommended_filter_bandwidth_nm",
        "optimization_score",
    ]

    # --------------------------------------------------
    # Validation
    # --------------------------------------------------

    def validate(self, state):

        if state.link_distance_km <= 0:

            raise ValueError("Target range invalid")

        if state.target_skr_bps <= 0:

            raise ValueError("Target SKR invalid")

        return True

    # --------------------------------------------------
    # Execute
    # --------------------------------------------------

    def execute(self, state):

        target_range = state.link_distance_km

        target_skr = state.target_skr_bps

        target_qber = state.target_qber

        sea_state = state.sea_state

        vis_tx = getattr(state, "tx_visibility_km", getattr(state, "visibility_km", 10.0))
        vis_rx = getattr(state, "rx_visibility_km", getattr(state, "visibility_km", 10.0))
        visibility = max((vis_tx + vis_rx) / 2.0, 1.0)

        w_tx = getattr(state, "tx_wind_speed_m_s", getattr(state, "wind_speed_m_s", 5.0))
        w_rx = getattr(state, "rx_wind_speed_m_s", getattr(state, "wind_speed_m_s", 5.0))
        wind_speed = max((w_tx + w_rx) / 2.0, 0.1)
        print("DESIGN OPTIMIZER RUNNING")
        # ==========================================
        # TX Aperture Estimate
        # ==========================================

        tx_aperture_mm = 75.0 + 7.5 * target_range

        if target_skr > 1e6:

            tx_aperture_mm *= 1.5

        tx_aperture_mm = min(max(tx_aperture_mm, 100), 1000)

        # ==========================================
        # RX Aperture Estimate
        # ==========================================

        rx_aperture_mm = 200.0 + 40.0 * target_range

        if target_skr > 1e6:

            rx_aperture_mm *= 1.4

        rx_aperture_mm = min(max(rx_aperture_mm, 300), 3000)

        # ==========================================
        # Divergence
        #
        # Lower divergence for
        # high SKR
        # ==========================================

        divergence_mrad = 1.0 / math.sqrt(target_range)

        divergence_mrad *= 0.5

        divergence_mrad = min(max(divergence_mrad, 0.02), 1.0)

        # ==========================================
        # Beacon Power
        # ==========================================

        beacon_power = 0.5 + target_range / 10.0

        beacon_power *= 1.0 + sea_state / 5.0

        beacon_power = min(max(beacon_power, 0.5), 20.0)

        # ==========================================
        # Gimbal BW
        # ==========================================

        gimbal_bw = 1.0 + 2.0 * sea_state

        gimbal_bw += 0.2 * wind_speed

        gimbal_bw = min(max(gimbal_bw, 2.0), 50.0)

        # ==========================================
        # FSM BW
        # ==========================================

        fsm_bw = 50.0 + 20.0 * sea_state

        fsm_bw += 5.0 * wind_speed

        fsm_bw = min(max(fsm_bw, 100.0), 5000.0)

        # ==========================================
        # Detector Recommendation
        # ==========================================

        if target_skr > 5e6:

            recommended_detector = "TES"

        elif target_skr > 1e6:

            recommended_detector = "SNSPD"

        elif visibility < 2:

            recommended_detector = "PMT"

        elif target_range > 50:

            recommended_detector = "APD"

        else:

            recommended_detector = "SPAD"

        state.recommended_detector_type = recommended_detector

        # ==========================================
        # Optical Filter Recommendation
        # ==========================================

        if visibility < 5:

            filter_bw = 0.2

        elif visibility < 20:

            filter_bw = 0.5

        else:

            filter_bw = 1.0

        state.recommended_filter_bandwidth_nm = filter_bw
        # ==========================================
        # Availability Estimate
        # ==========================================

        availability = 100.0 - 2.0 * target_range

        availability -= 4.0 * sea_state

        availability -= max(0.0, 10.0 - visibility)

        availability = max(0.0, min(availability, 99.0))

        # ------------------------------------------
        # Link Margin Estimate
        # ------------------------------------------

        link_margin = max(0.0, 20.0 - target_range)

        # ------------------------------------------
        # Day/Night Availability
        # ------------------------------------------

        availability_day = max(0.0, availability - 10.0)

        availability_night = min(99.0, availability + 5.0)

        # ==========================================
        # QBER Check
        # ==========================================

        if target_qber < 0.01:

            tx_aperture_mm *= 1.2
            rx_aperture_mm *= 1.2

        # ==========================================
        # Save Results
        # ==========================================

        state.recommended_tx_aperture_mm = tx_aperture_mm

        state.recommended_rx_aperture_mm = rx_aperture_mm

        state.recommended_divergence_mrad = divergence_mrad

        state.recommended_beacon_power_W = beacon_power

        state.recommended_gimbal_bandwidth_Hz = gimbal_bw

        state.recommended_fsm_bandwidth_Hz = fsm_bw

        state.predicted_availability_percent = availability
        state.link_margin_dB = link_margin

        state.availability_day_percent = availability_day

        state.availability_night_percent = availability_night

        optimization_score = (
            0.4 * availability
            + 0.3 * (100.0 - 200.0 * target_qber)
            + 0.3 * min(target_skr / 1e6, 100.0)
        )

        optimization_score = max(0.0, min(optimization_score, 100.0))

        state.optimization_score = optimization_score
        print("\nDESIGN DEBUG")
        print("Link Margin =", state.link_margin_dB)
        print("Availability Day =", state.availability_day_percent)
        print("Availability Night =", state.availability_night_percent)

        state.debug_message = "Design optimization completed"

        # ==========================================
        # Console Output
        # ==========================================

        print()

        print("=== DESIGN RECOMMENDATION ===")

        print(f"TX Aperture: " f"{tx_aperture_mm:.1f} mm")

        print(f"RX Aperture: " f"{rx_aperture_mm:.1f} mm")

        print(f"Divergence: " f"{divergence_mrad:.3f} mrad")

        print(f"Beacon Power: " f"{beacon_power:.2f} W")

        print(f"Gimbal BW: " f"{gimbal_bw:.1f} Hz")

        print(f"FSM BW: " f"{fsm_bw:.1f} Hz")

        print(f"Availability: " f"{availability:.1f}%")
        print(f"Detector: " f"{recommended_detector}")

        print(f"Filter BW: " f"{filter_bw:.2f} nm")

        print(f"Optimization Score: " f"{optimization_score:.1f}/100")
