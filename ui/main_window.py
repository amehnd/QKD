"""
FSO/QKmatplotlib.backends.backend_qtagg.3 COMPLETE OUTPUT SYSTEM
LIVE PHYSICS VERIFIER
NON-SCROLL SINGLE WINDOW
"""

from plots.mpl_canvas import MplCanvas
from plots.plot_manager import PlotManager
from ui.phase_screen_popup import PhaseScreenPopup
from ui.phase_screen_worker import PhaseScreenWorker, CumulativePhaseScreenWorker
from ui.cumulative_viewer import CumulativeViewer
from PySide6.QtWidgets import QScrollArea
from PySide6.QtWidgets import QPlainTextEdit
from core.logger import logger
from core.ui_database import (
    INPUT_DATABASE,
    DETECTOR_DATABASE,
    INPUT_LIMITS,
)
from core.output_database import OUTPUT_DATABASE
from core.qkd_input_database import QKD_INPUT_DATABASE
from core.qkd_output_database import QKD_OUTPUT_DATABASE
from core.settings_manager import SettingsManager

from matplotlib.backends.backend_qtagg import NavigationToolbar2QT

from PySide6.QtWidgets import QHBoxLayout
from PySide6.QtWidgets import QSplitter
from PySide6.QtCore import Qt, QThreadPool, QTimer
from PySide6.QtGui import QPainter, QPen, QColor, QBrush, QPainterPath
import math
import json
import time
import os
import subprocess
import socket
import time
import sys
import webbrowser
import numpy as np


from PySide6.QtWidgets import (
    QGridLayout,
    QMainWindow,
    QSizePolicy,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QGroupBox,
    QFrame,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QLabel,
    QCheckBox,
    QRadioButton,
    QComboBox,
    QToolButton,
    QSizePolicy,
    QMessageBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
)


class CollapsibleSection(QWidget):

    def __init__(self, title):

        super().__init__()

        self.toggle_btn = QToolButton()

        self.toggle_btn.setFixedHeight(14)
        self.toggle_btn.setText(f"▶ {title}")
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.setChecked(False)

        self.content = QWidget()
        self.content.hide()

        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(8, 0, 0, 0)
        self.content.setLayout(self.content_layout)

        layout = QVBoxLayout()
        layout.addWidget(self.toggle_btn)
        layout.addWidget(self.content)

        self.setLayout(layout)

        self.toggle_btn.clicked.connect(self.toggle_section)

        self.toggle_btn.setMaximumHeight(16)
        self.toggle_btn.setMinimumHeight(16)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        self.content_layout.setSpacing(0)

    def toggle_section(self):

        expanded = self.toggle_btn.isChecked()

        if expanded:

            self.toggle_btn.setText(self.toggle_btn.text().replace("▶", "▼"))

            self.content.show()

        else:
            self.toggle_btn.setText(self.toggle_btn.text().replace("▼", "▶"))
            self.content.hide()

    def addWidget(self, widget):

        widget.setMinimumHeight(22)

        self.content_layout.addWidget(widget)


class PropagationWidget(QWidget):

    def __init__(self, state):
        super().__init__()

        self.state = state

        self.setMinimumSize(900, 500)
        self.slice_screen_positions = []
        self.info_box = None

        # Phase screen hover popup (v0.4.1)
        self.setMouseTracking(True)
        self._phase_threadpool = QThreadPool.globalInstance()
        self._phase_popup = None
        self._hover_slice_id = None
        self._hover_job_id = 0
        self._active_phase_workers = {}

        # Debounce: the mouse sweeps across many markers per second in
        # densely-packed regions (e.g. near RX, where dozens of slices can
        # sit within a few dozen pixels). Without this, every transient
        # slice_id the cursor passes over immediately queued a full FFT
        # worker onto the shared QThreadPool -- those stale jobs still ran
        # to completion (nothing cancels a QRunnable already queued), so a
        # quick sweep could back the pool up with dozens of throwaway jobs
        # and make the hover the user actually paused on appear to never
        # respond. Only submit a worker once the cursor has rested on one
        # slice for HOVER_DEBOUNCE_MS.
        self.HOVER_DEBOUNCE_MS = 100
        self._hover_debounce_timer = QTimer(self)
        self._hover_debounce_timer.setSingleShot(True)
        self._hover_debounce_timer.timeout.connect(self._start_pending_phase_screen_job)
        self._pending_hover_slice = None
        self._pending_hover_global_pos = None

    def paintEvent(self, event):

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("white"))

        w = self.width()
        h = self.height()

        margin = 80

        tx_x = margin
        rx_x = w - margin

        slices = self.state.propagation_slices

        if not slices:
            return
        # ==========================================
        # Geometry
        # ==========================================

        total = self.state.link_distance_km * 1000.0

        Re = self.state.effective_earth_radius_m

        if Re <= 0:
            Re = self.state.earth_radius_m * self.state.effective_earth_radius_factor

        # ==========================================
        # Dynamic screen scaling
        # ==========================================

        top_margin = 80
        bottom_margin = 70

        earth_base_y = h - bottom_margin

        drawing_height = earth_base_y - top_margin

        max_drop = total * total / (8.0 * Re)

        max_beam_height = max(
            self.state.tx_height_msl_m,
            self.state.rx_height_msl_m,
            max(s.beam_height_m for s in slices),
        )
        VERTICAL_EXAGGERATION = 100.0

        # Real geometry height
        world_height = max_drop + max_beam_height

        # Vertical exaggeration (display only)
        VERTICAL_EXAGGERATION = 100.0

        display_height = max_drop + max_beam_height * VERTICAL_EXAGGERATION

        pixels_per_meter = drawing_height / max(display_height, 1.0)

        earth_scale = pixels_per_meter
        beam_scale = pixels_per_meter * VERTICAL_EXAGGERATION

        # ==========================================
        # Draw Earth
        # ==========================================

        earth_path = QPainterPath()

        first = True

        for i in range(201):

            d = total * i / 200.0

            x = tx_x + d / total * (rx_x - tx_x)

            drop = d * (total - d) / (2.0 * Re)

            # Apply the same vertical exaggeration to Earth curvature
            visual_drop = drop * earth_scale * VERTICAL_EXAGGERATION

            y = earth_base_y - visual_drop
            if first:
                earth_path.moveTo(x, y)
                first = False
            else:
                earth_path.lineTo(x, y)

        painter.setPen(QPen(QColor(0, 120, 0), 3))
        painter.drawPath(earth_path)

        # ==========================================
        # Draw Beam (Straight LOS)
        # ==========================================

        beam_points = []

        tx_y = earth_base_y - self.state.tx_height_msl_m * beam_scale
        rx_y = earth_base_y - self.state.rx_height_msl_m * beam_scale

        for s in slices:

            fraction = s.center_m / total

            x = tx_x + fraction * (rx_x - tx_x)

            y = tx_y + fraction * (rx_y - tx_y)

            beam_points.append((x, y))

        beam_path = QPainterPath()

        beam_path.moveTo(tx_x, tx_y)
        beam_path.lineTo(rx_x, rx_y)

        # ==========================================
        # Draw slice markers
        # ==========================================

        self.slice_screen_positions.clear()

        for i, s in enumerate(slices):

            if i == len(slices) - 1:
                # Last slice ends at RX
                x = rx_x
                y = rx_y
            else:
                fraction = s.end_m / total
                x = tx_x + fraction * (rx_x - tx_x)
                y = tx_y + fraction * (rx_y - tx_y)
            self.slice_screen_positions.append((int(x), s))

            if hasattr(self, "selected_slice") and self.selected_slice == s:
                painter.setPen(QPen(Qt.red, 4))
            else:
                painter.setPen(QPen(Qt.blue, 2))

            painter.drawEllipse(int(x) - 4, int(y) - 4, 8, 8)
            # Draw slice horizontal bar

            start_x = tx_x + (s.start_m / total) * (rx_x - tx_x)

            end_x = tx_x + (s.end_m / total) * (rx_x - tx_x)

            painter.setPen(QPen(QColor(180, 180, 180), 2))

            # Draw clearance line

            drop = (s.end_m * (total - s.end_m)) / (2.0 * Re)
            earth_x = x
            earth_screen_y = earth_base_y - drop * earth_scale * VERTICAL_EXAGGERATION
            painter.setPen(QPen(QColor(0, 120, 0), 1))

            painter.drawLine(int(x), int(y), int(earth_x), int(earth_screen_y))
            # Make RX represent the last slice

        painter.setPen(QPen(Qt.black, 3))
        painter.drawPath(beam_path)
        painter.setPen(QPen(Qt.black, 3))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(tx_x - 6, int(tx_y) - 6, 12, 12)
        painter.drawEllipse(rx_x - 6, int(rx_y) - 6, 12, 12)
        painter.drawText(tx_x - 18, int(tx_y) - 15, "TX")
        painter.drawText(rx_x - 10, int(rx_y) - 15, "RX")
        painter.setPen(QPen(QColor(0, 120, 0), 1))
        # TX
        painter.drawLine(tx_x, int(tx_y), tx_x, earth_base_y)

        # RX
        painter.drawLine(rx_x, int(rx_y), rx_x, earth_base_y)

    def mousePressEvent(self, event):

        click_x = event.position().x()

        nearest = None
        best_distance = 1e9

        for screen_x, s in self.slice_screen_positions:

            d = abs(click_x - screen_x)

            if d < best_distance:

                best_distance = d
                nearest = s
                self.selected_slice = nearest
                self.update()

        if nearest is None:
            return

        self.update_slice_info()

    def mouseMoveEvent(self, event):

        if not self.slice_screen_positions:
            return

        move_x = event.position().x()

        nearest = None
        best_distance = 1e9

        for screen_x, s in self.slice_screen_positions:
            d = abs(move_x - screen_x)
            if d < best_distance:
                best_distance = d
                nearest = s

        # Hit-test radius is intentionally generous -- it was not the cause
        # of the "hover does nothing near RX" reports (see debounce below).
        HOVER_RADIUS_PX = 18

        if nearest is None or best_distance > HOVER_RADIUS_PX:
            if self._hover_slice_id is not None:
                self._hover_slice_id = None
                self._hover_job_id += 1
                self._hover_debounce_timer.stop()
                self._pending_hover_slice = None
                if self._phase_popup is not None:
                    self._phase_popup.hide()
            return

        if nearest.slice_id == self._hover_slice_id:
            return

        self._hover_slice_id = nearest.slice_id

        # Debounce: remember this slice as the pending hover target and
        # (re)start the timer. If the mouse moves to a different slice
        # before the timer fires, this call runs again and QTimer.start()
        # restarts the countdown, so only the slice the cursor actually
        # settles on ever reaches _start_pending_phase_screen_job().
        self._pending_hover_slice = nearest
        self._pending_hover_global_pos = self.mapToGlobal(event.position().toPoint())
        self._hover_debounce_timer.start(self.HOVER_DEBOUNCE_MS)

    def _start_pending_phase_screen_job(self):
        nearest = self._pending_hover_slice
        if nearest is None or nearest.slice_id != self._hover_slice_id:
            # Cursor already moved on (or left) since this was scheduled.
            return

        self._hover_job_id += 1
        job_id = self._hover_job_id

        if self._phase_popup is None:
            self._phase_popup = PhaseScreenPopup(self)

        global_pos = self._phase_popup.clamp_to_screen(self._pending_hover_global_pos)
        self._phase_popup.show_loading(nearest, global_pos)

        wavelength_m = self.state.wavelength_nm * 1e-9
        total_link_m = self.state.link_distance_km * 1000.0

        # ── Independent worker (existing, bottom row) ──────────────
        worker = PhaseScreenWorker(nearest, wavelength_m, total_link_m=total_link_m)
        # Keep a Python reference until the job completes -- otherwise the
        # QRunnable/its signals QObject can be garbage-collected before
        # QThreadPool runs it, silently dropping the result.
        self._active_phase_workers[(job_id, 'ind')] = worker
        worker.signals.finished.connect(
            lambda slice_id, distances_m, images, eta_far, r0_used, jid=job_id: self._on_phase_screen_ready(
                jid, slice_id, distances_m, images, eta_far, r0_used
            )
        )
        worker.signals.error.connect(
            lambda slice_id, message, jid=job_id: self._on_phase_screen_error(jid, slice_id, message)
        )
        self._phase_threadpool.start(worker)

        # ── Cumulative worker (new, top row) ───────────────────────
        all_slices = self.state.propagation_slices
        if all_slices:
            # Find the index of the hovered slice in the list
            target_idx = None
            for idx, s in enumerate(all_slices):
                if s.slice_id == nearest.slice_id:
                    target_idx = idx
                    break

            if target_idx is not None:
                beam_waist_m = nearest.beam_radius_m
                if beam_waist_m <= 0:
                    beam_waist_m = max(nearest.beam_diameter_m / 2.0, 0.02)

                cum_worker = CumulativePhaseScreenWorker(
                    all_slices, target_idx, wavelength_m,
                    beam_waist_m, total_link_m=total_link_m,
                )
                self._active_phase_workers[(job_id, 'cum')] = cum_worker
                cum_worker.signals.finished.connect(
                    lambda slice_id, distances_m, images, eta_far, r0_used, jid=job_id, n=target_idx+1:
                        self._on_cumulative_phase_screen_ready(
                            jid, slice_id, distances_m, images, eta_far, r0_used, n
                        )
                )
                cum_worker.signals.error.connect(
                    lambda slice_id, message, jid=job_id:
                        self._on_cumulative_phase_screen_error(jid, slice_id, message)
                )
                self._phase_threadpool.start(cum_worker)

    def _on_phase_screen_ready(self, job_id, slice_id, distances_m, images, eta_far, r0_used):
        self._active_phase_workers.pop((job_id, 'ind'), None)
        if job_id != self._hover_job_id or slice_id != self._hover_slice_id:
            return
        if self._phase_popup is not None:
            self._phase_popup.show_result(distances_m, images, eta_far, r0_used)

    def _on_phase_screen_error(self, job_id, slice_id, message):
        self._active_phase_workers.pop((job_id, 'ind'), None)
        if job_id != self._hover_job_id or slice_id != self._hover_slice_id:
            return
        if self._phase_popup is not None:
            self._phase_popup.show_error(message)

    def _on_cumulative_phase_screen_ready(self, job_id, slice_id, distances_m, images, eta_far, r0_used, num_slices):
        self._active_phase_workers.pop((job_id, 'cum'), None)
        if job_id != self._hover_job_id or slice_id != self._hover_slice_id:
            return
        if self._phase_popup is not None:
            self._phase_popup.show_cumulative_result(distances_m, images, eta_far, r0_used, num_slices)

    def _on_cumulative_phase_screen_error(self, job_id, slice_id, message):
        self._active_phase_workers.pop((job_id, 'cum'), None)
        if job_id != self._hover_job_id or slice_id != self._hover_slice_id:
            return
        if self._phase_popup is not None:
            self._phase_popup.show_cumulative_error(message)

    def leaveEvent(self, event):
        self._hover_slice_id = None
        self._hover_job_id += 1
        self._hover_debounce_timer.stop()
        self._pending_hover_slice = None
        if self._phase_popup is not None:
            self._phase_popup.hide()
        super().leaveEvent(event)

    def update_slice_info(self):
        if not hasattr(self, "selected_slice") or self.selected_slice is None:
            return

        if self.info_box is None:
            return

        from core.state import PropagationSlice

        # Dynamically extract all attributes from the nearest slice
        hidden_fields = {
            "wind_direction_deg",
            "refinement_level",
            "dn_dz",
            "surface_height_m",
            "beam_above_surface_m",
            "height_above_msl_m",
            "start_height_m",
            "center_height_m",
            "end_height_m",
            "earth_drop_m",
            "start_distance_m",
            "end_distance_m",
            "center_distance_m",
            # Legacy leftover from the "dynamically injected attributes now
            # statically declared" migration (core/state.py). No per-slice
            # turbulence code ever writes this field (only the real "Cn2"
            # field is set, in models/turbulence.py) -- it just sits at a
            # stale value. Worse, format_attribute_name() strips the
            # "_m2_3" unit suffix, so it rendered as a second box also
            # labelled "Cn2" with a wildly different (wrong) number right
            # next to the real one. Hide it rather than show a bogus
            # duplicate; the real per-slice value is the "Cn2" field.
            "Cn2_m2_3",
        }

        selected_category = "All Parameters"
        if hasattr(self, "category_combo") and self.category_combo is not None:
            selected_category = self.category_combo.currentText()

        container = QWidget()
        layout = QGridLayout(container)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        for i in range(4):
            layout.setColumnStretch(i, 1)

        row = 0
        col = 0
        for attr, value in vars(self.selected_slice).items():
            # Skip hidden attributes
            if attr.startswith("_") or attr in hidden_fields:
                continue

            if (
                selected_category != "All Parameters"
                and PropagationSlice.get_category(attr) != selected_category
            ):
                continue

            name = PropagationSlice.format_attribute_name(attr)
            val_str = PropagationSlice.format_value(value, attr)

            box = QFrame()
            box.setFrameShape(QFrame.StyledPanel)
            box.setFrameShadow(QFrame.Raised)

            box_layout = QVBoxLayout(box)
            box_layout.setContentsMargins(4, 4, 4, 4)
            box_layout.setSpacing(2)

            name_label = QLabel(name)
            val_label = QLabel(val_str)

            box_layout.addWidget(name_label)
            box_layout.addWidget(val_label)

            layout.addWidget(box, row, col)

            col += 1
            if col == 4:
                col = 0
                row += 1

        # Push everything up
        layout.setRowStretch(row if col == 0 else row + 1, 1)

        self.info_box.setWidget(container)


