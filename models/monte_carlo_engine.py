"""
monte_carlo_engine.py

Monte Carlo Analysis Engine

Version:
    0.3
"""

import copy
import random
import numpy as np

from core.model import Model


class MonteCarloEngineModel(Model):

    name = "MonteCarloEngine"

    description = "Monte Carlo statistical analysis"

    version = "0.3"

    inputs = [
        "mc_num_runs",
        "mc_seed",
        "mc_visibility_sigma",
        "mc_wind_sigma",
        "mc_cn2_sigma",
        "mc_sea_state_sigma",
    ]

    outputs = ["mc_results"]

    # --------------------------------------------------
    # Validation
    # --------------------------------------------------

    def validate(self, state):

        if state.mc_num_runs < 10:

            raise ValueError("Minimum 10 runs required")

        return True

    # --------------------------------------------------
    # Sample Environment
    # --------------------------------------------------

    def sample_environment(self, state):
        vis_base = getattr(state, "effective_path_visibility_km", getattr(state, "tx_visibility_km", 10.0))
        wind_base = getattr(state, "effective_path_wind_speed_m_s", getattr(state, "tx_wind_speed_m_s", 5.0))

        visibility = max(
            0.1, random.gauss(vis_base, state.mc_visibility_sigma)
        )

        wind_speed = max(0.0, random.gauss(wind_base, state.mc_wind_sigma))

        sea_state = max(
            0, round(random.gauss(state.sea_state, state.mc_sea_state_sigma))
        )

        cn2 = max(1e-18, random.gauss(state.Cn2_m2_3, state.mc_cn2_sigma))

        return (visibility, wind_speed, sea_state, cn2)

    # --------------------------------------------------
    # Performance Approximation
    # --------------------------------------------------

    def estimate_performance(self, state, visibility, wind_speed, sea_state, cn2):

        skr = max(state.effective_secure_key_rate, 1.0)

        qber = max(state.qber, 0.001)

        availability = max(state.availability_percent, 1.0)

        # ==========================================
        # Visibility
        # ==========================================
        vis_base = getattr(state, "effective_path_visibility_km", getattr(state, "tx_visibility_km", 10.0))
        visibility_factor = visibility / max(vis_base, 0.1)

        skr *= visibility_factor

        qber /= max(visibility_factor, 0.1)

        availability *= visibility_factor

        # ==========================================
        # Wind
        # ==========================================
        wind_base = getattr(state, "effective_path_wind_speed_m_s", getattr(state, "tx_wind_speed_m_s", 5.0))
        wind_factor = wind_speed / max(wind_base, 0.1)

        skr *= wind_factor**-0.3

        qber *= wind_factor**0.2

        availability *= wind_factor**-0.1

        # ==========================================
        # Sea State
        # ==========================================

        sea_factor = (sea_state + 1) / (state.sea_state + 1)

        skr *= sea_factor**-1.0

        qber *= sea_factor

        availability *= sea_factor**-0.7

        # ==========================================
        # Turbulence
        # ==========================================

        cn2_factor = cn2 / max(state.Cn2_m2_3, 1e-18)

        skr *= cn2_factor**-0.2

        qber *= cn2_factor**0.2

        # ==========================================
        # Limits
        # ==========================================

        availability = max(0.0, min(availability, 100.0))

        qber = max(0.0, min(qber, 0.5))

        skr = max(0.0, skr)

        return (skr, qber, availability)

    # --------------------------------------------------
    # Execute
    # --------------------------------------------------

    def execute(self, state):

        random.seed(state.mc_seed)

        runs = state.mc_num_runs

        skr_values = []

        qber_values = []

        availability_values = []

        for _ in range(runs):

            visibility, wind, sea, cn2 = self.sample_environment(state)

            skr, qber, availability = self.estimate_performance(
                state, visibility, wind, sea, cn2
            )

            skr_values.append(skr)

            qber_values.append(qber)

            availability_values.append(availability)

        skr_arr = np.array(skr_values)

        qber_arr = np.array(qber_values)

        avail_arr = np.array(availability_values)

        results = {
            "runs": runs,
            # ---------------------
            # SKR
            # ---------------------
            "skr_mean": float(np.mean(skr_arr)),
            "skr_std": float(np.std(skr_arr)),
            "skr_min": float(np.min(skr_arr)),
            "skr_max": float(np.max(skr_arr)),
            "skr_95": float(np.percentile(skr_arr, 5)),
            # ---------------------
            # QBER
            # ---------------------
            "qber_mean": float(np.mean(qber_arr)),
            "qber_std": float(np.std(qber_arr)),
            "qber_min": float(np.min(qber_arr)),
            "qber_max": float(np.max(qber_arr)),
            # ---------------------
            # Availability
            # ---------------------
            "availability_mean": float(np.mean(avail_arr)),
            "availability_std": float(np.std(avail_arr)),
            "availability_min": float(np.min(avail_arr)),
            "availability_max": float(np.max(avail_arr)),
            "availability_95": float(np.percentile(avail_arr, 5)),
            # ---------------------
            # Raw Arrays
            # ---------------------
            "skr_samples": skr_values,
            "qber_samples": qber_values,
            "availability_samples": availability_values,
        }

        state.mc_results = results

        state.debug_message = "Monte Carlo completed"

        print()

        print("=== MONTE CARLO ===")

        print(f"Runs: {runs}")

        print(f"Mean SKR: " f"{results['skr_mean']:.3e}")

        print(f"Mean QBER: " f"{100*results['qber_mean']:.3f}%")

        print(f"Mean Availability: " f"{results['availability_mean']:.2f}%")
