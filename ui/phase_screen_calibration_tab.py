"""
phase_screen_calibration_tab.py
v2.0

"PHASE SCREEN CALIBRATION" tab, alongside SCHEMATIC.

v2.0 changes (extends v1.0, doesn't replace it conceptually):

  * Bound to the simulation: a "Slice" selector lets you pick a real
    PropagationSlice from the last "Run Simulation" (state.propagation_slices)
    and load its Cn2, wavelength, aperture geometry, divergence, and
    beam-spread factor as the slider starting point. Sliders stay fully
    adjustable after loading -- "calibration" means perturbing away from
    a real value, not typing one in from scratch. "Custom" is still
    available for a from-scratch sandbox with no slice behind it.

  * Beam growth vs. propagation distance now uses the SAME closed-form
    geometric divergence law as models/beam_propagation.py:

        w(z) = sqrt(w0^2 + (divergence_rad/2 * z)^2) * beam_spread_factor

    v1.0 instead held one fixed beam_waist_m and only let aotools'
    angularSpectrum's diffraction do any spreading -- but diffraction
    alone is a tiny effect at these grid sizes/distances next to real
    mrad-scale divergence, so the beam visibly barely grew with distance.
    Now each Near/Mid/Far checkpoint gets its own physically-correct
    width from the formula above, so dragging "Propagation distance"
    visibly opens the beam up the same way it would in the real link
    budget. The phase screen (turbulence texture) still rides on top of
    that width via ft_sh_phase_screen + a short angularSpectrum step,
    exactly as before, sized to fit whatever width Near/Mid/Far now needs.

  * eta (aperture transmittance) is now computed against an independent
    RX aperture radius slider, not against the (growing) TX beam width --
    matching how capture_fraction is computed in beam_propagation.py
    (rx_radius vs. current beam radius), instead of asking "what fraction
    of the beam lands inside itself", which was close to meaningless.
"""

import random

import numpy as np

from PySide6.QtCore import Qt, QObject, QRunnable, QThreadPool, QTimer, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from aotools.turbulence import ft_sh_phase_screen
from aotools.opticalpropagation import angularSpectrum

from models.phase_screen import (
    compute_reference_r0,
    estimate_aperture_transmittance,
    MIN_BEAM_WAIST_M,
    MIN_FRIED_PARAMETER_M,
)

# ── Slider ranges ─────────────────────────────────────────────────────
# Cn2 spans many orders of magnitude, so its slider works in log10 space;
# divergence is also log (0.01 - 10 mrad covers tight collimated links
# through deliberately-wide ones); everything else is linear.
CN2_LOG_MIN, CN2_LOG_MAX = -18.0, -12.0            # log10(Cn2), m^-2/3
OUTER_SCALE_MIN_M, OUTER_SCALE_MAX_M = 1.0, 200.0
INNER_SCALE_MIN_MM, INNER_SCALE_MAX_MM = 1.0, 100.0
WAVELENGTH_MIN_NM, WAVELENGTH_MAX_NM = 400.0, 2000.0
TX_RADIUS_MIN_CM, TX_RADIUS_MAX_CM = 0.5, 50.0
RX_RADIUS_MIN_CM, RX_RADIUS_MAX_CM = 1.0, 100.0
DIVERGENCE_LOG_MIN, DIVERGENCE_LOG_MAX = -2.0, 1.0  # log10(mrad): 0.01 - 10 mrad
BEAM_SPREAD_MIN, BEAM_SPREAD_MAX = 1.0, 3.0
DISTANCE_MIN_M, DISTANCE_MAX_M = 10.0, 5000.0

REFERENCE_LENGTH_M = 100.0  # same fixed length compute_reference_r0() uses elsewhere
SLIDER_RESOLUTION = 1000    # internal slider units, for smooth-feeling drags

