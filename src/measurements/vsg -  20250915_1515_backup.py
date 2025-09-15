# ==============================================================
# File: vsg.py
# Description: Vector Signal Generator (VSG) control module for
#              configuring and managing VSG instrument settings
#              during frequency sweep and power measurements.
# ==============================================================

import logging
from src.instruments.bench import bench
from time import time

# --------------------------------------------------------------
# Logging Setup
# --------------------------------------------------------------
logger = logging.getLogger(__name__)


class VSG:
    def __init__(self):
        """
        Initialize the VSG instrument, reset it, and load default settings.
        Measures and logs the initialization time.
        """
        # Start timing for initialization
        start_time = time()
        logger.info("Initializing VSG")

        # Initialize VSG instrument using bench module
        self.vsg = bench().VSG_start()

        # Reset instrument and wait for operation completion
        self.vsg.query('*RST; *OPC?')
        self.vsg.query('*OPC?')  # Ensure reset is complete

        # Load predefined configuration for 5G NR waveform
        self.vsg.query('SYSTem:RCL \'/var/user/Qorvo/NR5G_10MHz_UL_30kHzSCS_24QAM_24rb_0rbo.savrcltxt\' ;*OPC?')

        # Log initialization time
        self.setup_time = time() - start_time
        print(f"VSG setup time: {self.setup_time:.3f}s")
        print("this includes the time to load the .savrcltxt file")
        logger.info(f"VSG initialized in {self.setup_time:.3f}s")

    def configure(self, freq, initial_power, vsg_offset):
        """
        Configure VSG with specified frequency, power, and offset.

        Args:
            freq (float): Center frequency in Hz.
            initial_power (float): Initial power level in dBm.
            vsg_offset (float): Power offset in dB.
        """
        # Set power offset
        self.vsg.write(f':SOUR1:POW:LEV:IMM:OFFS {vsg_offset:.3f}')

        # Set frequency and wait for completion
        self.vsg.query(f':SOUR1:FREQ:CW {freq}; *OPC?')

        # Set power level and wait for completion
        self.vsg.query(f':SOUR1:POW:LEV:IMM:AMPL {initial_power}; *OPC?')

        # Enable output
        self.vsg.query(':OUTP1:STAT 1; *OPC?')

    def set_power(self, pwr):
        """
        Set the VSG power level.

        Args:
            pwr (float): Power level in dBm.
        """
        # Set immediate power level and wait for completion
        self.vsg.query(f':SOUR1:POW:LEV:IMM:AMPL {pwr}; *OPC?')

    def close(self):
        """
        Close the VSG instrument connection.
        """
        # Close the socket connection
        self.vsg.sock.close()
        logger.info("VSG socket closed")