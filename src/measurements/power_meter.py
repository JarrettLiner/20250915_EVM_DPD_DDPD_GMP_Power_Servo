# ==============================================================
# File: power_meter.py
# Description:
#   Power Meter control module for:
#     - Initialization of NRX power meter
#     - Frequency + offset configuration
#     - Measuring input/output power
#     - Sending commands with OPC sync
#     - Cleanup and socket close
# ==============================================================

import logging
from time import time
from src.instruments.bench import bench

# --------------------------------------------------------------
# Logging Setup
# --------------------------------------------------------------
logger = logging.getLogger(__name__)


class PowerMeter:
    # ----------------------------------------------------------
    # Initialization
    # ----------------------------------------------------------
    def __init__(self, host="192.168.200.40", port=5025):
        """
        Initialize the NRX Power Meter.

        Args:
            host (str): IP address of the power meter.
            port (int): TCP/IP port number for communication.
        """
        self.bench = bench()
        start_time = time()
        try:
            # Open socket session to NRX instrument
            self.instr = self.bench.NRX_start()
            self.setup_time = time() - start_time
            logger.info(f"PowerMeter (NRX) initialized in {self.setup_time:.3f}s")
        except Exception as e:
            logger.error(f"PowerMeter initialization failed: {str(e)}")
            raise

    # ----------------------------------------------------------
    # Configuration
    # ----------------------------------------------------------
    def configure(self, freq, input_offset, output_offset):
        """
        Configure NRX Power Meter for test:
          - Set frequency for both channels
          - Apply input/output offsets

        Args:
            freq (float): Frequency in Hz.
            input_offset (float): Input power offset in dB.
            output_offset (float): Output power offset in dB.
        """
        try:
            command = (
                f':SENS1:FREQ {freq};'
                f':SENS2:FREQ {freq};'
                f':CALCulate1:CHANnel1:CORRection:OFFSet:MAGNitude {input_offset};'
                f':CALCulate1:CHANnel1:CORRection:OFFSet:STATe ON;'
                f':CALCulate2:CHANnel1:CORRection:OFFSet:MAGNitude {output_offset};'
                f':CALCulate2:CHANnel1:CORRection:OFFSet:STATe ON;'
                f'*OPC?'
            )
            self.instr.query(command)
            logger.info(f"PowerMeter configured for {freq} Hz with offsets {input_offset}, {output_offset}")
        except Exception as e:
            logger.error(f"PowerMeter configuration failed: {str(e)}")
            raise

    # ----------------------------------------------------------
    # Measurement
    # ----------------------------------------------------------
    def measure(self):
        """
        Measure input and output power.

        Returns:
            tuple: (input_power, output_power) in dBm.
        """
        try:
            input_power = self.instr.queryFloat(':MEAS1?')
            output_power = self.instr.queryFloat(':MEAS2?')
            self.instr.query('*OPC?')
            return input_power, output_power
        except Exception as e:
            logger.error(f"Power measurement failed: {str(e)}")
            raise

    # ----------------------------------------------------------
    # Write with OPC sync
    # ----------------------------------------------------------
    def write_command_opc(self, command: str) -> None:
        """
        Write a SCPI command to the PowerMeter with OPC synchronization.

        Args:
            command (str): SCPI command string.
        """
        try:
            self.instr.write('*ESE 1')   # Enable operation complete bit
            self.instr.write('*SRE 32')  # Enable service request for OPC
            self.instr.write(f'{command};*OPC')
            while (int(self.instr.query('*ESR?')) & 1) != 1:
                time.sleep(0.2)  # Poll ESR until OPC complete
            logger.info(f"Command '{command}' completed with OPC sync.")
        except Exception as e:
            logger.error(f"Error during OPC write: {str(e)}")
            raise

    # ----------------------------------------------------------
    # Cleanup
    # ----------------------------------------------------------
    def close(self):
        """
        Close the PowerMeter instrument session.
        """
        try:
            self.instr.sock.close()
            logger.info("PowerMeter socket closed")
        except Exception as e:
            logger.error(f"PowerMeter close failed: {str(e)}")
            raise
