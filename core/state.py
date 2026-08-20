"""
state.py (v0.3 CLEAN FIXED)

Single source of truth for all simulation data.
No duplicates. No overrides. Fully stable.
"""

from dataclasses import dataclass, field
from typing import List, Dict

# ============================================================
# MAIN STATE CLASS
# ============================================================


@dataclass
class PropagationSlice:

    slice_id: int = 0
    start_m: float = 0.0
    end_m: float = 0.0
    length_m: float = 0.0

    ground_height_m: float = 0.0

    beam_above_ground_m: float = 0.0

    height_gradient: float = 0.0

    earth_curvature_drop_m: float = 0.0

    temperature_C: float = 0.0

    wind_direction_deg: float = 0.0

    refinement_level: int = 0
    latitude_deg: float = 0.0
    longitude_deg: float = 0.0
    ground_distance_m: float = 0.0

    surface_type: str = "Unknown"
    # Weather
    cloud_base_height_m: float = 2000.0

    aerosol_alpha: float = 1.3
    humidity_pct: float = 0.0
    pressure_hPa: float = 0.0
    visibility_km: float = 0.0
    rain_rate_mm_hr: float = 0.0

    cloud_cover_percent: float = 0.0
    wind_speed_m_s: float = 0.0
    refractive_index: float = 1.0
    capture_fraction: float = 1.0
    dn_dz: float = 0.0
    # Geometry
    surface_height_m: float = 0.0

    height_above_msl_m: float = 0.0

    beam_above_surface_m: float = 0.0

    path_fraction: float = 0.0
    beam_radius_m: float = 0.0
    beam_diameter_m: float = 0.0
    distance_from_tx_m: float = 0.0
    beam_center_x_m: float = 0.0
    beam_center_y_m: float = 0.0
    slant_distance_m: float = 0.0
    # Slant Geometry
    start_distance_m: float = 0.0
    end_distance_m: float = 0.0
    center_distance_m: float = 0.0

    start_height_m: float = 0.0
    end_height_m: float = 0.0
    center_height_m: float = 0.0

    line_of_sight_height_m: float = 0.0

    earth_drop_m: float = 0.0

    distance_from_surface_m: float = 0.0
    elevation_angle_deg: float = 0.0
    clearance_above_ground_m: float = 0.0
    local_horizon_m: float = 0.0
    los: bool = True

    fresnel_radius_m: float = 0.0
    total_geometric_loss_dB: float = 0.0
    ray_curvature_1_m: float = 0.0
    ray_bending_urad: float = 0.0
    # Marine
    sea_state: float = 0.0
    wave_height_m: float = 0.0
    # Refractivity
    refractivity_N: float = 0.0
    modified_refractivity_M: float = 0.0
    terrain_slope_deg: float = 0.0

    terrain_aspect_deg: float = 0.0

    terrain_elevation_m: float = 0.0

    surface_elevation_m: float = 0.0

    surface_roughness_m: float = 0.0
    vegetation_height_m: float = 0.0
    bathymetry_depth_m: float = 0.0
    is_land: bool = False

    is_sea: bool = False

    coastal: bool = False

    terrain_category: str = ""

    height_above_surface_m: float = 0.0
    clear_sky_radiance_W_sr_m2: float = 0.0
    total_background_radiance_W_sr_m2: float = 0.0

    solar_background_W_sr_m2: float = 0.0
    moon_background_W_sr_m2: float = 0.0
    sky_background_W_sr_m2: float = 0.0
    background_power_W: float = 0.0
    background_photon_rate: float = 0.0
    background_count_rate: float = 0.0

    background_transmission: float = 1.0

    surface_background_factor: float = 1.0

    background_radiance_W_sr_m2: float = 0.0

    filter_overlap_fraction: float = 1.0

    solar_overlap_fraction: float = 0.0
    tx_overlap_fraction: float = 0.0
    combined_solar_overlap: float = 0.0

    receiver_solid_angle_sr: float = 0.0

    cumulative_background_power_W: float = 0.0
    cumulative_background_photon_rate: float = 0.0
    cumulative_background_count_rate: float = 0.0

    background_source: str = ""

    # Turbulence
    Cn2: float = 0.0
    fried_parameter_m: float = 0.0
    rytov_variance: float = 0.0
    scintillation_index: float = 0.0
    roll_rate_deg_s: float = 0.0
    pitch_rate_deg_s: float = 0.0
    yaw_rate_deg_s: float = 0.0
    roll_rms_deg: float = 0.0
    pitch_rms_deg: float = 0.0
    yaw_rms_deg: float = 0.0

    # Losses
    atmospheric_loss_dB: float = 0.0
    # Research atmospheric quantities

    extinction_coefficient_km: float = 0.0

    beer_lambert_transmission: float = 1.0

    molecular_extinction_km: float = 0.0

    aerosol_extinction_km: float = 0.0

    fog_extinction_km: float = 0.0

    rain_extinction_km: float = 0.0

    cloud_extinction_km: float = 0.0

    visibility_exponent_q: float = 0.0

    attenuation_model_used: str = ""
    scintillation_loss_dB: float = 0.0
    geometric_loss_dB: float = 0.0

    # Power
    received_power_W: float = 0.0

    duct_height_m: float = 0.0

    duct_strength: float = 0.0

    super_refraction: bool = False
    beam_start_height_m: float = 0.0
    beam_end_height_m: float = 0.0
    los_height_m: float = 0.0
    curvature_error_m: float = 0.0

    effective_earth_radius_factor: float = 1.333
    beam_height_m: float = 0.0
    center_m: float = 0.0
    # Dynamically injected attributes now statically declared
    Cn2_m2_3: float = 0.0
    acquisition_probability: float = 0.0
    acquisition_time_s: float = 0.0
    aerosol_gamma_dB_per_km: float = 0.0
    aerosol_loss_dB: float = 0.0
    afterpulse_count_rate: float = 0.0
    afterpulse_counts: float = 0.0
    air_density_kg_m3: float = 0.0
    air_sea_temperature_difference_C: float = 0.0
    atmosphere_complete: float = 0.0
    atmospheric_transmission: float = 0.0
    atmospheric_transmission_percent: float = 0.0
    attenuation_coefficient_dB_per_km: float = 0.0
    authentication_cost: float = 0.0
    availability_percent: float = 0.0
    background_counts: float = 0.0
    beacon_qkd_offset_urad: float = 0.0
    beam_area_m2: float = 0.0
    beam_divergence_rad: float = 0.0
    beam_irradiance_W_m2: float = 0.0
    beam_offset_m: float = 0.0
    beam_power_W: float = 0.0
    beam_refraction_shift_m: float = 0.0
    beam_spread_factor: float = 0.0
    beam_waist_m: float = 0.0
    beam_wander_urad: float = 0.0
    bell_parameter: float = 0.0
    binary_entropy: float = 0.0
    channel_efficiency: float = 0.0
    chromatic_dispersion_factor: float = 0.0
    clearance_ratio: float = 0.0
    clock_offset_ns: float = 0.0
    cloud_gamma_dB_per_km: float = 0.0
    cloud_loss_dB: float = 0.0
    coherence_time_ms: float = 0.0
    coincidence_rate: float = 0.0
    corrected_pointing_error_urad: float = 0.0
    cumulative_atmospheric_loss_dB: float = 0.0
    cumulative_atmospheric_transmission: float = 0.0
    cumulative_bending_urad: float = 0.0
    cumulative_distance_m: float = 0.0
    cumulative_fsm_correction_urad: float = 0.0
    cumulative_loss_dB: float = 0.0
    cumulative_pointing_loss_dB: float = 0.0
    cumulative_receiver_separation_mm: float = 0.0
    cumulative_transmission: float = 0.0
    dark_count_rate: float = 0.0
    dark_counts: float = 0.0
    database_name: float = 0.0
    deadtime_loss_fraction: float = 0.0
    decoy_gain: float = 0.0
    delta_refractive_index: float = 0.0
    delta_wavelength_nm: float = 0.0
    dem_source: float = 0.0
    detection_probability: float = 0.0
    detector_efficiency: float = 0.0
    detector_saturation_fraction: float = 0.0
    detector_type: float = 0.0
    dew_point_C: float = 0.0
    differential_refraction_urad: float = 0.0
    diffraction_loss_dB: float = 0.0
    drag_coefficient: float = 0.0
    duct_decay: float = 0.0
    duct_decay_factor: float = 0.0
    effective_capture_fraction: float = 0.0
    effective_channel_efficiency: float = 0.0
    effective_secure_key_rate: float = 0.0
    error_correction_efficiency: float = 0.0
    error_correction_leakage: float = 0.0
    farid_A0: float = 0.0
    farid_equivalent_beam_radius_m: float = 0.0
    final_key_utilization: float = 0.0
    final_secure_key_rate: float = 0.0
    fresnel_number: float = 0.0
    friction_velocity_m_s: float = 0.0
    fsm_bandwidth_Hz: float = 0.0
    fsm_closed_loop: float = 0.0
    fsm_correction_required_urad: float = 0.0
    fsm_coupling_penalty_dB: float = 0.0
    fsm_margin_urad: float = 0.0
    fsm_residual_error_urad: float = 0.0
    fsm_settling_time_s: float = 0.0
    fsm_stroke_urad: float = 0.0
    fsm_suppression_ratio: float = 0.0
    fsm_tracking_efficiency: float = 0.0
    gate_efficiency: float = 0.0
    gimbal_acceleration_deg_s2: float = 0.0
    gimbal_azimuth_deg: float = 0.0
    gimbal_bandwidth_Hz: float = 0.0
    gimbal_closed_loop: float = 0.0
    gimbal_elevation_deg: float = 0.0
    gimbal_pointing_error_deg: float = 0.0
    gimbal_pointing_error_rad: float = 0.0
    gimbal_rate_deg_s: float = 0.0
    gimbal_settling_time_s: float = 0.0
    gimbal_tracking_efficiency: float = 0.0
    gimbal_tracking_error_urad: float = 0.0
    gimbal_tracking_quality: float = 0.0
    greenwood_frequency_Hz: float = 0.0
    humidity_scale: float = 0.0
    is_blocked: float = 0.0
    is_daylight: float = 0.0
    isoplanatic_angle_urad: float = 0.0
    land_percentage: float = 0.0
    line_of_sight_available: float = 0.0
    link_quality: float = 0.0
    link_transmission: float = 0.0
    lock_probability: float = 0.0
    m_deficit: float = 0.0
    marine_BL_height_m: float = 0.0
    marine_layer_fraction: float = 0.0
    mean_refractive_index: float = 0.0
    mean_sea_level_height_m: float = 0.0
    modified_refractivity_deficit: float = 0.0
    modified_refractivity_gradient: float = 0.0
    modified_refractivity_gradient_N_km: float = 0.0
    molecular_gamma_dB_per_km: float = 0.0
    molecular_loss_dB: float = 0.0
    monin_obukhov_length_m: float = 0.0
    noise_counts: float = 0.0
    noise_qber: float = 0.0
    observed_count_rate: float = 0.0
    optical_horizon_km: float = 0.0
    optical_power_W: float = 0.0
    pat_factor: float = 0.0
    path_length_m: float = 0.0
    path_transmission: float = 0.0
    pointing_angle_urad: float = 0.0
    pointing_efficiency: float = 0.0
    pointing_error_m: float = 0.0
    pointing_loss_dB: float = 0.0
    polarization_loss_dB: float = 0.0
    polarization_misalignment_loss_dB: float = 0.0
    polarization_qber: float = 0.0
    polarization_rotation_deg: float = 0.0
    polarization_visibility: float = 0.0
    privacy_amplification_loss: float = 0.0
    profile_height_m: float = 0.0
    propagation_distance_m: float = 0.0
    propagation_loss_dB: float = 0.0
    qber: float = 0.0
    quantum_refractive_index: float = 0.0
    quantum_wavelength_nm: float = 0.0
    rain_gamma_dB_per_km: float = 0.0
    rain_loss_dB: float = 0.0
    rain_loss_dB_km: float = 0.0
    raw_detection_rate: float = 0.0
    raw_key_rate: float = 0.0
    ray_bending_rad: float = 0.0
    rayleigh_length_m: float = 0.0
    receiver_offset_mm: float = 0.0
    receiver_separation_mm: float = 0.0
    refractivity_gradient_N_km: float = 0.0
    relative_humidity_pct: float = 0.0
    rx_coupling_efficiency: float = 0.0
    saturation_vapor_pressure_hPa: float = 0.0
    sea_percentage: float = 0.0
    sea_surface_temperature_C: float = 0.0
    secret_fraction: float = 0.0
    secure_detection_fraction: float = 0.0
    secure_key_rate: float = 0.0
    security_status: float = 0.0
    sensible_heat_flux_W_m2: float = 0.0
    ship_los_jitter_urad: float = 0.0
    ship_pointing_shift_m: float = 0.0
    sifted_coincidence_rate: float = 0.0
    sifted_key_rate: float = 0.0
    signal_count_rate: float = 0.0
    signal_counts: float = 0.0
    signal_detection_probability: float = 0.0
    signal_to_noise_ratio: float = 0.0
    single_photon_gain: float = 0.0
    sky_radiance_W_sr_m2: float = 0.0
    slice_transmission: float = 0.0
    solar_azimuth_deg: float = 0.0
    solar_azimuth_direction: float = 0.0
    solar_elevation_deg: float = 0.0
    solar_flux_W_m2: float = 0.0
    solar_zenith_deg: float = 0.0
    spot_diameter_m: float = 0.0
    stability_parameter: float = 0.0
    stability_regime: float = 0.0
    surface_factor: float = 0.0
    surface_refractivity_N: float = 0.0
    surface_vapor_pressure_hPa: float = 0.0
    sync_loss_dB: float = 0.0
    sync_penalty_factor: float = 0.0
    sync_qber: float = 0.0
    synchronization_error: float = 0.0
    temperature_K: float = 0.0
    temperature_scale_K: float = 0.0
    timing_jitter_ps: float = 0.0
    total_counts: float = 0.0
    total_gamma_dB_per_km: float = 0.0
    total_jitter_urad: float = 0.0
    total_noise_counts: float = 0.0
    total_ship_motion_deg: float = 0.0
    tracking_error_urad: float = 0.0
    tracking_probability: float = 0.0
    tracking_qber: float = 0.0
    tracking_refractive_index: float = 0.0
    tracking_wavelength_nm: float = 0.0
    transmission: float = 0.0
    turbulence_regime: float = 0.0
    turbulence_strength: float = 0.0
    tx_beam_divergence_mrad: float = 0.0
    u_star: float = 0.0
    vapor_pressure_hPa: float = 0.0
    visibility: float = 0.0
    visibility_gamma_dB_per_km: float = 0.0
    visibility_loss_dB: float = 0.0
    visibility_quality_factor: float = 0.0
    water_vapor_density_g_m3: float = 0.0
    wavefront_radius_m: float = 0.0
    # Debug
    notes: str = ""

    @staticmethod
    def format_attribute_name(attr_name: str) -> str:
        """Converts an attribute name like 'beam_height_m' to 'Beam Height'."""
        suffixes = {
            "_m", "_km", "_deg", "_C", "_hPa", "_pct", "_mm_hr", "_s", "_urad", "_dB",
            "_W", "_sr_m2", "_W_sr_m2", "_kg_m3", "_g_m3", "_Hz", "_km1", "_m2_3",
            "_deg_s", "_deg_s2", "_W_m2", "_nm", "_bps", "_cps"
        }
        
        for suffix in sorted(suffixes, key=len, reverse=True):
            if attr_name.endswith(suffix):
                attr_name = attr_name[:-len(suffix)]
                break
                
        name = " ".join(word.capitalize() for word in attr_name.split("_"))
        return name

    @staticmethod
    def format_value(val, attr_name: str = "") -> str:
        """Formats a float with engineering units or returns string representation."""
        if not isinstance(val, (int, float)):
            return str(val)
        if val == 0.0:
            return "0.0"

        import math
        
        unit = ""
        if attr_name.endswith("_m"): unit = "m"
        elif attr_name.endswith("_W"): unit = "W"
        elif attr_name.endswith("_Hz"): unit = "Hz"
        elif attr_name.endswith("_s"): unit = "s"
        elif attr_name.endswith("_bps"): unit = "bps"
        elif attr_name.endswith("_cps") or attr_name.endswith("count_rate"): unit = "cps"
        elif attr_name.endswith("_nm"): unit = "nm"
        
        # Original units that we don't scale with SI prefixes
        if not unit or attr_name.endswith(("_deg", "_dB", "_pct", "_C", "_K", "_hPa", "m2_3")):
            original_unit = ""
            if attr_name.endswith("_deg"): original_unit = " °"
            elif attr_name.endswith("_dB"): original_unit = " dB"
            elif attr_name.endswith("_pct"): original_unit = " %"
            elif attr_name.endswith("_C"): original_unit = " °C"
            elif attr_name.endswith("_K"): original_unit = " K"
            elif attr_name.endswith("_hPa"): original_unit = " hPa"
            elif attr_name.endswith("_urad"): original_unit = " µrad"
            elif attr_name.endswith("_mrad"): original_unit = " mrad"
            elif attr_name.endswith("_km"): original_unit = " km"
            elif attr_name.endswith("m2_3"): original_unit = " m⁻²/³"
            elif attr_name.endswith("sr_m2"): original_unit = " W/sr/m²"
            
            if abs(val) < 1e-3 or abs(val) > 1e4:
                return f"{val:.4e}{original_unit}"
            else:
                # heuristic: if small float show more decimals
                if abs(val) < 1.0:
                    return f"{val:.4f}{original_unit}"
                return f"{val:.2f}{original_unit}"

        abs_val = abs(val)

        if attr_name == "beam_radius_m":
            return f"{val:.6f} m"
        
        if unit == "m": prefixes = {3: "km", 0: "m", -2: "cm", -3: "mm", -6: "µm", -9: "nm"}
        elif unit == "W": prefixes = {3: "kW", 0: "W", -3: "mW", -6: "µW", -9: "nW"}
        elif unit == "Hz": prefixes = {9: "GHz", 6: "MHz", 3: "kHz", 0: "Hz"}
        elif unit == "s": prefixes = {0: "s", -3: "ms", -6: "µs", -9: "ns", -12: "ps"}
        elif unit == "bps": prefixes = {9: "Gbps", 6: "Mbps", 3: "kbps", 0: "bps"}
        elif unit == "cps": prefixes = {9: "Gcps", 6: "Mcps", 3: "kcps", 0: "cps"}
        elif unit == "nm": prefixes = {0: "nm"}
        
        if abs_val == 0:
            p = 0
        else:
            p = int(math.floor(math.log10(abs_val) / 3)) * 3
            
        # specifically check for cm
        if unit == "m" and 0.01 <= abs_val < 0.1:
            p = -2
            
        available_p = sorted(prefixes.keys())
        if p < available_p[0]:
            p = available_p[0]
        elif p > available_p[-1]:
            p = available_p[-1]
            
        scaled_val = val / (10**p)
        
        if abs(scaled_val) < 1e-3 or abs(scaled_val) >= 1e4:
            return f"{val:.4e} {prefixes[0]}"
            
        # Determine format (e.g. 15.00 instead of 15.000)
        if abs(scaled_val) >= 100:
            return f"{scaled_val:.1f} {prefixes[p]}"
        elif abs(scaled_val) >= 10:
            return f"{scaled_val:.2f} {prefixes[p]}"
        else:
            return f"{scaled_val:.3f} {prefixes[p]}"

    @staticmethod
    def get_category(attr_name: str) -> str:
        return SLICE_CATEGORY_MAP.get(attr_name, "Miscellaneous")

