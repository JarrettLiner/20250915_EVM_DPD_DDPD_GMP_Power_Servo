"""iSocket module for RF instrument communication.

Provides socket-based communication with VSA and VSG instruments.
"""

import socket
import os
import logging
import time

class iSocket:
    """Class for socket communication with RF instruments."""

    def __init__(self):
        """Initialize socket and logging."""
        # Setup logging to logs/iSocket.log
        log_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'logs')
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, 'iSocket.log')
        logging.basicConfig(
            filename=log_path,
            level=logging.INFO,
            format='%(asctime)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.idn = "Unknown"  # Placeholder for instrument ID

    def open(self, ip, port):
        """Connect to instrument at specified IP and port.

        Args:
            ip (str): Instrument IP address.
            port (int): Port number (e.g., 5025 for SCPI).

        Returns:
            iSocket: Self for method chaining.
        """
        try:
            self.sock.connect((ip, port))
            self.logger.info(f"Connected to {ip}:{port}")
            # Query instrument ID (example)
            self.idn = self.query('*IDN?').strip()
            return self
        except Exception as e:
            self.logger.error(f"Connection failed to {ip}:{port}: {e}")
            raise

    def close(self):
        """Close the socket connection."""
        try:
            self.sock.close()
            self.logger.info("Socket closed")
        except Exception as e:
            self.logger.error(f"Failed to close socket: {e}")
            raise

    def query(self, cmd):
        """Send SCPI command and return response.

        Args:
            cmd (str): SCPI command to send.

        Returns:
            str: Instrument response.
        """
        try:
            self.logger.info(f"Query: {cmd}")
            self.sock.send(f"{cmd}\n".encode())
            response = self.sock.recv(1024).decode().strip()
            self.logger.info(f"Response: {response}")
            return response
        except Exception as e:
            self.logger.error(f"Query failed: {cmd}, Error: {e}")
            raise

    def write(self, cmd):
        """Send SCPI command without expecting a response.

        Args:
            cmd (str): SCPI command to send.
        """
        try:
            self.logger.info(f"Write: {cmd}")
            self.sock.send(f"{cmd}\n".encode())
        except Exception as e:
            self.logger.error(f"Write failed: {cmd}, Error: {e}")
            raise

    def write_command_opc(self, command: str) -> None:
        """Sends a SCPI command with OPC synchronization to ensure completion.

        Args:
            command (str): SCPI command to send (e.g., "*RST").

        Raises:
            RsInstrException: If the command or synchronization fails.

        Note:
            Uses polling with *ESR? to confirm completion; polling interval is fixed at 0.2s.
        """
        try:
            # Configure instrument for OPC monitoring
            self.write("*ESE 1")  # Enable Operation Complete bit in event status
            self.write("*SRE 32")  # Enable service request for OPC
            self.write(f"{command};*OPC")  # Send command with OPC flag
            # Poll Event Status Register until bit 0 (Operation Complete) is set
            while (int(self.query("*ESR?")) & 1) != 1:
                time.sleep(0.2)  # Wait briefly between polls
            self.logger.info(f"Command '{command}' completed with OPC synchronization.")
        except Exception as e:
            self.logger.error(f"Error during OPC write for command '{command}': {e}")
            raise

    def queryFloat(self, cmd):
        """Send SCPI command and return response as float.

        Args:
            cmd (str): SCPI command to send.

        Returns:
            float: Parsed response.
        """
        try:
            return float(self.query(cmd))
        except Exception as e:
            self.logger.error(f"QueryFloat failed: {cmd}, Error: {e}")
            raise

    def clear_error(self):
        """Clear instrument error queue."""
        self.logger.info("Clearing error queue")
        self.query(':SYST:ERR?')

    def __del__(self):
        """Close socket."""
        if self.sock:
            self.sock.close()
            self.logger.info("Socket closed")


if __name__ == '__main__':
    # Example usage
    sock = iSocket()
    sock.open('192.168.200.40', 5025)
    print(sock.idn)