"""
model.py

Base class for all simulation models.

Extended for v0.3:
- supports post-processing hooks
- supports reporting integration
- supports optional plotting hooks
- supports trade study / Monte Carlo compatibility
"""

from abc import ABC, abstractmethod


class Model(ABC):

    # --------------------------------------------------
    # Metadata
    # --------------------------------------------------

    name = "BaseModel"
    description = ""
    inputs = []
    outputs = []
    version = "0.1"
    priority = 999

    dependencies = []

    enabled = True

    # --------------------------------------------------
    # Constructor
    # --------------------------------------------------

    def __init__(self):
        pass

    # --------------------------------------------------
    # Core execution (REQUIRED)
    # --------------------------------------------------

    @abstractmethod
    def execute(self, state):
        """
        Run model simulation step.
        Must modify SimulationState directly.
        """
        pass

    # --------------------------------------------------
    # Validation (OPTIONAL)
    # --------------------------------------------------

    def validate(self, state):
        return True

    # --------------------------------------------------
    # Reset (OPTIONAL)
    # --------------------------------------------------

    def reset(self):
        pass

    # ==================================================
    # v0.3 EXTENSIONS (SAFE ADDITIONS)
    # ==================================================

    def post_execute(self, state):
        """
        Called after execute() by kernel (optional hook).

        Used for:
        - logging
        - derived outputs
        - reporting hooks
        """
        return

    def get_plot_data(self, state):
        """
        Optional plotting hook.

        Return structure:
            dict or None

        Used by:
        - plot_manager.py
        - mpl_canvas.py
        """
        return None

    def trade_study_step(self, state):
        """
        Optional trade study hook.

        Used when sweeping parameters.
        """
        pass

    def monte_carlo_step(self, state):
        """
        Optional Monte Carlo hook.
        """
        pass

    def report_data(self, state):
        """
        Returns structured output for report_generator.

        Default: basic model info
        """

        return {"model": self.name, "status": "OK"}

    def summary(self, state):

        return {"model": self.name, "status": "OK"}

    # --------------------------------------------------
    # String Representation
    # --------------------------------------------------

    def __str__(self):
        return f"{self.name} (v{self.version})"
