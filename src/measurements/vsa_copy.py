import logging
from time import time
from src.instruments.bench import bench
from src.measurements.power_meter import PowerMeter
from src.measurements.vsg import VSG

logger = logging.getLogger(__name__)

class VSA:
    def __init__(self, host="192.168.200.20", port=5025):
        self.bench = bench()
        #  self.vsg = VSG()  # Instantiate VSG instead of assigning the class
        start_time = time()
        try:
            self.instr = self.bench.VSA_start()  # Get iSocket instance
            self.instr.query('*RST; *OPC?')
            self.instr.query('*OPC?')
            #  self.instr.query('MMEM:SEL:ITEM:HWS ON; *OPC?')
            self.instr.query(r'MMEM:LOAD:STAT 1,"C:\R_S\instr\user\Qorvo\5GNR_UL_10MHz_256QAM_30kHz_24RB_0RBO"; *OPC?')
            '''
            self.instr.query(':SENS:ADJ:LEV; *OPC?')
            self.instr.query(':SENS:ADJ:EVM; *OPC?')
            self.instr.query('CONF:GEN:CONN:STAT ON; *OPC?')
            self.instr.query('CONF:GEN:CONT:STAT ON; *OPC?')
            self.instr.query('CONF:SETT:RF; *OPC?')
            self.instr.query(':CONF:GEN:RFO:STAT ON; *OPC?')
            self.instr.query('CONF:SETT:NR5G; *OPC?')
            '''
            self.instr.query('INIT:IMM; *OPC?')
            self.setup_time = time() - start_time
            logger.info(f"VSA initialized in {self.setup_time:.3f}s")
        except Exception as e:
            logger.error(f"VSA initialization failed: {str(e)}")
            raise

    def autolevel(self):
        self.instr.query(':SENS:ADJ:LEV; *OPC?')

    def autoEVM(self):
        self.instr.query(':SENS:ADJ:EVM; *OPC?')

    def set_ref_level(self, ref_level):
        try:
            self.instr.query('DISP:WIND:TRAC:Y:SCAL:RLEV {ref_level:.2f}; *OPC?')
            logger.info(f"VSA reference level set to {ref_level:.2f} dBm")
        except Exception as e:
            logger.error(f"Setting VSA reference level failed: {str(e)}")
            raise

    def configure(self, freq, vsa_offset):
        try:
            self.instr.query(f':SENS:FREQ:CENT {freq}; *OPC?')
            self.instr.write(f':DISP:WIND:TRAC:Y:SCAL:RLEV:OFFS {vsa_offset:.2f}')
            self.instr.query(':INIT:IMM; *OPC?')
        except Exception as e:
            logger.error(f"VSA configuration failed: {str(e)}")
            raise

    def queryFloat(self, command):
        try:
            return float(self.instr.query(command))
        except ValueError:
            logger.warning(f"Non-float response for {command}")
            return float('nan')

    def write_command_opc(self, command: str) -> None:
        try:
            self.instr.write('*ESE 1')  # Enable Operation Complete bit
            self.instr.write('*SRE 32')  # Enable service request for OPC
            self.instr.write(f'{command};*OPC')  # Send command with OPC
            while (int(self.instr.query('*ESR?')) & 1) != 1:
                time.sleep(0.2)  # Wait briefly between polls
            logger.info(f"Command '{command}' completed with OPC synchronization.")
        except Exception as e:
            logger.error(f"Error during OPC write for command '{command}': {str(e)}")
            raise

    def measure_evm(self, freq_str, ref_lev, vsa_offset, ):
        try:
            #  self.set_ref_level(ref_lev)

            self.instr.query('INST:SEL "5G NR"; *OPC?')
            self.instr.query(':CONF:GEN:CONN:STAT ON; *OPC?')
            self.instr.query('CONF:GEN:CONT:STAT ON; *OPC?')
            self.instr.query('CONF:GEN:RFO:STAT ON; *OPC?')
            self.instr.query('CONF:GEN:POW:LEV:STAT ON; *OPC?')
            self.instr.query(f':SENS:FREQ:CENT {freq_str}; *OPC? ')
            self.instr.query('CONF:GEN:SETT:UPD:RF; *OPC?')
            self.instr.query('*OPC?')
            self.instr.query('CONF:SETT:RF; *OPC?')
            self.instr.query('CONF:SETT:NR5G; *OPC?')
            self.instr.query('CONF:GEN:RFO:STAT ON; *OPC?')
            self.instr.query('CONF:GEN:CONT:STAT OFF; *OPC?')

            self.instr.query(':SENS:ADJ:LEV; *OPC?')
            self.instr.query(':SENS:ADJ:EVM; *OPC?')
            self.instr.query(':DISP:WIND3:SUBW1:TRAC:Y:SCAL:AUTO ALL; *OPC?')
            self.instr.query('INIT:CONT OFF; *OPC?')
            self.instr.query('INIT:IMM; *OPC?')
            self.instr.query('INIT:IMM; *OPC?')

            '''
            self.instr.write('INST:SEL "5G NR"; *OPC')
            self.instr.write(':CONF:GEN:CONN:STAT ON')
            self.instr.write('CONF:GEN:CONT:STAT ON')
            self.instr.write('CONF:GEN:RFO:STAT ON')
            self.instr.write('CONF:GEN:POW:LEV:STAT ON')
            self.instr.write(f':SENS:FREQ:CENT {freq_str}')
            self.instr.write('CONF:GEN:SETT:UPD:RF; *OPC')
            self.instr.write('*OPC')
            self.instr.write('CONF:SETT:RF')
            self.instr.write('CONF:SETT:NR5G')
            self.instr.write('CONF:GEN:RFO:STAT ON')
            self.instr.write('CONF:GEN:CONT:STAT OFF')
            self.instr.write(':SENS:ADJ:LEV; *OPC')
            self.instr.write(':SENS:ADJ:EVM; *OPC')
            self.instr.write(':DISP:WIND3:SUBW1:TRAC:Y:SCAL:AUTO ALL')
            self.instr.write('INIT:CONT OFF; *OPC')
            self.instr.write('INIT:IMM; *OPC')
            self.instr.write('INIT:IMM; *OPC')
            '''

            start_time = time()
            vsa_power = self.queryFloat('FETC:CC1:ISRC:FRAM:SUMM:POW:AVERage?')
            evm = self.queryFloat('FETC:CC1:ISRC:FRAM:SUMM:EVM:ALL:AVERage?')
            evm_time = time() - start_time
            start_time = time()
            self.instr.write('CONF:NR5G:MEAS ACLR')
            self.instr.write('INIT:IMM;*WAI')
            aclr_list = self.instr.query('CALC:MARK:FUNC:POW:RES? ACP')
            chan_pow = float(aclr_list.split(',')[0])
            adj_chan_lower = float(aclr_list.split(',')[1])
            adj_chan_upper = float(aclr_list.split(',')[2])
            aclr_time = time() - start_time
            self.instr.write('CONF:NR5G:MEAS EVM')
            print(evm)
            #  self.instr.query('INIT:CONT OFF; *OPC?')
            logger.info(f"EVM measurement: Power={vsa_power}, EVM={evm}, Time={evm_time}")
            logger.info(f"ACLR measurement: Channel Power={chan_pow}, Lower Adjacent={adj_chan_lower}, Upper Adjacent={adj_chan_upper}, Time={aclr_time}")
            return vsa_power, evm, evm_time, chan_pow, adj_chan_lower, adj_chan_upper, aclr_time
        except Exception as e:
            logger.error(f"EVM measurement failed: {str(e)}")
            raise

    def measure_evm_K18(self, freq_str, vsa_offset, ref_lev):
        try:
            #  self.set_ref_level(ref_lev)
            self.instr.query('INST:SEL "5G NR"; *OPC?')
            self.instr.query(':SENS:ADJ:LEV; *OPC?')
            self.instr.query(':SENS:ADJ:EVM; *OPC?')
            self.instr.query(':DISP:WIND3:SUBW1:TRAC:Y:SCAL:AUTO ALL; *OPC?')
            '''
            self.instr.query('CONF:GEN:CONT:STAT ON; *OPC?')
            self.instr.query('CONF:GEN:RFO:STAT OFF; *OPC?')
            self.instr.query('CONF:GEN:POW:LEV:STAT OFF; *OPC?')
            self.instr.query('CONF:SETT:RF; *OPC?')
            self.instr.query('CONF:SETT:NR5G; *OPC?')
            self.instr.query('CONF:GEN:RFO:STAT ON; *OPC?')
            self.instr.query('CONF:GEN:CONT:STAT OFF; *OPC?')
            self.instr.query(':SENS:ADJ:LEV; *OPC?')
            self.instr.query(':SENS:ADJ:EVM; *OPC?')
            self.instr.query(':DISP:WIND3:SUBW1:TRAC:Y:SCAL:AUTO ALL; *OPC?')
            self.instr.query('INIT:CONT OFF; *OPC?')
            '''
            self.instr.query('INIT:IMM; *OPC?')
            start_time = time()
            vsa_power = self.queryFloat('FETC:CC1:ISRC:FRAM:SUMM:POW:AVERage?')
            evm = self.queryFloat('FETC:CC1:ISRC:FRAM:SUMM:EVM:ALL:AVERage?')
            evm_time = time() - start_time
            start_time = time()
            self.instr.write('CONF:NR5G:MEAS ACLR')
            self.instr.write('INIT:IMM;*WAI')
            aclr_list = self.instr.query('CALC:MARK:FUNC:POW:RES? ACP')
            chan_pow = float(aclr_list.split(',')[0])
            adj_chan_lower = float(aclr_list.split(',')[1])
            adj_chan_upper = float(aclr_list.split(',')[2])
            aclr_time = time() - start_time
            self.instr.write('CONF:NR5G:MEAS EVM')
            #  self.instr.query('INIT:CONT OFF; *OPC?')
            logger.info(f"K18 EVM measurement: Power={vsa_power}, EVM={evm}, Time={evm_time}")
            logger.info(f"K18 ACLR measurement: Channel Power={chan_pow}, Lower Adjacent={adj_chan_lower}, Upper Adjacent={adj_chan_upper}, Time={aclr_time}")
            return vsa_power, evm, evm_time, chan_pow, adj_chan_lower, adj_chan_upper, aclr_time
        except Exception as e:
            logger.error(f"K18 EVM measurement failed: {str(e)}")
            raise

    def K18_power_servo(self, Target_output, max_iterations):
        try:

            self.instr.query(':SENS:PSER:STAT ON; *OPC?')
            self.instr.query(f':SENS:PSER:TARG:VAL {Target_output}; *OPC?')
            self.instr.query(f':SENS:PSER:MAX:ITER {max_iterations}; *OPC?')
            self.instr.query(':SENS:PSER:GLC RFL; *OPC?')
            self.instr.query(':SENS:PSER:STAR; *OPC?')
            self.instr.query('INIT:IMM; *OPC?')
            '''
            self.instr.write(':SENS:PSER:STAT ON')
            self.instr.write(f':SENS:PSER:TARG:VAL {Target_output}')
            self.instr.write(f':SENS:PSER:MAX:ITER {max_iterations}')
            self.instr.write(':SENS:PSER:GLC RFL')
            self.instr.write(':SENS:PSER:STAR')
            self.instr.write('INIT:IMM; *OPC')
            '''

            print(self.instr.query(':FETC:POW:OUTP:CURR:RES?'))
        except Exception as e:
            logger.error(f"K18 power servo failed: {str(e)}")
            raise

    def perform_iterative_dpdxxx(self, freq_str, vsa_offset, ref_lev, iterations=5):
        try:
            # Initial configuration
            self.instr.query(':INST:CRE:NEW AMPL, "Amplifier"; *OPC?')
            self.instr.query('CONF:GEN:CONT:STAT ON; *OPC?')
            self.instr.query('CONF:SETT; *OPC?')
            self.instr.query(':CONF:REFS:CGW:READ; *OPC?')
            self.instr.query(':SENS:ADJ:LEV; *OPC?')
            self.instr.query(':TRIG:SEQ:SOUR EXT; *OPC?')
            self.instr.query('INIT:CONT OFF; *OPC?')
            self.instr.query('INIT:IMM; *OPC?')

            # Single DPD
            self.instr.query('CONF:DPD:SHAP:MODE POLY; *OPC?')
            self.instr.query(':CONF:DPD:TRAD 100; *OPC?')
            self.instr.query('INIT:CONT OFF; *OPC?')
            self.instr.query('INIT:IMM; *OPC?')
            start_time = time()
            self.instr.query(':CONF:DPD:UPD; *OPC?')
            self.instr.query('INIT:IMM; *OPC?')
            self.instr.query('CONF:DPD:AMAM:STAT ON; *OPC?')
            self.instr.query('CONF:DPD:AMPM:STAT ON; *OPC?')
            self.instr.query('INIT:IMM; *OPC?')
            self.K18_power_servo(ref_lev, max_iterations=iterations)

            self.instr.query('INST:SEL "5G NR"; *OPC?')
            self.instr.query(':SENS:ADJ:LEV; *OPC?')
            self.instr.query(':SENS:ADJ:EVM; *OPC?')
            self.instr.query(':DISP:WIND3:SUBW1:TRAC:Y:SCAL:AUTO ALL; *OPC?')
            self.instr.query('INIT:IMM; *OPC?')
            start_time = time()
            vsa_power = self.queryFloat('FETC:CC1:ISRC:FRAM:SUMM:POW:AVERage?')
            evm = self.queryFloat('FETC:CC1:ISRC:FRAM:SUMM:EVM:ALL:AVERage?')
            evm_time = time() - start_time
            start_time = time()
            self.instr.write('CONF:NR5G:MEAS ACLR')
            self.instr.write('INIT:IMM;*WAI')
            aclr_list = self.instr.query('CALC:MARK:FUNC:POW:RES? ACP')
            chan_pow = float(aclr_list.split(',')[0])
            adj_chan_lower = float(aclr_list.split(',')[1])
            adj_chan_upper = float(aclr_list.split(',')[2])
            aclr_time = time() - start_time
            self.instr.write('CONF:NR5G:MEAS EVM')
            single_dpd_power, single_dpd_evm, single_dpd_evm_time, single_dpd_chan_pow, single_dpd_adj_chan_lower, single_dpd_adj_chan_upper, single_dpd_aclr_time = self.measure_evm_K18(freq_str, vsa_offset, ref_lev)
            single_dpd_time = time() - start_time

            # DDPD
            self.instr.query('INST:SEL "Amplifier"; *OPC?')
            self.instr.query('CONF:GEN:CONT:STAT ON; *OPC?')
            self.instr.query('CONF:SETT; *OPC?')
            self.instr.query(':CONF:REFS:CGW:READ; *OPC?')
            self.instr.query('CONF:DPD:AMPM:STAT OFF; *OPC?')
            self.instr.query('CONF:DPD:AMAM:STAT OFF; *OPC?')
            self.instr.query('CONF:DDPD:STAT ON; *OPC?')
            self.instr.query('CONF:DDPD:TRAD 100; *OPC?')
            self.instr.query(f':CONF:DDPD:COUN {iterations}; *OPC?')
            start_time = time()
            self.instr.query(':CONF:DDPD:STAR; *OPC?')
            self.K18_power_servo(ref_lev, max_iterations=iterations)
            ddpd_power, ddpd_evm, ddpd_evm_time, ddpd_chan_pow, ddpd_adj_chan_lower, ddpd_adj_chan_upper, ddpd_aclr_time = self.measure_evm_K18(freq_str, vsa_offset, ref_lev)
            ddpd_time = time() - start_time

            # GMP
            self.write_command_opc('INST:SEL "Amplifier"')
            self.instr.query('CONF:GEN:CONT:STAT ON; *OPC?')
            self.instr.query('CONF:SETT; *OPC?')
            self.instr.query(':CONF:REFS:CGW:READ; *OPC?')
            start_time = time()
            self.instr.write('CONF:MDPD:STAT ON')
            self.instr.write('CONF:GMP:LAG:ORD:XTER 1')
            self.instr.write('CALC:MDPD:MOD;*WAI')
            self.instr.write('CALC:MDPD:MOD;*WAI')
            self.instr.write('CONF:MDPD:WAV:SEL MDPD;*WAI')
            self.K18_power_servo(ref_lev, max_iterations=iterations)
            gmp_power, gmp_evm, gmp_evm_time, gmp_chan_pow, gmp_adj_chan_lower, gmp_adj_chan_upper, gmp_aclr_time = self.measure_evm_K18(freq_str, vsa_offset, ref_lev)
            gmp_time = time() - start_time
            self.write_command_opc('INST:DEL "Amplifier"')
            logger.info(f"Single DPD: EVM={single_dpd_evm}, EVM Time={single_dpd_evm_time}, Total Time={single_dpd_time}, Channel Power={single_dpd_chan_pow}, Lower ACLR={single_dpd_adj_chan_lower}, Upper ACLR={single_dpd_adj_chan_upper}, ACLR Time={single_dpd_aclr_time}")
            logger.info(f"DDPD: EVM={ddpd_evm}, EVM Time={ddpd_evm_time}, Total Time={ddpd_time}, Channel Power={ddpd_chan_pow}, Lower ACLR={ddpd_adj_chan_lower}, Upper ACLR={ddpd_adj_chan_upper}, ACLR Time={ddpd_aclr_time}")
            logger.info(f"GMP: EVM={gmp_evm}, EVM Time={gmp_evm_time}, Total Time={gmp_time}, Channel Power={gmp_chan_pow}, Lower ACLR={gmp_adj_chan_lower}, Upper ACLR={gmp_adj_chan_upper}, ACLR Time={gmp_aclr_time}")

            return (
                single_dpd_evm, single_dpd_time, single_dpd_chan_pow, single_dpd_adj_chan_lower, single_dpd_adj_chan_upper, single_dpd_aclr_time,
                ddpd_evm, ddpd_time, ddpd_chan_pow, ddpd_adj_chan_lower, ddpd_adj_chan_upper, ddpd_aclr_time,
                gmp_evm, gmp_time, gmp_chan_pow, gmp_adj_chan_lower, gmp_adj_chan_upper, gmp_aclr_time
            )
        except Exception as e:
            logger.error(f"DPD measurement failed: {str(e)}")
            raise

    def perform_single_dpd(self, freq_str, vsa_offset, ref_lev, Target_output, iterations=5):
        try:
            # Initial configuration

            self.instr.query(':INST:CRE:NEW AMPL, "Amplifier"; *OPC?')
            self.instr.query('CONF:GEN:IPC:ADDR "192.168.200.10"; *OPC?')
            self.instr.query('CONF:GEN:CONN:STAT ON;*WAI; *OPC?')
            self.instr.query('CONF:GEN:CONT:STAT ON; *OPC?')
            self.instr.query('CONF:SETT; *OPC?')
            self.instr.query(':CONF:REFS:CGW:READ; *OPC?')

            self.instr.query(':SENS:ADJ:LEV; *OPC?')
            self.instr.query(':TRIG:SEQ:SOUR EXT; *OPC?')
            self.instr.query('INIT:CONT OFF; *OPC?')
            self.instr.query('INIT:IMM; *OPC?')
            
            '''
            self.instr.query(':INST:CRE:NEW AMPL, "Amplifier"; *OPC?')
            self.instr.write('CONF:GEN:IPC:ADDR "192.168.200.10"')
            self.instr.write('CONF:GEN:CONN:STAT ON')
            self.instr.write('CONF:GEN:CONT:STAT ON')
            self.instr.write('CONF:SETT')
            self.instr.write(':CONF:REFS:CGW:READ; *OPC')
            
            self.instr.write(':SENS:ADJ:LEV; *OPC')
            self.instr.write(':TRIG:SEQ:SOUR EXT')
            self.instr.write('INIT:CONT OFF')
            self.instr.write('INIT:IMM; *OPC')
            '''

            # Single DPD
            self.instr.query('CONF:DPD:SHAP:MODE POLY; *OPC?')
            self.instr.query(':CONF:DPD:TRAD 100; *OPC?')
            #  self.instr.query('INIT:CONT OFF; *OPC?')
            #  self.instr.query('INIT:IMM; *OPC?')
            start_time = time()
            self.instr.query(':CONF:DPD:UPD; *OPC?')
            #  self.instr.query('INIT:IMM; *OPC?')
            self.instr.query('CONF:DPD:AMAM:STAT ON; *OPC?')
            self.instr.query('CONF:DPD:AMPM:STAT ON; *OPC?')
            #  self.instr.query('INIT:IMM; *OPC?')
            self.K18_power_servo(Target_output, max_iterations=iterations)

            self.instr.query('INST:SEL "5G NR"; *OPC?')
            self.instr.query(':SENS:ADJ:LEV; *OPC?')
            self.instr.query(':SENS:ADJ:EVM; *OPC?')
            self.instr.query(':DISP:WIND3:SUBW1:TRAC:Y:SCAL:AUTO ALL; *OPC?')
            self.instr.query('INIT:IMM; *OPC?')
            start_time = time()
            single_dpd_power = self.queryFloat('FETC:CC1:ISRC:FRAM:SUMM:POW:AVERage?')
            single_dpd_evm = self.queryFloat('FETC:CC1:ISRC:FRAM:SUMM:EVM:ALL:AVERage?')
            single_dpd_evm_time = time() - start_time
            start_time = time()
            self.instr.query('CONF:NR5G:MEAS ACLR; *OPC?')
            self.instr.query('INIT:IMM;*OPC?')
            aclr_list = self.instr.query('CALC:MARK:FUNC:POW:RES? ACP')
            single_dpd_chan_pow = float(aclr_list.split(',')[0])
            single_dpd_adj_chan_lower = float(aclr_list.split(',')[1])
            single_dpd_adj_chan_upper = float(aclr_list.split(',')[2])
            single_dpd_aclr_time = time() - start_time
            self.instr.write('CONF:NR5G:MEAS EVM')
            print(single_dpd_evm)
            logger.info(f"Single DPD EVM measurement: Power={single_dpd_power}, EVM={single_dpd_evm}, Time={single_dpd_evm_time}")
            logger.info(
                f"Single DPD ACLR measurement: Channel Power={single_dpd_chan_pow}, Lower Adjacent={single_dpd_adj_chan_lower}, Upper Adjacent={single_dpd_adj_chan_upper}, Time={single_dpd_aclr_time}")
            return(single_dpd_power, single_dpd_evm, single_dpd_evm_time, single_dpd_chan_pow, single_dpd_adj_chan_lower,
             single_dpd_adj_chan_upper, single_dpd_aclr_time)
        except Exception as e:
            logger.error(f"Single DPD EVM measurement failed: {str(e)}")
            raise

    def perform_iterative_dpd(self, freq_str, vsa_offset, ref_lev, Target_output, dpd_iterations=5, iterations=5):
        try:
            # Initial configuration
            #  self.instr.query(':INST:CRE:NEW AMPL, "Amplifier"; *OPC?')
            self.write_command_opc('INST:SEL "Amplifier"')
            #  self.instr.query('CONF:GEN:CONT:STAT ON; *OPC?')
            #  self.instr.query('CONF:SETT; *OPC?')
            #  self.instr.query(':CONF:REFS:CGW:READ; *OPC?')
            #  self.instr.query(':SENS:ADJ:LEV; *OPC?')
            #  self.instr.query(':TRIG:SEQ:SOUR EXT; *OPC?')
            #  self.instr.query('INIT:CONT OFF; *OPC?')
            self.instr.query('CONF:DDPD:STAT ON; *OPC?')
            self.instr.query('CONF:DDPD:TRAD 100; *OPC?')
            self.instr.query(f':CONF:DDPD:COUN {dpd_iterations}; *OPC?')
            #  self.instr.query('INIT:IMM; *OPC?')
            self.instr.query(':CONF:DDPD:STAR; *OPC?')
            #  self.K18_power_servo(Target_output=10, max_iterations=iterations)
            self.K18_power_servo(Target_output, max_iterations=iterations)
            self.instr.query('INST:SEL "5G NR"; *OPC?')
            self.instr.query(':SENS:ADJ:LEV; *OPC?')
            self.instr.query(':SENS:ADJ:EVM; *OPC?')
            self.instr.query(':DISP:WIND3:SUBW1:TRAC:Y:SCAL:AUTO ALL; *OPC?')
            self.instr.query('INIT:IMM; *OPC?')
            #   self.instr.query('INIT:IMM; *OPC?')
            #   self.instr.query('INIT:IMM; *OPC?')
            start_time = time()
            ddpd_power = self.queryFloat('FETC:CC1:ISRC:FRAM:SUMM:POW:AVERage?')
            ddpd_evm = self.queryFloat('FETC:CC1:ISRC:FRAM:SUMM:EVM:ALL:AVERage?')
            ddpd_evm_time = time() - start_time
            start_time = time()
            self.instr.write('CONF:NR5G:MEAS ACLR')
            self.instr.write('INIT:IMM;*WAI')
            aclr_list = self.instr.query('CALC:MARK:FUNC:POW:RES? ACP')
            ddpd_chan_pow = float(aclr_list.split(',')[0])
            ddpd_adj_chan_lower = float(aclr_list.split(',')[1])
            ddpd_adj_chan_upper = float(aclr_list.split(',')[2])
            ddpd_aclr_time = time() - start_time
            ddpd_time = time() - start_time
            self.instr.write('CONF:NR5G:MEAS EVM')
            print(ddpd_evm)
            logger.info(f"Single DPD EVM measurement: Power={ddpd_power}, EVM={ddpd_evm}, Time={ddpd_evm_time}")
            logger.info(
                f"Single DPD ACLR measurement: Channel Power={ddpd_chan_pow}, Lower Adjacent={ddpd_adj_chan_lower}, Upper Adjacent={ddpd_adj_chan_upper}, Time={ddpd_aclr_time}")
            return (ddpd_power, ddpd_evm, ddpd_evm_time, ddpd_chan_pow, ddpd_adj_chan_lower, ddpd_adj_chan_upper, ddpd_aclr_time)
        except Exception as e:
            logger.error(f"Single DPD EVM measurement failed: {str(e)}")
            raise

    def perform_gmp_dpd(self, freq_str, vsa_offset, ref_lev, Target_output, dpd_iterations=5, iterations=5):
        try:
            # Initial configuration
            #  self.instr.query(':INST:CRE:NEW AMPL, "Amplifier"; *OPC?')
            self.write_command_opc('INST:SEL "Amplifier"')
            self.instr.query('CONF:DDPD:STAT ON; *OPC?')
            self.instr.query('CONF:DDPD:TRAD 100; *OPC?')
            self.instr.query(f':CONF:DDPD:COUN {dpd_iterations}; *OPC?')
            self.instr.query(':CONF:DDPD:STAR; *OPC?')
            #  self.instr.query('CONF:GEN:CONT:STAT ON; *OPC?')
            #  self.instr.query('CONF:SETT; *OPC?')
            #  self.instr.query(':CONF:REFS:CGW:READ; *OPC?')
            #  self.instr.query(':SENS:ADJ:LEV; *OPC?')
            #  self.instr.query(':TRIG:SEQ:SOUR EXT; *OPC?')
            #  self.instr.query('INIT:CONT OFF; *OPC?')
            #  self.instr.query('INIT:IMM; *OPC?')

            self.instr.query('CONF:MDPD:STAT ON; *OPC?')
            #  self.instr.write('CONF:GMP:LAG:ORD:XTER 1')
            self.instr.query('CALC:MDPD:MOD;*OPC?')
            self.instr.query('CONF:GMP:LAG:ORD:XTER 1;*OPC?')
            self.instr.query('CONF:GMP:LEAD:ORD:XTER 1;*OPC?')
            self.instr.query('CONF:MDPD:ITER 5;*OPC?')
            self.instr.query(':CALC:MDPD:MOD;*OPC?')
            self.instr.query(':CONF:MDPD:WAV:UPD;*OPC?')
            self.instr.query('CONF:MDPD:WAV:SEL MDPD;*OPC?')
            '''
            self.instr.query('CONF:MDPD:COEF:SEL MOD;*OPC?')
            self.instr.query('CONF:MDPD:WAV:UPD;*OPC?')
            self.instr.query('CONF:MDPD:WAV:SEL MDPD;*OPC?')
            '''
            self.K18_power_servo(Target_output, max_iterations=iterations)
            self.instr.query('INST:SEL "5G NR"; *OPC?')
            self.instr.query(':SENS:ADJ:LEV; *OPC?')
            self.instr.query(':SENS:ADJ:EVM; *OPC?')
            self.instr.query(':DISP:WIND3:SUBW1:TRAC:Y:SCAL:AUTO ALL; *OPC?')
            self.instr.query('INIT:IMM; *OPC?')
            start_time = time()
            gmp_power = self.queryFloat('FETC:CC1:ISRC:FRAM:SUMM:POW:AVERage?')
            gmp_evm = self.queryFloat('FETC:CC1:ISRC:FRAM:SUMM:EVM:ALL:AVERage?')
            gmp_evm_time = time() - start_time
            start_time = time()
            self.instr.write('CONF:NR5G:MEAS ACLR')
            self.instr.write('INIT:IMM;*WAI')
            aclr_list = self.instr.query('CALC:MARK:FUNC:POW:RES? ACP')
            gmp_chan_pow = float(aclr_list.split(',')[0])
            gmp_adj_chan_lower = float(aclr_list.split(',')[1])
            gmp_adj_chan_upper = float(aclr_list.split(',')[2])
            gmp_aclr_time = time() - start_time
            gmp_time = time() - start_time
            self.instr.query('CONF:NR5G:MEAS EVM; *OPC?')
            print(gmp_evm)
            self.instr.query('CONF:MDPD:WAV:SEL REF;*OPC?')
            self.instr.query('INST:DEL "Amplifier"; *OPC?')
            logger.info(f"Single DPD EVM measurement: Power={gmp_power}, EVM={gmp_evm}, Time={gmp_evm_time}")
            logger.info(
                f"Single DPD ACLR measurement: Channel Power={gmp_chan_pow}, Lower Adjacent={gmp_adj_chan_lower}, Upper Adjacent={gmp_adj_chan_upper}, Time={gmp_aclr_time}")
            return (gmp_power, gmp_evm, gmp_evm_time, gmp_chan_pow, gmp_adj_chan_lower, gmp_adj_chan_upper,
                    gmp_aclr_time)
        except Exception as e:
            logger.error(f"Single DPD EVM measurement failed: {str(e)}")
            raise

    def close(self):
        try:
            self.instr.close()
            logger.info("Socket closed")
        except Exception as e:
            logger.error(f"Error closing VSA socket: {str(e)}")
            raise