SLICE_CATEGORY_MAP = {
    "slice_id": "System", "refinement_level": "System", "notes": "System", "database_name": "System", "dem_source": "System",
    "start_m": "Geometry", "end_m": "Geometry", "length_m": "Geometry", "latitude_deg": "Geometry",
    "longitude_deg": "Geometry", "ground_distance_m": "Geometry", "distance_from_tx_m": "Geometry",
    "slant_distance_m": "Geometry", "start_distance_m": "Geometry", "end_distance_m": "Geometry",
    "center_distance_m": "Geometry", "start_height_m": "Geometry", "end_height_m": "Geometry",
    "center_height_m": "Geometry", "line_of_sight_height_m": "Geometry", "earth_drop_m": "Geometry",
    "distance_from_surface_m": "Geometry", "elevation_angle_deg": "Geometry", "clearance_above_ground_m": "Geometry",
    "local_horizon_m": "Geometry", "los": "Geometry", "fresnel_radius_m": "Geometry", "fresnel_number": "Geometry",
    "earth_curvature_drop_m": "Geometry", "height_above_msl_m": "Geometry", "path_fraction": "Geometry",
    "beam_above_ground_m": "Geometry", "beam_above_surface_m": "Geometry", "height_above_surface_m": "Geometry",
    "clearance_ratio": "Geometry", "cumulative_distance_m": "Geometry", "distance_m": "Geometry",
    "is_blocked": "Geometry", "line_of_sight_available": "Geometry", "los_height_m": "Geometry",
    "optical_horizon_km": "Geometry", "path_length_m": "Geometry", "profile_height_m": "Geometry",
    "propagation_distance_m": "Geometry", "curvature_error_m": "Geometry", "beam_height_m": "Geometry",
    "center_m": "Geometry", "mean_sea_level_height_m": "Geometry", "beam_start_height_m": "Geometry", "beam_end_height_m": "Geometry",
    "ground_height_m": "Terrain", "height_gradient": "Terrain", "surface_type": "Terrain", "surface_height_m": "Terrain",
    "terrain_slope_deg": "Terrain", "terrain_aspect_deg": "Terrain", "terrain_elevation_m": "Terrain",
    "surface_elevation_m": "Terrain", "surface_roughness_m": "Terrain", "vegetation_height_m": "Terrain",
    "is_land": "Terrain", "land_percentage": "Terrain", "sea_percentage": "Terrain", "terrain_category": "Terrain", "surface_factor": "Terrain",
    "minimum_clearance_m": "Terrain", "maximum_clearance_m": "Terrain", "lowest_los_height_m": "Terrain",
    "lowest_los_distance_m": "Terrain", "highest_los_height_m": "Terrain", "highest_los_distance_m": "Terrain",
    "average_ground_height_m": "Terrain", "coastal_path": "Terrain", "dominant_surface": "Terrain",
    "sea_state": "Marine", "wave_height_m": "Marine", "bathymetry_depth_m": "Marine", "is_sea": "Marine",
    "coastal": "Marine", "marine_BL_height_m": "Marine", "marine_layer_fraction": "Marine",
    "sea_surface_temperature_C": "Marine", "air_sea_temperature_difference_C": "Marine", "sensible_heat_flux_W_m2": "Marine",
    "temperature_C": "Atmosphere", "temperature_K": "Atmosphere", "pressure_hPa": "Atmosphere",
    "humidity_pct": "Atmosphere", "relative_humidity_pct": "Atmosphere", "air_density_kg_m3": "Atmosphere",
    "water_vapor_density_g_m3": "Atmosphere", "vapor_pressure_hPa": "Atmosphere",
    "saturation_vapor_pressure_hPa": "Atmosphere", "surface_vapor_pressure_hPa": "Atmosphere",
    "dew_point_C": "Atmosphere", "atmosphere_complete": "Atmosphere", "is_daylight": "Atmosphere",
    "solar_azimuth_deg": "Atmosphere", "solar_azimuth_direction": "Atmosphere", "solar_elevation_deg": "Atmosphere",
    "solar_flux_W_m2": "Atmosphere", "solar_zenith_deg": "Atmosphere",
    "cloud_base_height_m": "Weather", "cloud_cover_percent": "Weather", "rain_rate_mm_hr": "Weather",
    "wind_speed_m_s": "Weather", "wind_direction_deg": "Weather", "visibility_km": "Weather",
    "visibility": "Weather", "visibility_quality_factor": "Weather",
    "Cn2": "Turbulence", "Cn2_m2_3": "Turbulence", "fried_parameter_m": "Turbulence", "rytov_variance": "Turbulence",
    "scintillation_index": "Turbulence", "scintillation_loss_dB": "Turbulence", "coherence_time_ms": "Turbulence",
    "greenwood_frequency_Hz": "Turbulence", "isoplanatic_angle_urad": "Turbulence", "turbulence_regime": "Turbulence",
    "turbulence_strength": "Turbulence", "stability_parameter": "Turbulence", "stability_regime": "Turbulence",
    "friction_velocity_m_s": "Turbulence", "u_star": "Turbulence", "monin_obukhov_length_m": "Turbulence",
    "temperature_scale_K": "Turbulence", "humidity_scale": "Turbulence",
    "refractive_index": "Refraction", "dn_dz": "Refraction", "refractivity_N": "Refraction",
    "modified_refractivity_M": "Refraction", "delta_refractive_index": "Refraction", "mean_refractive_index": "Refraction",
    "quantum_refractive_index": "Refraction", "surface_refractivity_N": "Refraction",
    "refractivity_gradient_N_km": "Refraction", "modified_refractivity_gradient": "Refraction",
    "modified_refractivity_gradient_N_km": "Refraction", "modified_refractivity_deficit": "Refraction",
    "m_deficit": "Refraction", "duct_height_m": "Refraction", "duct_strength": "Refraction", "duct_decay": "Refraction",
    "duct_decay_factor": "Refraction", "super_refraction": "Refraction", "effective_earth_radius_factor": "Refraction",
    "ray_curvature_1_m": "Refraction", "ray_bending_urad": "Refraction", "ray_bending_rad": "Refraction",
    "differential_refraction_urad": "Refraction", "cumulative_bending_urad": "Refraction", "tracking_refractive_index": "Refraction",
    "extinction_coefficient_km": "Extinction", "aerosol_extinction_km": "Extinction", "cloud_extinction_km": "Extinction",
    "fog_extinction_km": "Extinction", "molecular_extinction_km": "Extinction", "rain_extinction_km": "Extinction",
    "aerosol_gamma_dB_per_km": "Extinction", "cloud_gamma_dB_per_km": "Extinction", "molecular_gamma_dB_per_km": "Extinction",
    "rain_gamma_dB_per_km": "Extinction", "total_gamma_dB_per_km": "Extinction", "visibility_gamma_dB_per_km": "Extinction",
    "attenuation_coefficient_dB_per_km": "Extinction", "attenuation_model_used": "Extinction", "visibility_exponent_q": "Extinction",
    "aerosol_alpha": "Scattering", "clear_sky_radiance_W_sr_m2": "Scattering", "total_background_radiance_W_sr_m2": "Scattering",
    "solar_background_W_sr_m2": "Scattering", "moon_background_W_sr_m2": "Scattering", "sky_background_W_sr_m2": "Scattering",
    "sky_radiance_W_sr_m2": "Scattering", "background_radiance_W_sr_m2": "Scattering", "background_power_W": "Scattering",
    "cumulative_background_power_W": "Scattering", "background_transmission": "Scattering", "surface_background_factor": "Scattering",
    "background_source": "Scattering", "rayleigh_length_m": "Scattering",
    "beam_radius_m": "Geometry", "beam_diameter_m": "Geometry", "beam_center_x_m": "Geometry",
    "beam_center_y_m": "Geometry", "beam_area_m2": "Geometry", "beam_divergence_rad": "Geometry",
    "tx_beam_divergence_mrad": "Geometry", "beam_irradiance_W_m2": "Geometry", "beam_power_W": "Geometry",
    "optical_power_W": "Geometry", "beam_offset_m": "Geometry", "beam_refraction_shift_m": "Geometry",
    "beam_spread_factor": "Geometry", "beam_waist_m": "Geometry", "beam_wander_urad": "Geometry",
    "farid_A0": "Geometry", "farid_equivalent_beam_radius_m": "Geometry", "spot_diameter_m": "Geometry",
    "wavefront_radius_m": "Geometry", "chromatic_dispersion_factor": "Geometry",
    "delta_wavelength_nm": "Geometry", "quantum_wavelength_nm": "Geometry", "tracking_wavelength_nm": "Geometry",
    "roll_rate_deg_s": "Pointing & Tracking", "pitch_rate_deg_s": "Pointing & Tracking", "yaw_rate_deg_s": "Pointing & Tracking",
    "roll_rms_deg": "Pointing & Tracking", "pitch_rms_deg": "Pointing & Tracking", "yaw_rms_deg": "Pointing & Tracking",
    "total_ship_motion_deg": "Pointing & Tracking", "ship_los_jitter_urad": "Pointing & Tracking", "ship_pointing_shift_m": "Pointing & Tracking",
    "gimbal_acceleration_deg_s2": "Pointing & Tracking", "gimbal_azimuth_deg": "Pointing & Tracking",
    "gimbal_bandwidth_Hz": "Pointing & Tracking", "gimbal_closed_loop": "Pointing & Tracking",
    "gimbal_elevation_deg": "Pointing & Tracking", "gimbal_pointing_error_deg": "Pointing & Tracking",
    "gimbal_pointing_error_rad": "Pointing & Tracking", "gimbal_rate_deg_s": "Pointing & Tracking",
    "gimbal_settling_time_s": "Pointing & Tracking", "gimbal_tracking_efficiency": "Pointing & Tracking",
    "gimbal_tracking_error_urad": "Pointing & Tracking", "gimbal_tracking_quality": "Pointing & Tracking",
    "fsm_bandwidth_Hz": "Pointing & Tracking", "fsm_closed_loop": "Pointing & Tracking",
    "fsm_correction_required_urad": "Pointing & Tracking", "fsm_coupling_penalty_dB": "Pointing & Tracking",
    "fsm_margin_urad": "Pointing & Tracking", "fsm_residual_error_urad": "Pointing & Tracking",
    "fsm_settling_time_s": "Pointing & Tracking", "fsm_stroke_urad": "Pointing & Tracking",
    "fsm_suppression_ratio": "Pointing & Tracking", "fsm_tracking_efficiency": "Pointing & Tracking",
    "cumulative_fsm_correction_urad": "Pointing & Tracking", "corrected_pointing_error_urad": "Pointing & Tracking",
    "pointing_angle_urad": "Pointing & Tracking", "pointing_efficiency": "Pointing & Tracking",
    "pointing_error_m": "Pointing & Tracking", "tracking_error_urad": "Pointing & Tracking", "total_jitter_urad": "Pointing & Tracking",
    "pat_factor": "Pointing & Tracking", "acquisition_probability": "Pointing & Tracking",
    "acquisition_time_s": "Pointing & Tracking", "tracking_probability": "Pointing & Tracking",
    "lock_probability": "Pointing & Tracking", "drag_coefficient": "Pointing & Tracking", "beacon_qkd_offset_urad": "Pointing & Tracking",
    "capture_fraction": "Link Budget", "effective_capture_fraction": "Link Budget", "filter_overlap_fraction": "Link Budget",
    "solar_overlap_fraction": "Link Budget", "tx_overlap_fraction": "Link Budget", "combined_solar_overlap": "Link Budget",
    "receiver_solid_angle_sr": "Link Budget", "receiver_offset_mm": "Link Budget", "receiver_separation_mm": "Link Budget",
    "cumulative_receiver_separation_mm": "Link Budget", "rx_coupling_efficiency": "Link Budget",
    "total_geometric_loss_dB": "Link Budget", "geometric_loss_dB": "Link Budget", "diffraction_loss_dB": "Link Budget",
    "pointing_loss_dB": "Link Budget", "cumulative_pointing_loss_dB": "Link Budget", "atmospheric_loss_dB": "Link Budget",
    "cumulative_atmospheric_loss_dB": "Link Budget", "aerosol_loss_dB": "Link Budget", "cloud_loss_dB": "Link Budget",
    "molecular_loss_dB": "Link Budget", "rain_loss_dB": "Link Budget", "rain_loss_dB_km": "Link Budget",
    "visibility_loss_dB": "Link Budget", "sync_loss_dB": "Link Budget", "polarization_loss_dB": "Link Budget",
    "polarization_misalignment_loss_dB": "Link Budget", "propagation_loss_dB": "Link Budget", "cumulative_loss_dB": "Link Budget",
    "beer_lambert_transmission": "Link Budget", "atmospheric_transmission": "Link Budget",
    "atmospheric_transmission_percent": "Link Budget", "cumulative_atmospheric_transmission": "Link Budget",
    "transmission": "Link Budget", "slice_transmission": "Link Budget", "path_transmission": "Link Budget",
    "link_transmission": "Link Budget", "cumulative_transmission": "Link Budget", "received_power_W": "Link Budget",
    "signal_to_noise_ratio": "Link Budget", "link_quality": "Link Budget", "availability_percent": "Link Budget",
    "channel_efficiency": "Link Budget", "effective_channel_efficiency": "Link Budget",
    "detector_efficiency": "Detector", "detector_type": "Detector", "detector_saturation_fraction": "Detector",
    "deadtime_loss_fraction": "Detector", "gate_efficiency": "Detector", "timing_jitter_ps": "Detector",
    "clock_offset_ns": "Detector", "synchronization_error": "Detector", "background_photon_rate": "Detector",
    "background_count_rate": "Detector", "cumulative_background_photon_rate": "Detector",
    "cumulative_background_count_rate": "Detector", "dark_count_rate": "Detector", "afterpulse_count_rate": "Detector",
    "signal_count_rate": "Detector", "observed_count_rate": "Detector", "raw_detection_rate": "Detector",
    "dark_counts": "Detector", "afterpulse_counts": "Detector", "background_counts": "Detector",
    "noise_counts": "Detector", "total_noise_counts": "Detector", "signal_counts": "Detector",
    "total_counts": "Detector", "detection_probability": "Detector", "signal_detection_probability": "Detector",
    "secure_detection_fraction": "Detector", "single_photon_gain": "Detector", "decoy_gain": "Detector",
    "coincidence_rate": "Detector", "sifted_coincidence_rate": "Detector",
    "bell_parameter": "QKD", "binary_entropy": "QKD", "authentication_cost": "QKD", "error_correction_efficiency": "QKD",
    "error_correction_leakage": "QKD", "privacy_amplification_loss": "QKD", "polarization_rotation_deg": "QKD",
    "polarization_visibility": "QKD", "polarization_qber": "QKD", "sync_qber": "QKD", "tracking_qber": "QKD",
    "noise_qber": "QKD", "qber": "QKD", "raw_key_rate": "QKD", "sifted_key_rate": "QKD", "secure_key_rate": "QKD",
    "effective_secure_key_rate": "QKD", "final_secure_key_rate": "QKD", "final_key_utilization": "QKD",
    "secret_fraction": "QKD", "sync_penalty_factor": "QKD", "security_status": "QKD"
}

