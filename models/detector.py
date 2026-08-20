import math
from core.model import Model


class DetectorModel(Model):

    name = "Detector"
    description = "Single photon detector model"
    version = "0.3"

    inputs = [
        "detector_type",
        "detector_efficiency",
        "mean_photon_number",
        "pulse_rate_mhz",
        "channel_efficiency",
        "filter_overlap_fraction",
        "dark_count_rate",
        "background_count_rate",
    ]

    outputs = [
        "signal_count_rate",
        "afterpulse_count_rate",
        "deadtime_loss_fraction",
        "total_counts",
        "detection_probability",
        "detector_saturation_fraction",
    ]

    # --------------------------------------------------
    def validate(self, state):

        if state.detector_efficiency <= 0:

            state.detector_efficiency = 0.01

        if getattr(state, "pulse_rate_mhz", 200.0) <= 0:

            state.pulse_rate_mhz = 1e-6

        return True

    # --------------------------------------------------
    def execute(self, state):

        detector_type = str(getattr(state, "detector_model", "SNSPD")).upper()

        state.detector_type = detector_type
        state.detector_model = detector_type

        user_eta = max(getattr(state, "detector_efficiency", 0.85), 1e-3)

        mu = max(
            getattr(
                state,
                "mean_photon_number",
                # mentor's correction
                1.0,
            ),
            1e-3,
        )
        pulse_rate = max(
            getattr(state, "pulse_rate_mhz", 200.0) * 1e6,
            1e-3,
        )
        filter_overlap = min(
            1.0, max(getattr(state, "filter_overlap_fraction", 1.0), 0.0)
        )

        # ==========================================
        # v0.4 Adaptive Slice Detector
        # ==========================================

        if state.propagation_slices:

            channel_eff = max(getattr(state, "channel_efficiency", 1e-12), 1e-12)

        else:

            channel_eff = max(getattr(state, "channel_efficiency", 1e-12), 1e-12)

        dark_counts = max(getattr(state, "dark_count_rate", 100.0), 0.0)
        print("\nDARK COUNT DEBUG")
        print("state.dark_count_rate =", state.dark_count_rate)
        print("dark_counts =", dark_counts)
        background_counts = max(getattr(state, "background_count_rate", 0.1), 0.0)

        gate_eff = getattr(state, "gate_efficiency", 1.0)

        background_counts *= gate_eff
        dark_counts *= gate_eff

        # Detector Parameters
        # ==========================================

        if detector_type == "SPAD":

            eta = 0.60

            dead_time_ns = 50.0

            afterpulse_prob = 0.02

            max_count_rate = 1e7

        elif detector_type == "SNSPD":

            default_eta = 0.95

            eta = (
                user_eta
                if getattr(state, "use_custom_detector_efficiency", False)
                else default_eta
            )

            dead_time_ns = 20.0

            afterpulse_prob = 0.003

            max_count_rate = 1e8

        elif detector_type == "APD":

            eta = 0.70

            dead_time_ns = 30.0

            afterpulse_prob = 0.01

            max_count_rate = 5e7

        elif detector_type == "PMT":

            eta = 0.30

            dead_time_ns = 10.0

            afterpulse_prob = 0.0

            max_count_rate = 1e8

        elif detector_type == "TES":

            eta = 0.98

            dead_time_ns = 1000.0

            afterpulse_prob = 0.0

            max_count_rate = 1e6

        else:

            eta = user_eta

            dead_time_ns = 50.0

            afterpulse_prob = 0.01

            max_count_rate = 1e7

        dead_time_ns = getattr(state, "detector_deadtime_ns", 0.0)

        if dead_time_ns <= 0.0:
            dead_time_ns = {
                "SNSPD": 20.0,
                "SPAD": 50.0,
                "APD": 30.0,
                "PMT": 10.0,
                "TES": 1000.0,
            }.get(detector_type, 50.0)
        dead_time_s = dead_time_ns * 1e-9

        if getattr(state, "use_custom_detector_efficiency", False):

            eta = user_eta

        # ==========================================
        # Signal Detection Probability
        # ==========================================

        try:

            effective_channel = channel_eff * filter_overlap

            signal_detection_probability = 1.0 - math.exp(-mu * effective_channel * eta)

        except OverflowError:

            signal_detection_probability = 1.0

        signal_detection_probability = max(0.0, min(signal_detection_probability, 1.0))

        # ==========================================
        # Signal Count Rate
        # ==========================================

        signal_count_rate = pulse_rate * signal_detection_probability

        signal_count_rate *= gate_eff

        # ==========================================
        # Raw Total Rate
        # ==========================================

        raw_rate = signal_count_rate + dark_counts + background_counts

        # ==========================================
        # Dead Time Correction
        # ==========================================

        print("\nDEADTIME DEBUG")
        print("raw_rate =", raw_rate)
        print("dead_time_ns =", dead_time_ns)
        print("dead_time_s =", dead_time_s)
        print("raw_rate * dead_time_s =", raw_rate * dead_time_s)

        if raw_rate > 0:
            observed_rate = raw_rate / (1.0 + raw_rate * dead_time_s)
        else:
            observed_rate = 0.0

        deadtime_loss = 1.0 - observed_rate / max(raw_rate, 1.0)
        deadtime_fraction = observed_rate / max(raw_rate, 1.0)
        
        signal_count_rate *= deadtime_fraction
        background_counts *= deadtime_fraction
        dark_counts *= deadtime_fraction

        print("observed_rate =", observed_rate)
        print("deadtime_loss =", deadtime_loss)
        print("deadtime_loss_percent =", 100.0 * deadtime_loss)

        observed_rate = min(observed_rate, max_count_rate)
        detector_saturation_fraction = observed_rate / max(max_count_rate, 1.0)

        detector_saturation_fraction = max(0.0, min(1.0, detector_saturation_fraction))

        # ==========================================
        # Afterpulsing
        # ==========================================

        afterpulse_counts = observed_rate * afterpulse_prob

        # ==========================================
        # Final Counts
        # ==========================================

        total_counts = observed_rate + afterpulse_counts

        # ==========================================
        # Detection Probability
        # ==========================================

        detection_probability = total_counts / max(pulse_rate, 1e-12)
        detection_probability = min(detection_probability, 1.0)

        # ==========================================
        # SAVE RESULTS (ONLY ONCE — NO OVERWRITES)
        # ==========================================

        if state.propagation_slices:

            for s in state.propagation_slices:

                local_channel = s.cumulative_transmission * filter_overlap
                s.effective_channel_efficiency = local_channel

                local_probability = 1.0 - math.exp(-mu * local_channel * eta)
                s.signal_detection_probability = local_probability

                local_signal = pulse_rate * local_probability

                local_signal *= gate_eff

                local_background = getattr(
                    s, "background_count_rate", background_counts
                )

                local_dark = dark_counts
                s.dark_count_rate = local_dark

                local_raw = local_signal + local_background + local_dark

                if local_raw > 0:

                    local_observed = local_raw / (1.0 + local_raw * dead_time_s)
                    local_fraction = local_observed / local_raw

                else:

                    local_observed = 0.0
                    local_fraction = 1.0
                    
                local_signal *= local_fraction
                local_background *= local_fraction
                local_dark *= local_fraction

                local_afterpulse = local_observed * afterpulse_prob

                local_total = local_observed + local_afterpulse

                s.signal_count_rate = local_signal

                s.background_count_rate = local_background

                s.dark_count_rate = local_dark

                s.afterpulse_count_rate = local_afterpulse

                s.total_counts = local_total
                s.observed_count_rate = local_observed

                s.detection_probability = local_total / max(pulse_rate, 1e-12)

                s.detector_efficiency = eta

                s.detector_saturation_fraction = min(
                    local_observed / max_count_rate, 1.0
                )
                s.deadtime_loss_fraction = 1.0 - local_observed / max(local_raw, 1.0)
                s.detector_type = detector_type
                s.filter_overlap_fraction = filter_overlap

                s.notes = (
                    f"Signal={local_signal:.2e}, "
                    f"Background={local_background:.2e}, "
                    f"Total={local_total:.2e}"
                )

            state.signal_count_rate = signal_count_rate
            state.background_count_rate = background_counts
            state.afterpulse_count_rate = afterpulse_counts
            state.total_counts = total_counts
            state.detection_probability = detection_probability
            state.detector_saturation_fraction = detector_saturation_fraction
            state.observed_count_rate = observed_rate
            state.deadtime_loss_fraction = deadtime_loss
            state.dark_count_rate = dark_counts

            print()
            print("===== DETECTOR → SLICES =====")

            for s in state.propagation_slices[:5]:

                print(
                    f"Slice {s.slice_id}: "
                    f"Signal={s.signal_count_rate:.2e} "
                    f"Background={s.background_count_rate:.2e}"
                )

            print("=============================")
            print()

        if not state.propagation_slices:

            state.signal_count_rate = signal_count_rate
            state.afterpulse_count_rate = afterpulse_counts
            state.deadtime_loss_fraction = deadtime_loss
            state.total_counts = total_counts
            state.observed_count_rate = observed_rate
            state.background_count_rate = background_counts
            state.dark_count_rate = dark_counts
            state.detection_probability = detection_probability
            state.detector_saturation_fraction = detector_saturation_fraction

        state.detector_deadtime_ns = dead_time_ns
        state.maximum_detector_rate = max_count_rate
        state.filter_overlap_fraction = filter_overlap
        state.effective_channel_efficiency = effective_channel
        state.detector_efficiency = eta

        state.debug_message = "Detector completed"

        # ==========================================
        # OUTPUT
        # ==========================================

        print()
        print(f"Detector Type: {detector_type}")
        print(f"Signal Count Rate: {signal_count_rate:.3e} cps")
        print(f"Background Count Rate: {background_counts:.3e} cps")
        print(f"Dark Count Rate: {dark_counts:.3e} cps")
        print(f"Afterpulse Rate: {afterpulse_counts:.3e} cps")
        print(f"Deadtime Loss: {100.0 * deadtime_loss:.2f}%")
        print(f"Total Counts: {total_counts:.3e} cps")
        print(f"Detection Probability: {detection_probability:.6f}")
        print(f"Detector Saturation: " f"{100 * detector_saturation_fraction:.2f}%")

        print("\nDETECTOR DEBUG")
        print("mu =", mu)
        print("pulse_rate =", pulse_rate)
        print("channel_eff =", channel_eff)
        print("filter_overlap =", filter_overlap)
        print("effective_channel =", effective_channel)
        print("eta =", eta)
        print("signal_detection_probability =", signal_detection_probability)
        print("\n===== DETECTOR OUTPUT =====")
        print("Background =", state.background_count_rate)
        print("Dark =", state.dark_count_rate)
        print("===========================\n")

        # ==========================================
        # VERIFIER TEXT GENERATION
        # ==========================================
        state.verifier_text["det"] = f"""
Channel Efficiency
η_eff = η_channel · Filter_Overlap = {effective_channel:.6e}

Signal Count Rate
P_signal = 1 - exp(-μ · η_eff · η_det) = {signal_detection_probability:.6f}
R_signal,raw = f_rep · P_signal = {pulse_rate * signal_detection_probability:.2e} cps
R_total,raw = R_signal,raw + R_dark + R_bg = {raw_rate:.2e} cps
R_obs = R_total,raw / (1 + R_total,raw · T_dead) = {observed_rate:.2e} cps
f_dead = 1 - (R_obs / R_total,raw) = {deadtime_fraction:.4f}
R_signal = R_signal,raw · (1 - f_dead) = {state.signal_count_rate:.2e} cps

Background Count Rate
R_bg' = R_bg · (1 - f_dead) = {state.background_count_rate:.2e} cps

Dark Count Rate
R_dark' = R_dark · (1 - f_dead) = {state.dark_count_rate:.2e} cps

Afterpulse Count Rate
R_ap = P_ap · R_obs = {state.afterpulse_count_rate:.2e} cps

Deadtime Loss
L_dead = f_dead = {deadtime_loss:.4f}

Total Counts
R_total = R_obs + R_ap = {state.total_counts:.2e} cps

Detector Saturation
Saturation = min(1, R_total,raw · T_dead) = {detector_saturation_fraction:.4f}

Detection Probability
P_det = 1 - exp(-η_det · η_eff) = {getattr(state, 'detection_probability', 0.0):.6f}

Background Power
P_bg = Computed from solar environment = {getattr(state, 'background_power_W', 0.0):.4e} W

Background Photon Rate
R_bg,photon = P_bg / (h · ν) = {getattr(state, 'background_photon_rate', 0.0):.4e} photons/s

Moon Phase
Phase_moon = {getattr(state, 'moon_phase_percent', 0.0):.2f} %
"""
