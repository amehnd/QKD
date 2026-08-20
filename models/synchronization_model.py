"""
synchronization_model.py
Version: 0.3
"""

import math
from core.model import Model


class SynchronizationModel(Model):

    name = "Synchronization"

    def execute(self, state):

        jitter = getattr(state, "beam_jitter_rms_urad", 0.0)
        frame_rate = getattr(state, "camera_frame_rate_Hz", 100.0)

        # --------------------------------------
        # Synchronization error
        # --------------------------------------

        sync_error = jitter / max(frame_rate, 1.0)

        # --------------------------------------
        # Clock offset
        # --------------------------------------

        clock_offset_ns = sync_error * 10.0

        # --------------------------------------
        # Timing jitter
        # --------------------------------------

        timing_jitter_ps = sync_error * 1000.0

        # --------------------------------------
        # Gate efficiency
        # --------------------------------------

        gate_efficiency = math.exp(-sync_error)

        # --------------------------------------
        # Synchronization loss
        # --------------------------------------

        sync_loss_dB = -10.0 * math.log10(max(gate_efficiency, 1e-12))

        # --------------------------------------
        # Synchronization QBER
        # --------------------------------------

        synchronization_qber = min(sync_error * 0.01, 0.02)

        # --------------------------------------
        # Save results
        # --------------------------------------

        state.synchronization_error = sync_error
        state.clock_offset_ns = clock_offset_ns
        state.timing_jitter_ps = timing_jitter_ps
        state.gate_efficiency = gate_efficiency
        state.sync_loss_dB = sync_loss_dB
        state.synchronization_qber = synchronization_qber
        state.sync_qber = synchronization_qber
        state.sync_penalty_factor = gate_efficiency
        # ======================================
        # v0.4 Propagation Slice Synchronization
        # ======================================

        if state.propagation_slices:

            cumulative_error = 0.0

            for s in state.propagation_slices:

                local_jitter = getattr(s, "beam_jitter_rms_urad", jitter)

                local_sync_error = local_jitter / max(frame_rate, 1.0)

                cumulative_error += local_sync_error

                local_clock_offset = cumulative_error * 10.0

                local_timing_jitter = cumulative_error * 1000.0

                local_gate = math.exp(-cumulative_error)

                local_loss = -10.0 * math.log10(max(local_gate, 1e-12))
                local_qber = min(cumulative_error * 0.01, 0.02)

                s.synchronization_error = cumulative_error

                s.clock_offset_ns = local_clock_offset

                s.timing_jitter_ps = local_timing_jitter

                s.gate_efficiency = local_gate

                s.sync_loss_dB = local_loss

                s.sync_qber = local_qber

                s.sync_penalty_factor = local_gate

                s.notes = f"Sync={local_qber:.4f}"

            rx = state.propagation_slices[-1]

            state.synchronization_error = rx.synchronization_error

            state.clock_offset_ns = rx.clock_offset_ns

            state.timing_jitter_ps = rx.timing_jitter_ps

            state.gate_efficiency = rx.gate_efficiency

            state.sync_loss_dB = rx.sync_loss_dB

            state.sync_qber = rx.sync_qber

            state.sync_penalty_factor = rx.sync_penalty_factor

            print()
            print("===== SYNCHRONIZATION → SLICES =====")

            for s in state.propagation_slices[:5]:

                print(
                    f"Slice {s.slice_id}: "
                    f"Gate={s.gate_efficiency:.4f} "
                    f"SyncQBER={s.sync_qber:.6f}"
                )

        print("==============================")
        print()
        print("SYNCHRONIZATION")
        print("----------------")
        print(f"Clock Offset : {state.clock_offset_ns:.3f} ns")
        print(f"Timing Jitter : {state.timing_jitter_ps:.3f} ps")
        print(f"Gate Efficiency : {state.gate_efficiency:.6f}")
        print(f"Sync Loss : {state.sync_loss_dB:.3f} dB")
        print(f"Sync QBER : {state.sync_qber:.6f}")
        state.debug_message = "Synchronization completed"
