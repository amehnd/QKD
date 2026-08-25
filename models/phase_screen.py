"""
phase_screen.py
v0.4.1

Per-slice atmospheric phase screen generation and beam propagation, used
by the SCHEMATIC tab's hover diagnostic (ui/phase_screen_popup.py).

This is a diagnostic/visualization layer only: it shows what one random
realization of a slice's turbulence might look like to a Gaussian beam.
It does not feed back into the reported link budget / SKR chain, which
keeps using the analytic statistics already computed by turbulence.py
(fried_parameter_m, Cn2, rytov_variance) via link_budget.py / detector.py.

Method: FFT + subharmonics (Lane, Glindemann & Dainty 1992), via aotools'
ft_sh_phase_screen(). Propagation via aotools' angularSpectrum(). See
PHASE_SCREEN_RESEARCH_AND_PLAN_3.md for the full derivation and references.
"""

import numpy as np
from aotools.turbulence import ft_sh_phase_screen
from aotools.opticalpropagation import angularSpectrum

# Outer/inner turbulence scale defaults (metres). Neither quantity exists
# yet in SimulationState/PropagationSlice, so these are literature-typical
# placeholders (see plan Part 4, "a real gap this surfaced"). Revisit if
# outer_scale_m / inner_scale_m are ever added to state.py.
DEFAULT_OUTER_SCALE_M = 50.0
DEFAULT_INNER_SCALE_M = 0.005

GRID_SIZE_DEFAULT = 256

# Floors so degenerate/unset slice geometry can't produce a zero-size grid
# or divide-by-zero before a simulation has actually been run.
MIN_FRIED_PARAMETER_M = 1e-3
MIN_BEAM_WAIST_M = 0.01
MIN_CN2 = 1e-18

# Fixed path length used ONLY to turn a slice's Cn2 into an r0 for this
# popup's phase screen -- deliberately NOT the slice's own length_m.
# turbulence.py computes fried_parameter_m as (0.423 k^2 Cn2 slice_L)^(-3/5),
# so it is a function of the adaptive slicer's (highly variable) bin size as
# well as Cn2. Reusing it directly here would make a short slice look
# "calmer" than a long one purely because it's a shorter bin, even when its
# Cn2 (the actual air property) is the same or worse. Recomputing r0 from
# Cn2 over one shared reference length makes what changes between slices'
# popups be the atmosphere at that point, not the slicer's bin size.
REFERENCE_LENGTH_M = 100.0


def compute_reference_r0(cn2, wavelength_m, reference_length_m=REFERENCE_LENGTH_M):
    """Fried parameter (m) from Cn2 alone, over a fixed reference path length.

    Same functional form as turbulence.py's per-slice r0, but with a constant
    length so cross-slice comparisons reflect Cn2, not slice size.
    """
    cn2 = max(float(cn2), MIN_CN2)
    k = 2.0 * np.pi / max(float(wavelength_m), 1e-12)
    base = max(0.423 * k ** 2 * cn2 * reference_length_m, 1e-18)
    return base ** (-3.0 / 5.0)


def generate_slice_phase_screen(slice_obj, wavelength_m, grid_size=GRID_SIZE_DEFAULT, seed=None):
    """One random phase screen (radians), sized from this slice's Cn2.

    Uses compute_reference_r0() (Cn2 over a fixed reference length) rather
    than slice_obj.fried_parameter_m, so screens are comparable slice to
    slice regardless of adaptive slicing bin size. Falls back to the app's
    own fried_parameter_m only if Cn2 hasn't been computed yet (e.g. before
    "Run Simulation").

    Returns (phase_rad, delta, r0_used) where delta is metres/pixel.
    """
    if slice_obj.Cn2 > 0:
        r0 = compute_reference_r0(slice_obj.Cn2, wavelength_m)
    else:
        r0 = float(slice_obj.fried_parameter_m)
    r0 = max(r0, MIN_FRIED_PARAMETER_M)

    beam_diam = max(float(slice_obj.beam_diameter_m), 4.0 * r0, 4.0 * MIN_BEAM_WAIST_M)
    delta = beam_diam / grid_size

    if seed is None:
        seed = int(slice_obj.slice_id)

    phase_rad = ft_sh_phase_screen(
        r0=r0,
        N=grid_size,
        delta=delta,
        L0=DEFAULT_OUTER_SCALE_M,
        l0=DEFAULT_INNER_SCALE_M,
        seed=seed,
    )
    return phase_rad, delta, r0


