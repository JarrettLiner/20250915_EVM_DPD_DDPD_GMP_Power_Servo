# ==============================================================
# File: main.py
# Description:
#   Main automation script for RF testing across a frequency sweep.
#   Performs:
#     - Instrument setup (VSG, VSA, Power Meter, Servo)
#     - Baseline measurements (power, EVM, ACLR)
#     - Single DPD, Iterative DPD, GMP DPD correction loops
#     - Power Servo (external NRX) and K18 Power Servo (VSA-based)
#     - Results logging and statistics generation in Excel
# ==============================================================

import os
import json
import pandas as pd
import numpy as np
import logging
from time import time
from openpyxl.styles import Font, PatternFill, Alignment
from src.measurements.vsg import VSG
from src.measurements.vsa import VSA
from src.measurements.power_meter import PowerMeter
from src.measurements.power_servo import PowerServo

# --------------------------------------------------------------
# Logging Setup
# --------------------------------------------------------------
logger = logging.getLogger(__name__)
base_path = os.path.dirname(__file__)
log_dir = os.path.join(base_path, 'logs')
os.makedirs(log_dir, exist_ok=True)


# --------------------------------------------------------------
# Main Sweep Routine
# --------------------------------------------------------------
def run_sweep():
    """
    Run a complete frequency sweep test using the configured parameters.
    Performs baseline and DPD-corrected measurements at each frequency,
    then saves results + summary statistics to Excel.
    """
    # -------------------------
    # File paths for test inputs, calibration data, and output
    # -------------------------
    json_path = os.path.join(base_path, 'test_inputs.json')
    cal_path = os.path.join(base_path, 'combined_cal_data.xlsx')
    output_path = os.path.join(base_path, 'sweep_measurements.xlsx')

    # -------------------------
    # Verify required files exist
    # -------------------------
    if not os.path.exists(json_path):
        logger.error(f"Test inputs file not found: {os.path.abspath(json_path)}")
        return
    if not os.path.exists(cal_path):
        logger.error(f"Calibration data file not found: {os.path.abspath(cal_path)}")
        return

    # -------------------------
    # Load sweep configuration from JSON
    # -------------------------
    with open(json_path, 'r') as f:
        config = json.load(f)

    sweep_params = config.get("Sweep_Measurement", {}).get("range", {})
    comment_mode = config.get("Sweep_Measurement", {}).get("user_comment_mode", "full_frame_nrx")
    comment_lines = config.get("User_Comments", {}).get(comment_mode, [])
    user_comment = "\n".join(comment_lines)

    # Sweep setup
    start = sweep_params["start_ghz"] * 1e9
    stop = sweep_params["stop_ghz"] * 1e9
    step = sweep_params["step_mhz"] * 1e6
    target_output = sweep_params.get("power_dbm", 10.0)
    tolerance = sweep_params.get("tolerence_db", 0.05)
    expected_gain = sweep_params.get("expected_gain_db", 0.0)
    ddpd_iterations = sweep_params.get("ddpd_iterations", 5)
    servo_iterations = sweep_params.get("servo_iterations", 5)

    # Generate frequency list
    freqs = np.arange(start, stop + step, step)
    freqs_ghz = [round(f / 1e9, 3) for f in freqs]

    # -------------------------
    # Load calibration offsets (Excel → dictionary)
    # -------------------------
    cal_df = pd.read_excel(cal_path)
    cal_dict = {
        round(float(row["Center Frequency (GHz)"]), 3): {
            "vsg_offset": float(row["VSG Offset (dB)"]),
            "vsa_offset": float(row["VSA Offset (dB)"]),
            "input_offset": float(row["Input Power Offset (dB)"]),
            "output_offset": float(row["Output Power Offset (dB)"])
        } for _, row in cal_df.iterrows()
    }

    # -------------------------
    # Initialize instruments
    # -------------------------
    vsg = VSG()   # Signal generator
    vsa = VSA()   # Signal analyzer
    pm = PowerMeter()  # NRX power meter
    power_servo = PowerServo(vsg, pm, vsa, max_iterations=servo_iterations, tolerance=tolerance)

    results = []
    matched_frequencies = []

    try:
        # ==========================================================
        # Loop through each frequency in the sweep
        # ==========================================================
        for freq in freqs:
            freq_ghz = round(freq / 1e9, 3)
            print(f"\n--- Testing Frequency: {freq_ghz} GHz ---")

            # Skip frequencies not found in calibration table
            if freq_ghz not in cal_dict:
                logger.warning(f"No calibration data for {freq_ghz} GHz — skipping")
                continue

            matched_frequencies.append(freq_ghz)
            offsets = cal_dict[freq_ghz]
            vsg_offset = offsets["vsg_offset"]
            vsa_offset = offsets["vsa_offset"]
            input_offset = offsets["input_offset"]
            output_offset = offsets["output_offset"]

            # -------------------------
            # Configure instruments with calibration offsets
            # -------------------------
            pm.configure(freq, input_offset, output_offset)
            vsg.configure(freq, target_output - expected_gain, vsg_offset)
            vsa.configure(freq, vsa_offset)

            # -------------------------
            # Baseline measurement (before DPD)
            # -------------------------
            servo_iterations_count, servo_settle_time = power_servo.servo_power(
                freq_ghz, target_output, expected_gain
            )
            corrected_input, corrected_output = pm.measure()
            start_time = time()
            freq_str = f"{freq:.0f}"

            vsa_power, evm_value, evm_time, chan_pow, adj_chan_lower, adj_chan_upper, aclr_time = (
                vsa.measure_evm(freq_str, vsa_offset, corrected_output)
            )

            # -------------------------
            # Single DPD measurement
            # -------------------------
            (single_dpd_power, single_dpd_evm, single_dpd_time,
             single_dpd_chan_pow, single_dpd_adj_chan_lower,
             single_dpd_adj_chan_upper, single_dpd_aclr_time,
             single_dpd_total_time, single_dpd_servo_loops,
             single_dpd_ext_servo_time, single_dpd_k18_time) = vsa.perform_single_dpd(
                freq_str, vsa_offset, target_output, servo_iterations,
                freq_ghz, expected_gain, power_servo
            )

            # -------------------------
            # Iterative DPD measurement
            # -------------------------
            (ddpd_power, ddpd_evm, ddpd_time,
             ddpd_chan_pow, ddpd_adj_chan_lower, ddpd_adj_chan_upper,
             ddpd_aclr_time, ddpd_total_time,
             ddpd_servo_loops, ddpd_ext_servo_time, ddpd_k18_time) = vsa.perform_iterative_dpd(
                freq_str, vsa_offset, target_output, ddpd_iterations,
                servo_iterations, freq_ghz, expected_gain, power_servo
            )

            # -------------------------
            # GMP DPD measurement
            # -------------------------
            (gmp_power, gmp_evm, gmp_time,
             gmp_chan_pow, gmp_adj_chan_lower, gmp_adj_chan_upper,
             gmp_aclr_time, gmp_total_time,
             gmp_servo_loops, gmp_ext_servo_time, gmp_k18_time) = vsa.perform_gmp_dpd(
                freq_str, vsa_offset, target_output, ddpd_iterations,
                servo_iterations, freq_ghz, expected_gain, power_servo
            )

            # -------------------------
            # Collect and store results for this frequency
            # -------------------------
            elapsed = time() - start_time
            print(f"Total measurement time at {freq_ghz} GHz: {elapsed:.3f}s")

            result = {
                # Instrument setup times
                "VSG Setup Time (s)": vsg.setup_time,
                "VSA Setup Time (s)": vsa.setup_time,

                # Frequency & servo information
                "Center Frequency (GHz)": freq_ghz,
                "Target Output Power (dBm)": target_output,
                "Servo Iterations": servo_iterations_count,
                "Servo Settle Time (s)": servo_settle_time,

                # Baseline measurements
                "Corrected Input Power (dBm)": corrected_input,
                "Corrected Output Power (dBm)": corrected_output,
                "VSA Output Power (dBm)": vsa_power,
                "EVM (dB)": evm_value,
                "EVM Measure Time (s)": evm_time,
                "Channel Power (dBm)": chan_pow,
                "Lower Adjacent ACLR (dB)": adj_chan_lower,
                "Upper Adjacent ACLR (dB)": adj_chan_upper,
                "ACLR Measure Time (s)": aclr_time,

                # Single DPD results
                "Single DPD Power (dBm)": single_dpd_power,
                "Single DPD EVM (dB)": single_dpd_evm,
                "Single DPD Measure Time (s)": single_dpd_time,
                "Single DPD Channel Power (dBm)": single_dpd_chan_pow,
                "Single DPD Lower Adjacent ACLR (dB)": single_dpd_adj_chan_lower,
                "Single DPD Upper Adjacent ACLR (dB)": single_dpd_adj_chan_upper,
                "Single DPD ACLR Measure Time (s)": single_dpd_aclr_time,
                "Single DPD Total Time (s)": single_dpd_total_time,
                "Single DPD Servo Loops": single_dpd_servo_loops,
                "Single DPD Ext Servo Time (s)": single_dpd_ext_servo_time,
                "Single DPD K18 Servo Time (s)": single_dpd_k18_time,

                # Iterative DPD results
                "Iterative DPD Power (dBm)": ddpd_power,
                "Iterative DPD EVM (dB)": ddpd_evm,
                "Iterative DPD Measure Time (s)": ddpd_time,
                "Iterative DPD Channel Power (dBm)": ddpd_chan_pow,
                "Iterative DPD Lower Adjacent ACLR (dB)": ddpd_adj_chan_lower,
                "Iterative DPD Upper Adjacent ACLR (dB)": ddpd_adj_chan_upper,
                "Iterative DPD ACLR Measure Time (s)": ddpd_aclr_time,
                "Iterative DPD Total Time (s)": ddpd_total_time,
                "Iterative DPD Servo Loops": ddpd_servo_loops,
                "Iterative DPD Ext Servo Time (s)": ddpd_ext_servo_time,
                "Iterative DPD K18 Servo Time (s)": ddpd_k18_time,

                # GMP DPD results
                "GMP Power (dBm)": gmp_power,
                "GMP EVM (dB)": gmp_evm,
                "GMP Measure Time (s)": gmp_time,
                "GMP Channel Power (dBm)": gmp_chan_pow,
                "GMP Lower Adjacent ACLR (dB)": gmp_adj_chan_lower,
                "GMP Upper Adjacent ACLR (dB)": gmp_adj_chan_upper,
                "GMP ACLR Measure Time (s)": gmp_aclr_time,
                "GMP Total Time (s)": gmp_total_time,
                "GMP Servo Loops": gmp_servo_loops,
                "GMP Ext Servo Time (s)": gmp_ext_servo_time,
                "GMP K18 Servo Time (s)": gmp_k18_time,

                # Summary
                "Total Elapsed Time (s)": round(elapsed, 3),
                "Comment": user_comment
            }

            results.append(result)
            print(user_comment)

    finally:
        # -------------------------
        # Always close instruments
        # -------------------------
        vsg.close()
        vsa.close()
        pm.close()

        # -------------------------
        # Save all results to Excel
        # -------------------------
        df = pd.DataFrame(results)
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # Measurements sheet
            df.to_excel(writer, sheet_name='Measurements', index=False)
            worksheet = writer.sheets['Measurements']

            # Wrap text in "Comment" column and resize rows
            for col_idx, col_name in enumerate(df.columns, start=1):
                if col_name == "Comment":
                    for row_idx in range(2, len(df)+2):
                        cell = worksheet.cell(row=row_idx, column=col_idx)
                        cell.alignment = Alignment(wrap_text=True)
                        value = str(cell.value) if cell.value else ""
                        lines = value.count("\n") + 1
                        worksheet.row_dimensions[row_idx].height = 15 * lines

            # Statistics sheet (summary across all frequencies)
            if not df.empty:
                stats_rows = [("Number of Tests", len(df))]
                numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
                for col in numeric_cols:
                    stats_rows.extend([
                        (f"{col} - Max", df[col].max()),
                        (f"{col} - Min", df[col].min()),
                        (f"{col} - Mean", df[col].mean())
                    ])
                stats_df = pd.DataFrame(stats_rows, columns=["Metric", "Value"])
                stats_df.to_excel(writer, sheet_name='Statistics', index=False)

                # Highlight means for readability
                yellow_fill = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid")
                bold_font = Font(bold=True, size=12)
                worksheet_stats = writer.sheets['Statistics']
                for row_idx in range(2, len(stats_rows)+2):
                    metric_cell = worksheet_stats.cell(row=row_idx, column=1)
                    value_cell = worksheet_stats.cell(row=row_idx, column=2)
                    if "Mean" in str(metric_cell.value):
                        metric_cell.fill = yellow_fill
                        value_cell.fill = yellow_fill
                        value_cell.font = bold_font

        logger.info(f"Saved sweep results to: {os.path.abspath(output_path)}")
        logger.info(f"Processed frequencies (GHz): {matched_frequencies}")


# --------------------------------------------------------------
# Script Entry Point
# --------------------------------------------------------------
if __name__ == "__main__":
    run_sweep()
