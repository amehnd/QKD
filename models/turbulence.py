"""
turbulence.py

Maritime Optical Turbulence Model

Computes:

    Cn²

    Fried Parameter r0

    Rytov Variance

    Scintillation Index

    Beam Wander

    Beam Spread

    Greenwood Frequency

Version:
    0.3
"""

import math
from core.model import Model


class TurbulenceModel(Model):

    name = "Turbulence"

    description = "Maritime optical turbulence model"

    version = "0.3"

    inputs = [
        "propagation_slices",
        "Cn2_m2_3",
        "link_distance_km",
        "wavelength_nm",
        "tx_temperature_C",
        "rx_temperature_C",
        "tx_humidity_pct",
        "rx_humidity_pct",
        "tx_pressure_hPa",
        "rx_pressure_hPa",
        "tx_visibility_km",
        "rx_visibility_km",
        "tx_wind_speed_m_s",
        "rx_wind_speed_m_s",
        "sea_surface_temperature_C",
        "marine_BL_height_m",
        "evap_duct_height_m",
        "wave_height_m",
        "cn2_model",
    ]

    outputs = [
        "fried_parameter_m",
        "rytov_variance",
        "scintillation_index",
        "beam_wander_urad",
        "beam_spread_factor",
        "greenwood_frequency_Hz",
        "isoplanatic_angle_urad",
        "coherence_time_ms",
        "scintillation_loss_dB",
        "temperature_structure_function",
        "temperature_structure_constant",
        "friction_velocity_m_s",
        "temperature_scale_K",
        "monin_obukhov_length_m",
        "stability_parameter",
    ]

    # --------------------------------------------------
    # Validation
    # --------------------------------------------------

    def validate(self, state):

        if not state.propagation_slices:
            raise ValueError("Adaptive slicing must run before Turbulence.")

        if state.link_distance_km <= 0:
            state.link_distance_km = 0.1

        if state.wavelength_nm <= 0:
            state.wavelength_nm = 1550

        return True

    def _rytov_variance_andrews(self, cn2, wavelength_m, path_length_m):
        """
        Andrews & Phillips (2005)

        Laser Beam Propagation through Random Media
        Eq. (12.24)

        Spherical-wave Rytov variance (appropriate for divergent FSO links)
        """

        k = 2.0 * math.pi / wavelength_m

        sigma_R2 = 0.496 * cn2 * (k ** (7.0 / 6.0)) * (path_length_m ** (11.0 / 6.0))

        return max(sigma_R2, 0.0)

    def _gamma_gamma_scintillation(self, sigma_R2):
        """
        Al-Habash, Andrews & Phillips (2001)

        Gamma-Gamma turbulence model

        Returns:
            scintillation index
        """

        sigma_R2 = max(sigma_R2, 1e-9)

        x = 0.49 * sigma_R2 / ((1.0 + 1.11 * sigma_R2 ** (12.0 / 5.0)) ** (7.0 / 6.0))

        alpha = 1.0 / max(math.expm1(x), 1e-12)

        y = 0.51 * sigma_R2 / ((1.0 + 0.69 * sigma_R2 ** (12.0 / 5.0)) ** (5.0 / 6.0))

        beta = 1.0 / max(math.expm1(y), 1e-12)
        scintillation = 1.0 + 1.0 / alpha + 1.0 / beta + 1.0 / (alpha * beta) - 1.0

        return max(scintillation, 0.0)

    def _beam_wander_andrews(self, cn2, wavelength_m, path_length_m, tx_aperture_m):
        """
        Andrews & Phillips (2005)

        Beam Wander
        Laser Beam Propagation through Random Media

        Returns
        -------
        beam wander (urad)
        """

        sigma_bw2 = 2.42 * cn2 * (path_length_m**3) * (tx_aperture_m / 2.0) ** (-1.0 / 3.0)

        sigma_bw = math.sqrt(max(sigma_bw2, 0.0))

        return (sigma_bw / max(path_length_m, 1.0)) * 1e6

    def _beam_spread_andrews(self, rytov_variance):
        """
        Andrews & Phillips (2005)

        Turbulence-induced beam spreading.

        Returns
        -------
        Beam spread factor
        """

        sigma = max(rytov_variance, 0.0)

        spread = math.sqrt(1.0 + 1.63 * sigma + 0.21 * sigma**2)

        return max(1.0, spread)

    def _greenwood_frequency(self, wind_speed, fried_parameter):
        """
        Greenwood (1977)

        Adaptive optics Greenwood frequency.

        Returns
        -------
        Hz
        """

        return 0.426 * wind_speed / max(fried_parameter, 1e-9)

    def _isoplanatic_angle(self, fried_parameter, propagation_distance):
        """
        Fried (1982)

        Isoplanatic Angle

        Returns
        -------
        radians
        """

        theta0 = 0.58 * fried_parameter / max(propagation_distance, 1.0)

        return theta0

    def _coherence_time(self, fried_parameter, wind_speed):
        """
        Greenwood (1977)

        Atmospheric coherence time

        Returns
        -------
        seconds
        """

        tau0 = 0.314 * fried_parameter / max(wind_speed, 0.1)

        return tau0

    # --------------------------------------------------
    # Execute
    # --------------------------------------------------

    def execute(self, state):

        model_type = state.cn2_model
        print()
        print("CN2 MODEL =", model_type)

        temperature = (state.tx_temperature_C + state.rx_temperature_C) / 2.0

        humidity = (state.tx_humidity_pct + state.rx_humidity_pct) / 2.0

        pressure = (state.tx_pressure_hPa + state.rx_pressure_hPa) / 2.0

        visibility = max((state.tx_visibility_km + state.rx_visibility_km) / 2.0, 0.1)

        wind = max((state.tx_wind_speed_m_s + state.rx_wind_speed_m_s) / 2.0, 0.1)

        temp_diff = abs(state.sea_surface_temperature_C - temperature)

        humidity_factor = 0.5 + 0.5 * humidity / 100.0

        visibility_factor = 1.0 / max(math.sqrt(visibility), 0.1)

        pressure_factor = max(pressure, 1.0) / 1013.25
        wave_factor = 1.0 + state.wave_height_m / 5.0
        mbl_factor = 1.0 + state.marine_BL_height_m / 1000.0

        duct_factor = 1.0 + state.evap_duct_height_m / 100.0

        maritime_cn2 = (
            1e-15
            * visibility_factor
            * pressure_factor
            * wave_factor
            * (1 + wind / 5.0)
            * (1 + temp_diff / 5.0)
            * humidity_factor
            * mbl_factor
            * duct_factor
        )

        if model_type == "User Defined":
            cn2 = state.Cn2_m2_3

        elif model_type == "Marine MOST":
            cn2 = maritime_cn2
        elif model_type == "Marine MOST (Remote Sensing 2023)":

            # ------------------------------------------
            # Constants
            # ------------------------------------------

            z = state.measurement_height_m

            P = pressure

            T = temperature + 273.15

            wind = max(wind, 0.1)

            deltaT = state.sea_surface_temperature_C - temperature

            # ------------------------------------------
            # Engineering approximation
            # (until measured sonic-anemometer data
            # are available)
            # ------------------------------------------

            u_star = 0.035 * wind

            T_star = deltaT / max(wind, 0.5)

            # Save

            # ------------------------------------------
            # Monin–Obukhov Length
            # Paper Eq. (4)
            # ------------------------------------------

            kappa = 0.4
            g = 9.81

            if abs(T_star) < 1e-6:

                L = 1e9

            else:

                L = ((u_star**2) * T) / (kappa * g * T_star)

            # ------------------------------------------
            # Stability Parameter
            # ξ = z / L
            # ------------------------------------------

            xi = z / max(abs(L), 1e-9)

            if L < 0:
                xi = -xi

            print()
            print("REMOTE SENSING MODEL")
            print("-------------------------")
            print("u* =", u_star)
            print("T* =", T_star)
            print("L =", L)
            print("xi =", xi)

            # ======================================
            # Remote Sensing 2023 Equation (10)
            # ======================================

            if xi <= -1.0:

                fT = 0.85

            elif xi <= 0.0:

                fT = 15.7 * ((1.0 - 79.5 * xi) ** (-2.0 / 3.0))

            else:

                fT = 15.7 * ((1.0 + 382.3 * xi) ** (-2.0 / 3.0))

            # ======================================
            # Equation (3)
            # CT²
            # ======================================

            CT2 = fT * (T_star**2) / (z ** (2.0 / 3.0))

            # ======================================
            # Solar heating factor
            # ======================================

            solar_factor = 1.0

            if hasattr(state, "solar_elevation_deg"):

                if state.solar_elevation_deg > 0:

                    solar_factor += state.solar_elevation_deg / 90.0

            CT2 *= solar_factor

            state.friction_velocity_m_s = u_star
            state.temperature_scale_K = T_star
            state.monin_obukhov_length_m = L
            state.stability_parameter = xi
            state.temperature_structure_function = fT
            state.temperature_structure_constant = CT2

            # ======================================
            # Equation (2)
            # Cn²
            # ======================================

            cn2 = ((79e-6 * P) / (T**2)) ** 2 * CT2

            state.Cn2_m2_3 = cn2

            print("fT =", fT)
            print("CT² =", CT2)
            print("Cn² =", cn2)

        elif model_type == "Hybrid":
            cn2 = 0.5 * state.Cn2_m2_3 + 0.5 * maritime_cn2
        elif model_type == "Hufnagel-Valley":

            h = 100

            A = 1.7e-14

            v = wind

            cn2 = (
                0.00594 * (v / 27) ** 2 * (1e-5 * h) ** 10 * math.exp(-h / 1000)
                + 2.7e-16 * math.exp(-h / 1500)
                + A * math.exp(-h / 100)
            )
        elif model_type == "Tatarski":

            cn2 = 1e-14 * (wind / 5) * (10 / max(visibility, 0.01))

        else:
            cn2 = maritime_cn2

        # ==========================================
        # Land / Sea Effect
        # ==========================================

        sea_fraction = getattr(state, "sea_percentage", 100.0) / 100.0
        land_fraction = getattr(state, "land_percentage", 0.0) / 100.0

        # Marine paths generally exhibit stronger optical turbulence.
        surface_factor = 1.0 * sea_fraction + 0.7 * land_fraction

        cn2 *= surface_factor

        if model_type == "Marine MOST (Remote Sensing 2023)":

            print()
            print("REMOTE SENSING RESULTS")
            print("---------------------------")
            print(f"u*   = {u_star:.4f} m/s")
            print(f"T*   = {T_star:.4f} K")
            print(f"L    = {L:.4f} m")
            print(f"xi   = {xi:.4f}")
            print(f"fT   = {fT:.4f}")
            print(f"CT²  = {CT2:.3e}")
            print(f"Cn²  = {cn2:.3e}")

        state.Cn2_m2_3 = cn2

        wavelength_m = state.wavelength_nm * 1e-9

        range_m = state.link_distance_km * 1000.0

        wind = max((state.tx_wind_speed_m_s + state.rx_wind_speed_m_s) / 2.0, 0.1)
        tx_aperture_m = state.tx_aperture_mm / 1000.0

        # ==========================================
        # Optical Wavenumber
        # ==========================================

        k = 2.0 * math.pi / wavelength_m

        # ==========================================
        # Fried Parameter
        #
        # r0
        # ==========================================

        base = max(0.423 * (k**2) * max(cn2, 1e-18) * max(range_m, 1.0), 1e-18)

        fried_parameter = base ** (-3.0 / 5.0)

        # ==========================================
        # Rytov Variance
        #
        # Spherical wave
        # ==========================================

        rytov_variance = self._rytov_variance_andrews(
            cn2=cn2, wavelength_m=wavelength_m, path_length_m=range_m
        )

        # ==========================================
        # Scintillation Index
        #
        # Weak fluctuation
        # ==========================================

        scintillation_index = self._gamma_gamma_scintillation(rytov_variance)
        # ==========================================
        # Beam Wander
        #
        # Approximation
        # ==========================================

        # ==========================================
        # Beam Wander
        #
        # Engineering maritime model
        # ==========================================

        beam_wander_urad = self._beam_wander_andrews(
            cn2=cn2,
            wavelength_m=wavelength_m,
            path_length_m=range_m,
            tx_aperture_m=tx_aperture_m,
        )

        beam_wander_urad = max(0.1, min(beam_wander_urad, 200.0))
        print()
        print("BEAM WANDER DEBUG")
        print("------------------")

        print("Cn2 =", cn2)

        print("Range =", range_m)

        print("k =", k)

        print("Tx Aperture =", tx_aperture_m)

        print("beam_wander_urad =", beam_wander_urad)

        # ==========================================
        # Beam Spread Factor
        #
        # Turbulence-induced spreading
        # ==========================================

        beam_spread = self._beam_spread_andrews(rytov_variance)
        # ==========================================
        # Greenwood Frequency
        #
        # Adaptive optics bandwidth
        # ==========================================

        greenwood_frequency = self._greenwood_frequency(wind, fried_parameter)
        # ==========================================
        # Isoplanatic Angle
        #
        # theta0 ≈ 0.31 r0 / L
        # ==========================================

        isoplanatic_angle_rad = self._isoplanatic_angle(fried_parameter, range_m)

        isoplanatic_angle_urad = isoplanatic_angle_rad * 1e6

        # ==========================================
        # Coherence Time
        #
        # tau0 ≈ 0.31 r0 / V
        # ==========================================

        coherence_time_s = self._coherence_time(fried_parameter, wind)

        coherence_time_ms = coherence_time_s * 1e3

        # ==========================================
        # Scintillation Loss
        #
        # Engineering estimate
        # ==========================================

        scintillation_loss_dB = 4.343 * math.log(1.0 + scintillation_index)

        scintillation_loss_dB = max(0.0, scintillation_loss_dB)

        # =========================
        # BEAM WANDER MODEL
        # =========================

        state.beam_wander_urad = beam_wander_urad

        # ==========================================
        # v0.4 Adaptive Slice Turbulence
        # ==========================================

        if state.propagation_slices:
            cn2_sum = 0.0
            weighted_r0_sum = 0.0
            weighted_rytov_sum = 0.0
            weighted_wander_sum = 0.0
            weighted_wind_cn2_sum = 0.0
            
            L_total = max(range_m, 1.0)

            for s in state.propagation_slices:
                height_factor = math.exp(
                    -s.beam_height_m / max(state.marine_BL_height_m, 1.0)
                )

                local_wind = max(getattr(s, "wind_speed_m_s", wind), 0.1)
                wind_factor = 1.0 + 0.05 * (local_wind / 5.0 - 1.0)
                local_cn2 = max(cn2 * height_factor * max(wind_factor, 0.5), 1e-18)

                s.Cn2 = local_cn2
                s.turbulence_strength = math.sqrt(local_cn2)

                slice_L = max(s.length_m, 1.0)
                base = max(0.423 * k**2 * local_cn2 * slice_L, 1e-18)
                s.fried_parameter_m = base ** (-3 / 5)

                z = max(s.center_m, 0.1)
                norm_z = min(max(z / L_total, 1e-4), 0.9999)

                # Path-weighted sums
                cn2_sum += local_cn2 * slice_L
                weighted_r0_sum += local_cn2 * (norm_z ** (5.0 / 3.0)) * slice_L
                weighted_rytov_sum += local_cn2 * (norm_z ** (5.0 / 6.0)) * ((1.0 - norm_z) ** (5.0 / 6.0)) * slice_L
                weighted_wander_sum += local_cn2 * ((1.0 - norm_z) ** 2) * slice_L
                weighted_wind_cn2_sum += local_cn2 * (local_wind ** (5.0 / 3.0)) * slice_L

                s.rytov_variance = self._rytov_variance_andrews(
                    cn2=local_cn2, wavelength_m=wavelength_m, path_length_m=slice_L
                )
                s.scintillation_index = self._gamma_gamma_scintillation(
                    s.rytov_variance
                )
                s.beam_wander_urad = self._beam_wander_andrews(
                    cn2=local_cn2,
                    wavelength_m=wavelength_m,
                    path_length_m=slice_L,
                    tx_aperture_m=tx_aperture_m,
                )

                local_rytov = self._rytov_variance_andrews(
                    cn2=local_cn2, wavelength_m=wavelength_m, path_length_m=slice_L
                )
                s.beam_spread_factor = self._beam_spread_andrews(local_rytov)
                s.greenwood_frequency_Hz = self._greenwood_frequency(
                    local_wind, s.fried_parameter_m
                )
                theta0 = self._isoplanatic_angle(s.fried_parameter_m, slice_L)
                s.isoplanatic_angle_urad = theta0 * 1e6
                tau0 = self._coherence_time(s.fried_parameter_m, local_wind)
                s.coherence_time_ms = tau0 * 1000
                s.scintillation_loss_dB = 4.343 * math.log(1.0 + s.scintillation_index)
                if s.rytov_variance < 0.3:
                    s.turbulence_regime = "Weak"
                elif s.rytov_variance < 1.0:
                    s.turbulence_regime = "Moderate"
                else:
                    s.turbulence_regime = "Strong"
                s.notes = f"Cn2={s.Cn2:.2e}, " f"r0={s.fried_parameter_m:.3f} m"

            cn2 = cn2_sum / L_total
            fried_parameter = (0.423 * (k**2) * max(weighted_r0_sum, 1e-18)) ** (-3.0 / 5.0)
            rytov_variance = max(0.907 * (k ** (7.0 / 6.0)) * (L_total ** (5.0 / 6.0)) * weighted_rytov_sum, 1e-9)
            scintillation_index = self._gamma_gamma_scintillation(rytov_variance)

            # Beam wander is heavily weighted towards transmitter (z=0, factor (1 - z/L)^2)
            wander_var2 = 2.42 * (L_total**2) * weighted_wander_sum / max((k * tx_aperture_m) ** (1.0 / 3.0), 1e-6)
            beam_wander_urad = math.sqrt(max(wander_var2, 0.0)) * 1e6
            beam_spread = self._beam_spread_andrews(rytov_variance)

            effective_v_wind = (weighted_wind_cn2_sum / max(cn2_sum, 1e-18)) ** (3.0 / 5.0)
            greenwood_frequency = self._greenwood_frequency(effective_v_wind, fried_parameter)
            isoplanatic_angle_urad = self._isoplanatic_angle(fried_parameter, L_total) * 1e6
            coherence_time_ms = self._coherence_time(fried_parameter, effective_v_wind) * 1000.0
            scintillation_loss_dB = sum(
                s.scintillation_loss_dB for s in state.propagation_slices
            )
            state.scintillation_loss_dB = scintillation_loss_dB

            print()
            print("===== TURBULENCE → SLICES =====")
            print("Slices Updated :", len(state.propagation_slices))
            print("===============================")
            print()

        # ==========================================
        # Save Results
        # ==========================================
        state.Cn2_m2_3 = cn2

        state.fried_parameter_m = fried_parameter

        state.greenwood_frequency_Hz = greenwood_frequency
        state.isoplanatic_angle_urad = isoplanatic_angle_urad

        state.coherence_time_ms = coherence_time_ms

        state.rytov_variance = rytov_variance

        state.scintillation_index = scintillation_index

        state.beam_spread_factor = beam_spread
        state.beam_wander_urad = beam_wander_urad

        state.scintillation_loss_dB = scintillation_loss_dB
        state.scintillation_index = scintillation_index

        state.debug_message = "Turbulence completed"

        # ==========================================
        # Console Output
        # ==========================================

        print()
        print("LAND / SEA EFFECT")
        print("------------------")
        print("Land % =", state.land_percentage)
        print("Sea %  =", state.sea_percentage)
        print("Surface Factor =", surface_factor)

        print()

        print(f"Cn²: " f"{cn2:.3e}")

        print(f"Fried Parameter r0: " f"{fried_parameter:.3f} m")

        print(f"Rytov Variance: " f"{rytov_variance:.3f}")

        print(f"Scintillation Index: " f"{scintillation_index:.3f}")

        print(f"Beam Wander: " f"{beam_wander_urad:.6e} urad")

        print(f"Beam Spread Factor: " f"{beam_spread:.3f}")

        print(f"Greenwood Frequency: " f"{greenwood_frequency:.1f} Hz")
        print("LOCAL =", scintillation_loss_dB)
        print("STATE =", state.scintillation_loss_dB)

        print(f"Scintillation Loss: " f"{state.scintillation_loss_dB:.2f} dB")

        # ==========================================
        # VERIFIER TEXT GENERATION
        # ==========================================
        if model_type == "Marine MOST (Remote Sensing 2023)":
            cn2_formula = f"""Cn2 (Marine MOST 2023)
u* = 0.035 · v = {state.friction_velocity_m_s:.4f} m/s
T* = ΔT / max(v, 0.5) = {state.temperature_scale_K:.4f} K
L = (u*² · T) / (κ · g · T*) = {state.monin_obukhov_length_m:.4f} m
ξ = z / L = {state.stability_parameter:.4f}
fT(ξ) = {state.temperature_structure_function:.4f}
CT² = fT · T*² / z^(2/3) = {state.temperature_structure_constant:.3e} K²/m^(2/3)
C_n² = (79e-6 · P / T²)² · CT² = {cn2:.3e} m^(-2/3)
"""
        elif model_type == "Marine MOST":
            cn2_formula = f"""Cn2 (Marine MOST)
C_n² = 1e-15 · f_vis · f_P · f_wave · f_wind · f_T · f_RH · f_MBL · f_duct = {cn2:.3e} m^(-2/3)
"""
        else:
            cn2_formula = f"""Cn2 ({model_type})
C_n² = {cn2:.3e} m^(-2/3)
"""

        state.verifier_text["turb"] = f"""
{cn2_formula}
**Fried Parameter**
k = 2π / λ
r_0 = (0.423 · k² · C_n² · L)^(-3/5) = {fried_parameter:.6f} m

**Rytov Variance**
σ_R² = 0.496 · C_n² · k^(7/6) · L^(11/6) = {rytov_variance:.6f}

**Scintillation Index**
x = 0.49 · σ_R² / (1 + 1.11 · σ_R^(24/5))^(7/6)
y = 0.51 · σ_R² / (1 + 0.69 · σ_R^(24/5))^(5/6)
α = 1 / (exp(x) - 1), β = 1 / (exp(y) - 1)
σ_I² = 1 + 1/α + 1/β + 1/(αβ) - 1 = {scintillation_index:.6f}

**Beam Wander**
σ_bw² = 2.42 · C_n² · L³ · (D_tx / 2)^(-1/3)
BW = √(σ_bw²) / L · 10⁶ = {beam_wander_urad:.6f} µrad

**Beam Spread Factor**
BSF = √(1 + 1.63 · σ_R² + 0.21 · (σ_R²)²) = {beam_spread:.6f}

**Greenwood Frequency**
f_G = 0.426 · v / r_0 = {greenwood_frequency:.6f} Hz

**Isoplanatic Angle**
θ_0 = 0.58 · r_0 / L = {isoplanatic_angle_urad:.6f} µrad

**Coherence Time**
τ_0 = 0.314 · r_0 / v = {coherence_time_ms:.6f} ms

**Scintillation Loss**
L_scint = 4.343 · ln(1 + σ_I²) = {state.scintillation_loss_dB:.6f} dB

**Surface Refractive Index**
n_s = 1 + N_s * 10⁻⁶ = {getattr(state, 'surface_refractive_index', 0.0):.6f}

**dn/dz**
dn/dz = -10⁻⁶ * (79/T² * (P + 4800*e/T) * dT/dz - 79/T * dP/dz) = {getattr(state, 'dn_dz', 0.0):.4e}

**Ray Curvature**
κ_ray = -1/n * dn/dz * cos(θ) = {getattr(state, 'ray_curvature_1_m', 0.0):.4e} 1/m

**Ray Bending Angle**
θ_bend = ∫ κ_ray ds = {getattr(state, 'ray_bending_angle_urad', 0.0):.4f} µrad

**Elevation Bias**
θ_bias = -θ_bend / 2 = {getattr(state, 'effective_elevation_bias_urad', 0.0):.4f} µrad

**Beam Refraction Shift**
Δy_shift = ∫ (L-s) * κ_ray ds = {getattr(state, 'beam_refraction_shift_m', 0.0):.4f} m
"""
