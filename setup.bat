
@echo off
echo Setting up virtual environment...
python -m venv .venv
if %ERRORLEVEL% neq 0 (
    echo Failed to create virtual environment.
    pause
    exit /b 1
)
echo Activating virtual environment...
call .venv\Scripts\activate
if %ERRORLEVEL% neq 0 (
    echo Failed to activate virtual environment.
    pause
    exit /b 1
)
echo Upgrading pip...
pip install --upgrade pip
if %ERRORLEVEL% neq 0 (
    echo Failed to upgrade pip.
    pause
    exit /b 1
)
echo Installing dependencies...
pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo Failed to install dependencies.
    pause
    exit /b 1
)
echo Setup complete. Run 'python src/main.py' to start measurements.
python --version | findstr "3.8 3.9 3.10 3.11 3.12 3.13" || (
    echo Python 3.8+ required.
    pause
    exit /b 1
)
pause