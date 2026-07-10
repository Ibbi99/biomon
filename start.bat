@echo off
echo Starting Medical Monitoring System...

start "Simulator" cmd /k "cd /d C:\Users\anton\Desktop\Licenta\biomon && python simulators/patient_simulator.py"
timeout /t 2 /nobreak > nul

start "Processor" cmd /k "cd /d C:\Users\anton\Desktop\Licenta\biomon && python app.py"
timeout /t 2 /nobreak > nul

start "UI" cmd /k "cd /d C:\Users\anton\Desktop\Licenta\biomon\ui && npm run dev"
timeout /t 3 /nobreak > nul

start "" "http://localhost:5173/patient_virtual.html"

echo All services started!