def compute_default_distances(total_link_m=None):
    """Near/mid/far propagation distances (metres), fixed across all slices.

    Deliberately NOT a function of the individual slice's own length.
    fried_parameter_m is already computed per-slice as a function of that
    slice's length (turbulence.py: r0 = (0.423 k^2 Cn2 * slice_L)^(-3/5)),
    so a shorter slice already gets a larger, "calmer-looking" r0 for that
    reason alone -- it is NOT evidence the atmosphere is actually weaker
    there. Tying near/mid/far to slice_L as well would double that effect
    and make cross-slice comparisons meaningless (a short slice would look
    doubly "cleaner": bigger r0 *and* less propagation distance shown).
    Using the same fixed distances for every slice means what changes
    panel-to-panel is only each slice's own r0/Cn2, which is the actual
    turbulence comparison the popup is meant to show.
    """
    base = float(total_link_m) if total_link_m and total_link_m > 0 else 1000.0

    near = max(base * 0.01, 5.0)
    mid = max(base * 0.05, 25.0)
    far = max(base * 0.15, 75.0)
    return (near, mid, far)


def render_near_mid_far(phase_rad, delta, wavelength_m, beam_waist_m, distances_m):
    """Apply the screen to a Gaussian field, propagate to 3 distances.

    Returns a list of 2D intensity arrays (one per distance in distances_m).
    """
    N = phase_rad.shape[0]
    beam_waist_m = max(float(beam_waist_m), MIN_BEAM_WAIST_M)

    x = (np.arange(N) - N // 2) * delta
    X, Y = np.meshgrid(x, x)
    amplitude = np.exp(-(X ** 2 + Y ** 2) / beam_waist_m ** 2)
    field = amplitude * np.exp(1j * phase_rad)

    images = []
    for z in distances_m:
        propagated = angularSpectrum(field, wavelength_m, delta, delta, float(z))
        images.append(np.abs(propagated) ** 2)
    return images


def estimate_aperture_transmittance(intensity, delta, aperture_radius_m):
    """Fraction of the panel's power landing inside a circular aperture.

    A quick, single-realization stand-in for the transmittance eta
    described in the research plan (Vasylyev et al. 2023) -- illustrative
    only, not a substitute for the analytic P(eta) pipeline.
    """
    N = intensity.shape[0]
    x = (np.arange(N) - N // 2) * delta
    X, Y = np.meshgrid(x, x)
    r2 = X ** 2 + Y ** 2

    total = intensity.sum()
    if total <= 0:
        return 0.0

    inside = intensity[r2 <= aperture_radius_m ** 2].sum()
    return float(inside / total)


# ── Cumulative (split-step) propagation ──────────────────────────────

def propagate_cumulative(
    all_slices,
    target_slice_idx,
    wavelength_m,
    beam_waist_m,
    total_link_m=None,
    grid_size=GRID_SIZE_DEFAULT,
    base_seed=42,
):
    """Split-step beam propagation through slices 0 … target_slice_idx.

    Unlike generate_slice_phase_screen() + render_near_mid_far(), which
    start from a fresh Gaussian every time, this function carries the
    complex electric field forward through every preceding slice so the
    result at slice N includes the accumulated distortions of slices
    0 … N-1.

    Returns (distances_m, images, eta_far, r0_target) — same shape as
    the independent pathway so the popup can display them identically.
    """
    beam_waist_m = max(float(beam_waist_m), MIN_BEAM_WAIST_M)

    # Use the same grid sizing logic as the independent mode so the two
    # rows in the popup are visually comparable pixel-for-pixel.
    target = all_slices[target_slice_idx]
    if target.Cn2 > 0:
        r0_target = compute_reference_r0(target.Cn2, wavelength_m)
    else:
        r0_target = float(target.fried_parameter_m)
    r0_target = max(r0_target, MIN_FRIED_PARAMETER_M)

    beam_diam = max(float(target.beam_diameter_m), 4.0 * r0_target, 4.0 * MIN_BEAM_WAIST_M)
    delta = beam_diam / grid_size

    # Build a Gaussian field on this grid
    x = (np.arange(grid_size) - grid_size // 2) * delta
    X, Y = np.meshgrid(x, x)
    field = np.exp(-(X ** 2 + Y ** 2) / beam_waist_m ** 2).astype(np.complex128)

    # Walk through slices 0 … target_slice_idx
    for i in range(target_slice_idx + 1):
        s = all_slices[i]

        # Compute r0 for this slice's phase screen
        if s.Cn2 > 0:
            r0_i = compute_reference_r0(s.Cn2, wavelength_m)
        else:
            r0_i = float(s.fried_parameter_m)
        r0_i = max(r0_i, MIN_FRIED_PARAMETER_M)

        # Generate phase screen for this slice
        screen = ft_sh_phase_screen(
            r0=r0_i,
            N=grid_size,
            delta=delta,
            L0=DEFAULT_OUTER_SCALE_M,
            l0=DEFAULT_INNER_SCALE_M,
            seed=base_seed + int(s.slice_id),
        )

        # Apply phase screen
        field = field * np.exp(1j * screen)

        # Free-space propagate across this slice's physical length
        slice_length = max(float(s.length_m), 1.0)
        field = angularSpectrum(field, wavelength_m, delta, delta, slice_length)

    # Now render near/mid/far from the accumulated field
    distances_m = compute_default_distances(total_link_m)
    images = []
    for z in distances_m:
        propagated = angularSpectrum(field, wavelength_m, delta, delta, float(z))
        images.append(np.abs(propagated) ** 2)

    aperture_radius_m = beam_waist_m
    eta_far = estimate_aperture_transmittance(images[-1], delta, aperture_radius_m)

    return distances_m, images, eta_far, r0_target


def propagate_all_slices(
    all_slices,
    wavelength_m,
    beam_waist_m,
    grid_size=GRID_SIZE_DEFAULT,
    base_seed=42,
    aperture_radius_m=None,
):
    """Full split-step propagation, returning a snapshot after every slice.

    This powers the "Beam Evolution" filmstrip viewer: one intensity image
    per slice, showing progressive cumulative degradation.

    Grid sizing and propagation distances are chosen to match the hover
    popup's approach so the two views are visually consistent:
      - Grid is sized from beam_waist_m and r0 (not the last slice's
        beam_diameter_m, which can be orders of magnitude larger than the
        beam waist at TX and would make the beam a tiny dot).
      - Each slice is propagated over REFERENCE_LENGTH_M (100 m) rather
        than the actual slice length (which can be thousands of metres and
        causes numerical artefacts with the angular spectrum at this grid
        resolution). This is the same reference length used to compute
        the popup's r0 from Cn2.

    Returns a list of dicts, one per slice:
        {
            "slice_id":   int,
            "slice_idx":  int,
            "intensity":  2D ndarray,
            "r0":         float  (Fried parameter used for this slice's screen),
            "cn2":        float,
            "distance_m": float  (cumulative distance from TX — real geometry),
            "eta":        float  (aperture transmittance),
            "delta":      float  (metres/pixel),
        }
    """
    beam_waist_m = max(float(beam_waist_m), MIN_BEAM_WAIST_M)
    if aperture_radius_m is None:
        aperture_radius_m = beam_waist_m

    # Compute a representative r0 from the median Cn2 to size the grid.
    cn2_values = [s.Cn2 for s in all_slices if s.Cn2 > 0]
    if cn2_values:
        median_cn2 = sorted(cn2_values)[len(cn2_values) // 2]
        r0_ref = compute_reference_r0(median_cn2, wavelength_m)
    else:
        r0_ref = MIN_FRIED_PARAMETER_M
    r0_ref = max(r0_ref, MIN_FRIED_PARAMETER_M)

    # Grid sized so the beam fills most of the panel — same logic as the
    # hover popup's generate_slice_phase_screen().
    beam_diam = max(4.0 * beam_waist_m, 4.0 * r0_ref, 4.0 * MIN_BEAM_WAIST_M)
    delta = beam_diam / grid_size

    # Start with a clean Gaussian field
    x = (np.arange(grid_size) - grid_size // 2) * delta
    X, Y = np.meshgrid(x, x)
    field = np.exp(-(X ** 2 + Y ** 2) / beam_waist_m ** 2).astype(np.complex128)

    results = []
    cumulative_distance = 0.0

    for idx, s in enumerate(all_slices):
        # Track real cumulative geometry for labels
        cumulative_distance += max(float(s.length_m), 1.0)

        # Compute r0 for this slice (same as hover popup)
        if s.Cn2 > 0:
            r0_i = compute_reference_r0(s.Cn2, wavelength_m)
        else:
            r0_i = float(s.fried_parameter_m)
        r0_i = max(r0_i, MIN_FRIED_PARAMETER_M)

        # Generate and apply phase screen
        screen = ft_sh_phase_screen(
            r0=r0_i,
            N=grid_size,
            delta=delta,
            L0=DEFAULT_OUTER_SCALE_M,
            l0=DEFAULT_INNER_SCALE_M,
            seed=base_seed + int(s.slice_id),
        )
        field = field * np.exp(1j * screen)

        # Propagate a fixed reference distance (matching the hover popup's
        # r0-from-Cn2 reference length) for numerical stability.
        field = angularSpectrum(
            field, wavelength_m, delta, delta, REFERENCE_LENGTH_M
        )

        # Record snapshot
        intensity = np.abs(field) ** 2
        eta = estimate_aperture_transmittance(intensity, delta, aperture_radius_m)

        results.append({
            "slice_id": int(s.slice_id),
            "slice_idx": idx,
            "intensity": intensity,
            "r0": r0_i,
            "cn2": float(s.Cn2),
            "distance_m": cumulative_distance,
            "eta": eta,
            "delta": delta,
        })

    return results