class MainWindow(QMainWindow):

    def __init__(self, state):
        self.state = state
        super().__init__()

        self.setWindowTitle("FSO/QKD FULL PHYSICS DASHBOARD - MERGED (v0.4.1)")
        self.resize(1400, 900)
        self.setMinimumSize(1200, 800)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.setMaximumWidth(2000)

        self.setStyleSheet("""

/* ==========================================================
   LABELS
========================================================== */

QLabel
{
    font-size:11px;
    color:#202124;
}

/* ==========================================================
   GROUP BOXES
========================================================== */

QGroupBox {
    font-size: 11px;
    font-weight: bold;
    color: #0B57D0;             /* Blue title */
    border: 1px solid #9DBCEB;  /* Blue border */
    border-radius: 4px;
    margin-top: 10px;
    padding-top: 8px;
    background: white;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    padding: 0 6px;
    background: white;
    color: #0B57D0;
    font-weight: 700;
}

/* ==========================================================
   INPUTS
========================================================== */

QLineEdit {
    font-size: 11px;
}

QComboBox
{
    font-size:11px;

    background:white;

    border:1px solid #9DBCEB;

    border-radius:4px;

    padding-left:6px;

    min-height:22px;
}

QComboBox:hover
{
    border:1px solid #0B57D0;
}

QComboBox::drop-down
{
    border:none;
    width:18px;
}

/* ==========================================================
   BUTTONS
========================================================== */

QPushButton
{
    font-size:11px;

    background:white;

    border:1px solid #9DBCEB;

    border-radius:4px;

    min-height:24px;
}

QPushButton:hover
{
    background:#E8F0FE;
}

QPushButton:pressed
{
    background:#DCEBFF;
}

/* ==========================================================
   CHECK/RADIO
========================================================== */

QCheckBox
{
    font-size:11px;
    spacing:6px;
}

QRadioButton {
    font-size: 11px;
}
/* ==========================================================
   MAIN TABS
========================================================== */

QTabWidget::pane
{
    border: 1px solid #9DBCEB;
    background: white;
}

QTabBar::tab
{
    background: #F5F8FF;
    color: #0B57D0;
    border: 1px solid #9DBCEB;
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    padding: 6px 14px;
    font-size: 11px;
    font-weight: bold;
}

QTabBar::tab:selected
{
    background: #0B57D0;
    color: white;
    border-color: #0B57D0;
}

QTabBar::tab:hover
{
    background: #E8F0FE;
}
""")
        self.build_ui()
        self.compute()
        self.update_aerosol_fields()

    # ================= SAFE GET =================
    def get(self, w, default=0.0, mn=None, mx=None):

        try:

            x = float(w.text())

            if math.isnan(x) or math.isinf(x):

                return default

            if mn is not None:

                x = max(x, mn)

            if mx is not None:

                x = min(x, mx)

            return x

        except:

            return default

    # ================= INPUT BUILDER =================
    def attach_dynamic_validator(self, line_edit, get_state_var_fn):
        def clamp():
            state_var = get_state_var_fn()
            if not state_var:
                return
            mn, mx = INPUT_LIMITS.get(state_var, (-1e20, 1e20))
            try:
                v = float(line_edit.text())
            except ValueError:
                return
            clamped = max(mn, min(mx, v))
            line_edit.setText(str(round(clamped, 6)))

        line_edit.editingFinished.connect(clamp)

    def make_input(self, val, unit="", name="", state_var=""):
        row = QHBoxLayout()

        row.setSpacing(4)

        row.setContentsMargins(0, 0, 0, 0)
        row.setAlignment(Qt.AlignLeft)

        # FIXED WIDTHS (this is what aligns everything)
        inp = QLineEdit(str(val))
        inp.default_value = str(val)
        from PySide6.QtGui import QDoubleValidator

        if state_var in INPUT_LIMITS:
            mn, mx = INPUT_LIMITS[state_var]
        else:
            mn, mx = (-1e20, 1e20)

        validator = QDoubleValidator(mn, mx, 6)
        validator.setNotation(QDoubleValidator.StandardNotation)
        inp.setValidator(validator)

        def clamp_value():
            try:
                v = float(inp.text())
            except ValueError:
                v = float(inp.default_value)
            v = max(mn, min(mx, v))
            inp.setText(str(round(v, 6)))

        inp.editingFinished.connect(clamp_value)

        if name == "RX Filter Bandwidth":
            step = 0.1
        elif name == "Source Bandwidth":
            step = 0.1
        elif name == "RX Filter Center WL":
            step = 0.1
        elif name == "Aerosol Alpha":
            step = 0.1
        elif name == "Detector QE":
            step = 0.5
        else:
            step = {
                "km": 0.1,
                "m": 0.5,
                "mm": 10,
                "nm": 10,
                "mrad": 0.01,
                "%": 1,
                "°C": 1,
                "m/s": 0.5,
                "Hz": 1,
            }.get(unit, 1)

        btn_minus = QPushButton("▼")
        btn_plus = QPushButton("▲")
        btn_reset = QPushButton("↺")
        btn_reset.setFixedSize(22, 18)
        btn_reset.setToolTip("Reset to default")
        btn_minus.setFixedSize(18, 18)
        btn_plus.setFixedSize(18, 18)
        unit_label = QLineEdit(unit)
        if name in ["Source Brightness", "Finite Key Block Size"]:
            inp.setFixedWidth(120)
        else:
            inp.setFixedWidth(48)

        unit_label.setFixedWidth(32)
        unit_label.setReadOnly(True)
        unit_label.setStyleSheet("border:none; background:transparent; color:gray;")

        def dec():
            try:
                v = float(inp.text())
            except ValueError:
                v = 0
            v = max(mn, v - step)
            inp.setText(str(round(v, 6)))

        def inc():
            try:
                v = float(inp.text())
            except ValueError:
                v = 0
            v = min(mx, v + step)
            inp.setText(str(round(v, 6)))

        def reset():
            inp.setText(inp.default_value)
            clamp_value()

        btn_minus.clicked.connect(dec)
        btn_plus.clicked.connect(inc)
        btn_reset.clicked.connect(reset)

        # IMPORTANT ORDER (locks alignment)
        row.addWidget(inp)
        row.addWidget(btn_minus)
        row.addWidget(btn_plus)
        row.addWidget(btn_reset)
        row.addWidget(unit_label)

        return inp, row

    def make_group(self, title, fields):
        box = QGroupBox(title)

        form = QFormLayout()
        form.setContentsMargins(4, 6, 2, 6)
        form.setSpacing(1)
        form.setVerticalSpacing(2)

        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        form.setFormAlignment(Qt.AlignTop)

        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        widgets = {}
        state_map = {}
        row_map = {}

        if title == "OPTICS":
            box.setMinimumWidth(300)
            box.setMaximumWidth(320)
        else:
            box.setMinimumWidth(360)
            box.setMaximumWidth(380)

        for name, (val, unit, state_var) in fields:

            inp, row = self.make_input(
                val,
                unit,
                name,
                state_var,
            )
            print(name, inp)
            from PySide6.QtGui import QIntValidator

            if name == "Month":
                inp.setValidator(QIntValidator(1, 12))

            elif name == "Day":
                inp.setValidator(QIntValidator(1, 31))

            elif name == "Time of Day":
                inp.setValidator(QIntValidator(0, 24))

            row_widget = QWidget()
            row_widget.setLayout(row)

            row_widget.setMinimumWidth(120)
            row_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            # ---------------------------------------
            # OPTICS HEADINGS
            # ---------------------------------------

            if title == "OPTICS":

                if name == "Wavelength":

                    heading = QLabel("TRANSMITTER")

                    heading.setStyleSheet("font-weight:bold; color:#4FC3F7;")

                    form.addRow(heading)

                elif name == "RX aperture":

                    heading = QLabel("RECEIVER")

                    heading.setStyleSheet("font-weight:bold; color:#4FC3F7;")

                    form.addRow(heading)

            label = QLabel(name)
            if title == "MISSION":
                label.setFixedWidth(150)
            else:
                label.setFixedWidth(145)
            label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

            form.addRow(label, row_widget)

            widgets[name] = inp
            if name == "Month":
                inp.editingFinished.connect(lambda w=inp: self.clamp_int(w, 1, 12))

            elif name == "Day":
                inp.editingFinished.connect(lambda w=inp: self.clamp_int(w, 1, 31))

            elif name == "Time of Day":
                inp.editingFinished.connect(lambda w=inp: self.clamp_int(w, 0, 24))
            row_map[name] = {"label": label, "row": row_widget}
            if state_var not in self.shared_inputs:
                self.shared_inputs[state_var] = []

            self.shared_inputs[state_var].append(inp)

        box.setLayout(form)

        box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        print(title)
        print(widgets.keys())

        return box, widgets, state_map, row_map

    # ================= UI =================

    def rebuild_qkd_protocol_inputs(self, protocol_name):
        if protocol_name not in QKD_INPUT_DATABASE["PROTOCOL"]:
            return

        # Clear existing
        while self.qkd_protocol_container_layout.count():
            item = self.qkd_protocol_container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Unregister from shared inputs and input sections
        if "PROTOCOL" in self.qkd_input_sections:
            for state_var, widgets in self.qkd_shared_inputs.items():
                widgets_to_remove = []
                for w in widgets:
                    if w in self.qkd_input_sections["PROTOCOL"]["widgets"].values():
                        widgets_to_remove.append(w)
                for w in widgets_to_remove:
                    self.qkd_shared_inputs[state_var].remove(w)
                    try:
                        w.textChanged.disconnect(self.trigger_live_update)
                    except:
                        pass

        converted = []
        for name, value, unit, state_var in QKD_INPUT_DATABASE["PROTOCOL"][
            protocol_name
        ]:
            converted.append((name, (value, unit, state_var)))

        box, widgets, state_map, row_map = self.make_group(protocol_name, converted)

        # Add the newly created box to the container
        box.setTitle(f"{protocol_name} INPUTS")
        self.qkd_protocol_container_layout.addWidget(box)

        self.qkd_input_sections["PROTOCOL"] = {
            "box": box,  # Note: this box is unused now, we just took its items
            "widgets": widgets,
            "rows": row_map,
            "state_widgets": state_map,
        }

        for name, inp in widgets.items():
            state_var = next(
                (
                    v[-1]
                    for v in QKD_INPUT_DATABASE["PROTOCOL"][protocol_name]
                    if v[0] == name
                ),
                None,
            )
            if state_var:
                if state_var not in self.qkd_shared_inputs:
                    self.qkd_shared_inputs[state_var] = []
                self.qkd_shared_inputs[state_var].append(inp)
                inp.textChanged.connect(self.trigger_live_update)

    def create_data_mode_output_widget(self):
        output_tabs = QTabWidget()
        debug_log = QPlainTextEdit()
        debug_log.setReadOnly(True)

        logger.attach(debug_log)
        sys.stdout = logger

        geometry_tabs = QTabWidget()
        model_tabs = QTabWidget()
        system_tabs = QTabWidget()
        output_widgets = {}

        geometry_sections = [
            "Geometry",
            "Slicing",
            "Terrain",
            "Solar",
        ]

        model_sections = [
            "Atmosphere",
            "Detector",
            "Turbulence",
            "Tracking",
        ]

        system_sections = [
            "Link",
            "QKD Outputs",
            "Design",
            "System",
        ]

        for section_name, outputs in OUTPUT_DATABASE.items():
            if (
                section_name not in geometry_sections
                and section_name not in model_sections
                and section_name not in system_sections
            ):
                continue
            page = QWidget()
            grid = QGridLayout(page)
            grid.setContentsMargins(6, 6, 6, 6)
            grid.setVerticalSpacing(14)

            value_labels = {}
            row = 0

            for name, state_var, unit in outputs:
                lbl_name = QLabel(name)
                lbl_name.setStyleSheet("font-weight:bold;")

                lbl_value = QLabel("-")
                lbl_value.setTextInteractionFlags(Qt.TextSelectableByMouse)

                value_labels[state_var] = (lbl_value, unit)

                col = (row % 3) * 2
                r = row // 3

                grid.addWidget(lbl_name, r, col)
                grid.addWidget(lbl_value, r, col + 1)
                row += 1

            grid.setColumnStretch(1, 1)
            grid.setColumnStretch(3, 1)
            grid.setColumnStretch(5, 1)

            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setWidget(page)

            if section_name in geometry_sections:
                geometry_tabs.addTab(scroll, section_name)
            elif section_name in model_sections:
                model_tabs.addTab(scroll, section_name)
            elif section_name in system_sections:
                system_tabs.addTab(scroll, section_name)

            output_widgets[section_name] = value_labels

        output_tabs.addTab(geometry_tabs, "Geometry")
        output_tabs.addTab(model_tabs, "Models")
        output_tabs.addTab(system_tabs, "System")
        output_tabs.addTab(debug_log, "Debug Log")

        return output_tabs, output_widgets, debug_log

    def create_data_mode_verifier_widget(self):
        verifier_tabs = QTabWidget()

        geometry_ver_tabs = QTabWidget()
        model_ver_tabs = QTabWidget()
        system_ver_tabs = QTabWidget()

        geo_ver = QTextEdit()
        solar_ver = QTextEdit()
        terrain_ver = QTextEdit()
        slice_ver = QTextEdit()

        atm_ver = QTextEdit()
        turb_ver = QTextEdit()
        track_ver = QTextEdit()
        det_ver = QTextEdit()

        link_ver = QTextEdit()
        sys_ver = QTextEdit()
        qkd_ver = QTextEdit()

        for w in [
            geo_ver,
            solar_ver,
            terrain_ver,
            slice_ver,
            atm_ver,
            turb_ver,
            track_ver,
            det_ver,
            link_ver,
            sys_ver,
            qkd_ver,
        ]:
            w.setReadOnly(True)

        geometry_ver_tabs.addTab(geo_ver, "Geometry")
        geometry_ver_tabs.addTab(solar_ver, "Solar")
        geometry_ver_tabs.addTab(terrain_ver, "Terrain")
        geometry_ver_tabs.addTab(slice_ver, "Slicing")

        model_ver_tabs.addTab(atm_ver, "Atmosphere")
        model_ver_tabs.addTab(turb_ver, "Turbulence")
        model_ver_tabs.addTab(track_ver, "Tracking")
        model_ver_tabs.addTab(det_ver, "Detector")

        system_ver_tabs.addTab(link_ver, "Link")
        system_ver_tabs.addTab(sys_ver, "System")
        system_ver_tabs.addTab(qkd_ver, "QKD Outputs")

        verifier_tabs.addTab(geometry_ver_tabs, "Geometry")
        verifier_tabs.addTab(model_ver_tabs, "Models")
        verifier_tabs.addTab(system_ver_tabs, "System")

        verifier_dict = {
            "geo": geo_ver,
            "solar": solar_ver,
            "terrain": terrain_ver,
            "slice": slice_ver,
            "atm": atm_ver,
            "turb": turb_ver,
            "track": track_ver,
            "det": det_ver,
            "link": link_ver,
            "sys": sys_ver,
            "qkd": qkd_ver,
        }

        return verifier_tabs, verifier_dict

    def build_ui(self):

        root = QWidget()
        self.input_sections = {}
        self.input_name_map = {}
        self.shared_inputs = {}
        self.shared_detector_inputs = {}
        self.detector_sections = []
        self.qkd_input_sections = {}
        self.qkd_shared_inputs = {}
        self.qkd_output_tabs = QTabWidget()
        self.qkd_output_widgets = {}
        self.qkd_verifier_tabs = QTabWidget()
        self.qkd_verifier_labels = {}
        self.data_output_widgets_list = []
        self.data_verifier_dicts_list = []

        for section_name, fields in INPUT_DATABASE.items():

            converted = []

            for name, value, unit, state_var in fields:

                self.input_name_map[name] = state_var

                converted.append((name, (value, unit, state_var)))

            box, widgets, state_map, row_map = self.make_group(section_name, converted)

            self.input_sections[section_name] = {
                "box": box,
                "widgets": widgets,
                "rows": row_map,
                "state_widgets": state_map,
            }
            self.mission_rows = self.input_sections["MISSION"]["rows"]
            # -----------------------------------------
            # Google Maps buttons
            # -----------------------------------------
            self.tx_maps_btn = QPushButton("🗺 Maps")
            self.rx_maps_btn = QPushButton("🗺 Maps")
            self.tx_maps_btn.hide()
            self.rx_maps_btn.hide()

            for b in (self.tx_maps_btn, self.rx_maps_btn):
                b.setFixedSize(65, 22)
                b.setParent(self.input_sections["MISSION"]["box"])
                b.raise_()

            self.tx_maps_btn.clicked.connect(self.open_tx_map)
            self.rx_maps_btn.clicked.connect(self.open_rx_map)

        # ==========================
        # DETECTOR PANEL (empty for now)
        # ==========================

        det_box = QGroupBox("DETECTOR")

        det_box.setMinimumWidth(320)
        det_box.setMaximumWidth(340)

        det_box.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        det_layout = QFormLayout()

        det_layout.setContentsMargins(6, 6, 6, 6)

        det_layout.setSpacing(2)

        det_layout.setVerticalSpacing(2)
        det_layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        det_layout.setFormAlignment(Qt.AlignTop)

        det_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        det_box.setLayout(det_layout)

        self.detector_box = det_box

        self.detector_layout = det_layout

        self.detector_widgets = {}

        self.input_sections["DETECTOR"] = {
            "box": self.detector_box,
            "widgets": self.detector_widgets,
        }
        top_layout = QGridLayout()

        top_layout.setContentsMargins(6, 6, 6, 6)
        top_layout.setHorizontalSpacing(20)
        top_layout.setVerticalSpacing(8)

        # ==========================================
        # DATA MODE LAYOUT
        # ==========================================

        # -------- TOP ROW --------

        top_layout.addWidget(self.input_sections["MISSION"]["box"], 0, 0)
        top_layout.addWidget(self.input_sections["TX_OPTICS"]["box"], 0, 1)
        top_layout.addWidget(self.input_sections["RX_OPTICS"]["box"], 0, 2)
        top_layout.addWidget(self.input_sections["DETECTOR"]["box"], 0, 3)

        # ------- BOTTOM ROW -------

        top_layout.addWidget(self.input_sections["TX_ENVIRONMENT"]["box"], 1, 0)
        top_layout.addWidget(self.input_sections["RX_ENVIRONMENT"]["box"], 1, 1)
        top_layout.addWidget(self.input_sections["TRACKING"]["box"], 1, 2)
        top_layout.addWidget(self.input_sections["MARINE"]["box"], 1, 3)

        if "QKD Inputs" in self.input_sections:
            top_layout.addWidget(self.input_sections["QKD Inputs"]["box"], 2, 0)
            self.input_sections["QKD Inputs"]["box"].hide()

        # ------- COLUMN STRETCH -------

        top_layout.setColumnStretch(0, 3)  # Mission
        top_layout.setColumnStretch(1, 2)  # TX Optics
        top_layout.setColumnStretch(2, 2)  # RX Optics
        top_layout.setColumnStretch(3, 2)  # Detector
        top_widget = QWidget()
        top_widget.setLayout(top_layout)
        top_widget.setMinimumHeight(300)

        top_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        model_bar = QVBoxLayout()

        self.atm_combo = QComboBox()
        self.atm_combo.addItems(["Kim", "Kruse", "Al Naboulsi"])
        self.fog_combo = QComboBox()

        self.fog_combo.addItems(["Advection", "Radiation"])

        self.fog_combo.setFixedWidth(150)

        self.fog_combo.currentTextChanged.connect(
            lambda x: setattr(self.state, "fog_type", x)
        )

        self.turb_combo = QComboBox()
        self.turb_combo.addItems(
            [
                "Hufnagel-Valley",
                "Marine MOST",
                "User Defined",
                "Hybrid",
                "Tatarski",
                "Marine MOST (Remote Sensing 2023)",
            ]
        )

        self.det_combo = QComboBox()
        self.det_combo.addItems(["SPAD", "SNSPD", "APD", "PMT", "TES"])

        self.qkd_combo = QComboBox()
        self.geom_combo = QComboBox()

        self.geom_combo.addItems(
            [
                "Gaussian Beam Theory",
                "Friis-like Optical Model",
                "Gaussian Coupling Model",
            ]
        )
        # ----------------------------
        # Pointing Loss Model
        # ----------------------------

        self.pointing_combo = QComboBox()

        self.pointing_combo.addItems(
            [
                "Gaussian Pointing Error Model",
                "Farid–Hranilovic Model",
            ]
        )
        self.pointing_combo.setFixedWidth(150)
        # ----------------------------
        # Rain Loss Model
        # ----------------------------

        self.rain_combo = QComboBox()

        self.rain_combo.addItems(["Carbonneau", "ITU", "Marshall-Palmer"])

        self.rain_combo.setFixedWidth(150)

        # ----------------------------
        # Molecular Loss Model
        # ----------------------------

        self.molecular_combo = QComboBox()

        self.molecular_combo.addItems(["Beer-Lambert", "HITRAN", "MODTRAN"])

        self.molecular_combo.setFixedWidth(150)

        # ----------------------------
        # Aerosol Loss Model
        # ----------------------------

        self.aerosol_combo = QComboBox()

        self.aerosol_combo.addItems(
            ["Kim", "Kruse", "Ijaz", "Shettle-Fenn", "Angstrom"]
        )

        self.aerosol_combo.setFixedWidth(150)

        self.geom_combo.setFixedWidth(150)
        self.atm_combo.setFixedWidth(150)

        self.turb_combo.setFixedWidth(150)

        self.det_combo.setFixedWidth(150)

        self.qkd_combo.setFixedWidth(150)
        self.qkd_combo.addItems(["Decoy BB84", "BB84", "B92", "BBM92", "E91"])

        self.mission_mode_combo = QComboBox()
        self.tracking_mode_combo = QComboBox()

        self.tracking_mode_combo.addItems(["Manual", "Wave"])

        self.tracking_mode_combo.setCurrentText("Manual")

        self.mission_mode_combo.addItems(["Manual Range", "Coordinates"])
        # ---------------------------------
        # Slice Accuracy
        # ---------------------------------

        self.slice_accuracy_combo = QComboBox()

        self.slice_accuracy_combo.addItems(["Low", "Medium", "High", "Research"])

        self.slice_count_label = QLabel("Estimated Slices : 50")

        self.slice_length_label = QLabel("Average Slice Length : 200 m")

        self.slice_accuracy_combo.currentTextChanged.connect(self.update_slice_accuracy)

        # self.mission_mode_combo.currentTextChanged.connect(lambda _: self.compute())

        self.mission_mode_combo.setFixedWidth(150)
        self.qkd_combo.setCurrentText(self.state.qkd_protocol)
        self.geom_combo.setCurrentText(self.state.geometric_loss_model)
        self.pointing_combo.setCurrentText(self.state.pointing_loss_model)
        self.rain_combo.setCurrentText(self.state.rain_model)

        self.molecular_combo.setCurrentText(self.state.molecular_model)

        self.aerosol_combo.setCurrentText(self.state.aerosol_model)
        self.atm_combo.currentTextChanged.connect(
            lambda x: setattr(self.state, "atmospheric_model", x)
        )
        self.atm_combo.currentTextChanged.connect(self.update_fog_combo)

        self.turb_combo.currentTextChanged.connect(
            lambda x: setattr(self.state, "cn2_model", x)
        )
        self.turb_combo.setCurrentText("Hufnagel-Valley")

        self.det_combo.currentTextChanged.connect(self.update_detector_panel)
        self.tracking_mode_combo.currentTextChanged.connect(self.update_tracking_mode)

        self.det_combo.currentTextChanged.connect(
            lambda x: setattr(self.state, "detector_model", x)
        )
        self.det_combo.setCurrentText("SPAD")

        self.qkd_combo.currentTextChanged.connect(
            lambda x: setattr(self.state, "qkd_protocol", x)
        )
        self.qkd_combo.setCurrentText("Decoy BB84")
        self.state.qkd_protocol = "Decoy BB84"
        self.rain_combo.currentTextChanged.connect(
            lambda x: setattr(self.state, "rain_model", x)
        )

        self.molecular_combo.currentTextChanged.connect(
            lambda x: setattr(self.state, "molecular_model", x)
        )

        self.aerosol_combo.currentTextChanged.connect(
            lambda x: setattr(self.state, "aerosol_model", x)
        )
        self.aerosol_combo.currentTextChanged.connect(self.update_aerosol_fields)

        def geom_changed(x):
            print("UI Changed ->", x)
            self.state.geometric_loss_model = x

        self.geom_combo.currentTextChanged.connect(geom_changed)

        def pointing_changed(x):
            print("Pointing Model ->", x)
            self.state.pointing_loss_model = x

        self.pointing_combo.currentTextChanged.connect(pointing_changed)
        self.mission_mode_combo.currentTextChanged.connect(self.update_mission_mode)

        model_bar.addWidget(QLabel("Atmospheric Model"))

        model_bar.addWidget(self.atm_combo)

        model_bar.addWidget(QLabel("Fog Type"))

        model_bar.addWidget(self.fog_combo)

        model_bar.addSpacing(15)

        model_bar.addWidget(QLabel("Turbulence Model"))

        model_bar.addWidget(self.turb_combo)

        model_bar.addSpacing(15)

        model_bar.addWidget(QLabel("Detector Model"))

        model_bar.addWidget(self.det_combo)

        model_bar.addSpacing(15)

        model_bar.addWidget(QLabel("QKD Protocol"))

        model_bar.addWidget(self.qkd_combo)
        model_bar.addSpacing(15)

        model_bar.addWidget(QLabel("Geometric Loss Model"))

        model_bar.addWidget(self.geom_combo)

        model_bar.addSpacing(15)
        model_bar.addWidget(QLabel("Pointing Loss Model"))

        model_bar.addWidget(self.pointing_combo)

        model_bar.addSpacing(15)
        model_bar.addWidget(QLabel("Rain Loss Model"))

        model_bar.addWidget(self.rain_combo)

        model_bar.addSpacing(15)

        model_bar.addWidget(QLabel("Molecular Loss Model"))

        model_bar.addWidget(self.molecular_combo)

        model_bar.addSpacing(15)

        model_bar.addWidget(QLabel("Aerosol Loss Model"))

        model_bar.addWidget(self.aerosol_combo)

        model_bar.addSpacing(15)

        model_bar.addWidget(QLabel("Mission Mode"))

        model_bar.addWidget(self.mission_mode_combo)
        model_bar.addSpacing(15)
        model_bar.addWidget(QLabel("Solve For"))

        self.solve_for_combo = QComboBox()

        self.solve_for_combo.addItems(
            ["Minimum Height Above Sea", "TX Height", "RX Height"]
        )

        self.solve_for_combo.setCurrentText(self.state.solve_for)

        model_bar.addWidget(self.solve_for_combo)
        self.solve_for_combo.currentTextChanged.connect(self.update_solve_for)

        model_bar.addSpacing(15)

        model_bar.addWidget(QLabel("Tracking Mode"))
        model_bar.addWidget(self.tracking_mode_combo)
        model_bar.addSpacing(15)

        model_bar.addWidget(QLabel("Slice Accuracy"))

        model_bar.addWidget(self.slice_accuracy_combo)

        model_bar.addWidget(self.slice_count_label)

        model_bar.addWidget(self.slice_length_label)

        model_bar.addSpacing(15)
        self.hide_models_btn = QPushButton("◀ Hide Left Panel")

        def toggle_models():
            if left_panel.isVisible():
                left_panel.hide()
                self.main_splitter.setSizes([0, 1450])
                self.hide_models_btn.setText("▶ Show Left Panel")
            else:
                left_panel.show()
                self.main_splitter.setSizes([260, 1190])
                self.hide_models_btn.setText("◀ Hide Left Panel")

        self.hide_models_btn.clicked.connect(toggle_models)

        self.reset_all_btn = QPushButton("↺ Reset All Inputs")

        self.reset_all_btn.clicked.connect(self.reset_all_inputs)

        self.run_btn = QPushButton("▶ Run Simulation")
        self.run_btn.setStyleSheet("""
QPushButton{
    background:#0B57D0;
    color:white;
    border:1px solid #0B57D0;
    border-radius:4px;
    font-weight:bold;
}
QPushButton:hover{
    background:#1A73E8;
}
""")

        self.reset_all_btn.setStyleSheet("""
QPushButton{
    background:#F5F8FF;
    color:#0B57D0;
    border:1px solid #9DBCEB;
    border-radius:4px;
}
QPushButton:hover{
    background:#E8F0FE;
}
""")
        self.debug_checkbox = QCheckBox("Enable Debug Output")
        self.debug_checkbox.setChecked(True)
        self.debug_checkbox.toggled.connect(logger.set_enabled)

        self.run_btn.clicked.connect(self.compute)

        left_panel = QWidget()

        left_layout = QVBoxLayout()

        # left_layout.addWidget(

        # self.hide_models_btn

        # )

        left_layout.addLayout(model_bar)

        left_layout.addStretch()
        left_layout.addWidget(self.reset_all_btn)

        left_layout.addWidget(self.run_btn)
        left_layout.addWidget(self.debug_checkbox)

        left_panel.setLayout(left_layout)
        left_panel.setMinimumWidth(200)

        left_panel.setMaximumWidth(200)

        # OUTPUTS & VERIFIER
        out_tabs, self.output_widgets, self.debug_log = (
            self.create_data_mode_output_widget()
        )
        out_box = QGroupBox("OUTPUTS")
        o = QVBoxLayout()
        o.addWidget(out_tabs)
        out_box.setLayout(o)
        self.data_output_widgets_list.append(self.output_widgets)

        ver_tabs, ver_dict = self.create_data_mode_verifier_widget()
        ver_box = QGroupBox("LIVE VERIFIER (ALL EQUATIONS STEPWISE)")
        v = QVBoxLayout()
        v.addWidget(ver_tabs)
        ver_box.setLayout(v)
        self.geo_ver = ver_dict["geo"]
        self.atm_ver = ver_dict["atm"]
        self.turb_ver = ver_dict["turb"]
        self.track_ver = ver_dict["track"]
        self.link_ver = ver_dict["link"]
        self.det_ver = ver_dict["det"]
        self.qkd_ver = ver_dict["qkd"]
        self.sys_ver = ver_dict["sys"]
        self.data_verifier_dicts_list.append(ver_dict)

        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(out_box)
        bottom_layout.addWidget(ver_box)

        bottom_widget = QWidget()
        bottom_widget.setLayout(bottom_layout)

        bottom_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        data_splitter = QSplitter(Qt.Vertical)

        data_splitter.addWidget(top_widget)

        data_splitter.addWidget(bottom_widget)

        data_splitter.setStretchFactor(0, 1)

        data_splitter.setStretchFactor(1, 1)
        data_splitter.setSizes([500, 400])

        data_tab = QWidget()

        data_layout = QVBoxLayout()

        data_layout.addWidget(data_splitter)

        data_tab.setLayout(data_layout)

        plot_tab = QWidget()

        plot_root = QVBoxLayout()
        # ======================
        # UPPER SPLITTER
        # ======================

        plot_splitter = QSplitter(Qt.Horizontal)

        plot_splitter.setStretchFactor(0, 1)

        plot_splitter.setStretchFactor(1, 1)

        plot_splitter.setStretchFactor(2, 3)

        # LEFT : Sweep Settings

        sweep_box = QGroupBox("SWEEP SETTINGS")

        sweep_box.setMinimumWidth(270)
        sweep_box.setMaximumWidth(300)

        sweep_box.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        sweep_layout = QFormLayout()
        font = self.font()

        font.setPointSize(10)

        sweep_box.setFont(font)

        sweep_layout.setContentsMargins(10, 10, 10, 10)

        sweep_layout.setSpacing(6)

        sweep_layout.setVerticalSpacing(5)

        sweep_layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        sweep_layout.setFormAlignment(Qt.AlignTop)

        sweep_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        self.xaxis_combo = QComboBox()
        self.xaxis_combo.setMinimumWidth(150)
        self.xaxis_combo.setMaximumWidth(180)
        self.xaxis_combo.setMinimumHeight(28)
        print(self.xaxis_combo.style().objectName())

        for section_name, section in INPUT_DATABASE.items():

            for name, _, _, state_var in section:

                display = name

                if section_name == "TX_ENVIRONMENT":
                    display = "TX " + name

                elif section_name == "RX_ENVIRONMENT":
                    display = "RX " + name

                elif section_name == "TX_OPTICS":
                    display = "TX " + name

                elif section_name == "RX_OPTICS":
                    display = "RX " + name

                self.xaxis_combo.addItem(display, state_var)

        self.unit_lbl = QLabel("Min / Max / Step Units")

        self.unit_lbl.setStyleSheet("""

            font-size:9px;

            font-style:italic;

            color:gray;

        """)

        self.xaxis_combo.currentTextChanged.connect(self.update_sweep_unit)

        self.update_sweep_unit()

        self.min_edit = QLineEdit("1")

        self.max_edit = QLineEdit("50")

        self.step_edit = QLineEdit("1")

        self.points_edit = QLineEdit("50")

        self.attach_dynamic_validator(
            self.min_edit, lambda: self.xaxis_combo.currentData()
        )
        self.attach_dynamic_validator(
            self.max_edit, lambda: self.xaxis_combo.currentData()
        )
        self.attach_dynamic_validator(
            self.step_edit, lambda: self.xaxis_combo.currentData()
        )

        self.min_edit.textChanged.connect(
            lambda: self.update_points_from_step(
                self.min_edit,
                self.max_edit,
                self.step_edit,
                self.points_edit,
            )
        )

        self.max_edit.textChanged.connect(
            lambda: self.update_points_from_step(
                self.min_edit,
                self.max_edit,
                self.step_edit,
                self.points_edit,
            )
        )

        self.step_edit.textChanged.connect(
            lambda: self.update_points_from_step(
                self.min_edit,
                self.max_edit,
                self.step_edit,
                self.points_edit,
            )
        )

        self.points_edit.textChanged.connect(
            lambda: self.update_step_from_points(
                self.min_edit,
                self.max_edit,
                self.step_edit,
                self.points_edit,
            )
        )
        self.linear_radio = QRadioButton("Linear")

        self.log_radio = QRadioButton("Logarithmic")
        self.linear_radio.toggled.connect(self.update_sweep_mode)

        self.log_radio.toggled.connect(self.update_sweep_mode)

        self.linear_radio.setChecked(True)

        xaxis_widget = QWidget()

        xaxis_row = QHBoxLayout()

        xaxis_row.setContentsMargins(0, 0, 0, 0)

        xaxis_row.addWidget(self.xaxis_combo)

        xaxis_row.addStretch()

        xaxis_row.addWidget(self.unit_lbl)

        xaxis_widget.setLayout(xaxis_row)

        sweep_layout.addRow("X Axis", xaxis_widget)

        self.min_lbl = QLabel("Min")
        self.max_lbl = QLabel("Max")
        self.step_lbl = QLabel("Step")
        self.points_lbl = QLabel("Points")

        range_row = QHBoxLayout()

        range_row.addWidget(self.min_lbl)
        range_row.addWidget(self.min_edit)

        range_row.addWidget(self.max_lbl)
        range_row.addWidget(self.max_edit)

        range_row.addWidget(self.step_lbl)
        range_row.addWidget(self.step_edit)

        range_row.addWidget(self.points_lbl)
        range_row.addWidget(self.points_edit)

        range_widget = QWidget()
        range_widget.setLayout(range_row)

        sweep_layout.addRow(range_widget)

        scale_row = QHBoxLayout()

        scale_row.addWidget(self.linear_radio)

        scale_row.addWidget(self.log_radio)

        scale_widget = QWidget()
        scale_widget.setLayout(scale_row)

        sweep_layout.addRow("", scale_widget)

        # =====================================================
        # PARAMETRIC SWEEP
        # =====================================================

        self.enable_parametric_sweep_chk = QCheckBox("Enable Parameter Sweep")

        sweep_layout.addRow(self.enable_parametric_sweep_chk)

        # ---------------- Sweep Parameter ----------------

        self.sweep_parameter_combo = QComboBox()

        self.sweep_parameter_combo.setMinimumWidth(150)
        self.sweep_parameter_combo.setMaximumWidth(180)
        self.sweep_parameter_combo.setMinimumHeight(28)

        for section_name, section in INPUT_DATABASE.items():

            for name, _, _, state_var in section:

                display = name

                if section_name == "TX_ENVIRONMENT":
                    display = "TX " + name

                elif section_name == "RX_ENVIRONMENT":
                    display = "RX " + name

                elif section_name == "TX_OPTICS":
                    display = "TX " + name

                elif section_name == "RX_OPTICS":
                    display = "RX " + name

                self.sweep_parameter_combo.addItem(display, state_var)

        self.sweep_unit_lbl = QLabel("")
        self.sweep_unit_lbl.setStyleSheet("""
font-size:9px;
font-style:italic;
color:gray;
""")

        self.sweep_parameter_combo.currentTextChanged.connect(
            self.update_parametric_sweep_unit
        )

        sweep_widget = QWidget()

        sweep_row = QHBoxLayout()
        sweep_row.setContentsMargins(0, 0, 0, 0)

        sweep_row.addWidget(self.sweep_parameter_combo)
        sweep_row.addStretch()
        sweep_row.addWidget(self.sweep_unit_lbl)

        sweep_widget.setLayout(sweep_row)

        sweep_layout.addRow("Sweep", sweep_widget)

        # ---------------- Sweep Range ----------------

        self.sweep_min_edit = QLineEdit("5")
        self.sweep_max_edit = QLineEdit("20")
        self.sweep_step_edit = QLineEdit("5")
        self.sweep_points_edit = QLineEdit("4")
        self.sweep_min_edit.textChanged.connect(
            lambda: self.update_points_from_step(
                self.sweep_min_edit,
                self.sweep_max_edit,
                self.sweep_step_edit,
                self.sweep_points_edit,
            )
        )

        self.sweep_max_edit.textChanged.connect(
            lambda: self.update_points_from_step(
                self.sweep_min_edit,
                self.sweep_max_edit,
                self.sweep_step_edit,
                self.sweep_points_edit,
            )
        )

        self.sweep_step_edit.textChanged.connect(
            lambda: self.update_points_from_step(
                self.sweep_min_edit,
                self.sweep_max_edit,
                self.sweep_step_edit,
                self.sweep_points_edit,
            )
        )

        self.sweep_points_edit.textChanged.connect(
            lambda: self.update_step_from_points(
                self.sweep_min_edit,
                self.sweep_max_edit,
                self.sweep_step_edit,
                self.sweep_points_edit,
            )
        )

        range2 = QHBoxLayout()

        range2.addWidget(QLabel("Min"))
        range2.addWidget(self.sweep_min_edit)

        range2.addWidget(QLabel("Max"))
        range2.addWidget(self.sweep_max_edit)

        range2.addWidget(QLabel("Step"))
        range2.addWidget(self.sweep_step_edit)

        range2.addWidget(QLabel("Points"))
        range2.addWidget(self.sweep_points_edit)

        range2_widget = QWidget()
        range2_widget.setLayout(range2)

        sweep_layout.addRow(range2_widget)

        # ---------------- Sweep Scale ----------------

        self.sweep_linear_radio = QRadioButton("Linear")
        self.sweep_log_radio = QRadioButton("Logarithmic")

        self.sweep_linear_radio.setChecked(True)

        scale2 = QHBoxLayout()

        scale2.addWidget(self.sweep_linear_radio)
        scale2.addWidget(self.sweep_log_radio)

        scale2_widget = QWidget()
        scale2_widget.setLayout(scale2)

        sweep_layout.addRow("", scale2_widget)

        input_title = QLabel("INPUTS")

        input_title.setStyleSheet("""
            font-size:12px;
            font-weight:bold;
            color:#1976D2;
        """)

        sweep_layout.addRow(input_title)
        input_container = QWidget()
        input_layout = QVBoxLayout()

        input_layout.setAlignment(Qt.AlignTop)
        input_layout.setSpacing(0)
        input_layout.setContentsMargins(0, 0, 0, 0)

        for section_name, fields in INPUT_DATABASE.items():

            section = CollapsibleSection(section_name)

            for name, value, unit, state_var in fields:
                inp, row = self.make_input(value, unit, name=name, state_var=state_var)

                if state_var not in self.shared_inputs:
                    self.shared_inputs[state_var] = []
                self.shared_inputs[state_var].append(inp)

                holder = QWidget()
                holder.setLayout(row)

                section.addWidget(QLabel(name))

                section.addWidget(holder)

            input_layout.addWidget(section)
        input_layout.addWidget(self.create_detector_section())
        input_scroll = QScrollArea()
        input_scroll.setWidgetResizable(True)

        input_widget = QWidget()
        input_widget.setLayout(input_layout)

        input_scroll.setWidget(input_widget)

        input_scroll.setMaximumHeight(250)

        sweep_layout.addRow(input_scroll)
        self.output_checks = {}
        title = QLabel("OUTPUTS")

        title.setStyleSheet("""
        font-size:12px;
        font-weight:bold;
        color:#1976D2;
        """)

        sweep_layout.addRow(title)

        output_container = QWidget()
        output_layout = QVBoxLayout()
        output_layout.setAlignment(Qt.AlignTop)
        output_layout.setSpacing(0)
        output_layout.setContentsMargins(0, 0, 0, 0)

        self.output_checks = {}
        self.output_log_checks = {}
        self.output_state_map = {}
        self.output_unit_map = {}
        self.output_unit_map = {}
        self.output_name_map = {}

        for section_name, outputs in OUTPUT_DATABASE.items():

            section = CollapsibleSection(section_name)

            for output_name, state_var, unit in outputs:

                row_widget = QWidget()

                row_layout = QHBoxLayout(row_widget)

                row_layout.setContentsMargins(0, 0, 0, 0)

                chk = QCheckBox(output_name)

                log_chk = QCheckBox("Log")

                row_layout.addWidget(chk)

                row_layout.addStretch()

                row_layout.addWidget(log_chk)

                key = f"{section_name}|{output_name}"

                self.output_checks[key] = chk
                self.output_log_checks[key] = log_chk

                self.output_state_map[key] = state_var
                self.output_unit_map[key] = unit

                self.output_name_map[output_name] = state_var

                section.addWidget(row_widget)

            output_layout.addWidget(section)

        output_scroll = QScrollArea()
        output_scroll.setWidgetResizable(True)

        output_container = QWidget()
        output_container.setLayout(output_layout)

        output_scroll.setWidget(output_container)

        output_scroll.setMaximumHeight(220)

        sweep_layout.addRow(output_scroll)

        self.separate_plot_chk = QCheckBox("Plot Separately")

        sweep_layout.addRow(self.separate_plot_chk)
        self.plot_btn = QPushButton("Generate Plot")

        self.plot_btn.clicked.connect(self.generate_plot)

        self.clear_btn = QPushButton("Clear All")

        self.clear_btn.clicked.connect(self.clear_outputs)

        self.save_png_btn = QPushButton("Save PNG")

        self.save_csv_btn = QPushButton("Save CSV")

        for btn in [
            self.plot_btn,
            self.clear_btn,
            self.save_png_btn,
            self.save_csv_btn,
        ]:

            btn.setMinimumHeight(28)
            btn.setMaximumHeight(32)

            btn.setMinimumWidth(120)
            btn.setMaximumWidth(150)

            btn.setStyleSheet("""
                font-size: 8px;
            """)

        self.save_png_btn.clicked.connect(self.save_plot_png)

        self.save_csv_btn.clicked.connect(self.save_results_csv)

        btn_grid = QGridLayout()

        btn_grid.setHorizontalSpacing(5)

        btn_grid.setVerticalSpacing(5)

        btn_grid.addWidget(self.plot_btn, 0, 0)

        btn_grid.addWidget(self.clear_btn, 0, 1)

        btn_grid.addWidget(self.save_png_btn, 1, 0)

        btn_grid.addWidget(self.save_csv_btn, 1, 1)

        btn_widget = QWidget()

        btn_widget.setLayout(btn_grid)

        sweep_layout.addRow(btn_widget)

        sweep_box.setLayout(sweep_layout)

        graph_box = QGroupBox("GRAPH")
        graph_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        graph_layout = QVBoxLayout()

        self.canvas = MplCanvas()

        self.plot_manager = PlotManager(self.canvas)

        toolbar = NavigationToolbar2QT(self.canvas, self)

        graph_layout.addWidget(toolbar)

        graph_layout.addWidget(self.canvas)
        graph_layout.setStretch(0, 0)

        graph_layout.setStretch(1, 1)

        graph_box.setLayout(graph_layout)
        plot_splitter.addWidget(sweep_box)

        plot_splitter.addWidget(graph_box)

        plot_splitter.setStretchFactor(0, 1)

        plot_splitter.setStretchFactor(1, 3)

        plot_splitter.setSizes([320, 900])

        plot_root.addWidget(plot_splitter)

        plot_root.setStretch(0, 1)
        plot_tab.setLayout(plot_root)
        compare_tab = QWidget()

        compare_root = QVBoxLayout()

        compare_splitter = QSplitter(Qt.Horizontal)

        compare_splitter.setSizes([320, 900])

        compare_splitter.setStretchFactor(0, 1)

        compare_splitter.setStretchFactor(1, 3)

        compare_box = QGroupBox("COMPARE SETTINGS")

        compare_box.setMinimumWidth(300)

        compare_box.setMaximumWidth(320)

        compare_layout = QFormLayout()

        compare_layout.setContentsMargins(10, 10, 10, 10)

        compare_layout.setSpacing(6)

        compare_layout.setVerticalSpacing(5)
        self.compare_category = QComboBox()

        self.compare_category.addItems(
            [
                "Atmosphere",
                "Rain",
                "Molecular",
                "Aerosol",
                "Turbulence",
                "Geometry",
                "Pointing",
                "Detector",
                "QKD",
            ]
        )

        self.compare_category.currentTextChanged.connect(self.update_compare_models)

        compare_layout.addRow("Category", self.compare_category)
        from PySide6.QtWidgets import QListWidget, QAbstractItemView

        self.compare_models = QListWidget()

        self.compare_models.setSelectionMode(QAbstractItemView.MultiSelection)

        compare_layout.addRow("Models", self.compare_models)
        # ==================================
        # X AXIS
        # ==================================

        self.compare_xaxis = QComboBox()

        for section_name, section in INPUT_DATABASE.items():

            for name, _, _, state_var in section:

                display = name

                if section_name == "TX_ENVIRONMENT":
                    display = "TX " + name

                elif section_name == "RX_ENVIRONMENT":
                    display = "RX " + name

                elif section_name == "TX_OPTICS":
                    display = "TX " + name

                elif section_name == "RX_OPTICS":
                    display = "RX " + name

                self.compare_xaxis.addItem(display, state_var)
        compare_layout.addRow("X Axis", self.compare_xaxis)

        # ==================================
        # RANGE
        # ==================================

        self.compare_min = QLineEdit("1")
        self.compare_max = QLineEdit("50")
        self.compare_step = QLineEdit("1")
        self.compare_points = QLineEdit("50")

        self.attach_dynamic_validator(
            self.compare_min, lambda: self.compare_xaxis.currentData()
        )
        self.attach_dynamic_validator(
            self.compare_max, lambda: self.compare_xaxis.currentData()
        )
        self.attach_dynamic_validator(
            self.compare_step, lambda: self.compare_xaxis.currentData()
        )

        self.compare_min.textChanged.connect(
            lambda: self.update_points_from_step(
                self.compare_min,
                self.compare_max,
                self.compare_step,
                self.compare_points,
            )
        )

        self.compare_max.textChanged.connect(
            lambda: self.update_points_from_step(
                self.compare_min,
                self.compare_max,
                self.compare_step,
                self.compare_points,
            )
        )

        self.compare_step.textChanged.connect(
            lambda: self.update_points_from_step(
                self.compare_min,
                self.compare_max,
                self.compare_step,
                self.compare_points,
            )
        )

        self.compare_points.textChanged.connect(
            lambda: self.update_step_from_points(
                self.compare_min,
                self.compare_max,
                self.compare_step,
                self.compare_points,
            )
        )

        range_row = QHBoxLayout()

        range_row.addWidget(QLabel("Min"))
        range_row.addWidget(self.compare_min)

        range_row.addWidget(QLabel("Max"))
        range_row.addWidget(self.compare_max)

        range_row.addWidget(QLabel("Step"))
        range_row.addWidget(self.compare_step)

        range_row.addWidget(QLabel("Points"))
        range_row.addWidget(self.compare_points)

        range_widget = QWidget()

        range_widget.setLayout(range_row)

        compare_layout.addRow(range_widget)
        # ==================================
        # SECOND PARAMETER SWEEP
        # ==================================
        self.compare_enable_sweep = QCheckBox("Enable Parametric Sweep")

        compare_layout.addRow(self.compare_enable_sweep)

        self.compare_sweep_parameter = QComboBox()

        self.compare_sweep_parameter.clear()

        for i in range(self.sweep_parameter_combo.count()):
            self.compare_sweep_parameter.addItem(
                self.sweep_parameter_combo.itemText(i),
                self.sweep_parameter_combo.itemData(i),
            )

        self.compare_sweep_min = QLineEdit("5")

        self.compare_sweep_max = QLineEdit("20")

        self.compare_sweep_step = QLineEdit("5")

        self.compare_sweep_points = QLineEdit("3")
        self.compare_sweep_min.textChanged.connect(
            lambda: self.update_points_from_step(
                self.compare_sweep_min,
                self.compare_sweep_max,
                self.compare_sweep_step,
                self.compare_sweep_points,
            )
        )

        self.compare_sweep_max.textChanged.connect(
            lambda: self.update_points_from_step(
                self.compare_sweep_min,
                self.compare_sweep_max,
                self.compare_sweep_step,
                self.compare_sweep_points,
            )
        )

        self.compare_sweep_step.textChanged.connect(
            lambda: self.update_points_from_step(
                self.compare_sweep_min,
                self.compare_sweep_max,
                self.compare_sweep_step,
                self.compare_sweep_points,
            )
        )

        self.compare_sweep_points.textChanged.connect(
            lambda: self.update_step_from_points(
                self.compare_sweep_min,
                self.compare_sweep_max,
                self.compare_sweep_step,
                self.compare_sweep_points,
            )
        )
        sweep_row = QHBoxLayout()

        sweep_row.setContentsMargins(0, 0, 0, 0)
        sweep_row.setSpacing(4)

        self.compare_sweep_parameter.setMaximumWidth(85)

        sweep_row.addWidget(QLabel("Sweep"))
        sweep_row.addWidget(self.compare_sweep_parameter)

        sweep_row.addWidget(QLabel("Min"))
        sweep_row.addWidget(self.compare_sweep_min)

        sweep_row.addWidget(QLabel("Max"))
        sweep_row.addWidget(self.compare_sweep_max)

        sweep_row.addWidget(QLabel("Step"))
        sweep_row.addWidget(self.compare_sweep_step)

        sweep_row.addWidget(QLabel("Points"))
        sweep_row.addWidget(self.compare_sweep_points)
        sweep_widget = QWidget()
        sweep_widget.setLayout(sweep_row)

        compare_layout.addRow(sweep_widget)

        # ==================================
        # SCALE
        # ==================================

        self.compare_linear = QRadioButton("Linear")

        self.compare_log = QRadioButton("Logarithmic")

        self.compare_linear.setChecked(True)

        scale_row = QHBoxLayout()

        scale_row.addWidget(self.compare_linear)

        scale_row.addWidget(self.compare_log)

        scale_widget = QWidget()

        scale_widget.setLayout(scale_row)

        compare_layout.addRow(scale_widget)
        self.compare_separate_chk = QCheckBox("Plot Separately")

        compare_layout.addRow(self.compare_separate_chk)

        self.compare_btn = QPushButton("Generate Compare")

        self.compare_clear_btn = QPushButton("Clear All")

        self.compare_save_png_btn = QPushButton("Save PNG")

        self.compare_save_csv_btn = QPushButton("Save CSV")

        self.compare_btn.clicked.connect(self.generate_compare_plot)

        self.compare_clear_btn.clicked.connect(self.clear_compare_plot)

        self.compare_save_png_btn.clicked.connect(self.save_compare_png)

        self.compare_save_csv_btn.clicked.connect(self.save_compare_csv)
        compare_graph = QGroupBox("GRAPH")

        graph_layout = QVBoxLayout()

        self.compare_canvas = MplCanvas()

        toolbar = NavigationToolbar2QT(self.compare_canvas, self)

        graph_layout.addWidget(toolbar)

        graph_layout.addWidget(self.compare_canvas)

        compare_graph.setLayout(graph_layout)
        # =========================
        # INPUTS
        # =========================

        input_title = QLabel("INPUTS")

        input_title.setStyleSheet("""
            font-size:12px;
            font-weight:bold;
            color:#1976D2;
        """)

        compare_layout.addRow(input_title)

        compare_input_scroll = QScrollArea()

        compare_input_scroll.setWidgetResizable(True)

        compare_input_scroll.setMaximumHeight(250)

        compare_input_widget = QWidget()

        compare_input_layout = QVBoxLayout()

        compare_input_layout.setAlignment(Qt.AlignTop)

        compare_input_layout.setSpacing(0)

        compare_input_layout.setContentsMargins(0, 0, 0, 0)

        for section_name, fields in INPUT_DATABASE.items():

            section = CollapsibleSection(section_name)

            for name, value, unit, state_var in fields:

                inp, row = self.make_input(value, unit, name=name, state_var=state_var)
                if state_var not in self.shared_inputs:
                    self.shared_inputs[state_var] = []

                self.shared_inputs[state_var].append(inp)

                holder = QWidget()

                holder.setLayout(row)

                section.addWidget(QLabel(name))

                section.addWidget(holder)

            compare_input_layout.addWidget(section)
        compare_input_layout.addWidget(self.create_detector_section())

        compare_input_widget.setLayout(compare_input_layout)

        compare_input_scroll.setWidget(compare_input_widget)

        compare_layout.addRow(compare_input_scroll)

        # =========================
        # OUTPUTS
        # =========================

        title = QLabel("OUTPUTS")

        title.setStyleSheet("""
            font-size:12px;
            font-weight:bold;
            color:#1976D2;
        """)

        compare_layout.addRow(title)

        compare_output_scroll = QScrollArea()

        compare_output_scroll.setWidgetResizable(True)

        compare_output_scroll.setMaximumHeight(220)

        compare_output_container = QWidget()

        compare_output_layout = QVBoxLayout()

        compare_output_layout.setAlignment(Qt.AlignTop)

        compare_output_layout.setSpacing(0)

        compare_output_layout.setContentsMargins(0, 0, 0, 0)
        self.compare_output_checks = {}
        self.compare_output_log_checks = {}

        for section_name, outputs in OUTPUT_DATABASE.items():

            section = CollapsibleSection(section_name)

            for output_name, state_var, unit in outputs:

                row_widget = QWidget()

                row_layout = QHBoxLayout(row_widget)

                row_layout.setContentsMargins(0, 0, 0, 0)

                chk = QCheckBox(output_name)

                log_chk = QCheckBox("Log")

                key = f"{section_name}|{output_name}"

                self.compare_output_checks[key] = chk
                self.compare_output_log_checks[key] = log_chk
                row_layout.addWidget(chk)

                row_layout.addStretch()

                row_layout.addWidget(log_chk)

                section.addWidget(row_widget)

            compare_output_layout.addWidget(section)

        compare_output_container.setLayout(compare_output_layout)

        compare_output_scroll.setWidget(compare_output_container)

        compare_layout.addRow(compare_output_scroll)

        btn_grid = QGridLayout()

        btn_grid.addWidget(self.compare_btn, 0, 0)

        btn_grid.addWidget(self.compare_clear_btn, 0, 1)

        btn_grid.addWidget(self.compare_save_png_btn, 1, 0)

        btn_grid.addWidget(self.compare_save_csv_btn, 1, 1)

        btn_widget = QWidget()
        btn_widget.setLayout(btn_grid)

        compare_layout.addRow(btn_widget)

        compare_box.setLayout(compare_layout)

        compare_splitter.addWidget(compare_box)

        compare_splitter.addWidget(compare_graph)

        compare_root.addWidget(compare_splitter)

        compare_tab.setLayout(compare_root)

        # =====================================
        # SLICE MODE
        # =====================================

        # =====================================
        # SLICE MODE
        # =====================================

        slice_tab = QWidget()

        slice_layout = QVBoxLayout()
        control_layout = QHBoxLayout()

        # ---------------- Display ----------------

        control_layout.addWidget(QLabel("Display"))

        self.slice_view_combo = QComboBox()

        self.slice_view_combo.addItems(
            ["First 10", "Middle 10", "Last 10", "All Slices"]
        )

        self.slice_view_combo.currentTextChanged.connect(self.update_slice_table)

        control_layout.addWidget(self.slice_view_combo)

        # ---------------- Category Filter ----------------
        control_layout.addSpacing(20)
        control_layout.addWidget(QLabel("Category"))
        self.slice_category_combo = QComboBox()
        self.slice_category_combo.addItems(
            [
                "All Parameters",
                "Geometry",
                "Terrain",
                "Atmosphere",
                "Weather",
                "Marine",
                "Turbulence",
                "Refraction",
                "Extinction",
                "Scattering",
                "Pointing & Tracking",
                "Link Budget",
                "Detector",
                "QKD",
                "System",
                "Miscellaneous",
            ]
        )
        self.slice_category_combo.currentTextChanged.connect(self.update_slice_table)
        control_layout.addWidget(self.slice_category_combo)

        # ---------------- Compare ----------------

        control_layout.addSpacing(20)

        control_layout.addWidget(QLabel("Compare"))

        from PySide6.QtWidgets import QListWidget, QAbstractItemView

        self.slice_compare_combo = QListWidget()

        self.slice_compare_combo.setSelectionMode(QAbstractItemView.MultiSelection)

        self.slice_compare_combo.setMaximumHeight(90)
        self.slice_compare_combo.setMaximumWidth(220)

        control_layout.addWidget(self.slice_compare_combo)

        self.slice_compare_combo.currentTextChanged.connect(self.update_slice_table)

        control_layout.addWidget(self.slice_compare_combo)

        control_layout.addStretch()

        slice_layout.addLayout(control_layout)

        info_layout = QHBoxLayout()

        self.total_slice_label = QLabel("Total Slices : 0")

        self.display_slice_label = QLabel("Displaying : 0-0")

        info_layout.addWidget(self.total_slice_label)

        info_layout.addStretch()

        info_layout.addWidget(self.display_slice_label)

        slice_layout.addLayout(info_layout)

        self.slice_table = QTableWidget()

        from core.state import PropagationSlice

        # Generate initial headers from default PropagationSlice fields
        dummy_slice = PropagationSlice()
        s_vars = vars(dummy_slice)
        filtered_keys = [k for k in s_vars.keys() if not k.startswith("_")]
        self.headers = [
            PropagationSlice.format_attribute_name(k) for k in filtered_keys
        ]

        self.slice_table.setColumnCount(len(self.headers))
        self.slice_table.setHorizontalHeaderLabels(self.headers)
        self.slice_compare_combo.addItems(self.headers)

        self.slice_compare_combo.itemSelectionChanged.connect(self.update_slice_table)
        self.slice_table.setRowCount(10)
        self.slice_table.verticalHeader().setDefaultSectionSize(28)

        self.slice_table.verticalHeader().setVisible(False)

        self.slice_table.setAlternatingRowColors(True)
        self.slice_table.setShowGrid(True)

        from PySide6.QtWidgets import QAbstractItemView

        self.slice_table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.slice_table.setSelectionBehavior(QAbstractItemView.SelectRows)

        self.slice_table.horizontalHeader().setStretchLastSection(True)

        header = self.slice_table.horizontalHeader()

        header = self.slice_table.horizontalHeader()

        # Size each column to its content
        header.setSectionResizeMode(QHeaderView.ResizeToContents)

        # Allow manual resizing
        header.setSectionsMovable(True)

        # Enable horizontal scrolling
        self.slice_table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)

        self.slice_table.horizontalScrollBar().setSingleStep(20)
        # Or if you want the first column smaller:
        # header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        # for i in range(1, self.slice_table.columnCount()):
        #     header.setSectionResizeMode(i, QHeaderView.Stretch)

        self.slice_table.setWordWrap(False)
        slice_layout.addWidget(self.slice_table)
        slice_layout.setStretch(0, 0)  # Controls
        slice_layout.setStretch(1, 0)  # Labels
        slice_layout.setStretch(2, 1)  # Table fills remaining space

        slice_tab.setLayout(slice_layout)

        # =====================================
        # PROPAGATION MODE
        # =====================================

        propagation_tab = QWidget()

        propagation_layout = QVBoxLayout()

        # -----------------------------
        # Drawing Area
        # -----------------------------

        self.propagation_widget = PropagationWidget(self.state)

        # "Show Beam Evolution" button bar
        beam_evo_bar = QHBoxLayout()
        beam_evo_bar.setContentsMargins(0, 4, 0, 4)
        beam_evo_bar.addStretch()
        self.beam_evolution_btn = QPushButton("⚡ Show Beam Evolution (Cumulative)")
        self.beam_evolution_btn.setStyleSheet(
            "QPushButton { background:#1a73e8; color:white; font-weight:bold; "
            "padding:6px 18px; border-radius:4px; font-size:11px; }"
            "QPushButton:hover { background:#1557b0; }"
        )
        self.beam_evolution_btn.setToolTip(
            "Open a filmstrip view showing how the beam degrades\n"
            "as it passes through each atmospheric slice cumulatively."
        )
        self.beam_evolution_btn.clicked.connect(self._open_beam_evolution_viewer)
        beam_evo_bar.addWidget(self.beam_evolution_btn)
        beam_evo_bar.addStretch()
        propagation_layout.addLayout(beam_evo_bar)

        # -----------------------------
        # Slice Information
        # -----------------------------

        info_box = QGroupBox("Slice Information")

        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)

        # ---------------- Category Filter ----------------
        cat_layout = QHBoxLayout()
        cat_layout.setContentsMargins(10, 5, 10, 5)
        cat_layout.addWidget(QLabel("Category:"))
        self.schematic_category_combo = QComboBox()
        self.schematic_category_combo.addItems(
            [
                "All Parameters",
                "Geometry",
                "Terrain",
                "Atmosphere",
                "Weather",
                "Marine",
                "Turbulence",
                "Refraction",
                "Extinction",
                "Scattering",
                "Pointing & Tracking",
                "Link Budget",
                "Detector",
                "QKD",
                "System",
                "Miscellaneous",
            ]
        )
        cat_layout.addWidget(self.schematic_category_combo)
        cat_layout.addStretch()
        info_layout.addLayout(cat_layout)

        self.propagation_widget.category_combo = self.schematic_category_combo
        self.schematic_category_combo.currentTextChanged.connect(
            self.propagation_widget.update_slice_info
        )

        self.slice_info_scroll = QScrollArea()
        self.slice_info_scroll.setWidgetResizable(True)
        self.slice_info_scroll.setFrameShape(QFrame.NoFrame)
        self.slice_info_scroll.setMinimumHeight(150)

        info_layout.addWidget(self.slice_info_scroll)

        self.propagation_widget.info_box = self.slice_info_scroll

        info_box.setLayout(info_layout)

        # -----------------------------
        # Splitter
        # -----------------------------

        splitter = QSplitter(Qt.Vertical)

        splitter.addWidget(self.propagation_widget)
        splitter.addWidget(info_box)

        # Prevent collapsing
        splitter.setChildrenCollapsible(False)

        # Drawing gets much more space
        splitter.setStretchFactor(0, 10)
        splitter.setStretchFactor(1, 1)

        # Initial position of the splitter
        splitter.setSizes([760, 140])

        propagation_layout.addWidget(splitter)

        propagation_tab.setLayout(propagation_layout)

        tabs = QTabWidget()
        self.tabs = tabs

        self.data_tab = data_tab
        self.plot_tab = plot_tab
        self.compare_tab = compare_tab
        self.slice_tab = slice_tab
        self.propagation_tab = propagation_tab

        # ==========================================
        # QKD TAB LAYOUT
        # ==========================================
        qkd_tab = QWidget()
        qkd_layout = QVBoxLayout()
        qkd_splitter = QSplitter(Qt.Vertical)

        # TOP WIDGET (Inputs)
        qkd_top_widget = QWidget()
        qkd_top_layout = QGridLayout()
        qkd_top_layout.setContentsMargins(6, 6, 6, 6)
        qkd_top_layout.setHorizontalSpacing(20)
        qkd_top_layout.setVerticalSpacing(8)

        # Placeholder for Protocol inputs
        self.qkd_protocol_container = QWidget()
        self.qkd_protocol_container_layout = QVBoxLayout()
        self.qkd_protocol_container_layout.setContentsMargins(0, 0, 0, 0)
        self.qkd_protocol_container.setLayout(self.qkd_protocol_container_layout)

        qkd_top_layout.addWidget(self.qkd_protocol_container, 0, 0)
        qkd_top_layout.setColumnStretch(0, 1)

        qkd_top_widget.setLayout(qkd_top_layout)
        qkd_top_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # BOTTOM WIDGET (Outputs & Verifier)
        qkd_bottom_widget = QWidget()
        qkd_bottom_layout = QHBoxLayout()

        # Build QKD Output sub-tabs widget
        for section_name, outputs in QKD_OUTPUT_DATABASE.items():
            page = QWidget()
            grid = QGridLayout(page)
            grid.setContentsMargins(6, 6, 6, 6)
            grid.setVerticalSpacing(14)
            value_labels = {}
            row = 0
            for name, state_var, unit in outputs:
                lbl_name = QLabel(name)
                lbl_name.setStyleSheet("font-weight:bold;")
                lbl_value = QLabel("-")
                lbl_value.setTextInteractionFlags(Qt.TextSelectableByMouse)
                value_labels[state_var] = (lbl_value, unit)
                col = (row % 2) * 2
                r = row // 2
                grid.addWidget(lbl_name, r, col)
                grid.addWidget(lbl_value, r, col + 1)
                row += 1
            grid.setColumnStretch(1, 1)
            grid.setColumnStretch(3, 1)
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setWidget(page)
            self.qkd_output_tabs.addTab(scroll, section_name)
            self.qkd_output_widgets[section_name] = value_labels

        # Build QKD Live Verifier sub-tabs widget
        self.qkd_verifier_tabs = QTabWidget()
        for proto in QKD_INPUT_DATABASE["PROTOCOL"].keys():
            ver = QTextEdit()
            ver.setReadOnly(True)
            self.qkd_verifier_tabs.addTab(ver, proto)
            self.qkd_verifier_labels[proto] = ver

        # QKD OUTPUTS Panel (Data Mode Output structure + 5th "QKD" tab)
        qkd_out_tabs, qkd_out_widgets, _ = self.create_data_mode_output_widget()
        self.data_output_widgets_list.append(qkd_out_widgets)
        qkd_out_tabs.addTab(self.qkd_output_tabs, "QKD")

        qkd_out_box = QGroupBox("QKD OUTPUTS")
        qkd_out_layout = QVBoxLayout()
        qkd_out_layout.addWidget(qkd_out_tabs)
        qkd_out_box.setLayout(qkd_out_layout)

        # QKD LIVE VERIFIER Panel (Data Mode Verifier structure + 4th "QKD" tab)
        qkd_ver_tabs, qkd_ver_dict = self.create_data_mode_verifier_widget()
        self.data_verifier_dicts_list.append(qkd_ver_dict)
        qkd_ver_tabs.addTab(self.qkd_verifier_tabs, "QKD")

        qkd_ver_box = QGroupBox("QKD LIVE VERIFIER")
        qkd_ver_layout = QVBoxLayout()
        qkd_ver_layout.addWidget(qkd_ver_tabs)
        qkd_ver_box.setLayout(qkd_ver_layout)

        qkd_bottom_layout.addWidget(qkd_out_box)
        qkd_bottom_layout.addWidget(qkd_ver_box)
        qkd_bottom_widget.setLayout(qkd_bottom_layout)

        qkd_splitter.addWidget(qkd_top_widget)
        qkd_splitter.addWidget(qkd_bottom_widget)
        qkd_splitter.setStretchFactor(0, 1)
        qkd_splitter.setStretchFactor(1, 1)

        qkd_layout.addWidget(qkd_splitter)
        qkd_tab.setLayout(qkd_layout)

        tabs.addTab(data_tab, "DATA MODE")
        tabs.addTab(qkd_tab, "QKD")

        self.qkd_combo.currentTextChanged.connect(self.rebuild_qkd_protocol_inputs)
        self.rebuild_qkd_protocol_inputs(self.qkd_combo.currentText())

        tabs.addTab(plot_tab, "PLOT")

        tabs.addTab(compare_tab, "COMPARE MODELS")
        tabs.addTab(slice_tab, "SLICE DETAILS")
        tabs.addTab(propagation_tab, "SCHEMATIC")

        settings_tab = self.create_settings_tab()

        tabs.addTab(settings_tab, "SETTINGS")
        tabs.setCornerWidget(self.hide_models_btn, Qt.TopRightCorner)

        right_panel = QWidget()

        right_layout = QVBoxLayout()

        right_layout.addWidget(tabs)

        right_panel.setLayout(right_layout)

        main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter = main_splitter

        main_splitter.addWidget(left_panel)

        main_splitter.addWidget(right_panel)

        main_splitter.setStretchFactor(0, 1)

        main_splitter.setStretchFactor(1, 4)

        main_splitter.setSizes([300, 1150])

        root_layout = QVBoxLayout()

        root_layout.addWidget(main_splitter)

        root.setLayout(root_layout)

        self.setCentralWidget(root)
        self.update_compare_models()
        self.update_detector_panel()
        self.connect_shared_inputs()
        self.connect_live_updates()
        self.update_sweep_mode()
        self.update_mission_mode()
        self.update_solve_for()
        self.update_fog_combo()
        self.propagation_widget.update()
        from PySide6.QtCore import QTimer

        # QTimer.singleShot(0, self.position_map_buttons)

        self.live_timer = QTimer()

        self.live_timer.setSingleShot(True)

        self.live_timer.timeout.connect(self.compute)
        # -------------------------------------------------
        # Live Map Coordinate Watcher
        # -------------------------------------------------

        self.last_map_timestamp = 0

        self.map_timer = QTimer()

        self.map_timer.timeout.connect(self.check_map_update)

        self.map_timer.start(500)

    def update_compare_models(self):

        self.compare_models.clear()

        cat = self.compare_category.currentText()

        if cat == "Atmosphere":

            models = ["Kim", "Kruse", "Al Naboulsi"]

        elif cat == "Turbulence":

            models = [
                "Hufnagel-Valley",
                "Marine MOST",
                "Tatarski",
                "Hybrid",
                "User Defined",
                "Marine MOST (Remote Sensing 2023)",
            ]

        elif cat == "Geometry":

            models = [
                "Gaussian Beam Theory",
                "Friis-like Optical Model",
                "Gaussian Coupling Model",
            ]

        elif cat == "Pointing":

            models = ["Gaussian Pointing Error Model", "Farid–Hranilovic Model"]

        elif cat == "Detector":

            models = ["SPAD", "SNSPD", "APD", "PMT", "TES"]

        elif cat == "Rain":

            models = [
                "Carbonneau",
                "ITU",
                "Marshall-Palmer",
            ]

        elif cat == "Molecular":

            models = [
                "Beer-Lambert",
                "HITRAN",
                "MODTRAN",
            ]

        elif cat == "Aerosol":

            models = [
                "Kim",
                "Kruse",
                "Ijaz",
                "Shettle-Fenn",
                "Angstrom",
            ]

        else:

            models = ["Decoy BB84", "BB84", "B92", "BBM92", "E91"]

        self.compare_models.addItems(models)

    def create_detector_section(self):

        section = CollapsibleSection("DETECTOR")

        # Keep a reference to every detector section
        if not hasattr(self, "detector_sections"):
            self.detector_sections = []

        self.detector_sections.append(section)

        detector = self.det_combo.currentText()

        if detector not in DETECTOR_DATABASE:
            return section

        for name, value, unit, state_var in DETECTOR_DATABASE[detector]:

            inp, row = self.make_input(value, unit, name=name, state_var=state_var)
            if state_var not in self.shared_detector_inputs:
                self.shared_detector_inputs[state_var] = []

            self.shared_detector_inputs[state_var].append(inp)

            holder = QWidget()
            holder.setLayout(row)

            section.addWidget(QLabel(name))
            section.addWidget(holder)

        return section

    def rebuild_detector_sections(self):

        for section in self.detector_sections:

            # Remove old detector widgets
            while section.content_layout.count():

                item = section.content_layout.takeAt(0)

                if item.widget():
                    item.widget().deleteLater()

            detector = self.det_combo.currentText()

            if detector not in DETECTOR_DATABASE:
                continue

            for name, value, unit, state_var in DETECTOR_DATABASE[detector]:

                inp, row = self.make_input(value, unit, name=name, state_var=state_var)

                if state_var not in self.shared_detector_inputs:
                    self.shared_detector_inputs[state_var] = []

                self.shared_detector_inputs[state_var].append(inp)

                holder = QWidget()
                holder.setLayout(row)

                section.addWidget(QLabel(name))
                section.addWidget(holder)
        self.connect_detector_inputs()

    def update_detector_panel(self):
        self.detector_widgets = {}

        self.shared_detector_inputs.clear()

        # Clear old widgets
        while self.detector_layout.rowCount():

            self.detector_layout.removeRow(0)

        self.detector_widgets = {}
        self.shared_detector_inputs.clear()

        detector = self.det_combo.currentText()

        if detector not in DETECTOR_DATABASE:
            return

        for name, value, unit, state_var in DETECTOR_DATABASE[detector]:

            inp, row = self.make_input(value, unit, name=name, state_var=state_var)
            if state_var not in self.shared_detector_inputs:
                self.shared_detector_inputs[state_var] = []

            self.shared_detector_inputs[state_var].append(inp)

            row_widget = QWidget()
            row_widget.setLayout(row)
            row_widget.setFixedWidth(160)
            row_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

            label = QLabel(name)
            label.setFixedWidth(130)
            label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

            self.detector_layout.addRow(label, row_widget)

            self.detector_widgets[name] = inp

        self.input_sections["DETECTOR"]["widgets"] = self.detector_widgets
        self.rebuild_detector_sections()
        self.connect_detector_inputs()

    def is_widget_valid(self, widget):
        try:
            widget.objectName()
            return True
        except RuntimeError:
            return False

    def clean_widget_dict(self, widget_dict):
        for state_var, widgets in list(widget_dict.items()):
            valid_widgets = [w for w in widgets if self.is_widget_valid(w)]
            if valid_widgets:
                widget_dict[state_var] = valid_widgets
            else:
                del widget_dict[state_var]

    def reset_all_inputs(self):

        self.clean_widget_dict(self.shared_inputs)
        self.clean_widget_dict(self.shared_detector_inputs)
        if hasattr(self, "qkd_shared_inputs"):
            self.clean_widget_dict(self.qkd_shared_inputs)

        # Main shared inputs
        for widgets in self.shared_inputs.values():

            if widgets:

                for w in widgets:

                    if hasattr(w, "default_value"):
                        w.setText(w.default_value)

        # Detector inputs
        for widgets in self.shared_detector_inputs.values():

            if widgets:

                for w in widgets:

                    if hasattr(w, "default_value"):
                        w.setText(w.default_value)

        # QKD inputs
        if hasattr(self, "qkd_shared_inputs"):
            for widgets in self.qkd_shared_inputs.values():
                if widgets:

                    for w in widgets:
                        if hasattr(w, "default_value"):
                            w.setText(w.default_value)
        # Reset all left-panel dropdowns
        self.atm_combo.setCurrentText("Kim")
        self.fog_combo.setCurrentText("Advection")
        self.turb_combo.setCurrentText("Hufnagel-Valley")
        self.det_combo.setCurrentText("SPAD")
        self.qkd_combo.setCurrentText("Decoy BB84")
        self.geom_combo.setCurrentText("Gaussian Beam Theory")
        self.pointing_combo.setCurrentText("Gaussian Pointing Error Model")
        self.rain_combo.setCurrentText("Carbonneau")
        self.molecular_combo.setCurrentText("Beer-Lambert")
        self.aerosol_combo.setCurrentText("Shettle-Fenn")
        self.mission_mode_combo.setCurrentText("Manual Range")
        self.solve_for_combo.setCurrentText("Minimum Height Above Sea")
        self.tracking_mode_combo.setCurrentText("Manual")
        self.slice_accuracy_combo.setCurrentText("Low")

        self.compute()

    def update_sweep_unit(self):

        unit_map = {
            # MISSION
            "Range": "km",
            "TX height": "m",
            "RX height": "m",
            "Elevation": "deg",
            "Effective Earth Radius Factor": "",
            "Coherence Time": "ms",
            "Isoplanatic Angle": "deg",
            # OPTICS
            "Wavelength": "nm",
            "Divergence": "mrad",
            "TX aperture": "mm",
            "RX aperture": "mm",
            "Detector QE": "",
            "Dark counts": "",
            "PPR (MHz)": "MHz",
            "FOV": "mrad",
            "RX Filter Bandwidth": "nm",
            "Beam Quality M2": "",
            "Coupling Efficiency": "",
            # ENVIRONMENT
            "Temperature": "C",
            "Humidity": "%",
            "Visibility": "km",
            "Wind": "m/s",
            "Pressure": "hPa",
            # TRACKING
            "Roll": "deg",
            "Pitch": "deg",
            "Yaw": "deg",
            "Gimbal BW": "Hz",
            "FSM BW": "Hz",
            # SEA
            "Sea State": "",
            "Wave Height": "m",
            "Wave Slope": "deg",
            "Evap Duct Height": "m",
            "Marine BL Height": "m",
            "Rain Rate": "mm/hr",
            "Sea Surface Temp": "C",
            "Inner Scale": "mm",
            "Outer Scale": "m",
            # ATM EXTRA
            "Extra Vis": "km",
            "Extra Wind": "m/s",
            "Cloud Cover": "%",
            "Cloud Base Height": "m",
            "Aerosol Alpha": "",
        }

        param = self.xaxis_combo.currentText()

        unit = unit_map.get(param, "")

        if unit:

            self.unit_lbl.setText(f"Min / Max / Step in {unit}")

        else:

            self.unit_lbl.setText("Min / Max / Step")

    def update_parametric_sweep_unit(self):

        name = self.sweep_parameter_combo.currentText()

        for section in INPUT_DATABASE.values():

            for display_name, _, unit, _ in section:

                if display_name == name:

                    self.sweep_unit_lbl.setText(unit)

                    return

        self.sweep_unit_lbl.setText("")

    def update_sweep_mode(self):

        if not hasattr(self, "step_edit"):
            return

        if hasattr(self, "step_lbl"):

            if self.log_radio.isChecked():

                self.step_lbl.hide()
                self.step_edit.hide()

                if hasattr(self, "points_lbl"):
                    self.points_lbl.setText("Points/Decade")

            else:

                self.step_lbl.show()
                self.step_edit.show()

                if hasattr(self, "points_lbl"):
                    self.points_lbl.setText("Points")

    def update_points_from_step(self, min_edit, max_edit, step_edit, points_edit):

        try:

            mn = float(min_edit.text())
            mx = float(max_edit.text())
            step = float(step_edit.text())

            if step <= 0:
                return

            points = int((mx - mn) / step) + 1

            points_edit.blockSignals(True)
            points_edit.setText(str(points))
            points_edit.blockSignals(False)

        except:
            pass

    def update_step_from_points(self, min_edit, max_edit, step_edit, points_edit):

        try:

            mn = float(min_edit.text())
            mx = float(max_edit.text())
            points = int(points_edit.text())

            if points <= 1:
                return

            step = (mx - mn) / (points - 1)

            step_edit.blockSignals(True)
            step_edit.setText(f"{step:.4f}")
            step_edit.blockSignals(False)

        except:
            pass

    def generate_compare_plot(self):
        self.compute()

        import numpy as np

        from copy import deepcopy

        from main import run_simulation_kernel

        selected = self.compare_models.selectedItems()

        if len(selected) == 0:

            return

        self.compare_canvas.fig.clear()

        axes = {}

        xmin = float(self.compare_min.text())
        xmax = float(self.compare_max.text())
        step = float(self.compare_step.text())
        points = int(self.compare_points.text())

        if step > 0:
            x = np.arange(xmin, xmax + step / 2, step)
        else:
            x = np.linspace(xmin, xmax, points)
        # ==================================
        # SECOND PARAMETER SWEEP
        # ==================================

        sweep_param = self.compare_sweep_parameter.currentText()

        sweep_state_var = self.compare_sweep_parameter.currentData()

        sweep_min = float(self.compare_sweep_min.text())
        sweep_max = float(self.compare_sweep_max.text())
        sweep_step = float(self.compare_sweep_step.text())
        sweep_points = int(self.compare_sweep_points.text())

        if self.compare_enable_sweep.isChecked():

            if sweep_step > 0:
                sweep_values = np.arange(
                    sweep_min, sweep_max + sweep_step / 2, sweep_step
                )
            else:
                sweep_values = np.linspace(sweep_min, sweep_max, sweep_points)

            print("Sweep Values =", sweep_values)

        else:

            sweep_values = [getattr(self.state, sweep_state_var)]
        # Store X values for CSV export
        self.compare_trade_x = list(x)

        # Clear previous compare data
        self.compare_plot_data = {}

        param = self.compare_xaxis.currentText()

        state_var = self.compare_xaxis.currentData()
        category = self.compare_category.currentText()
        selected_outputs = []

        for key, chk in self.compare_output_checks.items():

            if chk.isChecked():

                selected_outputs.append(key)

        if not selected_outputs:

            return

        line_styles = {
            # ---------- Atmosphere ----------
            "Kim": "-",
            "Kruse": "--",
            "Al Naboulsi": ":",
            # ---------- Rain ----------
            "Carbonneau": "-",
            "ITU": "--",
            "Marshall-Palmer": ":",
            # ---------- Molecular ----------
            "Beer-Lambert": "-.",
            "HITRAN": (0, (5, 2)),
            "MODTRAN": (0, (3, 1, 1, 1)),
            # ---------- Aerosol ----------
            "Ijaz": (0, (1, 1)),
            "Shettle-Fenn": (0, (3, 5, 1, 5)),
            "Angstrom": (0, (5, 5)),
            # ---------- Turbulence ----------
            "Hufnagel-Valley": "--",
            "Marine MOST": "-",
            "Tatarski": ":",
            "Hybrid": "-.",
            "User Defined": (0, (5, 2)),
            "Marine MOST (Remote Sensing 2023)": (0, (3, 1, 1, 1)),
            # ---------- Detector ----------
            "SPAD": "--",
            "SNSPD": "-",
            "APD": ":",
            "PMT": "-.",
            "TES": (0, (5, 2)),
            # ---------- QKD ----------
            "Decoy BB84": "--",
            "BB84": "-",
            "B92": ":",
            "BBM92": "-.",
            "E91": "-.",
        }

        for item in selected:

            model = item.text()
            print("================================")
            print("SELECTED MODEL =", repr(model))
            style = line_styles.get(model, "-")

            for selected_output in selected_outputs:

                out_attr = self.output_state_map[selected_output]

                original_state = deepcopy(self.state)
                original_state.plot_mode = True

                for sweep_value in sweep_values:

                    y = []

                    for val in x:

                        temp_state = deepcopy(original_state)

                        setattr(temp_state, state_var, val)
                        print("X =", state_var, getattr(temp_state, state_var))

                        setattr(temp_state, sweep_state_var, sweep_value)
                        print(
                            "Sweep =",
                            sweep_state_var,
                            getattr(temp_state, sweep_state_var),
                        )
                        print("----------------------")
                        print("Parameter =", state_var)
                        print("Value =", val)
                        print("State Value =", getattr(temp_state, state_var))
                        print("Model =", temp_state.atmospheric_model)

                        if category == "Atmosphere":

                            temp_state.atmospheric_model = model

                        elif category == "Rain":

                            temp_state.rain_model = model

                        elif category == "Molecular":

                            temp_state.molecular_model = model

                        elif category == "Aerosol":

                            temp_state.aerosol_model = model

                        elif category == "Turbulence":

                            temp_state.cn2_model = model

                        elif category == "Geometry":

                            temp_state.geometric_loss_model = model

                        elif category == "Pointing":

                            temp_state.pointing_loss_model = model

                        elif category == "Detector":

                            temp_state.detector_model = model

                        elif category == "QKD":

                            temp_state.qkd_protocol = model

                        run_simulation_kernel(temp_state)
                        print("Output =", getattr(temp_state, out_attr))

                        y.append(getattr(temp_state, out_attr, 0))

                    if self.compare_separate_chk.isChecked():

                        if selected_output not in axes:

                            axes[selected_output] = self.compare_canvas.fig.add_subplot(
                                len(selected_outputs), 1, len(axes) + 1
                            )

                        ax = axes[selected_output]

                    else:

                        if "combined" not in axes:

                            axes["combined"] = self.compare_canvas.fig.add_subplot(111)

                        ax = axes["combined"]
                    if self.compare_enable_sweep.isChecked():

                        if self.compare_separate_chk.isChecked():

                            curve_name = (
                                f"{model} | " f"{sweep_param} = {sweep_value:.2f}"
                            )

                        else:

                            curve_name = (
                                f"{model} | "
                                f"{sweep_param} = {sweep_value:.2f} | "
                                f"{selected_output.split('|')[1]}"
                            )

                    else:

                        if self.compare_separate_chk.isChecked():

                            curve_name = model

                        else:

                            curve_name = (
                                f"{model} - " f"{selected_output.split('|')[1]}"
                            )
                    self.compare_plot_data[curve_name] = list(y)

                    plot_y = y

                    use_log = self.compare_output_log_checks[
                        selected_output
                    ].isChecked()

                    if use_log:

                        plot_y = [max(v, 1e-15) for v in y]

                    ax.plot(x, plot_y, linewidth=2.2, linestyle=style, label=curve_name)

        for key, ax in axes.items():

            ax.set_xlabel(param)

            if key != "combined":

                unit = self.output_unit_map.get(key, "")

                ylabel = key.split("|")[1]

                if unit:

                    ylabel += f" ({unit})"

                ax.set_ylabel(ylabel)

            else:

                if len(selected_outputs) == 1:

                    unit = self.output_unit_map.get(selected_outputs[0], "")

                    ylabel = selected_outputs[0].split("|")[1]

                    if unit:

                        ylabel += f" ({unit})"

                else:

                    ylabel = "Output Value (Mixed Units)"

                ax.set_ylabel(ylabel)

            # ==========================================
            # Axis Scale
            # ==========================================

            if self.compare_separate_chk.isChecked():

                use_log = self.compare_output_log_checks[key].isChecked()

            else:

                use_log = self.compare_log.isChecked() or any(
                    self.compare_output_log_checks[o].isChecked()
                    for o in selected_outputs
                )

            if use_log:

                ax.set_yscale("log")

            else:

                ax.set_yscale("linear")

            ax.grid(True, alpha=0.3)

            ax.legend(
                loc="center left", bbox_to_anchor=(1.02, 0.5), fontsize=9, frameon=True
            )

        self.compare_canvas.fig.tight_layout(rect=[0, 0, 0.82, 1])

        self.compare_canvas.draw()

    def clear_compare_plot(self):

        # Clear Output checkboxes
        for chk in self.compare_output_checks.values():
            chk.setChecked(False)

        # Clear Log checkboxes
        for chk in self.compare_output_log_checks.values():
            chk.setChecked(False)

        # Clear graph
        self.compare_canvas.fig.clear()
        self.compare_canvas.draw()

        # Clear stored compare data
        self.compare_plot_data = {}
        self.compare_trade_x = []

    def save_compare_png(self):

        from PySide6.QtWidgets import QFileDialog

        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Compare Plot", "", "PNG Files (*.png)"
        )

        if filename:

            self.compare_canvas.fig.savefig(filename, dpi=300, bbox_inches="tight")

    def save_compare_csv(self):

        from PySide6.QtWidgets import QFileDialog
        import csv

        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Compare CSV", "", "CSV Files (*.csv)"
        )

        if not filename:
            return

        with open(filename, "w", newline="") as f:

            writer = csv.writer(f)

            header = ["X"]
            header.extend(self.compare_plot_data.keys())

            writer.writerow(header)

            for i in range(len(self.compare_trade_x)):

                row = [self.compare_trade_x[i]]

                for y in self.compare_plot_data.values():

                    row.append(y[i])

                writer.writerow(row)

        print("Compare CSV Saved:", filename)

    def connect_shared_inputs(self):

        for widgets in self.shared_inputs.values():

            for src in widgets:

                def sync(text, source=src, group=widgets):

                    for dst in group:
                        if dst is source:
                            continue
                        try:
                            if dst.text() == text:
                                continue
                            dst.blockSignals(True)
                            dst.setText(text)
                            dst.blockSignals(False)
                        except RuntimeError:
                            continue

                src.textChanged.connect(sync)

    def connect_detector_inputs(self):

        for widgets in self.shared_detector_inputs.values():

            for src in widgets:

                def sync(text, source=src, group=widgets):

                    for dst in group:
                        if dst is source:
                            continue
                        try:
                            if dst.text() == text:
                                continue
                            dst.blockSignals(True)
                            dst.setText(text)
                            dst.blockSignals(False)
                        except RuntimeError:
                            continue

                src.textChanged.connect(sync)

    def trigger_live_update(self):

        self.live_timer.start(200)

    def connect_live_updates(self):

        all_inputs = []

        for section in self.input_sections.values():
            all_inputs.extend(section["widgets"].values())

        for section in self.qkd_input_sections.values():

            all_inputs.extend(section["widgets"].values())

        for w in all_inputs:

            w.textChanged.connect(self.trigger_live_update)

    def is_map_server_running(self):

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            return sock.connect_ex(("127.0.0.1", 5050)) == 0
        finally:
            sock.close()

    def start_map_server(self):

        if self.is_map_server_running():
            print("Map server already running")
            return

        print("Starting map server...")

        subprocess.Popen([sys.executable, "map/map_server.py"])

        time.sleep(2)

        print("Done.")

    def _open_beam_evolution_viewer(self):
        """Open the filmstrip Beam Evolution viewer dialog."""
        if not self.state.propagation_slices:
            QMessageBox.information(
                self, "No Data",
                "Run a simulation first so there are propagation slices to visualise."
            )
            return
        viewer = CumulativeViewer(self.state, parent=self)
        viewer.exec()

    def open_tx_map(self):

        self.start_map_server()

        webbrowser.open("http://127.0.0.1:5050")

    def open_rx_map(self):

        self.start_map_server()

        webbrowser.open("http://127.0.0.1:5050")

    def load_map_coordinates(self):

        path = os.path.join(
            os.path.dirname(__file__), "..", "map", "selected_coordinates.json"
        )

        path = os.path.abspath(path)

        if not os.path.exists(path):
            return

        with open(path, "r") as f:
            data = json.load(f)

        self.input_sections["MISSION"]["widgets"]["TX Latitude"].setText(
            f"{data['tx_lat']:.4f}"
        )

        self.input_sections["MISSION"]["widgets"]["TX Longitude"].setText(
            f"{data['tx_lon']:.4f}"
        )

        self.input_sections["MISSION"]["widgets"]["RX Latitude"].setText(
            f"{data['rx_lat']:.4f}"
        )

        self.input_sections["MISSION"]["widgets"]["RX Longitude"].setText(
            f"{data['rx_lon']:.4f}"
        )

    def check_map_update(self):

        if self.mission_mode_combo.currentText() != "Coordinates":
            return

        path = os.path.join(
            os.path.dirname(__file__), "..", "map", "selected_coordinates.json"
        )

        path = os.path.abspath(path)

        if not os.path.exists(path):
            return

        timestamp = os.path.getmtime(path)

        if timestamp != self.last_map_timestamp:

            self.last_map_timestamp = timestamp

            self.load_map_coordinates()

            self.compute()

    def position_map_buttons(self):

        rows = self.mission_rows

        tx_label = rows["TX Latitude"]["label"]
        rx_label = rows["RX Latitude"]["label"]

        # Position beside TX Latitude
        tx_pos = tx_label.mapTo(
            self.input_sections["MISSION"]["box"], tx_label.rect().topLeft()
        )

        self.tx_maps_btn.move(tx_pos.x() - 19, tx_pos.y())  # adjust later if needed

        # Position beside RX Latitude
        rx_pos = rx_label.mapTo(
            self.input_sections["MISSION"]["box"], rx_label.rect().topLeft()
        )

        self.rx_maps_btn.move(rx_pos.x() - 19, rx_pos.y())

    def update_fog_combo(self):

        show = self.atm_combo.currentText() == "Al Naboulsi"

        self.fog_combo.setVisible(show)

        if show:
            self.fog_combo.show()
        else:
            self.fog_combo.hide()

    def update_mission_mode(self):

        manual = self.mission_mode_combo.currentText() == "Manual Range"

        rows = self.input_sections["MISSION"]["rows"]

        rows["Range"]["label"].setVisible(manual)
        rows["Range"]["row"].setVisible(manual)

        for field in [
            "TX Latitude",
            "TX Longitude",
            "RX Latitude",
            "RX Longitude",
        ]:
            rows[field]["label"].setVisible(not manual)
            rows[field]["row"].setVisible(not manual)
            self.tx_maps_btn.setVisible(not manual)
            self.rx_maps_btn.setVisible(not manual)

            if not manual:
                self.position_map_buttons()

    def update_solve_for(self):

        mode = self.solve_for_combo.currentText()

        rows = self.input_sections["MISSION"]["rows"]

        # Show everything first
        rows["TX height"]["label"].show()
        rows["TX height"]["row"].show()

        rows["RX height"]["label"].show()
        rows["RX height"]["row"].show()

        rows["Minimum Height Above Sea"]["label"].show()
        rows["Minimum Height Above Sea"]["row"].show()

        if mode == "Minimum Height Above Sea":

            rows["Minimum Height Above Sea"]["label"].hide()
            rows["Minimum Height Above Sea"]["row"].hide()

        elif mode == "TX Height":

            rows["TX height"]["label"].hide()
            rows["TX height"]["row"].hide()

        elif mode == "RX Height":

            rows["RX height"]["label"].hide()
            rows["RX height"]["row"].hide()

        self.state.solve_for = mode

    # Refresh outputs

    def update_aerosol_fields(self, model=None):
        if model is None:
            model = self.aerosol_combo.currentText()
        is_angstrom = model == "Angstrom"

        tx_alpha_widget = (
            self.input_sections.get("TX_ENVIRONMENT", {})
            .get("widgets", {})
            .get("Aerosol Alpha")
        )
        rx_alpha_widget = (
            self.input_sections.get("RX_ENVIRONMENT", {})
            .get("widgets", {})
            .get("Aerosol Alpha")
        )

        if tx_alpha_widget:
            tx_alpha_widget.setEnabled(is_angstrom)
        if rx_alpha_widget:
            rx_alpha_widget.setEnabled(is_angstrom)

    def update_tracking_mode(self):

        mode = self.tracking_mode_combo.currentText()

        rows = self.input_sections["TRACKING"]["rows"]

        manual_inputs = [
            "Roll",
            "Pitch",
            "Yaw",
        ]

        if mode == "Manual":

            for name in manual_inputs:

                rows[name]["label"].show()
                rows[name]["row"].show()

        else:

            for name in manual_inputs:

                rows[name]["label"].hide()
                rows[name]["row"].hide()

    def update_slice_accuracy(self):

        mode = self.slice_accuracy_combo.currentText()

        self.state.slice_accuracy = mode

        if mode == "Low":
            self.state.maximum_height_difference_m = 2.0

        elif mode == "Medium":
            self.state.maximum_height_difference_m = 1.0

        elif mode == "High":
            self.state.maximum_height_difference_m = 0.5

        else:
            self.state.maximum_height_difference_m = 0.1

        self.slice_count_label.setText("Estimated Slices : Adaptive")

        self.slice_length_label.setText(
            f"Max Height Difference : {self.state.maximum_height_difference_m:.2f} m"
        )

    def clamp_int(self, widget, mn, mx):
        print("CLAMP:", widget.text())

        print("CLAMP CALLED:", widget.text())

        try:
            value = int(float(widget.text()))
        except Exception:
            value = mn

            value = max(mn, min(mx, value))

            widget.setText(str(value))

    def create_settings_tab(self):
        from PySide6.QtWidgets import (
            QWidget,
            QVBoxLayout,
            QGroupBox,
            QFormLayout,
            QDoubleSpinBox,
            QPushButton,
            QGridLayout,
            QLabel,
            QScrollArea,
        )

        settings = SettingsManager().load()
        page = QWidget()
        layout = QVBoxLayout(page)
        self.setting_boxes = {}

        # SLICE SETTINGS
        slice_group = QGroupBox("Slice Settings")
        slice_layout = QGridLayout()
        row = 0
        for mode in ["Low", "Medium", "High", "Research"]:
            lbl = QLabel(mode)
            lbl.setStyleSheet("font-weight:bold;")
            slice_layout.addWidget(lbl, row, 0)
            col = 1
            for key, value in settings["slice_modes"][mode].items():
                lbl_key = QLabel(key)
                box = QDoubleSpinBox()
                box.setDecimals(4)
                box.setMaximum(1000000)
                box.setValue(value)
                box.setFixedWidth(80)
                slice_layout.addWidget(lbl_key, row, col)
                slice_layout.addWidget(box, row, col + 1)
                self.setting_boxes[("slice_modes", mode, key)] = box
                col += 2
            row += 1
        slice_group.setLayout(slice_layout)
        layout.addWidget(slice_group)

        # DETECTOR DEFAULTS
        det_group = QGroupBox("Detector Defaults")
        det_layout = QGridLayout()
        row = 0
        for det_type, det_params in settings.get("detector_defaults", {}).items():
            lbl = QLabel(det_type)
            lbl.setStyleSheet("font-weight:bold;")
            det_layout.addWidget(lbl, row, 0)
            col = 1
            for key, value in det_params.items():
                lbl_key = QLabel(key)
                box = QDoubleSpinBox()
                box.setDecimals(4)
                box.setMaximum(1000000)
                box.setValue(value)
                box.setFixedWidth(80)
                det_layout.addWidget(lbl_key, row, col)
                det_layout.addWidget(box, row, col + 1)
                self.setting_boxes[("detector_defaults", det_type, key)] = box
                col += 2
            row += 1
        det_group.setLayout(det_layout)
        layout.addWidget(det_group)



        save = QPushButton("Save Settings")
        save.clicked.connect(self.save_settings)
        layout.addWidget(save)
        
        restore_btn = QPushButton("Restore Default Settings")
        restore_btn.clicked.connect(self.restore_default_settings)
        layout.addWidget(restore_btn)

        layout.addStretch()
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(page)

        return scroll

    def save_settings(self):
        manager = SettingsManager()
        settings = manager.load()

        for (category, mode, key), box in self.setting_boxes.items():
            if category not in settings:
                settings[category] = {}
            if mode != "default" and mode not in settings[category]:
                settings[category][mode] = {}
            
            if mode == "default":
                settings[category][key] = box.value()
            else:
                settings[category][mode][key] = box.value()

        manager.save(settings)
        
        # Dynamically update DETECTOR_DATABASE and refresh Data tab
        from core.ui_database import DETECTOR_DATABASE
        det_defaults = settings.get("detector_defaults", {})
        for det_type, det_params in det_defaults.items():
            if det_type in DETECTOR_DATABASE:
                new_list = []
                for name, old_val, unit, state_var in DETECTOR_DATABASE[det_type]:
                    if state_var == "detector_efficiency":
                        new_val = det_params.get("qe", old_val)
                    elif state_var == "dark_count_rate":
                        new_val = det_params.get("dcr_cps", old_val)
                    elif state_var == "detector_deadtime_ns":
                        new_val = det_params.get("dead_time_ns", old_val)
                    else:
                        new_val = old_val
                    new_list.append((name, new_val, unit, state_var))
                DETECTOR_DATABASE[det_type] = new_list
                
        self.update_detector_panel()
        
        print("Settings saved.")

    def restore_default_settings(self):
        manager = SettingsManager()
        manager.restore_defaults()
        settings = manager.load()

        for (category, mode, key), box in self.setting_boxes.items():
            if mode == "default":
                box.setValue(settings[category][key])
            else:
                box.setValue(settings[category][mode][key])

        # Also refresh Data tab with restored defaults
        from core.ui_database import DETECTOR_DATABASE
        det_defaults = settings.get("detector_defaults", {})
        for det_type, det_params in det_defaults.items():
            if det_type in DETECTOR_DATABASE:
                new_list = []
                for name, old_val, unit, state_var in DETECTOR_DATABASE[det_type]:
                    if state_var == "detector_efficiency":
                        new_val = det_params.get("qe", old_val)
                    elif state_var == "dark_count_rate":
                        new_val = det_params.get("dcr_cps", old_val)
                    elif state_var == "detector_deadtime_ns":
                        new_val = det_params.get("dead_time_ns", old_val)
                    else:
                        new_val = old_val
                    new_list.append((name, new_val, unit, state_var))
                DETECTOR_DATABASE[det_type] = new_list
                
        self.update_detector_panel()

        print("Default settings restored.")

    # ================= PHYSICS ENGINE =================
    def compute(self):
        logger.clear()

        self.mission = self.input_sections["MISSION"]["widgets"]

        self.rx_optics = self.input_sections["RX_OPTICS"]["widgets"]
        self.tx_optics = self.input_sections["TX_OPTICS"]["widgets"]
        self.optics = {}
        self.optics.update(self.tx_optics)
        self.optics.update(self.rx_optics)
        self.detector = self.input_sections["DETECTOR"]["widgets"]

        self.tx_env = self.input_sections["TX_ENVIRONMENT"]["widgets"]
        self.rx_env = self.input_sections["RX_ENVIRONMENT"]["widgets"]
        self.state.tracking_mode = self.tracking_mode_combo.currentText()

        self.track = self.input_sections["TRACKING"]["widgets"]

        self.sea = self.input_sections["MARINE"]["widgets"]

        try:
            print("COMPUTE STARTED")

            self.mission["Range"].text()
            print("STATE RANGE BEFORE =", self.state.link_distance_km)

            # =========================
            # READ GUI INPUTS
            # =========================
            self.state.mission_mode = self.mission_mode_combo.currentText()
            self.state.solve_for = self.solve_for_combo.currentText()
            self.update_solve_for()

            if self.mission_mode_combo.currentText() == "Manual Range":

                self.state.link_distance_km = self.get(
                    self.mission["Range"], default=10, mn=0.1
                )

            else:

                self.state.tx_latitude_deg = self.get(self.mission["TX Latitude"])

                self.state.tx_longitude_deg = self.get(self.mission["TX Longitude"])

                self.state.rx_latitude_deg = self.get(self.mission["RX Latitude"])

                self.state.rx_longitude_deg = self.get(self.mission["RX Longitude"])

            print("STATE RANGE AFTER =", self.state.link_distance_km)

            self.state.tx_height_msl_m = self.get(
                self.mission["TX height"], default=10, mn=0
            )

            self.state.rx_height_msl_m = self.get(
                self.mission["RX height"], default=15, mn=0
            )
            self.state.minimum_height_above_sea_m = self.get(
                self.mission["Minimum Height Above Sea"], default=5, mn=0
            )

            self.state.month = int(
                self.get(self.mission["Month"], default=6, mn=1, mx=12)
            )
            self.state.month = max(1, min(12, self.state.month))

            self.state.day = int(self.get(self.mission["Day"], default=15, mn=1, mx=31))
            self.state.day = max(1, min(31, self.state.day))

            self.state.time_of_day_hr = self.get(
                self.mission["Time of Day"], default=12, mn=0, mx=24
            )
            self.state.time_of_day_hr = max(0, min(24, self.state.time_of_day_hr))

            self.state.effective_earth_radius_factor = self.get(
                self.mission["Effective Earth Radius Factor"], default=1.333, mn=0
            )

            self.state.wavelength_nm = self.get(
                self.optics["Wavelength"], default=1550, mn=400, mx=2000
            )

            self.state.tx_beam_divergence_mrad = self.get(
                self.optics["Divergence"], default=0.1, mn=0
            )

            self.state.tx_aperture_mm = self.get(
                self.optics["TX aperture"], default=150, mn=1
            )

            self.state.rx_aperture_mm = self.get(
                self.optics["RX aperture"], default=600, mn=1
            )
            self.state.tx_optical_loss_dB = self.get(
                self.optics["TX Optical Loss"], default=1.0, mn=0
            )

            self.state.rx_optical_loss_dB = self.get(
                self.optics["RX Optical Loss"], default=1.0, mn=0
            )

            self.state.detector_efficiency = self.get(
                self.detector["Detector QE"], default=0.85, mn=0, mx=1
            )

            self.state.dark_count_rate = self.get(
                self.detector["Dark Count Rate"], default=100, mn=0
            )

            self.state.rx_fov_mrad = self.get(self.optics["FOV"], default=1.0, mn=0)

            bw = self.get(self.optics["RX Filter Bandwidth"], default=1.0, mn=0)

            self.state.optical_filter_bw_nm = bw
            self.state.rx_filter_bandwidth_nm = bw

            self.state.source_bandwidth_nm = self.get(self.optics["Source Bandwidth"])

            self.state.rx_filter_center_wavelength_nm = self.get(
                self.optics["RX Filter Center WL"]
            )

            self.state.tx_temperature_C = self.get(self.tx_env["Temperature"])
            self.state.rx_temperature_C = self.get(self.rx_env["Temperature"])

            self.state.tx_visibility_km = self.get(self.tx_env["Visibility"])
            self.state.rx_visibility_km = self.get(self.rx_env["Visibility"])

            self.state.tx_humidity_pct = self.get(self.tx_env["Humidity"])
            self.state.rx_humidity_pct = self.get(self.rx_env["Humidity"])

            self.state.tx_pressure_hPa = self.get(self.tx_env["Pressure"])
            self.state.rx_pressure_hPa = self.get(self.rx_env["Pressure"])
            self.state.moon_phase_percent = self.get(self.mission["Moon Phase"])

            self.state.tx_wind_speed_m_s = self.get(self.tx_env["Wind"])

            self.state.rx_wind_speed_m_s = self.get(self.rx_env["Wind"])

            # ATMOSPHERE EXTRA

            self.state.tx_cloud_cover_percent = self.get(self.tx_env["Cloud Cover"])

            self.state.rx_cloud_cover_percent = self.get(self.rx_env["Cloud Cover"])
            self.state.tx_cloud_base_height_m = self.get(
                self.tx_env["Cloud Base Height"]
            )

            self.state.rx_cloud_base_height_m = self.get(
                self.rx_env["Cloud Base Height"]
            )

            self.state.tx_aerosol_alpha = self.get(self.tx_env["Aerosol Alpha"])

            self.state.rx_aerosol_alpha = self.get(self.rx_env["Aerosol Alpha"])

            if self.state.tracking_mode == "Manual":
                self.state.roll_rms_deg = self.get(self.track["Roll"], default=0)
                self.state.pitch_rms_deg = self.get(self.track["Pitch"], default=0)
                self.state.yaw_rms_deg = self.get(self.track["Yaw"], default=0)
            self.state.gimbal_bw_hz = self.get(
                self.track["Gimbal BW"], default=10, mn=0
            )

            self.state.fsm_bw_hz = self.get(self.track["FSM BW"], default=200, mn=0)

            self.state.sea_state = self.get(self.sea["Sea State"], default=3, mn=0)

            self.state.sig_wave_height_m = self.get(
                self.sea["Wave Height"], default=1, mn=0
            )
            self.state.wave_height_m = self.state.sig_wave_height_m

            self.state.wave_period_s = self.get(
                self.sea["Wave Period"], default=5, mn=1
            )

            self.state.wave_direction_deg = self.get(
                self.sea["Wave Direction"], default=0
            )

            self.state.ship_heading_deg = self.get(self.sea["Ship Heading"], default=0)

            self.state.tx_rain_rate_mm_hr = self.get(self.tx_env["Rain Rate"])

            self.state.rx_rain_rate_mm_hr = self.get(self.rx_env["Rain Rate"])

            self.state.sea_surface_temperature_C = self.get(
                self.sea["Sea Surface Temp"], default=27
            )

            self.state.marine_BL_height_m = self.get(
                self.sea["Marine BL Height"], default=500, mn=0
            )

            self.state.atmospheric_model = self.atm_combo.currentText()
            self.state.fog_type = self.fog_combo.currentText()

            self.state.cn2_model = self.turb_combo.currentText()

            self.state.detector_model = self.det_combo.currentText()

            self.state.qkd_protocol = self.qkd_combo.currentText()
            self.state.geometric_loss_model = self.geom_combo.currentText()

            # Read QKD inputs from UI to state
            if "PROTOCOL" in self.qkd_input_sections:
                protocol_name = self.state.qkd_protocol
                if protocol_name in QKD_INPUT_DATABASE["PROTOCOL"]:
                    for name, inp in self.qkd_input_sections["PROTOCOL"][
                        "widgets"
                    ].items():
                        state_var = next(
                            (
                                v[-1]
                                for v in QKD_INPUT_DATABASE["PROTOCOL"][protocol_name]
                                if v[0] == name
                            ),
                            None,
                        )
                        if state_var:
                            setattr(
                                self.state,
                                state_var,
                                self.get(inp, getattr(self.state, state_var, 0)),
                            )

            print("COMPUTE MODEL =", self.state.geometric_loss_model)

            from main import run_simulation_kernel

            self.state.tracking_mode = self.tracking_mode_combo.currentText()
            print("STATE Wave Direction =", self.state.wave_direction_deg)
            print("STATE Ship Heading =", self.state.ship_heading_deg)
            self.update_slice_accuracy()
            if self.state.propagation_slices:

                n = len(self.state.propagation_slices)

                self.slice_count_label.setText(f"Total Slices : {n}")

                avg = (self.state.link_distance_km * 1000) / n

                self.slice_length_label.setText(f"Average Slice Length : {avg:.1f} m")

            run_simulation_kernel(self.state)

            # Refresh propagation diagram
            self.propagation_widget.state = self.state
            self.propagation_widget.update()
            self.propagation_widget.repaint()

            if self.state.solve_for == "TX Height":
                self.mission["TX height"].blockSignals(True)
                self.mission["TX height"].setText(f"{self.state.tx_height_msl_m:.3f}")
                self.mission["TX height"].blockSignals(False)

            elif self.state.solve_for == "RX Height":
                self.mission["RX height"].blockSignals(True)
                self.mission["RX height"].setText(f"{self.state.rx_height_msl_m:.3f}")
                self.mission["RX height"].blockSignals(False)

            elif self.state.solve_for == "Minimum Height Above Sea":
                self.mission["Minimum Height Above Sea"].blockSignals(True)
                self.mission["Minimum Height Above Sea"].setText(
                    f"{self.state.minimum_height_above_sea_m:.3f}"
                )
                self.mission["Minimum Height Above Sea"].blockSignals(False)

            self.update_slice_accuracy()
            self.update_slice_table()
            self.generate_plot()
            self.update_tracking_mode()

        except Exception as e:

            import traceback

            traceback.print_exc()  # terminal

            print(traceback.format_exc())
            print("\n========== ERROR ==========")
            # self.sys_out.setText(
            # traceback.format_exc()
            # )

            self.state.debug_message = str(e)

    def update_slice_table(self):

        print("Updating Slice Table...")

        slices = getattr(self.state, "propagation_slices", [])

        total = len(slices)

        self.total_slice_label.setText(f"Total Slices : {total}")

        if total == 0:

            self.slice_table.clearContents()

            self.display_slice_label.setText("Displaying : 0-0")

            return

        mode = self.slice_view_combo.currentText()
        selected_columns = [
            item.text() for item in self.slice_compare_combo.selectedItems()
        ]
        if mode == "First 10":

            shown = slices[:10]
            start = 0
            end = len(shown)

        elif mode == "Middle 10":

            start = max(0, total // 2 - 5)
            end = min(start + 10, total)
            shown = slices[start:end]

        elif mode == "Last 10":

            start = max(0, total - 10)
            end = total
            shown = slices[start:end]

        elif mode == "All Slices":

            start = 0
            end = total
            shown = slices
        # Show every column by default
        self.display_slice_label.setText(f"Displaying : {start+1}-{end}")

        self.slice_table.clearContents()

        self.slice_table.setRowCount(len(shown))
        if len(shown) == 0:
            return

        from core.state import PropagationSlice

        s_vars = vars(shown[0])
        hidden_fields = {
            "wind_direction_deg",
            "refinement_level",
            "dn_dz",
            "surface_height_m",
            "beam_above_surface_m",
            "height_above_msl_m",
            "start_height_m",
            "center_height_m",
            "end_height_m",
            "earth_drop_m",
        }

        category_mode = getattr(self, "slice_category_combo", None)
        selected_category = (
            category_mode.currentText() if category_mode else "All Parameters"
        )

        filtered_keys = []
        for k in s_vars.keys():
            if not k.startswith("_") and k not in hidden_fields:
                if (
                    selected_category == "All Parameters"
                    or PropagationSlice.get_category(k) == selected_category
                ):
                    filtered_keys.append(k)

        new_headers = [PropagationSlice.format_attribute_name(k) for k in filtered_keys]

        if not hasattr(self, "headers") or self.headers != new_headers:
            self.headers = new_headers
            selected_items = [
                item.text() for item in self.slice_compare_combo.selectedItems()
            ]
            self.slice_compare_combo.blockSignals(True)
            self.slice_compare_combo.clear()
            self.slice_compare_combo.addItems(self.headers)
            for i in range(self.slice_compare_combo.count()):
                item = self.slice_compare_combo.item(i)
                if item.text() in selected_items:
                    item.setSelected(True)
            self.slice_compare_combo.blockSignals(False)

        selected = [item.text() for item in self.slice_compare_combo.selectedItems()]
        if not selected:
            selected = self.headers

        self.slice_table.setColumnCount(len(selected))
        self.slice_table.setHorizontalHeaderLabels(selected)

        for row, s in enumerate(shown):
            row_data = {}
            for k in filtered_keys:
                name = PropagationSlice.format_attribute_name(k)
                val = getattr(s, k)
                row_data[name] = PropagationSlice.format_value(val, k)

            for col, header in enumerate(selected):
                if header in row_data:
                    self.slice_table.setItem(
                        row, col, QTableWidgetItem(str(row_data[header]))
                    )

    def generate_plot(self):

        self.canvas.fig.clf()

        self.canvas.ax = None

        xlabel_map = {
            # ===== MISSION =====
            "Range": "Range (km)",
            "TX height": "TX Height (m)",
            "RX height": "RX Height (m)",
            "Elevation": "Elevation (deg)",
            "Effective Earth Radius Factor": "Effective Earth Radius Factor",
            "Coherence Time": "Coherence Time (ms)",
            "Isoplanatic Angle": "Isoplanatic Angle (urad)",
            # ===== OPTICS =====
            "Wavelength": "Wavelength (nm)",
            "Divergence": "Divergence (mrad)",
            "TX aperture": "TX Aperture (mm)",
            "RX aperture": "RX Aperture (mm)",
            "Detector QE": "Detector QE",
            "Dark counts": "Dark Count Rate",
            "PPR (MHz)": "Pulse Repetition Rate (MHz)",
            "FOV": "FOV (mrad)",
            "RX Filter Bandwidth": "RX Filter Bandwidth (nm)",
            "Beam Quality M2": "Beam Quality M2",
            "Coupling Efficiency": "Coupling Efficiency",
            # ===== ENVIRONMENT =====
            "Temperature": "Temperature (°C)",
            "Humidity": "Humidity (%)",
            "Visibility": "Visibility (km)",
            "Wind": "Wind Speed (m/s)",
            "Pressure": "Pressure (hPa)",
            # ===== TRACKING =====
            "Roll": "Roll (deg)",
            "Pitch": "Pitch (deg)",
            "Yaw": "Yaw (deg)",
            "Gimbal BW": "Gimbal BW (Hz)",
            "FSM BW": "FSM BW (Hz)",
            # ===== MARINE =====
            "Sea State": "Sea State",
            "Wave Height": "Wave Height (m)",
            "Wave Slope": "Wave Slope (deg)",
            "Evap Duct Height": "Evap Duct Height (m)",
            "Marine BL Height": "Marine BL Height (m)",
            "Rain Rate": "Rain Rate (mm/hr)",
            "Sea Surface Temp": "Sea Surface Temp (°C)",
            "Inner Scale": "Inner Scale (mm)",
            "Outer Scale": "Outer Scale (m)",
            # ===== ATM EXTRA =====
            "Extra Vis": "Extra Visibility (km)",
            "Extra Wind": "Extra Wind (m/s)",
            "Cloud Cover": "Cloud Cover (%)",
            "Cloud Base Height": "Cloud Base Height (m)",
            "Aerosol Alpha": "Aerosol Alpha",
        }

        output_widgets = self.output_widgets
        print("=== GENERATE PLOT ===")
        print("Atmospheric Loss =", self.state.atmospheric_loss_dB)
        print("QBER =", self.state.qber)
        print("Secure Key =", self.state.secure_key_rate)
        print("UI propagation_direction =", repr(self.state.propagation_direction))

        for section_name, outputs in QKD_OUTPUT_DATABASE.items():
            if section_name in self.qkd_output_widgets:
                widgets = self.qkd_output_widgets[section_name]
                for display_name, state_var, unit in outputs:
                    value = getattr(self.state, state_var, "N/A")
                    from core.state import PropagationSlice

                    if isinstance(value, (float, int)) and not isinstance(value, bool):
                        value_str = PropagationSlice.format_value(value, state_var)
                        if value_str and value_str[-1].isdigit():
                            text = f"{value_str} {unit}" if unit else value_str
                        else:
                            text = value_str
                    else:
                        value_str = str(value)
                        text = f"{value_str} {unit}" if unit else value_str

                    if state_var in widgets:
                        widgets[state_var][0].setText(text)

            for proto in self.qkd_verifier_labels:
                qkd_ver_text = getattr(self.state, "verifier_text", {}).get(
                    proto, f"Waiting for {proto} model..."
                )
                self.qkd_verifier_labels[proto].setText(qkd_ver_text)

        for section_name, outputs in OUTPUT_DATABASE.items():

            lines = []

            for display_name, state_var, unit in outputs:
                # ------------------------------------------
                # Show only the solved quantity
                # ------------------------------------------

                if state_var == "tx_height_msl_m":
                    if self.state.solve_for != "TX Height":
                        continue

                elif state_var == "rx_height_msl_m":
                    if self.state.solve_for != "RX Height":
                        continue

                elif state_var == "minimum_height_above_sea_m":
                    if self.state.solve_for != "Minimum Height Above Sea":
                        continue

                value = getattr(self.state, state_var, "N/A")
                from core.state import PropagationSlice

                if isinstance(value, (float, int)) and not isinstance(value, bool):
                    value_str = PropagationSlice.format_value(value, state_var)
                    if value_str and value_str[-1].isdigit():
                        text = (
                            f"{display_name} = {value_str} {unit}"
                            if unit
                            else f"{display_name} = {value_str}"
                        )
                    else:
                        text = f"{display_name} = {value_str}"
                else:
                    value_str = str(value)
                    text = (
                        f"{display_name} = {value_str} {unit}"
                        if unit
                        else f"{display_name} = {value_str}"
                    )
                lines.append(text)

            for out_w in self.data_output_widgets_list:
                if section_name in out_w:
                    widgets = out_w[section_name]
                    for display_name, state_var, unit in outputs:
                        # Keep the same hiding logic
                        if state_var == "tx_height_msl_m":
                            if self.state.solve_for != "TX Height":
                                continue

                        elif state_var == "rx_height_msl_m":
                            if self.state.solve_for != "RX Height":
                                continue

                        elif state_var == "minimum_height_above_sea_m":
                            if self.state.solve_for != "Minimum Height Above Sea":
                                continue

                        value = getattr(self.state, state_var, "N/A")
                        from core.state import PropagationSlice

                        if isinstance(value, (float, int)) and not isinstance(
                            value, bool
                        ):
                            value_str = PropagationSlice.format_value(value, state_var)
                            if value_str and value_str[-1].isdigit():
                                text = f"{value_str} {unit}" if unit else value_str
                            else:
                                text = value_str
                        else:
                            value_str = str(value)
                            text = f"{value_str} {unit}" if unit else value_str

                        if state_var in widgets:
                            widgets[state_var][0].setText(text)

        geo_ver = getattr(self.state, "verifier_text", {}).get(
            "geo", "Waiting for geometry model..."
        )
        solar_ver = getattr(self.state, "verifier_text", {}).get(
            "solar", "Waiting for solar model..."
        )
        terrain_ver = getattr(self.state, "verifier_text", {}).get(
            "terrain", "Waiting for terrain model..."
        )
        atm_ver = getattr(self.state, "verifier_text", {}).get(
            "atm", "Waiting for atmospheric model..."
        )
        turb_ver = getattr(self.state, "verifier_text", {}).get(
            "turb", "Waiting for turbulence model..."
        )
        track_ver = getattr(self.state, "verifier_text", {}).get(
            "track", "Waiting for tracking model..."
        )
        slice_ver = getattr(self.state, "verifier_text", {}).get(
            "slice", "Waiting for slicing model..."
        )
        link_ver = getattr(self.state, "verifier_text", {}).get(
            "link", "Waiting for link budget model..."
        )
        det_ver = getattr(self.state, "verifier_text", {}).get(
            "det", "Waiting for detector model..."
        )
        qkd_ver = getattr(self.state, "verifier_text", {}).get(
            "qkd", "Waiting for QKD model..."
        )

        sys_ver = f"""
System Status
Status = {getattr(self.state,"simulation_status","UNKNOWN")}
LOS = {getattr(self.state,"los",False)}
Link Available = {getattr(self.state,"link_available",False)}
Link Blocked Reason = {getattr(self.state,"link_blocked_reason","")}
System Health = {getattr(self.state,"system_health","UNKNOWN")}
Availability = {getattr(self.state,"availability_percent",0):.2f}%
Target QBER = {100*getattr(self.state,"target_qber",0):.2f}%
Actual QBER = {100*getattr(self.state,"qber",0):.4f}%
Target SKR = {getattr(self.state,"target_secure_key_rate_bps",0):.3e} bps
Actual SKR = {getattr(self.state,"secure_key_rate",0):.3e} bps
Target Availability = {100*getattr(self.state,"target_link_availability",0):.2f}%
Actual Availability = {getattr(self.state,"availability_percent",0):.2f}%
Debug Message = {getattr(self.state,"debug_message","")}
Simulation Time = {getattr(self.state,"simulation_time_sec",0.0):.2f} s
"""

        for ver_dict in self.data_verifier_dicts_list:
            if "geo" in ver_dict:
                ver_dict["geo"].setText(geo_ver)
            if "solar" in ver_dict:
                ver_dict["solar"].setText(solar_ver)
            if "terrain" in ver_dict:
                ver_dict["terrain"].setText(terrain_ver)
            if "atm" in ver_dict:
                ver_dict["atm"].setText(atm_ver)
            if "turb" in ver_dict:
                ver_dict["turb"].setText(turb_ver)
            if "track" in ver_dict:
                ver_dict["track"].setText(track_ver)
            if "slice" in ver_dict:
                ver_dict["slice"].setText(slice_ver)
            if "link" in ver_dict:
                ver_dict["link"].setText(link_ver)
            if "det" in ver_dict:
                ver_dict["det"].setText(det_ver)
            if "qkd" in ver_dict:
                ver_dict["qkd"].setText(qkd_ver)
            if "sys" in ver_dict:
                ver_dict["sys"].setText(sys_ver)

        x = []

        plot_data = {}

        for key, chk in self.output_checks.items():

            if chk.isChecked():

                plot_data[key] = []
        if len(plot_data) == 0:

            return

        mixed = False

        selected_logs = []

        for key, chk in self.output_checks.items():

            if chk.isChecked():

                selected_logs.append(self.output_log_checks[key].isChecked())

        mixed = len(set(selected_logs)) > 1

        xmin = float(self.min_edit.text())

        xmax = float(self.max_edit.text())

        points = int(self.points_edit.text())

        import numpy as np

        if xmin > xmax:

            xmin, xmax = xmax, xmin

        xvals = np.linspace(xmin, xmax, points)

        print("\n===== PLOT DATA BEFORE SWEEP =====")
        for k, v in plot_data.items():
            print(k, len(v))

        import copy

        original_state = copy.deepcopy(self.state)
        original_state.plot_mode = True

        # =====================================================
        # PARAMETRIC SWEEP SETTINGS
        # =====================================================

        parametric_enabled = self.enable_parametric_sweep_chk.isChecked()

        if parametric_enabled:

            sweep_param = self.sweep_parameter_combo.currentText()

            if sweep_param == self.xaxis_combo.currentText():

                QMessageBox.warning(
                    self,
                    "Invalid Sweep",
                    "X Axis and Sweep Parameter must be different.",
                )
                return

            sweep_state_var = self.sweep_parameter_combo.currentData()

            print("Sweep parameter =", sweep_param)
            print("State variable =", sweep_state_var)
            print("Mapping =", self.input_name_map)

            smin = float(self.sweep_min_edit.text())
            smax = float(self.sweep_max_edit.text())
            spoints = int(self.sweep_points_edit.text())

            if smin > smax:
                smin, smax = smax, smin

            if self.sweep_linear_radio.isChecked():
                sweep_values = np.linspace(smin, smax, spoints)
            else:
                sweep_values = np.logspace(np.log10(smin), np.log10(smax), spoints)

        else:

            sweep_values = [None]
        all_curves = []
        for sweep_value in sweep_values:

            x = []

            for key in plot_data:
                plot_data[key] = []

            if parametric_enabled:
                setattr(original_state, sweep_state_var, sweep_value)

            for r in xvals:
                param = self.xaxis_combo.currentText()
                state_var = self.xaxis_combo.currentData()

                temp_state = copy.deepcopy(original_state)

                # Set sweep parameter first
                if parametric_enabled:
                    setattr(temp_state, sweep_state_var, sweep_value)
                    print("After setattr:")
                    print("visibility_km =", temp_state.visibility_km)
                    print(sweep_state_var, "=", getattr(temp_state, sweep_state_var))

                # Then set X-axis parameter
                setattr(temp_state, state_var, r)

                print(param)

                print(state_var)

                print(getattr(temp_state, state_var))
                from main import run_simulation_kernel

                print("===================================")
                print("Sweep Value =", sweep_value)
                print("Before kernel visibility =", temp_state.visibility_km)
                run_simulation_kernel(temp_state)

                print("After kernel visibility =", temp_state.visibility_km)
                print("Visibility Loss =", temp_state.visibility_loss_dB)
                print(
                    "Visibility:",
                    sweep_value,
                    "Loss:",
                    temp_state.visibility_loss_dB,
                    "SKR:",
                    temp_state.secure_key_rate,
                )
                print("Wind =", temp_state.wind_speed_m_s)
                print("Cn2 =", temp_state.Cn2_m2_3)
                print("r0 =", temp_state.fried_parameter_m)
                print("Rytov =", temp_state.rytov_variance)
                print("----------------------")
                print("X =", value)
                print("Visibility =", temp_state.visibility_km)
                print("Range =", temp_state.link_distance_km)
                print("Visibility Loss =", temp_state.visibility_loss_dB)
                x.append(r)

                for key in plot_data:

                    attr = self.output_state_map.get(key)

                    if not attr:

                        print("Missing:", key)

                        continue

                    value = getattr(temp_state, attr, 0)

                    plot_data[key].append(value)
                    print(f"{key}: x={r}, y={value}")

                    print(key, len(plot_data[key]))
            curve = {"x": x.copy(), "plot_data": copy.deepcopy(plot_data), "label": ""}

            if parametric_enabled:
                curve["label"] = f"{sweep_param} = {sweep_value:.3f}"

            all_curves.append(curve)
            print(len(all_curves))
        self.state = original_state
        if not self.separate_plot_chk.isChecked():

            self.canvas.fig.clf()

            ax_linear = self.canvas.fig.add_subplot(111)

            ax_log = None

            # =====================================================
            # Draw every sweep curve
            # =====================================================

            for curve in all_curves:

                x = curve["x"]

                pdata = curve["plot_data"]

                curve_label = curve["label"]

                for key, y in pdata.items():

                    display_name = key.split("|")[1]

                    if curve_label:
                        legend = f"{display_name} ({curve_label})"
                    else:
                        legend = display_name

                    if len(y) != len(x):
                        continue

                    if self.output_log_checks[key].isChecked():

                        if ax_log is None:

                            ax_log = ax_linear.twinx()
                            ax_log.set_yscale("log")

                        ax_log.plot(x, y, linewidth=2, linestyle="--", label=legend)

                    else:

                        ax_linear.plot(x, y, linewidth=2, label=legend)

            ax_linear.grid(True, alpha=0.3)

            selected_linear = []

            for key, chk in self.output_checks.items():

                if chk.isChecked() and not self.output_log_checks[key].isChecked():

                    selected_linear.append(key)

            if len(selected_linear) == 1:

                key = selected_linear[0]

                unit = self.output_unit_map.get(key, "")

                ylabel = key.split("|")[1]

                if unit:
                    ylabel += f" ({unit})"

                ax_linear.set_ylabel(ylabel)

            else:

                ax_linear.set_ylabel("Output Value")

            handles1, labels1 = ax_linear.get_legend_handles_labels()

            if ax_log is not None:

                handles2, labels2 = ax_log.get_legend_handles_labels()

                ax_linear.legend(handles1 + handles2, labels1 + labels2)

            else:

                ax_linear.legend()

            self.canvas.ax = ax_linear

            self.canvas.ax.grid(True, alpha=0.3)

            self.canvas.ax.grid(True, alpha=0.3)
        else:
            print("SEPARATE PLOT MODE")

            self.canvas.fig.clf()
            selected_outputs = []

            for name, chk in self.output_checks.items():

                if chk.isChecked():

                    selected_outputs.append(name)

            n = len(plot_data)
            if n <= 4:

                cols = 2

            elif n <= 9:

                cols = 3

            elif n <= 16:

                cols = 4

            else:

                cols = 5

            rows = math.ceil(n / cols)

            for i, name in enumerate(selected_outputs):

                ax = self.canvas.fig.add_subplot(rows, cols, i + 1)

                # Draw every sweep on this subplot
                for curve in all_curves:

                    x = curve["x"]
                    y = curve["plot_data"][name]

                    if curve["label"]:
                        ax.plot(x, y, linewidth=2, label=curve["label"])
                    else:
                        ax.plot(x, y, linewidth=2)

                display_name = name.split("|")[1]

                display_name = name.split("|")[1]
                print(display_name, self.output_log_checks[name].isChecked())

                if self.output_log_checks[name].isChecked():

                    if max(y) > 0:

                        ax.set_yscale("log")

                else:

                    ax.set_yscale("linear")
                ax.set_title(display_name, fontsize=10, fontweight="bold")
                unit = self.output_unit_map.get(name, "")

                ylabel = display_name

                if unit:

                    ylabel += f" ({unit})"

                ax.set_ylabel(ylabel, fontsize=8)

                ax.grid(True, alpha=0.3)
                if parametric_enabled:
                    ax.legend(fontsize=8)

                param = self.xaxis_combo.currentText()

                ax.set_xlabel(xlabel_map.get(param, param), fontsize=8)

        if not self.separate_plot_chk.isChecked():

            param = self.xaxis_combo.currentText()

            self.canvas.ax.set_xlabel(xlabel_map.get(param, param))
        self.canvas.fig.tight_layout(pad=2.5, h_pad=2.0, w_pad=2.0)

        self.plot_data = plot_data

        self.trade_x = x

        self.canvas.draw()

    def clear_outputs(self):

        # Clear output checkboxes
        for chk in self.output_checks.values():
            chk.setChecked(False)

        # Clear Log checkboxes
        for chk in self.output_log_checks.values():
            chk.setChecked(False)

        # Clear graph
        self.canvas.fig.clf()
        self.canvas.ax = self.canvas.fig.add_subplot(111)
        self.canvas.draw()

        # Clear stored plot data
        self.plot_data = {}
        self.trade_x = []

    def save_plot_png(self):

        from PySide6.QtWidgets import QFileDialog

        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Plot", "", "PNG Files (*.png)"
        )

        if filename:

            self.canvas.fig.savefig(filename, dpi=300)

        print("Saved:", filename)

    def save_results_csv(self):

        from PySide6.QtWidgets import QFileDialog

        import csv

        filename, _ = QFileDialog.getSaveFileName(
            self, "Save CSV", "", "CSV Files (*.csv)"
        )

        if not filename:

            return

        with open(filename, "w", newline="") as f:

            writer = csv.writer(f)

            header = ["X"]

            header.extend(self.plot_data.keys())

            writer.writerow(header)

            for i in range(len(self.trade_x)):

                row = [self.trade_x[i]]

                for y in self.plot_data.values():

                    row.append(y[i])

            writer.writerow(row)

        print("CSV Saved:", filename)

        print("CURRENT X AXIS =", self.xaxis_combo.currentText())
