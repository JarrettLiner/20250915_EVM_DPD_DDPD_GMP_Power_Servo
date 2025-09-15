readme_content = """# RF DPD Sweep Measurement Project

## Overview
This project provides Python scripts to control RF instruments (Vector Signal Generator, Vector Signal Analyzer, and NRX Power Meter) to perform frequency sweeps, apply Digital Pre-Distortion (DPD) techniques (Single, Iterative, GMP), and stabilize output power using external (NRX-based) and internal (K18 VSA-based) power servo methods.  

Test parameters and execution flags are defined in a JSON configuration file (`config/test_inputs.json`). Results are saved in Excel (`results/sweep_measurements.xlsx`) with a separate statistics sheet for quick analysis.

---

## Project Structure

DPD_Sweep_Project/
├── src/
│ ├── instruments/
│ │ ├── iSocket.py # Custom socket communication
│ │ ├── bench.py # Bench config / instrument sessions
│ ├── measurements/
│ │ ├── main.py # Main sweep + DPD routines
│ │ ├── vsa.py # Vector Signal Analyzer driver
│ │ ├── vsg.py # Vector Signal Generator driver
│ │ ├── power_meter.py # NRX Power Meter driver
│ │ ├── power_servo.py # Power servo control logic
├── config/
│ ├── test_inputs.json # Test parameters and flags
│ ├── combined_cal_data.xlsx # Calibration offsets
├── logs/
├── results/
│ ├── sweep_measurements.xlsx
├── requirements.txt
├── setup.bat
├── .gitignore
└── README.md

yaml
Copy code

---

## Setup

### Prerequisites
- Python 3.9 or higher  
- Network-accessible RF instruments (VSG, VSA, NRX Power Meter)

### Install Dependencies
bash
pip install -r requirements.txt
Configure Instruments
Update src/instruments/bench.py with instrument IP addresses:

ini
Copy code
[Settings]
VSA_IP = 192.168.200.20
VSG_IP = 192.168.200.10
PM_IP  = 192.168.200.40
Configure Test Parameters
Edit config/test_inputs.json to define sweep ranges and test flags. Example:

json
Copy code
{
  "Sweep_Measurement": {
    "range": {
      "start_ghz": 3.3,
      "stop_ghz": 3.8,
      "step_mhz": 20,
      "power_dbm": 10.0,
      "tolerence_db": 0.05,
      "expected_gain_db": 30.0,
      "ddpd_iterations": 5,
      "servo_iterations": 5,
      "use_power_servo": true,
      "use_K18_power_servo": true
    }
  }
}
Execution Flow
main.py:

mathematica
Copy code
├─ Initialize instruments (VSG, VSA, Power Meter)
├─ Apply calibration offsets (combined_cal_data.xlsx)
├─ Load test parameters (test_inputs.json)
├─ For each frequency in sweep:
│   ├─ Baseline Measurement (Power, EVM, ACLR)
│   ├─ Single DPD → Run power servo → Measure
│   ├─ Iterative DPD → Run servo loops → Measure
│   ├─ GMP DPD → Sync waveform → Run servo → Measure
├─ Log results to console, logs/, and results/sweep_measurements.xlsx
Usage
bash
Copy code
python src/measurements/main.py
Supported Measurements
Baseline Measurement: Power, EVM, ACLR before DPD

Single DPD: Apply DPD once and measure improvements

Iterative DPD: Multiple DPD iterations (user-defined)

GMP DPD: Generalized Memory Polynomial DPD model

Servo Loops
NRX Power Meter (external)

VSA K18 Power Servo (internal)

Output
results/sweep_measurements.xlsx

Measurements sheet: per-frequency results

Statistics sheet: min, max, mean (highlighted)

Requirements
Python 3.9+

Libraries:

numpy>=1.24.0

pandas>=2.0.0

openpyxl>=3.1.0

Custom iSocket in src/instruments/

Notes
Calibration data must cover sweep range frequencies.

Frequencies in test_inputs.json are rounded to match calibration keys.

Mean values are highlighted in the Excel file.

Extendable: add new DPD models or measurement modes in vsa.py.

Contributing
Fork the repo

Create a branch (git checkout -b feature/your-feature)

Commit changes (git commit -m 'Add feature')

Push (git push origin feature/your-feature)

Open a pull request

License
[Specify license, e.g., MIT License, or "Proprietary"]
