from fastapi import FastAPI

from api.schemas import SimulationInput
from api.simulator import run_simulation

app = FastAPI(
    title="QKD-FSO Simulator API",
    description="API for Maritime Free Space Optical Quantum Key Distribution Simulator",
    version="0.3",
)


@app.get("/")
def home():
    return {"message": "QKD-FSO Simulator API", "version": "0.3", "status": "running"}


@app.post("/simulate")
def simulate(data: SimulationInput):

    return run_simulation(data.model_dump())
