@echo off
setlocal enabledelayedexpansion

:: Anzahl der Wiederholungen setzen
set "n=8"

:: Python-Skript ausführen n-mal
for /L %%i in (1,1,%n%) do (
    echo Starte Durchlauf %%i...
    start venv4\Scripts\Python.exe evaluate_combos.py
)

echo Alle Durchläufe abgeschlossen.
pause