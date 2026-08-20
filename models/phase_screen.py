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
