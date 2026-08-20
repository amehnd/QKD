# QKD — Maritime Free-Space-Optical QKD Link Simulator

A desktop tool that simulates a **free-space optical (FSO) Quantum Key Distribution (QKD) link**, built for ship-to-ship / ship-to-shore / coastal scenarios. Enter a transmitter and receiver location plus optics, weather, sea-state, and hardware parameters, and it predicts how many secure key bits per second the link could deliver — running the beam through geometry, atmospheric loss, marine turbulence, pointing/tracking, and detector models before feeding the result into a QKD protocol.

## What it does

- **Link geometry** — distance, bearing, elevation, line-of-sight / Earth-curvature and terrain-clearance checks
- **Atmosphere & marine effects** — fog/haze/rain/aerosol/molecular loss, optical turbulence (scintillation, beam wander, beam spreading), marine boundary-layer and evaporation-duct refraction
- **Platform & pointing** — ship roll/pitch/yaw motion, gimbal and fast-steering-mirror tracking, pointing-acquisition-tracking (PAT) lock probability
- **Detector performance** — signal/dark/background/afterpulse count rates for SPAD, SNSPD, APD, PMT, or TES detectors
- **QKD protocols** — QBER, sifted key rate, and secure key rate for **BB84**, **B92**, **E91**, **BBM92**, or **Decoy-State BB84**
- **Per-slice phase-screen viewer** — hover any slice marker on the SCHEMATIC tab to see a randomized atmospheric phase-screen realization for that slice, propagated to near/mid/far distances (built on [aotools](https://github.com/AOtools/aotools); visualization only, doesn't feed back into the reported numbers)
- **System tools** — design optimizer (suggests hardware for a target range/rate), trade-study sweeps, Monte Carlo sensitivity analysis

## Install

```bash
pip install -r requirements.txt
```

`requirements.txt` currently only lists `PySide6` and `numpy`. The app also imports a few packages that aren't declared there yet — install these too if you hit an `ImportError`:

```bash
pip install flask fastapi pydantic matplotlib pyyaml global-land-mask aotools
```

## Run

```bash
python main.py
```

This opens the main window, "FSO/QKD FULL PHYSICS DASHBOARD". Fill in mission/optics/environment/QKD parameters (grouped into collapsible sections), pick a QKD protocol, and run the simulation. Results appear across tabs:

- **DATA MODE** — categorized outputs (Geometry, Atmosphere, Turbulence, Tracking, Detector, Link, QKD, ...)
- **QKD** — protocol-specific results
- **PLOT** / **COMPARE MODELS** — sweep a parameter, compare models against each other
- **SLICE DETAILS** — every value for one selected slice along the path
- **SCHEMATIC** — a visual TX→RX beam path; hover a slice marker for its phase-screen popup
- **SETTINGS** — app configuration

TX/RX coordinates can be typed in or picked visually — a "map" button launches a small local map picker.

**Coordinate map picker:** a Flask server (`map/map_server.py`) starts automatically when needed, serving an interactive map at `http://127.0.0.1:5050`.

**REST API (optional, separate process):**

```bash
uvicorn api.app:app --reload
```

- `GET /` — health check
- `POST /simulate` — accepts `link_distance_km`, `wavelength_nm`, `visibility_km`, `humidity_pct` and returns secure key rate, QBER, and a few other summary outputs. This covers only 4 of the ~350 possible input parameters and isn't started automatically.

## Project layout

```
core/     simulation state, model pipeline/kernel, registry
models/   ~30 physics models (turbulence, beam propagation, detector, QKD protocols, phase screen, ...)
ui/       PySide6 desktop UI (main window, phase-screen hover popup/worker)
plots/    matplotlib canvas helpers
map/      local Flask map picker for TX/RX coordinates
api/      optional FastAPI service
config/   settings (config/settings.yaml, managed by core/settings_manager.py)
```

## Known limitations (honestly documented)

This is a research/engineering prototype, not a finished product.

- **Project save/load is broken** — the UI has no save/load-project hookup, and `core/project_io.py` doesn't contain a working `ProjectIO` class.
- **`requirements.txt` is out of date** — Flask, FastAPI, matplotlib, PyYAML, and aotools are used but not declared.
- **`config/default.yaml` and `core/config_manager.py` are orphaned** — nothing loads them; the real settings file is `config/settings.yaml`.
- **`plots/plot_manager.py` and `report_generator.py` (if present) are unused** — never called from anywhere.
- **Terrain data is synthetic** — `models/terrain_provider.py` procedurally generates plausible terrain rather than reading a real digital elevation model.
- **Trade-study and Monte Carlo results are statistical approximations**, not full physics-pipeline re-runs per data point.
- A Google Maps API key is hardcoded in `map/templates/map.html` — replace it with your own before relying on the map picker long-term.
- The phase-screen hover popup is a single random realization for visual intuition — it does not feed back into the reported link-budget / secure-key-rate numbers, which keep using the analytic turbulence statistics from `models/turbulence.py`.

## License

Not yet specified — add a `LICENSE` file if you plan to share or open this repo.
