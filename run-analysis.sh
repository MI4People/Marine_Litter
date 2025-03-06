#!/bin/bash

# Setze das Log-Verzeichnis und die Log-Datei
LOG_DIR="/home/demo1/logs"
LOG_FILE="$LOG_DIR/analysis_$(date +'%Y-%m-%d').log"

# Falls das Verzeichnis nicht existiert, erstelle es
mkdir -p $LOG_DIR

# Führe den Docker-Container aus und speichere das Log
docker run --rm -e DAYBEFORE=2 -e WORKERS=3 -e DEVICE="cuda" marine_litter-image > "$LOG_FILE" 2>&1
