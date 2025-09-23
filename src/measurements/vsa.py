# ==============================================================
# File: vsa.py
# Description:
#   Vector Signal Analyzer (VSA) control module for:
#     - Instrument initialization & setup
#     - Reference level / frequency configuration
#     - Baseline EVM and ACLR measurements
#     - Digital Pre-Distortion (DPD) tests:
#         * Single DPD
#         * Iterative DPD
#         * GMP DPD
#     - Power Servo controls:
#         * External NRX (via PowerServo)
#         * K18 internal VSA-based servo
# ==============================================================

import logging
from time import time, sleep
from src.instruments.bench import bench
from src.measurements.power_servo import PowerServo
import json
import os

# --------------------------------------------------------------
# Logging Setup
# --------------------------------------------------------------
logger = logging.getLogger(__name__)

# --------------------------------------------------------------
# Load Test Input JSON Config (test_inputs.json)
# Provides global defaults for servo behavior
# --------------------------------------------------------------
config_path = os.path.join(os.getcwd(), "test_inputs.json")
if os.path.exists(config_path):
    with open(config_path, "r") as f:
        test_config = json.load(f)
    sweep_cfg = test_config.get("Sweep_Measurement", {}).get("range", {})
else:
    test_config = {}
    sweep_cfg = {}

# Default flags (overridable via function args)
USE_POWER_SERVO = sweep_cfg.get("use_power_servo", True)
USE_K18_POWER_SERVO = sweep_cfg.get("use_K18_power_servo", True)