DEFAULTS = {
    "cn2": 1e-15,
    "outer_scale_m": 50.0,
    "inner_scale_mm": 5.0,
    "wavelength_nm": 1550.0,
    "tx_radius_cm": 7.5,       # tx_aperture_mm default (150mm) / 2
    "rx_radius_cm": 30.0,      # rx_aperture_mm default (600mm) / 2
    "divergence_mrad": 0.1,    # matches core/ui_database.py default
    "beam_spread_factor": 1.0,
    "distance_m": 1000.0,
    "grid_size": "256",
}


def _slider_to_value(slider_val, vmin, vmax, log=False):
    frac = slider_val / SLIDER_RESOLUTION
    if log:
        return 10.0 ** (vmin + frac * (vmax - vmin))
    return vmin + frac * (vmax - vmin)


def _value_to_slider(value, vmin, vmax, log=False):
    if log:
        value = np.log10(max(value, 10.0 ** vmin))
    frac = (value - vmin) / (vmax - vmin)
    return int(round(np.clip(frac, 0.0, 1.0) * SLIDER_RESOLUTION))


def geometric_beam_radius(w0_m, divergence_rad, z_m, beam_spread_factor=1.0):
    """Local beam radius (m) at distance z_m from the TX aperture.

    Identical formula to models/beam_propagation.py's per-slice update:
        current_radius = sqrt(initial_radius^2 + (divergence/2 * z)^2)
        current_radius *= turbulence beam_spread_factor
    kept in lockstep here so this tab's "does it expand?" answer matches
    what the real link budget would compute for the same inputs.
    """
    geometric = np.sqrt(w0_m ** 2 + (divergence_rad / 2.0 * z_m) ** 2)
    return geometric * max(float(beam_spread_factor), 1.0)


class _CalibrationWorkerSignals(QObject):
    finished = Signal(dict)
    error = Signal(str)


