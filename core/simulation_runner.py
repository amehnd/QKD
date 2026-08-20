from core.simulation_kernel import SimulationKernel

from models.solar_environment import SolarEnvironmentModel
from models.marine_boundary_layer import MarineBoundaryLayerModel
from models.evaporation_duct import EvaporationDuctModel
from models.refractivity import RefractivityModel
from models.chromatic_refraction import ChromaticRefractionModel
from models.background_radiance import BackgroundRadianceModel
from models.geometry import GeometryModel
from models.land_sea_classifier import LandSeaClassifierModel
from models.weather import WeatherModel

from models.atmospheric_loss import AtmosphericLossModel
from models.beam_propagation import BeamPropagationModel
from models.adaptive_slicing import AdaptiveSlicingModel
from models.turbulence import TurbulenceModel
from models.gimbal import GimbalModel
from models.terrain_database import TerrainDatabaseModel
from models.terrain_profile import TerrainProfileModel
from models.tracking import TrackingModel
from models.pointing_loss import PointingLossModel
from models.synchronization_model import SynchronizationModel
from models.polarization_model import PolarizationModel
from models.link_budget import LinkBudgetModel
from models.detector import DetectorModel
from models.bb84 import BB84Model
from models.decoy_bb84 import DecoyBB84Model
from models.b92 import B92Model
from models.e91 import E91Model
from models.bbm92 import BBM92Model

from models.ship_motion import ShipMotionModel
from models.most import MOSTModel
from models.sky_radiance import SkyRadianceModel
from models.fsm import FSMModel
from models.pat import PATModel

try:
    from models.skr import SKRModel
    from models.design_optimizer import DesignOptimizerModel

    ADVANCED_MODELS = True
except:
    ADVANCED_MODELS = False


def solve_tx_height(state):
    """
    Solve TX height that gives the requested
    Minimum Height Above Sea.
    """

    target = state.minimum_height_above_sea_m

    tx = state.tx_height_msl_m

    for _ in range(40):

        state.tx_height_msl_m = tx

        # Run only the models needed to compute clearance
        AdaptiveSlicingModel().execute(state)
        GeometryModel().execute(state)
        TerrainDatabaseModel().execute(state)
        TerrainProfileModel().execute(state)

        error = state.minimum_height_above_sea_m - target

        if abs(error) < 0.01:
            break

        tx -= error
        state.tx_height_msl_m = tx
    print("Solved TX Height =", state.tx_height_msl_m)


def solve_rx_height(state):
    """
    Solve RX height that gives the requested
    Minimum Height Above Sea.
    """

    target = state.minimum_height_above_sea_m

    rx = state.rx_height_msl_m

    for _ in range(40):

        state.rx_height_msl_m = rx

        AdaptiveSlicingModel().execute(state)
        GeometryModel().execute(state)
        TerrainDatabaseModel().execute(state)
        TerrainProfileModel().execute(state)

        error = state.minimum_height_above_sea_m - target

        if abs(error) < 0.01:
            break

        rx -= error

    state.rx_height_msl_m = rx

    print("Solved RX Height =", state.rx_height_msl_m)


