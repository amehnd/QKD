"""
settings_manager.py

Loads and saves simulator settings.
"""

from pathlib import Path
import yaml


class SettingsManager:

    DEFAULT_SETTINGS = {
        "slice_modes": {
            "Low": {
                "min_delta_s_m": 500.0,
                "max_delta_s_m": 5000.0,
                "max_delta_h_m": 2.0,
                "max_slices": 20.0,
            },
            "Medium": {
                "min_delta_s_m": 250.0,
                "max_delta_s_m": 2000.0,
                "max_delta_h_m": 1.0,
                "max_slices": 50.0,
            },
            "High": {
                "min_delta_s_m": 100.0,
                "max_delta_s_m": 1000.0,
                "max_delta_h_m": 0.5,
                "max_slices": 100.0,
            },
            "Research": {
                "min_delta_s_m": 25.0,
                "max_delta_s_m": 500.0,
                "max_delta_h_m": 0.1,
                "max_slices": 50.0,
            },
        },
        "detector_defaults": {
            "SPAD": {"qe": 0.20, "dcr_cps": 1000.0, "dead_time_ns": 200.0},
            "SNSPD": {"qe": 0.90, "dcr_cps": 10.0, "dead_time_ns": 20.0},
            "APD": {"qe": 0.45, "dcr_cps": 5000.0, "dead_time_ns": 30.0},
            "PMT": {"qe": 0.30, "dcr_cps": 500.0, "dead_time_ns": 10.0},
            "TES": {"qe": 0.98, "dcr_cps": 0.1, "dead_time_ns": 1000.0},
        },
        "terrain_defaults": {
            "surface_roughness_m": 0.0,
            "vegetation_height_m": 0.0,
            "bathymetry_depth_m": 0.0,
        },
        "tracking_defaults": {
            "gimbal_bandwidth_hz": 10.0,
            "fsm_bandwidth_hz": 200.0,
            "control_loop_bandwidth_hz": 500.0,
            "sampling_frequency_hz": 1000.0,
            "encoder_resolution_urad": 1.0,
            "pointing_accuracy_urad": 2.0,
            "servo_response_ms": 2.0,
            "acquisition_uncertainty_urad": 10.0,
            "tracking_jitter_urad": 1.0,
            "stabilization_performance_pct": 98.0,
        },
    }

    def __init__(self):

        self.settings_file = Path(__file__).parent.parent / "config" / "settings.yaml"

    def load(self):

        with open(self.settings_file, "r") as f:
            loaded = yaml.safe_load(f) or {}
            
            # Merge loaded settings into a copy of defaults
            settings = {}
            for k, default_v in self.DEFAULT_SETTINGS.items():
                if isinstance(default_v, dict):
                    settings[k] = dict(default_v)
                    if k in loaded and isinstance(loaded[k], dict):
                        settings[k].update(loaded[k])
                else:
                    settings[k] = loaded.get(k, default_v)
                    
            # Add any other top-level keys from loaded
            for k, v in loaded.items():
                if k not in settings:
                    settings[k] = v
                    
            return settings

    def save(self, settings):

        with open(self.settings_file, "w") as f:

            yaml.safe_dump(settings, f, sort_keys=False)

    def restore_defaults(self):

        self.save(self.DEFAULT_SETTINGS)
