import math

from core.model import Model


class SkyRadianceModel(Model):

    name = "SkyRadiance"

    description = "Solar and lunar sky radiance"

    version = "0.3"
    inputs = [
        "solar_flux_W_m2",
        "solar_elevation_deg",
        "is_daylight",
        "moon_phase_percent",
        "atmospheric_transmission",
    ]

    outputs = ["clear_sky_radiance_W_sr_m2"]

    def validate(self, state):

        if not state.propagation_slices:

            raise ValueError("Atmospheric Loss must run before Sky Radiance.")

        return True

    def execute(self, state):

        # ==========================================
        # Solar Background
        # ==========================================

        transmission = getattr(state, "atmospheric_transmission", 1.0)

        eff_temp = getattr(state, "effective_temperature_C", (getattr(state, "tx_temperature_C", 25.0) + getattr(state, "rx_temperature_C", 25.0)) / 2.0)
        temp_factor = 1.0 + 0.002 * (eff_temp - 15.0)

        if state.is_daylight:
            solar_background = state.solar_flux_W_m2 * 5e-9 * temp_factor
        else:
            solar_background = 0.0

        # ==========================================
        # Moon Background
        # ==========================================

        moon_phase = getattr(state, "moon_phase_percent", 50.0) / 100.0

        moon_background = 5e-8 * moon_phase

        # ==========================================
        # Natural Sky Background
        # ==========================================

        sky_background = 1e-8

        # ==========================================
        # Total Sky Radiance
        # ==========================================

        sky_radiance = solar_background + moon_background + sky_background

        # Store global values
        state.solar_background_W_sr_m2 = solar_background
        state.moon_background_W_sr_m2 = moon_background
        state.sky_background_W_sr_m2 = sky_background
        state.clear_sky_radiance_W_sr_m2 = sky_radiance
        print()
        print("SKY RADIANCE DEBUG")
        print("------------------")
        print("Solar Flux =", state.solar_flux_W_m2)
        print("Atmospheric Transmission =", transmission)

        print("Solar Background =", solar_background)
        print("Moon Background =", moon_background)
        print("Sky Background =", sky_background)
        print("Total Sky Radiance =", sky_radiance)
        # ======================================
        # v0.4 Propagation Slice Sky Radiance
        # ======================================

        if state.propagation_slices:

            n = len(state.propagation_slices)

            for s in state.propagation_slices:

                slice_transmission = getattr(
                    s,
                    "cumulative_atmospheric_transmission",
                    getattr(s, "path_transmission", transmission),
                )
                s.solar_background_W_sr_m2 = solar_background * slice_transmission

                s.moon_background_W_sr_m2 = moon_background * slice_transmission

                s.sky_background_W_sr_m2 = sky_background * slice_transmission

                slice_total = (
                    s.solar_background_W_sr_m2
                    + s.moon_background_W_sr_m2
                    + s.sky_background_W_sr_m2
                )
                s.clear_sky_radiance_W_sr_m2 = slice_total
                s.total_background_radiance_W_sr_m2 = slice_total

            state.clear_sky_radiance_W_sr_m2 = state.propagation_slices[
                -1
            ].clear_sky_radiance_W_sr_m2
            print()
            print("===== SKY RADIANCE → SLICES =====")
            print("Slices Updated :", n)
            print("=================================")
            print()
        state.debug_message = "SkyRadiance completed"

        print()

        print("Sky Radiance:", sky_radiance, "W/sr/m²")
