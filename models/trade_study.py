"""
trade_study.py

Trade Study Engine

Performs parameter sweeps and
sensitivity analysis.

Version:
    0.3
"""

import copy
import numpy as np

from core.model import Model


class TradeStudyModel(Model):

    name = "TradeStudy"

    description = "Parameter sweep engine"

    version = "0.3"

    inputs = ["trade_parameter", "trade_start", "trade_stop", "trade_steps"]

    outputs = [
        "trade_x",
        "trade_skr",
        "trade_qber",
        "trade_availability",
        "trade_snr",
        "trade_link_margin",
        "trade_score",
    ]

    # --------------------------------------------------
    # Validation
    # --------------------------------------------------

    def validate(self, state):

        if state.trade_steps < 2:

            raise ValueError("trade_steps must be >=2")

        return True

    # --------------------------------------------------
    # Safe performance estimate
    #
    # V0.3 uses current model outputs
    # without rerunning entire kernel.
    #
    # V0.4 will rerun full simulation
    # for every point.
    # --------------------------------------------------

    def estimate_performance(self, state, parameter, value):

        base_skr = max(state.effective_secure_key_rate, 1.0)

        base_qber = max(state.qber, 0.001)

        base_availability = max(state.availability_percent, 1.0)

        skr = base_skr
        qber = base_qber
        availability = base_availability

        # ==========================================
        # Range
        # ==========================================

        if parameter == "link_distance_km":

            ratio = value / max(state.link_distance_km, 0.1)

            skr *= ratio**-2.0

            qber *= ratio**0.5

            availability *= ratio**-0.3

        # ==========================================
        # Visibility
        # ==========================================

        elif parameter in ["visibility_km", "tx_visibility_km", "rx_visibility_km"]:
            vis_base = getattr(state, "tx_visibility_km", getattr(state, "visibility_km", 10.0))
            ratio = value / max(vis_base, 0.1)

            skr *= ratio
            qber /= max(ratio, 0.1)
            availability *= ratio

        # ==========================================
        # Sea State
        # ==========================================

        elif parameter == "sea_state":

            ratio = value / max(state.sea_state, 1)

            skr *= ratio**-1.2
            qber *= ratio
            availability *= ratio**-1.0

        # ==========================================
        # Wind
        # ==========================================

        elif parameter in ["wind_speed_m_s", "tx_wind_speed_m_s", "rx_wind_speed_m_s"]:
            wind_base = getattr(state, "tx_wind_speed_m_s", getattr(state, "wind_speed_m_s", 5.0))
            ratio = value / max(wind_base, 0.1)

            skr *= ratio**-0.5
            qber *= ratio**0.4
            availability *= ratio**-0.3

        # ==========================================
        # Divergence
        # ==========================================

        elif parameter == "tx_beam_divergence_mrad":

            ratio = value / max(state.tx_beam_divergence_mrad, 0.001)

            skr *= ratio**-1.0

            qber *= ratio**0.3

        availability = max(0.0, min(availability, 100.0))

        qber = max(0.0, min(qber, 0.5))

        skr = max(0.0, skr)

        return (skr, qber, availability)

    # --------------------------------------------------
    # Execute
    # --------------------------------------------------

    def execute(self, state):

        parameter = state.trade_parameter

        start = state.trade_start

        stop = state.trade_stop

        steps = state.trade_steps

        x_values = np.linspace(start, stop, steps)

        skr_values = []

        qber_values = []

        availability_values = []

        snr_values = []

        link_margin_values = []

        score_values = []

        for x in x_values:

            skr, qber, avail = self.estimate_performance(state, parameter, x)

            skr_values.append(float(skr))

            qber_values.append(float(qber))

            availability_values.append(float(avail))

        # ==========================================
        # Store Results
        # ==========================================

        state.trade_x = list(x_values)

        state.trade_skr = skr_values

        state.trade_qber = qber_values

        state.trade_availability = availability_values

        state.debug_message = "Trade study completed"

        # ==========================================
        # Console Summary
        # ==========================================

        print()

        print("=== TRADE STUDY ===")

        print(f"Parameter: " f"{parameter}")

        print(f"Range: " f"{start} → {stop}")

        print(f"Steps: " f"{steps}")

        print()

        print(f"First SKR: " f"{skr_values[0]:.3e}")

        print(f"Last SKR: " f"{skr_values[-1]:.3e}")

        print(f"First QBER: " f"{100*qber_values[0]:.2f}%")

        print(f"Last QBER: " f"{100*qber_values[-1]:.2f}%")
