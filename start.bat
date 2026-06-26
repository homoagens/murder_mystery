@echo off
cd /d "%~dp0"
start "" /b cmd /c "timeout /t 2 /nobreak > nul && start http://localhost:7860"
venv\Scripts\python.exe -m app.run
