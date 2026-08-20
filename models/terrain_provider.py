import math
import random


class TerrainProvider:

    def __init__(self):

        self.database_name = "Statistical Terrain Generator"

        random.seed(42)

        self.terrain = {
            "Sea": {
                "mean_height": 0.0,
                "height_std": 0.0,
                "roughness": 0.003,
                "vegetation": 0.0,
                "bathymetry": -20.0,
            },
            "Coastal": {
                "mean_height": 8.0,
                "height_std": 5.0,
                "roughness": 0.03,
                "vegetation": 1.0,
                "bathymetry": -5.0,
            },
            "Plain": {
                "mean_height": 25.0,
                "height_std": 10.0,
                "roughness": 0.08,
                "vegetation": 0.5,
                "bathymetry": 0.0,
            },
            "Rural": {
                "mean_height": 45.0,
                "height_std": 20.0,
                "roughness": 0.10,
                "vegetation": 2.0,
                "bathymetry": 0.0,
            },
            "Forest": {
                "mean_height": 80.0,
                "height_std": 30.0,
                "roughness": 0.40,
                "vegetation": 15.0,
                "bathymetry": 0.0,
            },
            "Hilly": {
                "mean_height": 200.0,
                "height_std": 80.0,
                "roughness": 0.20,
                "vegetation": 3.0,
                "bathymetry": 0.0,
            },
            "Mountain": {
                "mean_height": 1200.0,
                "height_std": 300.0,
                "roughness": 0.30,
                "vegetation": 1.0,
                "bathymetry": 0.0,
            },
        }

    # -------------------------------------------------
    # Elevation
    # -------------------------------------------------

    def get_elevation(
        self,
        latitude_deg,
        longitude_deg,
        surface_type,
        terrain_type="Auto",
    ):

        if surface_type == "Sea":
            terrain = "Sea"

        elif terrain_type == "Auto":
            terrain = "Plain"

        else:
            terrain = terrain_type

        p = self.terrain[terrain]

        if terrain == "Sea":
            return 0.0
        x = latitude_deg * 111000.0
        y = longitude_deg * 111000.0

        large_scale = 0.60 * p["height_std"] * math.sin(x / 4500.0)

        medium_scale = 0.30 * p["height_std"] * math.cos(y / 1800.0)

        small_scale = 0.10 * p["height_std"] * math.sin((x + y) / 700.0)

        elevation = p["mean_height"] + large_scale + medium_scale + small_scale

        return max(elevation, 0.0)

    # -------------------------------------------------
    # Terrain slope
    # -------------------------------------------------

    def get_slope(
        self,
        latitude_deg,
        longitude_deg,
    ):

        step = 0.0001

        h1 = self.get_elevation(
            latitude_deg,
            longitude_deg,
            "Land",
        )

        h2 = self.get_elevation(
            latitude_deg + step,
            longitude_deg,
            "Land",
        )

        dz = h2 - h1

        dx = step * 111000.0

        return math.degrees(math.atan2(dz, dx))

    # -------------------------------------------------
    # Terrain aspect
    # -------------------------------------------------

    def get_aspect(
        self,
        latitude_deg,
        longitude_deg,
    ):

        step = 0.0001

        hE = self.get_elevation(
            latitude_deg,
            longitude_deg + step,
            "Land",
        )

        hW = self.get_elevation(
            latitude_deg,
            longitude_deg - step,
            "Land",
        )

        hN = self.get_elevation(
            latitude_deg + step,
            longitude_deg,
            "Land",
        )

        hS = self.get_elevation(
            latitude_deg - step,
            longitude_deg,
            "Land",
        )

        dzdx = (hE - hW) / (2 * step)
        dzdy = (hN - hS) / (2 * step)

        aspect = math.degrees(math.atan2(dzdx, dzdy))

        if aspect < 0:
            aspect += 360

        return aspect

    # -------------------------------------------------
    # Surface roughness
    # -------------------------------------------------

    def get_surface_roughness(
        self,
        surface_type,
        terrain_type="Auto",
    ):
        print(
            "ROUGHNESS:",
            surface_type,
            terrain_type,
        )

        if surface_type == "Sea":
            return self.terrain["Sea"]["roughness"]

        if terrain_type == "Auto":
            terrain_type = "Plain"

        return self.terrain[terrain_type]["roughness"]

    # -------------------------------------------------
    # Vegetation
    # -------------------------------------------------

    def get_vegetation_height(
        self,
        surface_type,
        terrain_type="Auto",
    ):

        if surface_type == "Sea":
            return self.terrain["Sea"]["vegetation"]

        if terrain_type == "Auto":
            terrain_type = "Plain"

        return self.terrain[terrain_type]["vegetation"]

    # -------------------------------------------------
    # Bathymetry
    # -------------------------------------------------

    def get_bathymetry_depth(
        self,
        surface_type,
        terrain_type="Auto",
    ):

        if surface_type == "Sea":
            return self.terrain["Sea"]["bathymetry"]

        return self.terrain["Plain"]["bathymetry"]
