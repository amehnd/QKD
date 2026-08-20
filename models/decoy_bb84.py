"""
decoy_bb84.py

Decoy State BB84 Protocol

Maritime QKD Simulator v0.3
"""

import math

from core.model import Model


class DecoyBB84Model(Model):

    name = "DecoyBB84"
    version = "0.3"
    description = "Decoy-state BB84 QKD"

    inputs = [
        "pulse_rate_mhz",
        "signal_count_rate",
        "background_count_rate",
        "dark_count_rate",
        "polarization_error_rate",
        "tracking_error_urad",
        "mean_photon_number",
        "weak_decoy_intensity",
        "vacuum_decoy_intensity",
        "signal_probability",
        "weak_decoy_probability",
        "vacuum_probability",
    ]

    outputs = [
        "raw_key_rate",
        "sifted_key_rate",
        "qber",
        "secret_fraction",
        "secure_key_rate",
        "decoy_gain",
        "single_photon_gain",
        "signal_gain",
        "weak_gain",
        "vacuum_gain",
        "signal_qber",
        "weak_qber",
        "single_photon_yield",
        "single_photon_error_rate",
        "multi_photon_fraction",
    ]

    def validate(self, state):
        return True

    def execute(self, state):
        signal = max(getattr(state, "signal_count_rate", 0.0), 0.0)
        background = max(getattr(state, "background_count_rate", 0.0), 0.0)
        dark = max(getattr(state, "dark_count_rate", 0.0), 0.0)
        mu = max(getattr(state, "mean_photon_number", 0.5), 1e-3)
        pulse_rate = max(getattr(state, "pulse_rate_mhz", 200.0) * 1e6, 1.0)
        pol_error = getattr(state, "polarization_error_rate", 0.01)
        tracking_error = getattr(state, "tracking_error_urad", 0.0)
        afterpulse = max(getattr(state, "afterpulse_count_rate", 0.0), 0.0)
        total_noise = background + dark + afterpulse
        sync_qber = getattr(state, "sync_qber", 0.0)
        polarization_qber = getattr(state, "polarization_qber", pol_error)
        tracking_qber = min(0.08, tracking_error / 1e6)

        # ==================================
        # Raw and sifted keys
        # ==================================
        raw_key_rate = signal + total_noise
        basis_probability_z = getattr(state, "basis_probability_z", 0.5)
        basis_probability_x = getattr(state, "basis_probability_x", 1.0 - basis_probability_z)
        sift_probability = basis_probability_z**2 + basis_probability_x**2
        
        sifted_key_rate = sift_probability * (signal + total_noise)

        # ==================================
        # QBER (same physical channel as BB84)
        # ==================================
        noise_qber = 0.5 * total_noise / max(signal + total_noise, 1e-12)
        qber = noise_qber + polarization_qber + tracking_qber + sync_qber
        qber = max(0.0, min(qber, 0.5))

        print("\n===== DECOY INPUT DEBUG =====")
        print("Signal =", signal)
        print("Background =", background)
        print("Dark =", dark)
        print("Afterpulse =", afterpulse)
        print("Noise QBER =", noise_qber)
        print("Total QBER =", qber)
        print("=============================\n")

        # ==================================
        # Decoy State Parameters & Bounds
        # ==================================
        eta_eff = max(getattr(state, "channel_efficiency", 0.0), 1e-12)
        nu = max(getattr(state, "weak_decoy_intensity", 0.1), 1e-12)
        omega = max(getattr(state, "vacuum_decoy_intensity", 0.0), 0.0)
        
        Y0 = max(total_noise / pulse_rate, 1e-12)
        e0 = 0.5
        
        Q_mu = Y0 + 1.0 - math.exp(-eta_eff * mu)
        Q_nu = Y0 + 1.0 - math.exp(-eta_eff * nu)
        Q_omega = Y0 + 1.0 - math.exp(-eta_eff * omega)
        
        e_opt = polarization_qber + tracking_qber + sync_qber
        E_mu = (e0 * Y0 + e_opt * (1.0 - math.exp(-eta_eff * mu))) / max(Q_mu, 1e-12)
        E_nu = (e0 * Y0 + e_opt * (1.0 - math.exp(-eta_eff * nu))) / max(Q_nu, 1e-12)
        
        denom = (mu * nu - nu**2)
        if denom > 0:
            Y1_L = (mu / denom) * (Q_nu * math.exp(nu) - Q_omega * math.exp(omega) - (nu**2 / mu**2) * (Q_mu * math.exp(mu) - Q_omega * math.exp(omega)))
        else:
            Y1_L = 0.0
            
        if Y1_L > 0:
            e1_U = (E_nu * Q_nu * math.exp(nu) - e0 * Y0) / (Y1_L * nu)
        else:
            e1_U = 0.5
            
        Y1_L = max(0.0, min(Y1_L, 1.0))
        e1_U = max(0.0, min(e1_U, 0.5))

        Q1_L = mu * math.exp(-mu) * Y1_L
        single_photon_gain = Q1_L
        decoy_gain = Q_nu

        # ==================================
        # Binary entropy
        # ==================================
        if E_mu <= 0:
            H2 = 0
        else:
            H2 = -E_mu * math.log2(E_mu) - (1 - E_mu) * math.log2(1 - E_mu)
            
        if e1_U <= 0:
            H2_e1 = 0
        else:
            H2_e1 = -e1_U * math.log2(e1_U) - (1.0 - e1_U) * math.log2(1.0 - e1_U)

        # ==================================
        # Secret fraction
        # ==================================
        f_ec = getattr(state, "error_correction_factor", 1.16)

        # Decoy-state secret fraction: (Q1 / Q_mu) * [1 - H2(e1)] - f_ec * H2(E_mu)
        ratio_q1_qmu = min(1.0, max(0.0, Q1_L / max(Q_mu, 1e-12)))
        secret_fraction = max(
            0.0, ratio_q1_qmu * (1.0 - H2_e1) - f_ec * H2
        )
        secret_fraction = min(secret_fraction, 1.0)

        # Secure key rate
        secure_key_rate = sifted_key_rate * secret_fraction

        # ==========================================
        # v0.4 Propagation Slice Decoy BB84
        # ==========================================
        if state.propagation_slices:
            raw_sum = 0.0
            sifted_sum = 0.0
            secure_sum = 0.0
            qber_sum = 0.0
            decoy_sum = 0.0
            single_sum = 0.0
            secret_sum = 0.0

            for s in state.propagation_slices:
                slice_signal = getattr(s, "signal_count_rate", signal)
                slice_background = getattr(s, "background_count_rate", background)
                slice_dark = getattr(s, "dark_count_rate", dark)
                slice_afterpulse = getattr(s, "afterpulse_count_rate", afterpulse)
                slice_mu = getattr(s, "mean_photon_number", mu)
                slice_noise = slice_background + slice_dark + slice_afterpulse
                
                s.signal_counts = slice_signal
                s.background_counts = slice_background
                s.dark_counts = slice_dark
                s.afterpulse_counts = slice_afterpulse

                slice_raw = slice_signal + slice_noise
                slice_sifted = sift_probability * (slice_signal + slice_noise)

                noise_qber = 0.5 * slice_noise / max(slice_signal + slice_noise, 1e-12)
                slice_pol_qber = getattr(s, "polarization_qber", polarization_qber)
                slice_tracking_qber = min(0.08, getattr(s, "tracking_error_urad", tracking_error) / 1e6)
                slice_sync_qber = getattr(s, "sync_qber", sync_qber)

                slice_qber = noise_qber + slice_pol_qber + slice_tracking_qber + slice_sync_qber
                slice_qber = max(0.0, min(slice_qber, 0.5))

                slice_eta = max(getattr(s, "cumulative_transmission", 1e-12), 1e-12)
                
                # Slice Decoy Bounds
                s_Y0 = max(slice_noise / pulse_rate, 1e-12)
                s_Q_mu = s_Y0 + 1.0 - math.exp(-slice_eta * slice_mu)
                s_Q_nu = s_Y0 + 1.0 - math.exp(-slice_eta * nu)
                s_Q_omega = s_Y0 + 1.0 - math.exp(-slice_eta * omega)
                
                s_e_opt = slice_pol_qber + slice_tracking_qber + slice_sync_qber
                s_E_mu = (e0 * s_Y0 + s_e_opt * (1.0 - math.exp(-slice_eta * slice_mu))) / max(s_Q_mu, 1e-12)
                s_E_nu = (e0 * s_Y0 + s_e_opt * (1.0 - math.exp(-slice_eta * nu))) / max(s_Q_nu, 1e-12)
                
                s_denom = (slice_mu * nu - nu**2)
                if s_denom > 0:
                    s_Y1_L = (slice_mu / s_denom) * (s_Q_nu * math.exp(nu) - s_Q_omega * math.exp(omega) - (nu**2 / slice_mu**2) * (s_Q_mu * math.exp(slice_mu) - s_Q_omega * math.exp(omega)))
                else:
                    s_Y1_L = 0.0
                    
                if s_Y1_L > 0:
                    s_e1_U = (s_E_nu * s_Q_nu * math.exp(nu) - e0 * s_Y0) / (s_Y1_L * nu)
                else:
                    s_e1_U = 0.5
                    
                s_Y1_L = max(0.0, min(s_Y1_L, 1.0))
                s_e1_U = max(0.0, min(s_e1_U, 0.5))
                
                s_Q1_L = slice_mu * math.exp(-slice_mu) * s_Y1_L
                slice_single_gain = s_Q1_L
                slice_decoy_gain = s_Q_nu

                if s_E_mu <= 0.0:
                    s_H2 = 0.0
                else:
                    s_H2 = -s_E_mu * math.log2(s_E_mu) - (1.0 - s_E_mu) * math.log2(1.0 - s_E_mu)
                    
                if s_e1_U <= 0.0:
                    s_H2_e1 = 0.0
                else:
                    s_H2_e1 = -s_e1_U * math.log2(s_e1_U) - (1.0 - s_e1_U) * math.log2(1.0 - s_e1_U)

                s_ratio_q1_qmu = min(1.0, max(0.0, s_Q1_L / max(s_Q_mu, 1e-12)))
                slice_secret = max(0.0, s_ratio_q1_qmu * (1.0 - s_H2_e1) - f_ec * s_H2)
                slice_secret = min(slice_secret, 1.0)

                slice_secure = slice_sifted * slice_secret

                s.raw_key_rate = slice_raw
                s.raw_detection_rate = slice_raw
                s.sifted_key_rate = slice_sifted
                s.qber = slice_qber
                s.secret_fraction = slice_secret
                s.secure_key_rate = slice_secure
                s.decoy_gain = slice_decoy_gain
                s.single_photon_gain = slice_single_gain
                s.binary_entropy = s_H2
                s.noise_qber = noise_qber
                s.polarization_qber = slice_pol_qber
                s.tracking_qber = slice_tracking_qber
                s.sync_qber = slice_sync_qber
                s.noise_counts = slice_noise
                s.signal_to_noise_ratio = slice_signal / max(slice_noise, 1e-12)
                s.visibility = slice_signal / max(slice_signal + slice_noise, 1e-12)
                s.secure_detection_fraction = s.visibility * slice_secret
                s.notes = f"QBER={100*slice_qber:.2f}% Gain={slice_single_gain:.3f}"

                raw_sum += slice_raw
                sifted_sum += slice_sifted
                secure_sum += slice_secure
                qber_sum += slice_qber
                decoy_sum += slice_decoy_gain
                single_sum += slice_single_gain
                secret_sum += slice_secret
                
            n = len(state.propagation_slices)
            print()
            print("===== DECOY BB84 → SLICES =====")
            print("Slices Updated :", n)
            print("===============================")
            print()

        # ==================================
        # SAVE
        # ==================================
        state.raw_key_rate = raw_key_rate
        state.sifted_key_rate = sifted_key_rate
        state.qber = qber
        state.noise_qber = noise_qber
        state.polarization_qber = polarization_qber
        state.tracking_qber = tracking_qber
        state.sync_qber = sync_qber
        state.secret_fraction = secret_fraction
        state.secure_key_rate = secure_key_rate
        state.decoy_gain = decoy_gain
        state.single_photon_gain = single_photon_gain
        state.binary_entropy = H2
        state.noise_counts = total_noise
        state.signal_to_noise_ratio = signal / max(total_noise, 1e-12)
        state.visibility = signal / max(signal + total_noise, 1e-12)
        state.secure_detection_fraction = state.visibility * state.secret_fraction

        multi_photon_fraction = 1.0 - (mu * math.exp(-mu)) / max(1.0 - math.exp(-mu), 1e-12)

        state.signal_gain = Q_mu
        state.weak_gain = Q_nu
        state.vacuum_gain = Q_omega
        state.signal_qber = E_mu
        state.weak_qber = E_nu
        state.single_photon_yield = Y1_L
        state.single_photon_error_rate = e1_U
        state.multi_photon_fraction = max(0.0, min(multi_photon_fraction, 1.0))

        state.debug_message = "Decoy BB84 completed"

        print()
        print("DECOY BB84")
        print("--------------------")
        print("QBER:", f"{100*qber:.3f}%")
        print("Decoy Gain:", decoy_gain)
        print("Single Photon Gain:", single_photon_gain)
        print("Secure Key Rate:", f"{secure_key_rate:.3e}")
        print()
        print("INSIDE DECOY MODEL")
        print("QBER =", state.qber)
        print("Secret Fraction =", state.secret_fraction)
        print("Secure Key =", state.secure_key_rate)

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

