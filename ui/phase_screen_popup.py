"""
phase_screen_popup.py
v0.5.0

Transient hover popup for the SCHEMATIC tab: shows a per-slice phase
screen's effect on the beam at near/mid/far distances. Frameless,
tooltip-like, shown/hidden on hover -- not a docked panel.

v0.5.0: Expanded to two rows —
  Row 1 (CUMULATIVE):  beam after split-step propagation through slices 1…N
  Row 2 (INDEPENDENT): existing per-slice fresh-beam diagnostic
"""

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame


class PhaseScreenPopup(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent, Qt.ToolTip | Qt.FramelessWindowHint)

        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setFixedSize(600, 480)

        self.setStyleSheet("""
            PhaseScreenPopup {
                background-color: #fdfdfd;
                border: 1px solid #9DBCEB;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(3)

        # ── Title ──────────────────────────────────────────────────────
        self.title_label = QLabel("")
        self.title_label.setStyleSheet("font-weight:bold; font-size:11px; color:#0B57D0;")
        layout.addWidget(self.title_label)

        self.status_label = QLabel("Generating phase screens...")
        self.status_label.setStyleSheet("font-size:10px; color:#555;")
        layout.addWidget(self.status_label)

        # ── Row 1: Cumulative ──────────────────────────────────────────
        self.cum_label = QLabel("▎ CUMULATIVE (slices 1 → N)")
        self.cum_label.setStyleSheet(
            "font-weight:bold; font-size:10px; color:#E65100; margin-top:2px;"
        )
        layout.addWidget(self.cum_label)

        self.cum_eta_label = QLabel("")
        self.cum_eta_label.setStyleSheet("font-size:9px; color:#555;")
        layout.addWidget(self.cum_eta_label)

        self.cum_figure = Figure(figsize=(5.6, 1.7), dpi=100)
        self.cum_figure.patch.set_facecolor("#fafafa")
        self.cum_canvas = FigureCanvas(self.cum_figure)
        self.cum_axes = self.cum_figure.subplots(1, 3)
        for ax in self.cum_axes:
            ax.axis("off")
        layout.addWidget(self.cum_canvas)

        # ── Row 2: Independent ─────────────────────────────────────────
        self.ind_label = QLabel("▎ INDEPENDENT (this slice only)")
        self.ind_label.setStyleSheet(
            "font-weight:bold; font-size:10px; color:#2E7D32; margin-top:2px;"
        )
        layout.addWidget(self.ind_label)

        self.ind_eta_label = QLabel("")
        self.ind_eta_label.setStyleSheet("font-size:9px; color:#555;")
        layout.addWidget(self.ind_eta_label)

        self.ind_figure = Figure(figsize=(5.6, 1.7), dpi=100)
        self.ind_figure.patch.set_facecolor("#fafafa")
        self.ind_canvas = FigureCanvas(self.ind_figure)
        self.ind_axes = self.ind_figure.subplots(1, 3)
        for ax in self.ind_axes:
            ax.axis("off")
        layout.addWidget(self.ind_canvas)

        # Track which results have arrived for this hover
        self._cum_ready = False
        self._ind_ready = False

        frame = QFrame()
        frame.setFrameShape(QFrame.NoFrame)

    def clamp_to_screen(self, anchor_pos, offset=QPoint(16, 16)):
        """Position the popup near anchor_pos without letting it run off-screen.

        Flips to the left/above the cursor when it would otherwise overflow
        the right/bottom edge of the screen the cursor is on.
        """
        target = anchor_pos + offset
        w, h = self.width(), self.height()

        screen = QGuiApplication.screenAt(anchor_pos) or QGuiApplication.primaryScreen()
        avail = screen.availableGeometry() if screen else None

        if avail is not None:
            if target.x() + w > avail.right():
                target.setX(anchor_pos.x() - w - offset.x())
            if target.y() + h > avail.bottom():
                target.setY(anchor_pos.y() - h - offset.y())
            target.setX(max(avail.left(), min(target.x(), avail.right() - w)))
            target.setY(max(avail.top(), min(target.y(), avail.bottom() - h)))

        return target

    def show_loading(self, slice_obj, global_pos):
        self.title_label.setText(
            f"Slice {slice_obj.slice_id}  |  Cn² = {slice_obj.Cn2:.2e} m⁻²ᐟ³"
        )
        self.status_label.setText("Generating phase screens...")
        self.status_label.show()

        self._cum_ready = False
        self._ind_ready = False
        self.cum_eta_label.setText("")
        self.ind_eta_label.setText("")

        for ax in self.cum_axes:
            ax.clear()
            ax.axis("off")
        self.cum_canvas.draw_idle()

        for ax in self.ind_axes:
            ax.clear()
            ax.axis("off")
        self.ind_canvas.draw_idle()

        self.move(global_pos)
        self.show()
        self.raise_()

    def _maybe_hide_status(self):
        if self._cum_ready and self._ind_ready:
            self.status_label.hide()

    def show_result(self, distances_m, images, eta_far, r0_used_m):
        """Display INDEPENDENT (per-slice) result — bottom row."""
        self._ind_ready = True
        self._maybe_hide_status()

        self.ind_eta_label.setText(
            f"r₀ = {r0_used_m * 100.0:.2f} cm   |   η ≈ {eta_far:.3f}"
        )

        labels = ["Near", "Mid", "Far"]
        for ax, img, d, label in zip(self.ind_axes, images, distances_m, labels):
            ax.clear()
            ax.imshow(img, cmap="inferno", origin="lower")
            ax.set_title(f"{label} ({d:.0f} m)", fontsize=8, color="#2E7D32")
            ax.axis("off")

        self.ind_figure.tight_layout()
        self.ind_canvas.draw_idle()

    def show_cumulative_result(self, distances_m, images, eta_far, r0_used_m, num_slices):
        """Display CUMULATIVE (split-step) result — top row."""
        self._cum_ready = True
        self._maybe_hide_status()

        self.cum_label.setText(
            f"▎ CUMULATIVE (through {num_slices} slice{'s' if num_slices != 1 else ''})"
        )
        self.cum_eta_label.setText(
            f"r₀ (target) = {r0_used_m * 100.0:.2f} cm   |   η ≈ {eta_far:.3f}"
        )

        labels = ["Near", "Mid", "Far"]
        for ax, img, d, label in zip(self.cum_axes, images, distances_m, labels):
            ax.clear()
            ax.imshow(img, cmap="inferno", origin="lower")
            ax.set_title(f"{label} ({d:.0f} m)", fontsize=8, color="#E65100")
            ax.axis("off")

        self.cum_figure.tight_layout()
        self.cum_canvas.draw_idle()

    def show_error(self, message):
        self.status_label.setText(f"Error: {message}")
        self.status_label.show()
        self.ind_eta_label.setText("")
        for ax in self.ind_axes:
            ax.clear()
            ax.axis("off")
        self.ind_canvas.draw_idle()

    def show_cumulative_error(self, message):
        self.cum_eta_label.setText(f"Cumulative error: {message}")
        for ax in self.cum_axes:
            ax.clear()
            ax.axis("off")
        self.cum_canvas.draw_idle()
