@echo off
echo Starting Medical Monitoring System...

set ROOT=%~dp0

start "Simulator" cmd /k "cd /d "%ROOT%" && python simulators\patient_simulator.py"
timeout /t 2 /nobreak > nul

start "Processor" cmd /k "cd /d "%ROOT%" && python app.py"
timeout /t 2 /nobreak > nul

start "UI" cmd /k "cd /d "%ROOT%ui" && npm run dev"
timeout /t 3 /nobreak > nul

start "" "http://localhost:5173/patient_virtual.html"

echo All services started!
pause
