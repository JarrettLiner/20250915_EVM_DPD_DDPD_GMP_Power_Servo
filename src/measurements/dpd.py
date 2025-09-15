import logging
from time import time

logger = logging.getLogger(__name__)

class DPD:
    def __init__(self, vsa):
        self.vsa = vsa

    def perform_iterative_dpd(self, target_output, tolerance, max_iter):
        start_time = time()
        try:
            #  self.vsa.set_to_dpd_mode()
            self.vsa.query('INIT:IMM; *OPC?')
            time.wait(0.5)  # Wait for the VSA to settle
            self.vsa.write_command_opc('INST:SEL "Amplifier"')
            time.wait(1.0)  # Wait for the VSA to settle
            self.vsa.write_command_opc('CONF:GEN:CONN:STAT ON')
            self.vsa.write_command_opc('CONF:SETT')
            self.vsa.write_command_opc(':CONF:REFS:CGW:READ')
            self.vsa.query('INIT:IMM; *OPC?')
            self.vsa.write_command_opc('CONF:DPD:SHAP:MODE POLY')  # Enable DPD update
            self.vsa.write_command_opc('CONF:DPD:TRAD 0')  # Enable DPD update
            self.vsa.write_command_opc('CONF:DPD:UPD')  # Enable DPD update
            self.vsa.write_command_opc('CONF:DDPD:STAT ON')
            self.vsa.write_command_opc('CONF:DDPD:COUN 5')  # Example: Set 5 iterations
            self.vsa.write_command_opc('CONF:DDPD:TRAD 10')
            #  self.vsa.write_command_opc('CONF:GEN:CONT:STAT ON')
            #  self.vsa.write_command_opc('CONF:SETT')
            #  self.vsa.write_command_opc(':CONF:REFS:CGW:READ')
            #  self.vsa.write_command_opc('INIT:IMM')
            self.vsa.write_command_opc(':CONF:DDPD:STAR')  # Start with first iteration
            #  K18_power_servo()
            self.vsa.write_command_opc('INIT:IMM')
            self.vsa.write_command_opc('INST:SEL "5GNR"')  # Switch to 5G NR mode
            self.vsa.write_command_opc('INIT:IMM')
            dpd_evm = self.vsa.queryFloat('FETCh:CC1:ISRC:FRAM:SUMM:EVM:ALL:AVERage?')
            self.vsa.write('INST:SEL "Amplifier"; *OPC?')
            self.vsa.write('CONF:DDPD:APPL:STAT OFF; *OPC?')  # Disable DPD
            self.vsa.write('CONF:GEN:CONN:STAT OFF; *OPC?')
            dpd_time = time() - start_time
            dpd_iterations = 5  # Example value; replace with actual query if available
            return dpd_evm, dpd_time, dpd_iterations
        except Exception as e:
            logger.error(f"DPD measurement failed: {str(e)}")
            raise

    def K18_pwower_servo(self, target_output, tolerance, max_iter):
        start_time = time()
        # Servo input power to reach target output
        #  target_output
        tolerance = 0.1  # dB
        max_iter = 10
        servo_start_time = time()
        servo_iterations = 0
        K18_servo_settle_time = None
        try:
            self.vsa.write('SENS:PSER:STAT ON')
            self.vsa.write(f'SENS:PSER:TARG:VAL {target_output}')
            self.vsa.write(f'SENS:PSER:TARG:TOL {tolerance}')
            self.vsa.write(f'SENS:PSER:MAX:ITER {max_iter}')
            self.vsa.write('SENS:PSER:GLC RFL')
            self.vsa.query('SENS:PSER:STAR;*OPC?')
            K18_servo_settle_time = time() - start_time
            return K18_servo_settle_time
        except Exception as e:
            logger.error(f"K18 power servo failed: {str(e)}")
            raise


    def measure(self, freq_str, vsa_offset):
        start_time = time()
        try:
            self.vsa.set_to_dpd_mode()
            dpd_iterations = 5  # Example value
            self.vsa.write_command_opc('INST:SEL "Amplifier"')
            self.vsa.write_command_opc('CONF:DPD:SHAP:MODE POLY')  # Enable DPD update
            self.vsa.write_command_opc('CONF:DPD:TRAD 0')  # Enable DPD update
            self.vsa.write_command_opc('CONF:DPD:UPD')  # Enable DPD update
            self.vsa.write_command_opc('CONF:DDPD:STAT ON')
            self.vsa.write_command_opc(f'CONF:DDPD:COUN {dpd_iterations}')
            self.vsa.write_command_opc('CONF:DDPD:TRAD 10')
            self.vsa.write_command_opc('CONF:GEN:CONT:STAT ON')
            self.vsa.write_command_opc('CONF:SETT')
            self.vsa.write_command_opc(':CONF:REFS:CGW:READ')
            self.vsa.write_command_opc('INIT:IMM')
            self.vsa.write_command_opc(':CONF:DDPD:STAR')  # Start with first iteration
            self.vsa.write_command_opc('INIT:IMM')
            self.vsa.write_command_opc('INST:SEL "5GNR"')  # Switch to 5G NR mode
            self.vsa.write_command_opc('INIT:IMM')
            dpd_evm = self.vsa.queryFloat('FETCh:CC1:ISRC:FRAM:SUMM:EVM:ALL:AVERage?')
            self.vsa.write('INST:SEL "Amplifier"; *OPC?')
            self.vsa.write('CONF:DDPD:APPL:STAT OFF; *OPC?')  # Disable DPD
            self.vsa.write('CONF:GEN:CONN:STAT OFF; *OPC?')
            self.vsa.write(f':DISP:WIND:TRAC:Y:SCAL:RLEV:OFFS {vsa_offset:.2f}')
            self.vsa.write_command_opc('CONF:DDPD:STAR')
            self.vsa.write_command_opc('INIT:IMM')
            self.vsa.write_command_opc('INST:SEL "5GNR"')  # Switch to 5G NR mode
            self.vsa.write_command_opc('INIT:IMM')
            dpd_evm = self.vsa.queryFloat('FETCh:CC1:ISRC:FRAM:SUMM:EVM:ALL:AVERage?')
            self.vsa.write('INST:SEL "Amplifier"; *OPC?')
            self.vsa.write('CONF:DDPD:APPL:STAT OFF; *OPC?')  # Disable DPD
            self.vsa.write('CONF:GEN:CONN:STAT OFF; *OPC?')
            self.vsa.write('CONF:GEN:CONT:STAT OFF')
            measure_time = time() - start_time
            return dpd_evm, measure_time
        except Exception as e:
            logger.error(f"DPD measure failed: {str(e)}")
            raise