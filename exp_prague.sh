#!/bin/bash

# Check if the script received exactly one argument
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <filename_prefix>"
    exit 1
fi

# Variables
filename_prefix=$1
duration=300  # Replace with your desired duration
flows=5    # Replace with your desired number of flows
flows_ran=4
iperf_server_1="12.1.1.130"

# prague receiver corss traffic. 
iperf_server_2="10.0.8.2"


# Start ss monitoring for the first UE in the background
rm -f ${filename_prefix}-ss-prague.txt
start_time=$(date +%s)
while true; do
    ss --no-header -eipn dst $iperf_server_1 | ts '%.s' | tee -a ${filename_prefix}-ss-prague.txt
    current_time=$(date +%s)
    elapsed_time=$((current_time - start_time))
    if [ $elapsed_time -ge $duration ]; then
        break
    fi
    sleep 0.1
done &

# Start ss monitoring for the second UE in the background
rm -f ${filename_prefix}-ss-prague-cross-traffic.txt
start_time=$(date +%s)
while true; do
    ss --no-header -eipn dst $iperf_server_2 | ts '%.s' | tee -a ${filename_prefix}-ss-prague-cross-traffic.txt
    current_time=$(date +%s)
    elapsed_time=$((current_time - start_time))
    if [ $elapsed_time -ge $duration ]; then
        break
    fi
    sleep 0.1
done &

# Give some time for ss monitoring to start
sleep 1

# Start iperf3 for the first UE
iperf3 -c $iperf_server_1 -t $duration -P $flows_ran -C prague -p 4008 -J -O 60 > ${filename_prefix}-iperf-prague.json &

iperf3 -c $iperf_server_2 -t $duration -P $flows -C prague -p 4008 -b 2.5M -J -O 60 > ${filename_prefix}-iperf-prague-cross-traffic.json &


# Wait for background processes to complete
wait

echo "Iperf tests completed."
