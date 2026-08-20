"""
model_registry.py

Stores and manages all simulation models.

Version:
    v0.3 (extended stable registry)
"""

from typing import List

print("SORT FUNCTION CALLED")


class ModelRegistry:

    def __init__(self):

        self._models = []

    # ==================================================
    # Register Model
    # ==================================================

    def register(self, model):
        """
        Add a model to registry.
        """

        if self.get_model(model.name) is None:

            self._models.append(model)

        else:

            print(f"{model.name} already registered")

    # ==================================================
    # Get All Models
    # ==================================================

    def get_models(self) -> List:
        """
        Return all registered models.
        """

        return self._models

    # ==================================================
    # Find Model By Name
    # ==================================================

    def get_model(self, name):
        """
        Find model by name.
        """

        for model in self._models:

            if model.name == name:
                return model

        return None

    # ==================================================
    # Remove Model
    # ==================================================

    def remove_model(self, name):
        """
        Remove model by name.
        """

        self._models = [model for model in self._models if model.name != name]

    # ==================================================
    # Clear Registry
    # ==================================================

    def clear(self):
        """
        Remove all models.
        """

        self._models.clear()

    # ==================================================
    # Count
    # ==================================================

    def count(self):
        """
        Number of registered models.
        """

        return len(self._models)

    # ==================================================
    # List Model Names
    # ==================================================

    def list_model_names(self):
        """
        Return model names.
        """

        return [model.name for model in self._models]

    # ==================================================
    # EXECUTION ORDER CONTROL (NEW - IMPORTANT)
    # ==================================================

    def sort_by_priority(self):
        """
        Ensures correct physics pipeline order.

        This fixes:
        - zero outputs
        - missing dependencies
        """

        priority_map = {
            # ==================================================
            # Environment & Geometry
            # ==================================================
            "SolarEnvironment": 1,
            "Adaptive Slicing": 2,
            "Weather": 3,
            "LandSeaClassifier": 4,
            "Geometry": 5,
            "Terrain Database": 6,
            "Terrain Profile": 7,
            # ==================================================
            # Marine Environment
            # ==================================================
            "MOST": 8,
            "MarineBoundaryLayer": 9,
            "EvaporationDuct": 10,
            "Refractivity": 11,
            "ChromaticRefraction": 12,
            # ==================================================
            # Atmospheric Effects
            # ==================================================
            "AtmosphericLoss": 13,
            "SkyRadiance": 14,
            "BackgroundRadiance": 15,
            # ==================================================
            # Platform Motion & Turbulence
            # ==================================================
            "ShipMotion": 16,
            "Turbulence": 17,
            "BeamPropagation": 18,
            # ==================================================
            # Tracking
            # ==================================================
            "Gimbal": 19,
            "FSM": 20,
            "PAT": 21,
            "Tracking": 22,
            "PointingLoss": 23,
            # ==================================================
            # Quantum Channel
            # ==================================================
            "Synchronization": 24,
            "Polarization": 25,
            "LinkBudget": 26,
            "Detector": 27,
            # ==================================================
            # QKD Protocols
            # ==================================================
            "BB84": 28,
            "DecoyBB84": 28,
            "B92": 28,
            "E91": 28,
            "BBM92": 28,
            "SKR": 29,
            # ==================================================
            # Analysis
            # ==================================================
            "TradeStudy": 30,
            "MonteCarloEngine": 31,
            "DesignOptimizer": 32,
        }

        print("\nBEFORE SORT")
        for m in self._models:
            print(m.name)
        for m in self._models:
            print(m.name, "priority =", priority_map.get(m.name, 999))

        self._models.sort(key=lambda m: priority_map.get(m.name, 999))

        print("\nAFTER SORT\n")

        for m in self._models:
            print(m.name)
        print("\nAFTER SORT")
        for m in self._models:
            print(m.name)

    # ==================================================
    # DEBUG PRINT
    # ==================================================

    def print_models(self):
        """
        Print registered models.
        """

        print()
        print("Registered Models")
        print("------------------")

        for i, model in enumerate(self._models):

            print(f"{i+1}. {model.name}")

        print()

    # ==================================================
    # STRING
    # ==================================================

    def __str__(self):

        return f"ModelRegistry ({self.count()} models)"
