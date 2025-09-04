#!/bin/bash

LOG_DIR="/home/demo1/logs"
LOG_FILE="$LOG_DIR/analysis_$(date +'%Y-%m-%d').log"

mkdir -p $LOG_DIR

docker run --rm -e DAYBEFORE=2 -e WORKERS=3 -e DEVICE="cuda" marine_litter-image > "$LOG_FILE" 2>&1
