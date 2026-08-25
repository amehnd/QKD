"""
cumulative_viewer.py
v0.5.0

"Beam Evolution" filmstrip window: shows the beam's cross-section after
each successive atmospheric slice, all cumulative. Opens from a button
on the SCHEMATIC tab.

The heavy FFT work runs on a background QRunnable so the GUI stays
responsive, with a progress bar while it crunches.
"""

from PySide6.QtCore import Qt, QObject, QRunnable, Signal, QThreadPool
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QProgressBar, QScrollArea, QWidget, QSizePolicy,
)

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np

from models.phase_screen import propagate_all_slices


# ── Background worker ─────────────────────────────────────────────────

class _EvolutionWorkerSignals(QObject):
    finished = Signal(list)          # list of result dicts
    error = Signal(str)


class _EvolutionWorker(QRunnable):

    def __init__(self, all_slices, wavelength_m, beam_waist_m, grid_size=256):
        super().__init__()
        self.all_slices = all_slices
        self.wavelength_m = wavelength_m
        self.beam_waist_m = beam_waist_m
        self.grid_size = grid_size
        self.signals = _EvolutionWorkerSignals()

    def run(self):
        try:
            results = propagate_all_slices(
                self.all_slices,
                self.wavelength_m,
                self.beam_waist_m,
                grid_size=self.grid_size,
            )
            self.signals.finished.emit(results)
        except Exception as exc:
            self.signals.error.emit(str(exc))


# ── Viewer dialog ─────────────────────────────────────────────────────

