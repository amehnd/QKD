"""
e91.py

E91 Entanglement Based QKD

Maritime QKD Simulator v0.3
"""

import math
from core.model import Model


class E91Model(Model):

    name = "E91"

    version = "0.3"

    description = "Entanglement-based QKD"

    inputs = [
        "signal_count_rate",
        "background_count_rate",
        "dark_count_rate",
        "polarization_error_rate",
        "tracking_error_urad",
        "pair_generation_rate_hz",
        "coincidence_window_ns",
        "coincidence_efficiency",
        "alice_basis_probability",
        "bob_basis_probability",
        "bell_basis_angles",
    ]

    outputs = [
        "raw_key_rate",
        "sifted_key_rate",
        "qber",
        "secret_fraction",
        "secure_key_rate",
        "bell_parameter",
        "alice_singles_rate",
        "bob_singles_rate",
        "coincidence_rate",
        "coincidence_visibility",
        "eve_information",
    ]

    def validate(self, state):

        return True

    def execute(self, state):

        signal = max(getattr(state, "signal_count_rate", 0.0), 0.0)

        background = max(getattr(state, "background_count_rate", 0.0), 0.0)

        dark = max(getattr(state, "dark_count_rate", 0.0), 0.0)

        pol_error = getattr(state, "polarization_error_rate", 0.01)

        tracking_error = getattr(state, "tracking_error_urad", 0.0)

        # ==================================
        # Raw key
        # ==================================

        afterpulse = max(getattr(state, "afterpulse_count_rate", 0.0), 0.0)

        total_noise = background + dark + afterpulse

        p_a = getattr(state, "alice_basis_probability", 0.5)
        p_b = getattr(state, "bob_basis_probability", 0.5)
        sift_probability = p_a * p_b + (1.0 - p_a) * (1.0 - p_b)
        
        raw_key_rate = signal + total_noise
        sifted_key_rate = sift_probability * (signal + total_noise)
        # ==================================
        # QBER (same channel model as BB84)
        # ==================================

        noise_qber = 0.5 * total_noise / max(signal + total_noise, 1e-12)

        polarization_qber = getattr(state, "polarization_qber", pol_error)

        tracking_qber = min(0.08, tracking_error / 1e6)

        sync_qber = getattr(state, "sync_qber", 0.0)

        qber = noise_qber + polarization_qber + tracking_qber + sync_qber

        qber = max(0.0, min(qber, 0.5))

        # CHSH Bell parameter

        bell_parameter = max(0.0, 2 * math.sqrt(2) * (1 - 2 * qber))

        if qber <= 0:

            H2 = 0

        else:

            H2 = -qber * math.log2(qber) - (1 - qber) * math.log2(1 - qber)

        if qber < 0.11:
            secret_fraction = 0.9 * (1 - 2 * H2)
        else:
            secret_fraction = 0.0

        secret_fraction = max(0.0, min(secret_fraction, 1.0))

        # Final SKR is calculated by SKRModel
        secure_key_rate = sifted_key_rate * secret_fraction
        # ==========================================
        # v0.4 Propagation Slice E91
        # ==========================================

        if state.propagation_slices:

            raw_sum = 0.0
            sifted_sum = 0.0
            secure_sum = 0.0
            qber_sum = 0.0
            bell_sum = 0.0
            secret_sum = 0.0

            for s in state.propagation_slices:

                slice_signal = getattr(s, "signal_count_rate", signal)

                slice_background = getattr(s, "background_count_rate", background)

                slice_dark = getattr(s, "dark_count_rate", dark)

                slice_afterpulse = getattr(s, "afterpulse_count_rate", afterpulse)

                slice_noise = slice_background + slice_dark + slice_afterpulse

                slice_raw = slice_signal + slice_noise
                slice_sifted = sift_probability * (slice_signal + slice_noise)

                noise_qber = 0.5 * slice_noise / max(slice_signal + slice_noise, 1e-12)

                slice_pol_qber = getattr(s, "polarization_qber", polarization_qber)

                slice_tracking_qber = min(
                    0.08, getattr(s, "tracking_error_urad", tracking_error) / 1e6
                )

                slice_sync_qber = getattr(s, "sync_qber", sync_qber)

                slice_qber = (
                    noise_qber + slice_pol_qber + slice_tracking_qber + slice_sync_qber
                )

                slice_qber = max(0.0, min(slice_qber, 0.5))

                if slice_qber <= 0:

                    H2 = 0.0

                else:

                    H2 = -slice_qber * math.log2(slice_qber) - (
                        1.0 - slice_qber
                    ) * math.log2(1.0 - slice_qber)

                if slice_qber < 0.11:

                    slice_secret = 0.9 * (1.0 - 2.0 * H2)

                else:

                    slice_secret = 0.0

                slice_secret = max(0.0, min(slice_secret, 1.0))

                # Final slice SKR is calculated by SKRModel
                slice_secure = slice_sifted * slice_secret

                slice_bell = max(0.0, 2.0 * math.sqrt(2.0) * (1.0 - 2.0 * slice_qber))

                s.raw_key_rate = slice_raw
                s.sifted_key_rate = slice_sifted
                s.qber = slice_qber
                s.secret_fraction = slice_secret
                s.secure_key_rate = slice_secure
                s.bell_parameter = slice_bell
                s.noise_counts = slice_noise

                s.signal_to_noise_ratio = slice_signal / max(slice_noise, 1e-12)

                s.visibility = slice_signal / max(slice_raw, 1e-12)

                s.binary_entropy = H2
                s.signal_counts = slice_signal
                s.background_counts = slice_background
                s.dark_counts = slice_dark
                s.afterpulse_counts = slice_afterpulse

                s.raw_detection_rate = slice_raw

                s.noise_qber = noise_qber
                s.polarization_qber = slice_pol_qber
                s.tracking_qber = slice_tracking_qber
                s.sync_qber = slice_sync_qber

                s.secure_detection_fraction = s.visibility * slice_secret

                s.notes = f"QBER={100*slice_qber:.2f}% " f"S={slice_bell:.3f}"
                secret_sum += slice_secret
                raw_sum += slice_raw
                sifted_sum += slice_sifted
                secure_sum += slice_secure
                qber_sum += slice_qber
                bell_sum += slice_bell

            n = len(state.propagation_slices)

            print()
            print("===== E91 → SLICES =====")
            print("Slices Updated :", n)
            print("========================")
            print()

        state.raw_key_rate = raw_key_rate

        state.sifted_key_rate = sifted_key_rate

        state.qber = qber
        state.noise_qber = noise_qber
        state.polarization_qber = polarization_qber
        state.tracking_qber = tracking_qber
        state.sync_qber = sync_qber

        state.secret_fraction = secret_fraction

        state.secure_key_rate = secure_key_rate

        state.bell_parameter = bell_parameter
        state.binary_entropy = H2
        state.noise_qber = noise_qber
        state.polarization_qber = polarization_qber
        state.tracking_qber = tracking_qber
        state.sync_qber = sync_qber

        state.noise_counts = total_noise

        state.signal_to_noise_ratio = signal / max(total_noise, 1e-12)

        state.visibility = signal / max(raw_key_rate, 1e-12)
        state.secure_detection_fraction = state.visibility * state.secret_fraction

        R_pair = max(getattr(state, "pair_generation_rate_hz", 1e7), 0.0)
        eta_B = max(getattr(state, "channel_efficiency", 1.0), 0.0)
        eta_coin = max(getattr(state, "coincidence_efficiency", 1.0), 0.0)

        state.alice_singles_rate = R_pair * 1.0
        state.bob_singles_rate = R_pair * eta_B
        state.coincidence_rate = R_pair * 1.0 * eta_B * eta_coin
        state.coincidence_visibility = 1.0 - 2.0 * qber
        state.eve_information = H2

        state.debug_message = "E91 completed"

        print()

        print("E91")

        print("--------------------")

        print("Bell Parameter:", f"{bell_parameter:.3f}")

        print("QBER:", f"{100*qber:.3f}%")

        print("Secure Key Rate:", f"{secure_key_rate:.3e}")

        # ==========================================
        # VERIFIER TEXT GENERATION
        # ==========================================
        state.verifier_text["qkd"] = f"""
Raw Key Rate
R_raw = S + N_total = {raw_key_rate:.2f}

Sifted Key Rate
P_sift = Defined by Protocol = {sift_probability:.4f}
R_sift = R_raw · P_sift = {sifted_key_rate:.2f}

Bell Parameter
S_bell = 2√2 · (1 - 2E) = {bell_parameter:.4f}

Coincidence Visibility
V_coinc = 1 - 2E = {getattr(state, "coincidence_visibility", 0.0):.4f}

QBER
E_noise = (0.5 · N_total) / max(S + N_total, 1e-12) = {noise_qber:.4f}
E = E_noise + E_pol + E_track + E_sync = {qber:.4f}

Secret Fraction
H(E) = -E·log₂(E) - (1-E)·log₂(1-E) = {H2:.4f}
SF = 0.9 · (1 - 2 · H(E)) = {secret_fraction:.4f}

Secure Key Rate
R_sec = R_sift · SF = {secure_key_rate:.2f}

Singles Alice
R_alice = P_Alice * Rate_pulse = {getattr(state, 'singles_alice_hz', 0.0):.4e} Hz

Singles Bob
R_bob = P_Bob * Rate_pulse = {getattr(state, 'singles_bob_hz', 0.0):.4e} Hz

Coincidence Rate
R_coinc = R_alice * R_bob * Δt_coinc = {getattr(state, 'coincidence_rate_hz', 0.0):.4e} Hz

Visibility
V = (C_max - C_min) / (C_max + C_min) = {getattr(state, 'visibility', 0.0):.4f} %

Bell Parameter
S_bell = |E(a,b) - E(a,b') + E(a',b) + E(a',b')| = {getattr(state, 'bell_parameter', 0.0):.4f}

QBER
E_total = E_noise + E_pol + E_track = {getattr(state, 'qber', 0.0):.4f}

Secret Fraction
SF = max(0, 1 - (1+f_EC)*h(e)) = {getattr(state, 'secret_fraction', 0.0):.4f}

Secure Key Rate
R_sec = max(0, (R_coinc * SF) - Cost_auth) = {getattr(state, 'secure_key_rate', 0.0):.4e} bps
"""

