"""
report_generator.py

Simulation report builder

Version: 0.3
"""


class ReportGenerator:

    @staticmethod
    def generate(state) -> str:

        report = []

        report.append("=== QKD SIMULATION REPORT ===\n")

        report.append(f"Range: {state.link_distance_km} km")
        report.append(f"Channel Efficiency: {state.channel_efficiency:.6e}")
        report.append(f"Total Loss: {state.total_link_loss_dB:.2f} dB")
        report.append(f"Secure Key Rate: {state.secure_key_rate:.3e}")
        report.append(f"QBER: {state.qber:.4f}")

        report.append("\n=== TRACKING ===")
        report.append(f"Tracking Error: {state.tracking_error_urad:.3f} urad")
        report.append(f"Pointing Loss: {state.pointing_loss_dB:.2f} dB")

        report.append("\n=== DETECTOR ===")
        report.append(f"Signal Counts: {state.signal_count_rate:.3e}")
        report.append(f"Background Counts: {state.background_count_rate:.3e}")

        return "\n".join(report)
