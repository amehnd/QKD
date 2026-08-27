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

def _slice_r0(s, wavelength_m):
    """Fried parameter (m) for one slice, same rule used everywhere else
    in this module: Cn2-derived if available, else the app's own value."""
    if s.Cn2 > 0:
        r0 = compute_reference_r0(s.Cn2, wavelength_m)
    else:
        r0 = float(s.fried_parameter_m)
    return max(r0, MIN_FRIED_PARAMETER_M)


def compute_shared_grid_delta(all_slices, wavelength_m, grid_size=GRID_SIZE_DEFAULT):
    """Grid spacing (metres/pixel), identical for every slice in the walk.

    propagate_cumulative() previously derived `delta` from whichever slice
    was the *current hover target*, so the same slice's phase screen (same
    seed, same r0) could come out at a different physical scale depending
    on which slice the user was hovering -- breaking the Near(N) == Far(N-1)
    identity the split-step continuity depends on. Sizing the grid to fit
    the largest beam/r0 combination across ALL slices up front makes delta
    target-independent, so a given slice's screen is pixel-identical no
    matter which target_slice_idx it was generated under.
    """
    max_beam_diam = 4.0 * MIN_BEAM_WAIST_M
    for s in all_slices:
        r0 = _slice_r0(s, wavelength_m)
        beam_diam = max(float(s.beam_diameter_m), 4.0 * r0, 4.0 * MIN_BEAM_WAIST_M)
        max_beam_diam = max(max_beam_diam, beam_diam)
    return max_beam_diam / grid_size


