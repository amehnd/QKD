"""
atmospheric_loss.py

Atmospheric optical attenuation model.

Calculates:

1. Visibility attenuation (Kim model)
2. Rain attenuation
3. Molecular scattering estimate
4. Aerosol attenuation estimate
5. Total atmospheric loss
6. Atmospheric transmission

Supports:
    850 nm
    1064 nm
    1310 nm
    1550 nm

Author:
    Maritime QKD Simulator

Version:
    0.4
"""

import math


from core.model import Model


class AtmosphericLossModel(Model):

    name = "AtmosphericLoss"

    description = "Atmospheric attenuation model"

    version = "0.4"

    inputs = [
        "wavelength_nm",
        "visibility_km",
        "rain_rate_mm_hr",
        "link_distance_km",
        "relative_humidity_pct",
    ]

    outputs = [
        "visibility_loss_dB",
        "rain_loss_dB",
        "molecular_loss_dB",
        "aerosol_loss_dB",
        "atmospheric_loss_dB",
        "atmospheric_transmission",
    ]

    # --------------------------------------------------
    # Validation
    # --------------------------------------------------

    def validate(self, state):

        if not state.propagation_slices:

            raise ValueError("Adaptive Slicing must run before Atmospheric Loss.")

        if state.visibility_km <= 0:

            state.visibility_km = 0.05

        if state.link_distance_km <= 0:

            state.link_distance_km = 0.1

        if state.wavelength_nm <= 0:

            state.wavelength_nm = 1550

        valid_models = ["Kim", "Kruse", "Al Naboulsi", "MODTRAN", "libRadtran"]

        if getattr(state, "atmospheric_model", "Kim") not in valid_models:
            state.atmospheric_model = "Kim"

        valid_fog = ["Radiation", "Advection"]

        if getattr(state, "fog_type", "Advection") not in valid_fog:
            state.fog_type = "Advection"

        # -------------------------------
        # Rain attenuation model
        # -------------------------------

        valid_rain_models = ["Carbonneau", "ITU", "Marshall-Palmer"]

        if getattr(state, "rain_model", "Carbonneau") not in valid_rain_models:
            state.rain_model = "Carbonneau"

        # -------------------------------
        # Molecular absorption model
        # -------------------------------

        valid_molecular_models = ["Beer-Lambert", "HITRAN", "MODTRAN"]

        if (
            getattr(state, "molecular_model", "Beer-Lambert")
            not in valid_molecular_models
        ):
            state.molecular_model = "Beer-Lambert"

        # -------------------------------
        # Aerosol attenuation model
        # -------------------------------

        valid_aerosol_models = [
            "Kim",
            "Kruse",
            "Ijaz",
            "Shettle-Fenn",
            "Angstrom",
        ]
        if getattr(state, "aerosol_model", "Shettle-Fenn") not in valid_aerosol_models:
            state.aerosol_model = "Shettle-Fenn"
        return True

    def _rayleigh_scattering(self, wavelength_um, pressure_hpa, temperature_K):
        """
        Bucholtz (1995)
        Rayleigh scattering coefficient
        Returns dB/km
        """

        pressure_ratio = pressure_hpa / 1013.25

        temperature_ratio = 288.15 / temperature_K

        gamma = (
            0.008569
            * wavelength_um ** (-4)
            * (1 + 0.0113 * wavelength_um ** (-2) + 0.00013 * wavelength_um ** (-4))
        )

        gamma *= pressure_ratio

        gamma *= temperature_ratio

        return gamma * 4.343

    def _beer_lambert_absorption(
        self, wavelength_nm, pressure_hpa, temperature_K, humidity_pct
    ):
        """
        Beer-Lambert molecular absorption.

        Returns
        -------
        dB/km
        """

        if wavelength_nm >= 1500:
            alpha = 0.015

        elif wavelength_nm >= 1300:
            alpha = 0.010

        elif wavelength_nm >= 1000:
            alpha = 0.006

        else:
            alpha = 0.003

        pressure_factor = pressure_hpa / 1013.25

        humidity_factor = 1.0 + 0.003 * humidity_pct

        temperature_factor = (temperature_K / 288.15) ** 1.5

        return alpha * pressure_factor * humidity_factor * temperature_factor

    def _hitran_absorption(
        self, wavelength_nm, pressure_hpa, temperature_K, humidity_pct
    ):
        """
            HITRAN approximation.

            Placeholder until spectral database
            is integrated.

        Returns
        -------
        dB/km
        """

        if wavelength_nm >= 1500:
            alpha = 0.022

        elif wavelength_nm >= 1300:
            alpha = 0.013

        elif wavelength_nm >= 1000:
            alpha = 0.007

        else:
            alpha = 0.004

        pressure_factor = pressure_hpa / 1013.25

        humidity_factor = 1.0 + 0.004 * humidity_pct

        temperature_factor = (temperature_K / 288.15) ** 1.5

        return alpha * pressure_factor * humidity_factor * temperature_factor

    def _modtran_absorption(
        self, wavelength_nm, pressure_hpa, temperature_K, humidity_pct
    ):
        """
        MODTRAN approximation.

        Placeholder implementation.

        Returns
        -------
        dB/km
        """

        if wavelength_nm >= 1500:
            alpha = 0.018

        elif wavelength_nm >= 1300:
            alpha = 0.011

        elif wavelength_nm >= 1000:
            alpha = 0.006

        else:
            alpha = 0.003

        pressure_factor = pressure_hpa / 1013.25

        humidity_factor = 1.0 + 0.0035 * humidity_pct

        temperature_factor = (temperature_K / 288.15) ** 1.5

        return alpha * pressure_factor * humidity_factor * temperature_factor

    def _kim_aerosol(self, wavelength_um, visibility_km):
        """
        Kim aerosol attenuation.

        Returns
        -------
        dB/km
        """

        q = self._kim_q(visibility_km)

        gamma = 3.91 / max(visibility_km, 0.05) * (wavelength_um / 0.55) ** (-q)

        return gamma * 4.343

    def _kruse_aerosol(self, wavelength_um, visibility_km):
        """
        Kruse aerosol attenuation.

        Returns
        -------
        dB/km
        """

        q = 0.585 * visibility_km ** (1 / 3)

        gamma = 3.91 / max(visibility_km, 0.05) * (wavelength_um / 0.55) ** (-q)

        return gamma * 4.343

    def _ijaz_marine_aerosol(self, wavelength_um, humidity_pct, sea_percentage):
        """
        Ijaz maritime aerosol model.

        Returns
        -------
        dB/km
        """

        humidity_factor = 1.0 + 0.006 * humidity_pct

        sea_factor = 0.5 + 0.5 * sea_percentage / 100.0

        gamma = 0.08 * humidity_factor * sea_factor * (wavelength_um / 0.55) ** (-0.75)

        return gamma * 4.343

    def _shettle_fenn_aerosol(
        self, wavelength_um, relative_humidity_pct, maritime=True
    ):
        """
        Shettle & Fenn (1979)

        Maritime aerosol extinction coefficient.

        Returns
        -------
        dB/km
        """

        # -----------------------------
        # Dry maritime extinction
        # -----------------------------
        if maritime:
            beta0 = 0.08  # km^-1
            alpha = 0.70
        else:
            beta0 = 0.12
            alpha = 1.30

        RH = max(0.0, min(relative_humidity_pct / 100.0, 0.99))

        gamma = 0.35

        humidity_growth = (1.0 / (1.0 - RH)) ** gamma

        beta = beta0 * (wavelength_um / 0.55) ** (-alpha) * humidity_growth

        return beta * 4.343

    def _angstrom_aerosol(
        self,
        wavelength_um,
        visibility_km,
        aerosol_alpha,
    ):
        """
        Ångström aerosol attenuation model.

        Parameters
        ----------
        wavelength_um : float
        Operating wavelength (µm)

        visibility_km : float
        Meteorological visibility (km)

        aerosol_alpha : float
        Ångström exponent

        Returns
        -------
        float
        Aerosol extinction coefficient (dB/km)
        """

        reference_wavelength = 0.55

        visibility_km = max(visibility_km, 0.05)
        wavelength_um = max(wavelength_um, 1e-6)

        beta550 = 3.91 / visibility_km

        beta = beta550 * (wavelength_um / reference_wavelength) ** (-aerosol_alpha)

        return beta * 4.343

    # --------------------------------------------------
    # Kim Visibility Model
    # --------------------------------------------------

    def _kim_q(self, visibility):

        if visibility > 50:

            return 1.6

        elif visibility > 6:

            return 1.3

        elif visibility > 1:

            return 0.16 * visibility + 0.34

        elif visibility > 0.5:

            return visibility - 0.5

        else:

            return 0.0

    # --------------------------------------------------
    # Execute
    # --------------------------------------------------
    def _carbonneau_rain_attenuation(self, rain_rate, wavelength_nm):
        """
        Carbonneau optical rain attenuation model.

        Returns
        -------
        dB/km
        """

        if rain_rate <= 0:
            return 0.0

        if 1500 <= wavelength_nm <= 1600:

            a = 1.07
            b = 0.67

        elif 1250 <= wavelength_nm <= 1350:

            a = 1.15
            b = 0.66

        elif 1000 <= wavelength_nm <= 1100:

            a = 1.32
            b = 0.65

        else:

            a = 1.58
            b = 0.63

        return a * rain_rate**b


    def _itu_rain_attenuation(self, rain_rate, wavelength_nm, polarization="horizontal"):
        """
        ITU-R P.838-3
        Returns dB/km
        """
        if rain_rate <= 0:
            return 0.0

        if 1500 <= wavelength_nm <= 1600:
            if polarization.lower() == "horizontal":
                k = 1.05
                alpha = 0.70
            else:
                k = 1.02
                alpha = 0.69
        elif 1250 <= wavelength_nm <= 1350:
            k = 1.12
            alpha = 0.71
        elif 1000 <= wavelength_nm <= 1100:
            k = 1.25
            alpha = 0.72
        else:
            k = 1.30
            alpha = 0.72

        return k * rain_rate ** alpha


    def _marshall_palmer_rain_attenuation(self, rain_rate, wavelength_nm):
        """
        Marshall-Palmer optical approximation.

        Returns
        -------
        dB/km
        """

        if rain_rate <= 0:
            return 0.0

        if wavelength_nm >= 1500:

            c = 1.10
            d = 0.69

        elif wavelength_nm >= 1300:

            c = 1.18
            d = 0.68

        elif wavelength_nm >= 1000:

            c = 1.33
            d = 0.67

        else:

            c = 1.60
            d = 0.65

        return c * rain_rate**d

    def execute(self, state):
        q = None

        wavelength_um = max(state.wavelength_nm, 1) / 1000.0

        vis_tx = getattr(state, "tx_visibility_km", getattr(state, "visibility_km", 10.0))
        vis_rx = getattr(state, "rx_visibility_km", getattr(state, "visibility_km", 10.0))
        visibility = max((vis_tx + vis_rx) / 2.0, 0.05)

        range_km = max(state.link_distance_km, 0.1)

        hum_tx = getattr(state, "tx_humidity_pct", getattr(state, "relative_humidity_pct", 80.0))
        hum_rx = getattr(state, "rx_humidity_pct", getattr(state, "relative_humidity_pct", 80.0))
        humidity = max(0.0, min((hum_tx + hum_rx) / 2.0, 100.0))

        c_tx = getattr(state, "tx_cloud_cover_percent", getattr(state, "cloud_cover_percent", 0.0))
        c_rx = getattr(state, "rx_cloud_cover_percent", getattr(state, "cloud_cover_percent", 0.0))
        cloud_cover = max(0.0, min((c_tx + c_rx) / 2.0, 100.0))

        r_tx = getattr(state, "tx_rain_rate_mm_hr", getattr(state, "rain_rate_mm_hr", 0.0))
        r_rx = getattr(state, "rx_rain_rate_mm_hr", getattr(state, "rain_rate_mm_hr", 0.0))
        rain_rate = max((r_tx + r_rx) / 2.0, 0.0)

        # ==========================================
        # Visibility Attenuation
        # ==========================================

        model = getattr(state, "atmospheric_model", "Kim")

        if model == "Kim":

            q = self._kim_q(visibility)

            gamma = 3.91 / max(visibility, 0.01) * (wavelength_um / 0.55) ** (-q)

        elif model == "Kruse":

            q = 0.585 * visibility ** (1 / 3)

            gamma = 3.91 / max(visibility, 0.01) * (wavelength_um / 0.55) ** (-q)

        elif model == "Al Naboulsi":

            fog_type = getattr(state, "fog_type", "Advection")

            if fog_type == "Radiation":

                gamma = (0.18126 * wavelength_um**2 + 0.13709 * wavelength_um + 3.7502) / max(visibility, 0.01)

            else:
                gamma = (0.11478 * wavelength_um + 3.8367) / max(visibility, 0.01)
                
            gamma *= 4.343

        elif model == "MODTRAN":

            # Placeholder
            q = self._kim_q(visibility)

            gamma = 3.91 / max(visibility, 0.01) * (wavelength_um / 0.55) ** (-q)
            gamma *= 4.343

        elif model == "libRadtran":

            # Placeholder
            q = self._kim_q(visibility)

            gamma = 3.91 / max(visibility, 0.01) * (wavelength_um / 0.55) ** (-q)
            gamma *= 4.343

        visibility_loss = gamma * range_km
        print("\nDEBUG")
        print("Model =", model)
        if model in ["MODTRAN", "libRadtran"]:
            print("Using placeholder implementation (Kim)")
        print("Visibility =", visibility)
        print("Range =", range_km)
        print("Wavelength =", wavelength_um)
        if model != "Al Naboulsi":
            print("q =", q)
        print("Gamma =", gamma)
        print("Visibility Loss =", visibility_loss)

        # --------------------------------
        # Cloud estimate from weather
        # --------------------------------

        # --------------------------------
        # Cloud attenuation
        # --------------------------------

        cloud_loss_per_km = 0.05 * (cloud_cover / 100.0)

        cloud_loss = cloud_loss_per_km * range_km
        # ==========================================
        # Rain Attenuation
        # ==========================================

        rain_model = getattr(state, "rain_model", "Carbonneau")

        if rain_rate <= 0:

            rain_loss_per_km = 0.0

        elif rain_model == "Carbonneau":

            rain_loss_per_km = self._carbonneau_rain_attenuation(
                rain_rate, state.wavelength_nm
            )

        elif rain_model == "ITU":

            rain_loss_per_km = self._itu_rain_attenuation(
                rain_rate, state.wavelength_nm
            )

        elif rain_model == "Marshall-Palmer":

            rain_loss_per_km = self._marshall_palmer_rain_attenuation(
                rain_rate, state.wavelength_nm
            )

        rain_loss = rain_loss_per_km * range_km

        # ==========================================
        # Molecular Scattering
        #
        # Simplified estimate
        # ==========================================

        # ==========================================
        # Rayleigh (Molecular) Scattering
        # Based on Bucholtz (1995)
        # ==========================================

        p_tx = getattr(state, "tx_pressure_hPa", getattr(state, "pressure_hPa", 1013.25))
        p_rx = getattr(state, "rx_pressure_hPa", getattr(state, "pressure_hPa", 1013.25))
        pressure = (p_tx + p_rx) / 2.0

        t_tx = getattr(state, "tx_temperature_C", getattr(state, "temperature_C", 15.0))
        t_rx = getattr(state, "rx_temperature_C", getattr(state, "temperature_C", 15.0))
        temperature = (t_tx + t_rx) / 2.0 + 273.15

        

        molecular_model = getattr(state, "molecular_model", "Beer-Lambert")

        rayleigh = self._rayleigh_scattering(wavelength_um, pressure, temperature)

        if molecular_model == "Beer-Lambert":

            absorption = self._beer_lambert_absorption(
                state.wavelength_nm, pressure, temperature, humidity
            )

        elif molecular_model == "HITRAN":

            absorption = self._hitran_absorption(
                state.wavelength_nm, pressure, temperature, humidity
            )

        elif molecular_model == "MODTRAN":

            absorption = self._modtran_absorption(
                state.wavelength_nm, pressure, temperature, humidity
            )

        molecular_loss_per_km = rayleigh + absorption
        molecular_loss = molecular_loss_per_km * range_km

        # ==========================================
        # Aerosol Loss
        #
        # Humidity dependent
        # ==========================================

        # ==========================================
        # Aerosol Attenuation
        # Shettle & Fenn (1979)
        # Maritime Aerosol Model
        # ==========================================

        aerosol_model = getattr(state, "aerosol_model", "Shettle-Fenn")

        tx_alpha = getattr(state, "tx_aerosol_alpha", 1.3)
        rx_alpha = getattr(state, "rx_aerosol_alpha", 1.3)

        effective_alpha = (tx_alpha + rx_alpha) / 2.0
        state.effective_aerosol_alpha = effective_alpha

        maritime = state.sea_percentage >= state.land_percentage
        if aerosol_model == "Kim":

            aerosol_loss_per_km = self._kim_aerosol(wavelength_um, visibility)

        elif aerosol_model == "Kruse":

            aerosol_loss_per_km = self._kruse_aerosol(wavelength_um, visibility)

        elif aerosol_model == "Ijaz":

            aerosol_loss_per_km = self._ijaz_marine_aerosol(
                wavelength_um, humidity, state.sea_percentage
            )
        elif aerosol_model == "Angstrom":

            aerosol_loss_per_km = self._angstrom_aerosol(
                wavelength_um=wavelength_um,
                visibility_km=visibility,
                aerosol_alpha=effective_alpha,
            )

        elif aerosol_model == "Shettle-Fenn":

            aerosol_loss_per_km = self._shettle_fenn_aerosol(
                wavelength_um=wavelength_um,
                relative_humidity_pct=humidity,
                maritime=maritime,
            )

        aerosol_loss = aerosol_loss_per_km * range_km
        # ==========================================
        # Land / Sea Effect
        # ==========================================

        # Marine paths generally have lower aerosol attenuation
        # than continental paths.

        # ==========================================
        # Total Loss
        # ==========================================

        # ==========================================
        # v0.4 Adaptive Slice Propagation
        # ==========================================

        path_transmission = 1.0

        if state.propagation_slices:

            total_loss = 0.0

            for s in state.propagation_slices:

                slice_range_km = s.length_m / 1000.0

                slice_visibility = max(s.visibility_km, 0.05)

                # ----------------------------
                # Visibility
                # ----------------------------

                if model == "Kim":

                    q = self._kim_q(slice_visibility)

                    gamma = 3.91 / slice_visibility * (wavelength_um / 0.55) ** (-q)

                elif model == "Kruse":

                    q = 0.585 * slice_visibility ** (1 / 3)

                    gamma = 3.91 / slice_visibility * (wavelength_um / 0.55) ** (-q)

                elif model == "Al Naboulsi":

                    fog_type = getattr(state, "fog_type", "Advection")

                    if fog_type == "Radiation":

                        gamma = (0.18126 * wavelength_um**2 + 0.13709 * wavelength_um + 3.7502) / max(slice_visibility, 0.01)

                    else:

                        gamma = (0.11478 * wavelength_um + 3.8367) / max(slice_visibility, 0.01)
                        
                    gamma *= 4.343

                elif model == "MODTRAN":

                    q = self._kim_q(slice_visibility)

                    gamma = 3.91 / slice_visibility * (wavelength_um / 0.55) ** (-q)
                    gamma *= 4.343

                elif model == "libRadtran":

                    q = self._kim_q(slice_visibility)

                    gamma = 3.91 / slice_visibility * (wavelength_um / 0.55) ** (-q)

                visibility_slice = gamma * slice_range_km
                s.visibility_gamma_dB_per_km = gamma
                slice_rain = getattr(s, "rain_rate_mm_hr", rain_rate)

                if slice_rain <= 0:

                    rain_gamma = 0.0

                elif rain_model == "Carbonneau":

                    rain_gamma = self._carbonneau_rain_attenuation(
                        slice_rain, state.wavelength_nm
                    )

                elif rain_model == "ITU":

                    rain_gamma = self._itu_rain_attenuation(
                        slice_rain, state.wavelength_nm
                    )

                elif rain_model == "Marshall-Palmer":

                    rain_gamma = self._marshall_palmer_rain_attenuation(
                        slice_rain, state.wavelength_nm
                    )

                rain_slice = rain_gamma * slice_range_km

                slice_pressure = s.pressure_hPa

                slice_temperature = s.temperature_C + 273.15
                slice_humidity = getattr(s, "humidity_pct", state.relative_humidity_pct)
                slice_sea = getattr(s, "sea_percentage", state.sea_percentage)

                slice_land = getattr(s, "land_percentage", state.land_percentage)

                slice_alpha = getattr(s, "aerosol_alpha", (tx_alpha + rx_alpha) / 2.0)

                maritime = slice_sea >= slice_land

                rayleigh = self._rayleigh_scattering(
                    wavelength_um, slice_pressure, slice_temperature
                )

                if molecular_model == "Beer-Lambert":

                    absorption = self._beer_lambert_absorption(
                        state.wavelength_nm,
                        slice_pressure,
                        slice_temperature,
                        slice_humidity,
                    )

                elif molecular_model == "HITRAN":

                    absorption = self._hitran_absorption(
                        state.wavelength_nm,
                        slice_pressure,
                        slice_temperature,
                        slice_humidity,
                    )

                elif molecular_model == "MODTRAN":

                    absorption = self._modtran_absorption(
                        state.wavelength_nm,
                        slice_pressure,
                        slice_temperature,
                        slice_humidity,
                    )

                molecular_slice_per_km = rayleigh + absorption
                s.molecular_extinction_km = molecular_slice_per_km

                molecular_slice = molecular_slice_per_km * slice_range_km

                if aerosol_model == "Kim":

                    aerosol_slice_per_km = self._kim_aerosol(
                        wavelength_um, slice_visibility
                    )

                elif aerosol_model == "Kruse":

                    aerosol_slice_per_km = self._kruse_aerosol(
                        wavelength_um, slice_visibility
                    )

                elif aerosol_model == "Ijaz":

                    aerosol_slice_per_km = self._ijaz_marine_aerosol(
                        wavelength_um, slice_humidity, slice_sea
                    )
                elif aerosol_model == "Angstrom":

                    aerosol_slice_per_km = self._angstrom_aerosol(
                        wavelength_um=wavelength_um,
                        visibility_km=slice_visibility,
                        aerosol_alpha=slice_alpha,
                    )

                elif aerosol_model == "Shettle-Fenn":

                    aerosol_slice_per_km = self._shettle_fenn_aerosol(
                        wavelength_um=wavelength_um,
                        relative_humidity_pct=slice_humidity,
                        maritime=maritime,
                    )
                s.aerosol_extinction_km = aerosol_slice_per_km
                s.rain_extinction_km = rain_gamma
                s.rain_gamma_dB_per_km = rain_gamma

                aerosol_slice = aerosol_slice_per_km * slice_range_km
                slice_cloud = getattr(s, "cloud_cover_percent", cloud_cover)

                cloud_slice_per_km = 0.05 * slice_cloud / 100.0
                s.cloud_extinction_km = cloud_slice_per_km

                cloud_slice = cloud_slice_per_km * slice_range_km
                s.total_gamma_dB_per_km = (
                    gamma
                    + rain_gamma
                    + molecular_slice_per_km
                    + aerosol_slice_per_km
                    + cloud_slice_per_km
                )
                s.rain_gamma_dB_per_km = rain_gamma
                s.molecular_gamma_dB_per_km = molecular_slice_per_km
                s.aerosol_gamma_dB_per_km = aerosol_slice_per_km
                s.cloud_gamma_dB_per_km = cloud_slice_per_km

                slice_loss = (
                    visibility_slice
                    + rain_slice
                    + molecular_slice
                    + aerosol_slice
                    + cloud_slice
                )

                s.visibility_loss_dB = visibility_slice

                s.cloud_loss_dB = cloud_slice
                s.rain_loss_dB = rain_slice

                s.molecular_loss_dB = molecular_slice

                s.aerosol_loss_dB = aerosol_slice

                s.atmospheric_loss_dB = slice_loss
                s.atmospheric_transmission = 10 ** (-slice_loss / 10.0)
                s.atmospheric_transmission_percent = s.atmospheric_transmission * 100.0
                s.attenuation_coefficient_dB_per_km = s.total_gamma_dB_per_km
                path_transmission *= s.atmospheric_transmission
                s.cumulative_atmospheric_loss_dB = -10.0 * math.log10(
                    max(path_transmission, 1e-30)
                )
                s.cumulative_atmospheric_transmission = path_transmission
                s.notes = f"Atm Loss={slice_loss:.3f} dB"

                total_loss += slice_loss

            print()
            print("===== ATMOSPHERE → SLICES =====")
            print("Slices Updated :", len(state.propagation_slices))
            print("===============================")
            print()
            state.average_visibility_loss_dB = sum(
                s.visibility_loss_dB for s in state.propagation_slices
            ) / max(len(state.propagation_slices), 1)

            state.average_rain_loss_dB = sum(
                s.rain_loss_dB for s in state.propagation_slices
            ) / max(len(state.propagation_slices), 1)

            state.average_molecular_loss_dB = sum(
                s.molecular_loss_dB for s in state.propagation_slices
            ) / max(len(state.propagation_slices), 1)

            state.average_aerosol_loss_dB = sum(
                s.aerosol_loss_dB for s in state.propagation_slices
            ) / max(len(state.propagation_slices), 1)

            state.average_cloud_loss_dB = sum(
                s.cloud_loss_dB for s in state.propagation_slices
            ) / max(len(state.propagation_slices), 1)

        else:

            total_loss = (
                visibility_loss + rain_loss + molecular_loss + aerosol_loss + cloud_loss
            )
        # ==========================================
        # Transmission
        # ==========================================

        if state.propagation_slices:

            atmospheric_transmission = path_transmission

            total_loss = -10.0 * math.log10(max(path_transmission, 1e-30))
            state.average_atmospheric_transmission = sum(
                s.atmospheric_transmission for s in state.propagation_slices
            ) / max(len(state.propagation_slices), 1)

        else:

            atmospheric_transmission = max(0.0, min(1.0, 10 ** (-total_loss / 10.0)))
        # ==========================================
        # Save Results
        # ==========================================

        state.atmospheric_loss_dB = total_loss

        state.atmospheric_transmission = atmospheric_transmission

        state.rain_gamma_dB_per_km = rain_loss_per_km
        state.molecular_gamma_dB_per_km = molecular_loss_per_km
        state.aerosol_gamma_dB_per_km = aerosol_loss_per_km
        state.cloud_gamma_dB_per_km = cloud_loss_per_km
        if state.propagation_slices:

            state.visibility_loss_dB = sum(
                s.visibility_loss_dB for s in state.propagation_slices
            )

            state.rain_loss_dB = sum(s.rain_loss_dB for s in state.propagation_slices)

            state.molecular_loss_dB = sum(
                s.molecular_loss_dB for s in state.propagation_slices
            )

            state.aerosol_loss_dB = sum(
                s.aerosol_loss_dB for s in state.propagation_slices
            )

            state.cloud_loss_dB = sum(s.cloud_loss_dB for s in state.propagation_slices)

        else:

            state.visibility_loss_dB = visibility_loss

            state.rain_loss_dB = rain_loss

            state.molecular_loss_dB = molecular_loss

            state.aerosol_loss_dB = aerosol_loss

            state.cloud_loss_dB = cloud_loss

        state.fog_loss_dB = state.visibility_loss_dB

        if state.propagation_slices:

            state.visibility_gamma_dB_per_km = state.visibility_loss_dB / max(
                state.link_distance_km, 1e-9
            )

        else:

            state.visibility_gamma_dB_per_km = gamma

        state.atmosphere_complete = True

        state.debug_message = "Atmospheric attenuation completed"

        # ==========================================
        # Console Output
        # ==========================================
        print()
        print("LAND / SEA EFFECT")
        print("------------------")
        print("Land % =", state.land_percentage)
        print("Sea %  =", state.sea_percentage)

        print()

        print(f"Wavelength: " f"{state.wavelength_nm} nm")

        print(f"Visibility Loss: " f"{state.visibility_loss_dB:.3f} dB")

        print(f"Rain Loss: " f"{state.rain_loss_dB:.3f} dB")

        print(f"Molecular Loss: " f"{state.molecular_loss_dB:.3f} dB")

        print(f"Aerosol Loss: " f"{state.aerosol_loss_dB:.3f} dB")

        print(f"Transmission: " f"{atmospheric_transmission:.6f}")

        # ==========================================
        # VERIFIER TEXT GENERATION
        # ==========================================
        state.verifier_text["atm"] = f"""
Visibility Attenuation ({model})
γ_vis = 3.91 / V * (λ / 550)^(-q)
L_vis = γ_vis * L = {state.visibility_loss_dB:.4f} dB

Rain Attenuation ({rain_model})
L_rain = k * R^α * L = {state.rain_loss_dB:.4f} dB

Cloud Attenuation
L_cloud = {getattr(state, 'cloud_loss_dB', 0.0):.4f} dB

Molecular Attenuation ({molecular_model})
L_mol = γ_mol * L = {state.molecular_loss_dB:.4f} dB

Aerosol Attenuation ({aerosol_model})
L_aer = γ_aer * L = {state.aerosol_loss_dB:.4f} dB

Total Atmospheric Attenuation
α_atm = {state.atmospheric_loss_dB / max(state.link_distance_km, 1e-9):.4f} dB/km

Transmission
T_atm = exp(-α_atm · L / 4.343) = {atmospheric_transmission:.6e}

Total Atmospheric Loss
L_atm = α_atm · L = {state.atmospheric_loss_dB:.4f} dB

Refractivity
N = 77.6/T_K * (P + 4810*e/T_K) = {getattr(state, 'refractivity_N', 0.0):.4f} N

Differential Refraction
Δθ_refract = ∫ (1/n) * (dn/dz) dz = {getattr(state, 'differential_refraction_urad', 0.0):.4f} µrad

Receiver Offset
Δy_rx = ∫ (L-z) * (1/n) * (dn/dz) dz = {getattr(state, 'receiver_plane_offset_mm', 0.0):.4f} mm

FSM Correction Required
FSM_corr = {getattr(state, 'fsm_correction_required_urad', 0.0):.4f} µrad

Duct Height
h_duct = {getattr(state, 'duct_height_m', 0.0):.4f} m

Duct Strength
S_duct = ΔM / Δz = {getattr(state, 'duct_strength', 0.0):.4f}

Dew Point
T_dew = (243.04 * (ln(RH/100) + (17.625*T)/(243.04+T))) / (17.625 - ln(RH/100) - (17.625*T)/(243.04+T)) = {getattr(state, 'dew_point_C', 0.0):.4f} °C

Air Density
ρ_air = P / (R_spec * T_K) = {getattr(state, 'air_density_kg_m3', 0.0):.4f} kg/m³

Water Vapor Density
ρ_water = e / (R_v * T_K) = {getattr(state, 'water_vapor_density_g_m3', 0.0):.4f} g/m³

Surface Refractivity
N_s = N(z=0) = {getattr(state, 'surface_refractivity_N', 0.0):.4f} N

Refractivity Gradient
dN/dh = (N(z2) - N(z1)) / Δz = {getattr(state, 'refractivity_gradient_N_km', 0.0):.4f} N/km

Modified Refractivity
M = N + (h/R_e) * 10⁶ = {getattr(state, 'modified_refractivity_M', 0.0):.4f} M

Land Percentage
%_land = {getattr(state, 'land_percentage', 0.0):.2f} %

Sea Percentage
%_sea = {getattr(state, 'sea_percentage', 0.0):.2f} %

Dominant Surface
Surface = {getattr(state, 'dominant_surface', '')}

Coastal Path
Coastal = {getattr(state, 'coastal_path', '')}
"""

