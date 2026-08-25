"""
cumulative_phase_screen.py
==========================

Cumulative (split-step) atmospheric phase-screen beam propagation.

Whereas the existing models/phase_screen.py treats every slice independently
(fresh Gaussian beam each time), this script propagates a SINGLE beam through
N consecutive slices, accumulating distortions slice by slice — the physically
correct "split-step" approach.

Output:  A matplotlib figure with two rows:
  Row 1 — CUMULATIVE:   beam cross-section after passing through 1, 2, … N slices
  Row 2 — INDEPENDENT:  same slices, but each starts from a clean Gaussian beam

This lets you visually compare cumulative degradation vs. the per-slice
diagnostic the existing app shows.

Usage:
    python cumulative_phase_screen.py                      # default scenario
    python cumulative_phase_screen.py --num_slices 8       # more slices
    python cumulative_phase_screen.py --cn2 5e-14          # stronger turbulence
    python cumulative_phase_screen.py --preset strong      # preset scenario

Dependencies: numpy, aotools, matplotlib  (already in requirements.txt)
"""

import argparse
import sys
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from aotools.turbulence import ft_sh_phase_screen
from aotools.opticalpropagation import angularSpectrum


# ── Defaults ───────────────────────────────────────────────────────────────
DEFAULT_WAVELENGTH_NM   = 1550        # telecom C-band
DEFAULT_BEAM_WAIST_M    = 0.05        # 5 cm beam waist at TX
DEFAULT_LINK_DISTANCE_M = 2000        # 2 km total link
DEFAULT_NUM_SLICES      = 6
DEFAULT_CN2             = 1e-14       # moderate maritime Cn2  (m^-2/3)
DEFAULT_GRID_SIZE       = 256
DEFAULT_OUTER_SCALE_M   = 50.0        # Kolmogorov outer scale L0
DEFAULT_INNER_SCALE_M   = 0.005       # Kolmogorov inner scale l0
DEFAULT_RX_APERTURE_M   = 0.10        # 10 cm receiver aperture radius

# Presets for quick demos
PRESETS = {
    "weak": {
        "cn2": 1e-16,
        "num_slices": 6,
        "link_distance_m": 1000,
        "description": "Weak turbulence — clear night, calm air",
    },
    "moderate": {
        "cn2": 1e-14,
        "num_slices": 6,
        "link_distance_m": 2000,
        "description": "Moderate turbulence — typical maritime daytime",
    },
    "strong": {
        "cn2": 5e-13,
        "num_slices": 8,
        "link_distance_m": 3000,
        "description": "Strong turbulence — hot sea surface, high wind",
    },
}


# ── Core physics functions ─────────────────────────────────────────────────

def compute_r0(cn2: float, wavelength_m: float, path_length_m: float) -> float:
    """Fried parameter r0 (m) from Cn2 over a given path length.

    r0 = (0.423 · k² · Cn2 · L)^(-3/5)
    """
    cn2 = max(cn2, 1e-20)
    k = 2.0 * np.pi / wavelength_m
    base = max(0.423 * k**2 * cn2 * path_length_m, 1e-20)
    return base ** (-3.0 / 5.0)


