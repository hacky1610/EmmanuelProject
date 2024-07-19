#!/bin/bash

# Pfad zum Python-Interpreter
PYTHON_INTERPRETER="~/Documents/Projects/EmmanuelProject/venv/bin/python"

# Name des Python-Skripts
PYTHON_SCRIPT="train_matrix.py"

# Anzahl der Wiederholungen
NUM_RUNS=10

# Zeit in Sekunden zwischen den Aufrufen
SLEEP_TIME=60

# Schleife für die Ausführung des Python-Skripts
for ((i=1; i<=NUM_RUNS; i++))
do
  echo "Ausführung $i von $NUM_RUNS"
  python $PYTHON_SCRIPT &
  if [ $i -lt $NUM_RUNS ]; then
    echo "Warten für $SLEEP_TIME Sekunden..."
    sleep $SLEEP_TIME
  fi
done

echo "Alle $NUM_RUNS Ausführungen abgeschlossen."
