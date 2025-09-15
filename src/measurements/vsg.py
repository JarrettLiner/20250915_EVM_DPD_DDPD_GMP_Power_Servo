# ==============================================================
# File: vsg.py
# Description:
#   Vector Signal Generator (VSG) control module for:
#     - Initialization and default waveform load
#     - Frequency + power configuration
#     - Output power adjustments
#     - Cleanup and socket close
# ==============================================================

import logging
from src.instruments.bench import bench
from time import time

# --------------------------------------------------------------
# Logging Setup
# --------------------------------------------------------------
logger = logging.getLogger(__name__)


class VSG:
    # ----------------------------------------------------------
    # Initialization
    # ----------------------------------------------------------
    def __init__(self):
        """
        Initialize the VSG instrument:
          - Connect via bench helper
          - Reset instrument
          - Load default 5G NR waveform configuration
          - Record initialization/setup time
        """
        start_time = time()
        logger.info("Initializing VSG")

        # Start instrument session (socket open)
        self.vsg = bench().VSG_start()

        # Reset instrument to known state
        self.vsg.query('*RST; *OPC?')
        self.vsg.query('*OPC?')  # Wait until reset complete

        # Load predefined 5G NR waveform setup file
        self.vsg.query(
            'SYSTem:RCL \'/var/user/Qorvo/NR5G_10MHz_UL_30kHzSCS_24QAM_24rb_0rbo.savrcltxt\' ;*OPC?'
        )

        # Track and log setup time
        self.setup_time = time() - start_time
        print(f"VSG setup time: {self.setup_time:.3f}s")
        print("This includes the time to load the .savrcltxt file")
        logger.info(f"VSG initialized in {self.setup_time:.3f}s")

    # ----------------------------------------------------------
    # Configuration
    # ----------------------------------------------------------
    def configure(self, freq, initial_power, vsg_offset):
        """
        Configure VSG for test:
          - Apply power offset
          - Set frequency
          - Set power level
          - Enable RF output

        Args:
            freq (float): Center frequency in Hz.
            initial_power (float): Initial power level in dBm.
            vsg_offset (float): Output power offset in dB.
        """
        # Apply output power offset
        self.vsg.write(f':SOUR1:POW:LEV:IMM:OFFS {vsg_offset:.3f}')

        # Set RF frequency
        self.vsg.query(f':SOUR1:FREQ:CW {freq}; *OPC?')

        # Set output power
        self.vsg.query(f':SOUR1:POW:LEV:IMM:AMPL {initial_power}; *OPC?')

        # Enable RF output
        self.vsg.query(':OUTP1:STAT 1; *OPC?')

    # ----------------------------------------------------------
    # Power adjustment
    # ----------------------------------------------------------
    def set_power(self, pwr):
        """
        Adjust VSG output power level.

        Args:
            pwr (float): Desired power level in dBm.
        """
        self.vsg.query(f':SOUR1:POW:LEV:IMM:AMPL {pwr}; *OPC?')

    # ----------------------------------------------------------
    # Cleanup
    # ----------------------------------------------------------
    def close(self):
        """
        Close the VSG instrument session and socket.
        """
        self.vsg.sock.close()
        logger.info("VSG socket closed")