class _CalibrationWorker(QRunnable):
    """Runs phase-screen generation + propagation for all three checkpoints
    off the GUI thread, the same split as PhaseScreenWorker in
    phase_screen_worker.py -- sliders can fire many jobs quickly."""

    def __init__(self, params):
        super().__init__()
        self.params = params
        self.signals = _CalibrationWorkerSignals()

    def run(self):
        p = self.params
        try:
            r0 = compute_reference_r0(p["cn2"], p["wavelength_m"], REFERENCE_LENGTH_M)
            r0 = max(r0, MIN_FRIED_PARAMETER_M)

            grid_size = p["grid_size"]
            distance_m = p["distance_m"]
            # Absolute distance-from-TX for each checkpoint. If this tab is
            # bound to a real slice, base_distance_m is that slice's own
            # start_m, so these line up with the slice's real position in
            # the link rather than always starting fresh from z=0.
            base_z = p.get("base_distance_m", 0.0)
            checkpoints = (
                base_z + distance_m / 3.0,
                base_z + 2.0 * distance_m / 3.0,
                base_z + distance_m,
            )

            images = []
            widths_m = []
            for z in checkpoints:
                w_z = geometric_beam_radius(
                    p["w0_m"], p["divergence_rad"], z, p["beam_spread_factor"]
                )
                w_z = max(w_z, MIN_BEAM_WAIST_M)
                widths_m.append(w_z)

                beam_diam = max(2.0 * w_z, 4.0 * r0, 4.0 * MIN_BEAM_WAIST_M)
                delta = beam_diam / grid_size

                screen = ft_sh_phase_screen(
                    r0=r0,
                    N=grid_size,
                    delta=delta,
                    L0=p["outer_scale_m"],
                    l0=p["inner_scale_m"],
                    seed=p["seed"],
                )

                x = (np.arange(grid_size) - grid_size // 2) * delta
                X, Y = np.meshgrid(x, x)
                amplitude = np.exp(-(X ** 2 + Y ** 2) / w_z ** 2)
                field = amplitude * np.exp(1j * screen)

                # Short local diffraction step to turn the wavefront ripple
                # into visible speckle -- NOT what grows the spot; the
                # geometric width above already carries the real growth.
                local_step_m = max(0.02 * z, 1.0)
                propagated = angularSpectrum(
                    field, p["wavelength_m"], delta, delta, float(local_step_m)
                )
                images.append((np.abs(propagated) ** 2, delta))

            far_img, far_delta = images[-1]
            eta = estimate_aperture_transmittance(far_img, far_delta, p["rx_radius_m"])

            self.signals.finished.emit({
                "images": images,
                "checkpoints": checkpoints,
                "widths_m": widths_m,
                "r0": r0,
                "eta": eta,
            })
        except Exception as exc:
            self.signals.error.emit(str(exc))


class PhaseScreenCalibrationTab(QWidget):
    """Calibration tab bound to the simulation: pick a slice (or go
    Custom), drag sliders, watch the phase screen and the beam's real
    geometric growth over distance update live."""

    DEBOUNCE_MS = 120
    CUSTOM_LABEL = "Custom (no slice — free sandbox)"

    def __init__(self, state=None, parent=None):
        super().__init__(parent)

        self.state = state
        self._slices_by_label = {}

        self._threadpool = QThreadPool()
        self._job_id = 0
        self._active_worker = None
        self._seed = 0

        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.timeout.connect(self._run_job)

        root = QHBoxLayout(self)

        # ── Left: controls ──────────────────────────────────────────
        controls = QGroupBox("Calibration Controls")
        controls.setMaximumWidth(380)
        grid = QGridLayout()
        grid.setVerticalSpacing(8)
        row = 0

        # -- Slice binding --
        slice_row = QHBoxLayout()
        slice_lbl = QLabel("Slice:")
        slice_lbl.setStyleSheet("font-weight:bold; font-size:11px;")
        self.slice_combo = QComboBox()
        self.slice_combo.addItem(self.CUSTOM_LABEL)
        self.slice_combo.currentTextChanged.connect(self._on_slice_selected)
        slice_row.addWidget(slice_lbl)
        slice_row.addWidget(self.slice_combo, 1)
        grid.addLayout(slice_row, row, 0)
        row += 1

        self.refresh_btn = QPushButton("↻ Refresh slice list from last run")
        self.refresh_btn.clicked.connect(lambda: self.refresh_from_state(self.state))
        grid.addWidget(self.refresh_btn, row, 0)
        row += 1

        self.context_label = QLabel("Calibrating: Custom parameters (no simulation run yet)")
        self.context_label.setWordWrap(True)
        self.context_label.setStyleSheet(
            "font-size:10px; color:#0B57D0; font-weight:bold; margin-bottom:4px;"
        )
        grid.addWidget(self.context_label, row, 0)
        row += 1

        self._sliders = {}

        def add_slider(key, label, vmin, vmax, default, log=False):
            nonlocal row
            lbl = QLabel(label)
            lbl.setStyleSheet("font-weight:bold; font-size:11px;")
            val_lbl = QLabel("")
            val_lbl.setStyleSheet("font-size:11px; color:#0B57D0;")
            val_lbl.setMinimumWidth(90)
            val_lbl.setAlignment(Qt.AlignRight)

            header = QHBoxLayout()
            header.addWidget(lbl)
            header.addStretch()
            header.addWidget(val_lbl)
            grid.addLayout(header, row, 0, 1, 1)
            row += 1

            slider = QSlider(Qt.Horizontal)
            slider.setMinimum(0)
            slider.setMaximum(SLIDER_RESOLUTION)
            slider.setValue(_value_to_slider(default, vmin, vmax, log=log))
            grid.addWidget(slider, row, 0, 1, 1)
            row += 1

            self._sliders[key] = (slider, vmin, vmax, log, val_lbl)
            slider.valueChanged.connect(self._on_slider_changed)
            return slider

        add_slider("cn2", "Cn² — turbulence strength (m⁻²ᐟ³)",
                    CN2_LOG_MIN, CN2_LOG_MAX, DEFAULTS["cn2"], log=True)
        add_slider("outer_scale_m", "Outer scale L₀ (m)",
                    OUTER_SCALE_MIN_M, OUTER_SCALE_MAX_M, DEFAULTS["outer_scale_m"])
        add_slider("inner_scale_mm", "Inner scale l₀ (mm)",
                    INNER_SCALE_MIN_MM, INNER_SCALE_MAX_MM, DEFAULTS["inner_scale_mm"])
        add_slider("wavelength_nm", "Wavelength (nm)",
                    WAVELENGTH_MIN_NM, WAVELENGTH_MAX_NM, DEFAULTS["wavelength_nm"])
        add_slider("tx_radius_cm", "TX aperture radius w₀ (cm)",
                    TX_RADIUS_MIN_CM, TX_RADIUS_MAX_CM, DEFAULTS["tx_radius_cm"])
        add_slider("divergence_mrad", "Beam divergence (mrad)",
                    DIVERGENCE_LOG_MIN, DIVERGENCE_LOG_MAX, DEFAULTS["divergence_mrad"], log=True)
        add_slider("beam_spread_factor", "Turbulence beam-spread factor",
                    BEAM_SPREAD_MIN, BEAM_SPREAD_MAX, DEFAULTS["beam_spread_factor"])
        add_slider("rx_radius_cm", "RX aperture radius (cm)",
                    RX_RADIUS_MIN_CM, RX_RADIUS_MAX_CM, DEFAULTS["rx_radius_cm"])
        add_slider("distance_m", "Propagation distance beyond slice start (m)",
                    DISTANCE_MIN_M, DISTANCE_MAX_M, DEFAULTS["distance_m"])

        # Grid size (discrete, so a combo box rather than a slider)
        grid_row = QHBoxLayout()
        grid_lbl = QLabel("Grid size")
        grid_lbl.setStyleSheet("font-weight:bold; font-size:11px;")
        self.grid_combo = QComboBox()
        self.grid_combo.addItems(["128", "256", "512"])
        self.grid_combo.setCurrentText(DEFAULTS["grid_size"])
        self.grid_combo.currentTextChanged.connect(self._on_slider_changed)
        grid_row.addWidget(grid_lbl)
        grid_row.addStretch()
        grid_row.addWidget(self.grid_combo)
        grid.addLayout(grid_row, row, 0)
        row += 1

        # Seed controls -- same random realization vs. a fresh one
        seed_row = QHBoxLayout()
        self.seed_label = QLabel("Seed: 0")
        self.seed_label.setStyleSheet("font-size:10px; color:#555;")
        self.randomize_btn = QPushButton("🎲 New realization")
        self.randomize_btn.clicked.connect(self._randomize_seed)
        seed_row.addWidget(self.seed_label)
        seed_row.addStretch()
        seed_row.addWidget(self.randomize_btn)
        grid.addLayout(seed_row, row, 0)
        row += 1

        reset_btn = QPushButton("Reset to defaults")
        reset_btn.clicked.connect(self._reset_defaults)
        grid.addWidget(reset_btn, row, 0)
        row += 1

        self.readout_label = QLabel("")
        self.readout_label.setWordWrap(True)
        self.readout_label.setStyleSheet(
            "font-size:11px; color:#333; background:#f2f2f2; "
            "padding:8px; border-radius:4px; margin-top:6px;"
        )
        grid.addWidget(self.readout_label, row, 0)
        row += 1

        grid.setRowStretch(row, 1)
        controls.setLayout(grid)

        # ── Right: live preview ─────────────────────────────────────
        plot_box = QGroupBox("Live Preview — beam width grows with distance per "
                              "the same divergence law as the link budget")
        plot_layout = QVBoxLayout()

        self.figure = Figure(figsize=(7.5, 3.6), dpi=100)
        self.figure.patch.set_facecolor("#fafafa")
        self.canvas = FigureCanvas(self.figure)
        self.axes = self.figure.subplots(1, 3)
        for ax in self.axes:
            ax.axis("off")
        plot_layout.addWidget(self.canvas)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("font-size:10px; color:#888;")
        plot_layout.addWidget(self.status_label)

        plot_box.setLayout(plot_layout)

        root.addWidget(controls)
        root.addWidget(plot_box, 1)

        self._base_distance_m = 0.0
        self._update_value_labels()
        self.refresh_from_state(state)
        self._run_job()  # initial render, no need to wait for a drag

    # ------------------------------------------------------------------
    # Simulation binding
    # ------------------------------------------------------------------
    def refresh_from_state(self, state):
        """Repopulate the slice dropdown from state.propagation_slices.

        Call this whenever a simulation finishes (main_window does, right
        after run_simulation_kernel()) so the calibration tab can offer
        the slices that actually exist in the current run. Safe to call
        with state=None or an empty slice list -- falls back to Custom.
        """
        if state is not None:
            self.state = state

        current_label = self.slice_combo.currentText()

        self.slice_combo.blockSignals(True)
        self.slice_combo.clear()
        self.slice_combo.addItem(self.CUSTOM_LABEL)
        self._slices_by_label = {}

        slices = getattr(self.state, "propagation_slices", None) or []
        for s in slices:
            label = f"Slice {s.slice_id}  ({s.start_m:.0f}\u2013{s.end_m:.0f} m)"
            self._slices_by_label[label] = s
            self.slice_combo.addItem(label)

        # Keep the same slice selected across a refresh if it still exists,
        # otherwise fall back to Custom rather than silently jumping slices.
        if current_label in self._slices_by_label or current_label == self.CUSTOM_LABEL:
            idx = self.slice_combo.findText(current_label)
            if idx >= 0:
                self.slice_combo.setCurrentIndex(idx)
        self.slice_combo.blockSignals(False)

        self._on_slice_selected(self.slice_combo.currentText())

    def _on_slice_selected(self, label):
        slice_obj = self._slices_by_label.get(label)

        if slice_obj is None:
            self.context_label.setText(
                "Calibrating: Custom parameters (no simulation slice — "
                "free sandbox; sliders keep whatever you last set)."
            )
            self._base_distance_m = 0.0
            self._on_slider_changed()
            return

        # Seed sliders from the real slice. Still fully adjustable
        # afterwards -- this is a starting point, not a lock.
        wavelength_nm = float(getattr(self.state, "wavelength_nm", DEFAULTS["wavelength_nm"]) or DEFAULTS["wavelength_nm"])
        divergence_mrad = float(getattr(self.state, "tx_beam_divergence_mrad",
                                         getattr(slice_obj, "tx_beam_divergence_mrad", DEFAULTS["divergence_mrad"])) or DEFAULTS["divergence_mrad"])
        tx_aperture_mm = getattr(self.state, "tx_aperture_mm", None)
        if tx_aperture_mm:
            tx_radius_cm = float(tx_aperture_mm) / 2.0 / 10.0
        else:
            tx_radius_cm = DEFAULTS["tx_radius_cm"]
        rx_aperture_mm = getattr(self.state, "rx_aperture_mm", None)
        if rx_aperture_mm:
            rx_radius_cm = float(rx_aperture_mm) / 2.0 / 10.0
        else:
            rx_radius_cm = DEFAULTS["rx_radius_cm"]
        beam_spread_factor = float(getattr(slice_obj, "beam_spread_factor", 1.0) or 1.0)
        cn2 = float(getattr(slice_obj, "Cn2", 0.0) or 0.0)
        if cn2 <= 0:
            cn2 = DEFAULTS["cn2"]

        self._set_slider("cn2", cn2, CN2_LOG_MIN, CN2_LOG_MAX, log=True)
        self._set_slider("wavelength_nm", wavelength_nm, WAVELENGTH_MIN_NM, WAVELENGTH_MAX_NM)
        self._set_slider("tx_radius_cm", tx_radius_cm, TX_RADIUS_MIN_CM, TX_RADIUS_MAX_CM)
        self._set_slider("rx_radius_cm", rx_radius_cm, RX_RADIUS_MIN_CM, RX_RADIUS_MAX_CM)
        self._set_slider("divergence_mrad", divergence_mrad, DIVERGENCE_LOG_MIN, DIVERGENCE_LOG_MAX, log=True)
        self._set_slider("beam_spread_factor", max(beam_spread_factor, BEAM_SPREAD_MIN),
                          BEAM_SPREAD_MIN, BEAM_SPREAD_MAX)
        self._set_slider("distance_m", max(float(slice_obj.length_m) or DEFAULTS["distance_m"], DISTANCE_MIN_M),
                          DISTANCE_MIN_M, DISTANCE_MAX_M)

        # This is what makes Near/Mid/Far land at this slice's true
        # position in the link, instead of always restarting at z=0.
        self._base_distance_m = float(getattr(slice_obj, "start_m", 0.0) or 0.0)

        self.context_label.setText(
            f"Calibrating: Slice {slice_obj.slice_id}  "
            f"({slice_obj.start_m:.0f}\u2013{slice_obj.end_m:.0f} m from TX)  |  "
            f"Cn\u00b2 = {cn2:.2e} m\u207b\u00b2\u1d40\u2044\u00b3"
        )
        self._on_slider_changed()

    def _set_slider(self, key, value, vmin, vmax, log=False):
        slider, _, _, _, _ = self._sliders[key]
        slider.blockSignals(True)
        slider.setValue(_value_to_slider(value, vmin, vmax, log=log))
        slider.blockSignals(False)

    # ------------------------------------------------------------------
    def _update_value_labels(self):
        formats = {
            "cn2": lambda v: f"{v:.2e}",
            "outer_scale_m": lambda v: f"{v:.1f} m",
            "inner_scale_mm": lambda v: f"{v:.1f} mm",
            "wavelength_nm": lambda v: f"{v:.0f} nm",
            "tx_radius_cm": lambda v: f"{v:.1f} cm",
            "rx_radius_cm": lambda v: f"{v:.1f} cm",
            "divergence_mrad": lambda v: f"{v:.3f} mrad",
            "beam_spread_factor": lambda v: f"{v:.2f}\u00d7",
            "distance_m": lambda v: f"{v:.0f} m",
        }
        for key, (slider, vmin, vmax, log, val_lbl) in self._sliders.items():
            value = _slider_to_value(slider.value(), vmin, vmax, log=log)
            val_lbl.setText(formats[key](value))

    def _current_params(self):
        def value(key):
            slider, vmin, vmax, log, _ = self._sliders[key]
            return _slider_to_value(slider.value(), vmin, vmax, log=log)

        return {
            "cn2": value("cn2"),
            "outer_scale_m": value("outer_scale_m"),
            "inner_scale_m": value("inner_scale_mm") / 1000.0,
            "wavelength_m": value("wavelength_nm") * 1e-9,
            "w0_m": value("tx_radius_cm") / 100.0,
            "rx_radius_m": value("rx_radius_cm") / 100.0,
            "divergence_rad": value("divergence_mrad") * 1e-3,
            "beam_spread_factor": value("beam_spread_factor"),
            "distance_m": value("distance_m"),
            "base_distance_m": self._base_distance_m,
            "grid_size": int(self.grid_combo.currentText()),
            "seed": self._seed,
        }

    def _on_slider_changed(self, *args):
        self._update_value_labels()
        self._debounce.start(self.DEBOUNCE_MS)

    def _randomize_seed(self):
        self._seed = random.randint(0, 1_000_000)
        self.seed_label.setText(f"Seed: {self._seed}")
        self._on_slider_changed()

    def _reset_defaults(self):
        self._set_slider("cn2", DEFAULTS["cn2"], CN2_LOG_MIN, CN2_LOG_MAX, log=True)
        self._set_slider("outer_scale_m", DEFAULTS["outer_scale_m"], OUTER_SCALE_MIN_M, OUTER_SCALE_MAX_M)
        self._set_slider("inner_scale_mm", DEFAULTS["inner_scale_mm"], INNER_SCALE_MIN_MM, INNER_SCALE_MAX_MM)
        self._set_slider("wavelength_nm", DEFAULTS["wavelength_nm"], WAVELENGTH_MIN_NM, WAVELENGTH_MAX_NM)
        self._set_slider("tx_radius_cm", DEFAULTS["tx_radius_cm"], TX_RADIUS_MIN_CM, TX_RADIUS_MAX_CM)
        self._set_slider("rx_radius_cm", DEFAULTS["rx_radius_cm"], RX_RADIUS_MIN_CM, RX_RADIUS_MAX_CM)
        self._set_slider("divergence_mrad", DEFAULTS["divergence_mrad"], DIVERGENCE_LOG_MIN, DIVERGENCE_LOG_MAX, log=True)
        self._set_slider("beam_spread_factor", DEFAULTS["beam_spread_factor"], BEAM_SPREAD_MIN, BEAM_SPREAD_MAX)
        self._set_slider("distance_m", DEFAULTS["distance_m"], DISTANCE_MIN_M, DISTANCE_MAX_M)
        self.grid_combo.setCurrentText(DEFAULTS["grid_size"])
        self._seed = 0
        self.seed_label.setText("Seed: 0")

        self.slice_combo.blockSignals(True)
        self.slice_combo.setCurrentIndex(0)  # Custom
        self.slice_combo.blockSignals(False)
        self._base_distance_m = 0.0
        self.context_label.setText(
            "Calibrating: Custom parameters (no simulation slice — free sandbox)."
        )

        self._on_slider_changed()

    # ------------------------------------------------------------------
    def _run_job(self):
        params = self._current_params()
        self._job_id += 1
        job_id = self._job_id
        self.status_label.setText("Computing…")

        worker = _CalibrationWorker(params)
        self._active_worker = worker  # keep alive until QThreadPool runs it
        worker.signals.finished.connect(
            lambda result, jid=job_id: self._on_result(jid, result)
        )
        worker.signals.error.connect(
            lambda message, jid=job_id: self._on_error(jid, message)
        )
        self._threadpool.start(worker)

    def _on_result(self, job_id, result):
        if job_id != self._job_id:
            return  # a newer slider drag already superseded this job
        self._active_worker = None
        self.status_label.setText("")

        images = result["images"]
        checkpoints = result["checkpoints"]
        widths_m = result["widths_m"]
        r0 = result["r0"]
        eta = result["eta"]

        labels = ["Near", "Mid", "Far"]
        for i, ((img, delta), d, w, label) in enumerate(zip(images, checkpoints, widths_m, labels)):
            ax = self.axes[i]
            ax.clear()
            extent_m = delta * img.shape[0]
            ax.imshow(img, cmap="inferno", origin="lower",
                      extent=[-extent_m / 2, extent_m / 2, -extent_m / 2, extent_m / 2])
            ax.set_title(f"{label}: {d:.0f} m, w={w * 100:.1f} cm", fontsize=9)
            ax.axis("off")

        self.figure.tight_layout()
        self.canvas.draw_idle()

        far_w = widths_m[-1]
        d_over_r0 = (2.0 * far_w) / r0 if r0 > 0 else float("inf")
        self.readout_label.setText(
            f"r\u2080 = {r0 * 100.0:.2f} cm    |    Far beam width w(z) = {far_w * 100.0:.1f} cm    |    "
            f"D/r\u2080 \u2248 {d_over_r0:.2f}    |    \u03b7 (into RX aperture) \u2248 {eta:.3f}"
        )

    def _on_error(self, job_id, message):
        if job_id != self._job_id:
            return
        self._active_worker = None
        self.status_label.setText(f"Error: {message}")
