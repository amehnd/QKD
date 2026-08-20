"""
adaptive_slicing.py

Adaptive Path Slicing Engine

FSO/QKD Maritime Simulator v0.4

Generates adaptive propagation slices.
"""

from core.model import Model
from core.state import PropagationSlice
from core.settings_manager import SettingsManager


class AdaptiveSlicingModel(Model):

    name = "Adaptive Slicing"

    description = "Generates adaptive propagation slices"

    def beam_height(self, state, distance_m):
        """
        Beam height above mean sea level
        including Earth curvature.
        """

        total = state.link_distance_km * 1000.0

        fraction = distance_m / max(total, 1e-9)

        # Straight LOS
        los_height = (
            state.tx_height_msl_m
            + (state.rx_height_msl_m - state.tx_height_msl_m) * fraction
        )

        # Earth curvature
        if state.effective_earth_radius_m > 0:
            Re = state.effective_earth_radius_m
        else:
            Re = state.earth_radius_m * state.effective_earth_radius_factor
        curvature_drop = (distance_m * (total - distance_m)) / (2.0 * Re)

        return los_height - curvature_drop

    def refine_slice(self, state, start, end):

        distance = state.link_distance_km * 1000.0

        length = end - start
        # ---------------------------------------
        # Emergency recursion stop
        # Prevent infinite subdivisionf
        # ---------------------------------------

        if length <= 0.1:

            s = PropagationSlice()

            s.start_m = start
            s.end_m = end
            s.center_m = (start + end) / 2.0
            s.length_m = length

            start_beam = self.beam_height(state, start)
            end_beam = self.beam_height(state, end)

            s.beam_height_m = self.beam_height(state, s.center_m)

            s.beam_start_height_m = start_beam
            s.beam_end_height_m = end_beam
            s.height_change_m = abs(end_beam - start_beam)

            s.maximum_allowed_height_difference_m = state.maximum_height_difference_m

            state.propagation_slices.append(s)

            return

        start_beam = self.beam_height(state, start)
        end_beam = self.beam_height(state, end)

        height_change = abs(end_beam - start_beam)

        mid = (start + end) / 2.0

        allowed_height = state.maximum_height_difference_m
        min_length = state.minimum_slice_length_limit_m
        max_length = state.maximum_slice_length_limit_m

        # ---------------------------------------
        # Decide whether to split
        # ---------------------------------------

        # ---------------------------------------
        # Decide whether to split
        # ---------------------------------------

        if length <= min_length:

            # Cannot subdivide further.
            need_split = False

        elif length > max_length:

            need_split = True

        elif height_change > allowed_height:

            need_split = True

        else:

            need_split = False
        # ---------------------------------------
        # Accept slice
        # ---------------------------------------

        if not need_split:

            s = PropagationSlice()

            s.start_m = start
            s.end_m = end
            s.center_m = mid

            s.length_m = length

            s.beam_height_m = self.beam_height(state, mid)

            s.beam_start_height_m = start_beam
            s.beam_end_height_m = end_beam

            s.height_gradient = (end_beam - start_beam) / max(length, 1.0)

            s.height_change_m = height_change

            s.maximum_allowed_height_difference_m = allowed_height

            state.propagation_slices.append(s)

            return

        mid = (start + end) / 2.0

        self.refine_slice(state, start, mid)

        self.refine_slice(state, mid, end)

    def execute(self, state):

        # =====================================
        # CLEAR OLD SLICES
        # =====================================

        state.propagation_slices.clear()

        # =====================================
        # INPUTS
        # =====================================

        distance = state.link_distance_km * 1000.0

        print("distance_m =", state.distance_m)
        print("link_distance_km =", state.link_distance_km)
        print("distance used =", distance)
        print("SLICER distance =", distance)

        if distance <= 0:
            return

        # Temporary fixed number of slices
        settings = SettingsManager().load()
        print("state.slice_accuracy =", repr(state.slice_accuracy))
        print("Available modes =", settings["slice_modes"].keys())

        slice_settings = settings["slice_modes"][state.slice_accuracy]
        print()
        print("===== SETTINGS LOADED =====")
        print(slice_settings)
        print("===========================")
        print()
        accuracy = state.slice_accuracy

        state.minimum_slice_length_limit_m = slice_settings["min_delta_s_m"]

        state.maximum_slice_length_limit_m = slice_settings["max_delta_s_m"]

        state.maximum_height_difference_m = slice_settings["max_delta_h_m"]

        state.maximum_slice_count = int(slice_settings["max_slices"])
        # =====================================
        # GENERATE SLICES
        # =====================================
        # =====================================
        # Find lowest LOS point
        # =====================================

        # =====================================
        # Generate slices respecting maximum slice count
        # =====================================

        max_iterations = 20
        previous_count = None

        for _ in range(max_iterations):

            state.propagation_slices.clear()

            self.refine_slice(state, 0.0, distance)

            current_count = len(state.propagation_slices)

            if current_count <= state.maximum_slice_count:
                break

            # Stop if increasing Δs is no longer reducing slice count
            if previous_count == current_count:

                print("Δh criterion prevents further reduction in slice count.")

                break

            previous_count = current_count

            # ---------------------------------------
            # Adjust maximum Δs according to
            # generated slice count
            # ---------------------------------------

            factor = current_count / state.maximum_slice_count

            # Prevent tiny adjustments
            factor = max(factor, 1.10)

            state.maximum_slice_length_limit_m *= factor

            print(
                "Increasing maximum slice length to",
                state.maximum_slice_length_limit_m,
                "m",
            )
        if len(state.propagation_slices) > state.maximum_slice_count:

            print(
                "Warning: Could not satisfy maximum slice count "
                "because the Δh constraint required further refinement."
            )
        for i, s in enumerate(state.propagation_slices):
            tx_lat = getattr(state, "tx_latitude_deg", 0.0)
            tx_lon = getattr(state, "tx_longitude_deg", 0.0)

            rx_lat = getattr(state, "rx_latitude_deg", tx_lat)
            rx_lon = getattr(state, "rx_longitude_deg", tx_lon)

            fraction = s.center_m / max(distance, 1.0)
            s.path_fraction = fraction

            s.latitude_deg = tx_lat + fraction * (rx_lat - tx_lat)

            s.longitude_deg = tx_lon + fraction * (rx_lon - tx_lon)
            # =====================================
            # Interpolate Environment
            # =====================================

            s.temperature_C = state.tx_temperature_C + fraction * (
                state.rx_temperature_C - state.tx_temperature_C
            )

            s.humidity_pct = state.tx_humidity_pct + fraction * (
                state.rx_humidity_pct - state.tx_humidity_pct
            )

            s.pressure_hPa = state.tx_pressure_hPa + fraction * (
                state.rx_pressure_hPa - state.tx_pressure_hPa
            )

            s.visibility_km = state.tx_visibility_km + fraction * (
                state.rx_visibility_km - state.tx_visibility_km
            )

            s.wind_speed_m_s = state.tx_wind_speed_m_s + fraction * (
                state.rx_wind_speed_m_s - state.tx_wind_speed_m_s
            )

            s.rain_rate_mm_hr = state.tx_rain_rate_mm_hr + fraction * (
                state.rx_rain_rate_mm_hr - state.tx_rain_rate_mm_hr
            )

            s.cloud_cover_percent = state.tx_cloud_cover_percent + fraction * (
                state.rx_cloud_cover_percent - state.tx_cloud_cover_percent
            )
            s.cloud_base_height_m = state.tx_cloud_base_height_m + fraction * (
                state.rx_cloud_base_height_m - state.tx_cloud_base_height_m
            )

            s.aerosol_alpha = state.tx_aerosol_alpha + fraction * (
                state.rx_aerosol_alpha - state.tx_aerosol_alpha
            )

            s.slice_id = i + 1

            s.refinement_level = 0

            s.ground_height_m = 0.0
            s.clearance_above_ground_m = 0.0

            s.surface_type = "Unknown"

        state.slice_count = len(state.propagation_slices)
        state.minimum_slice_length_m = min(s.length_m for s in state.propagation_slices)

        state.maximum_slice_length_m = max(s.length_m for s in state.propagation_slices)

        state.average_slice_length_m = sum(
            s.length_m for s in state.propagation_slices
        ) / max(state.slice_count, 1)
        # =====================================
        # Lowest LOS Point
        # =====================================

        if state.propagation_slices:

            lowest = min(state.propagation_slices, key=lambda s: s.beam_height_m)

            state.lowest_los_height_m = lowest.beam_height_m
            state.minimum_height_above_sea_m = state.lowest_los_height_m
            highest = max(state.propagation_slices, key=lambda s: s.beam_height_m)

            state.highest_los_height_m = highest.beam_height_m
            state.highest_los_distance_m = highest.center_m

            state.lowest_los_distance_m = lowest.center_m

            state.minimum_clearance_m = state.minimum_height_above_sea_m
        print("Generated", len(state.propagation_slices), "slices")
        state.slice_statistics = {
            "count": state.slice_count,
            "total_distance_m": distance,
            "accuracy": accuracy,
        }
        print()
        print("===== ADAPTIVE SLICING =====")
        print("Accuracy :", accuracy)
        print("Slices Generated :", state.slice_count)

        print(
            "Maximum Allowed Height Difference :",
            state.maximum_height_difference_m,
            "m",
        )

        print("Slices Generated :", state.slice_count)
        height_changes = [
            getattr(s, "height_change_m", 0.0) for s in state.propagation_slices
        ]

        print("Largest Slice Height Difference :", max(height_changes))

        print(
            "Average Slice Height Difference :",
            sum(height_changes) / max(len(height_changes), 1),
        )

        print("============================")
        print()

        print("Lowest LOS Height :", state.lowest_los_height_m)

        print("Lowest LOS Distance :", state.lowest_los_distance_m)

        print("Minimum Clearance :", state.minimum_clearance_m)

        # ==========================================
        # VERIFIER TEXT GENERATION
        # ==========================================
        state.verifier_text["slice"] = f"""
Slice Count
N_slices = {state.slice_count}

Slice Accuracy
Accuracy = {state.slice_accuracy}

Slice Generation
Method = {getattr(state, 'slice_generation_method', 'Adaptive')}

Minimum Slice Length
Δs_min = min(Δs_i) = {state.minimum_slice_length_m:.4f}

Maximum Slice Length
Δs_max = max(Δs_i) = {state.maximum_slice_length_m:.4f}

Average Slice Length
Δs_avg = (1 / N_slices) · Σ(Δs_i) = {state.average_slice_length_m:.4f}

Lowest LOS Height
D = L_km · 1000
f = d / max(D, 1e-9)
h_LOS = h_tx + (h_rx - h_tx) · f
drop = d · (D - d) / (2 · R_e)
h_beam = h_LOS - drop
h_LOS,min = min(h_beam,i) = {state.lowest_los_height_m:.4f}

Lowest LOS Distance
d_LOS,min = argmin_d(h_beam,i) = {state.lowest_los_distance_m:.4f}

Highest LOS Height
h_LOS,max = max(h_beam,i) = {getattr(state, 'highest_los_height_m', 0):.4f}

Highest LOS Distance
d_LOS,max = argmax_d(h_beam,i) = {getattr(state, 'highest_los_distance_m', 0):.4f}

Minimum Clearance
h_clear,min = h_LOS,min = {state.minimum_clearance_m:.4f}

Minimum Height Above Sea
h_sea,min = h_LOS,min = {state.minimum_height_above_sea_m:.4f}

Link Blocked
Blocked = (Clearance_min < 0) = {getattr(state, 'link_blocked', False)}
"""
