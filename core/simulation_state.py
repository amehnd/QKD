"""
SimulationState
Central container for all QKD / FSO simulation parameters and results
"""


class SimulationState:

    def __init__(self):

        self.verifier_text = {}

        # =========================
        # Mission parameters
        # =========================
        self.link_distance_km = 0.0
        self.tx_height_msl_m = 0.0
        self.rx_height_msl_m = 0.0

        # =========================
        # Optics parameters
        # =========================
        self.wavelength_nm = 0.0
        self.tx_aperture_dia_mm = 0.0
        self.rx_aperture_mm = 0.0
        self.tx_beam_divergence_mrad = 0.0
        self.detector_efficiency = 0.0
        self.mean_photon_number = 0.5

        # =========================
        # Environment parameters
        # =========================
        self.temperature_C = 0.0
        self.relative_humidity_pct = 0.0
        self.visibility_km = 0.0
        self.wind_speed_m_s = 0.0
        self.rain_rate_mm_hr = 0.0

        # =========================
        # Channel losses (dB)
        # =========================
        self.geometric_loss_dB = 0.0
        self.atmospheric_loss_dB = 0.0
        self.scintillation_loss_dB = 0.0
        self.pointing_loss_dB = 0.0
        self.optical_loss_dB = 0.0
        self.total_loss_dB = 0.0

        # =========================
        # Link budget outputs
        # =========================
        self.link_budget_dB = 0.0
        self.channel_efficiency = 1e-3
        self.capture_fraction = 1e-3

        # =========================
        # Detection
        # =========================
        self.signal_count_rate = 0.0
        self.detection_probability = 0.0

        # =========================
        # QKD outputs
        # =========================
        self.raw_key_rate = 0.0
        self.sifted_key_rate = 0.0
        self.skr_bps = 0.0
        self.qber = 0.0
        self.secret_fraction = 0.0

        # =========================
        # Error / noise parameters
        # =========================
        self.polarization_error_rate = 0.01