def run_simulation_kernel(state):
    if state.solve_for == "TX Height":
        solve_tx_height(state)

    elif state.solve_for == "RX Height":
        solve_rx_height(state)

    kernel = SimulationKernel()

    # ==================================================
    # ENVIRONMENT
    # ==================================================

    kernel.register_model(SolarEnvironmentModel())
    kernel.register_model(AdaptiveSlicingModel())

    kernel.register_model(WeatherModel())

    kernel.register_model(LandSeaClassifierModel())
    kernel.register_model(GeometryModel())

    kernel.register_model(TerrainDatabaseModel())

    kernel.register_model(TerrainProfileModel())

    kernel.register_model(MOSTModel())

    kernel.register_model(MarineBoundaryLayerModel())

    kernel.register_model(EvaporationDuctModel())

    kernel.register_model(RefractivityModel())

    kernel.register_model(ChromaticRefractionModel())

    kernel.register_model(AtmosphericLossModel())

    kernel.register_model(SkyRadianceModel())

    kernel.register_model(BackgroundRadianceModel())

    # ==================================================
    # PLATFORM / TURBULENCE
    # ==================================================

    kernel.register_model(ShipMotionModel())

    kernel.register_model(TurbulenceModel())
    kernel.register_model(BeamPropagationModel())
    # ==================================================
    # POINTING, ACQUISITION & TRACKING
    # ==================================================

    kernel.register_model(GimbalModel())

    kernel.register_model(FSMModel())

    kernel.register_model(PATModel())

    kernel.register_model(TrackingModel())
    kernel.register_model(PointingLossModel())

    # ==================================================
    # SYSTEM
    # ==================================================

    kernel.register_model(SynchronizationModel())

    kernel.register_model(PolarizationModel())

    kernel.register_model(LinkBudgetModel())

    kernel.register_model(DetectorModel())

    # ==================================
    # QKD PROTOCOL SELECTION
    # ==================================

    print()

    print("QKD PROTOCOL SELECTED =", state.qkd_protocol)

    protocol = getattr(state, "qkd_protocol", "BB84")

    print()

    print("state.qkd_protocol =", repr(state.qkd_protocol))
    print("protocol =", repr(protocol))

    if protocol == "BB84":

        kernel.register_model(BB84Model())

    elif protocol == "Decoy BB84":

        kernel.register_model(DecoyBB84Model())

    elif protocol == "B92":

        kernel.register_model(B92Model())

    elif protocol == "E91":

        kernel.register_model(E91Model())

    elif protocol == "BBM92":
        kernel.register_model(BBM92Model())

    else:

        print("Unknown protocol -> using BB84")

        kernel.register_model(BB84Model())
    # ==================================
    # ADVANCED MODELS
    # ==================================
    if ADVANCED_MODELS:
        kernel.register_model(SKRModel())
        kernel.register_model(DesignOptimizerModel())

    # elif protocol == "MDI-QKD":

    # kernel.register_model(

    # MDIQKDModel()

    # )

    print("\n==============================")
    print("RUNNING SIMULATION (v0.3)")
    print("==============================\n")

    kernel.run(state)
    print("AFTER KERNEL propagation_direction =", repr(state.propagation_direction))

    print("\n==============================")
    print("FINAL OUTPUTS")
    print("==============================")

    print("Channel Efficiency:", state.channel_efficiency)
    print("Signal Rate:", state.signal_count_rate)
    print("Raw Key Rate:", state.raw_key_rate)
    print("Sifted Key Rate:", state.sifted_key_rate)
    print("QBER:", state.qber)
    print("Secret Fraction:", state.secret_fraction)
    print("Secure Key Rate:", state.secure_key_rate)
    print("Has rytov_variance:", hasattr(state, "rytov_variance"))
    print("\nDEBUG AFTER KERNEL")
    print("rx_coupling_efficiency:", state.rx_coupling_efficiency)
    print("beam_wander:", state.beam_wander_urad)
    print("background:", state.background_count_rate)
    print("afterpulse:", state.afterpulse_count_rate)
    print("sky:", state.clear_sky_radiance_W_sr_m2)

    # Generate verifier text for ALL QKD protocols
    import copy
    temp_state = copy.deepcopy(state)
    for model_class, proto_name in [
        (BB84Model, "BB84"),
        (DecoyBB84Model, "Decoy BB84"),
        (B92Model, "B92"),
        (E91Model, "E91"),
        (BBM92Model, "BBM92")
    ]:
        m = model_class()
        temp_state.qkd_protocol = proto_name
        m.execute(temp_state)
        state.verifier_text[proto_name] = temp_state.verifier_text.get("qkd", "")