@dataclass
class SimulationState:

    # =========================================================
    # MISSION INPUTS
    # =========================================================
    link_distance_km: float = 10.0
    tx_height_msl_m: float = 10.0
    tx_latitude_deg: float = 28.6139
    tx_longitude_deg: float = 77.2090

    rx_latitude_deg: float = 28.7041
    rx_longitude_deg: float = 77.1025
    month: int = 6

    day: int = 15
    path_direction: str = "Unknown"

    minimum_slice_height_difference_m: float = 2.0

    time_of_day_hr: float = 12.0
    moon_phase_percent: float = 50.0
    rx_height_msl_m: float = 15.0
    minimum_height_above_sea_m: float = 5.0

    solve_for: str = "Minimum Height Above Sea"

    earth_curvature_enabled: bool = True

    day_of_year: int = 180
    wave_period_s: float = 5.0

    local_time_hours: float = 12.0
    slant_range_m: float = 0.0

    height_difference_m: float = 0.0
    tx_height_agl_m: float = 20.0
    rx_height_agl_m: float = 20.0

    earth_radius_m: float = 6378137.0

    effective_earth_radius_factor: float = 1.333

    lowest_los_point_m: float = 0.0

    lowest_los_distance_m: float = 0.0

    slice_height_step_m: float = 2.0

    beam_elevation_angle_deg: float = 0.0
    cloud_type: str = "Clear"
    # =========================================================
    # MODEL SELECTION
    # =========================================================

    # Atmospheric attenuation model
    atmospheric_model: str = "Kim"

    # Literature reference
    atmospheric_model_reference: str = ""

    # Validity information
    atmospheric_model_validity: str = ""

    # Extinction coefficient
    extinction_coefficient_km: float = 0.0

    # Beer–Lambert transmission
    beer_lambert_transmission: float = 1.0

    # Spectral transmission
    spectral_transmission: float = 1.0
    # =========================================================
    # Research Atmospheric Model Outputs (v0.4)
    # =========================================================

    atmospheric_transmission_db: float = 0.0

    molecular_extinction_km: float = 0.0

    aerosol_extinction_km: float = 0.0

    fog_extinction_km: float = 0.0

    rain_extinction_km: float = 0.0

    cloud_extinction_km: float = 0.0

    total_extinction_km: float = 0.0

    visibility_exponent_q: float = 0.0

    attenuation_model_used: str = ""

    attenuation_reference: str = ""

    attenuation_validity: str = ""

    tracking_model: str = "FSM"

    detector_model = "SPAD"
    detector_type: str = "SNSPD"

    qkd_protocol: str = "Decoy BB84"

    # =========================================================
    # OPTICS INPUTS
    # =========================================================
    wavelength_nm: float = 1550

    highest_los_height_m: float = 0.0

    highest_los_distance_m: float = 0.0
    # -----------------------------
    # Optical Filter
    # -----------------------------

    source_bandwidth_nm = 2.0
    average_slice_capture_fraction = 1.0

    rx_filter_bandwidth_nm = 0.5

    rx_filter_center_wavelength_nm = 1550.0

    filter_overlap_fraction = 1.0

    filtered_signal_fraction = 1.0

    filtered_background_fraction = 1.0

    tx_aperture_mm: float = 150.0
    rx_aperture_mm: float = 600.0
    tx_beam_divergence_mrad: float = 0.1
    tx_beam_quality_M2: float = 1.0
    optical_system_loss_dB: float = 2.0
    detector_efficiency: float = 0.85
    dark_count_rate: float = 100.0
    mean_photon_number: float = 0.3
    pulse_rate_mhz: float = 200.0
    rx_fov_mrad: float = 1.0
    optical_filter_bw_nm: float = 1.0
    detector_responsivity_AW: float = 0.9
    target_skr_bps: float = 10.0  # or whatever default target you want

    # =========================================================
    # ENVIRONMENT INPUTS
    # =========================================================
    temperature_C: float = 25.0
    tx_temperature_C: float = 25.0
    rx_temperature_C: float = 25.0
    relative_humidity_pct: float = 80.0
    tx_humidity_pct: float = 80.0
    rx_humidity_pct: float = 80.0
    pressure_hPa: float = 1013.25
    tx_pressure_hPa: float = 1013.25
    rx_pressure_hPa: float = 1013.25
    visibility_km: float = 10.0
    terrain_model: str = "Statistical"
    terrain_type: str = "Coastal"
    tx_visibility_km: float = 10.0
    rx_visibility_km: float = 10.0
    wind_speed_m_s: float = 5.0
    tx_wind_speed_m_s: float = 5.0
    rx_wind_speed_m_s: float = 5.0
    rain_rate_mm_hr: float = 0.0
    cloud_cover_percent: float = 0.0
    tx_rain_rate_mm_hr: float = 0.0
    rx_rain_rate_mm_hr: float = 0.0
    geometric_loss_model: str = "Gaussian Beam Theory"

    tx_cloud_cover_percent: float = 0.0
    rx_cloud_cover_percent: float = 0.0

    tx_cloud_base_height_m: float = 2000.0
    rx_cloud_base_height_m: float = 2000.0

    tx_aerosol_alpha: float = 1.3
    rx_aerosol_alpha: float = 1.3
    effective_aerosol_alpha: float = 1.3
    sea_state: float = 3
    wave_height_m: float = 1.5
    wave_slope_rms_deg: float = 5.0
    evap_duct_height_m: float = 15.0
    marine_BL_height_m: float = 500.0
    stability_parameter: float = 0.0

    temperature_scale_K: float = 0.05
    total_geometric_loss_dB: float = 0.0

    humidity_scale: float = 0.05
    sea_surface_temperature_C: float = 27.0

    # =========================================================
    # TRACKING INPUTS
    # =========================================================
    roll_rms_deg: float = 0.0
    pitch_rms_deg: float = 0.0
    yaw_rms_deg: float = 0.0
    roll_rate_deg_s: float = 0.0
    pitch_rate_deg_s: float = 0.0
    yaw_rate_deg_s: float = 0.0
    gimbal_bw_hz: float = 10.0
    fsm_bw_hz: float = 200.0

    beam_jitter_rms_urad: float = 0.0
    acquisition_error_urad: float = 10.0
    polarization_error_rate: float = 0.01

    slice_min_length_m = 10.0

    slice_max_length_m = 500.0

    slice_height_tolerance_m = 1.0
    slice_curvature_tolerance_m: float = 0.05
    slice_clearance_tolerance_m: float = 0.5

    slice_cn2_tolerance = 0.05

    slice_refractivity_tolerance = 0.5

    # =========================================================
    # GEOMETRY OUTPUTS
    # =========================================================
    tx_height_out_m: float = 0.0
    rx_height_out_m: float = 0.0
    tx_aperture_out_mm: float = 0.0
    rx_aperture_out_mm: float = 0.0
    beam_divergence_out_mrad: float = 0.0
    spot_diameter_m: float = 0.0
    optical_horizon_km: float = 0.0
    earth_curvature_drop_m: float = 0.0
    effective_elevation_angle_deg: float = 0.0
    los: bool = True
    link_available: bool = True
    link_blocked_reason: str = ""
    los_margin_m: float = 0.0
    fresnel_radius_m: float = 0.0
    fresnel_clearance_pct: float = 100.0
    beam_radius_m: float = 0.0
    beam_diameter_m: float = 0.0
    capture_fraction: float = 0.0
    effective_earth_radius_m: float = 0.0
    distance_m: float = 0.0
    bearing_deg: float = 0.0
    wavelength_m: float = 0.0
    geometry_tx_latitude_deg: float = 0.0
    geometry_tx_longitude_deg: float = 0.0
    geometry_rx_latitude_deg: float = 0.0
    geometry_rx_longitude_deg: float = 0.0
    # =========================================================
    # ATMOSPHERE OUTPUTS
    # =========================================================
    solar_elevation_deg: float = 0.0
    solar_flux_W_m2: float = 0.0
    solar_azimuth_deg: float = 0.0
    solar_separation_deg: float = 180.0
    is_daylight: bool = False
    refractivity_N: float = 0.0
    sky_radiance_W_sr_m2: float = 0.0
    clear_sky_radiance_W_sr_m2: float = 0.0
    natural_sky_background_W: float = 0.0
    tracking_refractive_index: float = 0.0
    quantum_refractive_index: float = 0.0
    differential_refraction_urad: float = 0.0
    receiver_plane_offset_mm: float = 0.0
    receiver_separation_mm: float = 0.0
    fsm_correction_required_urad: float = 0.0
    fsm_correction_applied: bool = False
    solar_angle_factor: float = 1.0

    surface_refractivity_N: float = 0.0
    refractivity_gradient_N_km: float = 0.0
    fog_type: str = "Advection"

    duct_height_m: float = 0.0
    m_deficit: float = 0.0
    duct_strength: float = 0.0
    super_refraction: bool = False

    beacon_qkd_offset_urad: float = 0.0
    saturation_vapor_pressure_hPa: float = 0.0
    vapor_pressure_hPa: float = 0.0
    dew_point_C: float = 0.0
    air_density_kg_m3: float = 0.0
    water_vapor_density_g_m3: float = 0.0
    air_sea_temp_difference_C: float = 0.0
    modified_refractivity_M: float = 0.0
    refractivity_gradient: float = 0.0
    visibility_quality_factor: float = 0.0
    rain_loss_dB_km: float = 0.0
    visibility_loss_dB: float = 0.0
    rain_loss_dB: float = 0.0
    molecular_loss_dB: float = 0.0
    aerosol_loss_dB: float = 0.0
    atmospheric_transmission: float = 1.0
    fog_loss_dB: float = 0.0

    cloud_loss_dB: float = 0.0

    extinction_coefficient_km1: float = 0.0

    # =========================================================
    # PATH GEOMETRY (v0.4)
    # =========================================================
    path_type: str = "Unknown"

    ground_distance_km: float = 0.0

    gps_distance_km: float = 0.0

    path_length_m: float = 0.0

    lowest_los_height_m: float = 0.0

    lowest_los_distance_m: float = 0.0

    minimum_clearance_m: float = 0.0

    # =========================================================
    # TURBULENCE OUTPUTS
    # =========================================================
    cn2_model = "Hufnagel-Valley"
    pointing_loss_model: str = "Gaussian Pointing Error Model"
    Cn2_m2_3: float = 1e-15
    fried_parameter_m: float = 0.0
    rytov_variance: float = 0.0
    scintillation_index: float = 0.0
    beam_wander_urad: float = 0.0
    beam_spread_factor: float = 1.0
    greenwood_frequency_Hz: float = 0.0
    isoplanatic_angle_urad: float = 0.0
    coherence_time_ms: float = 0.0
    measurement_height_m: float = 2.0

    friction_velocity_m_s: float = 0.0

    temperature_scale_K: float = 0.0

    stability_parameter: float = 0.0

    temperature_structure_function: float = 0.0

    temperature_structure_constant: float = 0.0
    monin_obukhov_length_m: float = 0.0

    # Refractivity

    surface_refractive_index: float = 0.0
    dn_dz: float = 0.0
    ray_curvature_1_m: float = 0.0
    ray_bending_angle_urad: float = 0.0
    effective_elevation_bias_urad: float = 0.0
    beam_refraction_shift_m: float = 0.0

    # =========================================================
    # LINK BUDGET OUTPUTS
    # =========================================================
    geometric_loss_dB: float = 0.0
    atmospheric_loss_dB: float = 0.0
    pointing_loss_dB: float = 0.0
    total_link_loss_dB: float = 0.0
    rx_coupling_efficiency: float = 0.0
    effective_capture_fraction: float = 0.0
    availability_percent: float = 0.0
    channel_efficiency: float = 0.0
    scintillation_loss_dB: float = 0.0
    # =========================================================
    # DETECTOR OUTPUTS
    # =========================================================
    signal_count_rate: float = 0.0
    afterpulse_count_rate: float = 0.0
    tx_optical_loss_dB: float = 1.0
    rx_optical_loss_dB: float = 1.0
    background_count_rate: float = 0.0
    background_power_W: float = 0.0
    sky_background_W: float = 0.0
    sky_background_photons: float = 0.0
    dark_count_rate_out: float = 0.0
    # Ship Motion Inputs

    wave_direction_deg: float = 0.0
    wind_direction_deg: float = 0.0
    ship_heading_deg: float = 0.0
    ship_speed_knots: float = 15.0
    total_counts: float = 0.0
    detection_probability: float = 0.0
    background_photon_rate: float = 0.0

    deadtime_loss_fraction: float = 0.0
    detector_deadtime_ns: float = 0.0

    # =========================================================
    # QKD OUTPUTS
    # =========================================================
    qber: float = 0.0
    raw_key_rate: float = 0.0
    sifted_key_rate: float = 0.0
    rain_model: str = "Carbonneau"
    molecular_model: str = "Beer-Lambert"
    aerosol_model: str = "Shettle-Fenn"
    secret_fraction: float = 0.0
    secure_key_rate: float = 0.0
    # -------------------------------------------------
    # Common Derived QKD Parameters
    # -------------------------------------------------
    raw_detection_rate: float = 0.0
    signal_detection_probability: float = 0.0
    background_detection_probability: float = 0.0
    dark_detection_probability: float = 0.0
    signal_to_noise_ratio: float = 0.0
    visibility: float = 0.0
    noise_counts: float = 0.0
    sync_qber: float = 0.0
    secure_detection_fraction: float = 0.0
    authentication_cost: float = 0.0
    effective_secure_key_rate: float = 0.0
    final_secure_key_rate: float = 0.0
    pat_factor: float = 0.0
    error_correction_efficiency: float = 0.0
    final_key_utilization: float = 0.0
    tx_half_fov_mrad: float = 0.0
    rx_half_fov_mrad: float = 0.0
    error_correction_factor: float = 1.16
    binary_entropy: float = 0.0
    noise_qber: float = 0.0
    polarization_rotation_deg: float = 0.0

    polarization_visibility: float = 1.0

    polarization_loss_dB: float = 0.0

    polarization_qber: float = 0.0

    tracking_qber: float = 0.0

    # =========================================================
    # TRACKING OUTPUTS
    # =========================================================
    ship_los_jitter_urad: float = 0.0
    tracking_error_urad: float = 0.0
    lock_probability: float = 0.0
    tracking_probability: float = 0.0

    fsm_residual_error_urad: float = 0.0
    fsm_tracking_efficiency: float = 0.0
    gimbal_tracking_error_urad: float = 0.0
    gimbal_azimuth_deg: float = 0.0
    gimbal_elevation_deg: float = 0.0
    gimbal_rate_deg_s: float = 0.0
    gimbal_acceleration_deg_s2: float = 0.0
    gimbal_bandwidth_Hz: float = 0.0

    acquisition_probability: float = 0.0
    fsm_stroke_urad: float = 0.0
    # Tracking efficiencies

    gimbal_tracking_efficiency: float = 0.0
    tracking_wavelength_nm: float = 850.0
    quantum_wavelength_nm: float = 1550.0

    # =====================================
    # LAND / SEA ANALYSIS
    # =====================================

    land_percentage: float = 0.0

    sea_percentage: float = 0.0

    coastal_path: bool = False

    dominant_surface: str = "Unknown"

    # =========================================================
    # DESIGN OUTPUTS
    # =========================================================
    recommended_tx_aperture_mm: float = 0.0
    recommended_rx_aperture_mm: float = 0.0
    recommended_divergence_mrad: float = 0.0
    predicted_availability_percent: float = 0.0

    link_margin_dB: float = 0.0
    availability_day_percent: float = 0.0
    availability_night_percent: float = 0.0
    target_qber: float = 0.02

    target_secure_key_rate_bps: float = 1e6

    target_link_availability: float = 0.95

    # =========================================================
    # EXTENDED PROTOCOL INPUTS & OUTPUTS
    # =========================================================

    # Common Security Inputs
    basis_probability_z: float = 0.5
    basis_probability_x: float = 0.5
    authentication_cost_bits: float = 1e5
    finite_key_block_size: int = 1000000

    # Common Derived Outputs
    background_detection_probability: float = 0.0
    dark_detection_probability: float = 0.0
    sift_factor: float = 0.5
    error_correction_leakage: float = 0.0
    privacy_amplification_loss: float = 0.0

    # Decoy BB84 Inputs
    weak_decoy_intensity: float = 0.1
    vacuum_decoy_intensity: float = 0.0

    signal_probability: float = 0.8
    weak_decoy_probability: float = 0.15
    vacuum_probability: float = 0.05

    # Decoy Outputs
    signal_gain: float = 0.0
    weak_gain: float = 0.0
    vacuum_gain: float = 0.0

    signal_qber: float = 0.0
    weak_qber: float = 0.0

    single_photon_yield: float = 0.0
    single_photon_error_rate: float = 0.0

    multi_photon_fraction: float = 0.0

    # B92 Inputs
    state_overlap_angle_deg: float = 45.0

    # B92 Outputs
    conclusive_probability: float = 0.0
    eve_information: float = 0.0
    pair_generation_rate_mhz: float = 10.0

    @property
    def pair_generation_rate_hz(self) -> float:
        return self.pair_generation_rate_mhz * 1e6

    @pair_generation_rate_hz.setter
    def pair_generation_rate_hz(self, val: float):
        self.pair_generation_rate_mhz = val / 1e6

    # E91 Inputs
    coincidence_window_ns: float = 1.0
    coincidence_efficiency: float = 1.0

    alice_basis_probability: float = 0.5
    bob_basis_probability: float = 0.5

    bell_basis_angles: list = field(default_factory=lambda: [0.0, 45.0, 22.5, 67.5])

    # E91 Outputs
    alice_singles_rate: float = 0.0
    bob_singles_rate: float = 0.0

    coincidence_rate: float = 0.0
    coincidence_visibility: float = 0.0

    # BBM92 Inputs
    entangled_source_brightness: float = 1e7
    pair_production_probability: float = 0.01

    # BBM92 Outputs
    sifted_coincidence_rate: float = 0.0

    # =========================================================
    # INTERNAL DEBUG
    # =========================================================
    debug_message: str = ""
    simulation_status: str = "READY"

    system_health: str = "GOOD"
    simulation_time_sec: float = 0.0

    verifier_text: dict = field(default_factory=dict)
    # =========================================================
    # LISTS / ADVANCED
    # =========================================================
    profile_heights_m: List[float] = field(default_factory=list)

    temperature_profile_C: List[float] = field(default_factory=list)
    path_distance_m: List[float] = field(default_factory=list)

    beam_height_profile_m: List[float] = field(default_factory=list)

    earth_curvature_profile_m: List[float] = field(default_factory=list)
    slice_count: int = 0
    slice_accuracy: str = "Medium"
    # Slice constraints
    minimum_slice_length_limit_m: float = 100.0
    maximum_slice_length_limit_m: float = 1000.0
    maximum_height_difference_m: float = 1.0
    maximum_slice_count: int = 100
    number_of_slices: int = 50
    adaptive_slicing: bool = True
    propagation_type: str = ""

    propagation_direction: str = ""

    minimum_slice_length_m: float = 10.0
    tx_surface_type: str = ""

    rx_surface_type: str = ""
    # =========================================================
    # TERRAIN OUTPUTS
    # =========================================================

    terrain_elevation_m: float = 0.0
    average_slice_length_m: float = 0.0
    average_ground_height_m: float = 0.0

    maximum_clearance_m: float = 0.0

    link_blocked: bool = False

    surface_elevation_m: float = 0.0

    surface_roughness_m: float = 0.0

    vegetation_height_m: float = 0.0

    bathymetry_depth_m: float = 0.0

    maximum_slice_length_m: float = 1000.0

    slice_generation_method: str = "Uniform"

    slice_statistics: Dict = field(default_factory=dict)

    slice_boundaries_m: List[float] = field(default_factory=list)
    slice_centers_m: List[float] = field(default_factory=list)

    slice_lengths_m: List[float] = field(default_factory=list)

    humidity_profile_pct: List[float] = field(default_factory=list)

    pressure_profile_hPa: List[float] = field(default_factory=list)

    refractivity_profile_N: List[float] = field(default_factory=list)
    modified_refractivity_profile_M: list = field(default_factory=list)
    model_times: Dict = field(default_factory=dict)
    path_distance_profile: list = field(default_factory=list)

    beam_height_profile: list = field(default_factory=list)

    curvature_profile: list = field(default_factory=list)

    modified_refractivity_heights_m: list = field(default_factory=list)
    trade_x: List[float] = field(default_factory=list)
    trade_skr: List[float] = field(default_factory=list)
    trade_qber: List[float] = field(default_factory=list)

    mc_results: Dict = field(default_factory=dict)
    settings: Dict = field(default_factory=dict)
    # =========================================================
    # ADAPTIVE PROPAGATION SLICES (v0.4)
    # =========================================================

    propagation_slices: List[PropagationSlice] = field(default_factory=list)
