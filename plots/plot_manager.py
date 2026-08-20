"""
plot_manager.py
v0.3
"""

from plots.mpl_canvas import MplCanvas


class PlotManager:

    def __init__(self, canvas: MplCanvas):
        self.canvas = canvas

    def plot_skr_vs_param(self, x, skr):

        self.canvas.plot(
            x,
            skr,
            title="Secure Key Rate vs Parameter",
            xlabel="Parameter",
            ylabel="SKR (bps)",
        )

    def plot_qber(self, x, qber):

        self.canvas.plot(
            x, qber, title="QBER Variation", xlabel="Parameter", ylabel="QBER (%)"
        )

    def plot_efficiency(self, x, eff):

        self.canvas.plot(
            x, eff, title="Channel Efficiency", xlabel="Parameter", ylabel="Efficiency"
        )
