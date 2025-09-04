#!/bin/bash

LOG_DIR="/home/demo1/logs"
LOG_FILE="$LOG_DIR/analysis_$(date +'%Y-%m-%d').log"

mkdir -p $LOG_DIR

docker run --rm -e DAYS_BEFORE=2 -e ORDER_WORKERS=3 -e PREDICT_WORKERS=3 -e DEVICE="cuda" marine_litter-image > "$LOG_FILE" 2>&1
