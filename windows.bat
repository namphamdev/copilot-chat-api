@echo off

:: Check if virtual environment exists, create if it doesn't
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

:: Activate virtual environment
call venv\Scripts\activate.bat

:: Install requirements if needed
pip install -r requirements.txt

:: Run the API
python api.py

:: Keep the window open if there's an error
if %ERRORLEVEL% NEQ 0 (
    pause
)
