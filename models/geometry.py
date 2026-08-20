"""
geometry.py

Research Grade Geometry Model
FSO/QKD Maritime Simulator v0.3

Computes

- Beam radius
- Beam diameter
- Capture fraction
- Geometric loss

- Earth curvature drop
- Optical horizon
- Line of Sight (LOS)
- LOS margin

- Fresnel radius
- Fresnel clearance

"""

import math

from core.model import Model


class GeometryModel(Model):

    name = "Geometry"

    description = "Research grade free-space geometry model"

    def _gaussian_beam_radius(self, wavelength_m, waist_radius_m, distance_m):
        """
        Siegman (1986)
        Lasers

        Gaussian beam propagation
        """

        zR = math.pi * waist_radius_m**2 / wavelength_m

        return waist_radius_m * math.sqrt(1.0 + (distance_m / zR) ** 2)

    def _gaussian_receiver_coupling(self, beam_radius, receiver_radius):
        """
        Gaussian encircled energy

        Siegman (1986)
        """

        beam_radius = max(beam_radius, 1e-12)

        return 1.0 - math.exp(-2.0 * receiver_radius**2 / beam_radius**2)

    def _gaussian_beam_theory(self, beam_radius, receiver_radius):
        """
        Gaussian Beam Theory
        """

        beam_radius = max(beam_radius, 1e-12)

        return 1.0 - math.exp(-2.0 * receiver_radius**2 / beam_radius**2)

    def _friis_like_optical_model(
        self, divergence_rad, distance_m, receiver_diameter_m
    ):
        """
        Friis-like Optical Model
        """

        beam_diameter = max(divergence_rad * distance_m, 1e-12)

        return min(1.0, (receiver_diameter_m / beam_diameter) ** 2)

    def _gaussian_coupling_model(self, beam_radius, receiver_radius, pointing_error_m):
        """
        Gaussian Coupling Model with Pointing Error
        Using Farid & Hranilovic (2007) approximation.
        """
        w = max(beam_radius, 1e-12)
        a = receiver_radius
        r = pointing_error_m
        
        v = (math.sqrt(math.pi) * a) / (math.sqrt(2) * w)
        if v < 1e-6:
            A0 = (v * 2.0 / math.sqrt(math.pi))**2
            weq2 = w**2
        else:
            A0 = math.erf(v)**2
            weq2 = w**2 * (math.sqrt(math.pi) * math.erf(v)) / (2.0 * v * math.exp(-v**2))
            
        eta = A0 * math.exp(-2.0 * r**2 / max(weq2, 1e-12))
        return eta

    def execute(self, state):

        # =====================================
        # INPUTS
        # =====================================

        distance_km = getattr(state, "link_distance_km", 10.0)

        # =====================================
        # GPS COORDINATES
        # =====================================

        tx_lat = math.radians(getattr(state, "tx_latitude_deg", 28.6139))

        tx_lon = math.radians(getattr(state, "tx_longitude_deg", 77.2090))

        rx_lat = math.radians(getattr(state, "rx_latitude_deg", 28.7041))

        rx_lon = math.radians(getattr(state, "rx_longitude_deg", 77.1025))

        dlat = rx_lat - tx_lat
        dlon = rx_lon - tx_lon

        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(tx_lat) * math.cos(rx_lat) * math.sin(dlon / 2) ** 2
        )

        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        # =====================================
        # WGS-84 EARTH RADIUS
        # =====================================

        a = 6378137.0  # Equatorial radius (m)
        b = 6356752.314245  # Polar radius (m)

        mean_lat = (tx_lat + rx_lat) / 2.0

        cos_lat = math.cos(mean_lat)
        sin_lat = math.sin(mean_lat)

        num = (a**2 * cos_lat) ** 2 + (b**2 * sin_lat) ** 2
        den = (a * cos_lat) ** 2 + (b * sin_lat) ** 2

        earth_radius_m = math.sqrt(num / den)

        earth_radius_km = earth_radius_m / 1000.0

        gps_distance_km = earth_radius_km * c
        state.gps_distance_km = gps_distance_km

        if getattr(
            state, "mission_mode", "Manual Range"
        ) == "Coordinates" and not getattr(state, "plot_mode", False):

            if gps_distance_km > 0.01:
                distance_km = gps_distance_km

        state.link_distance_km = distance_km

        print()
        print("===== GEOMETRY =====")
        print("Mission Mode :", getattr(state, "mission_mode", None))
        print("Plot Mode    :", getattr(state, "plot_mode", False))
        print("GPS Distance :", gps_distance_km)
        print("Distance In  :", distance_km)
        print("Distance Out :", state.link_distance_km)
        print("====================")
        print()

        # =====================================
        # INITIAL BEARING (TX → RX)
        # =====================================

        y = math.sin(dlon) * math.cos(rx_lat)

        x = math.cos(tx_lat) * math.sin(rx_lat) - math.sin(tx_lat) * math.cos(
            rx_lat
        ) * math.cos(dlon)

        bearing_deg = (math.degrees(math.atan2(y, x)) + 360) % 360
        # =====================================
        # RX POINTING DIRECTION
        # =====================================

        rx_bearing_deg = (bearing_deg + 180.0) % 360

        wavelength_nm = getattr(state, "wavelength_nm", 1550.0)

        tx_aperture_mm = getattr(state, "tx_aperture_mm", 50.0)

        rx_aperture_mm = getattr(state, "rx_aperture_mm", 100.0)

        divergence_mrad = getattr(state, "tx_beam_divergence_mrad", 0.3)

        tx_height_msl_m = getattr(state, "tx_height_msl_m", 10.0)

        rx_height_msl_m = getattr(state, "rx_height_msl_m", 15.0)
        minimum_height_above_sea_m = getattr(state, "minimum_height_above_sea_m", 5.0)

        solve_for = getattr(state, "solve_for", "Minimum Height Above Sea")

        earth_radius_factor = getattr(state, "effective_earth_radius_factor", 1.333)
        geometric_loss_model = getattr(
            state, "geometric_loss_model", "Gaussian Beam Theory"
        )
        print("Geometry receives:", state.geometric_loss_model)
        print()
        print("===================================")
        print("Selected Geometric Model =", geometric_loss_model)
        print("===================================")
        print()

        # =====================================
        # UNIT CONVERSIONS
        # =====================================

        distance_m = distance_km * 1000
        earth_radius_m *= earth_radius_factor
        # =====================================
        # Elevation Angle
        # =====================================

        # =====================================
        # Elevation Angle (Earth Curvature Corrected)
        # =====================================

        # Earth curvature drop
        earth_curvature_drop_m = distance_m**2 / (2 * earth_radius_m)
        # =====================================
        # Solve TX Height (Input)
        # =====================================

        height_difference = rx_height_msl_m - tx_height_msl_m

        # Effective height difference
        effective_height_difference = height_difference - earth_curvature_drop_m

        # TX elevation
        elevation_angle_rad = math.atan2(effective_height_difference, distance_m)

        elevation_angle_deg = math.degrees(elevation_angle_rad)

        # RX points back to TX
        rx_elevation_deg = -elevation_angle_deg

        # True slant range
        slant_range_m = math.sqrt(distance_m**2 + effective_height_difference**2)

        wavelength_m = wavelength_nm * 1e-9

        tx_aperture_m = tx_aperture_mm * 1e-3

        rx_aperture_m = rx_aperture_mm * 1e-3

        # =====================================
        # BEAM PROPAGATION
        # =====================================

        beam_waist_radius_m = getattr(
            state, "beam_waist_radius_m", 0.90 * tx_aperture_m / 2
        )

        initial_beam_radius = beam_waist_radius_m

        beam_radius = self._gaussian_beam_radius(
            wavelength_m, initial_beam_radius, distance_m
        )

        beam_diameter = 2 * beam_radius

        # =====================================
        # RECEIVER COUPLING
        # =====================================

        rx_radius = rx_aperture_m / 2

        divergence_rad = divergence_mrad * 1e-3

        pointing_error_m = getattr(state, "pointing_error_m", 0.0)

        if geometric_loss_model == "Gaussian Beam Theory":

            capture_fraction = self._gaussian_beam_theory(beam_radius, rx_radius)

        elif geometric_loss_model == "Friis-like Optical Model":

            capture_fraction = self._friis_like_optical_model(
                divergence_rad, distance_m, rx_aperture_m
            )

        elif geometric_loss_model == "Gaussian Coupling Model":

            capture_fraction = self._gaussian_coupling_model(
                beam_radius, rx_radius, pointing_error_m
            )

        else:

            capture_fraction = self._gaussian_beam_theory(beam_radius, rx_radius)

        capture_fraction = max(1e-12, min(capture_fraction, 1.0))

        # =====================================
        # GEOMETRIC LOSS
        # =====================================

        geometric_loss_db = -10 * math.log10(capture_fraction)
        print("Beam Radius =", beam_radius)
        print("RX Radius   =", rx_radius)
        print("Capture     =", capture_fraction)
        print("Loss dB     =", geometric_loss_db)

        # =====================================
        # EARTH CURVATURE
        # =====================================

        # =====================================
        # OPTICAL HORIZON
        # =====================================

        # =====================================
        # OPTICAL HORIZON
        # =====================================

        optical_horizon_m = math.sqrt(2 * earth_radius_m * tx_height_msl_m) + math.sqrt(
            2 * earth_radius_m * rx_height_msl_m
        )
        optical_horizon_km = optical_horizon_m / 1000.0

        # =====================================
        # LOS
        # =====================================

        los = distance_km <= optical_horizon_km

        los_margin_m = optical_horizon_m - distance_m

        # =====================================
        # FRESNEL RADIUS
        # =====================================

        d1 = distance_m / 2

        d2 = distance_m / 2

        # Fresnel radius at midpoint for reference
        fresnel_radius_m = math.sqrt(wavelength_m * d1 * d2 / (d1 + d2))

        # =====================================
        # WRITE TO STATE
        # =====================================

        state.distance_m = distance_m
        print("GEOMETRY distance_m =", state.distance_m)
        state.bearing_deg = bearing_deg

        state.tx_azimuth_deg = bearing_deg

        state.tx_elevation_deg = elevation_angle_deg

        state.rx_azimuth_deg = rx_bearing_deg

        state.rx_elevation_deg = rx_elevation_deg

        state.wavelength_m = wavelength_m

        state.tx_aperture_m = tx_aperture_m

        state.rx_aperture_m = rx_aperture_m
        state.tx_fov_mrad = divergence_mrad

        state.beam_radius_m = beam_radius

        state.beam_diameter_m = beam_diameter

        # ==========================================
        # v0.4 Slice Geometric Loss
        # ==========================================

        state.capture_fraction = capture_fraction
        state.effective_earth_radius_m = earth_radius_m

        state.geometric_loss_dB = geometric_loss_db

        state.earth_curvature_drop_m = earth_curvature_drop_m

        state.optical_horizon_km = optical_horizon_km
        state.beam_elevation_angle_deg = elevation_angle_deg
        state.slant_range_m = slant_range_m

        state.height_difference_m = height_difference
        # =====================================
        # PROPAGATION TYPE
        # =====================================

        # =====================================
        # PROPAGATION INFORMATION
        # =====================================

        state.propagation_type = "Slant"

        tx = getattr(state, "tx_surface_type", "Unknown")
        rx = getattr(state, "rx_surface_type", "Unknown")
        print("Geometry sees:")
        print("TX =", repr(tx))
        print("RX =", repr(rx))

        if tx == "Land" and rx == "Sea":
            state.propagation_direction = "Shore → Sea"

        elif tx == "Sea" and rx == "Land":
            state.propagation_direction = "Sea → Shore"

        elif tx == "Sea" and rx == "Sea":
            state.propagation_direction = "Sea → Sea"

        elif tx == "Land" and rx == "Land":
            state.propagation_direction = "Land → Land"

        else:
            state.propagation_direction = f"{tx} → {rx}"
        print("Propagation Direction SET =", repr(state.propagation_direction))
        state.effective_height_difference_m = effective_height_difference
        print("Height Difference =", height_difference)
        print("Curvature Drop =", earth_curvature_drop_m)
        print("Effective Height Difference =", effective_height_difference)
        print("TX Elevation =", elevation_angle_deg)
        print("RX Elevation =", rx_elevation_deg)

        print()
        print("GEOMETRY DEBUG")
        print("----------------")
        print("distance_km =", distance_km)
        print("bearing_deg =", bearing_deg)
        print("tx_height =", tx_height_msl_m)
        print("Solve For =", solve_for)
        print("Minimum Height Target =", minimum_height_above_sea_m)
        print("rx_height =", rx_height_msl_m)
        print("earth_radius_factor =", earth_radius_factor)
        print("optical_horizon_km =", optical_horizon_km)
        state.los = los

        print("los =", state.los)
        if not los:

            state.warning_message = "Receiver out of sight due to Earth curvature."

        else:

            state.warning_message = ""

        state.los_margin_m = los_margin_m

        state.fresnel_radius_m = fresnel_radius_m

        # ==========================================
        # CLEAR GEOMETRY PROFILES
        # ==========================================

        state.path_distance_profile.clear()
        state.beam_height_profile.clear()
        state.curvature_profile.clear()
        print()
        print("GEOMETRY SEES", len(state.propagation_slices), "SLICES")
        print()
        print()
        print("Geometry slice count =", len(state.propagation_slices))
        print()

        # ==========================================
        # v0.4 PROPAGATION SLICE GEOMETRY
        # ==========================================
        minimum_clearance = float("inf")

        if state.propagation_slices:

            tx_lat = state.tx_latitude_deg
            tx_lon = state.tx_longitude_deg

            rx_lat = state.rx_latitude_deg
            rx_lon = state.rx_longitude_deg

            for s in state.propagation_slices:

                # Distance from transmitter
                local_distance = s.center_m
                # Fraction of total path
                path_fraction = local_distance / max(distance_m, 1.0)

                s.latitude_deg = tx_lat + path_fraction * (rx_lat - tx_lat)

                s.longitude_deg = tx_lon + path_fraction * (rx_lon - tx_lon)

                s.ground_distance_m = local_distance
                s.start_distance_m = s.start_m
                s.center_distance_m = s.center_m
                s.end_distance_m = s.end_m
                state.path_distance_profile.append(local_distance)
                s.path_fraction = path_fraction

                beam_height = s.beam_height_m

                s.line_of_sight_height_m = beam_height
                state.beam_height_profile.append(beam_height)

                # Earth curvature at this slice
                state.curvature_profile.append(s.earth_curvature_drop_m)
                # Ground height (flat terrain for v0.4)

                # Beam clearance above ground
                s.beam_above_ground_m = beam_height - s.ground_height_m
                minimum_clearance = min(minimum_clearance, s.beam_above_ground_m)

                # Local elevation angle
                slice_angle = math.degrees(
                    math.atan2(beam_height - tx_height_msl_m, max(local_distance, 1e-9))
                )

                s.elevation_angle_deg = slice_angle
                # Slant distance to this slice
                s.slant_distance_m = math.sqrt(
                    local_distance**2 + (beam_height - tx_height_msl_m) ** 2
                )
                # LOS clearance
                s.clearance_above_ground_m = s.beam_above_ground_m
                # Line of sight flag
                s.los = s.beam_above_ground_m > 0
                # Local optical horizon
                s.local_horizon_m = math.sqrt(
                    2.0 * earth_radius_m * max(beam_height, 0.0)
                )

                # Beam radius at this slice
                local_beam_radius = self._gaussian_beam_radius(
                    wavelength_m, initial_beam_radius, local_distance
                )
                beam_spread_factor = getattr(s, "beam_spread_factor", 1.0)

                local_beam_radius *= beam_spread_factor

                local_beam_diameter = 2.0 * local_beam_radius

                # Receiver overlap (Gaussian approximation)
                if local_beam_radius > 0:

                    if geometric_loss_model == "Gaussian Beam Theory":

                        local_capture = self._gaussian_beam_theory(
                            local_beam_radius, rx_radius
                        )

                    elif geometric_loss_model == "Friis-like Optical Model":

                        local_capture = self._friis_like_optical_model(
                            divergence_rad, local_distance, rx_aperture_m
                        )

                    elif geometric_loss_model == "Gaussian Coupling Model":

                        local_capture = self._gaussian_coupling_model(
                            local_beam_radius, rx_radius, pointing_error_m
                        )

                    else:

                        local_capture = self._gaussian_beam_theory(
                            local_beam_radius, rx_radius
                        )

                else:

                    local_capture = 1.0

                local_capture = max(1e-12, min(local_capture, 1.0))

                # Fresnel radius at slice
                d1 = local_distance
                d2 = max(distance_m - local_distance, 1.0)

                local_fresnel = math.sqrt(wavelength_m * d1 * d2 / (d1 + d2))

                s.beam_radius_m = local_beam_radius
                print(s.slice_id, s.center_m, local_beam_radius)
                s.beam_diameter_m = local_beam_diameter
                s.capture_fraction = local_capture
                print(f"Slice {s.slice_id} Capture = {s.capture_fraction}")
                s.geometric_loss_dB = -10.0 * math.log10(local_capture)

                # Geometry is not a propagation loss

                s.distance_from_tx_m = local_distance
                s.fresnel_radius_m = local_fresnel
                s.beam_center_x_m = local_distance
                s.beam_center_y_m = beam_height

                # Earth curvature drop up to this slice
                local_earth_drop = (local_distance**2) / (2.0 * earth_radius_m)

                s.earth_curvature_drop_m = local_earth_drop
                s.path_length_m = s.slant_distance_m
                s.notes = (
                    f"Beam={local_beam_diameter:.3f} m, " f"Capture={local_capture:.4f}"
                )

            state.receiver_capture_fraction = state.propagation_slices[
                -1
            ].capture_fraction
            if solve_for == "Minimum Height Above Sea":

                state.minimum_height_above_sea_m = minimum_clearance

                print("Minimum Height Above Sea =", minimum_clearance)

        # ==========================================
        # ADDITIONAL STATE VARIABLES FOR OUTPUT/VERIFIER
        # ==========================================
        tx_fov = getattr(state, "tx_beam_divergence_mrad", 0.0)
        rx_fov = getattr(state, "rx_fov_mrad", 0.0)
        
        state.tx_half_fov_mrad = tx_fov / 2.0
        state.rx_half_fov_mrad = rx_fov / 2.0
        
        # Solid angle in steradians
        state.receiver_solid_angle_sr = 2 * math.pi * (1 - math.cos(rx_fov * 1e-3 / 2))
        
        state.fresnel_radius_m = fresnel_radius_m
        
        # ==========================================
        # VERIFIER TEXT GENERATION
        # ==========================================
        capture_eq = ""
        if geometric_loss_model == "Gaussian Beam Theory" or geometric_loss_model not in ["Friis-like Optical Model", "Gaussian Coupling Model"]:
            capture_eq = f"η = 1 - exp(-2 · (R_rx / r_beam)²) = 1 - exp(-2 · ({rx_radius:.4f}/{beam_radius:.4f})²) = {capture_fraction:.6e}"
        elif geometric_loss_model == "Friis-like Optical Model":
            beam_diameter_friis = max(divergence_rad * distance_m, 1e-12)
            capture_eq = f"η = min(1.0, (D_rx / D_beam)²) = min(1.0, ({rx_aperture_m:.4f}/{beam_diameter_friis:.4f})²) = {capture_fraction:.6e}"
        elif geometric_loss_model == "Gaussian Coupling Model":
            v = (math.sqrt(math.pi) * rx_radius) / (math.sqrt(2) * max(beam_radius, 1e-12))
            if v < 1e-6:
                A0 = (v * 2.0 / math.sqrt(math.pi))**2
                weq2 = beam_radius**2
            else:
                A0 = math.erf(v)**2
                weq2 = beam_radius**2 * (math.sqrt(math.pi) * math.erf(v)) / (2.0 * v * math.exp(-v**2))
            capture_eq = f"""v = (√π · R_rx) / (√2 · r_beam) = {v:.6e}
A₀ = erf(v)² = {A0:.6f}
w_eq² = {weq2:.6e}
η = A₀ · exp(-2 · Error_pointing² / w_eq²) = {capture_fraction:.6e}"""

        state.verifier_text["geo"] = f"""
**Range**
L_ground = {distance_km:.4f} km

**TX Height**
h_TX = {getattr(state, 'tx_height_msl_m', 0.0):.2f} m

**RX Height**
h_RX = {getattr(state, 'rx_height_msl_m', 0.0):.2f} m

**TX Azimuth**
θ_TX_az = atan2(sin(Δλ)·cos(φ₂), cos(φ₁)·sin(φ₂) - sin(φ₁)·cos(φ₂)·cos(Δλ)) = {getattr(state, 'bearing_deg', 0.0):.4f} deg

**RX Azimuth**
θ_RX_az = (θ_TX_az + 180) % 360 = {getattr(state, 'rx_azimuth_deg', 0.0):.4f} deg

**TX Elevation**
θ_TX_el = atan(Δh_effective / L_ground) = {getattr(state, 'beam_elevation_angle_deg', 0.0):.4f} deg

**RX Elevation**
θ_RX_el = -θ_TX_el = {getattr(state, 'rx_elevation_deg', 0.0):.4f} deg

**TX FOV**
θ_TX_FOV = {getattr(state, 'tx_beam_divergence_mrad', 0.0):.4f} mrad

**RX FOV**
θ_RX_FOV = {getattr(state, 'rx_fov_mrad', 0.0):.4f} mrad

**TX Half FOV**
θ_TX_halfFOV = θ_TX_FOV / 2 = {getattr(state, 'tx_half_fov_mrad', 0.0):.4f} mrad

**RX Half FOV**
θ_RX_halfFOV = θ_RX_FOV / 2 = {getattr(state, 'rx_half_fov_mrad', 0.0):.4f} mrad

**Receiver Solid Angle**
Ω_RX = 2π(1 - cos(θ_RX_FOV / 2)) = {getattr(state, 'receiver_solid_angle_sr', 0.0):.4e} sr

**Min height**
h_sea = {getattr(state, "minimum_height_above_sea_m", 0.0):.4f} m

**Beam Radius**
r_beam = w_0 · √(1 + (L_ground / z_R)²) = {beam_radius:.6f} m

**Beam Diameter**
D_beam = 2 · r_beam = {beam_diameter:.6f} m

**Capture Fraction**
{capture_eq}

**Geometric Loss**
L_geo = -10 · log₁₀(η) = {geometric_loss_db:.4f} dB

**LOS**
LOS = L_ground ≤ d_horizon = {los}

**LOS Margin**
d_margin = d_horizon - L_ground = {getattr(state, 'los_margin_m', 0.0):.4f} m

**Optical Horizon**
d_horizon = √(2 · R_e · h_TX) + √(2 · R_e · h_RX) = {optical_horizon_km:.4f} km

**Curvature Drop**
Δh_curvature = (L_ground)² / (2 · R_e) = {earth_curvature_drop_m:.4f} m

**Slant Range**
d_slant = √((L_ground)² + (Δh_effective)²) = {slant_range_m:.4f} m

**Height Difference**
Δh_effective = h_RX - h_TX - Δh_curvature = {height_difference:.4f} - {earth_curvature_drop_m:.4f} = {effective_height_difference:.4f} m

**Fresnel Radius**
r_F = √(λ · d₁ · d₂ / (d₁ + d₂)) = √( {wavelength_m:.2e} · {distance_m/2:.2f} · {distance_m/2:.2f} / {distance_m:.2f} ) = {fresnel_radius_m:.6f} m

**Propagation Type**
Type = {getattr(state, 'propagation_type', '')}

**Propagation Direction**
Dir = {getattr(state, 'propagation_direction', '')}

**Effective Earth Radius**
R_e_eff = R_e · factor = {earth_radius_m:.2f} m

*Additional Formulae:*
h_LOS_i = h_TX + d_i · tan(θ_TX_el)
h_terrain_i = h_ground_i + h_veg + R_z
"""
