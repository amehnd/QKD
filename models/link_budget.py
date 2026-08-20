"""
link_budget.py

Maritime QKD Optical Link Budget
"""

import math
from core.model import Model


class LinkBudgetModel(Model):

    name = "LinkBudget"
    description = "Optical maritime link budget"
    version = "0.3"

    inputs = [
        "link_distance_km",
        "tx_aperture_mm",
        "rx_aperture_mm",
        "tx_beam_divergence_mrad",
        "wavelength_nm",
        "tx_optical_loss_dB",
        "rx_optical_loss_dB",
        "atmospheric_loss_dB",
        "pointing_loss_dB",
        "scintillation_loss_dB",
    ]

    outputs = [
        "spot_diameter_m",
        "capture_fraction",
        "total_link_loss_dB",
        "channel_efficiency",
    ]

    # --------------------------------------------------
    # Validation
    # --------------------------------------------------

    def validate(self, state):

        if state.link_distance_km <= 0:
            raise ValueError("Invalid range")

        if state.rx_aperture_mm <= 0:
            raise ValueError("Invalid receiver aperture")

        return True

    # --------------------------------------------------
    # Execute
    # --------------------------------------------------

    def execute(self, state):
        current_power = getattr(state, "tx_power_W", 1.0)
        cumulative_transmission = 1.0

        range_m = state.link_distance_km * 1000.0

        rx_radius = state.rx_aperture_mm / 1000.0 / 2.0

        # ==========================================
        # Divergence
        # ==========================================

        # ==========================================
        # Spot Size
        # ==========================================
        spot_diameter = max(getattr(state, "beam_diameter_m", 1e-6), 1e-6)

        spot_diameter = max(spot_diameter, 1e-6)

        # ----------------------------------------
        # Save beam geometry
        # ----------------------------------------

        state.spot_diameter_m = spot_diameter

        # safety normalization (unchanged physics)

        range_m = max(range_m, 1.0)
        rx_radius = max(rx_radius, 1e-3)

        # ==========================================
        # Gaussian Capture Fraction
        # ==========================================
        effective_capture = max(state.effective_capture_fraction, 1e-20)

        geometric_loss_dB = -10.0 * math.log10(effective_capture)
        # ==========================================
        # LOSS COMPONENTS (SAFE FALLBACKS)
        # ==========================================

        tx_optical_loss = getattr(state, "tx_optical_loss_dB", 1.0)

        rx_optical_loss = getattr(state, "rx_optical_loss_dB", 1.0)
        print("\n===== LINK BUDGET =====")
        print("TX Optical Loss =", tx_optical_loss)
        print("RX Optical Loss =", rx_optical_loss)
        # ==========================================
        # TOTAL LOSS
        # ==========================================
        path_loss = 0.0

        path_transmission = 1.0
        propagation_loss = 0.0
        if state.propagation_slices:

            number_of_slices = len(state.propagation_slices)

            total_loss_dB = 0.0

            cumulative_transmission = 1.0

            for s in state.propagation_slices:
                if s.slice_id <= 5:
                    print()
                    print("Slice", s.slice_id)
                    print("Length =", s.length_m)
                    print("Atmos =", s.atmospheric_loss_dB)
                    print("Scint =", s.scintillation_loss_dB)

                slice_loss = (
                    s.atmospheric_loss_dB + s.scintillation_loss_dB + s.pointing_loss_dB
                )
                transmission = 10 ** (-slice_loss / 10.0)

                current_power *= transmission
                current_power = max(current_power, 0.0)

                cumulative_transmission *= transmission

                s.transmission = transmission

                s.cumulative_transmission = cumulative_transmission

                s.optical_power_W = current_power

                print(
                    f"Slice {s.slice_id}: "
                    f"Atm={s.atmospheric_loss_dB:.4f} "
                    f"Scint={s.scintillation_loss_dB:.4f} "
                    f"Point={s.pointing_loss_dB:.4f} "
                    f"SliceLoss={slice_loss:.4f}"
                )
                propagation_loss += slice_loss
                print(
                    s.slice_id,
                    s.atmospheric_loss_dB,
                    s.scintillation_loss_dB,
                    s.pointing_loss_dB,
                    propagation_loss,
                )

                if s.slice_id <= 5:
                    print(
                        f"Slice {s.slice_id}: "
                        f"Geo={s.geometric_loss_dB:.3f}  "
                        f"Atm={s.atmospheric_loss_dB:.3f}  "
                        f"Scint={s.scintillation_loss_dB:.3f}  "
                        f"Point={s.pointing_loss_dB:.3f}  "
                        f"Total={slice_loss:.3f}"
                    )

                    print("Geo =", s.geometric_loss_dB)

                    print("Atmos =", s.atmospheric_loss_dB)

                    print("Scint =", s.scintillation_loss_dB)

                    print("Point =", s.pointing_loss_dB)

                    print("Total =", slice_loss)

                    print("----------------------")

                s.propagation_loss_dB = slice_loss

                # Optical loss distributed equally over all slices
                # Transmission through THIS slice only
                slice_transmission = 10 ** (-slice_loss / 10.0)

                slice_transmission = max(slice_transmission, 1e-30)

                # Cumulative transmission from TX up to this slice
                path_transmission *= slice_transmission

                # Save values
                s.slice_transmission = slice_transmission

                s.link_transmission = path_transmission

                s.path_transmission = path_transmission

                s.channel_efficiency = path_transmission

                s.cumulative_transmission = path_transmission

                if s.slice_id <= 5:

                    print(
                        f"Slice Transmission={slice_transmission:.6e}  "
                        f"Cumulative={path_transmission:.6e}"
                    )
                s.cumulative_loss_dB = -10.0 * math.log10(max(path_transmission, 1e-30))

                s.notes = f"Total={slice_loss:.3f} dB"
            atm = sum(s.atmospheric_loss_dB for s in state.propagation_slices)
            scint = sum(s.scintillation_loss_dB for s in state.propagation_slices)
            point = sum(s.pointing_loss_dB for s in state.propagation_slices)

            print()
            print("===== SLICE SUM CHECK =====")
            print("Atmos =", atm)
            print("Scint =", scint)
            print("Point =", point)

            print("Propagation =", propagation_loss)
            print("===========================")

            print()
            print("===== LINK BUDGET → SLICES =====")
            print("Slices Updated :", number_of_slices)
            print("================================")
            total_loss_dB = (
                propagation_loss + geometric_loss_dB + tx_optical_loss + rx_optical_loss
            )
            optical_transmission = 10 ** (-(tx_optical_loss + rx_optical_loss) / 10.0)
            current_power *= optical_transmission
            print("TOTAL LOSS =", total_loss_dB)
            print()
            print("===== FINAL LOSS CHECK =====")

            print("Geometric      =", geometric_loss_dB)
            print("Propagation    =", propagation_loss)
            print("Atmospheric    =", state.atmospheric_loss_dB)
            print("Scintillation  =", state.scintillation_loss_dB)
            print("Pointing       =", state.pointing_loss_dB)

            print("Calculated     =", geometric_loss_dB + propagation_loss)
            print("Stored Total   =", total_loss_dB)

            print("============================")
            print()
            print("Propagation Loss =", propagation_loss)
            print("Geometric Loss =", geometric_loss_dB)

            state.path_transmission = path_transmission
            print()

        else:

            total_loss_dB = (
                geometric_loss_dB + propagation_loss + tx_optical_loss + rx_optical_loss
            )
            current_power *= 10 ** (-total_loss_dB / 10.0)
        total_loss_dB = min(total_loss_dB, 300.0)

        # ==========================================
        # LOS BLOCKAGE
        # ==========================================

        print()

        print("LOS DEBUG")

        print("----------------")

        print("state.los =", state.los)

        print()

        if hasattr(state, "los"):

            if state.los is False:

                total_loss_dB = float("inf")

                channel_efficiency = 0.0

                state.spot_diameter_m = spot_diameter
                print()
                print("LINK SAVING")
                print("----------------")
                print("spot_diameter =", spot_diameter)
                print("state.spot_diameter_m =", state.spot_diameter_m)

                state.capture_fraction = 0.0

                state.geometric_loss_dB = float("inf")

                state.total_link_loss_dB = float("inf")

                state.channel_efficiency = 0.0
                state.received_power_W = 0.0

                state.path_transmission = 0.0

                state.channel_transmission = 0.0
                print()

                print("RETURNING EARLY FROM LINKBUDGET")

                print()
                
                import re
                if "geo" in state.verifier_text:
                    state.verifier_text["geo"] = re.sub(
                        r'(Geometric Loss\n.*= ).*?( dB\n)', 
                        r'\g<1>inf' + r'\g<2>', 
                        state.verifier_text["geo"]
                    )

                state.verifier_text["link"] = f"""
Geometric Loss
L_geo = -10 · log₁₀(η_capture) = {getattr(state, 'geometric_loss_dB', 0.0):.4f} dB

Attenuation Coefficient
γ = α_atm / L = {getattr(state, 'visibility_gamma_dB_per_km', 0.0):.4f} dB/km

Visibility Loss
L_vis = {getattr(state, 'visibility_loss_dB', 0.0):.4f} dB

Rain Loss
L_rain = {getattr(state, 'rain_loss_dB', 0.0):.4f} dB

Cloud Loss
L_cloud = {getattr(state, 'cloud_loss_dB', 0.0):.4f} dB

Aerosol Loss
L_aer = {getattr(state, 'aerosol_loss_dB', 0.0):.4f} dB

Molecular Loss
L_mol = {getattr(state, 'molecular_loss_dB', 0.0):.4f} dB

Atmospheric Loss
L_atm = {getattr(state, 'atmospheric_loss_dB', 0.0):.4f} dB

Scintillation Loss
L_scint = {getattr(state, 'scintillation_loss_dB', 0.0):.4f} dB

Pointing Loss
L_point = {getattr(state, 'pointing_loss_dB', 0.0):.4f} dB

TX Optical Loss
L_tx = {getattr(state, 'tx_optical_loss_dB', 0.0):.4f} dB

RX Optical Loss
L_rx = {getattr(state, 'rx_optical_loss_dB', 0.0):.4f} dB

Total Link Loss
L_total = ∞ dB

Channel Efficiency
η_channel = 0.000000e+00

RX Coupling Efficiency
η_rx = 10^(-L_rx / 10) = {getattr(state, 'rx_coupling_efficiency', 0.0):.4e}

Availability
Availability = (Time uptime / Total Time) * 100 = {getattr(state, 'availability_percent', 0.0):.2f} %

Spot Diameter
D_spot = {getattr(state, 'spot_diameter_m', 0.0):.6f} m

Beam Diameter
D_beam = 2 · w(z) = {getattr(state, 'beam_diameter_m', 0.0):.6f} m

Capture Fraction
η_capture = {getattr(state, 'capture_fraction', 0.0):.6e}

Link Margin
M_link = P_rx - Sensitivity = {getattr(state, 'link_margin_dB', 0.0):.4f} dB
"""

                return

        # ==========================================
        # CHANNEL EFFICIENCY
        # ==========================================

        channel_efficiency = 10 ** (-total_loss_dB / 10.0)
        print("Channel Efficiency =", channel_efficiency)
        print("Received Power =", current_power)

        channel_efficiency = max(1e-12, min(channel_efficiency, 1.0))
        state.path_transmission = channel_efficiency

        print()

        print("LINK DEBUG")
        print("----------------")

        print("Range =", state.link_distance_km)

        print("Spot Diameter =", spot_diameter)

        print("Total Loss =", total_loss_dB)

        print("Channel Efficiency =", channel_efficiency)

        print()

        # ==========================================
        # STORE RESULTS
        # ==========================================

        print()

        print("SPOT DEBUG")

        print("beam_diameter_m =", getattr(state, "beam_diameter_m", None))
        print("spot_diameter_m =", getattr(state, "spot_diameter_m", None))
        print("beam_radius_m =", getattr(state, "beam_radius_m", None))

        state.geometric_loss_dB = geometric_loss_dB

        state.total_link_loss_dB = total_loss_dB
        state.channel_efficiency = channel_efficiency
        state.received_power_W = current_power

        state.channel_transmission = path_transmission
        print()
        print("FINAL LINK VALUES")
        print("----------------")
        print("state.channel_efficiency =", state.channel_efficiency)
        print("state.total_link_loss_dB =", state.total_link_loss_dB)
        print()

        state.debug_message = "Link budget completed"

        # ==========================================
        # VERIFIER TEXT GENERATION
        # ==========================================
        import re
        if "geo" in state.verifier_text:
            state.verifier_text["geo"] = re.sub(
                r'(Geometric Loss\n.*= ).*?( dB\n)', 
                r'\g<1>' + f'{geometric_loss_dB:.4f}' + r'\g<2>', 
                state.verifier_text["geo"]
            )
        state.verifier_text["link"] = f"""
Geometric Loss
L_geo = -10 · log₁₀(η_capture) = {geometric_loss_dB:.4f} dB

Attenuation Coefficient
γ = α_atm / L = {getattr(state, 'visibility_gamma_dB_per_km', 0.0):.4f} dB/km

Visibility Loss
L_vis = {getattr(state, 'visibility_loss_dB', 0.0):.4f} dB

Rain Loss
L_rain = {getattr(state, 'rain_loss_dB', 0.0):.4f} dB

Cloud Loss
L_cloud = {getattr(state, 'cloud_loss_dB', 0.0):.4f} dB

Aerosol Loss
L_aer = {getattr(state, 'aerosol_loss_dB', 0.0):.4f} dB

Molecular Loss
L_mol = {getattr(state, 'molecular_loss_dB', 0.0):.4f} dB

Atmospheric Loss
L_atm = {getattr(state, 'atmospheric_loss_dB', 0.0):.4f} dB

Scintillation Loss
L_scint = {getattr(state, 'scintillation_loss_dB', 0.0):.4f} dB

Pointing Loss
L_point = {getattr(state, 'pointing_loss_dB', 0.0):.4f} dB

TX Optical Loss
L_tx = {getattr(state, 'tx_optical_loss_dB', 0.0):.4f} dB

RX Optical Loss
L_rx = {getattr(state, 'rx_optical_loss_dB', 0.0):.4f} dB

Total Link Loss
L_total = L_geo + L_atm + L_scint + L_point + L_tx + L_rx = {total_loss_dB:.4f} dB

Channel Efficiency
η_channel = 10^(-L_total / 10) = {channel_efficiency:.6e}

RX Coupling Efficiency
η_rx = 10^(-L_rx / 10) = {getattr(state, 'rx_coupling_efficiency', 0.0):.4e}

Availability
Availability = (Time uptime / Total Time) * 100 = {getattr(state, 'availability_percent', 0.0):.2f} %

Spot Diameter
D_spot = {getattr(state, 'spot_diameter_m', 0.0):.6f} m

Beam Diameter
D_beam = 2 · w(z) = {getattr(state, 'beam_diameter_m', 0.0):.6f} m

Capture Fraction
η_capture = {getattr(state, 'capture_fraction', 0.0):.6e}

Link Margin
M_link = P_rx - Sensitivity = {getattr(state, 'link_margin_dB', 0.0):.4f} dB
"""


        # ==========================================
        # NEW FILES COMPATIBILITY HOOKS (ADDED ONLY)
        # ==========================================

        # sync model support
        if hasattr(state, "sync_error_ps"):
            state.sync_penalty_factor = min(1.0, state.sync_error_ps / 100.0)

        # polarization model support
        if hasattr(state, "polarization_misalignment_loss_dB"):
            state.total_link_loss_dB += state.polarization_misalignment_loss_dB

        # tracking coupling (future enhancement compatibility)
        if hasattr(state, "tracking_error_urad"):
            state.pointing_quality_factor = max(
                0.0, 1.0 - state.tracking_error_urad / 1000.0
            )

        # report/project compatibility
        if hasattr(state, "project_metadata"):
            state.project_metadata["link_budget_status"] = "computed"

            print("DEBUG LinkBudget inputs:")
            print("atmospheric_loss:", getattr(state, "atmospheric_loss_dB", None))
            print("scintillation_loss:", getattr(state, "scintillation_loss_dB", None))
            print("pointing_loss:", getattr(state, "pointing_loss_dB", None))

            print("\n===== LINK OUTPUT =====")
            print("Geo Loss =", state.geometric_loss_dB)
            print("Atmos Loss =", state.atmospheric_loss_dB)
            print("Scint Loss =", state.scintillation_loss_dB)
            print("Pointing Loss =", state.pointing_loss_dB)
            print("Total Loss =", state.total_link_loss_dB)
            print("Channel Efficiency =", state.channel_efficiency)
            print("Capture =", state.capture_fraction)
            print("=======================\n")
