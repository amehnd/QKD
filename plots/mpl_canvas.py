"""
mpl_canvas.py
v0.3
"""

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from PySide6.QtWidgets import QSizePolicy


class MplCanvas(FigureCanvas):

    def __init__(self, parent=None):

        self.fig = Figure(dpi=100)

        self.ax = self.fig.add_subplot(111)

        super().__init__(self.fig)

        self.setParent(parent)

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.updateGeometry()

    def clear(self):

        self.fig.clear()

        self.ax = self.fig.add_subplot(111)

        self.draw()

    def plot(self, x, y, title="", xlabel="", ylabel=""):

        self.ax.clear()

        self.ax.plot(x, y, linewidth=2)

        self.ax.set_title(title)

        self.ax.set_xlabel(xlabel)

        self.ax.set_ylabel(ylabel)

        self.ax.grid(True, alpha=0.3)

        self.draw()
