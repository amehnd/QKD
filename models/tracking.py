"""
tracking.py (FIXED MODEL)

PAT / Tracking physics model
"""

from core.model import Model
import math


class TrackingModel(Model):

    name = "Tracking"
    version = "0.3"

    def validate(self, state):
        return True

    def execute(self, state):

        # =========================
        # INPUTS
        # =========================
        roll = getattr(state, "roll_rms_deg", 0.0)
        pitch = getattr(state, "pitch_rms_deg", 0.0)
        yaw = getattr(state, "yaw_rms_deg", 0.0)
        print("TRACKING RECEIVED")
        print("Roll =", roll)
        print("Pitch =", pitch)
        print("Yaw =", yaw)

        jitter = getattr(state, "beam_jitter_rms_urad", 0.0)
        beam_wander_urad = getattr(state, "beam_wander_urad", 0.0)

        # Hardware parameters
        gimbal_bw = getattr(state, "gimbal_bw_hz", 10.0)
        fsm_bw = getattr(state, "fsm_bw_hz", 200.0)
        control_loop_bw = getattr(state, "control_loop_bw_hz", 500.0)
        sampling_freq = getattr(state, "sampling_frequency_hz", 1000.0)
        encoder_res = getattr(state, "encoder_resolution_urad", 1.0)
        pointing_acc = getattr(state, "pointing_accuracy_urad", 2.0)
        servo_res_ms = getattr(state, "servo_response_ms", 2.0)
        acq_uncertainty = getattr(state, "acquisition_uncertainty_urad", 10.0)
        tracking_jitter_hw = getattr(state, "tracking_jitter_urad", 1.0)
        stab_perf = getattr(state, "stabilization_performance_pct", 98.0)

        # =========================
        # PLATFORM MOTION → urad
        # =========================
        motion_deg = (roll**2 + pitch**2 + yaw**2) ** 0.5
        motion_urad = motion_deg * math.pi / 180 * 1e6

        # =========================
        # PHYSICS DERIVATIONS
        # =========================
        
        # 1. Acquisition Error
        theta_acq_error = math.sqrt(acq_uncertainty**2 + encoder_res**2)
        
        # 2. Pointing Bias
        # Bias from steady-state pointing accuracy + servo lag
        theta_bias = math.sqrt(pointing_acc**2 + ((servo_res_ms / 1000.0) * 0.1 * motion_urad)**2)
        
        # 3. Base Jitter
        # Hardware tracking jitter + residual un-stabilized platform motion + beam wander + beam jitter
        theta_jitter = math.sqrt(tracking_jitter_hw**2 + ((1.0 - stab_perf / 100.0) * motion_urad)**2 + beam_wander_urad**2 + jitter**2)

        # 4. Control Loop Noise Bandwidth (sigma_bw)
        # Noise equivalent bandwidth contribution
        sigma_bw = theta_jitter * math.sqrt(control_loop_bw / max(sampling_freq, 1.0))

        # 5. Disturbance Rejection
        f_dist_gimbal = 1.0  # Hz
        f_dist_fsm = 10.0    # Hz

        # Standard control theory 1st order rejection
        R_gimbal = 1.0 / math.sqrt(1.0 + (f_dist_gimbal / max(gimbal_bw, 1e-6))**2)
        R_fsm = 1.0 / math.sqrt(1.0 + (f_dist_fsm / max(fsm_bw, 1e-6))**2)
        
        # 6. Residual Errors
        # Gimbal reduces the jitter
        gimbal_error = theta_jitter * (1.0 - R_gimbal)
        # FSM reduces the gimbal residual
        fsm_error = gimbal_error * (1.0 - R_fsm)
        
        # 7. Total Tracking Error
        # Combines FSM residual + Control Noise + Pointing Bias
        theta_total = math.sqrt(fsm_error**2 + sigma_bw**2 + theta_bias**2)
        tracking_error = max(theta_total, 1e-12)

        # =========================
        # STORE RESULTS (CORE)
        # =========================
        state.tracking_error_urad = tracking_error
        state.gimbal_tracking_error_urad = gimbal_error
        state.fsm_residual_error_urad = fsm_error
        state.acquisition_error_urad = theta_acq_error
        state.total_jitter_urad = theta_jitter

        state.ship_los_jitter_urad = motion_urad
        state.fsm_stroke_urad = 3.0 * abs(fsm_error)

        spot_radius = max(state.beam_radius_m, 1e-6)
        sigma = tracking_error * 1e-6
        eta_geo = math.exp(-2 * (sigma / spot_radius) ** 2)
        eta_geo = max(eta_geo, 1e-12)

        state.pointing_loss_dB = -10 * math.log10(eta_geo)

        # ========================
        # PROBABILITIES & EFFICIENCIES
        # =========================
        rx_fov_urad = getattr(state, "rx_fov_mrad", 1.0) * 1000.0
        tx_fov_urad = getattr(state, "tx_beam_divergence_mrad", 1.0) * 1000.0

        eta_gimbal = math.exp(- (gimbal_error / max(rx_fov_urad/2, 1e-6))**2 )
        eta_fsm = math.exp(- (fsm_error / max(tx_fov_urad/2, 1e-6))**2 )

        state.lock_probability = math.exp(- (tracking_error / max(rx_fov_urad/2, 1e-6))**2 )
        state.tracking_probability = state.lock_probability * eta_fsm
        state.acquisition_probability = math.exp(- (theta_acq_error / max(rx_fov_urad/2, 1e-6))**2 ) * eta_gimbal
        
        state.gimbal_tracking_efficiency = eta_gimbal
        state.fsm_tracking_efficiency = eta_fsm

        state.debug_message = "Tracking OK"

        # ==========================================
        # v0.4 Slice Tracking
        # ==========================================

        if state.propagation_slices:
            tracking_sum = 0.0
            path_pointing_transmission = 1.0

            for s in state.propagation_slices:
                local_jitter = math.sqrt(tracking_jitter_hw**2 + ((1.0 - stab_perf / 100.0) * motion_urad)**2 + getattr(s, "beam_wander_urad", 0.0)**2 + jitter**2)
                local_sigma_bw = local_jitter * math.sqrt(control_loop_bw / max(sampling_freq, 1.0))
                
                local_gimbal = local_jitter * (1.0 - R_gimbal)
                local_fsm = local_gimbal * (1.0 - R_fsm)
                
                local_total = math.sqrt(local_fsm**2 + local_sigma_bw**2 + theta_bias**2)
                local_tracking = max(local_total, 1e-12)
                
                local_sigma = local_tracking * 1e-6
                local_spot = max(getattr(s, "beam_radius_m", spot_radius), 1e-6)
                local_eta_geo = math.exp(-2.0 * (local_sigma / local_spot) ** 2)
                local_eta_geo = max(local_eta_geo, 1e-12)
                
                path_pointing_transmission *= local_eta_geo
                local_loss = -10.0 * math.log10(local_eta_geo)

                s.gimbal_tracking_error_urad = local_gimbal
                s.fsm_residual_error_urad = local_fsm
                s.tracking_error_urad = local_tracking
                
                s.pointing_loss_dB = 0.0
                s.pointing_efficiency = local_eta_geo
                
                s.lock_probability = math.exp(- (local_tracking / max(rx_fov_urad/2, 1e-6))**2 )
                s.gimbal_tracking_efficiency = math.exp(- (local_gimbal / max(rx_fov_urad/2, 1e-6))**2 )
                s.fsm_tracking_efficiency = math.exp(- (local_fsm / max(tx_fov_urad/2, 1e-6))**2 )
                s.tracking_probability = s.lock_probability * s.fsm_tracking_efficiency
                s.acquisition_probability = math.exp(- (theta_acq_error / max(rx_fov_urad/2, 1e-6))**2 ) * s.gimbal_tracking_efficiency

                s.notes = (f"Tracking={local_tracking:.2f} urad, Pointing={local_loss:.2f} dB")
                tracking_sum += local_tracking

            n = len(state.propagation_slices)
            tracking_error = tracking_sum / n
            state.capture_fraction = state.propagation_slices[-1].capture_fraction

        if hasattr(state, "sync_error_ps"):
            state.sync_tracking_penalty = tracking_error * 1e-3

        if hasattr(state, "polarization_error_rate"):
            state.total_tracking_degradation = state.pointing_loss_dB + (getattr(state, "polarization_error_rate", 0.0) * 10.0)

        # ==========================================
        # VERIFIER TEXT GENERATION
        # ==========================================
        if "track" not in state.verifier_text:
            state.verifier_text["track"] = ""
            
        state.verifier_text["track"] = f"""
**Acquisition Error (θ_acq_error)**
θ_acq_error = √(Uncertainty² + Encoder_Res²) = √({acq_uncertainty:.2f}² + {encoder_res:.2f}²) = {theta_acq_error:.2f} µrad

**Pointing Bias (θ_bias)**
θ_bias = √(Accuracy² + (Servo_lag · 0.1 · θ_motion)²) = √({pointing_acc:.2f}² + ({servo_res_ms/1000.0:.3f} · 0.1 · {motion_urad:.2f})²) = {theta_bias:.2f} µrad

**Base Jitter (θ_jitter)**
θ_jitter = √(HW_Jitter² + Unstabilized_Motion² + Wander² + Jitter²)
θ_jitter = √({tracking_jitter_hw:.2f}² + ({1.0 - stab_perf/100.0:.3f} · {motion_urad:.2f})² + {beam_wander_urad:.2f}² + {jitter:.2f}²) = {theta_jitter:.2f} µrad

**Control Loop Noise (sigma_bw)**
σ_bw = θ_jitter · √(BW_control / F_sampling) = {theta_jitter:.2f} · √({control_loop_bw:.1f} / {sampling_freq:.1f}) = {sigma_bw:.2f} µrad

**Gimbal Rejection (R_gimbal)**
R_gimbal = 1 / √(1 + (f_dist_gimbal / BW_gimbal)²) = 1 / √(1 + (1.0 / {gimbal_bw:.1f})²) = {R_gimbal:.4f}

**FSM Rejection (R_FSM)**
R_FSM = 1 / √(1 + (f_dist_FSM / BW_FSM)²) = 1 / √(1 + (10.0 / {fsm_bw:.1f})²) = {R_fsm:.4f}

**Total Tracking Error (θ_total)**
θ_gimbal = θ_jitter · (1 - R_gimbal) = {gimbal_error:.2f} µrad
θ_FSM = θ_gimbal · (1 - R_FSM) = {fsm_error:.2f} µrad
θ_total = √(θ_FSM² + σ_bw² + θ_bias²) = √({fsm_error:.2f}² + {sigma_bw:.2f}² + {theta_bias:.2f}²) = {tracking_error:.2f} µrad

**Geometric Efficiency (η_geo)**
η_geo = exp(-2 · (θ_total / r_beam)²) = exp(-2 · ({tracking_error*1e-6:.2e} / {spot_radius:.4f})²) = {eta_geo:.4e}

**Gimbal Efficiency (η_gimbal)**
η_gimbal = exp(-(θ_gimbal / (θ_RX_FOV/2))²) = {eta_gimbal:.4e}

**FSM Efficiency (η_FSM)**
η_FSM = exp(-(θ_FSM / (θ_TX_FOV/2))²) = {eta_fsm:.4e}
"""
