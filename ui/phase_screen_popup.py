"""
phase_screen_popup.py
v0.4.1

Transient hover popup for the SCHEMATIC tab: shows a per-slice phase
screen's effect on the beam at near/mid/far distances. Frameless,
tooltip-like, shown/hidden on hover -- not a docked panel.
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
        self.setFixedSize(560, 260)

        self.setStyleSheet("""
            PhaseScreenPopup {
                background-color: #fdfdfd;
                border: 1px solid #9DBCEB;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        self.title_label = QLabel("")
        self.title_label.setStyleSheet("font-weight:bold; font-size:11px; color:#0B57D0;")
        layout.addWidget(self.title_label)

        self.status_label = QLabel("Generating phase screen...")
        self.status_label.setStyleSheet("font-size:10px; color:#555;")
        layout.addWidget(self.status_label)

        self.eta_label = QLabel("")
        self.eta_label.setStyleSheet("font-size:10px; color:#555;")
        layout.addWidget(self.eta_label)

        self.figure = Figure(figsize=(5.4, 1.9), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.axes = self.figure.subplots(1, 3)
        for ax in self.axes:
            ax.axis("off")
        layout.addWidget(self.canvas)

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
            f"Slice {slice_obj.slice_id}  |  Cn2 = {slice_obj.Cn2:.2e} m^-2/3"
        )
        self.status_label.setText("Generating phase screen...")
        self.status_label.show()
        self.eta_label.setText("")

        for ax in self.axes:
            ax.clear()
            ax.axis("off")
        self.canvas.draw_idle()

        self.move(global_pos)
        self.show()
        self.raise_()

    def show_result(self, distances_m, images, eta_far, r0_used_m):
        self.status_label.hide()
        self.eta_label.setText(
            f"Phase screen r0 (Cn2 over a fixed 100 m reference): {r0_used_m * 100.0:.2f} cm   |   "
            f"Estimated aperture transmittance (far, single realization): eta ~= {eta_far:.2f}"
        )

        labels = ["Near", "Mid", "Far"]
        for ax, img, d, label in zip(self.axes, images, distances_m, labels):
            ax.clear()
            ax.imshow(img, cmap="inferno", origin="lower")
            ax.set_title(f"{label} ({d:.0f} m)", fontsize=9)
            ax.axis("off")

        self.figure.tight_layout()
        self.canvas.draw_idle()

    def show_error(self, message):
        self.status_label.setText(f"Error: {message}")
        self.status_label.show()
        self.eta_label.setText("")
        for ax in self.axes:
            ax.clear()
            ax.axis("off")
        self.canvas.draw_idle()
