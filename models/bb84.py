"""
bb84.py

BB84 Protocol Model

Computes:

    Raw Key Rate

    Sifted Key Rate

    QBER

    Binary Entropy

    Secret Fraction

Version:
    0.3
"""

import math

from core.model import Model


class BB84Model(Model):

    name = "BB84"

    description = "BB84 protocol performance model"

    version = "0.3"

    inputs = [
        "pulse_rate_mhz",
        "signal_count_rate",
        "dark_count_rate",
        "background_count_rate",
        "afterpulse_count_rate",
        "polarization_error_rate",
        "tracking_error_urad",
        "basis_probability_z",
        "basis_probability_x",
        "authentication_cost_bits",
        "finite_key_block_size",
    ]

    outputs = [
        "raw_key_rate",
        "sifted_key_rate",
        "qber",
        "binary_entropy",
        "secret_fraction",
        "noise_counts",
        "signal_to_noise_ratio",
        "visibility",
        "secure_detection_fraction",
        "error_correction_leakage",
        "privacy_amplification_loss",
    ]

    # --------------------------------------------------
    # Validation
    # --------------------------------------------------

    def validate(self, state):

        if getattr(state, "pulse_rate_mhz", 200.0) <= 0:

            state.pulse_rate_mhz = 1e-6

        return True

    # --------------------------------------------------
    # Binary Entropy
    # --------------------------------------------------

    def binary_entropy(self, p):

        p = max(1e-12, min(p, 1.0 - 1e-12))

        return -p * math.log2(p) - (1.0 - p) * math.log2(1.0 - p)

    # --------------------------------------------------
    # Execute
    # --------------------------------------------------

    def execute(self, state):

        signal_counts = max(state.signal_count_rate, 0.0)

        background_counts = max(state.background_count_rate, 0.0)

        afterpulse_counts = max(state.afterpulse_count_rate, 0.0)

        dark_counts = max(state.dark_count_rate, 0.0)

        background_counts = max(background_counts, 0.0)

        afterpulse_counts = max(afterpulse_counts, 0.0)

        total_noise = dark_counts + background_counts + afterpulse_counts

        state.noise_counts = total_noise

        # ==========================================
        # Raw Detection Rate
        # ==========================================

        # Total detector clicks
        raw_detection_rate = signal_counts + total_noise

        raw_key_rate = signal_counts + total_noise
        signal_to_noise_ratio = signal_counts / max(
            dark_counts + background_counts, 1e-12
        )

        state.signal_to_noise_ratio = signal_to_noise_ratio
        visibility = signal_counts / max(signal_counts + total_noise, 1e-12)

        state.visibility = visibility

        # ==========================================
        # BB84 Basis Sifting
        #
        # 50%
        # ==========================================

        basis_probability_z = getattr(state, "basis_probability_z", 0.5)
        basis_probability_x = getattr(state, "basis_probability_x", 1.0 - basis_probability_z)
        sift_probability = basis_probability_z**2 + basis_probability_x**2
        sifted_key_rate = sift_probability * (signal_counts + total_noise)
        # ==========================================
        # Noise-Induced QBER
        #
        # Random counts produce
        # 50% errors.

        # Noise QBER (STABLE VERSION)
        # ==========================
        noise_qber = 0.5 * total_noise / max(signal_counts + total_noise, 1e-12)
        noise_qber_total = noise_qber
        # ==========================================
        # Polarization Error
        # ==========================================

        # ==========================
        # Polarization QBER (BOUND)
        # ==========================
        polarization_qber = getattr(
            state, "polarization_qber", getattr(state, "polarization_error_rate", 0.01)
        )
        # ==========================================
        # Tracking Error Contribution
        #
        # Engineering approximation
        # ==========================================

        # ==========================
        # Tracking QBER (FIXED SCALE)
        # ==========================
        tracking_qber = min(0.08, getattr(state, "tracking_error_urad", 0.0) / 1e6)

        sync_qber = getattr(state, "sync_qber", 0.0)
        # ==========================================
        # Total QBER
        # ==========================================

        qber = noise_qber + polarization_qber + tracking_qber + sync_qber

        qber = max(0.0, min(qber, 0.5))

        # ==========================================
        # Binary Entropy
        # ==========================================
        print()
        print("QBER DEBUG")
        print("----------------")
        print("noise_qber =", noise_qber)
        print("polarization_qber =", polarization_qber)
        print("tracking_qber =", tracking_qber)
        print("sync_qber =", sync_qber)
        print("Final qber =", qber)
        print()
        print("QBER RAW DEBUG")
        print("----------------")
        print("qber =", qber)
        print("qber_percent =", qber * 100)

        entropy = self.binary_entropy(qber)
        print("Computed Entropy =", entropy)

        if qber < 0.11:
            print("Expected Secret Fraction =", 1.0 - 2.0 * entropy)

        # ==========================================
        # Secret Fraction
        #
        # Asymptotic BB84
        # ==========================================

        # practical BB84 secret fraction model
        f_ec = getattr(state, "error_correction_factor", 1.16)
        if qber < 0.11:
            secret_fraction = 1.0 - (1.0 + f_ec) * entropy
        else:
            secret_fraction = 0.0

        secret_fraction = max(0.0, min(secret_fraction, 1.0))
        secure_detection_fraction = visibility * secret_fraction

        state.secure_detection_fraction = secure_detection_fraction

        # ==========================================
        # Save Results
        # ==========================================

        state.raw_key_rate = raw_key_rate

        state.sifted_key_rate = sifted_key_rate

        state.qber = qber
        state.noise_qber = noise_qber

        state.polarization_qber = polarization_qber

        state.tracking_qber = tracking_qber
        state.sync_qber = sync_qber

        state.binary_entropy = entropy

        state.secret_fraction = secret_fraction
        state.signal_to_noise_ratio = signal_to_noise_ratio
        state.visibility = visibility

        state.raw_detection_rate = raw_detection_rate
        if state.propagation_slices:

            for s in state.propagation_slices:

                signal = getattr(s, "signal_count_rate", 0.0)

                background = s.background_count_rate

                dark = getattr(s, "dark_count_rate", state.dark_count_rate)

                afterpulse = getattr(s, "afterpulse_count_rate", 0.0)

                noise = background + dark + afterpulse

                raw_detection = signal + noise
                s.signal_counts = signal
                s.background_counts = background
                s.dark_counts = dark
                s.afterpulse_counts = afterpulse

                raw = signal + noise

                sifted = sift_probability * (signal + noise)

                snr = signal / max(noise, 1e-12)

                visibility = signal / max(signal + noise, 1e-12)

                noise_qber = 0.5 * noise / max(signal + noise, 1e-12)

                qber_slice = noise_qber + polarization_qber + tracking_qber + sync_qber

                qber_slice = max(0.0, min(qber_slice, 0.5))

                entropy_slice = self.binary_entropy(qber_slice)

                if qber_slice < 0.11:

                    secret_slice = 1.0 - 2.0 * entropy_slice

                else:

                    secret_slice = 0.0

                s.raw_key_rate = raw
                s.raw_detection_rate = raw_detection

                s.sifted_key_rate = sifted

                s.qber = qber_slice

                s.binary_entropy = entropy_slice

                s.secret_fraction = secret_slice

                s.secure_key_rate = sifted * secret_slice

                s.signal_to_noise_ratio = snr

                s.visibility = visibility

                s.noise_counts = noise
                s.total_noise_counts = noise
                s.secure_detection_fraction = visibility * secret_slice

                s.noise_qber = noise_qber
                s.polarization_qber = polarization_qber
                s.tracking_qber = tracking_qber
                s.sync_qber = sync_qber

                s.notes = f"QBER={100*qber_slice:.2f}%"
            # Do not overwrite the state values.
            # The state values were already computed using the detector outputs.
            # The loop above only stores per-slice information.

            print()
            print("===== BB84 → SLICES =====")
            print("Slices Updated :", len(state.propagation_slices))
            print("=========================")
            print()
        # ==========================================
        # v0.4 Adaptive Slice BB84
        # ==========================================

        state.debug_message = "BB84 completed"

        # ==========================================
        # Console Output
        # ==========================================

        print()

        print(f"Signal Counts: " f"{signal_counts:.3e} cps")

        print(f"Noise Counts: " f"{total_noise:.3e} cps")

        print(f"Raw Detection Rate: {raw_detection_rate:.3e} cps")
        print(f"Raw Key Rate: {state.raw_key_rate:.3e} bps")

        print(f"Sifted Key Rate: {state.sifted_key_rate:.3e} bps")

        print(f"QBER = {100*qber:.6f}%")

        print(f"Secret Fraction: {state.secret_fraction:.4f}")
        print(f"Binary Entropy: " f"{state.binary_entropy:.4f}")

        print(f"SNR: " f"{signal_to_noise_ratio:.2f}")

        print(f"Visibility: " f"{100*visibility:.2f}%")

        print(f"Secure Detection Fraction: " f"{100*secure_detection_fraction:.2f}%")
        print(f"Noise QBER = {100*noise_qber_total:.6f}%")

        print(f"""
DEBUG QBER BREAKDOWN
---------------------
Noise QBER        : {100*noise_qber_total:.6f} %
Polarization QBER : {polarization_qber:.6f}
Tracking QBER     : {tracking_qber:.6f}
TOTAL QBER        : {qber:.6f}
Sync QBER         : {sync_qber:.6f}
""")

        print("\n===== QKD OUTPUT =====")
        print("QBER =", state.qber)
        print("Secret Fraction =", state.secret_fraction)
        print("SKR =", getattr(state, "secure_key_rate", 0.0))
        print("======================\n")

        # ==========================================
        # VERIFIER TEXT GENERATION
        # ==========================================
        state.verifier_text["qkd"] = f"""
Raw Key Rate
R_raw = S + N_total = {raw_key_rate:.2f}

Sifted Key Rate
P_sift = Defined by Protocol = {sift_probability:.4f}
R_sift = R_raw · P_sift = {sifted_key_rate:.2f}

QBER
E_noise = (0.5 · N_total) / max(S + N_total, 1e-12) = {noise_qber:.4f}
E = E_noise + E_pol + E_track + E_sync = {qber:.4f}

Secret Fraction
H(E) = -E·log₂(E) - (1-E)·log₂(1-E) = {entropy:.4f}
SF = max(0, 1 - 2 · H(E)) = {secret_fraction:.4f}

Secure Key Rate
R_sec = R_sift · SF = {getattr(state, "secure_key_rate", 0.0):.2f}

Raw Key Rate
R_raw = R_sig + R_noise = {getattr(state, 'raw_key_rate', 0.0):.4e} bps

Sifted Key Rate
R_sifted = R_raw * (P_z² + P_x²) = {getattr(state, 'sifted_key_rate', 0.0):.4e} bps

QBER
E_total = E_noise + E_pol + E_track + E_sync = {getattr(state, 'qber', 0.0):.4f}

Binary Entropy
h(e) = -E_total·log₂(E_total) - (1-E_total)·log₂(1-E_total) = {getattr(state, 'binary_entropy', 0.0):.4f}

Error Correction Leakage
Leak_EC = f_EC · h(e) = {getattr(state, 'error_correction_leakage', 0.0):.4f}

Privacy Amplification
PA = 1 - (1 + f_EC) * h(e) = {getattr(state, 'privacy_amplification_loss', 0.0):.4f}

Authentication Cost
Cost_auth = (AuthBits / BlockSize) * R_sifted = {getattr(state, 'authentication_cost', 0.0):.4e}

Secret Fraction
SF = max(0, 1 - (1+f_EC) * h(e)) = {getattr(state, 'secret_fraction', 0.0):.4f}

Secure Key Rate
R_sec = max(0, (R_sifted * SF) - Cost_auth) = {getattr(state, 'secure_key_rate', 0.0):.4e} bps
"""

