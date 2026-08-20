"""
background_radiance.py

Background Radiance Model

Computes:

    Sky Radiance

    Solar Background

    Lunar Background

    Background Photon Flux

    Detector Background Count Rate

Version:
    0.3
"""

import math

from core.model import Model


class BackgroundRadianceModel(Model):

    name = "BackgroundRadiance"

    description = "Solar and lunar background model"

    version = "0.3"

    inputs = [
        "solar_elevation_deg",
        "solar_flux_W_m2",
        "is_daylight",
        "rx_fov_mrad",
        "source_bandwidth_nm",
        "rx_filter_bandwidth_nm",
        "rx_filter_center_wavelength_nm",
        "rx_aperture_mm",
        "wavelength_nm",
        "detector_efficiency",
        "moon_phase_percent",
        "solar_azimuth_deg",
        "bearing_deg",
        "visibility_km",
        "cloud_cover_percent",
    ]

    outputs = [
        "solar_separation_deg",
        "receiver_solid_angle_sr",
        "solar_background_W",
        "moon_background_W",
        "sky_radiance_W_sr_m2",
        "background_power_W",
        "filter_overlap_fraction",
        "filtered_background_fraction",
        "background_photon_rate",
        "background_count_rate",
        "tx_overlap_fraction",
        "solar_overlap_fraction",
        "combined_solar_overlap",
        "sun_inside_tx_beam",
        "sun_inside_rx_fov",
        "solar_tx_separation_deg",
        "solar_rx_separation_deg",
    ]
    PLANCK = 6.62607015e-34

    LIGHT_SPEED = 2.99792458e8
    # -----------------------------------------
    # Solar Geometry
    # -----------------------------------------

    SUN_ANGULAR_DIAMETER_DEG = 0.53

    SUN_ANGULAR_RADIUS_DEG = SUN_ANGULAR_DIAMETER_DEG / 2.0

    # --------------------------------------------------
    # Validation
    # --------------------------------------------------

    def validate(self, state):

        if not state.propagation_slices:
            raise ValueError("SkyRadiance must run before BackgroundRadiance.")

        if state.rx_fov_mrad <= 0:
            raise ValueError("Receiver FOV invalid")

        if state.rx_filter_bandwidth_nm <= 0:
            raise ValueError("RX filter bandwidth invalid")

        if state.source_bandwidth_nm <= 0:
            raise ValueError("Source bandwidth invalid")

        vis_tx = getattr(state, "tx_visibility_km", getattr(state, "visibility_km", 10.0))
        if vis_tx <= 0:
            raise ValueError("Visibility must be positive")

        return True

    # --------------------------------------------------
    # Photon Energy
    # --------------------------------------------------

    def photon_energy(self, wavelength_nm):

        wavelength_m = wavelength_nm * 1e-9

        return self.PLANCK * self.LIGHT_SPEED / wavelength_m

    # --------------------------------------------------
    # Execute
    # --------------------------------------------------

    def execute(self, state):

        solar_elevation = getattr(state, "solar_elevation_deg", 0.0)

        solar_azimuth = getattr(state, "solar_azimuth_deg", 0.0)

        tx_azimuth = getattr(
            state, "tx_azimuth_deg", getattr(state, "bearing_deg", 0.0)
        )

        tx_elevation = getattr(
            state, "tx_elevation_deg", getattr(state, "beam_elevation_angle_deg", 0.0)
        )
        rx_azimuth = getattr(state, "rx_azimuth_deg", (tx_azimuth + 180.0) % 360.0)

        rx_elevation = getattr(state, "rx_elevation_deg", -tx_elevation)

        print("\nSUN DEBUG")
        print("Solar Azimuth =", solar_azimuth)
        print("Solar Elevation =", solar_elevation)
        print("TX Azimuth =", tx_azimuth)
        print("TX Elevation =", tx_elevation)
        print("RX Azimuth =", rx_azimuth)
        print("RX Elevation =", rx_elevation)

        sun_az = math.radians(solar_azimuth)
        sun_el = math.radians(solar_elevation)

        tx_az = math.radians(tx_azimuth)
        tx_el = math.radians(tx_elevation)
        rx_az = math.radians(rx_azimuth)
        rx_el = math.radians(rx_elevation)

        # ==========================================
        # Sun -> TX Separation
        # ==========================================

        cos_sep_tx = math.sin(sun_el) * math.sin(tx_el) + math.cos(sun_el) * math.cos(
            tx_el
        ) * math.cos(sun_az - tx_az)

        cos_sep_tx = max(-1.0, min(1.0, cos_sep_tx))

        solar_tx_separation_deg = math.degrees(math.acos(cos_sep_tx))

        # ==========================================
        # Sun -> RX Separation
        # ==========================================

        cos_sep_rx = math.sin(sun_el) * math.sin(rx_el) + math.cos(sun_el) * math.cos(
            rx_el
        ) * math.cos(sun_az - rx_az)

        cos_sep_rx = max(-1.0, min(1.0, cos_sep_rx))

        solar_rx_separation_deg = math.degrees(math.acos(cos_sep_rx))

        state.solar_tx_separation_deg = solar_tx_separation_deg
        state.solar_rx_separation_deg = solar_rx_separation_deg

        # Keep this for compatibility with the rest of the simulator
        state.solar_separation_deg = solar_rx_separation_deg
        solar_separation_deg = solar_rx_separation_deg
        # ==========================================
        # Receiver Half FOV
        # ==========================================

        rx_half_fov_deg = state.rx_fov_mrad * 1e-3 * 180.0 / math.pi

        # ---------------------------------
        # TX beam half-angle
        # ---------------------------------

        # ---------------------------------
        # TX beam overlap
        # ---------------------------------
        tx_half_fov_deg = state.tx_fov_mrad * 1e-3 * 180.0 / math.pi

        state.tx_half_fov_mrad = state.tx_fov_mrad / 2.0

        sun_radius_deg = self.SUN_ANGULAR_RADIUS_DEG

        if solar_tx_separation_deg >= (tx_half_fov_deg + sun_radius_deg):

            tx_overlap = 0.0

        elif solar_tx_separation_deg <= abs(tx_half_fov_deg - sun_radius_deg):

            tx_overlap = 1.0

        else:

            tx_overlap = (
                (tx_half_fov_deg + sun_radius_deg) - solar_tx_separation_deg
            ) / (2.0 * sun_radius_deg)

        tx_overlap = max(0.0, min(1.0, tx_overlap))

        state.tx_overlap_fraction = tx_overlap

        state.sun_inside_tx_beam = tx_overlap > 0.0

        state.rx_half_fov_mrad = state.rx_fov_mrad / 2.0
        state.sun_radius_deg = self.SUN_ANGULAR_RADIUS_DEG
        # ==========================================
        # Sun inside Receiver FOV?
        # ==========================================

        sun_inside_rx_fov = solar_rx_separation_deg <= rx_half_fov_deg

        state.sun_inside_rx_fov = sun_inside_rx_fov
        # ==========================================
        # Solar Disc Overlap with RX FOV
        # ==========================================

        sun_radius_deg = self.SUN_ANGULAR_RADIUS_DEG

        if solar_rx_separation_deg >= (rx_half_fov_deg + sun_radius_deg):

            overlap_fraction = 0.0

        elif solar_rx_separation_deg <= abs(rx_half_fov_deg - sun_radius_deg):

            overlap_fraction = 1.0

        else:

            overlap_fraction = (
                (rx_half_fov_deg + sun_radius_deg) - solar_rx_separation_deg
            ) / (2.0 * sun_radius_deg)
        overlap_fraction = max(0.0, min(1.0, overlap_fraction))

        wavelength_nm = state.wavelength_nm

        rx_diameter_m = state.rx_aperture_mm / 1000.0

        rx_area = math.pi * (rx_diameter_m / 2.0) ** 2

        rx_fov_rad = state.rx_fov_mrad * 1e-3

        half_angle = rx_fov_rad / 2.0

        receiver_solid_angle_sr = 2.0 * math.pi * (1.0 - math.cos(half_angle))

        state.receiver_solid_angle_sr = receiver_solid_angle_sr
        solid_angle = receiver_solid_angle_sr

        filter_bw_nm = state.rx_filter_bandwidth_nm
        print("\nFILTER DEBUG")
        print("Source BW =", state.source_bandwidth_nm)
        print("RX Filter BW =", state.rx_filter_bandwidth_nm)
        print("RX Center =", state.rx_filter_center_wavelength_nm)

        # ==========================================
        # Spectral Filter Overlap
        # ==========================================

        source_bw = max(state.source_bandwidth_nm, 1e-12)

        rx_bw = max(state.rx_filter_bandwidth_nm, 1e-12)

        tx_center = state.wavelength_nm

        rx_center = state.rx_filter_center_wavelength_nm

        center_offset = abs(tx_center - rx_center)

        spectral_overlap = min(1.0, rx_bw / source_bw)
        center_factor = 1.0 - center_offset / ((source_bw + rx_bw) / 2.0)

        center_factor = max(0.0, min(1.0, center_factor))

        overlap = spectral_overlap * center_factor

        state.filter_overlap_fraction = overlap
        state.filtered_background_fraction = overlap
        # ==========================================
        # Use SkyRadianceModel output
        # ==========================================

        sky_radiance = getattr(state, "clear_sky_radiance_W_sr_m2", 0.0)

        solar_background = getattr(state, "solar_background_W_sr_m2", 0.0)

        moon_background = getattr(state, "moon_background_W_sr_m2", 0.0)

        sky_background = getattr(state, "sky_background_W_sr_m2", 0.0)
        print()
        print("BACKGROUND INPUTS")
        print("-----------------")
        print("Sky Radiance =", sky_radiance)
        print("Solar Background =", solar_background)
        print("Moon Background =", moon_background)
        print("Sky Background =", sky_background)

        if solar_rx_separation_deg <= rx_half_fov_deg:

            angle_factor = 1.0

        else:

            angle_factor = 0.02
        combined_overlap = tx_overlap * overlap_fraction

        # ==========================================
        # Optical Power
        # ==========================================
        print()
        print("BACKGROUND DEBUG")
        print("----------------")
        print("rx_area =", rx_area)
        print("solid_angle =", solid_angle)
        print("filter_bw_nm =", filter_bw_nm)
        print("source_bw =", source_bw)
        print("rx_filter_bw =", rx_bw)
        print("center_offset =", center_offset)
        print("filter_overlap =", overlap)
        print("sky_radiance =", sky_radiance)
        print("solar_tx_separation =", state.solar_tx_separation_deg)
        print("solar_rx_separation =", state.solar_rx_separation_deg)
        print("overlap_fraction =", overlap_fraction)
        print("tx_overlap =", tx_overlap)
        print("combined_overlap =", combined_overlap)
        print("sun_inside_tx =", state.sun_inside_tx_beam)

        print("sun_inside_rx =", state.sun_inside_rx_fov)
        print("angle_factor =", angle_factor)

        background_power = sky_radiance * rx_area * solid_angle * overlap * angle_factor
        # ==========================================
        # Photon Rate
        # ==========================================

        photon_energy = self.photon_energy(wavelength_nm)

        photon_rate = background_power / max(photon_energy, 1e-30)

        # ==========================================
        # Detector Counts
        # ==========================================

        background_counts = photon_rate * state.detector_efficiency
        print()
        print("BACKGROUND CHECK")
        print("----------------")
        print("Sky Radiance =", sky_radiance)
        print("Receiver Area =", rx_area)
        print("Solid Angle =", solid_angle)
        print("Filter Overlap =", overlap)
        print("Background Power =", background_power)
        print("Photon Energy =", photon_energy)
        print("Photon Rate =", photon_rate)
        print("Background Counts =", background_counts)
        # ==========================================
        # v0.4 Adaptive Slice Background
        # ==========================================

        if state.propagation_slices:

            total_background_power = 0.0
            total_background_photons = 0.0
            total_background_counts = 0.0
            running_background = 0.0

            for s in state.propagation_slices:

                slice_radiance = getattr(s, "clear_sky_radiance_W_sr_m2", sky_radiance)
                # -------------------------------------
                # Land / Sea Background
                # -------------------------------------

                if s.surface_type == "Sea":

                    surface_background = 1.20

                else:

                    surface_background = 0.80

                slice_radiance *= surface_background

                s.surface_background_factor = surface_background

                s.sky_radiance_W_sr_m2 = slice_radiance
                s.solar_background_W_sr_m2 = solar_background
                s.moon_background_W_sr_m2 = moon_background
                s.sky_background_W_sr_m2 = sky_background

                slice_transmission = getattr(
                    s,
                    "cumulative_atmospheric_transmission",
                    state.atmospheric_transmission,
                )
                s.background_transmission = slice_transmission

                slice_fraction = s.length_m / state.distance_m

                s.background_power_W = (
                    slice_radiance
                    * rx_area
                    * solid_angle
                    * overlap
                    * angle_factor
                    * slice_fraction
                )
                s.background_photon_rate = s.background_power_W / photon_energy

                local_background = s.background_photon_rate * state.detector_efficiency

                running_background += local_background

                s.background_count_rate = local_background

                s.cumulative_background_count_rate = running_background
                s.background_radiance_W_sr_m2 = slice_radiance
                s.filter_overlap_fraction = overlap
                s.solar_overlap_fraction = overlap_fraction
                s.tx_overlap_fraction = tx_overlap
                s.combined_solar_overlap = combined_overlap
                s.receiver_solid_angle_sr = solid_angle

                s.notes = f"Background={s.background_count_rate:.2e} cps"

                total_background_power += s.background_power_W
                s.cumulative_background_power_W = total_background_power
                total_background_photons += s.background_photon_rate
                s.cumulative_background_photon_rate = total_background_photons
                if state.is_daylight:

                    s.background_source = "Solar"

                elif state.moon_phase_percent > 20:

                    s.background_source = "Moon"

                else:

                    s.background_source = "Dark Sky"
                # Store slice values only

            # Do NOT accumulate

            background_power = total_background_power
            photon_rate = total_background_photons
            background_counts = running_background
            state.average_background_power_W = sum(
                s.background_power_W for s in state.propagation_slices
            ) / max(len(state.propagation_slices), 1)

            state.average_background_photon_rate = sum(
                s.background_photon_rate for s in state.propagation_slices
            ) / max(len(state.propagation_slices), 1)

            state.average_background_count_rate = sum(
                s.background_count_rate for s in state.propagation_slices
            ) / max(len(state.propagation_slices), 1)

            print()
            print("===== BACKGROUND → SLICES =====")
            print("Slices Updated :", len(state.propagation_slices))
            print("===============================")
            print()

        # ==========================================
        # Solar Angle Factor (Scattering Phase Function)
        # ==========================================
        # Rayleigh scattering phase function P(θ) = (3/4) * (1 + cos²(θ))
        # This describes the angular distribution of scattered sunlight
        theta_rad = math.radians(solar_rx_separation_deg)
        rayleigh_phase = 0.75 * (1.0 + math.cos(theta_rad)**2)
        
        # Henyey-Greenstein for aerosols (g ≈ 0.8 forward scattering)
        g = 0.8
        hg_phase = (1 - g**2) / (1 + g**2 - 2*g*math.cos(theta_rad))**1.5
        
        # Combined scattering factor (weighted 30% Rayleigh, 70% Aerosol)
        angle_factor = 0.3 * rayleigh_phase + 0.7 * hg_phase

        # ==========================================
        # Save Results
        # ==========================================

        state.solar_background_W = solar_background
        state.moon_background_W = moon_background
        state.solar_angle_factor = angle_factor
        state.sky_radiance_W_sr_m2 = getattr(
            state, "clear_sky_radiance_W_sr_m2", sky_radiance
        )
        state.sky_background_W = sky_background
        state.natural_sky_background_W = sky_background
        state.background_power_W = background_power
        state.background_photon_rate = photon_rate

        state.solar_angle_factor = angle_factor
        state.solar_overlap_fraction = overlap_fraction
        state.tx_overlap_fraction = tx_overlap
        state.combined_solar_overlap = combined_overlap

        state.background_count_rate = background_counts

        state.debug_message = "Background radiance completed"

        # ==========================================
        # Console Output
        # ==========================================

        print()

        print(f"Sky Radiance: " f"{sky_radiance:.3e} " f"W/sr/m²")

        print(f"Background Power: " f"{background_power:.3e} W")

        print(f"Background Photon Rate: " f"{photon_rate:.3e} cps")

        print(f"Background Count Rate: " f"{background_counts:.3e} cps")

        if "solar" not in state.verifier_text:
            state.verifier_text["solar"] = ""
            
        state.verifier_text["solar"] += f"""
**Sky Radiance (L_sky)**
L_sky = L_solar + L_moon + L_sky_natural = {solar_background:.4e} + {moon_background:.4e} + {sky_background:.4e} = {sky_radiance:.4e} W/sr/m²

**Solar Background**
L_solar = Flux_solar · 5e-9 · Temp_Factor = {solar_background:.4e} W/sr/m²

**Moon Background**
L_moon = 5e-8 · Phase = 5e-8 · {getattr(state, 'moon_phase_percent', 0.0)/100:.2f} = {moon_background:.4e} W/sr/m²

**Sky Background**
L_sky_natural = 1e-8 = {sky_background:.4e} W/sr/m²

**Solar Separation**
θ_sep = {getattr(state, 'solar_separation_deg', 0.0):.4f} deg

**Solar TX Separation**
θ_sep_tx = {getattr(state, 'solar_tx_separation_deg', 0.0):.4f} deg

**Solar RX Separation**
θ_sep_rx = {getattr(state, 'solar_rx_separation_deg', 0.0):.4f} deg

**Sun Inside RX FOV**
Sun_in_RX = (θ_sep_rx ≤ θ_RX_FOV/2) = {getattr(state, 'sun_inside_rx_fov', False)}

**Sun Inside TX Beam**
Sun_in_TX = (θ_sep_tx ≤ θ_TX_FOV/2) = {getattr(state, 'sun_inside_tx_beam', False)}

**Solar Overlap**
f_overlap = Area_sun_overlap / Area_FOV = {getattr(state, 'solar_overlap_fraction', 0.0):.4e}

**Solar Angle Factor (Scattering Phase Function)**
P_Rayleigh = 0.75 · (1 + cos²(θ_sep_rx))
P_Aerosol = (1 - g²) / (1 + g² - 2g·cos(θ_sep_rx))^1.5  (g=0.8)
f_angle = 0.3 · P_Rayleigh + 0.7 · P_Aerosol = {angle_factor:.4e}

**Filter Overlap**
f_filter = min(1, Δλ_rx / Δλ_tx) · f_center = {getattr(state, 'filter_overlap_fraction', 0.0):.4e}

**Filtered Background Radiance**
L_filtered = L_sky · f_filter = {sky_radiance * overlap:.4e} W/sr/m²

**Background Power**
P_bg = L_filtered · Ω_RX · A_RX · f_angle = {background_power:.4e} W

**Background Photon Rate**
R_bg_photon = P_bg / (h · ν) = {photon_rate:.4e} photons/s
"""