def propagate_cumulative(
    all_slices,
    target_slice_idx,
    wavelength_m,
    beam_waist_m,
    total_link_m=None,
    grid_size=GRID_SIZE_DEFAULT,
    base_seed=0,
    launch_beam_waist_m=None,
):
    """Split-step beam propagation through slices 0 … target_slice_idx.

    Unlike generate_slice_phase_screen() + render_near_mid_far(), which
    start from a fresh Gaussian every time, this function carries the
    complex electric field forward through every preceding slice so the
    result at slice N includes the accumulated distortions of slices
    0 … N-1.

    Near/Mid/Far are real per-slice checkpoints, not fixed offsets, so
    adjacent slices' popups connect:
      - Near(N)  = field entering slice N, i.e. exactly Far(N-1) (or the
                   fresh TX Gaussian for slice 0). Not recomputed — it is
                   literally the same array produced while walking slice
                   N-1's own Far checkpoint.
      - Mid(N)   = after applying slice N's own phase screen, propagate
                   HALF of slice N's length_m.
      - Far(N)   = after applying slice N's own phase screen, propagate
                   the FULL slice N's length_m.

    distances_m is the true absolute cumulative distance from TX for each
    checkpoint (sum of prior slices' lengths, plus half/full of the
    current slice's length) -- not the fixed-offset numbers used by the
    independent pathway.

    Two different beam sizes are involved, and they must NOT be the same
    value:

      * launch_beam_waist_m: the width the split-step field starts at,
        BEFORE slice 0's screen is applied. This has to be the same value
        no matter which target_slice_idx is requested -- otherwise the
        Near(N) == Far(N-1) identity above is only true *within* one call,
        not across separate hovers, because "Far(N-1)" computed while
        hovering slice N-1 and the "slices 0..N-2" reconstructed while
        hovering slice N would be seeded with two different starting
        widths (whichever slice happened to be hovered) and so would not
        actually be the same array. If the caller doesn't pass one, this
        falls back to all_slices[0]'s own beam radius -- not physically
        exact (it's the size a little past true z=0, not at the TX
        aperture itself), but it is at minimum the SAME value on every
        call, which is what the continuity guarantee depends on.

      * beam_waist_m: the LOCAL size at the target slice, used only to
        size the receiving aperture for estimate_aperture_transmittance()
        at the end -- this legitimately does vary slice to slice (a
        downstream slice's own expected local spot size), unlike the
        launch size above.

    Returns (distances_m, images, eta_far, r0_target) — same shape as
    the independent pathway so the popup can display them identically.
    """
    beam_waist_m = max(float(beam_waist_m), MIN_BEAM_WAIST_M)

    if launch_beam_waist_m is None or launch_beam_waist_m <= 0:
        launch_beam_waist_m = float(getattr(all_slices[0], "beam_radius_m", 0.0))
    launch_beam_waist_m = max(launch_beam_waist_m, MIN_BEAM_WAIST_M)

    target = all_slices[target_slice_idx]
    r0_target = _slice_r0(target, wavelength_m)

    # Shared across every slice/target so a slice's screen (same seed) is
    # pixel-identical regardless of which slice is being hovered.
    delta = compute_shared_grid_delta(all_slices, wavelength_m, grid_size)

    # Build a Gaussian field on this grid -- the fresh TX beam. Uses the
    # fixed launch size, not the target slice's own (distance-dependent)
    # beam_waist_m -- see docstring above.
    x = (np.arange(grid_size) - grid_size // 2) * delta
    X, Y = np.meshgrid(x, x)
    field = np.exp(-(X ** 2 + Y ** 2) / launch_beam_waist_m ** 2).astype(np.complex128)

    # Walk through slices 0 … target_slice_idx - 1 to build the field
    # entering the target slice. This is the SAME computation slice N-1
    # performs to produce its own Far checkpoint, so the result here is
    # bit-identical to Far(N-1) (given the same launch_beam_waist_m and
    # base_seed on every call -- see docstring above).
    near_distance_m = 0.0
    for i in range(target_slice_idx):
        s = all_slices[i]
        r0_i = _slice_r0(s, wavelength_m)

        screen = ft_sh_phase_screen(
            r0=r0_i,
            N=grid_size,
            delta=delta,
            L0=DEFAULT_OUTER_SCALE_M,
            l0=DEFAULT_INNER_SCALE_M,
            seed=base_seed + int(s.slice_id),
        )
        field = field * np.exp(1j * screen)

        slice_length = max(float(s.length_m), 1.0)
        field = angularSpectrum(field, wavelength_m, delta, delta, slice_length)
        near_distance_m += slice_length

    near_field = field

    # Apply the target slice's own phase screen, then branch to Mid/Far.
    screen = ft_sh_phase_screen(
        r0=r0_target,
        N=grid_size,
        delta=delta,
        L0=DEFAULT_OUTER_SCALE_M,
        l0=DEFAULT_INNER_SCALE_M,
        seed=base_seed + int(target.slice_id),
    )
    field_after_screen = near_field * np.exp(1j * screen)

    target_length = max(float(target.length_m), 1.0)
    half_length = target_length / 2.0

    mid_field = angularSpectrum(field_after_screen, wavelength_m, delta, delta, half_length)
    far_field = angularSpectrum(field_after_screen, wavelength_m, delta, delta, target_length)

    distances_m = (
        near_distance_m,
        near_distance_m + half_length,
        near_distance_m + target_length,
    )
    images = [
        np.abs(near_field) ** 2,
        np.abs(mid_field) ** 2,
        np.abs(far_field) ** 2,
    ]

    aperture_radius_m = beam_waist_m
    eta_far = estimate_aperture_transmittance(images[-1], delta, aperture_radius_m)

    return distances_m, images, eta_far, r0_target


def propagate_all_slices(
    all_slices,
    wavelength_m,
    beam_waist_m,
    total_link_m,
    grid_size=GRID_SIZE_DEFAULT,
    base_seed=0,
):
    """Full split-step propagation, returning a snapshot after every slice.

    This powers the "Beam Evolution" filmstrip viewer: one intensity image
    per slice, showing progressive cumulative degradation.

    To ensure the filmstrip looks EXACTLY like the "CUMULATIVE" row in the
    hover popup, this simply calls propagate_cumulative() for each slice and
    returns the 'Near' distance image.

    Returns a list of dicts, one per slice:
        {
            "slice_id":   int,
            "slice_idx":  int,
            "intensity":  2D ndarray,
            "r0":         float  (Fried parameter used for this slice's screen),
            "cn2":        float,
            "distance_m": float  (cumulative distance from TX — real geometry),
            "eta":        float  (aperture transmittance),
            "delta":      float  (metres/pixel, though unused in the viewer directly),
        }
    """
    results = []

    # Fixed launch size for the WHOLE filmstrip -- every frame is meant to
    # be the same beam further along, not a fresh restart at each slice's
    # own already-grown local radius. See propagate_cumulative()'s
    # docstring for why this must stay constant across the loop.
    launch_bw = float(getattr(all_slices[0], "beam_radius_m", 0.0))
    if launch_bw <= 0:
        launch_bw = beam_waist_m

    for idx, s in enumerate(all_slices):
        # Local (target-slice) size -- used only for the receiving-aperture
        # sizing in propagate_cumulative(), not for seeding the field.
        bw = s.beam_radius_m
        if bw <= 0:
            bw = max(s.beam_diameter_m / 2.0, 0.02)
        if bw <= 0:
            bw = beam_waist_m

        distances_m, images, eta_far, r0_target = propagate_cumulative(
            all_slices,
            idx,
            wavelength_m,
            bw,
            total_link_m=total_link_m,
            grid_size=grid_size,
            base_seed=base_seed,
            launch_beam_waist_m=launch_bw,
        )

        results.append({
            "slice_id": int(s.slice_id),
            "slice_idx": idx,
            "intensity": images[0],  # Use the 'Near' image to match popup
            "r0": r0_target,
            "cn2": float(s.Cn2),
            "distance_m": distances_m[0],  # real Near distance, matches intensity image
            "eta": eta_far,
            "delta": 0.0,  # not strictly needed by the viewer anymore
        })

    return results