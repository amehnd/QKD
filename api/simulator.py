from dataclasses import asdict

from core.state import SimulationState
from core.simulation_runner import run_simulation_kernel


def run_simulation(parameters: dict):

    # Create default simulation state
    state = SimulationState()

    # Update state from API request
    for key, value in parameters.items():

        if hasattr(state, key):

            setattr(state, key, value)

    # Run the simulator
    run_simulation_kernel(state)

    # Return ALL outputs
    return {
        "status": "success",
        "secure_key_rate": state.secure_key_rate,
        "raw_key_rate": state.raw_key_rate,
        "qber": state.qber,
        "atmospheric_loss_dB": state.atmospheric_loss_dB,
        "total_link_loss_dB": state.total_link_loss_dB,
        "beam_wander_urad": state.beam_wander_urad,
        "tracking_error_urad": state.tracking_error_urad,
        "simulation_time_sec": state.simulation_time_sec,
    }