class VSA:
    # ----------------------------------------------------------
    # Initialization
    # ----------------------------------------------------------
    def __init__(self, host="192.168.200.20", port=5025):
        """
        Initialize the VSA instrument.
        - Resets the analyzer
        - Loads the configured 5G NR setup (full frame or first slot)
        - Prepares measurement environment for EVM/ACLR/DPD
        """
        self.bench = bench()
        start_time = time()
        try:
            vsa_setup_start = time()

            # Start instrument connection
            self.instr = self.bench.VSA_start()
            self.instr.query('*RST; *OPC?')   # Reset analyzer
            self.instr.query('*OPC?')

            # Select setup file (full frame vs. first slot)
            setup_mode = test_config.get("Sweep_Measurement", {}).get("setup_mode", "fullframe")
            if setup_mode.lower() == "fullframe":
                setup_file = r'C:\R_S\instr\user\Qorvo\5GNR_UL_10MHz_256QAM_30kHz_24RB_0RBO_fullframe'
            elif setup_mode.lower() == "firstslot":
                setup_file = r'C:\R_S\instr\user\Qorvo\5GNR_UL_10MHz_256QAM_30kHz_24RB_0RBO_1slot'
            else:
                logger.warning(f"Unknown setup_mode '{setup_mode}', defaulting to fullframe")
                setup_file = r'C:\R_S\instr\user\Qorvo\5GNR_UL_10MHz_256QAM_30kHz_24RB_0RBO_fullframe'

            # Load selected memory setup file
            self.instr.query(fr'MMEM:LOAD:STAT 1,"{setup_file}"; *OPC?')
            #  self.instr.query('CONF:NR5G:DL:CC1:RFUC:STAT ON; *OPC?')
            #  self.instr.query('CONF:NR5G:DL:CC1:RFUC:FZER:MODE CF; *OPC?')
            #  self.instr.query(':SENS:SWE:TIME 0.01; *OPC?')
            self.instr.query('INIT:IMM; *OPC?')

            # Ensure 5G NR measurement setup
            '''
            self.instr.query('INST:SEL "5G NR"; *OPC?')
            self.instr.query(':CONF:GEN:CONN:STAT ON; *OPC?')
            self.instr.query('CONF:GEN:CONT:STAT ON; *OPC?')
            self.instr.query('CONF:GEN:RFO:STAT ON; *OPC?')
            self.instr.query('CONF:GEN:POW:LEV:STAT ON; *OPC?')
            self.instr.query('CONF:GEN:SETT:UPD:RF; *OPC?')
            self.instr.query('CONF:SETT:RF; *OPC?')
            self.instr.query('CONF:SETT:NR5G; *OPC?')
            self.instr.query(':SENS:ADJ:LEV; *OPC?')
            self.instr.query(':SENS:ADJ:EVM; *OPC?')
            self.instr.query(':DISP:WIND3:SUBW1:TRAC:Y:SCAL:AUTO ALL; *OPC?')            
            #  self.instr.query(':CONF:NR5G:DL:CC1:RFUC:FZER:MODE CF; *OPC?')
            self.instr.query(':INIT:IMM; *OPC?')
            '''
            # Amplifier/K18 setup
            self.write_command_opc('INST:SEL "Amplifier"')
            self.instr.query('CONF:GEN:CONT:STAT ON; *OPC?')

            '''
            K18_setup_start = time()
            self.instr.query(':INST:CRE:NEW AMPL, "Amplifier"; *OPC?')
            self.instr.query('CONF:GEN:CONT:STAT ON; *OPC?')
            self.instr.query('CONF:SETT; *OPC?')
            self.instr.query(':CONF:REFS:CGW:READ; *OPC?')
            self.instr.query(':SENS:ADJ:LEV; *OPC?')
            self.instr.query(':TRIG:SEQ:SOUR EXT; *OPC?')
            self.instr.query('INIT:CONT OFF; *OPC?')
            self.instr.query(':INIT:IMM; *OPC?')
            self.instr.query('INST:SEL "5G NR"; *OPC?')
            K18_setup_time = time() - K18_setup_start
            print(f"K18 setup time: {K18_setup_time:.3f}s")
            '''
            # Total setup timing
            self.setup_time = time() - start_time
            print(f"Total VSA setup time: {self.setup_time:.3f}s")
            vsa_setup_time = time() - vsa_setup_start
            print(f"VSA setup (reset + setup file load) time: {vsa_setup_time:.3f}s")
            logger.info(f"VSA initialized in {self.setup_time:.3f}s using setup '{setup_mode}'")

        except Exception as e:
            logger.error(f"VSA initialization failed: {str(e)}")
            raise

    # ----------------------------------------------------------
    # Utility methods
    # ----------------------------------------------------------
    def autolevel(self):
        """Automatically adjust analyzer input level."""
        self.instr.query(':SENS:ADJ:LEV; *OPC?')

    def autoEVM(self):
        """Automatically optimize EVM measurement settings."""
        self.instr.query(':SENS:ADJ:EVM; *OPC?')

    def set_ref_level(self, ref_level):
        """Set the reference level (dBm)."""
        try:
            self.instr.query(f'DISP:WIND:TRAC:Y:SCAL:RLEV {ref_level:.2f}; *OPC?')
            logger.info(f"VSA reference level set to {ref_level:.2f} dBm")
        except Exception as e:
            logger.error(f"Setting VSA reference level failed: {str(e)}")
            raise

    def configure(self, freq, vsa_offset):
        """Configure analyzer frequency and offset."""
        try:
            self.instr.query('INST:SEL "5G NR"; *OPC?')
            #  self.instr.query('CONF:NR5G:DL:CC1:RFUC:STAT OFF; *OPC?')
            #  self.instr.query('CONF:NR5G:DL:CC1:RFUC:FZER:MODE CF; *OPC?')
            self.instr.query(f':SENS:FREQ:CENT {freq}; *OPC?')
            self.instr.write(f':DISP:WIND:TRAC:Y:SCAL:RLEV:OFFS {vsa_offset:.2f}')
            self.instr.query(':SENS:ADJ:EVM; *OPC?')
            self.instr.query(':DISP:WIND3:SUBW1:TRAC:Y:SCAL:AUTO ALL; *OPC?')
            self.instr.query(':INIT:IMM; *OPC?')

            self.instr.query('INST:SEL "Amplifier"; *OPC?')
            self.instr.query('CONF:GEN:CONN:STAT ON; *OPC?')
            self.instr.query('CONF:GEN:CONT:STAT ON; *OPC?')
            self.instr.write(f':DISP:WIND:TRAC:Y:SCAL:RLEV:OFFS {vsa_offset:.2f}')
            self.instr.query(f':CONF:GEN:LEV:DUTL {5}; *OPC?')
            self.instr.query('INST:SEL "5G NR"; *OPC?')
            logger.info(f"VSA configured: Freq={freq} Hz, Offset={vsa_offset} dB")
        except Exception as e:
            logger.error(f"VSA configuration failed: {str(e)}")
            raise

    def queryFloat(self, command):
        """Send SCPI query and return float response."""
        try:
            return float(self.instr.query(command))
        except Exception:
            logger.warning(f"Non-float response for {command}")
            return float('nan')

    def write_command_opc(self, command: str) -> None:
        """
        Write a command and wait for operation complete (OPC).
        Ensures command execution before proceeding.
        """
        try:
            self.instr.write('*ESE 1')   # Enable Operation Complete bit
            self.instr.write('*SRE 32')  # Enable service request for OPC
            self.instr.write(f'{command};*OPC')  # Send command with OPC
            while (int(self.instr.query('*ESR?')) & 1) != 1:
                sleep(0.2)  # Poll ESR until OPC complete
            logger.info(f"Command '{command}' completed with OPC synchronization.")
        except Exception as e:
            logger.error(f"Error during OPC write for command '{command}': {str(e)}")
            raise

    # ----------------------------------------------------------
    # Power Servo helpers
    # ----------------------------------------------------------
    def power_servo(self, power_servo, freq_ghz, target_output, expected_gain, max_iterations):
        """
        Run external NRX-based power servo loop.
        Returns (servo_iterations, servo_time_s, servo_settle_time).
        """
        try:
            start_time = time()
            servo_iterations, servo_settle_time = power_servo.servo_power(freq_ghz, target_output, expected_gain)
            servo_time = round(time() - start_time, 3)
            logger.info(f"Power servo completed in {servo_time:.3f}s ({servo_iterations} iterations)")
            print(f"Power servo time: {servo_time:.3f}s over {servo_iterations} iterations, settle time: {servo_settle_time:.3f}s, Power Servo Target: {target_output} dBm")
            return servo_iterations, servo_time, servo_settle_time
        except Exception as e:
            logger.error(f"Power servo failed: {str(e)}")
            raise

    def K18_power_servo(self, target_output, max_iterations):
        """
        Run VSA internal (K18) power servo.
        Returns elapsed time in seconds.
        """
        try:
            self.instr.query('INST:SEL "Amplifier"; *OPC?')

            self.instr.query('CONF:GEN:CONN:STAT ON; *OPC?')
            self.instr.query('CONF:GEN:CONT:STAT ON; *OPC?')
            self.instr.query(':CONF:SETT; *OPC?')
            self.instr.query('INIT:CONT OFF; *OPC?')
            self.instr.query('INIT:IMM; *OPC?')
            self.instr.query(':SENS:PSER:STAT ON; *OPC?')
            self.instr.query(f':SENS:PSER:TARG:VAL {target_output}; *OPC?')
            self.instr.query(f':SENS:PSER:MAX:ITER {max_iterations}; *OPC?')
            #  self.instr.query(':SENS:PSER:GLC RFL; *OPC?')
            start_time = time()
            self.instr.query(':SENS:PSER:STAR; *OPC?')
            #  self.instr.query(':SENS:PSER:STAR; *OPC?')
            elapsed = round(time() - start_time, 3)
            self.instr.query(':INIT:IMM; *OPC?')
            logger.info(f"K18 power servo completed in {elapsed:.3f}s")
            '''
            self.instr.query('CONF:GEN:CONT:STAT OFF; *OPC?')
            self.instr.query('CONF:GEN:CONN:STAT OFF; *OPC?')
            '''
            PowerLevel = self.instr.query(':FETCh:POWer:OUTPut:CURRent:RES?; *OPC?')
            print(f"K18 power servo time: {elapsed:.3f}s, Power Servo Target: {PowerLevel} dBm")
            return elapsed

        except Exception as e:
            logger.error(f"K18 power servo failed: {str(e)}")
            raise

    def _resolve_servo_flags(self, use_power_servo_arg, use_k18_power_servo_arg):
        """Resolve servo flags (explicit args take precedence over global defaults)."""
        use_power_servo = bool(use_power_servo_arg) if use_power_servo_arg is not None else globals().get("USE_POWER_SERVO", True)
        use_k18_power_servo = bool(use_k18_power_servo_arg) if use_k18_power_servo_arg is not None else globals().get("USE_K18_POWER_SERVO", False)
        return use_power_servo, use_k18_power_servo

    def _run_servos(self, power_servo_obj, freq_ghz, target_output, expected_gain, max_iterations,
                    use_power_servo, use_k18_power_servo):
        """
        Run enabled servos (external + K18).
        Returns (servo_loops, ext_servo_time, k18_time).
        """
        servo_loops = 0
        ext_servo_time = 0.0
        k18_time = 0.0
        if use_power_servo and power_servo_obj is not None:
            servo_loops, ext_servo_time, _ = self.power_servo(power_servo_obj, freq_ghz, target_output, expected_gain, max_iterations)
        if use_k18_power_servo:
            k18_time = self.K18_power_servo(target_output, max_iterations)
        return servo_loops, ext_servo_time, k18_time

    # ----------------------------------------------------------
    # Baseline EVM/ACLR measurement (no DPD applied)
    # ----------------------------------------------------------
    def measure_evm(self, freq_str, vsa_offset, target_output, servo_iterations,
                           freq_ghz, expected_gain, power_servo,
                           USE_POWER_SERVO=None, USE_K18_POWER_SERVO=None):

        """
        Perform baseline measurement (before DPD):
          - EVM
          - Channel Power
          - ACLR (Lower/Upper Adjacent)
        Returns (vsa_power, evm, evm_time, chan_pow, adj_lower, adj_upper, aclr_time).
        """
        try:
            total_start = time()
            # EVM measurement

            self.instr.query('INIT:CONT OFF; *OPC?')
            self.instr.query('INIT:IMM; *OPC?')

            # Run servos (external + K18 as configured)
            power_servo_start = time()
            use_power_servo, use_k18_power_servo = self._resolve_servo_flags(USE_POWER_SERVO, USE_K18_POWER_SERVO)
            servo_loops, ext_servo_time, k18_time = self._run_servos(power_servo, freq_ghz, target_output,
                                                                     expected_gain, servo_iterations,
                                                                     use_power_servo, use_k18_power_servo)
            power_servo_time = time() - power_servo_start
            evm_start = time()
            self.instr.query(':INST:SEL "5G NR"; *OPC?')
            self.instr.query('INIT:IMM; *OPC?')
            vsa_power = self.queryFloat('FETC:CC1:ISRC:FRAM:SUMM:POW:AVERage?')
            evm = self.queryFloat('FETC:CC1:ISRC:FRAM:SUMM:EVM:ALL:AVERage?')
            print(f"Baseline EVM measurement: Power={vsa_power}, EVM={evm}")
            evm_time = time() - evm_start
            print(f"uncorrected EVM and VSA Power time: {evm_time:.3f}s")

            # ACLR measurement
            aclr_start = time()
            self.instr.write('CONF:NR5G:MEAS ACLR')
            self.instr.write('INIT:IMM;*WAI')
            aclr_list = self.instr.query('CALC:MARK:FUNC:POW:RES? ACP')
            chan_pow, adj_lower, adj_upper = [float(x) for x in aclr_list.split(',')[:3]]
            aclr_time = time() - aclr_start
            print(f"uncorrected ACLR time: {aclr_time:.3f}s")
            total_evm_time = time() - total_start
            print(f"Total baseline evm time: {total_evm_time:.3f}s")

            # Restore EVM mode
            self.instr.write('CONF:NR5G:MEAS EVM')
            total_evm_time = time() - total_start
            logger.info(f"Baseline measurement done: Power={vsa_power}, EVM={evm}, ACLR time={aclr_time:.3f}s")

            return (vsa_power, evm, evm_time, chan_pow, adj_lower, adj_upper, aclr_time, total_evm_time, servo_loops, ext_servo_time, k18_time)

        except Exception as e:
            logger.error(f"Baseline EVM measurement failed: {str(e)}")
            raise

    # ----------------------------------------------------------
    # Single DPD
    # Returns 11-tuple (power, evm, evm_time, chan_pow, adj_lower, adj_upper,
    #                   aclr_time, total_time, servo_loops, ext_servo_time, k18_time)
    # ----------------------------------------------------------
    def perform_single_dpd(self, freq_str, vsa_offset, target_output, servo_iterations,
                           freq_ghz, expected_gain, power_servo,
                           USE_POWER_SERVO=None, USE_K18_POWER_SERVO=None):
        """Run single DPD correction + measurement."""
        try:
            total_start = time()

            # Select amplifier block
            self.write_command_opc('INST:SEL "Amplifier"')
            self.instr.query('CONF:GEN:CONN:STAT ON; *OPC?')
            self.instr.query('CONF:GEN:CONT:STAT ON; *OPC?')
            self.instr.query('CONF:SETT; *OPC?')
            self.instr.query(':CONF:REFS:CGW:READ; *OPC?')

            # Configure Single DPD
            dpd_setup_start = time()
            self.instr.query('INIT:CONT OFF; *OPC?')
            self.instr.query('INIT:IMM; *OPC?')
            self.instr.query('CONF:DDPD:STAT OFF; *OPC?')
            self.instr.query('CONF:DPD:SHAP:MODE POLY; *OPC?')
            self.instr.query(':CONF:DPD:TRAD 10; *OPC?')
            self.instr.query('INIT:IMM; *OPC?')
            self.instr.query(':CONF:DPD:FILE:GEN; *OPC?')
            self.instr.query(':CONF:DPD:UPD; *OPC?')
            self.instr.query('CONF:DPD:AMAM:STAT ON; *OPC?')
            self.instr.query('CONF:DPD:AMPM:STAT ON; *OPC?')
            self.instr.query('INIT:IMM; *OPC?')
            dpd_setup_time = time() - dpd_setup_start
            print(f"DPD setup time: {dpd_setup_time:.3f}s")
            print(" this includes single dpd config and update")

            # Run servos (external + K18 as configured)
            power_servo_start = time()
            use_power_servo, use_k18_power_servo = self._resolve_servo_flags(USE_POWER_SERVO, USE_K18_POWER_SERVO)
            servo_loops, ext_servo_time, k18_time = self._run_servos(power_servo, freq_ghz, target_output,
                                                                     expected_gain, servo_iterations,
                                                                     use_power_servo, use_k18_power_servo)
            power_servo_time = time() - power_servo_start
            print(f"single dpd Servo loop time: {power_servo_time:.3f}s")
            print(f"use nrx", {use_power_servo}, "use K18", {use_k18_power_servo}, "servo iterations", {servo_loops})

            # EVM measurement (after DPD)
            self.instr.query('INST:SEL "5G NR"; *OPC?')
            evm_start = time()
            self.instr.query('CONF:NR5G:MEAS EVM; *OPC?')
            self.instr.query('INIT:IMM; *OPC?')
            self.instr.query('INIT:IMM; *OPC?')
            dpd_power = self.queryFloat('FETC:CC1:ISRC:FRAM:SUMM:POW:AVERage?')
            dpd_evm = self.queryFloat('FETC:CC1:ISRC:FRAM:SUMM:EVM:ALL:AVERage?')
            print(f"Single DPD measurement: Power={dpd_power}, EVM={dpd_evm}")
            evm_time = time() - evm_start
            print(f"single dpd EVM and VSA Power time: {evm_time:.3f}s")

            # ACLR measurement
            aclr_start = time()
            self.instr.query('CONF:NR5G:MEAS ACLR; *OPC?')
            self.instr.query('INIT:IMM;*OPC?')
            aclr_list = self.instr.query('CALC:MARK:FUNC:POW:RES? ACP')
            chan_pow, adj_lower, adj_upper = [float(x) for x in aclr_list.split(',')[:3]]
            aclr_time = time() - aclr_start
            print(f"single dpd ACLR time: {aclr_time:.3f}s")
            total_time = time() - total_start
            print(f"Total single dpd evm time: {total_time:.3f}s")
            logger.info(f"Single DPD done: Power={dpd_power}, EVM={dpd_evm}, Total={total_time:.3f}s")
            self.write_command_opc('INST:SEL "Amplifier"')
            self.instr.query('CONF:DPD:AMAM:STAT OF; *OPC?')
            self.instr.query('CONF:DPD:AMPM:STAT OF; *OPC?')
            self.instr.query('INST:SEL "5G NR"; *OPC?')
            '''
            self.instr.query('CONF:GEN:CONT:STAT OFF; *OPC?')
            self.instr.query('CONF:GEN:CONN:STAT OFF; *OPC?')
            '''

            return (dpd_power, dpd_evm, evm_time,
                    chan_pow, adj_lower, adj_upper,
                    aclr_time, total_time,
                    servo_loops, ext_servo_time, k18_time)

        except Exception as e:
            logger.error(f"Single DPD failed: {str(e)}")
            raise

    # ----------------------------------------------------------
    # Iterative DPD
    # ----------------------------------------------------------
    def perform_iterative_dpd(self, freq_str, vsa_offset, target_output, ddpd_iterations, servo_iterations,
                              freq_ghz, expected_gain, power_servo,
                              USE_POWER_SERVO=None, USE_K18_POWER_SERVO=None):
        """Run iterative DPD (multiple correction loops) + measurement."""
        try:
            # Select amplifier

            self.write_command_opc('INST:SEL "Amplifier"')
            self.instr.query('CONF:GEN:CONN:STAT ON; *OPC?')
            self.instr.query('CONF:GEN:CONT:STAT ON; *OPC?')
            self.instr.query('CONF:SETT; *OPC?')
            self.instr.query(':CONF:REFS:CGW:READ; *OPC?')
            total_start = time()
            ddpd_setup_start = time()


            # Configure Iterative DPD
            ddpd_measure_start = time()
            self.instr.query('CONF:DDPD:STAT ON; *OPC?')
            self.instr.query('CONF:DDPD:TRAD 100; *OPC?')
            self.instr.query(f':CONF:DDPD:COUN {ddpd_iterations}; *OPC?')
            self.instr.query(':CONF:DDPD:STAR; *OPC?')
            ddpd_measure_time = time() - ddpd_measure_start
            print(f"Iterative DPD measurement time: {ddpd_measure_time:.3f}s")
            print("this includes ddpd config and iterative dpd run")
            print(f"ddpd iterations: {ddpd_iterations}")

            # Run servos
            ddpd_power_servo_start = time()
            use_power_servo, use_k18_power_servo = self._resolve_servo_flags(USE_POWER_SERVO, USE_K18_POWER_SERVO)
            servo_loops, ext_servo_time, k18_time = self._run_servos(power_servo, freq_ghz, target_output,
                                                                     expected_gain, servo_iterations,
                                                                     use_power_servo, use_k18_power_servo)
            ddpd_power_servo_time = time() - ddpd_power_servo_start
            print(f"Iterative DPD Servo loop time: {ddpd_power_servo_time:.3f}s")
            print(f"use nrx", {use_power_servo}, "use K18", {use_k18_power_servo}, "servo iterations", {servo_loops})

            # EVM measurement
            evm_start = time()
            self.instr.query('INST:SEL "5G NR"; *OPC?')
            self.instr.query('CONF:NR5G:MEAS EVM; *OPC?')
            self.instr.query('INIT:IMM; *OPC?')
            self.instr.query('INIT:IMM; *OPC?')
            ddpd_power = self.queryFloat('FETC:CC1:ISRC:FRAM:SUMM:POW:AVERage?')
            ddpd_evm = self.queryFloat('FETC:CC1:ISRC:FRAM:SUMM:EVM:ALL:AVERage?')
            print(f"Iterative DPD measurement: Power={ddpd_power}, EVM={ddpd_evm}")
            ddpd_evm_time = time() - evm_start
            print(f"Iterative DPD EVM and VSA Power time: {ddpd_evm_time:.3f}s")

            # ACLR measurement
            aclr_start = time()
            self.instr.query('CONF:NR5G:MEAS ACLR; *OPC?')
            self.instr.query('INIT:IMM;*OPC?')
            aclr_list = self.instr.query('CALC:MARK:FUNC:POW:RES? ACP')
            ddpd_chan_pow, ddpd_adj_lower, ddpd_adj_upper = [float(x) for x in aclr_list.split(',')[:3]]
            ddpd_aclr_time = time() - aclr_start
            print(f"Iterative DPD ACLR time: {ddpd_aclr_time:.3f}s")
            ddpd_total_time = time() - total_start
            print(f"Total iterative dpd evm time: {ddpd_total_time:.3f}s")
            logger.info(f"Iterative DPD done: Power={ddpd_power}, EVM={ddpd_evm}, Total={ddpd_total_time:.3f}s")
            self.instr.query(':CONF:DDPD:STAT OFF; *OPC?')
            self.instr.query('CONF:GEN:CONT:STAT OFF; *OPC?')
            self.instr.query('CONF:GEN:CONN:STAT OFF; *OPC?')

            return (ddpd_power, ddpd_evm, ddpd_evm_time,
                    ddpd_chan_pow, ddpd_adj_lower, ddpd_adj_upper,
                    ddpd_aclr_time, ddpd_total_time,
                    servo_loops, ext_servo_time, k18_time)

        except Exception as e:
            logger.error(f"Iterative DPD failed: {str(e)}")
            raise

    # ----------------------------------------------------------
    # GMP DPD
    # ----------------------------------------------------------
    def perform_gmp_dpd(self, freq_str, vsa_offset, target_output, ddpd_iterations, servo_iterations,
                        freq_ghz, expected_gain, power_servo,
                        USE_POWER_SERVO=None, USE_K18_POWER_SERVO=None):
        """Run GMP (Generalized Memory Polynomial) DPD + measurement."""
        try:
            self.write_command_opc('INST:SEL "Amplifier"')
            self.instr.query('CONF:GEN:CONN:STAT ON; *OPC?')
            self.instr.query('CONF:GEN:CONT:STAT ON; *OPC?')
            self.instr.query('CONF:SETT; *OPC?')
            self.instr.query(':CONF:REFS:CGW:READ; *OPC?')
            total_start = time()
            gmp_setup_start = time()
            # Select amplifier + run DDPD as base
            gmp_ddpd_setup_start = time()
            self.write_command_opc('INST:SEL "Amplifier"')
            self.instr.query('CONF:DDPD:STAT ON; *OPC?')
            self.instr.query('CONF:DDPD:TRAD 100; *OPC?')
            self.instr.query(f':CONF:DDPD:COUN {ddpd_iterations}; *OPC?')
            self.instr.query(':CONF:DDPD:STAR; *OPC?')
            gmp_ddpd_setup_time = time() - gmp_ddpd_setup_start
            print(f"GMP DDPD setup time: {gmp_ddpd_setup_time:.3f}s")
            print("this includes ddpd config and iterative dpd run")
            print(f"ddpd iterations: {ddpd_iterations}")

            # GMP-specific configuration
            gmp_calc_setup_start = time()
            self.instr.query('CONF:MDPD:STAT ON; *OPC?')
            self.instr.query('CALC:MDPD:MOD;*OPC?')
            self.instr.query('CONF:GMP:LAG:ORD:XTER 1;*OPC?')
            self.instr.query('CONF:GMP:LEAD:ORD:XTER 1;*OPC?')
            self.instr.query('CONF:MDPD:ITER 5;*OPC?')
            self.instr.query(':CALC:MDPD:MOD;*OPC?')
            self.instr.query(':CONF:MDPD:WAV:UPD;*OPC?')
            self.instr.query('CONF:MDPD:WAV:SEL MDPD;*OPC?')
            gmp_calc_setup_time = time() - gmp_calc_setup_start
            print(f"GMP Calc setup time: {gmp_calc_setup_time:.3f}s")
            print(" this includes gmp config, calc and sync to vsg")
            gmp_setup_time = time() - gmp_setup_start
            print(f"GMP total setup time: {gmp_setup_time:.3f}s")
            self.instr.query('CONF:GEN:CONT:STAT OFF; *OPC?')
            self.instr.query('CONF:GEN:CONN:STAT OFF; *OPC?')

            # Run servos
            gmp_power_servo_start = time()
            use_power_servo, use_k18_power_servo = self._resolve_servo_flags(USE_POWER_SERVO, USE_K18_POWER_SERVO)
            servo_loops, ext_servo_time, k18_time = self._run_servos(power_servo, freq_ghz, target_output,
                                                                     expected_gain, servo_iterations,
                                                                     use_power_servo, use_k18_power_servo)
            gmp_power_servo_time = time() - gmp_power_servo_start
            print(f"GMP DPD Servo loop time: {gmp_power_servo_time:.3f}s")
            print(f"use nrx", {use_power_servo}, "use K18", {use_k18_power_servo}, "servo iterations", {servo_loops})

            # EVM measurement
            evm_start = time()
            self.instr.query('INST:SEL "5G NR"; *OPC?')
            self.instr.query('CONF:NR5G:MEAS EVM; *OPC?')
            self.instr.query('INIT:IMM; *OPC?')
            gmp_power = self.queryFloat('FETC:CC1:ISRC:FRAM:SUMM:POW:AVERage?')
            gmp_evm = self.queryFloat('FETC:CC1:ISRC:FRAM:SUMM:EVM:ALL:AVERage?')
            print(f"GMP DPD measurement: Power={gmp_power}, EVM={gmp_evm}")
            gmp_evm_time = time() - evm_start
            print(f"GMP DPD EVM and VSA Power time: {gmp_evm_time:.3f}s")

            # ACLR measurement
            aclr_start = time()
            self.instr.write('CONF:NR5G:MEAS ACLR')
            self.instr.write('INIT:IMM;*WAI')
            aclr_list = self.instr.query('CALC:MARK:FUNC:POW:RES? ACP')
            gmp_chan_pow, gmp_adj_lower, gmp_adj_upper = [float(x) for x in aclr_list.split(',')[:3]]
            gmp_aclr_time = time() - aclr_start
            print(f"GMP DPD ACLR time: {gmp_aclr_time:.3f}s")

            total_time = time() - total_start
            print(f"Total GMP dpd evm time: {total_time:.3f}s")
            print("this includes gmp setup, ddpd, gmp calc and sync, power servo, evm and aclr")
            logger.info(f"GMP DPD done: Power={gmp_power}, EVM={gmp_evm}, Total={total_time:.3f}s")

            # Restore EVM mode
            self.instr.query(':INST:SEL "Amplifier"; *OPC?')
            self.instr.query(':CONF:MDPD:WAV:SEL REF; *OPC?')
            self.instr.query(':CONF:DDPD:APPL:STAT OFF; *OPC?')
            self.instr.query(':INST:SEL "5G NR"; *OPC?')
            self.instr.query(':CONF:NR5G:MEAS EVM; *OPC?')
            self.instr.query(f':CONF:NR5G:DL:CC1:RFUC:STAT OFF; *OPC?')
            self.instr.query('CONF:GEN:CONT:STAT OFF; *OPC?')
            self.instr.query('CONF:GEN:CONN:STAT OFF; *OPC?')
            return (gmp_power, gmp_evm, gmp_evm_time,
                    gmp_chan_pow, gmp_adj_lower, gmp_adj_upper,
                    gmp_aclr_time, total_time,
                    servo_loops, ext_servo_time, k18_time)

        except Exception as e:
            logger.error(f"GMP DPD failed: {str(e)}")
            raise

    # ----------------------------------------------------------
    # Cleanup
    # ----------------------------------------------------------
    def close(self):
        """Close socket connection to VSA."""
        try:
            self.instr.close()
            logger.info("VSA socket closed")
        except Exception as e:
            logger.error(f"Error closing VSA socket: {str(e)}")
            raise
# ==============================================================