class CumulativeViewer(QDialog):
    """Filmstrip window showing cumulative beam evolution through all slices."""

    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = state
        self._worker_ref = None            # prevent GC

        self.setWindowTitle("Beam Evolution — Cumulative Phase Screen Propagation")
        self.setMinimumSize(960, 520)
        self.resize(1100, 600)
        self.setStyleSheet("""
            QDialog { background-color: #0d1117; }
            QLabel  { color: #e6edf3; }
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        # ── Header ────────────────────────────────────────────────────
        hdr = QLabel("Cumulative Beam Evolution — TX → RX")
        hdr.setStyleSheet("font-size:15px; font-weight:bold; color:#58a6ff;")
        root.addWidget(hdr)

        self.info_label = QLabel("")
        self.info_label.setStyleSheet("font-size:11px; color:#8b949e;")
        root.addWidget(self.info_label)

        # ── Progress bar ──────────────────────────────────────────────
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)        # indeterminate
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(6)
        self.progress.setStyleSheet("""
            QProgressBar        { background: #161b22; border: none; border-radius: 3px; }
            QProgressBar::chunk { background: #58a6ff; border-radius: 3px; }
        """)
        root.addWidget(self.progress)

        # ── Scrollable filmstrip area ─────────────────────────────────
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.NoFrame)
        self.scroll.setStyleSheet("background: #0d1117;")
        root.addWidget(self.scroll, stretch=1)

        # ── Eta chart area ────────────────────────────────────────────
        self.eta_figure = Figure(figsize=(10, 1.8), dpi=100)
        self.eta_figure.patch.set_facecolor("#0d1117")
        self.eta_canvas = FigureCanvas(self.eta_figure)
        self.eta_canvas.setFixedHeight(160)
        root.addWidget(self.eta_canvas)

        # ── Launch computation ────────────────────────────────────────
        self._launch()

    # ──────────────────────────────────────────────────────────────────

    def _launch(self):
        slices = self.state.propagation_slices
        if not slices:
            self.info_label.setText("No propagation slices — run a simulation first.")
            self.progress.hide()
            return

        wavelength_m = self.state.wavelength_nm * 1e-9
        # Derive beam waist from TX aperture (state has tx_aperture_mm, not beam_waist_m)
        if self.state.tx_aperture_mm > 0:
            beam_waist_m = (self.state.tx_aperture_mm / 1000.0) / 2.0
        elif slices[0].beam_radius_m > 0:
            beam_waist_m = slices[0].beam_radius_m
        else:
            beam_waist_m = 0.05

        n = len(slices)
        link_km = self.state.link_distance_km
        self.info_label.setText(
            f"λ = {self.state.wavelength_nm:.0f} nm  |  "
            f"Link = {link_km:.2f} km  |  "
            f"{n} slices  |  Computing…"
        )

        worker = _EvolutionWorker(slices, wavelength_m, beam_waist_m, grid_size=256)
        self._worker_ref = worker
        worker.signals.finished.connect(self._on_finished)
        worker.signals.error.connect(self._on_error)
        QThreadPool.globalInstance().start(worker)

    # ──────────────────────────────────────────────────────────────────

    def _on_finished(self, results):
        self.progress.hide()
        if not results:
            self.info_label.setText("No results.")
            return

        n = len(results)
        link_km = self.state.link_distance_km
        self.info_label.setText(
            f"λ = {self.state.wavelength_nm:.0f} nm  |  "
            f"Link = {link_km:.2f} km  |  "
            f"{n} slices  |  TX aperture = {self.state.tx_aperture_mm:.0f} mm"
        )

        # ── Build filmstrip ───────────────────────────────────────────
        # Determine grid layout: try to keep ~5 columns
        cols = min(n, 5)
        rows = (n + cols - 1) // cols

        fig = Figure(figsize=(3.0 * cols, 3.2 * rows), dpi=100)
        fig.patch.set_facecolor("#0d1117")

        # Global intensity scale for consistent colour mapping
        vmin = min(r["intensity"].min() for r in results)
        vmax = max(r["intensity"].max() for r in results)

        for i, r in enumerate(results):
            ax = fig.add_subplot(rows, cols, i + 1)
            ax.imshow(r["intensity"], cmap="inferno", origin="lower",
                      vmin=vmin, vmax=vmax)
            ax.set_title(
                f"Slice {r['slice_id']}\n"
                f"{r['distance_m']:.0f} m   r₀={r['r0']*100:.1f}cm",
                fontsize=8, color="white", pad=4,
            )
            ax.set_xlabel(f"η = {r['eta']:.3f}", fontsize=8, color="#4fc3f7")
            ax.tick_params(colors="#555", labelsize=5)
            ax.set_facecolor("#0d1117")
            for spine in ax.spines.values():
                spine.set_color("#30363d")

        fig.tight_layout(pad=1.5)

        canvas = FigureCanvas(fig)
        canvas.setMinimumHeight(int(3.2 * rows * 100))
        self.scroll.setWidget(canvas)

        # ── Eta trend chart ───────────────────────────────────────────
        self.eta_figure.clear()
        ax_eta = self.eta_figure.add_subplot(111)
        ax_eta.set_facecolor("#0d1117")

        distances = [r["distance_m"] for r in results]
        etas = [r["eta"] for r in results]

        ax_eta.fill_between(distances, etas, alpha=0.25, color="#ff7043")
        ax_eta.plot(distances, etas, "-o", color="#ff7043", markersize=4, linewidth=1.5)

        ax_eta.set_xlabel("Distance from TX (m)", color="white", fontsize=9)
        ax_eta.set_ylabel("Aperture η", color="white", fontsize=9)
        ax_eta.set_title(
            "Cumulative Aperture Transmittance Along Link",
            color="white", fontsize=10, fontweight="bold",
        )
        ax_eta.set_ylim(0, 1.05)
        ax_eta.tick_params(colors="white", labelsize=7)
        ax_eta.grid(axis="y", color="#30363d", linewidth=0.4, alpha=0.6)
        for spine in ax_eta.spines.values():
            spine.set_color("#30363d")

        self.eta_figure.tight_layout()
        self.eta_canvas.draw_idle()

    def _on_error(self, message):
        self.progress.hide()
        self.info_label.setText(f"Error: {message}")
        self.info_label.setStyleSheet("font-size:11px; color:#f85149;")
