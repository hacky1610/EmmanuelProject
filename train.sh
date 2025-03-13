#!/bin/bash

# Anzahl der Wiederholungen setzen
n=6

# Python-Skript n-mal ausführen
for ((i=1; i<=n; i++))
do
    echo "Starte Durchlauf $i..."
    ./venv4/bin/python evaluate_combos.py &
done

echo "Alle Durchläufe abgeschlossen."
read -p "Drücke Enter zum Beenden..."