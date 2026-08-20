"""
skr.py

Secure Key Rate Model

Computes:

    Error Corrected SKR

    Privacy Amplified SKR

    PAT Weighted SKR

    Availability Weighted SKR

    Final Delivered Key Rate

Version:
    0.3
"""

import math

from core.model import Model


class SKRModel(Model):

    name = "SKR"

    description = "Secure key rate model"

    version = "0.3"

    inputs = [
        "sifted_key_rate",
        "secret_fraction",
        "qber",
        "lock_probability",
        "tracking_probability",
        "error_correction_factor",
        "binary_entropy",
        "authentication_cost_bits",
        "finite_key_block_size",
    ]

    outputs = [
        "secure_key_rate",
        "effective_secure_key_rate",
        "availability_percent",
        "pat_factor",
        "privacy_amplification_loss",
        "error_correction_efficiency",
        "final_key_utilization",
        "error_correction_leakage",
        "authentication_cost",
        "final_secure_key_rate",
    ]

    # --------------------------------------------------
    # Validation
    # --------------------------------------------------

    def validate(self, state):

        if state.sifted_key_rate < 0:

            raise ValueError("Invalid sifted key rate")

        return True

    # --------------------------------------------------
    # Execute
    # --------------------------------------------------

    def execute(self, state):

        # ==========================================
        # v0.4 Adaptive Slice SKR
        # ==========================================

        sifted_key_rate = state.sifted_key_rate
        secret_fraction = state.secret_fraction
        qber = state.qber

        sifted_key_rate = max(sifted_key_rate, 0.0)
        secret_fraction = max(min(secret_fraction, 1.0), 0.0)

        qber = max(min(qber, 0.5), 0.0)
        lock_probability = max(min(state.lock_probability, 1.0), 0.0)

        tracking_probability = max(min(state.tracking_probability, 1.0), 0.0)

        f_ec = max(getattr(state, "error_correction_factor", 1.16), 1.0)

        # ==========================================
        # Error Correction Efficiency
        #
        # Approximation:
        #
        # larger QBER
        # → larger penalty
        # ==========================================

        error_correction_efficiency = 1.0

        error_correction_efficiency = max(0.0, min(error_correction_efficiency, 1.0))

        state.error_correction_efficiency = error_correction_efficiency

        # ==========================================
        # Secure Key Rate
        #
        # After privacy amplification
        # ==========================================

        if state.qkd_protocol == "Decoy BB84" or state.qkd_protocol == "BBM92":

            secure_key_rate = (
                sifted_key_rate * secret_fraction * error_correction_efficiency
            )

        else:

            secure_key_rate = (
                sifted_key_rate * secret_fraction * error_correction_efficiency
            )
        print()
        print("===== SKR CALCULATION =====")
        print("Sifted =", sifted_key_rate)
        print("Secret =", secret_fraction)
        print("EC =", error_correction_efficiency)
        print("Calculated SKR =", secure_key_rate)
        print("===========================")

        privacy_amplification_loss = sifted_key_rate - secure_key_rate

        state.privacy_amplification_loss = privacy_amplification_loss

        H2 = getattr(state, "binary_entropy", 0.0)
        error_correction_leakage = f_ec * H2 * sifted_key_rate
        state.error_correction_leakage = error_correction_leakage

        # ==========================================
        # PAT Weighting
        #
        # Acquisition and tracking
        # availability
        # ==========================================

        pat_factor = lock_probability * tracking_probability
        state.pat_factor = pat_factor

        # ==========================================
        # Effective Secure Key Rate
        # ==========================================

        effective_secure_key_rate = secure_key_rate * pat_factor
        final_key_utilization = effective_secure_key_rate / max(sifted_key_rate, 1e-12)

        state.final_key_utilization = final_key_utilization
        
        auth_bits = getattr(state, "authentication_cost_bits", 1e5)
        block_size = getattr(state, "finite_key_block_size", 1000000)
        
        authentication_cost = 0.0
        if block_size > 0:
            authentication_cost = (auth_bits / block_size) * sifted_key_rate
            
        state.authentication_cost = authentication_cost
        
        final_secure_key_rate = max(0.0, effective_secure_key_rate - authentication_cost)
        state.final_secure_key_rate = final_secure_key_rate

        # ==========================================
        # Availability
        # ==========================================

        availability = 100.0 * pat_factor

        availability = max(0.0, min(availability, 100.0))

        # ==========================================
        # Link Quality
        # ==========================================

        if effective_secure_key_rate <= 0:

            state.link_quality = "NO LINK"

        elif effective_secure_key_rate < 1e3:

            state.link_quality = "POOR"

        elif effective_secure_key_rate < 1e5:

            state.link_quality = "FAIR"

        elif effective_secure_key_rate < 1e6:

            state.link_quality = "GOOD"

        else:

            state.link_quality = "EXCELLENT"

        # ==========================================
        # Security Status
        # ==========================================

        if qber > 0.11:

            state.security_status = "UNSECURE"

        else:

            state.security_status = "SECURE"
        state.is_secure = qber <= 0.11

        # ==========================================
        # Save Results
        # ==========================================
        print()
        print("===== SKR INPUT DEBUG =====")
        print("Sifted =", sifted_key_rate)
        print("Secret Fraction =", secret_fraction)
        print("EC =", error_correction_efficiency)
        print("Calculated SKR =", secure_key_rate)
        print("===========================")

        state.secure_key_rate = secure_key_rate
        print("Stored state.secure_key_rate =", state.secure_key_rate)

        state.effective_secure_key_rate = effective_secure_key_rate

        state.availability_percent = availability
        # ==========================================
        # Store results in propagation slices
        # ==========================================

        if state.propagation_slices:

            for s in state.propagation_slices:

                sifted = getattr(s, "sifted_key_rate", 0.0)

                secret = getattr(s, "secret_fraction", 0.0)

                qber_slice = getattr(s, "qber", 0.5)

                ec = 1.0

                ec = max(0.0, min(ec, 1.0))

                if state.qkd_protocol == "Decoy BB84" or state.qkd_protocol == "BBM92":

                    skr = sifted * secret * ec
                else:

                    skr = sifted * secret * ec

                effective = skr * pat_factor

                privacy_loss = sifted - skr

                utilization = effective / max(sifted, 1e-12)

                s.error_correction_efficiency = ec

                s.privacy_amplification_loss = privacy_loss

                s.pat_factor = pat_factor

                s.secure_key_rate = skr

                s.effective_secure_key_rate = effective

                s.final_key_utilization = utilization

                s.availability_percent = availability

                s.link_quality = state.link_quality

                s.security_status = state.security_status
                
                slice_H2 = getattr(s, "binary_entropy", 0.0)
                s.error_correction_leakage = f_ec * slice_H2 * sifted
                
                slice_auth = 0.0
                if block_size > 0:
                    slice_auth = (auth_bits / block_size) * sifted
                s.authentication_cost = slice_auth
                
                s.final_secure_key_rate = max(0.0, effective - slice_auth)

                s.notes = f"SKR={skr:.2e} bps"

            print()
            print("===== SKR → SLICES =====")

            for s in state.propagation_slices[:5]:

                print(
                    f"Slice {s.slice_id}: "
                    f"QBER={100*s.qber:.2f}% "
                    f"SKR={s.secure_key_rate:.2e}"
                )

            print("========================")
            print()

        state.pat_availability = pat_factor
        state.lock_availability = lock_probability

        state.tracking_availability = tracking_probability

        state.debug_message = "SKR completed"

        # ==========================================
        # Console Output
        # ==========================================

        print()

        print(f"Sifted Key Rate: " f"{sifted_key_rate:.3e} bps")

        print(f"Secret Fraction: " f"{secret_fraction:.4f}")

        print(
            f"Error Correction Efficiency: " f"{100.0*error_correction_efficiency:.2f}%"
        )

        print(f"Secure Key Rate: " f"{secure_key_rate:.3e} bps")

        print(f"Lock Probability: " f"{100.0*lock_probability:.2f}%")

        print(f"Tracking Probability: " f"{100.0*tracking_probability:.2f}%")

        print(f"Effective SKR: " f"{effective_secure_key_rate:.3e} bps")

        print(f"PAT Factor: " f"{100.0*pat_factor:.2f}%")

        print(f"Privacy Amplification Loss: " f"{privacy_amplification_loss:.3e} bps")

        print(f"Final Key Utilization: " f"{100.0*final_key_utilization:.2f}%")

        print(f"Availability: " f"{availability:.2f}%")

        print(f"Link Quality: " f"{state.link_quality}")

        print(f"Security Status: " f"{state.security_status}")

        print("\nSKR DEBUG")
        print("----------------")
        print("PAT Factor =", pat_factor)
        print("Error Correction Efficiency =", error_correction_efficiency)
        print("Privacy Amplification Loss =", privacy_amplification_loss)
        print("Final Key Utilization =", final_key_utilization)