def make_gaussian_field(N: int, delta: float, beam_waist_m: float) -> np.ndarray:
    """Create a 2D Gaussian electric-field amplitude on an NxN grid."""
    x = (np.arange(N) - N // 2) * delta
    X, Y = np.meshgrid(x, x)
    amplitude = np.exp(-(X**2 + Y**2) / beam_waist_m**2)
    return amplitude.astype(np.complex128)


def generate_phase_screen(r0, grid_size, delta, L0, l0, seed=None):
    """Generate a single Kolmogorov phase screen (FFT + subharmonics)."""
    return ft_sh_phase_screen(
        r0=r0,
        N=grid_size,
        delta=delta,
        L0=L0,
        l0=l0,
        seed=seed,
    )


def propagate_angular_spectrum(field, wavelength_m, delta, distance_m):
    """Free-space propagation using the Angular Spectrum Method."""
    return angularSpectrum(field, wavelength_m, delta, delta, float(distance_m))


def aperture_transmittance(intensity, delta, aperture_radius_m):
    """Fraction of power inside a circular aperture centred on the grid."""
    N = intensity.shape[0]
    x = (np.arange(N) - N // 2) * delta
    X, Y = np.meshgrid(x, x)
    r2 = X**2 + Y**2
    total = intensity.sum()
    if total <= 0:
        return 0.0
    inside = intensity[r2 <= aperture_radius_m**2].sum()
    return float(inside / total)


# ── Cn2 profile generators ────────────────────────────────────────────────

def uniform_cn2_profile(num_slices, cn2):
    """All slices share the same Cn2 — simplest case."""
    return [cn2] * num_slices


def maritime_cn2_profile(num_slices, cn2_base):
    """Realistic-ish maritime profile: strongest near the sea surface
    (first and last slices, where the beam is near the water), weakest
    at the midpoint (highest beam altitude above the surface).

    Uses a parabolic shape:  Cn2(i) = cn2_base * (1 + 4·(x - 0.5)²)
    where x goes from 0 → 1 across the slices.
    """
    profile = []
    for i in range(num_slices):
        x = i / max(num_slices - 1, 1)           # 0 → 1
        scale = 1.0 + 4.0 * (x - 0.5) ** 2       # parabola: 2 at edges, 1 at centre
        profile.append(cn2_base * scale)
    return profile


# ── Simulation runners ─────────────────────────────────────────────────────

def run_cumulative(
    cn2_profile,
    wavelength_m,
    beam_waist_m,
    slice_length_m,
    grid_size,
    delta,
    L0,
    l0,
    base_seed=42,
):
    """Split-step propagation through N consecutive phase screens.

    Returns:
        snapshots : list of 2D intensity arrays (one after each slice)
        r0_list   : Fried parameter used for each slice
        eta_list  : aperture transmittance after each slice
    """
    num_slices = len(cn2_profile)
    field = make_gaussian_field(grid_size, delta, beam_waist_m)

    snapshots = []
    r0_list = []
    eta_list = []

    for i, cn2 in enumerate(cn2_profile):
        r0 = compute_r0(cn2, wavelength_m, slice_length_m)
        r0_list.append(r0)

        # 1. Apply this slice's phase screen to the current field
        screen = generate_phase_screen(r0, grid_size, delta, L0, l0, seed=base_seed + i)
        field = field * np.exp(1j * screen)

        # 2. Free-space propagate to the next slice
        field = propagate_angular_spectrum(field, wavelength_m, delta, slice_length_m)

        # 3. Record intensity snapshot
        intensity = np.abs(field) ** 2
        snapshots.append(intensity)
        eta_list.append(aperture_transmittance(intensity, delta, DEFAULT_RX_APERTURE_M))

    return snapshots, r0_list, eta_list


def run_independent(
    cn2_profile,
    wavelength_m,
    beam_waist_m,
    slice_length_m,
    grid_size,
    delta,
    L0,
    l0,
    base_seed=42,
):
    """Independent per-slice simulation (same approach as the existing app).

    Each slice starts from a FRESH Gaussian beam, so there is no cumulative
    degradation.  This is the existing repo's diagnostic mode.

    Returns:
        snapshots : list of 2D intensity arrays
        r0_list   : Fried parameter for each slice
        eta_list  : aperture transmittance for each slice
    """
    num_slices = len(cn2_profile)
    snapshots = []
    r0_list = []
    eta_list = []

    for i, cn2 in enumerate(cn2_profile):
        r0 = compute_r0(cn2, wavelength_m, slice_length_m)
        r0_list.append(r0)

        # Fresh Gaussian for every slice
        field = make_gaussian_field(grid_size, delta, beam_waist_m)

        # Apply screen
        screen = generate_phase_screen(r0, grid_size, delta, L0, l0, seed=base_seed + i)
        field = field * np.exp(1j * screen)

        # Propagate the same distance
        field = propagate_angular_spectrum(field, wavelength_m, delta, slice_length_m)

        intensity = np.abs(field) ** 2
        snapshots.append(intensity)
        eta_list.append(aperture_transmittance(intensity, delta, DEFAULT_RX_APERTURE_M))

    return snapshots, r0_list, eta_list


# ── Visualisation ──────────────────────────────────────────────────────────

def plot_comparison(
    cum_snaps, cum_r0, cum_eta,
    ind_snaps, ind_r0, ind_eta,
    cn2_profile, slice_length_m, wavelength_nm, total_link_m,
    profile_name,
):
    """Side-by-side figure: cumulative (top) vs independent (bottom)."""
    n = len(cum_snaps)

    fig = plt.figure(figsize=(3.2 * n + 1.5, 9.5), facecolor="#0d1117")
    fig.patch.set_facecolor("#0d1117")

    gs = GridSpec(
        3, n + 1,
        figure=fig,
        height_ratios=[4, 4, 1.8],
        width_ratios=[1] * n + [0.08],
        hspace=0.35,
        wspace=0.25,
    )

    # ── Title ──────────────────────────────────────────────────────────
    title = (
        f"Cumulative vs Independent Phase-Screen Propagation\n"
        f"λ = {wavelength_nm} nm   |   Link = {total_link_m:.0f} m   |   "
        f"{n} slices × {slice_length_m:.0f} m   |   Cn² profile: {profile_name}"
    )
    fig.suptitle(title, color="white", fontsize=13, fontweight="bold", y=0.97)

    vmin_cum = min(s.min() for s in cum_snaps)
    vmax_cum = max(s.max() for s in cum_snaps)
    vmin_ind = min(s.min() for s in ind_snaps)
    vmax_ind = max(s.max() for s in ind_snaps)

    im_cum = None
    im_ind = None

    for i in range(n):
        dist_m = (i + 1) * slice_length_m

        # ── Row 1: Cumulative ──────────────────────────────────────────
        ax1 = fig.add_subplot(gs[0, i])
        im_cum = ax1.imshow(
            cum_snaps[i], cmap="inferno", origin="lower",
            vmin=vmin_cum, vmax=vmax_cum,
        )
        ax1.set_title(
            f"Slice {i+1}\n@ {dist_m:.0f} m",
            color="white", fontsize=9, pad=6,
        )
        ax1.tick_params(colors="white", labelsize=6)
        ax1.set_xlabel(
            f"η = {cum_eta[i]:.3f}",
            color="#4fc3f7", fontsize=8,
        )
        if i == 0:
            ax1.set_ylabel("CUMULATIVE", color="#ff7043", fontsize=11, fontweight="bold")
        ax1.set_facecolor("#0d1117")
        for spine in ax1.spines.values():
            spine.set_color("#30363d")

        # ── Row 2: Independent ─────────────────────────────────────────
        ax2 = fig.add_subplot(gs[1, i])
        im_ind = ax2.imshow(
            ind_snaps[i], cmap="inferno", origin="lower",
            vmin=vmin_ind, vmax=vmax_ind,
        )
        ax2.set_title(
            f"r₀ = {ind_r0[i]*100:.1f} cm\nCn² = {cn2_profile[i]:.1e}",
            color="#aaa", fontsize=8, pad=6,
        )
        ax2.tick_params(colors="white", labelsize=6)
        ax2.set_xlabel(
            f"η = {ind_eta[i]:.3f}",
            color="#4fc3f7", fontsize=8,
        )
        if i == 0:
            ax2.set_ylabel("INDEPENDENT", color="#66bb6a", fontsize=11, fontweight="bold")
        ax2.set_facecolor("#0d1117")
        for spine in ax2.spines.values():
            spine.set_color("#30363d")

    # ── Colorbars ──────────────────────────────────────────────────────
    cax1 = fig.add_subplot(gs[0, n])
    cb1 = fig.colorbar(im_cum, cax=cax1)
    cb1.ax.tick_params(colors="white", labelsize=7)
    cb1.set_label("Intensity", color="white", fontsize=8)

    cax2 = fig.add_subplot(gs[1, n])
    cb2 = fig.colorbar(im_ind, cax=cax2)
    cb2.ax.tick_params(colors="white", labelsize=7)
    cb2.set_label("Intensity", color="white", fontsize=8)

    # ── Row 3: Eta comparison bar chart ────────────────────────────────
    ax_bar = fig.add_subplot(gs[2, :n])
    ax_bar.set_facecolor("#0d1117")
    x_pos = np.arange(n)
    width = 0.35

    bars_cum = ax_bar.bar(
        x_pos - width / 2, cum_eta, width,
        color="#ff7043", alpha=0.85, label="Cumulative η",
    )
    bars_ind = ax_bar.bar(
        x_pos + width / 2, ind_eta, width,
        color="#66bb6a", alpha=0.85, label="Independent η",
    )

    ax_bar.set_xlabel("Slice", color="white", fontsize=10)
    ax_bar.set_ylabel("Aperture Transmittance η", color="white", fontsize=10)
    ax_bar.set_xticks(x_pos)
    ax_bar.set_xticklabels([f"{i+1}" for i in range(n)], color="white")
    ax_bar.tick_params(colors="white", labelsize=8)
    ax_bar.legend(loc="upper right", fontsize=9, facecolor="#161b22", edgecolor="#30363d", labelcolor="white")
    ax_bar.set_ylim(0, 1.05)
    ax_bar.grid(axis="y", color="#30363d", linewidth=0.5, alpha=0.5)
    for spine in ax_bar.spines.values():
        spine.set_color("#30363d")

    # Add value labels on bars
    for bar in bars_cum:
        h = bar.get_height()
        ax_bar.text(
            bar.get_x() + bar.get_width() / 2, h + 0.02,
            f"{h:.2f}", ha="center", va="bottom", color="#ff7043", fontsize=7,
        )
    for bar in bars_ind:
        h = bar.get_height()
        ax_bar.text(
            bar.get_x() + bar.get_width() / 2, h + 0.02,
            f"{h:.2f}", ha="center", va="bottom", color="#66bb6a", fontsize=7,
        )

    plt.savefig("cumulative_vs_independent.png", dpi=150, bbox_inches="tight",
                facecolor="#0d1117", edgecolor="none")
    print(f"\n  Plot saved → cumulative_vs_independent.png")

    plt.show()


# ── CLI entry point ────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(
        description="Cumulative vs Independent Phase-Screen Beam Propagation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cumulative_phase_screen.py                          # moderate defaults
  python cumulative_phase_screen.py --preset strong          # strong turbulence
  python cumulative_phase_screen.py --cn2 1e-13 --num_slices 10
  python cumulative_phase_screen.py --profile maritime       # realistic Cn2 shape
        """,
    )
    p.add_argument("--preset", choices=list(PRESETS.keys()), default=None,
                   help="Use a predefined scenario (overrides --cn2 / --num_slices / --link_distance_m)")
    p.add_argument("--cn2", type=float, default=DEFAULT_CN2,
                   help=f"Base Cn² value in m^-2/3 (default: {DEFAULT_CN2})")
    p.add_argument("--num_slices", type=int, default=DEFAULT_NUM_SLICES,
                   help=f"Number of atmospheric slices (default: {DEFAULT_NUM_SLICES})")
    p.add_argument("--link_distance_m", type=float, default=DEFAULT_LINK_DISTANCE_M,
                   help=f"Total link distance in metres (default: {DEFAULT_LINK_DISTANCE_M})")
    p.add_argument("--wavelength_nm", type=float, default=DEFAULT_WAVELENGTH_NM,
                   help=f"Laser wavelength in nm (default: {DEFAULT_WAVELENGTH_NM})")
    p.add_argument("--beam_waist_m", type=float, default=DEFAULT_BEAM_WAIST_M,
                   help=f"TX beam waist in metres (default: {DEFAULT_BEAM_WAIST_M})")
    p.add_argument("--grid_size", type=int, default=DEFAULT_GRID_SIZE,
                   help=f"Phase screen grid size NxN (default: {DEFAULT_GRID_SIZE})")
    p.add_argument("--profile", choices=["uniform", "maritime"], default="maritime",
                   help="Cn² variation across slices (default: maritime)")
    p.add_argument("--seed", type=int, default=42,
                   help="Random seed for reproducibility (default: 42)")
    return p.parse_args()


def main():
    args = parse_args()

    # Apply preset if selected
    if args.preset:
        p = PRESETS[args.preset]
        args.cn2 = p["cn2"]
        args.num_slices = p["num_slices"]
        args.link_distance_m = p["link_distance_m"]
        print(f"\n  Preset: {args.preset} — {p['description']}")

    wavelength_m = args.wavelength_nm * 1e-9
    slice_length_m = args.link_distance_m / args.num_slices

    # Build Cn2 profile
    if args.profile == "maritime":
        cn2_profile = maritime_cn2_profile(args.num_slices, args.cn2)
        profile_name = "Maritime (parabolic)"
    else:
        cn2_profile = uniform_cn2_profile(args.num_slices, args.cn2)
        profile_name = "Uniform"

    # Grid spacing: fit ~4× beam diameter into the grid
    beam_diam = 2.0 * args.beam_waist_m
    delta = max(beam_diam * 4.0, 0.5) / args.grid_size

    # ── Print simulation parameters ────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  Cumulative vs Independent Phase-Screen Simulation")
    print(f"{'='*60}")
    print(f"  Wavelength       :  {args.wavelength_nm} nm")
    print(f"  Total link       :  {args.link_distance_m:.0f} m")
    print(f"  Slices           :  {args.num_slices}")
    print(f"  Slice length     :  {slice_length_m:.1f} m")
    print(f"  Beam waist (TX)  :  {args.beam_waist_m*100:.1f} cm")
    print(f"  Grid             :  {args.grid_size} × {args.grid_size}")
    print(f"  Grid spacing (δ) :  {delta*1e3:.2f} mm")
    print(f"  RX aperture      :  {DEFAULT_RX_APERTURE_M*100:.0f} cm radius")
    print(f"  Cn² profile      :  {profile_name}")
    print(f"  Cn² values       :  {['%.1e' % c for c in cn2_profile]}")
    print(f"{'='*60}")

    # ── Run both simulations ───────────────────────────────────────────
    print("\n  Running CUMULATIVE simulation (split-step)...")
    cum_snaps, cum_r0, cum_eta = run_cumulative(
        cn2_profile, wavelength_m, args.beam_waist_m,
        slice_length_m, args.grid_size, delta,
        DEFAULT_OUTER_SCALE_M, DEFAULT_INNER_SCALE_M,
        base_seed=args.seed,
    )

    print("  Running INDEPENDENT simulation (per-slice fresh beam)...")
    ind_snaps, ind_r0, ind_eta = run_independent(
        cn2_profile, wavelength_m, args.beam_waist_m,
        slice_length_m, args.grid_size, delta,
        DEFAULT_OUTER_SCALE_M, DEFAULT_INNER_SCALE_M,
        base_seed=args.seed,
    )

    # ── Print summary table ────────────────────────────────────────────
    print(f"\n  {'Slice':>5}  {'Cn²':>10}  {'r₀ (cm)':>8}  {'η cumul.':>9}  {'η indep.':>9}  {'Δη':>7}")
    print(f"  {'─'*5}  {'─'*10}  {'─'*8}  {'─'*9}  {'─'*9}  {'─'*7}")
    for i in range(args.num_slices):
        delta_eta = cum_eta[i] - ind_eta[i]
        print(
            f"  {i+1:>5}  {cn2_profile[i]:>10.1e}  {cum_r0[i]*100:>8.2f}  "
            f"{cum_eta[i]:>9.4f}  {ind_eta[i]:>9.4f}  {delta_eta:>+7.4f}"
        )
    print()

    # ── Plot ───────────────────────────────────────────────────────────
    plot_comparison(
        cum_snaps, cum_r0, cum_eta,
        ind_snaps, ind_r0, ind_eta,
        cn2_profile, slice_length_m, args.wavelength_nm, args.link_distance_m,
        profile_name,
    )


if __name__ == "__main__":
    main()
