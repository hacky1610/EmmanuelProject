#!/bin/bash

# Name des Programms, das gestartet werden soll
PROGRAMM="python train_matrix.py"


# Anzahl der Aufrufe
ANZAHL=10

# Anzahl der verfügbaren CPU-Kerne (Ermittle die Anzahl der Kerne im System)
KERNANZAHL=$(nproc)

for i in $(seq 0 $((ANZAHL-1)))
do
  # Berechne den CPU-Kern, auf dem dieser Aufruf laufen soll (Modulo-Operation)
  KERN=$((i % KERNANZAHL))

  echo "Starte $PROGRAMM auf CPU-Kern $KERN"

  # Starte das Programm auf dem entsprechenden Kern
  taskset -c $KERN $PROGRAMM &

  # Optional: Warten, bis der vorherige Prozess abgeschlossen ist (entfernen, wenn parallele Ausführung gewünscht ist)
  sleep 10
done
