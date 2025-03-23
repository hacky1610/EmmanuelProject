#!/bin/bash

# Anzahl der Wiederholungen setzen
n=6

# Python-Skript n-mal ausführen
for i in $(seq 1 $n)
do
    echo "Starte Durchlauf $i..."
    ./venv1/bin/python evaluate_combos.py &
done

echo "Alle Durchläufe abgeschlossen."
read -p "Drücke Enter zum Beenden..."