@echo off
rem Starts Image Hash Lab. Scan results are saved into the csv folder and opened automatically.
set PYTHONHOME=
cd /d "%~dp0"
python -m pip install -q -r requirements.txt
python server.py
pause
