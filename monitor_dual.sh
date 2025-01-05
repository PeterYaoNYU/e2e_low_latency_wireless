#!/bin/bash

# Check if the correct number of arguments are provided
if [ "$#" -ne 3 ]; then
    echo "Usage: $0 interface duration interval"
    echo "where 'interface' is the name of the interface on which the queue"
    echo "is running (e.g., eth2), 'duration' is the total runtime (in seconds),"
    echo "and 'interval' is the time between measurements (in seconds)"
    exit 1
fi

# Assign input arguments to variables
interface=$1
duration=$2
interval=$3

# Calculate the end time based on the duration
end=$((SECONDS + duration))

# Start monitoring the queue
while [ $SECONDS -lt $end ]
do
    # Print timestamp at the beginning of each line (useful for data analysis)
    echo -n "$(date +%s.%N) "
    
    # Monitor the qdisc on the specified interface (shows packet stats, queue length, and drop info)
    # Specifically monitor the DualPI2 queue (handle 3: in this case)
    echo $(tc -p -s -d qdisc show dev $interface)
    
    # Sleep for the specified interval before taking the next measurement
    sleep $interval
done
