@echo off
set count=0
:loop
set /a count+=1
if %count% gtr 3 (
    exit /b
)
start "Matrix Train %count%" "D:\Code\EmmanuelProject\venv\Scripts\python.exe" "D:\Code\EmmanuelProject\train_matrix.py"
timeout /t 5 /nobreak >nul
goto loop