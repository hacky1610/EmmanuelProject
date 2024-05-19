@echo off
set count=0
:loop
set /a count+=1
if %count% gtr 15 (
    exit /b
)
start "MeinProzess" "D:\Code\EmmanuelProject\venv\Scripts\python.exe" "D:\Code\EmmanuelProject\train.py"
timeout /t 80 /nobreak >nul
goto loop