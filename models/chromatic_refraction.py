"""
chromatic_refraction.py

Dual-Wavelength Maritime Refraction Model

Computes:

    1310 nm refractive index

    1550 nm refractive index

    Differential refraction

    Beacon-QKD angular separation

    Receiver plane separation

    Required FSM correction

Version:
    0.3
"""

import math
from core.model import Model


class ChromaticRefractionModel(Model):
    name = "ChromaticRefraction"
    description = "Dual wavelength atmospheric refraction"
    version = "0.3"
    inputs = [
        "tracking_wavelength_nm",
        "quantum_wavelength_nm",
        "surface_refractive_index",
        "ray_bending_angle_urad",
        "link_distance_km",
        "temperature_C",
        "pressure_hPa",
        "relative_humidity_pct",
    ]
    outputs = [
        "tracking_refractive_index",
        "quantum_refractive_index",
        "differential_refraction_urad",
        "beacon_qkd_offset_urad",
        "receiver_separation_mm",
        "fsm_correction_required_urad",
    ]

    # --------------------------------------------------
    # Validation
    # --------------------------------------------------
    def validate(self, state):

        if not state.propagation_slices:

            raise ValueError("Refractivity must run before Chromatic Refraction.")

        if state.tracking_wavelength_nm <= 0:

            raise ValueError("Tracking wavelength invalid")

        if state.quantum_wavelength_nm <= 0:

            raise ValueError("Quantum wavelength invalid")

        return True

    # --------------------------------------------------
    # Edlen / Ciddor style approximation
    #
    # Infrared refractive index
    # --------------------------------------------------

    def refractive_index_air(
        self, wavelength_nm, pressure_hPa, temperature_C, humidity_pct
    ):

        wavelength_um = wavelength_nm / 1000.0

        sigma2 = 1.0 / (wavelength_um**2)

        n_minus_1 = 1e-8 * (
            8342.13 + 2406030.0 / (130.0 - sigma2) + 15997.0 / (38.9 - sigma2)
        )

        pressure_factor = pressure_hPa / 1013.25

        temperature_factor = 288.15 / (273.15 + temperature_C)

        humidity_factor = 1.0 + humidity_pct / 10000.0

        n = 1.0 + n_minus_1 * pressure_factor * temperature_factor * humidity_factor

        return n

    # --------------------------------------------------
    # Execute
    # --------------------------------------------------

    def execute(self, state):

        tracking_wl = state.tracking_wavelength_nm
        quantum_wl = state.quantum_wavelength_nm

        p_tx = getattr(state, "tx_pressure_hPa", getattr(state, "pressure_hPa", 1013.25))
        p_rx = getattr(state, "rx_pressure_hPa", getattr(state, "pressure_hPa", 1013.25))
        pressure = (p_tx + p_rx) / 2.0

        t_tx = getattr(state, "tx_temperature_C", getattr(state, "temperature_C", 25.0))
        t_rx = getattr(state, "rx_temperature_C", getattr(state, "temperature_C", 25.0))
        temperature = (t_tx + t_rx) / 2.0

        rh_tx = getattr(state, "tx_humidity_pct", getattr(state, "relative_humidity_pct", 80.0))
        rh_rx = getattr(state, "rx_humidity_pct", getattr(state, "relative_humidity_pct", 80.0))
        humidity = (rh_tx + rh_rx) / 2.0

        range_m = state.link_distance_km * 1000.0

        # ==========================================
        # Refractive Index
        # ==========================================

        n_tracking = self.refractive_index_air(
            tracking_wl, pressure, temperature, humidity
        )

        n_quantum = self.refractive_index_air(
            quantum_wl, pressure, temperature, humidity
        )

        # ==========================================
        # Differential Refractive Index
        # ==========================================

        delta_n = n_tracking - n_quantum

        # ==========================================
        # Differential Refraction
        #
        # Scale relative to
        # bulk atmospheric bending
        # ==========================================

        base_bending = state.ray_bending_angle_urad

        mean_n = (n_tracking + n_quantum) / 2.0

        differential_refraction = abs(delta_n) / max(mean_n - 1.0, 1e-12)

        differential_refraction *= abs(base_bending)

        # ==========================================
        # Receiver Plane Separation
        # ==========================================

        receiver_separation_m = differential_refraction * 1e-6 * range_m

        receiver_separation_mm = receiver_separation_m * 1000.0

        # ==========================================
        # FSM Correction
        # ==========================================

        fsm_correction = differential_refraction
        # ==========================================
        # PROPAGATION SLICE CHROMATIC REFRACTION (v0.4)
        # ==========================================

        total_differential = 0.0
        total_receiver_offset_mm = 0.0
        cumulative_offset = 0.0

        if state.propagation_slices:

            for s in state.propagation_slices:

                local_tracking_n = self.refractive_index_air(
                    tracking_wl,
                    s.pressure_hPa,
                    s.temperature_C,
                    s.relative_humidity_pct,
                )

                local_quantum_n = self.refractive_index_air(
                    quantum_wl, s.pressure_hPa, s.temperature_C, s.relative_humidity_pct
                )
                local_delta_n = abs(local_tracking_n - local_quantum_n)

                local_mean_n = (local_tracking_n + local_quantum_n) / 2.0

                local_bending = getattr(s, "ray_bending_urad", 0.0)

                local_refraction = local_delta_n / max(local_mean_n - 1.0, 1e-12)

                local_refraction *= abs(local_bending)

                local_offset_mm = (
                    local_refraction * 1e-6 * s.distance_from_tx_m * 1000.0
                )
                s.tracking_refractive_index = local_tracking_n

                s.quantum_refractive_index = local_quantum_n
                s.tracking_wavelength_nm = tracking_wl
                s.quantum_wavelength_nm = quantum_wl

                s.differential_refraction_urad = local_refraction

                s.receiver_offset_mm = local_offset_mm
                s.receiver_separation_mm = local_offset_mm
                s.fsm_correction_required_urad = local_refraction
                total_differential += local_refraction
                total_receiver_offset_mm += local_offset_mm
                cumulative_offset += local_offset_mm

                s.cumulative_receiver_separation_mm = cumulative_offset
                s.cumulative_fsm_correction_urad = total_differential
                s.delta_refractive_index = local_delta_n
                s.mean_refractive_index = local_mean_n
                s.delta_wavelength_nm = tracking_wl - quantum_wl

                s.chromatic_dispersion_factor = local_delta_n / max(local_mean_n, 1e-12)
                s.beacon_qkd_offset_urad = local_refraction
                s.notes = (
                    f"{tracking_wl:.0f}/{quantum_wl:.0f} nm "
                    f"Δn={local_delta_n:.3e} "
                    f"Offset={local_refraction:.3f} urad"
                )

            print()
            print("===== CHROMATIC REFRACTION → SLICES =====")

            for s in state.propagation_slices[:5]:

                print(
                    f"Slice {s.slice_id}: "
                    f"nT={s.tracking_refractive_index:.9f} "
                    f"nQ={s.quantum_refractive_index:.9f} "
                    f"Diff={s.differential_refraction_urad:.6f} urad"
                )

            print("==============================")
            print()

        # ==========================================
        # Save Results
        # ==========================================
        if state.propagation_slices:
            state.receiver_separation_mm = total_receiver_offset_mm
        else:
            state.receiver_separation_mm = receiver_separation_mm

        state.tracking_refractive_index = n_tracking

        state.quantum_refractive_index = n_quantum

        if state.propagation_slices:

            state.differential_refraction_urad = total_differential
            state.fsm_correction_required_urad = total_differential

        else:

            state.differential_refraction_urad = differential_refraction
            state.fsm_correction_required_urad = differential_refraction

        if state.propagation_slices:
            state.beacon_qkd_offset_urad = total_differential
        else:
            state.beacon_qkd_offset_urad = differential_refraction

        state.receiver_plane_offset_mm = state.receiver_separation_mm
        state.delta_refractive_index = delta_n
        state.mean_refractive_index = mean_n
        if state.propagation_slices:

            state.average_tracking_refractive_index = sum(
                s.tracking_refractive_index for s in state.propagation_slices
            ) / len(state.propagation_slices)

            state.average_quantum_refractive_index = sum(
                s.quantum_refractive_index for s in state.propagation_slices
            ) / len(state.propagation_slices)

        state.debug_message = "Chromatic refraction completed"

        # ==========================================
        # VERIFIER TEXT GENERATION
        # ==========================================
        if "turb" not in state.verifier_text:
            state.verifier_text["turb"] = ""

        state.verifier_text["turb"] += f"""
**Tracking Refractive Index**
n_T = {n_tracking:.9f}

**Quantum Refractive Index**
n_Q = {n_quantum:.9f}

**Differential Refractive Index**
Δn = |n_T - n_Q| = {abs(delta_n):.3e}

**Differential Refraction**
θ_diff = Δn / (mean_n - 1) · θ_bend = {state.differential_refraction_urad:.4f} µrad

**Receiver Plane Separation**
Δy_sep = θ_diff · L = {state.receiver_separation_mm:.4f} mm

**FSM Correction Required**
θ_FSM = θ_diff = {state.fsm_correction_required_urad:.4f} µrad
"""

        # ==========================================
        # Console Output
        # ==========================================

        print()

        print(f"Tracking WL: " f"{tracking_wl:.0f} nm")

        print(f"Quantum WL: " f"{quantum_wl:.0f} nm")

        print(f"n(Tracking): " f"{n_tracking:.9f}")

        print(f"n(Quantum): " f"{n_quantum:.9f}")

        if state.propagation_slices:

            print(
                f"Integrated Differential Refraction: "
                f"{state.differential_refraction_urad:.3f} urad"
            )

            print(
                f"Integrated Receiver Separation: "
                f"{state.receiver_separation_mm:.3f} mm"
            )

        else:

            print(f"Differential Refraction: " f"{differential_refraction:.3f} urad")

            print(f"Receiver Separation: " f"{receiver_separation_mm:.3f} mm")

        if state.propagation_slices:

            print(
                f"FSM Correction Required: "
                f"{state.fsm_correction_required_urad:.3f} urad"
            )

        else:

            print(f"FSM Correction Required: " f"{fsm_correction:.3f} urad")