Single Photon Yield
Y₁ = Computed from Decoy States = {Y1_L:.4f}

Single Photon Error
e₁ = Computed from Decoy States = {e1_U:.4f}

Secret Fraction
H(E) = -E·log₂(E) - (1-E)·log₂(1-E) = {H2:.4f}
H(e₁) = -e₁·log₂(e₁) - (1-e₁)·log₂(1-e₁) = {H2_e1:.4f}
SF = Q₁ · (1 - H(e₁)) - f · Q_μ · H(E) = {secret_fraction:.4f}

Secure Key Rate
R_sec = R_sift · SF = {secure_key_rate:.2f}

Signal Gain
Q_signal = Y_0 + 1 - exp(-η_sys * μ_sig) = {getattr(state, 'signal_gain', 0.0):.4e}

Weak Gain
Q_weak = Y_0 + 1 - exp(-η_sys * μ_weak) = {getattr(state, 'weak_gain', 0.0):.4e}

Vacuum Gain
Q_vacuum = Y_0 = {getattr(state, 'vacuum_gain', 0.0):.4e}

Signal QBER
E_signal = (E_0*Y_0 + E_d*(Q_sig - Y_0)) / Q_sig = {getattr(state, 'signal_qber', 0.0):.4f} %

Weak QBER
E_weak = (E_0*Y_0 + E_d*(Q_weak - Y_0)) / Q_weak = {getattr(state, 'weak_qber', 0.0):.4f} %

Single Photon Yield
Y_1 = (μ_sig/(μ_sig*μ_weak - μ_weak**2)) * (Q_weak*exp(μ_weak) - Q_vac - (μ_weak**2/μ_sig**2)*(Q_sig*exp(μ_sig) - Q_vac)) = {getattr(state, 'single_photon_yield', 0.0):.4e}

Single Photon Gain
Q_1 = Y_1 * μ_sig * exp(-μ_sig) = {getattr(state, 'single_photon_gain', 0.0):.4e}

Single Photon Error
e_1 = (E_weak*Q_weak*exp(μ_weak) - E_0*Y_0) / (Y_1 * μ_weak) = {getattr(state, 'single_photon_error_rate', 0.0):.4f} %

Multi Photon Fraction
f_multi = 1 - (Q_1 + Q_vac) / Q_signal = {getattr(state, 'multi_photon_fraction', 0.0):.4f}

Secret Fraction
SF = Q_1*(1 - h(e_1)) - Q_signal*f_EC*h(E_signal) = {getattr(state, 'secret_fraction', 0.0):.4f}

Secure Key Rate
R_sec = max(0, (Rate_pulse * SF) - Cost_auth) = {getattr(state, 'secure_key_rate', 0.0):.4e} bps
"""

