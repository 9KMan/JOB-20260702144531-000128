#!/bin/bash
REPO="/home/deploy/squad/build-worker/JOB-20260616155014-000100"
MAX_ITER=14
SLEEP_SEC=90
LOGFILE="/home/deploy/tuinui/build_monitor.log"

prev_hash=""
consecutive_count=0

echo "Starting build monitor at $(date)" > "$LOGFILE"

for i in $(seq 1 $MAX_ITER); do
    commit_info=$(timeout 10 git -C "$REPO" log --oneline -1 2>&1)
    if [ $? -ne 0 ]; then
        echo "[Check $i/$MAX_ITER] git failed" >> "$LOGFILE"
    else
        commit_hash=$(echo "$commit_info" | awk '{print $1}')
        commit_msg=$(echo "$commit_info" | cut -d' ' -f2-)
        echo "[Check $i/$MAX_ITER] Hash: $commit_hash | Msg: $commit_msg" >> "$LOGFILE"
        
        if echo "$commit_msg" | grep -qi "SUMMARY"; then
            echo "JOB-100 build complete: $commit_hash" >> "$LOGFILE"
            echo "JOB-100 build complete: $commit_hash"
            exit 0
        fi
        
        if [ "$commit_hash" = "$prev_hash" ]; then
            consecutive_count=$((consecutive_count + 1))
            if [ $consecutive_count -ge 5 ]; then
                echo "JOB-100 build complete: $commit_hash" >> "$LOGFILE"
                echo "JOB-100 build complete: $commit_hash"
                exit 0
            fi
        else
            consecutive_count=1
            prev_hash="$commit_hash"
        fi
    fi
    
    if [ $i -lt $MAX_ITER ]; then
        sleep $SLEEP_SEC
    fi
done

final_hash=$(timeout 10 git -C "$REPO" log --oneline -1 2>/dev/null | awk '{print $1}')
echo "JOB-100 build may be stalled — last commit: $final_hash" >> "$LOGFILE"
echo "JOB-100 build may be stalled — last commit: $final_hash"
exit 0
