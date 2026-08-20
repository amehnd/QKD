from core.model import Model
from models.terrain_provider import TerrainProvider

print("TERRAIN DATABASE FILE =", __file__)


class TerrainDatabaseModel(Model):

    name = "Terrain Database"

    description = "Loads terrain and bathymetry data for propagation slices"

    version = "0.4"

    inputs = [
        "tx_latitude_deg",
        "tx_longitude_deg",
        "rx_latitude_deg",
        "rx_longitude_deg",
        "propagation_slices",
    ]
    outputs = [
        "ground_height_m",
        "terrain_slope_deg",
        "terrain_aspect_deg",
        "surface_type",
        "surface_roughness_m",
        "vegetation_height_m",
        "bathymetry_depth_m",
    ]

    def validate(self, state):

        if not state.propagation_slices:

            raise ValueError("Adaptive slicing must run first.")

        return True

    def execute(self, state):
        print("STATE TERRAIN TYPE =", state.terrain_type)
        print(">>> TERRAIN DATABASE MODEL EXECUTED <<<")

        provider = TerrainProvider()

        state.terrain_database = provider.database_name

        for s in state.propagation_slices:
            s.ground_height_m = provider.get_elevation(
                s.latitude_deg, s.longitude_deg, s.surface_type, state.terrain_type
            )
            s.surface_elevation_m = s.ground_height_m
            s.mean_sea_level_height_m = s.surface_elevation_m

            s.surface_roughness_m = provider.get_surface_roughness(
                s.surface_type,
                state.terrain_type,
            )

            s.vegetation_height_m = provider.get_vegetation_height(
                s.surface_type,
                state.terrain_type,
            )

            s.bathymetry_depth_m = provider.get_bathymetry_depth(
                s.surface_type,
                state.terrain_type,
            )

            if s.surface_type == "Sea":
                s.terrain_category = "Ocean"

            elif state.terrain_type == "Auto":
                s.terrain_category = "Plain"

            else:
                s.terrain_category = state.terrain_type

            # ----------------------------
            # Terrain geometry
            # ----------------------------

            s.terrain_slope_deg = provider.get_slope(s.latitude_deg, s.longitude_deg)

            s.terrain_aspect_deg = provider.get_aspect(s.latitude_deg, s.longitude_deg)
            s.dem_source = state.terrain_database
            s.database_name = state.terrain_database

            # ----------------------------
            # LOS clearance
            # ----------------------------
            print(
                f"DB Slice {s.slice_id}: "
                f"Ground={s.ground_height_m:.3f}, "
                f"Surface={s.surface_type}"
            )

            s.clearance_above_ground_m = s.beam_height_m - s.ground_height_m
            s.clearance_ratio = s.clearance_above_ground_m / max(
                s.clearance_above_ground_m + s.ground_height_m, 1e-6
            )

            s.notes = f"{s.surface_type} " f"Ground={s.ground_height_m:.1f} m"

        state.average_ground_height_m = sum(
            s.ground_height_m for s in state.propagation_slices
        ) / max(len(state.propagation_slices), 1)
        state.average_terrain_slope_deg = sum(
            s.terrain_slope_deg for s in state.propagation_slices
        ) / max(len(state.propagation_slices), 1)
        state.average_bathymetry_depth_m = sum(
            s.bathymetry_depth_m for s in state.propagation_slices
        ) / max(len(state.propagation_slices), 1)

        # =====================================
        # PATH TERRAIN OUTPUTS
        # =====================================

        state.terrain_elevation_m = state.average_ground_height_m

        state.surface_elevation_m = state.average_ground_height_m

        state.surface_roughness_m = sum(
            s.surface_roughness_m for s in state.propagation_slices
        ) / max(len(state.propagation_slices), 1)

        state.vegetation_height_m = sum(
            s.vegetation_height_m for s in state.propagation_slices
        ) / max(len(state.propagation_slices), 1)

        state.bathymetry_depth_m = sum(
            s.bathymetry_depth_m for s in state.propagation_slices
        ) / max(len(state.propagation_slices), 1)
        print()
        print("===== TERRAIN DATABASE =====")
        print("Slices :", len(state.propagation_slices))
        print("Database :", state.terrain_database)
        print("Average Ground Height :", state.average_ground_height_m)
        print("Average Terrain Slope :", state.average_terrain_slope_deg)
        print("Average Bathymetry    :", state.average_bathymetry_depth_m)
        land = sum(1 for s in state.propagation_slices if s.surface_type == "Land")

        sea = len(state.propagation_slices) - land

        print("Land Slices :", land)
        print("Sea Slices  :", sea)
        print("============================")
        print()
        state.terrain_database_name = state.terrain_database

        state.dem_loaded = True

        state.total_land_slices = land

        state.total_sea_slices = sea
