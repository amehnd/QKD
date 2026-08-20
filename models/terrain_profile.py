import math

from core.model import Model


class TerrainProfileModel(Model):

    name = "Terrain Profile"

    description = "Terrain and bathymetry profile along slant propagation path"

    version = "0.4"
    inputs = [
        "tx_latitude_deg",
        "tx_longitude_deg",
        "rx_latitude_deg",
        "rx_longitude_deg",
        "tx_height_msl_m",
        "rx_height_msl_m",
        "propagation_slices",
    ]
    outputs = ["lowest_los_height_m", "minimum_clearance_m", "ground_distance_km"]

    def validate(self, state):

        if not state.propagation_slices:

            raise ValueError("Adaptive slicing must run before Terrain Profile.")

        return True

    def execute(self, state):

        wavelength_m = getattr(state, "wavelength_m", 1550e-9)
        distance_m = getattr(state, "distance_m", state.link_distance_km * 1000)
        
        lowest_clearance = float("inf")
        lowest_slice = None
        state.profile_heights_m.clear()
        state.path_distance_profile.clear()
        
        veg_height = getattr(state, "vegetation_height_m", 0.0)
        roughness = getattr(state, "surface_roughness_m", 0.0)
        
        min_fresnel_clearance_pct = float("inf")

        for s in state.propagation_slices:
            s.surface_elevation_m = s.ground_height_m + veg_height + roughness
            s.clearance_above_ground_m = s.beam_height_m - s.surface_elevation_m

            s.is_blocked = s.clearance_above_ground_m <= 0
            s.los = s.clearance_above_ground_m > 0
            
            d1 = s.center_m
            d2 = max(distance_m - d1, 1.0)
            if d1 > 0 and d2 > 0:
                r_f = math.sqrt((wavelength_m * d1 * d2) / max(d1 + d2, 1.0))
                s.fresnel_radius_m = r_f
                fresnel_pct = (s.clearance_above_ground_m / r_f) * 100.0
                min_fresnel_clearance_pct = min(min_fresnel_clearance_pct, fresnel_pct)
            
            state.profile_heights_m.append(s.surface_elevation_m)
            state.path_distance_profile.append(s.ground_distance_m)
            
            if s.clearance_above_ground_m < lowest_clearance:
                lowest_clearance = s.clearance_above_ground_m
                lowest_slice = s

        state.fresnel_clearance_pct = min_fresnel_clearance_pct if min_fresnel_clearance_pct != float("inf") else 100.0
        
        # Save bottleneck slice for verifier
        bottleneck_fresnel_slice = None
        for s in state.propagation_slices:
            if s.clearance_above_ground_m > 0 and s.fresnel_radius_m > 0:
                if abs((s.clearance_above_ground_m / s.fresnel_radius_m) * 100.0 - state.fresnel_clearance_pct) < 1e-4:
                    bottleneck_fresnel_slice = s
                    break

        if lowest_slice:
            state.minimum_clearance_m = lowest_slice.clearance_above_ground_m
            state.lowest_los_height_m = lowest_slice.beam_height_m
            state.lowest_los_distance_m = lowest_slice.center_m
            
        state.average_ground_height_m = sum(
            s.ground_height_m for s in state.propagation_slices
        ) / max(len(state.propagation_slices), 1)

        state.terrain_height_variation_m = max(
            s.ground_height_m for s in state.propagation_slices
        ) - min(s.ground_height_m for s in state.propagation_slices)

        state.minimum_ground_height_m = min(
            s.ground_height_m for s in state.propagation_slices
        )

        state.maximum_ground_height_m = max(
            s.ground_height_m for s in state.propagation_slices
        )

        state.maximum_clearance_m = max(
            s.clearance_above_ground_m for s in state.propagation_slices
        )
        state.link_blocked = any(s.is_blocked for s in state.propagation_slices)

        state.ground_distance_km = state.link_distance_km
        
        highest_slice = max(state.propagation_slices, key=lambda s: s.beam_height_m, default=None)
        if highest_slice:
            state.highest_los_height_m = highest_slice.beam_height_m
            state.highest_los_distance_m = highest_slice.center_m
        else:
            state.highest_los_height_m = 0.0
            state.highest_los_distance_m = 0.0

        print()
        print("===== TERRAIN PROFILE =====")
        print("Slices =", len(state.propagation_slices))
        print("Lowest Clearance =", state.minimum_clearance_m)
        print("Lowest LOS Height =", state.lowest_los_height_m)
        print("Lowest LOS Distance =", state.lowest_los_distance_m)
        print("===========================")
        print()
        print("Link Blocked =", state.link_blocked)
        print("Maximum Clearance =", state.maximum_clearance_m)
        print("Minimum Ground Height =", state.minimum_ground_height_m)
        print("Maximum Ground Height =", state.maximum_ground_height_m)

        # ==========================================
        # VERIFIER TEXT GENERATION
        # ==========================================
        
        state.terrain_elevation_m = state.average_ground_height_m
        state.surface_elevation_m = state.terrain_elevation_m + veg_height + roughness

        state.verifier_text["terrain"] = f"""
**Dominant Surface**
Surface = {getattr(state, 'dominant_surface', '')}

**Land Percentage**
%_land = {getattr(state, 'land_percentage', 0.0):.2f} %

**Sea Percentage**
%_sea = {getattr(state, 'sea_percentage', 0.0):.2f} %

**Coastal Path**
Coastal = {getattr(state, 'coastal_path', '')}

**Terrain Elevation**
h_terrain = {state.terrain_elevation_m:.4f} m

**Surface Elevation**
h_surf = h_terrain + h_veg + R_z = {state.terrain_elevation_m:.4f} + {veg_height:.4f} + {roughness:.4f} = {state.surface_elevation_m:.4f} m

**Lowest LOS Height**
h_LOS,min = min(h_beam,i) = {getattr(state, 'lowest_los_height_m', 0.0):.4f} m

**Lowest LOS Distance**
d_LOS,min = argmin_d(h_beam,i) = {getattr(state, 'lowest_los_distance_m', 0.0):.4f} m

**Highest LOS Height**
h_LOS,max = max(h_beam,i) = {getattr(state, 'highest_los_height_m', 0.0):.4f} m

**Highest LOS Distance**
d_LOS,max = argmax_d(h_beam,i) = {getattr(state, 'highest_los_distance_m', 0.0):.4f} m

**Minimum Clearance**
Clearance_min = min(h_beam,i - h_surf,i) = {state.minimum_clearance_m:.4f} m

**Maximum Clearance**
Clearance_max = max(h_beam,i - h_surf,i) = {state.maximum_clearance_m:.4f} m

**Average Ground Height**
h_ground,avg = (1/N) · Σ h_ground,i = {state.average_ground_height_m:.4f} m
"""

        # Append Fresnel Clearance to Geometry verifier
        if "geo" in state.verifier_text and bottleneck_fresnel_slice:
            s = bottleneck_fresnel_slice
            state.verifier_text["geo"] += f"""
**Fresnel Clearance** (Bottleneck at d = {s.center_m:.2f} m)
r_F,min = √(λ · d₁ · d₂ / (d₁ + d₂)) = √({wavelength_m:.2e} · {s.center_m:.2f} · {max(distance_m - s.center_m, 1.0):.2f} / {distance_m:.2f}) = {s.fresnel_radius_m:.4f} m
h_LOS,min = {s.line_of_sight_height_m:.4f} m
h_terrain,min = h_ground + h_veg + R_z = {s.ground_height_m:.4f} + {veg_height:.4f} + {roughness:.4f} = {s.surface_elevation_m:.4f} m
Clearance_F = (h_LOS,min - h_terrain,min) / r_F,min · 100 = ({s.clearance_above_ground_m:.4f} / {s.fresnel_radius_m:.4f}) · 100 = {state.fresnel_clearance_pct:.2f} %
"""
        elif "geo" in state.verifier_text:
            state.verifier_text["geo"] += f"""
**Fresnel Clearance**
Clearance_F = 100.00 % (No bottleneck found)
"""
