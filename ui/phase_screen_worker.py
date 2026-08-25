"""
phase_screen_worker.py
v0.4.1

Background QRunnable that generates a slice's phase screen and near/mid/far
propagation images off the GUI thread, so the FFT work in models/phase_screen.py
never freezes the SCHEMATIC tab while the user hovers.
"""

from PySide6.QtCore import QObject, QRunnable, Signal

from models.phase_screen import (
    generate_slice_phase_screen,
    render_near_mid_far,
    compute_default_distances,
    estimate_aperture_transmittance,
    propagate_cumulative,
)


class PhaseScreenWorkerSignals(QObject):
    # slice_id, distances_m, images, eta_far, r0_used_m
    finished = Signal(int, tuple, list, float, float)
    error = Signal(int, str)  # slice_id, message


class PhaseScreenWorker(QRunnable):

    def __init__(self, slice_obj, wavelength_m, total_link_m=None, grid_size=256):
        super().__init__()
        self.slice_obj = slice_obj
        self.wavelength_m = wavelength_m
        self.total_link_m = total_link_m
        self.grid_size = grid_size
        self.signals = PhaseScreenWorkerSignals()

    def run(self):
        slice_id = self.slice_obj.slice_id
        try:
            phase_rad, delta, r0_used = generate_slice_phase_screen(
                self.slice_obj, self.wavelength_m, grid_size=self.grid_size
            )
            distances_m = compute_default_distances(self.total_link_m)

            beam_waist_m = self.slice_obj.beam_radius_m
            if beam_waist_m <= 0:
                beam_waist_m = max(self.slice_obj.beam_diameter_m / 2.0, 0.02)

            images = render_near_mid_far(
                phase_rad, delta, self.wavelength_m, beam_waist_m, distances_m
            )

            aperture_radius_m = beam_waist_m
            eta_far = estimate_aperture_transmittance(images[-1], delta, aperture_radius_m)

            self.signals.finished.emit(slice_id, distances_m, images, eta_far, r0_used)
        except Exception as exc:
            self.signals.error.emit(slice_id, str(exc))


class CumulativePhaseScreenWorkerSignals(QObject):
    # slice_id, distances_m, images, eta_far, r0_used_m
    finished = Signal(int, tuple, list, float, float)
    error = Signal(int, str)


class CumulativePhaseScreenWorker(QRunnable):
    """Split-step propagation through slices 0 … target on a background thread."""

    def __init__(self, all_slices, target_slice_idx, wavelength_m,
                 beam_waist_m, total_link_m=None, grid_size=256):
        super().__init__()
        self.all_slices = all_slices
        self.target_slice_idx = target_slice_idx
        self.wavelength_m = wavelength_m
        self.beam_waist_m = beam_waist_m
        self.total_link_m = total_link_m
        self.grid_size = grid_size
        self.signals = CumulativePhaseScreenWorkerSignals()

    def run(self):
        target = self.all_slices[self.target_slice_idx]
        slice_id = target.slice_id
        try:
            distances_m, images, eta_far, r0_used = propagate_cumulative(
                self.all_slices,
                self.target_slice_idx,
                self.wavelength_m,
                self.beam_waist_m,
                total_link_m=self.total_link_m,
                grid_size=self.grid_size,
            )
            self.signals.finished.emit(slice_id, distances_m, images, eta_far, r0_used)
        except Exception as exc:
            self.signals.error.emit(slice_id, str(exc))
