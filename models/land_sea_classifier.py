"""
land_sea_classifier.py

Land / Sea Path Classification

Version: 0.3
"""

from core.model import Model
from global_land_mask import globe


class LandSeaClassifierModel(Model):

    name = "LandSeaClassifier"

    description = "Computes land and sea path percentages"
    version = "0.4"

    def validate(self, state):

        if not state.propagation_slices:

            raise ValueError("Adaptive slicing must run before LandSeaClassifier.")

        return True

    def execute(self, state):

        # Temporary implementation

        import math

        # ----------------------------
        # Read coordinates
        # ----------------------------

        tx_lat = getattr(state, "tx_latitude_deg", 0.0)
        tx_lon = getattr(state, "tx_longitude_deg", 0.0)

        rx_lat = getattr(state, "rx_latitude_deg", 0.0)
        rx_lon = getattr(state, "rx_longitude_deg", 0.0)
        # =====================================
        # TX / RX SURFACE TYPES
        # =====================================

        state.tx_surface_type = "Land" if globe.is_land(tx_lat, tx_lon) else "Sea"

        state.rx_surface_type = "Land" if globe.is_land(rx_lat, rx_lon) else "Sea"

        print("TX Surface =", state.tx_surface_type)
        print("RX Surface =", state.rx_surface_type)
        # ------------------------------------
        # TX / RX Surface Classification
        # ------------------------------------

        tx_is_land = globe.is_land(tx_lat, tx_lon)
        rx_is_land = globe.is_land(rx_lat, rx_lon)

        state.tx_surface_type = "Land" if tx_is_land else "Sea"
        state.rx_surface_type = "Land" if rx_is_land else "Sea"

        # ----------------------------
        # Generate points along path
        # ----------------------------

        samples = []

        N = 100

        for i in range(N + 1):

            t = i / N

            lat = tx_lat + t * (rx_lat - tx_lat)

            lon = tx_lon + t * (rx_lon - tx_lon)

            samples.append((lat, lon))
            # Store sampled path for future models
        state.path_samples = samples
        # ------------------------------------
        # Placeholder Classification
        # (Will be replaced with real GIS logic)
        # ------------------------------------

        # ----------------------------------------
        # Land / Sea Classification
        # ----------------------------------------

        land_count = 0
        sea_count = 0

        for lat, lon in samples:

            if globe.is_land(lat, lon):

                land_count += 1

            else:

                sea_count += 1

        total = len(samples)

        state.land_percentage = 100.0 * land_count / total
        state.sea_percentage = 100.0 * sea_count / total

        state.coastal_path = land_count > 0 and sea_count > 0

        if state.land_percentage >= state.sea_percentage:

            state.dominant_surface = "Land"

        else:

            state.dominant_surface = "Sea"

        print()
        print("===== LAND / SEA =====")
        print("Land :", state.land_percentage, "%")
        print("Sea  :", state.sea_percentage, "%")
        print("Surface :", state.dominant_surface)
        print("Coastal :", state.coastal_path)
        print("Land Samples =", land_count)
        print("Sea Samples =", sea_count)
        print("======================")

        print(f"Sample Points = {len(samples)}")
        print("First =", samples[0])
        print("Middle =", samples[len(samples) // 2])
        print("Last =", samples[-1])

        # =====================================
        # PROPAGATION SLICE SURFACE TYPE (v0.4)
        # =====================================

        for s in state.propagation_slices:

            # Fraction along the propagation path

            lat = s.latitude_deg
            lon = s.longitude_deg
            is_land = globe.is_land(lat, lon)

            s.is_land = is_land
            s.is_sea = not is_land
            s.coastal = state.coastal_path
            # Overall path percentages
            s.land_percentage = state.land_percentage
            s.sea_percentage = state.sea_percentage

            if is_land:

                s.surface_type = "Land"

                s.terrain_category = "Land"

            else:

                s.surface_type = "Sea"

                s.terrain_category = "Ocean"

            # Height above local surface

            if s.surface_type == "Sea":

                s.surface_height_m = 0.0
                s.height_above_surface_m = max(s.beam_height_m, 0.0)

            else:

                s.surface_height_m = s.ground_height_m
                s.height_above_surface_m = max(s.beam_height_m - s.ground_height_m, 0.0)
        land_slices = sum(
            1 for s in state.propagation_slices if s.surface_type == "Land"
        )

        sea_slices = len(state.propagation_slices) - land_slices

        state.land_slices = land_slices
        state.sea_slices = sea_slices
        state.total_land_slices = land_slices
        state.total_sea_slices = sea_slices

        state.land_fraction = land_slices / max(len(state.propagation_slices), 1)
        state.sea_fraction = sea_slices / max(len(state.propagation_slices), 1)
        state.mixed_surface_path = state.coastal_path

        print()
        print("===== LAND/SEA → SLICES =====")
        print("Slices Updated :", len(state.propagation_slices))
        print("Land Slices    :", land_slices)
        print("Sea Slices     :", sea_slices)
        print("Dominant       :", state.dominant_surface)
        print("Coastal Path   :", state.coastal_path)
        print("=============================")
        print()
        print("TX Surface =", state.tx_surface_type)
        print("RX Surface =", state.rx_surface_type)
