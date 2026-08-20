"""
bbm92.py

BBM92 Entanglement-Based Quantum Key Distribution

Maritime QKD Simulator v0.3
"""

import math

from core.model import Model


class BBM92Model(Model):

    name = "BBM92"

    version = "0.3"

    description = "BBM92 Entanglement-Based Quantum Key Distribution"

    inputs = [
        "signal_count_rate",
        "background_count_rate",
        "dark_count_rate",
        "afterpulse_count_rate",
        "tracking_error_urad",
        "polarization_error_rate",
        "pair_generation_rate_hz",
        "coincidence_window_ns",
        "coincidence_efficiency",
        "entangled_source_brightness",
        "pair_production_probability",
    ]

    outputs = [
        "raw_key_rate",
        "sifted_key_rate",
        "coincidence_rate",
        "sifted_coincidence_rate",
        "qber",
        "binary_entropy",
        "secret_fraction",
        "secure_key_rate",
    ]

    def validate(self, state):
        return True

    def execute(self, state):
        signal = max(getattr(state, "signal_count_rate", 0.0), 0.0)
        background = max(getattr(state, "background_count_rate", 0.0), 0.0)
        dark = max(getattr(state, "dark_count_rate", 0.0), 0.0)
        afterpulse = max(getattr(state, "afterpulse_count_rate", 0.0), 0.0)
        
        pol_error = getattr(state, "polarization_error_rate", 0.01)
        tracking_error = getattr(state, "tracking_error_urad", 0.0)
        
        total_noise = background + dark + afterpulse
        
        raw_key_rate = signal + total_noise
        sifted_key_rate = 0.5 * (signal + total_noise)
        
        noise_qber = 0.5 * total_noise / max(signal + total_noise, 1e-12)
        polarization_qber = getattr(state, "polarization_qber", pol_error)
        tracking_qber = min(0.08, tracking_error / 1e6)
        sync_qber = getattr(state, "sync_qber", 0.0)
        
        qber = noise_qber + polarization_qber + tracking_qber + sync_qber
        qber = max(0.0, min(qber, 0.5))

        if qber <= 0:
            H2 = 0.0
        else:
            H2 = -qber * math.log2(qber) - (1.0 - qber) * math.log2(1.0 - qber)
            
        if qber < 0.11:
            secret_fraction = 1.0 - 2.0 * H2
        else:
            secret_fraction = 0.0
            
        secret_fraction = max(0.0, min(secret_fraction, 1.0))
        secure_key_rate = sifted_key_rate * secret_fraction

        R_pair = max(getattr(state, "pair_production_probability", 0.01) * getattr(state, "entangled_source_brightness", 1e7), 0.0)
        eta_B = max(getattr(state, "channel_efficiency", 1.0), 0.0)
        eta_coin = max(getattr(state, "coincidence_efficiency", 1.0), 0.0)
        
        coincidence_rate = R_pair * 1.0 * eta_B * eta_coin
        sifted_coincidence_rate = 0.5 * coincidence_rate

        # ==========================================
        # v0.4 Propagation Slice BBM92
        # ==========================================
        if state.propagation_slices:
            for s in state.propagation_slices:
                slice_signal = getattr(s, "signal_count_rate", signal)
                slice_background = getattr(s, "background_count_rate", background)
                slice_dark = getattr(s, "dark_count_rate", dark)
                slice_afterpulse = getattr(s, "afterpulse_count_rate", afterpulse)
                
                slice_noise = slice_background + slice_dark + slice_afterpulse
                slice_raw = slice_signal + slice_noise
                slice_sifted = 0.5 * (slice_signal + slice_noise)
                
                slice_noise_qber = 0.5 * slice_noise / max(slice_signal + slice_noise, 1e-12)
                slice_pol_qber = getattr(s, "polarization_qber", polarization_qber)
                slice_tracking_qber = min(0.08, getattr(s, "tracking_error_urad", tracking_error) / 1e6)
                slice_sync_qber = getattr(s, "sync_qber", sync_qber)
                
                slice_qber = slice_noise_qber + slice_pol_qber + slice_tracking_qber + slice_sync_qber
                slice_qber = max(0.0, min(slice_qber, 0.5))
                
                if slice_qber <= 0:
                    slice_H2 = 0.0
                else:
                    slice_H2 = -slice_qber * math.log2(slice_qber) - (1.0 - slice_qber) * math.log2(1.0 - slice_qber)
                    
                if slice_qber < 0.11:
                    slice_secret = 1.0 - 2.0 * slice_H2
                else:
                    slice_secret = 0.0
                    
                slice_secret = max(0.0, min(slice_secret, 1.0))
                
                s.raw_key_rate = slice_raw
                s.sifted_key_rate = slice_sifted
                s.qber = slice_qber
                s.binary_entropy = slice_H2
                s.secret_fraction = slice_secret
                s.secure_key_rate = slice_sifted * slice_secret
                s.coincidence_rate = coincidence_rate
                s.sifted_coincidence_rate = sifted_coincidence_rate
                
                s.noise_counts = slice_noise
                s.signal_to_noise_ratio = slice_signal / max(slice_noise, 1e-12)
                s.visibility = slice_signal / max(slice_raw + slice_noise, 1e-12)
                s.secure_detection_fraction = s.visibility * slice_secret
                
                s.signal_counts = slice_signal
                s.background_counts = slice_background
                s.dark_counts = slice_dark
                s.afterpulse_counts = slice_afterpulse
                s.raw_detection_rate = slice_raw
                s.noise_qber = slice_noise_qber
                s.polarization_qber = slice_pol_qber
                s.tracking_qber = slice_tracking_qber
                s.sync_qber = slice_sync_qber
                s.notes = f"QBER={100*slice_qber:.2f}%"

        state.raw_key_rate = raw_key_rate
        state.sifted_key_rate = sifted_key_rate
        state.qber = qber
        state.binary_entropy = H2
        state.secret_fraction = secret_fraction
        state.secure_key_rate = secure_key_rate
        state.coincidence_rate = coincidence_rate
        state.sifted_coincidence_rate = sifted_coincidence_rate

        state.noise_qber = noise_qber
        state.polarization_qber = polarization_qber
        state.tracking_qber = tracking_qber
        state.sync_qber = sync_qber
        state.noise_counts = total_noise
        state.signal_to_noise_ratio = signal / max(total_noise, 1e-12)
        state.visibility = signal / max(signal + total_noise, 1e-12)
        state.secure_detection_fraction = state.visibility * state.secret_fraction

        state.debug_message = "BBM92 completed"

        # ==========================================
        # VERIFIER TEXT GENERATION
        # ==========================================
        state.verifier_text["qkd"] = f"""
Raw Key Rate
R_raw = S_coinc + N_total = {raw_key_rate:.2f}

Sifted Key Rate
P_sift = Defined by Protocol = 0.5000
R_sift = R_raw · P_sift = {sifted_key_rate:.2f}

QBER
E_noise = (0.5 · N_total) / max(S_coinc + N_total, 1e-12) = {noise_qber:.4f}
E = E_noise + E_pol + E_track + E_sync = {qber:.4f}

Secret Fraction
H(E) = -E·log₂(E) - (1-E)·log₂(1-E) = {H2:.4f}
SF = max(0, 1 - 2 · H(E)) = {secret_fraction:.4f}

Secure Key Rate
R_sec = R_sift · SF = {secure_key_rate:.2f}

Coincidence Rate
R_coinc = R_alice * R_bob * Δt_coinc = {getattr(state, 'coincidence_rate_hz', 0.0):.4e} Hz

Sifted Coincidence Rate
R_sifted = R_coinc * P_sift = {getattr(state, 'sifted_coincidence_rate_hz', 0.0):.4e} Hz

QBER
E_total = E_noise + E_pol + E_track = {getattr(state, 'qber', 0.0):.4f}

Secret Fraction
SF = max(0, 1 - (1+f_EC)*h(e)) = {getattr(state, 'secret_fraction', 0.0):.4f}

Secure Key Rate
R_sec = max(0, (R_sifted * SF) - Cost_auth) = {getattr(state, 'secure_key_rate', 0.0):.4e} bps
"""

