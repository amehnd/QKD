"""
simulation_kernel.py

Main simulation engine.

Responsible for:
1. Executing all registered models
2. Managing simulation state
3. Error handling
4. Progress reporting
5. Producing final outputs

Version:
    0.3
"""

import time
import traceback
from core.model_registry import ModelRegistry

print("SIMULATION KERNEL LOADED")


class SimulationKernel:

    def __init__(self):

        self.registry = ModelRegistry()

        self.simulation_name = "Maritime QKD Simulator"

        self.version = "0.3"

        self.execution_log = []

    # ==================================================
    # MODEL REGISTRATION
    # ==================================================

    def register_model(self, model):
        self.registry.register(model)

    # ==================================================
    # MAIN RUN PIPELINE
    # ==================================================

    def run(self, state):

        start_time = time.time()
        self.execution_log.clear()

        state.simulation_status = "RUNNING"

        print("\n" + "=" * 60)
        print("SIMULATION STARTED")
        print("=" * 60)

        try:

            print("\nBEFORE SORT")
            for m in self.registry.get_models():
                print(m.name)

            self.registry.sort_by_priority()
            print("\nDEBUG PRIORITIES")
            for m in self.registry.get_models():
                print(repr(m.name))
            for m in self.registry.get_models():
                print(repr(m.name))

            print("\nAFTER SORT")
            for m in self.registry.get_models():
                print(m.name)
            print("\n===== MODEL EXECUTION ORDER =====")

            for model in self.registry.get_models():
                print(model.name)

            print("===============================\n")

            if not hasattr(state, "model_times"):

                state.model_times = {}

            for model in self.registry.get_models():

                self._execute_model(model, state)

            state.simulation_status = "COMPLETED"
            state.system_health = "GOOD"

            if hasattr(state, "los"):

                if state.los is False:

                    state.system_health = "BLOCKED"

                    state.link_available = False

                    state.link_blocked_reason = "Earth curvature / LOS"
                else:

                    state.link_available = True

        except Exception as e:

            state.simulation_status = "FAILED"
            state.debug_message = str(e)

            print("\nSIMULATION ERROR")
            traceback.print_exc()

            raise

        elapsed = time.time() - start_time
        state.simulation_time_sec = elapsed

        print("\n" + "=" * 60)
        print(f"SIMULATION FINISHED ({elapsed:.3f} sec)")
        print("=" * 60)

    # ==================================================
    # MODEL EXECUTION
    # ==================================================

    def _execute_model(self, model, state):

        print(f"\nExecuting: {model.name}")

        model_start = time.time()

        if hasattr(model, "validate"):
            if not model.validate(state):
                print(f"Skipping {model.name} (validation failed)")
                return
        model.execute(state)

        # Optional hook
        if hasattr(model, "post_execute"):

            model.post_execute(state)

        model_time = time.time() - model_start

        self.execution_log.append({"model": model.name, "runtime_sec": model_time})
        state.model_times[model.name] = model_time

        print(f"Completed: {model.name} ({model_time:.4f} sec)")

    # ==================================================
    # REPORTING
    # ==================================================

    def print_execution_report(self):

        print("\n" + "=" * 60)
        print("EXECUTION REPORT")
        print("=" * 60)

        for item in self.execution_log:
            print(f"{item['model']:25s} {item['runtime_sec']:.5f} sec")

        print()

    def print_registered_models(self):
        self.registry.print_models()

    def model_count(self):
        return self.registry.count()

    def clear_models(self):
        self.registry.clear()

    # ==================================================
    # OPTIONAL EXTENSIONS (NEW v0.3 SYSTEMS HOOKS)
    # ==================================================

    def attach_post_processors(self, state):
        """
        Optional hook for:
        - report_generator.py
        - project_io.py
        """
        try:
            # safe imports (only used if files exist)
            from core.report_generator import ReportGenerator

            report = ReportGenerator()
            report.generate(state)

        except Exception:
            pass

    def save_project(self, state, filename):
        try:
            from core.project_io import ProjectIO

            io = ProjectIO()
            io.save(state, filename)

        except Exception as e:
            print("Save failed:", e)

    def load_project(self, state, filename):
        try:
            from core.project_io import ProjectIO

            io = ProjectIO()
            io.load(state, filename)

        except Exception as e:
            print("Load failed:", e)

    # ==================================================
    # UTILITY
    # ==================================================

    def __str__(self):
        return f"{self.simulation_name} v{self.version}"
