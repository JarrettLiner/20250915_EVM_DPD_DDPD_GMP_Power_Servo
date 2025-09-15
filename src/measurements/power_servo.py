# ==============================================================
# File: power_servo.py
# Description:
#   Power servo module for:
#     - Adjusting VSG input power
#     - Iteratively driving DUT output power to target level
#     - Using NRX Power Meter feedback
#     - Supporting servo loop with tolerance + iteration limits
# ==============================================================

import logging
from time import time

# --------------------------------------------------------------
# Logging Setup
# --------------------------------------------------------------
logger = logging.getLogger(__name__)


class PowerServo:
    # ----------------------------------------------------------
    # Initialization
    # ----------------------------------------------------------
    def __init__(self, vsg, pm, vsa, max_iterations=10, tolerance=0.1):
        """
        Initialize PowerServo.

        Args:
            vsg: VSG instance for setting input power.
            pm: PowerMeter instance for measuring DUT power.
            vsa: VSA instance (used to update reference level).
            max_iterations (int): Max allowed servo iterations.
            tolerance (float): Power tolerance in dB for convergence.
        """
        self.vsg = vsg
        self.pm = pm
        self.vsa = vsa
        self.max_iterations = max_iterations
        self.tolerance = tolerance
        self.logger = logging.getLogger(__name__)

    # ----------------------------------------------------------
    # Servo loop
    # ----------------------------------------------------------
    def servo_power(self, freq_ghz, target_output, expected_gain):
        """
        Run servo loop to adjust input power until DUT output reaches target.

        Args:
            freq_ghz (float): Frequency in GHz (for logging).
            target_output (float): Desired output power (dBm).
            expected_gain (float): Expected DUT gain (dB).

        Returns:
            tuple: (servo_iterations, servo_settle_time)
        """
        # Measure initial DUT gain
        expected_gain = self.pm.measure()[1] - self.pm.measure()[0]
        self.logger.info(f"Measured gain in dB: {expected_gain:.3f}")

        # Calculate initial input power estimate
        initial_pwr = target_output - expected_gain
        self.vsg.set_power(initial_pwr)

        servo_start_time = time()
        servo_iterations = 0
        servo_settle_time = None

        # Iteratively adjust input power
        for i in range(self.max_iterations):
            _, current_output = self.pm.measure()
            servo_iterations = i + 1

            # Check convergence
            if abs(current_output - target_output) < self.tolerance:
                servo_settle_time = round(time() - servo_start_time, 3)
                self.logger.info(
                    f"Servo converged after {servo_iterations} iterations "
                    f"in {servo_settle_time} s at {freq_ghz} GHz"
                )
                break

            # Adjust input power based on error
            adjustment = target_output - current_output
            initial_pwr += adjustment
            self.vsg.set_power(initial_pwr)
        else:
            # Did not converge
            servo_settle_time = round(time() - servo_start_time, 3)
            self.logger.warning(
                f"Servo did not converge within {self.max_iterations} iterations "
                f"at {freq_ghz} GHz (Time: {servo_settle_time} s)"
            )

        # Final log + return
        self.logger.info(f"Servo Iterations: {servo_iterations}, Servo Time: {servo_settle_time}")
        return servo_iterations, servo_settle_time
